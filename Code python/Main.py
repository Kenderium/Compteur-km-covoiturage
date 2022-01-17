'''
File: Main.py
Project: Code python
Created Date: Su Jan 2022
Author: Julien Dagnelie
-----
Last Modified: Mon Jan 17 2022
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
import time

bouton1 = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_DOWN) # bouton suivant
bouton2 = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_DOWN) # bouton valider
led_verte = machine.Pin(17, machine.Pin.OUT)
led_rouge = machine.Pin(16, machine.Pin.OUT)

def bonjour():
    """ Message de bienvenue
    """
    led_verte.value(1)
    led_rouge.value(1)
    ECRAN.txt("Bonjour", 0, 0)
    ECRAN.txt("Que voulez-vous faire ?", 1, 1)
    ECRAN.afficher()
    time.sleep(1)
    led_verte.value(0)
    led_rouge.value(0)
def aurevoir():
    """ Message d'aurevoir
    """
    led_verte.value(1)
    led_rouge.value(1)
    ECRAN.txt("Merci de m'avoir utilisé", 0, 0)
    ECRAN.txt("Bye", 1, 1)
    ECRAN.afficher()
    time.sleep(1)
    led_verte.value(0)
    led_rouge.value(0)

def menu1():
    """ Menu 1: encodage chauffeur
    """
    ECRAN.txt("Encoder chauffeur", 1, 1)
    ECRAN.afficher()
def menu2():
    """ Menu 2: encodage passager
    """
    ECRAN.txt("Encoder passagers", 1, 1)
    ECRAN.afficher()
def menu3():
    """ Menu 3: démarrage du voyage
    """
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
                run()                             # Démarer voyage
        if bouton1.value():                     # Changer de menu
            i +=1

aurevoir()