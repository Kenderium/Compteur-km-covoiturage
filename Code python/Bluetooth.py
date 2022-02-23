'''
File: Bluetooth.py
Project: Code python
Created Date: Su Jan 2022
Author: Julien Dagnelie & Loïc Tumelaire
-----
Last Modified: Sat Feb 19 2022
Modified By: Julien Dagnelie & Loïc Tumelaire
-----
Copyright (c) 2022 Universite catholique de Louvain
-----
HISTORY:
Date   Sun Jan 16 2022   	By Julien Dagnelie & Loïc Tumelaire	Comments
----------	---	---------------------------------------------------------
'''

'''
Envoi d'un message via bluetooth par un HC-05 branché à un Raspberry Pi Pico
Pour plus d'infos:
https://electroniqueamateur.blogspot.com/2021/05/module-bluetooth-hc-06-et-raspberry-pi.html
'''


import machine
from utime import sleep

BT= machine.UART(0,baudrate=9600)  # initialisation UART

compteur = 0

while(True):
    BT.write(str(compteur)+'\n')
    compteur += 1
    sleep(1)

'''
Réception d'un message bluetooth par un HC-06
branché au Raspberry Pi Pico.
Pour plus d'infos:
https://electroniqueamateur.blogspot.com/2021/05/module-bluetooth-hc-06-et-raspberry-pi.html
'''

import machine

BT= machine.UART(0,baudrate=9600)

# broche 25 définie en sortie
led_embarquee = machine.Pin(25, machine.Pin.OUT)

while(True):
    if BT.any():
        message = BT.readline().decode('utf-8')
        print(message)
        if (message[0]=='a'):
            led_embarquee.value(1) # on allume
        if (message[0]=='b'):
            led_embarquee.value(0) # on éteint