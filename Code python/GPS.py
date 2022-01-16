'''
File: GPS.py
Project: Code python
Created Date: Su Jan 2022
Author: Julien Dagnelie
-----
Last Modified: Sun Jan 16 2022
Modified By: Julien Dagnelie & Loïc Tumelaire
-----
Copyright (c) 2022 Universite catholique de Louvain
-----
HISTORY:
Date   Sun Jan 16 2022   	By Julien Dagnelie	Comments
----------	---	---------------------------------------------------------
'''
import machine
from micropyGPS import MicropyGPS
from math import sin, cos, atan2, radians, sqrt

uart = machine.UART(1, baudrate=9600, tx = machine.Pin(1))
gps = MicropyGPS()

def startgps(running=False):
    while running:
        if uart.any():
            lat = gps.latitude_string()
            long = gps.longitude_string()

            log = gps.start_logging("logs.txt")



def distance(lat1,lat2, long1, long2):
    """Calcul la distance entre deux points grace a la formule haversine

    Args:
        lat1 [int]: Latitude des points du point de depart
        lat2 [int]: Latitude des points du point d'arrivee
        long1 [int]: Longitude des points du point de depart
        long2 [int]: Longitude des points du point d'arrivee

    Returns:
        distkm [int]: distance entre les deux point (lat1, long1) et (lat2, long2)
    """
    R = 6371000 # Rayon de la terre [m]

    phi1, phi2 = radians(lat1), radians(lat2)

    delta_phi = radians(phi2 - phi1)
    delta_lambda = radians(long2-long1)

    # Calcul grace a la formule haversine c.f Wikipedia

    a = sin(delta_phi / 2.0) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2.0) ** 2
    
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distm = R * c # distance [m]
    distkm = round(distm / 1000, 3) # distance [km]

    return distkm
    

