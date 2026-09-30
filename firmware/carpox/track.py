"""Parcours d'un trajet, simplifié pour tenir dans la flash et le WiFi.

On garde un point au plus tous les `min_step_m` mètres. Au-delà de
`max_points`, on retire un point sur deux et on double l'écart minimal :
un long trajet reste dessiné en entier, juste moins finement.
"""

from carpox_core.geo import haversine_m


class Track:
    def __init__(self, min_step_m=200.0, max_points=250, points=None):
        self.min_step_m = min_step_m
        self.max_points = max_points
        self.points = [list(p) for p in points] if points else []
        self._tail = None  # dernier point vu, pas encore retenu

    def add(self, lat, lon):
        point = [round(lat, 5), round(lon, 5)]
        if self.points:
            last = self.points[-1]
            if haversine_m(last[0], last[1], point[0], point[1]) < self.min_step_m:
                self._tail = point
                return False
        self.points.append(point)
        self._tail = None
        if len(self.points) > self.max_points:
            self.points = self.points[:-1:2] + [self.points[-1]]
            self.min_step_m *= 2
        return True

    def copy(self):
        """Points retenus plus le dernier point vu, sans modifier le parcours."""
        if self._tail is None:
            return list(self.points)
        return self.points + [self._tail]

    def finish(self):
        """Liste des points, arrivée comprise."""
        if self._tail is not None:
            self.points.append(self._tail)
            self._tail = None
        return self.points
