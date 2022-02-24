'''
File: Main.py
Project: Code python
Created Date: Su Jan 2022
Author: Julien Dagnelie
-----
Last Modified: Wed Feb 23 2022
Modified By: Julien Dagnelie & Loïc Tumelaire
-----
Copyright (c) 2022 Universite catholique de Louvain
-----
HISTORY:
Date   Sun Jan 16 2022   	By Julien Dagnelie	Comments
----------	---	---------------------------------------------------------
'''

import machine
import time
import ECRAN
import RFID1
#import GPS1
#import covoit

# -------------------------------------------
# Creation des boutons, led indicatrices ----
# -------------------------------------------

bouton1 = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_DOWN) # bouton suivant
bouton2 = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_DOWN) # bouton valider
led_verte = machine.Pin(17, machine.Pin.OUT)
led_rouge = machine.Pin(16, machine.Pin.OUT)

# --------------------------
# Gestion des passagers ----
# --------------------------

Conducteur = ""
Passagers = []
trajet_numero = 0

# ------------------------------
# Fonctions menus, et run ------
# ------------------------------

def bonjour():
    """ Message de bienvenue
    """
    led_verte.value(1)
    led_rouge.value(1)
    ECRAN.clean()
    ECRAN.txt("Bonjour", 0, 0)
    ECRAN.txt("Que voulez-vous", 0, 10)
    ECRAN.txt("faire ?", 0, 20)
    ECRAN.afficher()
    time.sleep(2)
    led_verte.value(0)
    led_rouge.value(0)

def aurevoir():
    global on
    """ Message d'aurevoir
    """
    led_verte.value(1)
    led_rouge.value(1)
    ECRAN.clean()
    ECRAN.txt("Merci de m'avoir", 0, 0)
    ECRAN.txt("utilise", 0, 10)
    ECRAN.txt("Bye", 0, 20)
    ECRAN.afficher()
    time.sleep(1)
    ECRAN.clean()
    ECRAN.afficher()
    led_verte.value(0)
    led_rouge.value(0)
    on = False


def menu1():
    """ Menu 1: encodage chauffeur
    """
    ECRAN.clean()
    ECRAN.txt("Encoder", 0, 0)
    ECRAN.txt("chauffeur", 0, 10)
    ECRAN.afficher()

def menu2():
    """ Menu 2: encodage passager
    """
    ECRAN.clean()
    ECRAN.txt("Encoder", 0, 0)
    ECRAN.txt("passagers", 0, 10)
    ECRAN.afficher()

def menu3():
    """ Menu 3: démarrage du voyage
    """
    ECRAN.clean()
    ECRAN.txt("Demarrer", 0, 0)
    ECRAN.txt("le voyage", 0, 10)
    ECRAN.afficher()

def menu4():
    """ Menu 4: historique
    """
    ECRAN.clean()
    ECRAN.txt("Historique", 0, 0)
    ECRAN.afficher()

def menu5():
    """ Menu 5: Bluetooth / Plein
    """
    ECRAN.clean()
    ECRAN.txt("Bluetooth", 0, 0)
    ECRAN.afficher()

def menu6():
    """ Menu 6: Scan de carte
    """
    ECRAN.clean()
    ECRAN.txt("Scan de", 0, 0)
    ECRAN.txt("la carte", 0, 10)
    ECRAN.afficher()

def menu_exit():
    """ Menu_exit: exit
    """
    ECRAN.clean()
    ECRAN.txt("Exit ?", 0, 0)
    ECRAN.afficher()

def run():
    """Lance toute l'artillerie lourde
    """
    km = 60
    #with open("historique_trajets.txt") as historique:             #Enregistrer le trajet (km + conducteur + passagers)
    #    historique.append("Trajet numéro {} ".format(trajet_numero) + "\n" + "km = {}".format(km) + "\t" +"Conducteur : " + Conducteur + "\t" + "Passagers : {}".format(Passagers))   

print("start")
while True:
    if bouton1.value():                             # Allumage
        bonjour()                                   # Message de bienvenue
        on = True
        i = 1
        while on:

            if i == 1:                              # Encoder conducteur
                menu1()
                if bouton2.value():                 # Confirmation
                    led_verte.value(1)
                    time.sleep(0.5)
                    led_verte.value(0)
                    Conducteur = RFID1.lecture()     # Encodage conducteur

            if i == 2:                              # Encoder passagers
                menu2()
                if bouton2.value():                 # Confirmation
                    led_verte.value(1)
                    time.sleep(0.5)
                    led_verte.value(0)
                    while not bouton2.value():      # Encodage Passager
                        Passagers.append(RFID1.lecture())
                        led_rouge.value(1)
                        time.sleep(0.5)
                        led_rouge.value(0)

            if i == 3:                              # Démarer voyage
                menu3()
                if bouton2.value():                 # Confirmation
                    led_rouge.value(1)
                    time.sleep(0.5)
                    led_rouge.value(0)
                    run()                           # Démarage voyage

            if i == 4:
                menu4()                             # Historique
                if bouton2.value():                 # Confirmation
                    led_verte.value(1)
                    time.sleep(0.5)
                    led_verte.value(0)
                    with open("historique_trajets.txt") as historique:
                        i=0
                        while not bouton2.value():
                            if bouton1.value():
                                i +=1
                            try:
                                ECRAN.txt(historique[i], 1, 1)
                                ECRAN.afficher()
                            except IndexError:
                                break

            if i == 5:
                menu5()                             # Bluetooth / plein
                if bouton2.value():                 # Confirmation
                    led_verte.value(1)
                    time.sleep(0.5)
                    led_verte.value(0)
                    pass
                    #prix = covoit.prix(km, Passagers)

            if i == 6:
                menu6()                             # Scan de la carte
                if bouton2.value():                 # Confirmation
                    ECRAN.clean()
                    ECRAN.txt("Sannez", 0,0)
                    ECRAN.afficher()
                    led_verte.value(1)
                    time.sleep(0.5)
                    led_verte.value(0)
                    sc = True
                    while sc:                       # Fonctionne pas avec "while not bouton2.value():"
                        scan = RFID1.lecture()
                        ECRAN.clean()
                        ECRAN.txt(scan, 0,0)
                        ECRAN.afficher()
                        time.sleep(3)
                        if bouton2.value():
                            sc = False
                    led_rouge.value(1)
                    time.sleep(0.5)
                    led_rouge.value(0)

            if i == 7:                              # Menu exit
                menu_exit()
                if bouton2.value():                 # Confirmation
                    led_rouge.value(1)
                    time.sleep(0.5)
                    led_rouge.value(0)
                    aurevoir()
                    

            if bouton1.value():                     # Changer de menu
                if i == 7:
                    i = 1
                else:
                    i += 1
                time.sleep(1)
            
'''           
    Menu Bluethoot:
    km total ?
    prix du plein
    recevoir historique
    stats?

    GPS
    Boite
    RFID
    Messages
'''