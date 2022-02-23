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
#ssd1306py.ssd1306.SSD1306_I2C

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

def afficher():
    """Pour afficher les textes réalisés à l'écran.
    """
    oled.show()

def pixel(x, y):
    """Créée un pixel.

    Args:
        x (int): Coordonnée x
        y (int): Coordonnée y
    """
    oled.pixel(x,y,1)

def line(x1, y1, x2, y2):
    """Créee une ligne (diagonale, verticale, horizontale)

    Args:
        x1 (int): Coordonnée x début
        y1 (int): Coordonnée y début
        x2 (int): Coordonnée x fin
        y2 (int): Coordonnée y fin
    """
    oled.line(x1,y1,x2,y2,1)
    pass

def rectangle(x1, y1, x2, y2, fill=False):
    """Créée un rectangle, remplis ou pas

    Args:
        x1 (int): Coordonnée x début
        y1 (int): Coordonnée y début
        x2 (int): Coordonnée x fin
        y2 (int): Coordonnée y fin
        fill (bool, optional): Remplir le rectangle. Defaults to False.
    """
    oled.rect(x1, y1, x2, y2, 1)
    pass
    if fill == True:
        oled.fill_rect(x1, y1, x2, y2, 1)
        pass

#Images et défilements inutiles?