"""Fait tourner le vrai firmware (carpox.app) sous CPython avec du matériel simulé.

Le GPS reçoit de vraies phrases NMEA, décodées par la vraie bibliothèque
micropyGPS : c'est la chaîne complète UART -> km -> journal qui est testée.
"""

import importlib
import json
import sys
import time
import types

import pytest

# --- faux matériel -----------------------------------------------------------


class FakePin:
    IN = OUT = PULL_DOWN = 0
    registry = {}

    def __init__(self, n, *args, **kwargs):
        self.n = n
        self._v = 0
        FakePin.registry[n] = self

    def value(self, v=None):
        if v is None:
            return self._v
        self._v = v


class FakeUART:
    instance = None

    def __init__(self, *a, **k):
        self.buf = b""
        FakeUART.instance = self

    def any(self):
        return len(self.buf)

    def read(self):
        data, self.buf = self.buf, b""
        return data


class FakeOled:
    def __init__(self, *a):
        self.lines = []
        self.screen = []

    def fill(self, c):
        self.lines = []

    def text(self, t, x, y):
        self.lines.append(t)

    def show(self):
        self.screen = list(self.lines)


class FakeRFID:
    OK = 0
    REQIDL = 0x26
    card = None

    def __init__(self, **k):
        pass

    def init(self):
        pass

    def request(self, mode):
        return (0 if FakeRFID.card else 2), 0

    def SelectTagSN(self):
        return 0, list(FakeRFID.card.to_bytes(4, "little"))


class FakeBLE:
    def __init__(self):
        self.notified = []

    def active(self, *a):
        return True

    def config(self, **k):
        pass

    def irq(self, handler):
        self.handler = handler

    def gatts_register_services(self, services):
        return ((1, 2),)

    def gatts_set_buffer(self, *a):
        pass

    def gap_advertise(self, *a, **k):
        pass

    def gatts_read(self, handle):
        return self.pending

    def gatts_notify(self, conn, handle, data):
        self.notified.append(bytes(data))


class FakeUUID:
    def __init__(self, s):
        self.s = s

    def __bytes__(self):
        return bytes(16)


def nmea(body):
    crc = 0
    for ch in body:
        crc ^= ord(ch)
    return "$%s*%02X\r\n" % (body, crc)


def ddm(value, width):
    deg = int(value)
    minutes = (value - deg) * 60
    return "%0*d%07.4f" % (width, deg, minutes)


def gps_sentences(lat, lon, second):
    hhmmss = "12%02d%02d.00" % (second // 60 % 60, second % 60)
    return (nmea("GPGGA,%s,%s,N,%s,E,1,08,0.9,100.0,M,47.0,M,," % (hhmmss, ddm(lat, 2), ddm(lon, 3)))
            + nmea("GPRMC,%s,A,%s,N,%s,E,40.0,0.0,300926,,,A" % (hhmmss, ddm(lat, 2), ddm(lon, 3))))


@pytest.fixture
def firmware(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    clock_ms = [0]
    monkeypatch.setattr(time, "ticks_ms", lambda: clock_ms[0], raising=False)
    monkeypatch.setattr(time, "ticks_diff", lambda a, b: a - b, raising=False)
    monkeypatch.setattr(time, "ticks_add", lambda a, b: a + b, raising=False)

    def sleep_ms(ms):
        clock_ms[0] += ms

    monkeypatch.setattr(time, "sleep_ms", sleep_ms, raising=False)

    machine = types.ModuleType("machine")
    machine.Pin = FakePin
    machine.UART = FakeUART
    machine.I2C = lambda *a, **k: None
    machine.ADC = lambda n: types.SimpleNamespace(read_u16=lambda: 14000)
    ssd = types.ModuleType("ssd1306")
    ssd.SSD1306_I2C = FakeOled
    mfrc = types.ModuleType("mfrc522")
    mfrc.MFRC522 = FakeRFID
    bt = types.ModuleType("bluetooth")
    bt.UUID = FakeUUID
    bt.BLE = FakeBLE
    mp = types.ModuleType("micropython")
    mp.const = lambda x: x
    network = types.ModuleType("network")
    network.STA_IF = 0
    requests = types.ModuleType("requests")
    config = types.ModuleType("config")
    exec(open(__file__.replace("tests/test_app_simulation.py", "config_example.py")).read(), config.__dict__)
    config.BLE_PIN = "123456"
    for name, mod in [("machine", machine), ("ssd1306", ssd), ("mfrc522", mfrc), ("bluetooth", bt),
                      ("micropython", mp), ("network", network), ("requests", requests), ("config", config)]:
        monkeypatch.setitem(sys.modules, name, mod)
    lib = str(__import__("pathlib").Path(__file__).parents[1] / "lib")
    monkeypatch.syspath_prepend(lib)
    for mod in list(sys.modules):
        if mod.startswith("carpox.") or mod == "micropyGPS":
            monkeypatch.delitem(sys.modules, mod)
    app_module = importlib.import_module("carpox.app")
    monkeypatch.setattr(app_module.wifi, "try_sync", lambda j, b: (False, "Aucun WiFi connu"))
    app = app_module.App()
    return app, clock_ms


def press(app, button):
    pin = app.hw.next.pin if button == "next" else app.hw.ok.pin
    pin.value(1)
    for _ in range(3):
        app.step()
        time.sleep_ms(40)
    pin.value(0)
    for _ in range(3):
        app.step()
        time.sleep_ms(40)


def run_for(app, ms):
    for _ in range(ms // 20):
        app.ble.poll()
        fix = app.gps.poll()
        if fix and app.recorder.active:
            app.recorder.add_fix(*fix)
        app.step()
        time.sleep_ms(20)


def present_badge(app, uid):
    FakeRFID.card = uid
    run_for(app, 400)
    FakeRFID.card = None
    run_for(app, 1500)


def test_trajet_complet_avec_gps(firmware):
    app, _ = firmware
    assert app.state == "menu"
    press(app, "ok")  # Nouveau trajet
    assert app.state == "driver"
    present_badge(app, 54835169)
    assert app.state == "passengers"
    present_badge(app, 707308629)
    present_badge(app, 401531548)
    present_badge(app, 401531548)  # scanné deux fois : compté une fois
    assert app.recorder.passengers == ["707308629", "401531548"]
    press(app, "ok")  # démarrer
    assert app.state == "trip"

    # 5 km vers le nord, une position par seconde à ~72 km/h.
    step = 0.02 / 111.195
    for s in range(251):
        FakeUART.instance.buf += gps_sentences(50.6680 + s * step, 4.6118, s).encode()
        run_for(app, 1000)
    assert app.recorder.km == pytest.approx(5.0, abs=0.1)

    press(app, "ok")
    assert app.state == "confirm_end"
    press(app, "ok")
    events = app.journal.all()
    assert len(events) == 1
    trip = events[0]
    assert trip["driver"] == "54835169"
    assert trip["passengers"] == ["707308629", "401531548"]
    assert trip["km"] == pytest.approx(5.0, abs=0.1)


def test_reprise_apres_coupure(firmware, tmp_path):
    app, _ = firmware
    press(app, "ok")
    present_badge(app, 54835169)
    press(app, "ok")
    assert app.state == "trip"
    app.recorder.acc.total_m = 1234.0
    run_for(app, 31000)  # sauvegarde périodique
    saved = json.loads((tmp_path / "trip_state.json").read_text())
    assert saved["total_m"] == 1234.0

    app2 = type(app)()  # redémarrage du boîtier
    assert app2.state == "resume"
    press(app2, "next")  # terminer
    assert app2.journal.all()[0]["km"] == pytest.approx(1.234)
    assert not (tmp_path / "trip_state.json").exists()


def test_bluetooth_de_bout_en_bout(firmware):
    app, _ = firmware
    ble = app.ble._ble

    def send(line):
        ble.pending = line.encode()
        app.ble._irq(3, (7, app.ble._rx))
        app.ble.poll()

    app.ble._irq(1, (7, 0, b""))
    app.ble.poll()
    send("AUTH 123456\n")
    send("STATUS\n")
    replies = b"".join(ble.notified).decode().strip().split("\n")
    assert json.loads(replies[0])["ok"] is True
    assert json.loads(replies[1])["pending"] == 0
