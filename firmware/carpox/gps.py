"""GPS NEO-6M sur UART, lu sans bloquer.

`poll()` doit être appelé souvent (boucle principale) : il consomme les
caractères reçus et renvoie une position quand une nouvelle phrase valide est
arrivée. Les km sont additionnés par carpox_core.geo.DistanceAccumulator.
"""

import time

import machine
from micropyGPS import MicropyGPS

import config


class Gps:
    def __init__(self):
        self.uart = machine.UART(config.GPS_UART, baudrate=9600,
                                 tx=machine.Pin(config.GPS_TX), rx=machine.Pin(config.GPS_RX))
        self.parser = MicropyGPS(location_formatting="dd")
        self.last_fix_ms = None
        # Horloge monotone en ms qui ne reboucle pas (ticks_ms reboucle après ~12 jours).
        self._prev_ticks = time.ticks_ms()
        self._elapsed_ms = 0

    def poll(self):
        """Retourne (lat, lon, t_s, hdop) si une nouvelle position est disponible."""
        fix = None
        while self.uart.any():
            data = self.uart.read()
            if not data:
                break
            for byte in data:
                sentence = self.parser.update(chr(byte))
                if sentence in ("GPRMC", "GNRMC", "GPGGA", "GNGGA") and self.has_fix():
                    fix = self._position()
        return fix

    def has_fix(self):
        return self.parser.valid and self.parser.fix_stat > 0

    def satellites(self):
        return self.parser.satellites_in_use

    def _position(self):
        lat, ns = self.parser.latitude
        lon, ew = self.parser.longitude
        if ns == "S":
            lat = -lat
        if ew == "W":
            lon = -lon
        now = time.ticks_ms()
        self._elapsed_ms += time.ticks_diff(now, self._prev_ticks)
        self._prev_ticks = now
        self.last_fix_ms = now
        return lat, lon, self._elapsed_ms / 1000.0, self.parser.hdop
