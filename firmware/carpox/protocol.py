"""Commandes texte échangées avec l'app par Bluetooth (BLE).

Une commande par ligne, chaque réponse est une ligne JSON :

    AUTH <code>          code d'appairage du boîtier (obligatoire en premier)
    STATUS               état du boîtier et du trajet en cours
    EVENTS <seq>         événements après <seq>, un par ligne, puis {"end": true}
    APPLY <json>         applique la réponse du serveur relayée par l'app
    BADGE <uid> <nom>    nomme un badge (nom vide = oublier)
    LASTSCAN             dernier badge présenté au lecteur (pour l'associer)

Ce module ne dépend pas du matériel : il est testé sous CPython.
"""

import json

from carpox import sync

MAX_AUTH_FAILURES = 5


class CommandHandler:
    def __init__(self, device_id, pin, journal, badges, recorder=None, clock=None, drive=None):
        self.device_id = device_id
        self.pin = str(pin)
        self.journal = journal
        self.badges = badges
        self.recorder = recorder
        self.clock = clock
        self.drive = drive
        self.last_scan = None
        self.on_connect()

    def on_connect(self):
        self.authenticated = False
        self.failures = 0

    def handle(self, line):
        """Traite une ligne reçue. Retourne la liste des lignes à renvoyer."""
        line = line.strip()
        if not line:
            return []
        parts = line.split(" ", 1)
        cmd = parts[0].upper()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "AUTH":
            return [self._auth(arg)]
        if not self.authenticated:
            return [_err("auth requise")]
        try:
            if cmd == "STATUS":
                return [json.dumps(self.status())]
            if cmd == "EVENTS":
                return self._events(arg)
            if cmd == "APPLY":
                acked = sync.apply_response(json.loads(arg), self.journal, self.badges, self.clock)
                return [json.dumps({"ok": True, "acked": acked, "synced_seq": self.journal.synced_seq})]
            if cmd == "BADGE":
                bits = arg.split(" ", 1)
                if not bits[0]:
                    return [_err("usage : BADGE <uid> <nom>")]
                self.badges.set(bits[0], bits[1] if len(bits) > 1 else "")
                return [json.dumps({"ok": True})]
            if cmd == "LASTSCAN":
                return [json.dumps({"ok": True, "uid": self.last_scan})]
        except (ValueError, KeyError, TypeError) as exc:
            return [_err(str(exc))]
        return [_err("commande inconnue")]

    def _auth(self, code):
        if self.failures >= MAX_AUTH_FAILURES:
            return _err("trop d'essais, reconnectez-vous")
        if code.strip() == self.pin:
            self.authenticated = True
            self.failures = 0
            return json.dumps({"ok": True, "device_id": self.device_id})
        self.failures += 1
        return _err("code incorrect")

    def _events(self, arg):
        after = int(arg) if arg.strip() else self.journal.synced_seq
        out = []
        for e in self.journal.after(after, sync.BATCH_SIZE, sync.BATCH_BYTES):
            out.append(json.dumps({"event": e}))
        out.append(json.dumps({"ok": True, "end": True, "count": len(out)}))
        return out

    def status(self):
        trip = None
        r = self.recorder
        if r is not None and (r.active or r.driver):
            trip = {"active": r.active, "km": round(r.km, 2), "driver": r.driver, "passengers": r.passengers}
        return {
            "ok": True,
            "device_id": self.device_id,
            "last_seq": self.journal.last_seq(),
            "synced_seq": self.journal.synced_seq,
            "pending": self.journal.pending_count(),
            "trip": trip,
            "drive_km": round(self.drive.km, 2) if self.drive is not None else None,
        }


def _err(message):
    return json.dumps({"ok": False, "error": message})
