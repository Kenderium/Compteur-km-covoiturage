'''
File: Main.py
Project: Code python
Created Date: Su Jan 2022
Author: Julien Dagnelie
-----
Last Modified: Sun Sep 11 2022
Modified By: Julien Dagnelie & Loïc Tumelaire
-----
Copyright (c) 2022 Universite catholique de Louvain
-----
HISTORY:
Date   Sun Jan 16 2022   	By Julien Dagnelie	Comments
----------	---	---------------------------------------------------------
'''

# from ast import Import             WTF, c quoi ce truc ptdrrr
import machine
import time
import ECRAN
import RFID1
import Bluetooth
import covoit
# import GPS1
import temperature

# -------------------------------------------
# Creation des boutons, led indicatrices ----
# -------------------------------------------

print("Run")

bouton1 = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_DOWN)  # bouton suivant
bouton2 = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_DOWN)  # bouton valider
led_verte = machine.Pin(17, machine.Pin.OUT)
led_rouge = machine.Pin(16, machine.Pin.OUT)

# --------------------------
# Gestion des passagers ----
# --------------------------

Conducteur = None
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
    Conducteur = None
    Passagers = []
    on = False


def menu1():
    """ Menu 1: encodage chauffeur
    """
    ECRAN.clean()
    ECRAN.txt("Encoder", 0, 0)
    ECRAN.txt("chauffeur ?", 0, 10)
    ECRAN.afficher()


def menu2():
    """ Menu 2: encodage passager
    """
    ECRAN.clean()
    ECRAN.txt("Encoder", 0, 0)
    ECRAN.txt("passagers ?", 0, 10)
    ECRAN.afficher()


def menu3():
    """ Menu 3: démarrage du voyage
    """
    ECRAN.clean()
    ECRAN.txt("Demarrer", 0, 0)
    ECRAN.txt("le voyage ?", 0, 10)
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
    # Calcule les km avec le gps, ici on met 30 et on les ajoute à chaque passagers
    km = 30
    # km = GPS1.main()?
    # date = GPS1.date()
    tempera = temperature.temperature_actuelle()
    with open("historique_trajets.txt", "a") as historique:  # Enregistrer le trajet (km + conducteur + passagers)
        trajets = historique.readlines()
        if trajets == []:
            historique.write(str(km) + " " + str(Conducteur) + " " + str(Passagers) + " " + str(tempera))
        else:
            historique.write("\n" + str(km) + " " + str(Conducteur) + " " + str(Passagers) + " " + str(tempera))
    ECRAN.clean()
    ECRAN.txt("Km parcourus :", 0, 0)
    ECRAN.txt(str(km), 0, 10)
    ECRAN.afficher()
    time.sleep(1)


def stats():
    """Affiche un graph des km parcourus par pers
    """


while True:
    if bouton1.value():  # Allumage
        bonjour()  # Message de bienvenue
        on = True
        i = 1
        while on:

            if i == 1:  # Encoder conducteur
                menu1()
                if bouton2.value():  # Confirmation
                    led_verte.value(1)
                    time.sleep(0.5)
                    led_verte.value(0)
                    ECRAN.clean()
                    ECRAN.txt("Encodez :", 0, 0)
                    ECRAN.afficher()
                    while Conducteur == None:
                        Conducteur = RFID1.name(RFID1.lecture())  # Encodage conducteur
                    led_rouge.value(1)
                    ECRAN.clean()
                    ECRAN.txt("Hello", 0, 0)
                    ECRAN.txt(Conducteur + " !", 0, 10)
                    ECRAN.afficher()
                    time.sleep(1)
                    led_rouge.value(0)
                    i += 1

            if i == 2:  # Encoder passagers
                menu2()
                if bouton2.value():  # Confirmation
                    led_verte.value(1)
                    time.sleep(0.5)
                    led_verte.value(0)
                    while not bouton2.value():  # Encodage Passager
                        ECRAN.clean()
                        ECRAN.txt("Encodez :", 0, 0)
                        ECRAN.afficher()
                        passager = RFID1.name(RFID1.lecture())
                        if passager not in Passagers and passager != None:
                            Passagers.append(passager)
                            led_rouge.value(1)
                            ECRAN.clean()
                            ECRAN.txt("Hello", 0, 0)
                            ECRAN.txt(passager + " !", 0, 10)
                            ECRAN.afficher()
                            time.sleep(1)
                            led_rouge.value(0)
                            ECRAN.clean()
                            ECRAN.txt("Autre passager ?", 0, 0)
                            ECRAN.afficher()
                            time.sleep(1)
                        time.sleep(0.5)
                    time.sleep(0.5)
                    i += 1

            if i == 3:  # Démarer voyage
                menu3()
                if bouton2.value():  # Confirmation
                    led_rouge.value(1)
                    time.sleep(0.5)
                    led_rouge.value(0)
                    run()  # Démarage voyage
                    i += 1

            if i == 4:
                menu4()  # Historique
                if bouton2.value():  # Confirmation
                    led_verte.value(1)
                    time.sleep(0.5)
                    led_verte.value(0)

                    with open("historique_trajets.txt") as historique:
                        trajets = historique.readlines()
                        # Prendre après le dernier plein
                        trajets.reverse()
                        if 'Plein\n' in trajets:
                            position = len(trajets) - (trajets.index('Plein\n') + 1)
                        else:
                            position = 0
                        trajets.reverse()
                        trajets = trajets[position + 1:]
                    l = 0

                    while not bouton2.value() and l < len(trajets):
                        ECRAN.clean()
                        ECRAN.txt(str(trajets[l][0:14]), 0, 0)
                        ECRAN.txt(str(trajets[l][15:29]), 0, 10)
                        ECRAN.txt(str(trajets[l][30:44]), 0, 20)
                        ECRAN.txt(str(trajets[l][45:59]), 0, 30)
                        ECRAN.afficher()
                        time.sleep(0.1)
                        if bouton1.value():
                            l += 1
                    time.sleep(0.5)
                    i += 1

            if i == 5:
                menu5()  # Bluetooth / plein
                if bouton2.value():  # Confirmation
                    led_verte.value(1)
                    time.sleep(0.5)
                    led_verte.value(0)

                    # Demande connection
                    while not bouton2.value() and Bluetooth.statut() != 1:
                        ECRAN.clean()
                        ECRAN.txt(" Connectez-", 0, 0)
                        ECRAN.txt(" vous", 0, 10)
                        ECRAN.txt(" en bluetooth", 0, 20)
                        ECRAN.afficher()
                        time.sleep(0.1)
                    ECRAN.clean()
                    ECRAN.txt("Connecte !", 0, 0)
                    ECRAN.afficher()
                    time.sleep(1)

                    # Plein
                    ECRAN.clean()
                    ECRAN.txt("Voir bluetooth", 0, 0)
                    ECRAN.afficher()

                    Bluetooth.envoi("Quel est le prix du plein (en euros)?")
                    print("demande rpix")
                    prix_plein = int(Bluetooth.reception())
                    print("ok")
                    Bluetooth.envoi(covoit.prix("historique_trajets.txt", prix_plein))

                    # Rajoute Plein à la fin du fichier
                    with open("historique_trajets.txt") as historique:
                        historique.write(str("/n" + "Plein"))
                    i += 1

            if i == 6:
                menu6()  # Scan de la carte
                if bouton2.value():  # Confirmation

                    led_verte.value(1)
                    time.sleep(0.5)
                    led_verte.value(0)
                    while not bouton2.value():
                        scan = RFID1.lecture()
                        nom = RFID1.name(scan)
                        if scan == None:
                            ECRAN.clean()
                            ECRAN.txt("Sannez", 0, 0)
                            ECRAN.afficher()
                        else:
                            ECRAN.clean()
                            ECRAN.txt("Nom :", 0, 0)
                            ECRAN.txt(str(nom), 0, 10)
                            ECRAN.txt("Numero :", 0, 20)
                            ECRAN.txt(str(scan), 0, 30)
                            ECRAN.afficher()
                    led_rouge.value(1)
                    time.sleep(0.5)
                    led_rouge.value(0)
                    i += 1

            if i == 7:  # Menu exit
                menu_exit()
                if bouton2.value():  # Confirmation
                    led_rouge.value(1)
                    time.sleep(0.5)
                    led_rouge.value(0)
                    aurevoir()

            time.sleep(0.1)
            if bouton1.value():  # Changer de menu
                if i == 7:
                    i = 1
                else:
                    i += 1
                time.sleep(0.5)

''' 
    Bluethoot plante
    Bug même conducteur....
    Bouton fin passagers lent
    stats?
    GPS
    Boite
    Historique pas beau
    App (bluethoot, stats, serveur)
'''
