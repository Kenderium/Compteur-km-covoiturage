'''
File: main.py
Project: Compteur-km-covoiturage
Created Date: Sa Jan 2022
Author: Julien Dagnelie
-----
Last Modified: Sun Jan 16 2022
Modified By: Julien Dagnelie
-----
Copyright (c) 2022 Universite catholique de Louvain
-----
HISTORY:
Date   Sun Jan 16 2022   	By Julien Dagnelie	Comments
----------	---	---------------------------------------------------------
'''

from machine import Pin, Timer
import time

#Setup
led = Pin(0, Pin.OUT)
button = Pin(2, Pin.IN, Pin.PULL_DOWN)

#Bouton pendant 5 fois
i=0
while i<6:
    if button.value():
        led.toggle()
        time.sleep(0.5)
        i += 1
        print("oki")

#Allumer-Eteindre led sur commandes
run  = True 
while run:
    x = int(input("Entre 0/1/2pour allumer, eteindre la lampe ou stopper le systeme:"))
    if x == 1:
        print("J'allume la led")
        led.value(x)
    elif x == 0:
        print("J'eteint la led")
        time.sleep(1)
        led.value(x)
    elif x == 2:
        print("Eteignons la led et arretons.")
        time.sleep(5)
        led.value(0)
        run = False 

led = Pin(15, Pin.OUT)
button = Pin(14, Pin.IN, Pin.PULL_DOWN)

while True:
    if button.value():
        led.toggle()
        time.sleep(0.5)
