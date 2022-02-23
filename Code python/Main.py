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
#import GPS1
import ECRAN
import RFID1
import covoit

#  Creation des boutons, led indicatrices
bouton1 = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_DOWN) # bouton suivant
bouton2 = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_DOWN) # bouton valider
led_verte = machine.Pin(17, machine.Pin.OUT)
led_rouge = machine.Pin(16, machine.Pin.OUT)

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

def menu4():
    """ Menu 4: historique
    """
    ECRAN.txt("Historique", 1, 1)
    ECRAN.afficher()

def menu5():
    """ Menu 5: Bluetooth / Plein
    """
    ECRAN.txt("Bluetooth", 1, 1)
    ECRAN.afficher()

def menu_exit():
    """ Menu_exit: exit
    """
    ECRAN.txt("Exit ?", 1, 1)
    ECRAN.afficher()

def run():
    """Lance toute l'artillerie lourde
    """
    km = GPS1.run()
    
    with open("historique_trajets.txt") as historique:
        historique.append("Trajet numéro {} ".format(trajet_numero) + "\n" + "km = {}".format(km) + "\t" +"Conducteur : " + Conducteur + "\t" + "Passagers : {}".format(Passagers))
    

Run = True
if __name__ == "main":
    while (Run):
        print("start")
        if bouton1.value():                             # Allumage
            bonjour()                                   # Message de bienvenue

            while True:
                i = 1
                if i == 1:                              # Encoder conducteur

                    menu1()
                    if bouton2.value():                 # Confirmation
                        led_verte.value(1)
                        time.sleep(0.5)
                        led_verte.value(0)
                        Conducteur = RFID.lecture()     # Encodage conducteur

                if i == 2:                              # Encoder passagers
                    menu2()
                    if bouton2.value():                 # Confirmation
                        led_verte.value(1)
                        time.sleep(0.5)
                        led_verte.value(0)
                        while not bouton2.value():      # Encodage Passager
                            Passagers.append(RFID.lecture())
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
                        prix = covoit.prix(km, Passagers)
                        pass

                if i == 6:                              # Menu exit
                    menu_exit()
                    if bouton2.value():                 # Confirmation
                        led_rouge.value(1)
                        time.sleep(0.5)
                        led_rouge.value(0)
                        aurevoir()
                        Run = False

                if bouton1.value():                     # Changer de menu
                    if i == 6:
                        i = 1
                    else:
                        i += 1
             
'''           
    Menu Bluethoot:
    km total ?
    prix du plein
    recevoir historique
    stats?
'''