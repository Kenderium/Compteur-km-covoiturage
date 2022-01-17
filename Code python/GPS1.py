'''
File: GPS.py
Project: Code python
Created Date: Su Jan 2022
Author: Julien Dagnelie
-----
Last Modified: Tue Jan 18 2022
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
from math import radians, acos, cos, sin
import time
import os 

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
            coordonees = gps.latitude, gps.longitude

            gps.write_log(str(coordonees) + '\n')
            
        time.sleep(1.5) 

    gps.stop_logging()  


def transformation_coord(coord): 
    new_coord = coord[0] + coord[1] / 60
    return new_coord
    

def distance(coord1, coord2):
    """Calcul la distance entre 2 point avec les latitudes et longitudes

    Args:
        coord1 (tuple): tuple contenant la latitude et la longitude d'un point
        coord2 (tuple): tuple contenant la latitude et la longitude d'un point

    Returns:
        [type]: [description]
    """
  
    R = 6378137 # Rayon de la terre [m]

    phi1, phi2 = radians(coord1[0]), radians(coord2[0])
    lambda1, lambda2 = radians(coord1[0]), radians(coord2[1])

    delta_phi = radians(phi2 - phi1)
    delta_lambda = radians(lambda2-lambda1)

    # Calcul grace a la formule haversine c.f Wikipedia

    S = acos(sin(phi1)*sin(phi2) + cos(lambda1)*cos(lambda2)*cos(delta_lambda))

    distm = R * S # distance [m]
    distkm = round(distm / 1000, 3) # distance [km]

    return distkm


with open("C:\\Users\\jujud\\Documents\\Covoiturage\\Compteur-km-covoiturage\\Code python\\logs\\logs.txt") as file:
    l = []
    for line in file:
        l.append(line.strip())
    print(l)                            # Liste contenant comme chaque élément une coordonnée
    
    km = 0
    for c in range(len(l)):
        time.sleep(1.5)                 # Attendre que la voiture change de coordonnées
        km += distance(l[c],l[c+1])     # Somme distance entre chaque point