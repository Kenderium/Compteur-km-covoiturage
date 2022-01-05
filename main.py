from machine import Pin
import time

pin = Pin(0, Pin.OUT)

# while True:
#     pin.toggle()
#     time.sleep_ms(1000)

run  = True 
while run:
    x = int(input("Entre 0/1/2pour allumer, eteindre la lampe ou stopper le systeme:"))
    if x == 1:
        print("J'allume la led")
        pin.value(x)
    elif x == 0:
        print("J'eteint la led")
        time.sleep(1)
        pin.value(x)
    elif x == 2:
        print("Eteignons la led et arretons.")
        time.sleep(5)
        pin.value(0)
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