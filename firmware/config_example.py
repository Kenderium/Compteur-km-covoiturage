"""Configuration du boîtier. Copiez ce fichier en `config.py` et adaptez-le.

`config.py` n'est pas versionné (il contient vos mots de passe WiFi).
"""

# Identifiant et jeton du boîtier : donnés par l'app quand vous ajoutez la
# voiture (menu « Voitures > Ajouter »). Le jeton n'est affiché qu'une fois.
DEVICE_ID = "box-a-remplacer"
DEVICE_TOKEN = "jeton-a-remplacer"

# Code à 6 chiffres demandé par l'app pour se connecter en Bluetooth.
BLE_PIN = "000000"
BLE_NAME = "CarpoX"

# Serveur (HTTPS recommandé). Exemple : "https://carpox.mondomaine.be"
SERVER_URL = "https://carpox.example.org"

# Réseaux WiFi connus : le boîtier se synchronise quand il en voit un.
WIFI_NETWORKS = [
    ("MaBox-Maison", "mot-de-passe"),
    # ("PartageTelephone", "mot-de-passe"),
]

# Tentative de synchro automatique toutes les N secondes quand aucun trajet
# n'est en cours.
SYNC_INTERVAL_S = 300

# Le boîtier compte les km dès qu'il est allumé, même sans badge. Après N
# secondes à l'arrêt, les km roulés hors trajet sont écrits au journal.
DRIVE_IDLE_S = 180

# Brochage (voir hardware/README.md).
PIN_BUTTON_NEXT = 14
PIN_BUTTON_OK = 15
PIN_LED_GREEN = 17
PIN_LED_RED = 16
OLED_I2C = 1
OLED_SDA = 26
OLED_SCL = 27
RFID = {"spi_id": 0, "sck": 2, "miso": 4, "mosi": 3, "cs": 6, "rst": 5}
GPS_UART = 1
GPS_TX = 8
GPS_RX = 9
