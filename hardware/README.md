# Matériel

| Élément | Rôle | Branchement sur le Pico W |
|---|---|---|
| Raspberry Pi **Pico W** | cerveau, WiFi et Bluetooth intégrés | |
| GPS NEO-6M | mesure des km | UART1 : TX du GPS → GP9, RX du GPS → GP8, 3V3, GND |
| Lecteur RFID RC522 | badges conducteur / passagers | SPI0 : SCK GP2, MOSI GP3, MISO GP4, CS GP6, RST GP5, 3V3, GND |
| Écran OLED SSD1306 128×64 (I2C) | affichage | I2C1 : SDA GP26, SCL GP27, 3V3, GND |
| Bouton « suivant » | menu suivant / annuler | GP14 ↔ 3V3 (pull-down interne) |
| Bouton « OK » | valider | GP15 ↔ 3V3 (pull-down interne) |
| LED verte / rouge | retours visuels | GP17 / GP16 via résistance ~220 Ω |

Les broches se changent dans `firmware/config.py`.

## Passage du Pico au Pico W

Le Pico W a le même brochage que le Pico : tout se rebranche à l'identique.

- **Le module Bluetooth HC-05/HC-06 n'est plus nécessaire** : le Pico W a le
  Bluetooth (BLE) intégré, utilisé directement par l'app. Les broches GP0/GP1 et
  GP13 (état du HC-05) sont libérées.
- Le module WiFi ESP8266 prévu en bonus n'est plus nécessaire non plus.
- Installer MicroPython **pour Pico W** (fichier `RPI_PICO_W-*.uf2` sur
  micropython.org), pas celui du Pico simple.

## Conseil pour le GPS

Le NEO-6M a besoin de voir le ciel : sans antenne près du pare-brise il peut
mettre plusieurs minutes à trouver sa position (l'écran « Etat » affiche le
nombre de satellites). Sa LED clignote une fois par seconde quand il a un fix.

## Fichiers

- `fritzing/` : schémas de câblage V1 et V2 (V2 = avec HC-06, à mettre à jour
  pour le Pico W)
- `boitier-3d/` : boîtier FreeCAD
- `materiel.md` : liens d'achat d'origine
