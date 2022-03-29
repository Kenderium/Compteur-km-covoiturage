'''
File: covoit.py
Project: Code python
Created Date: Su Jan 2022
Author: Julien Dagnelie
-----
Last Modified: Mon Mar 28 2022
Modified By: Julien Dagnelie & Loïc Tumelaire
-----
Copyright (c) 2022 Universite catholique de Louvain
-----
HISTORY:
Date   Sun Jan 16 2022   	By Julien Dagnelie	Comments
----------	---	---------------------------------------------------------
'''
def prix(historique, prix_plein= 70 ):
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
    historiquev2 = []
    with open(historique) as hist:
        for line in hist:
            if line.strip() == 'Plein':
                Start = numéro_ligne
            numéro_ligne +=1

    with open(historique) as hist:
        historiquev2 = (hist.readlines()[Start+1:])


    # Création d'un dico et du compteur de km totaux
    dico = {}                           # De type: Nom --> [km, prix]
    km_tot = 0
    
    # Lecture des trajets du plein
    for trajets in historiquev2:         # Commener à partir du start == au mot Plein
        trajet = trajets.split()
        km = int(trajet[0])
        km_tot += km
        conducteur = trajet[1]
        passagers = trajet[2 :]

        # Ajout des km
        if conducteur not in dico:
            dico[conducteur] = km
        else:
            dico[conducteur] += km

        for passager in passagers:
            if passager not in dico:
                dico[passager] = km
            else:
                dico[passager] += km

    # Ajout des prix
    for personnes in dico:
        dico[personnes]  += (dico[personnes]/km_tot)*prix_plein
    return dico



print(prix('historique.txt', 15))