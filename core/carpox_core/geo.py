"""Distances GPS.

Compatible CPython et MicroPython (pas d'annotations, pas de dataclasses).
"""

import math

# Rayon terrestre moyen (IUGG), en mètres.
EARTH_RADIUS_M = 6371008.8


def haversine_m(lat1, lon1, lat2, lon2):
    """Distance orthodromique en mètres entre deux points en degrés décimaux."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    # min() protège contre a légèrement > 1 par erreur d'arrondi.
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(min(1.0, a)))


def haversine_km(lat1, lon1, lat2, lon2):
    return haversine_m(lat1, lon1, lat2, lon2) / 1000.0


def to_decimal(degrees, minutes, hemisphere):
    """Convertit le format micropyGPS 'ddm' ([deg, min, 'N']) en degrés décimaux signés."""
    value = degrees + minutes / 60.0
    if hemisphere in ("S", "W"):
        value = -value
    return value


class DistanceAccumulator:
    """Additionne la distance parcourue à partir de positions GPS successives.

    Un GPS à l'arrêt « tremble » de quelques mètres : additionner tous les points
    gonflerait les km. On ne compte donc un déplacement que lorsqu'on s'est
    éloigné d'au moins `min_step_m` du dernier point retenu. Les sauts
    impossibles (vitesse > `max_speed_kmh`) sont ignorés, ainsi que les points
    trop imprécis (HDOP > `max_hdop`).
    """

    def __init__(self, min_step_m=25.0, max_speed_kmh=250.0, max_hdop=5.0):
        self.min_step_m = min_step_m
        self.max_speed_kmh = max_speed_kmh
        self.max_hdop = max_hdop
        self.total_m = 0.0
        self.points = 0
        self._last = None  # (lat, lon, t_s)

    def add(self, lat, lon, t_s=None, hdop=None):
        """Ajoute une position. Retourne True si elle a été retenue."""
        if hdop is not None and hdop > 0 and hdop > self.max_hdop:
            return False
        if lat == 0.0 and lon == 0.0:  # pas de fix
            return False
        if self._last is None:
            self._last = (lat, lon, t_s)
            self.points += 1
            return True
        last_lat, last_lon, last_t = self._last
        step = haversine_m(last_lat, last_lon, lat, lon)
        if step < self.min_step_m:
            return False
        if t_s is not None and last_t is not None:
            dt = t_s - last_t
            if dt <= 0 or (step / dt) * 3.6 > self.max_speed_kmh:
                return False
        self.total_m += step
        self._last = (lat, lon, t_s)
        self.points += 1
        return True

    @property
    def position(self):
        """Dernier point retenu (lat, lon, t_s), ou None."""
        return self._last

    def restart(self, keep_position=True):
        """Remet la distance à zéro. Avec `keep_position`, le prochain point est
        mesuré depuis le dernier point retenu : aucun mètre n'est perdu."""
        self.total_m = 0.0
        self.points = 0
        if not keep_position:
            self._last = None

    @property
    def total_km(self):
        return self.total_m / 1000.0
