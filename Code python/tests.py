'''
File: tests.py
Project: Code python
Created Date: Sa Jan 2022
Author: Julien Dagnelie & Loïc Tumelaire
-----
Last Modified: Mon Jan 31 2022
Modified By: Julien Dagnelie & Loïc Tumelaire
-----
Copyright (c) 2022 Universite catholique de Louvain
-----
HISTORY:
Date   Mon Jan 31 2022   	By Julien Dagnelie & Loïc Tumelaire	Comments
----------	---	---------------------------------------------------------
'''

import machine
import _thread
import time
from micropyGPS import MicropyGPS
gps = MicropyGPS()
uart = machine.UART(0, baudrate=9600, tx = machine.Pin(0))  #Pin du GPS

i=0
gps.start_logging("logs.txt")

while i != 8:
    coordonees = gps.latitude, gps.longitude
    gps.write_log(str(coordonees) + "\n") 
    time.sleep(1.5)
    i +=1
    
gps.stop_logging()


'''
compteur_km = True

running = True

def second_thread():         # Seconde tâche
    global compteur_km
    while compteur_km:
        baton.acquire()      # Regarde si le thread est libre et se l'acquière
        gps.start_logging("logs.txt")    # Base de données meilleure ?
        while running:
            if uart.any():
                print("nani")                               # La boucle n'est réalisée que 2 fois ? --> bug
                coordonees = gps.latitude, gps.longitude
                gps.write_log(str(coordonees))  
        time.sleep(1.5) 
        gps.stop_logging()
        print("okthread1")
        time.sleep(5)        # Pendant 5 secs (pour les tests)
        compteur_km = False
        print("okthread2")
        baton.release()      # Libère le thread

baton = _thread.allocate_lock()               # Bloqueur de thread pour éviter crash,...
_thread.start_new_thread(second_thread, ())   # Création du thread et démarrage

print("okmain1")
time.sleep(5)        # Pendant 5 secs (pour les tests)
print("okmain2")

'''