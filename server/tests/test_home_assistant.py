"""Jetons personnels, réglages de la voiture, vue d'ensemble et historique des
trajets : ce dont l'intégration Home Assistant a besoin."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from carpox_server.app import create_app
from test_devices import box_sync, make_device, trip

STEP = 0.02 / 111.195


def track(n, lat0=50.668):
    return [[round(lat0 + i * STEP, 5), 4.6118] for i in range(n)]


def api_token(client, headers, name="Home Assistant"):
    r = client.post("/api/me/tokens", headers=headers, json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()


def bearer(token):
    return {"Authorization": "Bearer " + token}


def test_jeton_personnel_lecture_seule_et_revocable(client, loic):
    device = make_device(client, loic)
    created = api_token(client, loic)
    assert created["token"].startswith("cpx_")
    ha = bearer(created["token"])

    assert client.get("/api/me", headers=ha).json()["username"] == "loic"
    assert client.get("/api/me/overview", headers=ha).status_code == 200
    assert client.get("/api/devices/%s/summary" % device["id"], headers=ha).status_code == 200
    # Le code Bluetooth n'est pas donné à un jeton en lecture seule.
    assert "ble_pin" not in client.get("/api/devices/%s" % device["id"], headers=ha).json()
    assert "ble_pin" in client.get("/api/devices/%s" % device["id"], headers=loic).json()

    # Aucune écriture possible, ni gestion des jetons.
    me = client.get("/api/me", headers=loic).json()["person"]
    r = client.post("/api/devices/%s/entries" % device["id"], headers=ha,
                    json={"type": "fuel", "amount_cents": 1000, "payer": me})
    assert r.status_code == 403
    assert client.post("/api/devices", headers=ha, json={"name": "X"}).status_code == 403
    assert client.post("/api/me/tokens", headers=ha, json={"name": "X"}).status_code == 403
    assert client.get("/api/me/tokens", headers=ha).status_code == 403

    tokens = client.get("/api/me/tokens", headers=loic).json()
    assert [t["name"] for t in tokens] == ["Home Assistant"]
    assert tokens[0]["last_used_at"] is not None
    assert "token" not in tokens[0] and "token_hash" not in tokens[0]

    assert client.delete("/api/me/tokens/%d" % created["id"], headers=loic).status_code == 204
    assert client.get("/api/me", headers=ha).status_code == 401


def test_jeton_d_un_autre_compte_non_revocable(client, loic, julien):
    created = api_token(client, loic)
    assert client.delete("/api/me/tokens/%d" % created["id"], headers=julien).status_code == 404
    assert client.get("/api/me", headers=bearer(created["token"])).status_code == 200


def test_jeton_survit_au_changement_de_mot_de_passe(client, loic):
    ha = bearer(api_token(client, loic)["token"])
    r = client.post("/api/me/password", headers=loic,
                    json={"old_password": "correct-horse-battery", "new_password": "une-autre-phrase-longue"})
    assert r.status_code == 204
    assert client.get("/api/me/overview", headers=ha).status_code == 200


def test_reglages_reserves_au_proprietaire(client, loic, julien):
    device = make_device(client, loic)
    dev = "/api/devices/%s" % device["id"]
    client.post(dev + "/members", headers=loic, json={"username": "julien"})
    r = client.patch(dev, headers=loic, json={"name": "Golf bleue", "tank_l": 50, "consumption_l_100km": 6.2,
                                                "odometer_start_km": 123456})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Golf bleue"
    assert r.json()["settings"] == {"tank_l": 50, "consumption_l_100km": 6.2, "odometer_start_km": 123456}
    assert client.patch(dev, headers=julien, json={"tank_l": 10}).status_code == 403
    assert client.patch(dev, headers=loic, json={"tank_l": -1}).status_code == 422
    assert client.patch(dev, headers=loic, json={"name": None}).status_code == 400
    # null efface un réglage, un champ absent ne change rien.
    r = client.patch(dev, headers=loic, json={"odometer_start_km": None})
    assert r.json()["settings"] == {"tank_l": 50, "consumption_l_100km": 6.2, "odometer_start_km": None}


def test_km_sans_badge_et_estimation_du_plein(client, loic, julien):
    device = make_device(client, loic)
    dev = "/api/devices/%s" % device["id"]
    client.post(dev + "/members", headers=loic, json={"username": "julien"})
    client.put(dev + "/badges/111", headers=loic, json={"label": "Loic", "username": "loic"})
    client.put(dev + "/badges/222", headers=loic, json={"label": "Julien", "username": "julien"})
    client.patch(dev, headers=loic, json={"tank_l": 50, "consumption_l_100km": 6, "odometer_start_km": 100000})
    people = {p["name"]: p["key"] for p in client.get(dev, headers=loic).json()["people"]}

    # Premier plein : réservoir plein.
    client.post(dev + "/entries", headers=loic,
                json={"type": "fuel", "amount_cents": 7000, "payer": people["Loïc"], "litres": 45})
    r = box_sync(client, device, [
        {**trip(1, 100, "111", "222"), "track": track(20)},
        {"seq": 2, "type": "drive", "km": 50, "start": 1_800_000_000, "end": 1_800_001_000, "track": track(5)},
    ])
    assert r.status_code == 200, r.text
    summary = client.get(dev + "/summary", headers=loic).json()
    assert summary["km"] == {"total": 150, "tracked": 100, "untracked": 50, "since_fill": 150, "odometer": 100150}
    assert summary["pending_untracked_km"] == 50
    fuel = summary["fuel"]
    assert fuel["consumption_source"] == "configured"
    assert fuel["remaining_l"] == 41.0  # 50 - 150 km × 6 L/100
    assert fuel["remaining_pct"] == 82
    assert fuel["last_fill"]["litres"] == 45

    # Deuxième plein de 9 L : 6 L/100 km mesurés. Julien paie 15 € ; le trajet
    # à deux coûte 10 € (5 chacun), les 50 km sans badge sont pour Julien.
    client.post(dev + "/entries", headers=julien,
                json={"type": "fuel", "amount_cents": 1500, "payer": people["Julien"], "litres": 9})
    summary = client.get(dev + "/summary", headers=loic).json()
    assert summary["fuel"]["consumption_source"] == "measured"
    assert summary["fuel"]["measured_l_100km"] == 6.0
    assert summary["fuel"]["remaining_l"] == 50
    balances = {b["name"]: b["cents"] for b in summary["balances"]}
    assert balances == {"Loïc": -500, "Julien": 500}


def test_vue_d_ensemble(client, loic, julien):
    device = make_device(client, loic)
    dev = "/api/devices/%s" % device["id"]
    client.post(dev + "/members", headers=loic, json={"username": "julien"})
    client.put(dev + "/badges/111", headers=loic, json={"label": "Loic", "username": "loic"})
    client.put(dev + "/badges/222", headers=loic, json={"label": "Julien", "username": "julien"})
    box_sync(client, device, [{**trip(1, 100, "111", "222"), "end": 1_800_000_000, "track": track(10)}])
    people = {p["name"]: p["key"] for p in client.get(dev, headers=loic).json()["people"]}
    client.post(dev + "/entries", headers=loic, json={"type": "fuel", "amount_cents": 1000, "payer": people["Loïc"]})
    make_device(client, julien, "Clio")  # voiture de Julien seul

    ov = client.get("/api/me/overview", headers=bearer(api_token(client, julien)["token"])).json()
    assert ov["user"]["username"] == "julien"
    assert [c["name"] for c in ov["cars"]] == ["Clio", "Golf"]
    golf = ov["cars"][1]
    assert golf["is_owner"] is False
    assert golf["last_sync_at"] is not None
    assert golf["me"]["balance_cents"] == -500
    assert golf["me"]["km"] == 100
    assert golf["me"]["owes"] == [{"to": {"key": people["Loïc"], "name": "Loïc"}, "amount_cents": 500}]
    assert golf["me"]["owed"] == []
    assert golf["trips_count"] == 1
    assert golf["last_trip"]["people"] == ["Loïc", "Julien"]
    assert golf["last_position"] == {"lat": track(10)[-1][0], "lon": 4.6118, "at": 1_800_000_000}
    assert golf["fuel"]["remaining_l"] is None  # réservoir non réglé
    assert ov["totals"] == {"balance_cents": -500, "owes_cents": 500, "owed_cents": 0, "km": 100}
    clio = ov["cars"][0]
    assert clio["is_owner"] is True and clio["last_trip"] is None and clio["last_position"] is None


def test_historique_et_parcours(client, loic, julien):
    device = make_device(client, loic)
    dev = "/api/devices/%s" % device["id"]
    box_sync(client, device, [
        {**trip(1, 10, "111"), "track": track(30)},
        {"seq": 2, "type": "drive", "km": 3},
        trip(3, 5, "111"),
    ])
    trips = client.get(dev + "/trips", headers=loic).json()
    assert [(t["seq"], t["type"], t["track_points"]) for t in trips] == [(3, "trip", 0), (2, "drive", 0),
                                                                         (1, "trip", 30)]
    assert "track" not in trips[2]
    assert [t["seq"] for t in client.get(dev + "/trips?before=3&limit=1", headers=loic).json()] == [2]
    one = client.get(dev + "/trips/%d" % trips[2]["id"], headers=loic).json()
    assert one["track"] == track(30)
    # Le journal ne renvoie pas les parcours (trop lourds), juste leur taille.
    events = client.get(dev + "/events", headers=loic).json()
    assert all("track" not in e["data"] for e in events)
    assert [e["label"] for e in events if e["type"] == "drive"] == ["Sans badge"]
    # Réservé aux membres.
    assert client.get(dev + "/trips/%d" % trips[2]["id"], headers=julien).status_code == 404


def test_parcours_invalide_refuse(client, loic):
    device = make_device(client, loic)
    assert box_sync(client, device, [{**trip(1, 1, "1"), "track": [[91, 4]]}]).status_code == 422
    assert box_sync(client, device, [{**trip(1, 1, "1"), "track": [[50]]}]).status_code == 422
    assert box_sync(client, device, [{**trip(1, 1, "1"), "track": track(1001)}]).status_code == 422
    assert box_sync(client, device, [{"seq": 1, "type": "autre", "km": 1}]).status_code == 422


def test_fond_de_carte_dans_la_politique_de_securite(tmp_path):
    client = TestClient(create_app(str(tmp_path / "a.sqlite3"), app_dir=str(tmp_path), invite_code=""))
    assert client.get("/api/config").json()["map_tiles"].startswith("https://tile.openstreetmap.org/")
    assert "img-src 'self' data: https://tile.openstreetmap.org;" in client.get("/api/config").headers[
        "Content-Security-Policy"]
    client = TestClient(create_app(str(tmp_path / "b.sqlite3"), app_dir=str(tmp_path), invite_code="",
                                   map_tiles=""))
    assert client.get("/api/config").json()["map_tiles"] is None
    assert "img-src 'self' data:;" in client.get("/api/config").headers["Content-Security-Policy"]
    with pytest.raises(ValueError):
        create_app(str(tmp_path / "c.sqlite3"), app_dir=str(tmp_path), map_tiles="http://x/{z}/{x}/{y}.png")


def test_ancienne_base_mise_a_jour(tmp_path):
    """Une base créée par la version précédente reçoit les nouvelles colonnes."""
    path = str(tmp_path / "old.sqlite3")
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            display_name TEXT NOT NULL, password_hash TEXT NOT NULL, failed_logins INTEGER NOT NULL DEFAULT 0,
            locked_until INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL);
        CREATE TABLE devices (id TEXT PRIMARY KEY, name TEXT NOT NULL, owner_id INTEGER NOT NULL REFERENCES users(id),
            token_hash TEXT NOT NULL, ble_pin TEXT NOT NULL, created_at INTEGER NOT NULL, last_sync_at INTEGER);
    """)
    conn.close()
    client = TestClient(create_app(path, app_dir=str(tmp_path / "x"), invite_code=""))
    r = client.post("/api/auth/register", json={"username": "loic", "password": "correct-horse-battery",
                                                "display_name": "Loïc"})
    headers = bearer(r.json()["token"])
    device = make_device(client, headers)
    r = client.patch("/api/devices/%s" % device["id"], headers=headers, json={"tank_l": 40})
    assert r.json()["settings"]["tank_l"] == 40


def _same_shape(actual, expected, path="overview"):
    """Mêmes clés, récursivement (les valeurs et les listes vides ne comptent pas)."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        assert set(actual) == set(expected), (path, set(actual) ^ set(expected))
        for key in expected:
            _same_shape(actual[key], expected[key], path + "." + key)
    elif isinstance(expected, list) and isinstance(actual, list):
        if actual and expected:
            _same_shape(actual[0], expected[0], path + "[0]")


def test_contrat_avec_l_integration_home_assistant(client, loic, julien):
    """L'intégration HA est testée avec home-assistant/tests/overview.json : le
    serveur doit renvoyer exactement les mêmes clés."""
    import json
    from pathlib import Path

    expected = json.loads((Path(__file__).parents[2] / "home-assistant/tests/overview.json").read_text("utf-8"))
    device = make_device(client, loic)
    dev = "/api/devices/%s" % device["id"]
    client.post(dev + "/members", headers=loic, json={"username": "julien"})
    client.put(dev + "/badges/111", headers=loic, json={"label": "Loic", "username": "loic"})
    client.put(dev + "/badges/222", headers=loic, json={"label": "Julien", "username": "julien"})
    client.patch(dev, headers=loic, json={"tank_l": 50, "consumption_l_100km": 6})
    people = {p["name"]: p["key"] for p in client.get(dev, headers=loic).json()["people"]}
    client.post(dev + "/entries", headers=loic, json={"type": "fuel", "amount_cents": 7000, "payer": people["Loïc"],
                                                      "litres": 45})
    box_sync(client, device, [{**trip(1, 100, "111", "222"), "track": track(20)}])
    client.post(dev + "/entries", headers=julien, json={"type": "fuel", "amount_cents": 1000, "payer": people["Julien"]})
    box_sync(client, device, [{**trip(2, 50, "111", "222"), "track": track(20)}])
    ov = client.get("/api/me/overview", headers=bearer(api_token(client, loic)["token"])).json()
    _same_shape(ov, expected)


def test_parcours_visible_par_le_proprietaire_et_les_personnes_a_bord(client, loic, julien):
    device = make_device(client, loic)
    dev = "/api/devices/%s" % device["id"]
    client.post(dev + "/members", headers=loic, json={"username": "julien"})
    client.put(dev + "/badges/111", headers=loic, json={"label": "Loic", "username": "loic"})
    client.put(dev + "/badges/222", headers=loic, json={"label": "Julien", "username": "julien"})
    box_sync(client, device, [
        {**trip(1, 10, "111", "222"), "track": track(5)},  # Julien à bord
        {**trip(2, 10, "111"), "track": track(5)},  # Loïc seul
        {"seq": 3, "type": "drive", "km": 3, "track": track(5)},  # sans badge
    ])
    seen = {t["seq"]: t["track_visible"] for t in client.get(dev + "/trips", headers=julien).json()}
    assert seen == {1: True, 2: False, 3: False}
    assert all(t["track_visible"] for t in client.get(dev + "/trips", headers=loic).json())
    ids = {t["seq"]: t["id"] for t in client.get(dev + "/trips", headers=julien).json()}
    assert client.get(dev + "/trips/%d" % ids[1], headers=julien).json()["track"] == track(5)
    assert client.get(dev + "/trips/%d" % ids[2], headers=julien).json()["track"] == []
    assert client.get(dev + "/trips/%d" % ids[3], headers=loic).json()["track"] == track(5)
    # Dernière position : celle du dernier parcours que la personne peut voir.
    julien_car = client.get("/api/me/overview", headers=julien).json()["cars"][0]
    assert julien_car["last_position"]["lat"] == track(5)[-1][0]
    client2 = box_sync(client, device, [{**trip(4, 10, "111"), "track": track(5, lat0=51.0)}])
    assert client2.status_code == 200
    assert client.get("/api/me/overview", headers=julien).json()["cars"][0]["last_position"]["lat"] == track(5)[-1][0]
    assert client.get("/api/me/overview", headers=loic).json()["cars"][0]["last_position"]["lat"] == track(5, 51.0)[-1][0]
