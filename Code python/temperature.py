'''
File: Temperature.py
Project: Code python
Created Date: Fr Aug 2022
Author: Julien Dagnelie & Loïc Tumelaire
-----
Last Modified: Fri Aug 26 2022
Modified By: Julien Dagnelie & Loïc Tumelaire
-----
Copyright (c) 2022 Universite catholique de Louvain
-----
HISTORY:
Date   Fri Aug 26 2022   	By Julien Dagnelie & Loïc Tumelaire	Comments
----------	---	---------------------------------------------------------
'''

import machine, time, ECRAN, math

thermometre = machine.ADC(4)
conversion = 3.3 / (65535)
temperatures = [0.0,0.0,0.0]

def temperature_actuelle():
    valeur = thermometre.read_u16() * conversion
    return 27 - (valeur - 0.706) / 0.001721

def futur():
    valeur = (temperatures[-1] + temperatures[-2] + temperatures[-3])/3
    if math.fabs( temperature - valeur) <= 0.1:
        return "Constant"
    elif temperature > valeur:
        return "Augmente"
    else:
        return "Diminue"

def continu():
    global temperature
    while True:
        valeur = thermometre.read_u16() * conversion
        temperature = 27 - (valeur - 0.706) / 0.001721
        #print("Température: {}" .format(temperature))
        temperatures.append(temperature)
        ECRAN.clean()
        ECRAN.txt("Temperature :",0,0)
        ECRAN.txt(str(temperature) + " C",0,10)
        ECRAN.txt(futur(),0,20)
        ECRAN.afficher()

        time.sleep(20)

#continu()