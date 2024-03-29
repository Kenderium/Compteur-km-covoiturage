'''
File: covoit.py
Project: Code python
Created Date: Su Jan 2022
Author: Julien Dagnelie
-----
Last Modified: Sat Sep 17 2022
Modified By: Julien Dagnelie & Loïc Tumelaire
-----
Copyright (c) 2022 Universite catholique de Louvain
-----
HISTORY:
Date   Sun Jan 16 2022   	By Julien Dagnelie	Comments
----------	---	---------------------------------------------------------
'''


def prix(historique, prix_plein=70, km_tot=None):
    """ Retourne le prix de chaque voyageur dans un dico.

    Args:
        historique (fichier texte): De type "km + conducteur + [ passagers ]" pour chaque trajet effectué, avec une ligne "plein" lorsque le plein est réalisé.
        km_tot (int, optional): Le nombre de km parcourus par la voiture
        prix_plein (int, optional): Le prix du plein. Defaults to 70.

    Return:
        prix (dico): De type: Nom --> [km, prix]
    """
    numéro_ligne = 0
    Start = -1
    historiquev2 = []

    # Si il y a des km supp
    if km_tot == None:
        km_tot = 0
        ajoutkm = True
    else:
        ajoutkm = False
    km_tt = km_tot

    # Trouver où se trouve le dernier plein dans l'historique
    with open(historique) as hist:

        # hist.reverse()
        # Start = len(hist) - (hist.index("Plein") +1)
        # hist.reverse()
        # historiquev2 = hist.readlines()[Start+1:]

        for line in hist:
            if line.strip() == 'Plein':
                Start = numéro_ligne
            numéro_ligne += 1

    # Créer un nouvel historique avec seulement les infos récentes
    with open(historique) as hist:
        historiquev2 = (hist.readlines()[Start + 1:])

    # Création d'un dico et du compteur de km totaux
    dico = {}  # De type: Nom --> [km, prix]
    km_trajets = 0
    km_parcourus_tot = 0

    # Lecture des trajets du plein
    for trajets in historiquev2:  # Commener à partir du start == au mot Plein
        trajet = []
        temp = ""
        # Divise la ligne en liste
        for char in trajets:

            if char == "]":
                trajet.append(temp)
                break
            elif char == " " and temp != "":
                trajet.append(temp)
                temp = ""
            elif char == "," or char == "'" or char == "[":
                pass
            else:
                temp += char

        km = int(trajet[0])
        km_trajets += km

        if ajoutkm: #Is True ?
            km_tot += km
        conducteur = trajet[1]
        passagers = trajet[2:]

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

    if km_trajets < km_tt:  # Si il y a des km supp, les retires dans le plein
        pourcentage = (km_trajets / km_tt)
        prix_plein *= (1 - (1 - pourcentage))

    # Ajout des prix
    for personnes in dico:
        km_perso = dico[personnes]
        dico[personnes] = round((km_perso / (km_tot + km_parcourus_tot)) * prix_plein, 2)
    return dico


print(prix("historique.txt", 84.18, 750))
