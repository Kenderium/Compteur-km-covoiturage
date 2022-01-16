'''
File: ECRAN.py
Project: Code python
Created Date: Su Jan 2022
Author: Julien Dagnelie & Loïc Tumelaire
-----
Last Modified: Sun Jan 16 2022
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

ssd1306py.ssd1306.SSD1306_I2C
i2c=I2C(1,sda=Pin(0), scl=Pin(1), freq=400000)