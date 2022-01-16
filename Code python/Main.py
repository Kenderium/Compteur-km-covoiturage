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


run()