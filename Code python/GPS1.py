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
import time

uart = machine.UART(1, baudrate=9600, tx = machine.Pin(1))
gps = MicropyGPS()

def startgps(running=False):
    """Demarre le tracking gps et logs les latitudes et longitudes dans le fichier de logs

    Args:
        running (bool, optional): . Defaults to False.
    """

    gps.start_logging("logs.txt")

    while running:
        if uart.any():
            coordonees = gps.latitude_string(), gps.longitude_string()

            gps.write_log(str(coordonees) + '\n')
            
        time.sleep(1.5) 

    gps.stop_logging()     

def distance(lat1,lat2, long1, long2):
    """Calcul la distance entre deux points grace a la formule haversine

    Args:
        lat1 [coordonees]: Latitude des points du point de depart
        lat2 [coordonees]: Latitude des points du point d'arrivee
        long1 [coordonees]: Longitude des points du point de depart
        long2 [coordonees]: Longitude des points du point d'arrivee

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

lat1 = 50 + 43/60 + 28.4/3600
long1 = 4 + 23/60+ 4.6/3600
lat2 = 50 + 42/60 + 56.5/3600
long2 = 4 + 22/60 + 18.4/3600
print(distance(lat1, lat2, long1, long2))