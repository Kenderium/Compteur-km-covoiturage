"""Accès au matériel : boutons, LED, écran OLED, capteur de température."""

import time

import machine
from ssd1306 import SSD1306_I2C

import config


class Button:
    """Bouton avec anti-rebond : `pressed()` renvoie True une fois par appui."""

    def __init__(self, pin):
        self.pin = machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_DOWN)
        self._was_down = False
        self._changed_ms = 0

    def pressed(self):
        down = self.pin.value() == 1
        now = time.ticks_ms()
        if down != self._was_down and time.ticks_diff(now, self._changed_ms) > 30:
            self._was_down = down
            self._changed_ms = now
            return down
        return False


class Hardware:
    def __init__(self):
        self.next = Button(config.PIN_BUTTON_NEXT)
        self.ok = Button(config.PIN_BUTTON_OK)
        self.led_green = machine.Pin(config.PIN_LED_GREEN, machine.Pin.OUT)
        self.led_red = machine.Pin(config.PIN_LED_RED, machine.Pin.OUT)
        i2c = machine.I2C(config.OLED_I2C, sda=machine.Pin(config.OLED_SDA),
                          scl=machine.Pin(config.OLED_SCL), freq=400000)
        self.oled = SSD1306_I2C(128, 64, i2c)
        self._adc = machine.ADC(4)

    def show(self, *lines):
        """Affiche jusqu'à 6 lignes de 16 caractères."""
        self.oled.fill(0)
        for i, line in enumerate(lines[:6]):
            self.oled.text(str(line)[:16], 0, i * 10)
        self.oled.show()

    def blink(self, led, ms=300):
        led.value(1)
        time.sleep_ms(ms)
        led.value(0)

    def temperature(self):
        volts = self._adc.read_u16() * 3.3 / 65535
        return 27 - (volts - 0.706) / 0.001721
