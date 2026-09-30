"""Km roulés sans trajet badgé.

Le boîtier est alimenté par la voiture : il compte les km dès que la voiture
roule, même si personne n'a badgé. Ces km servent à estimer le carburant
restant, et sont à la charge de celui qui paie le plein suivant.

Un « segment » commence au premier déplacement et se termine quand la voiture
reste immobile `idle_s` secondes (ou au démarrage suivant, si le courant a
été coupé). Il est alors écrit au journal comme un événement "drive".
"""

from carpox_core.geo import DistanceAccumulator
from carpox.track import Track


class DriveRecorder:
    def __init__(self, min_step_m=25.0):
        self.min_step_m = min_step_m
        self.acc = DistanceAccumulator(min_step_m=min_step_m)
        self._clear()

    def _clear(self):
        self.track = Track()
        self.started_at = None
        self.ended_at = None
        self.last_move_s = None

    @property
    def active(self):
        """Vrai dès que la voiture a vraiment bougé (pas un GPS qui tremble)."""
        return self.acc.total_m > 0

    @property
    def km(self):
        return self.acc.total_km

    def add_fix(self, lat, lon, t_s=None, hdop=None, now_s=None, unix_ts=None):
        """Ajoute une position. `now_s` : horloge monotone du boîtier, en secondes."""
        before_m = self.acc.total_m
        origin = self.acc.position
        if not self.acc.add(lat, lon, t_s, hdop):
            return False
        if self.acc.total_m > before_m:
            if self.started_at is None:
                self.started_at = unix_ts
                if origin is not None:
                    self.track.add(origin[0], origin[1])
            self.track.add(lat, lon)
            self.ended_at = unix_ts
            self.last_move_s = now_s
        return True

    def idle_for(self, now_s):
        if not self.active or self.last_move_s is None or now_s is None:
            return 0
        return now_s - self.last_move_s

    def close(self, keep_position=True):
        """Termine le segment. Retourne l'événement à écrire au journal, ou None.

        `keep_position` : le prochain segment repart de la dernière position,
        pour ne perdre aucun mètre. À désactiver quand un trajet badgé
        commence, car c'est alors lui qui compte les km.
        """
        event = None
        if self.active:
            event = {
                "type": "drive",
                "km": round(self.acc.total_km, 3),
                "start": self.started_at,
                "end": self.ended_at,
                "gps_points": self.acc.points,
                "track": self.track.finish(),
            }
        self.acc.restart(keep_position)
        self._clear()
        return event

    def snapshot(self):
        """État à sauvegarder : la coupure du contact coupe aussi le boîtier."""
        return {
            "total_m": self.acc.total_m,
            "points": self.acc.points,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "track": self.track.copy() if self.active else [],
        }

    def restore(self, state):
        self.acc.total_m = state.get("total_m", 0.0)
        self.acc.points = state.get("points", 0)
        self.started_at = state.get("started_at")
        self.ended_at = state.get("ended_at")
        self.track = Track(points=state.get("track"))
