# Firmware du boîtier (Raspberry Pi Pico W, MicroPython)

## Installation

1. Installer MicroPython pour **Pico W** : maintenir BOOTSEL en branchant le
   Pico W, puis copier le fichier `RPI_PICO_W-*.uf2` de micropython.org.
2. Dans l'app, onglet **Voitures > Ajouter** : l'app affiche l'identifiant, le
   jeton et le code Bluetooth du boîtier.
3. `cp firmware/config_example.py firmware/config.py`, puis y coller ces valeurs,
   l'adresse du serveur et vos réseaux WiFi.
4. `pip install mpremote` puis `firmware/tools/deploy.sh` (boîtier branché en USB).

Mettre à jour le firmware plus tard : relancer `deploy.sh`. Les trajets déjà
enregistrés (`journal.jsonl`) restent sur le boîtier.

## Utilisation

Deux boutons : **SUIVANT** (menu suivant / annuler) et **OK** (valider).

- **Nouveau trajet** : badge du conducteur, puis badges des passagers, OK pour
  partir. L'écran affiche les km en direct. OK à l'arrivée, puis OK pour
  confirmer. Si le courant est coupé en route, le boîtier propose de reprendre
  le trajet au redémarrage.
- **Historique** : derniers trajets (SUIVANT pour défiler).
- **Synchro WiFi** : envoie les trajets tout de suite. Sinon le boîtier le fait
  seul toutes les 5 minutes quand il voit un WiFi connu et n'est pas en trajet.
- **Scanner badge** : affiche le numéro d'un badge, pour l'associer à une
  personne depuis l'app (onglet Boîtier).
- **Etat** : trajets en attente, satellites GPS, Bluetooth, heure.

Les frais ne se calculent plus sur le boîtier : les pleins se saisissent dans
l'app et les soldes sont calculés par le serveur.

## Organisation

```
main.py              démarrage
config_example.py    modèle de configuration (config.py n'est pas versionné)
carpox/app.py        écrans et boucle principale (non bloquante)
carpox/gps.py        lecture du GPS sur l'UART
carpox/trip.py       trajet en cours, km via carpox_core.geo
carpox/journal.py    trajets numérotés, stockés en JSON lines
carpox/wifi.py       synchro WiFi
carpox/ble.py        Bluetooth BLE (service Nordic UART)
carpox/protocol.py   commandes Bluetooth (AUTH, STATUS, EVENTS, APPLY, BADGE, LASTSCAN)
carpox/sync.py       protocole de synchro commun au WiFi et au Bluetooth
lib/                 pilotes GPS (micropyGPS), RFID (mfrc522), écran (ssd1306)
tests/               tests sous CPython, avec une simulation du matériel
```

`deploy.sh` copie aussi `core/carpox_core/geo.py` (calcul des distances).

## Sécurité

- Le jeton du boîtier ne sert qu'à envoyer ses trajets. S'il est perdu,
  régénérez-le dans l'app (onglet Membres) et mettez à jour `config.py`.
- Le Bluetooth demande le code à 6 chiffres de la voiture ; après 5 codes faux
  il faut se reconnecter. La liaison BLE n'est pas chiffrée : elle ne transporte
  que des trajets et des noms de badges, jamais de mot de passe.
- Utilisez une adresse `https://` pour le serveur.
