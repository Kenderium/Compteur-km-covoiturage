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

def run():
    """Lance toute l'artillerie lourde
    """
    pass

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

if bouton1:
    bonjour()                       # Message de bienvenue
    if bouton1:                     # Choix du menu
        i=0
        if i != 3:
            i+=1
        else:
            i = 1
        menu = str("menu" + str(i))
        #menu()

run()