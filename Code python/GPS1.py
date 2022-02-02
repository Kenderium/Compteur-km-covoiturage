'''
File: GPS.py
Project: Code python
Created Date: Su Jan 2022
Author: Julien Dagnelie
-----
Last Modified: Wed Feb 02 2022
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
gps = MicropyGPS()
from math import radians, acos, cos, sin
import time
import _thread                                              # Pour exécuter plusieures taches en simultané

baton = _thread.allocate_lock()                             # Bloqueur de thread pour éviter crash,...
uart = machine.UART(0, baudrate=9600)  # Pin du GPS     , tx = machine.Pin(0) ?
on = True

def startgps(on):
    """Demarre le tracking gps et logs les latitudes et longitudes dans le fichier de logs

    Args:
        running (bool, optional): . Defaults to False.
    """

    gps.start_logging("logs.txt")                       # Base de données meilleure ?
    while on:
        if uart.any():
            coordonees = gps.latitude, gps.longitude
            gps.write_log(str(coordonees) + "\n")  
        time.sleep(1.5)
        print("pas ok")
    print("oki")
    gps.stop_logging()
    print("ok") 

def second_thread():        # Seconde tâche: Si on appuie sur le bouton
        baton.acquire()     # Regarde si le thread est libre et se l'acquière
        global on
        time.sleep(5)
        bouton = True       # On appuie sur le bouton "A modifier"
        if bouton:
            on = False      # On arrete le Gps
            print("bouton")
        baton.release()     # Libère le thread

"""
INUTILE ?

def transformation_coord(coord): 
    new_coord = coord[0] + coord[1] / 60
    return new_coord
"""

def distance(coord1, coord2):
    """Calcul la distance entre 2 point avec les latitudes et longitudes

    Args:
        coord1 (tuple): tuple contenant la latitude et la longitude d'un point
        coord2 (tuple): tuple contenant la latitude et la longitude d'un point

    Returns:
        [type]: [description]
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
    global on
    _thread.start_new_thread(second_thread, ())   # Création du thread et démarrage
    
    while on:
        print("bug")
        startgps(True)              # Démarre le gps
        print('bugg')
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
    return km

print(run())