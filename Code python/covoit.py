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
def prix(historique, prix_plein = 70, km_tot = None ):
    """ Retourne le prix de chaque voyageur dans un dico.

    Args:
        historique (fichier texte): De type "km + conducteur + passagers" pour chaque trajet effectué, avec une ligne "plein" lorsque le plein est réalisé.
        km_tot (int, optional): Le nombre de km parcourus par la voiture
        prix_plein (int, optional): Le prix du plein. Defaults to 16.

    Return:
        prix (dico): De type: Nom --> [km, prix]
    """
    
    numéro_ligne = 0
    Start = 0
    historiquev2 = []

    # Trouver où se trouve le dernier plein dans l'historique
    with open(historique) as hist:
        for line in hist:
            if line.strip() == 'Plein':
                Start = numéro_ligne
            numéro_ligne +=1

    # Créer un nouvel historique avec seulement les infos récentes
    with open(historique) as hist:
        historiquev2 = (hist.readlines()[Start+1:])


    # Création d'un dico et du compteur de km totaux
    dico = {}                           # De type: Nom --> [km, prix]
    km_parcourus_tot = 0

    if km_tot == None:
        km_tot = 0
        ajoutkm = True
    else:
        ajoutkm = False

    # Lecture des trajets du plein
    for trajets in historiquev2:         # Commener à partir du start == au mot Plein
        trajet = trajets.split()
        km = int(trajet[0])
        if ajoutkm == True:
            km_tot += km
        conducteur = trajet[1]
        passagers = trajet[2 :]

        # Ajout des km
        if conducteur not in dico:
            dico[conducteur] = km
        else:
            dico[conducteur] += km

        for passager in passagers:
            km_parcourus_tot += km
            if passager not in dico:
                dico[passager] = km
            else:
                dico[passager] += km

    # Ajout des prix
    for personnes in dico:
        km_perso = dico[personnes]
        dico[personnes]  = round((km_perso/(km_tot + km_parcourus_tot))*prix_plein , 2)
    return dico