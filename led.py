from machine import Pin
import time

led = Pin(0, Pin.OUT)
led.value(1)
for i in range(3):
    x = int(input("Entre 0/1 pour allumer ou eteindre la lampe:"))
    if x ==0:
        print("J'éteint la led")
        time.sleep(1)
        led.value(x)
    if x == 1:
        print("J'allume la led")
        time.sleep(1)
        led.value(x)
