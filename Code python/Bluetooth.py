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

BT= machine.UART(0,baudrate=9600)       # Pin 0, 1 fonctionne pas ?

def reception(run):
    """Pour recevoir un message en blutooth

    Args:
        run (bool): Statut (on/off)

    Returns:
        str: message reçu
    """
    message = ""
    while(run):
        if BT.any():
            message = BT.readline().decode('utf-8')
            run = False                                 # Juste 1 carractère...
    return message

def envoi(message):
    """Pour envoyer un message en bluetooth

    Args:
        message (str): Le message
    """
    BT.write(str(message))

envoi("yo")
print(reception(True))