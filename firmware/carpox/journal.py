"""Journal des événements du boîtier (trajets), stocké en JSON lines.

Chaque événement reçoit un numéro de séquence croissant `seq`. Le serveur
s'en sert pour dédoublonner : renvoyer deux fois le même événement (coupure
WiFi pendant la synchro, relais par le téléphone puis par le WiFi) est sans
danger. `synced_seq` retient jusqu'où le serveur a confirmé la réception.

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

    def all(self):
        events = []
        try:
            with open(self.path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except ValueError:
                        # Ligne tronquée (coupure de courant pendant l'écriture).
                        pass
        except OSError:
            pass
        return events

    def after(self, seq, limit=None):
        out = []
        for e in self.all():
            if e.get("seq", 0) > seq:
                out.append(e)
                if limit is not None and len(out) >= limit:
                    break
        return out

    def unsynced(self, limit=None):
        return self.after(self.synced_seq, limit)

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

    def recent(self, count):
        events = self.all()
        return events[-count:] if count else []

    def compact(self, keep_synced=50):
        """Supprime les vieux événements déjà synchronisés pour libérer la flash."""
        events = self.all()
        kept_synced = [e for e in events if e.get("seq", 0) <= self.synced_seq][-keep_synced:]
        unsynced = [e for e in events if e.get("seq", 0) > self.synced_seq]
        kept = kept_synced + unsynced
        if len(kept) == len(events):
            return 0
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            for e in kept:
                f.write(json.dumps(e) + "\n")
        _replace(tmp, self.path)
        return len(events) - len(kept)
