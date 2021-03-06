'''
File: GPS.py
Project: Code python
Created Date: Su Jan 2022
Author: Julien Dagnelie
-----
Last Modified: Wed Apr 20 2022
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
import _thread                                              # Pour exécuter plusieures taches en simultané

uart = machine.UART(1, baudrate=9600, tx = machine.Pin(8), rx = machine.Pin(9))
gps = MicropyGPS()

def startgps(start):
    """Demarre le tracking gps et logs les latitudes et longitudes dans le fichier de logs

    Args:
        running (bool, optional): . Defaults to False.
    """

    gps.start_logging("logs.txt")                       # Base de données meilleure ?
    if uart.any():
        coordonees = gps.latitude, gps.longitude
        gps.write_log(str(coordonees) + "\n")  
    time.sleep(1.5)
    gps.stop_logging()


"""
INUTILE ?

def transformation_coord(coord): 
    new_coord = float(coord[0]) + float(coord[1]) / 60
    return new_coord
"""

def distance(coord1, coord2):
    """Calcul la distance entre 2 point avec les latitudes et longitudes

    Args:
        coord1 (tuple): tuple contenant la latitude et la longitude d'un point
        coord2 (tuple): tuple contenant la latitude et la longitude d'un point

    Returns:
        distkm: [description]
    """
  
    R = 6378137 # Rayon de la terre [m]
    
    phi1, phi2 = radians(float(coord1[0])), radians(float(coord2[0]))
    lambda1, lambda2 = radians(float(coord1[0])), radians(float(coord2[1]))

    delta_phi = radians(phi2 - phi1)
    delta_lambda = radians(lambda2-lambda1)

    # Calcul grace a la formule haversine c.f Wikipedia

    S = acos(sin(phi1)*sin(phi2) + cos(lambda1)*cos(lambda2)*cos(delta_lambda))

    distm = R * S                   # distance [m]
    distkm = round(distm / 1000, 3) # distance [km]

    return distkm

def run():
    _thread.start_new_thread(second_thread, ())   # Création du thread et démarrage
    global go
    while go:
        startgps(True)              # Démarre le gps
    startgps(False)                 # Arrete le gps

    with open("logs.txt") as file:  # Ouvre le fichier des trajets
        l = []                      # Liste contenant comme chaque élément une coordonnée: ([0, 0.0, 'N'], [0, 0.0, 'W'])
        d = []                      # Liste finale, avec juste longitude, lat (sans "(" ")"
        km = 0                      # Compteur de km
        
        for line in file:
            l.append(line.strip())  # Ajoute les lignes du fichier dans une liste
            
        for c in range(len(l)):
            element = ""
            for char in l[c]:
                if char != "(" and char != ")":
                    element += char
            d.append(element)                   # Création de la liste d
            try:
                km += distance(d[c],d[c+1])     # Somme distance entre chaque point
            except IndexError:
                pass
            print(km)
    return km

def second_thread():        # Seconde tâche: Si on appuie sur le bouton
    global go
    bouton = True
    baton = _thread.allocate_lock()
    while bouton:
        baton.acquire()     # Regarde si le thread est libre et se l'acquière
        time.sleep(50)
        bouton = False       # On appuie sur le bouton "A modifier"
        if bouton == False:
            go = False
        baton.release()     # Libère le thread


go = True
print(run())