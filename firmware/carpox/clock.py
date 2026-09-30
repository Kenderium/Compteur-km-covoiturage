"""Heure réelle du boîtier.

Le Pico n'a pas d'horloge sauvegardée : à chaque démarrage il ignore l'heure.
Dès qu'une synchro avec le serveur réussit, on retient le décalage entre son
horloge interne et l'heure Unix du serveur.
"""

import time

_offset = None


def set_unix_time(unix_ts):
    global _offset
    _offset = int(unix_ts) - int(time.time())


def now():
    """Heure Unix, ou None si l'heure n'a pas encore été reçue."""
    if _offset is None:
        return None
    return int(time.time()) + _offset
