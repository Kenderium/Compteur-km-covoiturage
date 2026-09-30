"""Bluetooth Low Energy intégré au Pico W (service « Nordic UART »).

Remplace le module HC-05 : l'app (Chrome Android / ordinateur) se connecte
directement au boîtier. Les messages sont des lignes de texte, traitées par
carpox.protocol.CommandHandler. Les notifications BLE font 20 octets par
défaut : les réponses sont découpées et l'app les recolle jusqu'au "\\n".
"""

import struct
import time

import bluetooth
from micropython import const

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_MTU_EXCHANGED = const(21)

_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

_UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_TX = (bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E"), _FLAG_READ | _FLAG_NOTIFY)
_UART_RX = (bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E"), _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE)
_UART_SERVICE = (_UART_UUID, (_UART_TX, _UART_RX))

_MAX_LINE = 2048


def _adv_payload(name, service_uuid):
    payload = bytearray()

    def append(adv_type, value):
        payload.extend(struct.pack("BB", len(value) + 1, adv_type) + value)

    append(0x01, struct.pack("B", 0x02 | 0x04))  # LE seulement, découvrable
    append(0x09, name.encode())
    return payload, bytes([17, 0x07]) + bytes(service_uuid)


class BleUart:
    def __init__(self, name, handler):
        self.handler = handler
        self.name = name
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.config(gap_name=name)
        self._ble.irq(self._irq)
        ((self._tx, self._rx),) = self._ble.gatts_register_services((_UART_SERVICE,))
        self._ble.gatts_set_buffer(self._rx, 256, True)
        self._conn = None
        self._chunk = 20
        self._buffer = b""
        self._inbox = []
        self._adv, self._resp = _adv_payload(name, _UART_UUID)
        self.advertise()

    def advertise(self):
        self._ble.gap_advertise(500000, adv_data=self._adv, resp_data=self._resp)

    def connected(self):
        return self._conn is not None

    def _irq(self, event, data):
        # Appelé en interruption : on stocke, le traitement se fait dans poll().
        if event == _IRQ_CENTRAL_CONNECT:
            self._conn = data[0]
            self._chunk = 20
            self._buffer = b""
            self._inbox.append(None)  # marqueur de nouvelle connexion
        elif event == _IRQ_CENTRAL_DISCONNECT:
            self._conn = None
            self.advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn, handle = data
            if conn == self._conn and handle == self._rx:
                self._buffer += self._ble.gatts_read(self._rx)
                while b"\n" in self._buffer:
                    line, self._buffer = self._buffer.split(b"\n", 1)
                    self._inbox.append(line)
                if len(self._buffer) > _MAX_LINE:
                    self._buffer = b""
        elif event == _IRQ_MTU_EXCHANGED:
            self._chunk = max(20, data[1] - 3)

    def poll(self):
        """Traite les commandes reçues. À appeler dans la boucle principale."""
        while self._inbox:
            item = self._inbox.pop(0)
            if item is None:
                self.handler.on_connect()
                continue
            try:
                text = item.decode()
            except UnicodeError:
                continue
            for reply in self.handler.handle(text):
                self.send(reply + "\n")

    def send(self, text):
        if self._conn is None:
            return
        data = text.encode()
        for i in range(0, len(data), self._chunk):
            # La pile BLE refuse quand sa file d'envoi est pleine : on réessaie.
            for _ in range(50):
                if self._conn is None:
                    return
                try:
                    self._ble.gatts_notify(self._conn, self._tx, data[i:i + self._chunk])
                    break
                except OSError:
                    time.sleep_ms(10)
            else:
                return
