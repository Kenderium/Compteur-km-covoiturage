"""Boucle principale du boîtier.

La boucle ne bloque jamais longtemps : à chaque tour elle lit les boutons,
le GPS, le lecteur RFID et les commandes Bluetooth. Chaque écran est un état.

Boutons : SUIVANT (menu suivant / annuler) et OK (valider).

Le boîtier compte les km dès qu'il est allumé (donc dès que la voiture
roule) : hors trajet badgé, ils vont dans des segments "drive" (carpox.drive).
"""

import json
import time

import config
from carpox import clock, wifi
from carpox.badges import Badges
from carpox.ble import BleUart
from carpox.drive import DriveRecorder
from carpox.gps import Gps
from carpox.hw import Hardware
from carpox.journal import Journal
from carpox.protocol import CommandHandler
from carpox.rfid import RfidReader
from carpox.trip import TripRecorder

MENU = ["Nouveau trajet", "Historique", "Synchro WiFi", "Scanner badge", "Etat"]
TRIP_STATE_FILE = "trip_state.json"
DRIVE_STATE_FILE = "drive_state.json"
SAVE_EVERY_MS = 30000
RFID_EVERY_MS = 250
# Segment hors trajet terminé après N secondes à l'arrêt (config.DRIVE_IDLE_S).
DRIVE_IDLE_S = getattr(config, "DRIVE_IDLE_S", 180)


def _save_state(path, recorder):
    with open(path, "w") as f:
        f.write(json.dumps(recorder.snapshot()))


def _clear_state(path):
    try:
        import os
        os.remove(path)
    except OSError:
        pass


def _load_state(path):
    try:
        with open(path) as f:
            return json.loads(f.read())
    except (OSError, ValueError):
        return None


def _save_trip(recorder):
    _save_state(TRIP_STATE_FILE, recorder)


def _clear_trip():
    _clear_state(TRIP_STATE_FILE)


class App:
    def __init__(self):
        self.hw = Hardware()
        self.hw.show("CarpoX", "Demarrage...")
        self.journal = Journal()
        self.badges = Badges()
        self.recorder = TripRecorder()
        self.drive = DriveRecorder()
        self.gps = Gps()
        self.rfid = RfidReader()
        self.handler = CommandHandler(config.DEVICE_ID, config.BLE_PIN, self.journal,
                                      self.badges, self.recorder, clock, self.drive)
        self.ble = BleUart(config.BLE_NAME, self.handler)
        self.state = "menu"
        self.menu_index = 0
        self.history = []
        self.history_index = 0
        self.message_until = 0
        self.last_rfid_ms = 0
        self.last_save_ms = 0
        self.last_drive_save_ms = 0
        self.last_sync_s = time.time() - config.SYNC_INTERVAL_S + 20  # 1re synchro ~20 s après démarrage
        self.dirty = True

        # Km roulés hors trajet avant la dernière coupure du contact.
        saved = _load_state(DRIVE_STATE_FILE)
        if saved:
            self.drive.restore(saved)
            self.close_drive(keep_position=False)

        saved = _load_state(TRIP_STATE_FILE)
        if saved and saved.get("driver"):
            self.recorder.restore(saved)
            self.state = "resume"

    # --- utilitaires -------------------------------------------------------

    def goto(self, state):
        self.state = state
        self.dirty = True

    def message(self, *lines, ms=1500, then="menu"):
        self.hw.show(*lines)
        self.message_until = time.ticks_add(time.ticks_ms(), ms)
        self.after_message = then
        self.state = "message"

    def scan_badge(self):
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_rfid_ms) < RFID_EVERY_MS:
            return None
        self.last_rfid_ms = now
        uid = self.rfid.read()
        if uid:
            self.handler.last_scan = uid
        return uid

    # --- boucle ------------------------------------------------------------

    def run(self):
        while True:
            self.poll_inputs()
            self.step()
            time.sleep_ms(20)

    def poll_inputs(self):
        """Bluetooth et GPS. Les km comptent toujours : dans le trajet s'il y en
        a un, sinon dans le segment hors trajet."""
        self.ble.poll()
        fix = self.gps.poll()
        if fix:
            if self.recorder.active:
                if self.recorder.add_fix(*fix):
                    self.dirty = True
            else:
                self.drive.add_fix(fix[0], fix[1], fix[2], fix[3], time.time(), clock.now())
        if self.drive.active:
            if self.drive.idle_for(time.time()) >= DRIVE_IDLE_S:
                self.close_drive()
            elif time.ticks_diff(time.ticks_ms(), self.last_drive_save_ms) > SAVE_EVERY_MS:
                _save_state(DRIVE_STATE_FILE, self.drive)
                self.last_drive_save_ms = time.ticks_ms()

    def close_drive(self, keep_position=True):
        """Écrit au journal les km roulés hors trajet depuis le dernier arrêt."""
        event = self.drive.close(keep_position)
        if event is not None and event["km"] > 0:
            self.journal.append(event)
        _clear_state(DRIVE_STATE_FILE)

    def step(self):
        nxt = self.hw.next.pressed()
        ok = self.hw.ok.pressed()
        getattr(self, "state_" + self.state)(nxt, ok)

    # --- écrans ------------------------------------------------------------

    def state_message(self, nxt, ok):
        if nxt or ok or time.ticks_diff(time.ticks_ms(), self.message_until) >= 0:
            self.goto(self.after_message)

    def state_menu(self, nxt, ok):
        if nxt:
            self.menu_index = (self.menu_index + 1) % len(MENU)
            self.dirty = True
        if ok:
            self.hw.blink(self.hw.led_green, 150)
            choice = MENU[self.menu_index]
            if choice == "Nouveau trajet":
                self.recorder.reset()
                self.goto("driver")
            elif choice == "Historique":
                self.history = self.journal.recent(20, "trip")
                self.history.reverse()
                self.history_index = 0
                self.goto("history")
            elif choice == "Synchro WiFi":
                self.sync_now()
            elif choice == "Scanner badge":
                self.goto("scan")
            elif choice == "Etat":
                self.goto("status")
            return
        if time.time() - self.last_sync_s >= config.SYNC_INTERVAL_S and self.journal.pending_count():
            self.sync_now(quiet=True)
            return
        if self.dirty:
            item = MENU[self.menu_index]
            pending = self.journal.pending_count()
            self.hw.show("CarpoX", "", "> " + item, "", "",
                         ("%d a envoyer" % pending) if pending else ("BT connecte" if self.ble.connected() else ""))
            self.dirty = False

    def sync_now(self, quiet=False):
        self.last_sync_s = time.time()
        self.hw.show("Synchro WiFi...")
        ok, msg = wifi.try_sync(self.journal, self.badges)
        if quiet and not ok:
            self.goto("menu")
        else:
            self.message("Synchro WiFi", "OK" if ok else "Echec", msg, ms=2000)

    def state_driver(self, nxt, ok):
        if nxt:
            self.goto("menu")
            return
        if self.dirty:
            self.hw.show("Nouveau trajet", "", "Badge du", "conducteur ?", "", "SUIVANT: annuler")
            self.dirty = False
        uid = self.scan_badge()
        if uid:
            self.recorder.set_driver(uid)
            self.hw.blink(self.hw.led_red, 200)
            self.message("Conducteur :", self.badges.name(uid), ms=1200, then="passengers")

    def state_passengers(self, nxt, ok):
        if nxt:
            self.recorder.reset()
            self.goto("menu")
            return
        if ok:
            # À partir d'ici, c'est le trajet qui compte les km.
            self.close_drive(keep_position=False)
            self.recorder.start(clock.now())
            _save_trip(self.recorder)
            self.last_save_ms = time.ticks_ms()
            self.hw.blink(self.hw.led_green, 300)
            self.goto("trip")
            return
        if self.dirty:
            names = [self.badges.name(p) for p in self.recorder.passengers]
            self.hw.show("Passagers: %d" % len(names), *(names[-3:] + ["OK: demarrer"]))
            self.dirty = False
        uid = self.scan_badge()
        if uid and self.recorder.add_passenger(uid):
            self.hw.blink(self.hw.led_red, 200)
            self.dirty = True

    def state_resume(self, nxt, ok):
        if self.dirty:
            self.hw.show("Trajet en cours", "%.1f km" % self.recorder.km, "", "OK: reprendre", "SUIVANT: finir")
            self.dirty = False
        if ok:
            self.goto("trip")
        elif nxt:
            self.finish_trip()

    def state_trip(self, nxt, ok):
        if time.ticks_diff(time.ticks_ms(), self.last_save_ms) > SAVE_EVERY_MS:
            _save_trip(self.recorder)
            self.last_save_ms = time.ticks_ms()
        if ok:
            self.goto("confirm_end")
            return
        if self.dirty:
            gps = ("GPS %d sat" % self.gps.satellites()) if self.gps.has_fix() else "GPS: recherche"
            self.hw.show("En route", "", "%.2f km" % self.recorder.km,
                         "%d personne(s)" % (1 + len(self.recorder.passengers)), gps, "OK: arriver")
            self.dirty = False

    def state_confirm_end(self, nxt, ok):
        if self.dirty:
            self.hw.show("Terminer le", "trajet ?", "", "OK: oui", "SUIVANT: non")
            self.dirty = False
        if ok:
            self.finish_trip()
        elif nxt:
            self.goto("trip")

    def finish_trip(self):
        try:
            temp = self.hw.temperature()
        except Exception:
            temp = None
        event = self.journal.append(self.recorder.stop(clock.now(), temp))
        _clear_trip()
        self.hw.blink(self.hw.led_green, 500)
        self.last_sync_s = time.time() - config.SYNC_INTERVAL_S + 60  # synchro une minute après l'arrivée
        self.message("Trajet fini", "%.1f km" % event["km"],
                     "%d personne(s)" % (1 + len(event["passengers"])), ms=3000)

    def state_history(self, nxt, ok):
        if ok or not self.history:
            if not self.history:
                self.message("Historique vide")
            else:
                self.goto("menu")
            return
        if nxt:
            self.history_index = (self.history_index + 1) % len(self.history)
            self.dirty = True
        if self.dirty:
            t = self.history[self.history_index]
            names = [self.badges.name(p) for p in t.get("passengers", [])]
            self.hw.show("%d/%d  %.1f km" % (self.history_index + 1, len(self.history), t["km"]),
                         "C: " + self.badges.name(t["driver"]), *names[:4])
            self.dirty = False

    def state_scan(self, nxt, ok):
        if nxt or ok:
            self.goto("menu")
            return
        if self.dirty:
            self.hw.show("Presentez", "un badge...")
            self.dirty = False
        uid = self.scan_badge()
        if uid:
            known = self.badges.known(uid)
            self.hw.show("Badge", uid, "", self.badges.name(uid) if known else "(inconnu)", "",
                         "OK: retour")

    def state_status(self, nxt, ok):
        if nxt or ok:
            self.goto("menu")
            return
        if self.dirty:
            self.hw.show("Etat", "Trajets: %d" % self.journal.last_seq(),
                         "A envoyer: %d" % self.journal.pending_count(),
                         "Hors trajet: %.1f km" % self.drive.km,
                         ("GPS %d sat" % self.gps.satellites()) if self.gps.has_fix() else "GPS: pas de fix",
                         "BT: connecte" if self.ble.connected() else "BT: libre")
            self.dirty = False


def main():
    App().run()
