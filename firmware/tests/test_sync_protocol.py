import json

from carpox import sync
from carpox.protocol import CommandHandler
from carpox.trip import TripRecorder


class FakeClock:
    value = None

    def set_unix_time(self, ts):
        self.value = ts


def fill(journal, n):
    for i in range(n):
        journal.append({"type": "trip", "km": i + 1, "driver": "1", "passengers": []})


def test_sync_all_par_lots(journal, badges):
    fill(journal, 120)
    received = []

    def post(payload):
        received.extend(payload["events"])
        return {"acked_seq": payload["events"][-1]["seq"], "badges": {"1": "Loic"}, "server_time": 1700000000}

    clock = FakeClock()
    assert sync.sync_all(post, "box-1", journal, badges, clock) == 120
    assert len(received) == 120
    assert journal.pending_count() == 0
    assert badges.name(1) == "Loic"
    assert clock.value == 1700000000


def test_sync_echec_garde_le_journal(journal):
    fill(journal, 3)

    def post(payload):
        raise OSError("pas de réseau")

    try:
        sync.sync_all(post, "box-1", journal)
    except OSError:
        pass
    assert journal.pending_count() == 3


def handler(journal, badges):
    return CommandHandler("box-1", "4821", journal, badges, TripRecorder(), FakeClock())


def test_protocole_exige_le_code(journal, badges):
    h = handler(journal, badges)
    assert json.loads(h.handle("STATUS")[0])["ok"] is False
    assert json.loads(h.handle("AUTH 0000")[0])["ok"] is False
    assert json.loads(h.handle("AUTH 4821")[0])["ok"] is True
    status = json.loads(h.handle("STATUS")[0])
    assert status["device_id"] == "box-1"


def test_protocole_bloque_apres_trop_d_essais(journal, badges):
    h = handler(journal, badges)
    for _ in range(5):
        h.handle("AUTH 1111")
    assert json.loads(h.handle("AUTH 4821")[0])["ok"] is False
    h.on_connect()
    assert json.loads(h.handle("AUTH 4821")[0])["ok"] is True


def test_protocole_relais_via_app(journal, badges):
    fill(journal, 3)
    h = handler(journal, badges)
    h.handle("AUTH 4821")
    lines = [json.loads(l) for l in h.handle("EVENTS 0")]
    assert [l["event"]["seq"] for l in lines[:-1]] == [1, 2, 3]
    assert lines[-1]["end"] is True
    resp = json.loads(h.handle('APPLY {"acked_seq": 3, "badges": {"9": "Julien"}}')[0])
    assert resp["acked"] == 3
    assert journal.pending_count() == 0
    assert badges.name(9) == "Julien"


def test_protocole_badges_et_scan(journal, badges):
    h = handler(journal, badges)
    h.handle("AUTH 4821")
    h.last_scan = "401531548"
    assert json.loads(h.handle("LASTSCAN")[0])["uid"] == "401531548"
    h.handle("BADGE 401531548 Julien D")
    assert badges.name("401531548") == "Julien D"
    assert json.loads(h.handle("BLA")[0])["ok"] is False
    assert json.loads(h.handle("APPLY pas-du-json")[0])["ok"] is False
