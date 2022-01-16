'''
File: Main.py
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

import GPS1
import ECRAN
import RFID
import Maths 
import machine

bouton1 = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_DOWN) # bouton suivant
bouton2 = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_DOWN) # bouton valider
led_verte = machine.Pin(17, machine.Pin.OUT)
led_rouge = machine.Pin(16, machine.Pin.OUT)

def bonjour():
    ECRAN.txt("Bonjour", 0, 0)
    ECRAN.txt("Que voulez-vous faire ?", 1, 1)
    ECRAN.afficher()

def menu1():
    ECRAN.txt("Encoder Chauffeur", 1, 1)
    ECRAN.afficher()
def menu2():
    ECRAN.txt("Encoder Passagers", 1, 1)
    ECRAN.afficher()
def menu3():
    ECRAN.txt("Démarrer le voyage", 1, 1)
    ECRAN.afficher()

def run():
    """Lance toute l'artillerie lourde
    """
    pass

if bouton1.value():                             # Allumage
    bonjour()                                   # Message de bienvenue
    while True:
        i = 1
        if i == 1:
            menu1()
            if bouton2.value():                 # Confirmation
                pass                            # Encoder conducteur
        if i == 2:
            menu2()
            if bouton2.value():                 # Confirmation
                pass                            # Encoder Passager
        if i == 3:
            menu1()
            if bouton2.value():                 # Confirmation
                run                             # Démarer voyage
        if bouton1.value():                     # Changer de menu
            i +=1

run()