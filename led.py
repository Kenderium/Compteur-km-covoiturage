from machine import Pin
import time

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
