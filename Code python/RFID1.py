'''
File: RFID.py
Project: Code python
Created Date: Su Jan 2022
Author: Julien Dagnelie
-----
Last Modified: Mon Jan 17 2022
Modified By: Julien Dagnelie & Loïc Tumelaire
-----
Copyright (c) 2022 Universite catholique de Louvain
-----
HISTORY:
Date   Sun Jan 16 2022   	By Julien Dagnelie	Comments
----------	---	---------------------------------------------------------
'''
from mfrc522 import MFRC522

reader = MFRC522(spi_id=0,sck=2,miso=4,mosi=3,cs=6,rst=5)       # spi_id =?

def lecture():
    """ Lire le numéro de la carte
    """
    #while True:
    reader.init()                                           # Start the connection to the RFID reader
    (stat, tag_type) = reader.request(reader.REQIDL)        # Request the current status of the reader. Nani ?
    if stat == reader.OK:                                   # Checks the value stored in stat, if the reader is ok, the code moves forward.
        (stat, uid) = reader.SelectTagSN()
        card = int.from_bytes(bytes(uid), "little", False)  # Card store the data from an RFID card / tag
        return(card)                                        # Print the card details to the Python shell
        #if card == 611994825:                              # Si la carte est le numéro ...
            #print("Hello user1")

def name(card):
    """Retourne ne nom du propriétaire de la carte

    Args:
        card (int): Numéro de la carte
    Returns:
        str: nom du propriétaire
    """
    if card == 0:
        return "Rescannez"
    elif card == 707308629:
        return "Lucas"
    elif card == 401531548:
        return "Julien"
    elif card == 852861376:
        return "Eduardo"
    elif card == 54835169:
        return "Loic"

    else:
        return "Inconnu"

#Source:
#https://www.tomshardware.com/how-to/raspberry-pi-pico-powered-rfid-lighting
#https://github.com/danjperron/micropython-mfrc522