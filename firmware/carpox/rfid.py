"""Lecteur RFID RC522."""

from mfrc522 import MFRC522

import config


class RfidReader:
    def __init__(self):
        self.reader = MFRC522(**config.RFID)

    def read(self):
        """Numéro du badge présenté (chaîne), ou None."""
        self.reader.init()
        stat, _ = self.reader.request(self.reader.REQIDL)
        if stat != self.reader.OK:
            return None
        stat, uid = self.reader.SelectTagSN()
        if stat != self.reader.OK:
            return None
        card = int.from_bytes(bytes(uid), "little")
        return str(card) if card else None
