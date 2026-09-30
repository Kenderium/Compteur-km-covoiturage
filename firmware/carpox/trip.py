"""Enregistrement d'un trajet : conducteur, passagers, km et parcours mesurés au GPS."""

from carpox_core.geo import DistanceAccumulator
from carpox.track import Track


class TripRecorder:
    def __init__(self, min_step_m=25.0):
        self.min_step_m = min_step_m
        self.reset()

    def reset(self):
        self.driver = None
        self.passengers = []
        self.active = False
        self.started_at = None
        self.acc = DistanceAccumulator(min_step_m=self.min_step_m)
        self.track = Track()

    def set_driver(self, uid):
        self.driver = str(uid)
        if self.driver in self.passengers:
            self.passengers.remove(self.driver)

    def add_passenger(self, uid):
        """Ajoute un passager. Retourne False s'il est déjà à bord ou conduit."""
        uid = str(uid)
        if uid == self.driver or uid in self.passengers:
            return False
        self.passengers.append(uid)
        return True

    def start(self, unix_ts=None):
        if self.driver is None:
            raise ValueError("pas de conducteur")
        self.active = True
        self.started_at = unix_ts

    def add_fix(self, lat, lon, t_s=None, hdop=None):
        if self.active and self.acc.add(lat, lon, t_s, hdop):
            self.track.add(lat, lon)
            return True
        return False

    @property
    def km(self):
        return self.acc.total_km

    def snapshot(self):
        """État à sauvegarder : le boîtier peut perdre le courant en cours de route."""
        return {
            "driver": self.driver,
            "passengers": list(self.passengers),
            "total_m": self.acc.total_m,
            "points": self.acc.points,
            "started_at": self.started_at,
            "track": self.track.copy(),
        }

    def restore(self, state):
        self.reset()
        self.driver = state["driver"]
        self.passengers = list(state.get("passengers") or [])
        self.acc.total_m = state.get("total_m", 0.0)
        self.acc.points = state.get("points", 0)
        self.started_at = state.get("started_at")
        self.track = Track(points=state.get("track"))
        self.active = True

    def stop(self, unix_ts=None, temp_c=None):
        """Termine le trajet et retourne l'événement à écrire au journal."""
        event = {
            "type": "trip",
            "driver": self.driver,
            "passengers": list(self.passengers),
            "km": round(self.acc.total_km, 3),
            "start": self.started_at,
            "end": unix_ts,
            "gps_points": self.acc.points,
            "track": self.track.finish(),
        }
        if temp_c is not None:
            event["temp_c"] = round(temp_c, 1)
        self.reset()
        return event
