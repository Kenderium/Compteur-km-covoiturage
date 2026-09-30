"""Correspondance badge RFID -> nom affiché.

Les noms ne sont plus codés en dur : ils viennent du serveur (synchro WiFi)
ou de l'app (Bluetooth), et sont gardés dans badges.json.
"""

import json


def uid_str(uid):
    """Numéro de badge normalisé en chaîne (clé JSON)."""
    return str(uid)


class Badges:
    def __init__(self, path="badges.json"):
        self.path = path
        try:
            with open(path) as f:
                self.names = json.loads(f.read())
        except (OSError, ValueError):
            self.names = {}

    def save(self):
        with open(self.path, "w") as f:
            f.write(json.dumps(self.names))

    def name(self, uid):
        uid = uid_str(uid)
        return self.names.get(uid) or ("Badge " + uid[-4:])

    def known(self, uid):
        return uid_str(uid) in self.names

    def set(self, uid, name):
        uid = uid_str(uid)
        name = (name or "").strip()[:16]
        if name:
            self.names[uid] = name
        elif uid in self.names:
            del self.names[uid]
        self.save()

    def replace_all(self, mapping):
        self.names = {}
        for uid in mapping:
            if mapping[uid]:
                self.names[uid_str(uid)] = str(mapping[uid])[:16]
        self.save()
