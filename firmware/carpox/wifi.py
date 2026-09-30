"""Synchronisation WiFi : quand un réseau connu est à portée, envoyer le
journal au serveur, puis couper le WiFi pour économiser la batterie."""

import json
import time

import network

try:
    import requests
except ImportError:  # anciennes versions de MicroPython
    import urequests as requests

import config
from carpox import clock, sync


def _known_network_in_range(wlan):
    known = dict(config.WIFI_NETWORKS)
    try:
        seen = [s[0].decode() for s in wlan.scan()]
    except OSError:
        return None
    for ssid in seen:
        if ssid in known:
            return ssid, known[ssid]
    return None


def _connect(wlan, ssid, password, timeout_s=15):
    wlan.connect(ssid, password)
    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > timeout_s:
            return False
        time.sleep_ms(200)
    return True


def _post(payload):
    url = config.SERVER_URL.rstrip("/") + "/api/device/sync"
    resp = requests.post(
        url,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + config.DEVICE_TOKEN},
    )
    try:
        if resp.status_code != 200:
            raise OSError("serveur : HTTP %d" % resp.status_code)
        return resp.json()
    finally:
        resp.close()


def try_sync(journal, badges):
    """Tente une synchro. Retourne (ok, message court pour l'écran)."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        found = _known_network_in_range(wlan)
        if found is None:
            return False, "Aucun WiFi connu"
        if not _connect(wlan, found[0], found[1]):
            return False, "WiFi: echec"
        count = sync.sync_all(_post, config.DEVICE_ID, journal, badges, clock)
        journal.compact()
        return True, "%d envoye(s)" % count
    except Exception as exc:  # réseau, TLS, serveur : on réessaiera plus tard
        return False, str(exc)[:16]
    finally:
        wlan.disconnect()
        wlan.active(False)
