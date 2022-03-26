'''
File: covoit.py
Project: Code python
Created Date: Su Jan 2022
Author: Julien Dagnelie
-----
Last Modified: Wed Mar 02 2022
Modified By: Julien Dagnelie & Loïc Tumelaire
-----
Copyright (c) 2022 Universite catholique de Louvain
-----
HISTORY:
Date   Sun Jan 16 2022   	By Julien Dagnelie	Comments
----------	---	---------------------------------------------------------
'''
def prix(historique, prix_plein= 16 ):
    """ Retourne le prix de chaque voyageur dans un dico.

    Args:
        historique (fichier texte): De type "km + conducteur + passagers" pour chaque trajet effectué, avec une ligne "plein" lorsque le plein est réalisé.
        prix_plein (int, optional): Le prix du plein. Defaults to 16.

    Return:
        prix (dico): De type: Nom --> [km, prix]
    """
    #with open("historique_trajets.txt") as historique:   #Enregistrer le trajet (km + conducteur + passagers)

    # Trouver où se trouve le dernier plein dans l'historique
    numéro_ligne = 0
    Start = 0
    for lines in historique:
        if lines == "Plein":
            Start = numéro_ligne
        numéro_ligne += 1

    # Création d'un dico et du compteur de km totaux
    dico = {}                           # De type: Nom --> [km, prix]
    km_tot = 0

    # Lecture des trajets du plein
    for trajets in historique[Start +1 :]:         # Commener à partir du start == au mot Plein
        trajet = trajets.split()
        km = trajet[0]
        km_tot += km
        conducteur = trajet[1]
        passagers = trajet[2 :]

        # Ajout des km
        dico[conducteur][0] += km

        for passager in passagers:
            dico[passager][0] += km

    # Ajout des prix
    for passager in dico:
        dico[passager][1]  = (dico[passager][0]/km_tot)*prix_plein
    return dico