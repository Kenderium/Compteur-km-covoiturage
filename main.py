from machine import Pin
import time

#Setup
led = Pin(0, Pin.OUT)
button = Pin(2, Pin.IN, Pin.PULL_DOWN)

#Bouton pendant 5 fois
i=0
while i<6:
    print("Question?")
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


'''rom machine import Pin
import sys, time
import RPi.GPIO as GPIO

#Led RGB pin(0,1,2 + GND)
redPin = 0
greenPin = 1
bluePin = 2

def blink(pin):
    GPIO.setmode(GPIO.BMC)
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)    

def turnOFF(pin):
    GPIO.setmode(GPIO.BMC)
    GPIO.setup(pin, GPIO.OUT)
    GPIO.setup(pin, GPIO.LOW)

led = Pin(0, Pin.OUT)
led.value(1)
run  = True 
while run:
    x = input("Entre 0/1/2pour allumer, eteindre la lampe ou stopper le système:")
    if x == 0:
        print("J'allume la led")
        time.sleep(1)
        led.value(x)
    elif x == 1:
        print("J'éteint la led")
        time.sleep(1)
        led.value(x)
    elif x == 2:
        print("Eteignons la led de l'arduino")
        time.sleep(5)
        led.value(0)
        run = False 
'''