'''
File: ECRAN.py
Project: Code python
Created Date: Su Jan 2022
Author: Julien Dagnelie & Loïc Tumelaire
-----
Last Modified: Wed Feb 23 2022
Modified By: Julien Dagnelie & Loïc Tumelaire
-----
Copyright (c) 2022 Universite catholique de Louvain
-----
HISTORY:
Date   Sun Jan 16 2022   	By Julien Dagnelie & Loïc Tumelaire	Comments
----------	---	---------------------------------------------------------
'''

from machine import Pin, I2C
import ssd1306py

i2c=I2C(1,sda=Pin(26), scl=Pin(27), freq=400000)
oled = ssd1306py.ssd1306.SSD1306_I2C(128, 64, i2c)

def txt(texte, x, y):
    """Crée un texte à afficher sur l'écran.

    Args:
        texte (str): Le texte
        x (int): Coordonnée x
        y (int): Coordonnée y
    """
    oled.text(texte, x, y)

def pixel(x, y):
    """Créée un pixel.

    Args:
        x (int): Coordonnée x
        y (int): Coordonnée y
    """
    oled.pixel(x,y,1)

def afficher():
    """Pour afficher les textes réalisés à l'écran.
    """
    oled.show()

#Images et défilements inutiles?