# Librairie
- math
- machine (micropython)
- time/utime
- MicropyGPS
- ssd1306py


# [GPS](Code%20python/GPS1.py)
- startgps(running)
    - cette fonction permet de demarer les logs du gps pour recuperer les latitudes et longitudes
- distance(lat1, lat2, long1, long2)
    - calcul la distance selon la formule haversine pour savoir les km parcourus lors du trajets

# [Affichage LCD](Code%20python/ECRAN.py)
- txt(texte, x, y)
    - Crée un texte à afficher sur l'écran.
- pixel(x, y)
    - Créée un pixel.
- line(x1, y1, x2, y2):
    - Créee une ligne (diagonale, verticale, horizontale)
- rectangle(x1, y1, x2, y2, fill=False):
    - Créée un rectangle, remplis ou pas
- afficher()
    - Pour afficher les éléments réalisés à l'écran.

# [RFID](Code%20python/RFID1.py)

# [Bluethoot - App](Code%20python/Bluetooth.py)

# Partie mathematique

# Fonctionnement du boitier :

### <ins> Avant de demarrer</ins> :
1. Scanner la carte, -> RFID init 
2. Commencer le tracking GPS 
3. Afficher a l'ecran les km sur la carte de chaque personne

### <ins>Fin du trajet</ins> :
1. Re-scanner la carte, -> RFID 
2. Stopper le tracking, enregistrer les km + ajouter les km a chacun 
3. Afficher a l'ecran les km de tout le monde
4. Effectuez un pre calcul pour avoir une idee du solde ??

### <ins> Lors du plein</ins> :
1. Scanner la carte du conducteur
2. Entrez le prix du plein, consomation moyenne 
3. Effectuez le calcul 
4. Afficher quel passager doit payer combien 