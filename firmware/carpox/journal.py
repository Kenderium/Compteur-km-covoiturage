"""Journal des événements du boîtier (trajets), stocké en JSON lines.

Chaque événement reçoit un numéro de séquence croissant `seq`. Le serveur
s'en sert pour dédoublonner : renvoyer deux fois le même événement (coupure
WiFi pendant la synchro, relais par le téléphone puis par le WiFi) est sans
danger. `synced_seq` retient jusqu'où le serveur a confirmé la réception.

Les trajets contiennent leur parcours GPS (quelques Ko chacun) : le fichier
est donc lu ligne par ligne, sans jamais le charger en entier en mémoire.

Tourne sous MicroPython et CPython (les tests l'utilisent directement).
"""

import json


def _read_json(path, default):
    try:
        with open(path) as f:
            return json.loads(f.read())
    except (OSError, ValueError):
        return default


def _write_json(path, value):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(json.dumps(value))
    _replace(tmp, path)


def _replace(src, dst):
    try:
        import os
    except ImportError:  # pragma: no cover
        import uos as os
    try:
        os.remove(dst)
    except OSError:
        pass
    os.rename(src, dst)


class Journal:
    def __init__(self, path="journal.jsonl", state_path="journal_state.json"):
        self.path = path
        self.state_path = state_path
        state = _read_json(state_path, {})
        self.next_seq = state.get("next_seq", 1)
        self.synced_seq = state.get("synced_seq", 0)

    def _save_state(self):
        _write_json(self.state_path, {"next_seq": self.next_seq, "synced_seq": self.synced_seq})

    def append(self, event):
        """Ajoute un événement et retourne-le avec son `seq`."""
        event = dict(event)
        event["seq"] = self.next_seq
        with open(self.path, "a") as f:
            f.write(json.dumps(event) + "\n")
        self.next_seq += 1
        self._save_state()
        return event

    def _lines(self):
        """(événement, ligne brute) un par un. Ignore une ligne tronquée par une coupure."""
        try:
            f = open(self.path)
        except OSError:
            return
        with f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line), line
                except ValueError:
                    pass

    def all(self):
        return [e for e, _ in self._lines()]

    def after(self, seq, limit=None, max_bytes=None):
        """Événements après `seq`. `max_bytes` limite la taille totale (au moins un
        événement est toujours renvoyé), pour tenir dans la mémoire du Pico."""
        out = []
        size = 0
        for e, line in self._lines():
            if e.get("seq", 0) <= seq:
                continue
            if max_bytes is not None and out and size + len(line) > max_bytes:
                break
            out.append(e)
            size += len(line)
            if limit is not None and len(out) >= limit:
                break
        return out

    def unsynced(self, limit=None, max_bytes=None):
        return self.after(self.synced_seq, limit, max_bytes)

    def pending_count(self):
        return self.next_seq - 1 - self.synced_seq

    def last_seq(self):
        return self.next_seq - 1

    def mark_synced(self, seq):
        """Le serveur a tout reçu jusqu'à `seq` (inclus)."""
        seq = min(seq, self.last_seq())
        if seq > self.synced_seq:
            self.synced_seq = seq
            self._save_state()

    def recent(self, count, kind=None, strip=("track",)):
        """Les `count` derniers événements (du type `kind` si donné), sans le parcours."""
        out = []
        if not count:
            return out
        for e, _ in self._lines():
            if kind is not None and e.get("type") != kind:
                continue
            for key in strip:
                e.pop(key, None)
            out.append(e)
            if len(out) > count:
                out.pop(0)
        return out

    def compact(self, keep_synced=50):
        """Supprime les vieux événements déjà synchronisés pour libérer la flash."""
        synced = 0
        for e, _ in self._lines():
            if e.get("seq", 0) <= self.synced_seq:
                synced += 1
        drop = synced - keep_synced
        if drop <= 0:
            return 0
        tmp = self.path + ".tmp"
        dropped = 0
        with open(tmp, "w") as f:
            for e, line in self._lines():
                if dropped < drop and e.get("seq", 0) <= self.synced_seq:
                    dropped += 1
                    continue
                f.write(line + "\n")
        _replace(tmp, self.path)
        return dropped
