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

reader = MFRC522(spi_id=0,sck=2,miso=4,mosi=3,cs=6,rst=5)  #spi_id =?