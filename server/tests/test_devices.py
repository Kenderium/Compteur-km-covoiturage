def trip(seq, km, driver, *passengers):
    return {"seq": seq, "type": "trip", "km": km, "driver": driver, "passengers": list(passengers)}


def make_device(client, headers, name="Golf"):
    r = client.post("/api/devices", headers=headers, json={"name": name})
    assert r.status_code == 201
    return r.json()


def box_sync(client, device, events):
    return client.post("/api/device/sync", headers={"Authorization": "Bearer " + device["device_token"]},
                       json={"device_id": device["id"], "events": events})


def test_synchro_wifi_idempotente(client, loic):
    device = make_device(client, loic)
    client.put("/api/devices/%s/badges/54835169" % device["id"], headers=loic,
               json={"label": "Loic", "username": "loic"})
    r = box_sync(client, device, [trip(1, 60, "54835169", "707308629"), trip(2, 30, "54835169")])
    assert r.status_code == 200
    body = r.json()
    assert body["acked_seq"] == 2
    assert body["badges"] == {"54835169": "Loic"}
    assert body["server_time"] > 1_700_000_000
    # Renvoi (coupure pendant la réponse) : pas de doublon.
    assert box_sync(client, device, [trip(2, 30, "54835169")]).json()["acked_seq"] == 2
    events = client.get("/api/devices/%s/events" % device["id"], headers=loic).json()
    assert len(events) == 2


def test_mauvais_jeton_refuse(client, loic):
    device = make_device(client, loic)
    r = client.post("/api/device/sync", headers={"Authorization": "Bearer faux"}, json={"events": []})
    assert r.status_code == 401
    other = make_device(client, loic, "Autre")
    r = client.post("/api/device/sync", headers={"Authorization": "Bearer " + other["device_token"]},
                    json={"device_id": device["id"], "events": []})
    assert r.status_code == 401


def test_nouveau_jeton_invalide_l_ancien(client, loic):
    device = make_device(client, loic)
    new = client.post("/api/devices/%s/token" % device["id"], headers=loic).json()["device_token"]
    assert box_sync(client, device, []).status_code == 401
    device["device_token"] = new
    assert box_sync(client, device, []).status_code == 200


def test_trajet_invalide_refuse(client, loic):
    device = make_device(client, loic)
    assert box_sync(client, device, [trip(1, -5, "1")]).status_code == 422
    assert box_sync(client, device, [trip(1, 5, "1; DROP TABLE")]).status_code == 422


def test_acces_reserve_aux_membres(client, loic, julien):
    device = make_device(client, loic)
    assert client.get("/api/devices/%s" % device["id"], headers=julien).status_code == 404
    assert client.post("/api/devices/%s/members" % device["id"], headers=loic,
                       json={"username": "julien"}).status_code == 201
    assert client.get("/api/devices/%s" % device["id"], headers=julien).status_code == 200
    # Julien est membre mais pas propriétaire.
    assert client.post("/api/devices/%s/token" % device["id"], headers=julien).status_code == 403
    assert [d["id"] for d in client.get("/api/devices", headers=julien).json()] == [device["id"]]


def test_soldes_de_bout_en_bout(client, loic, julien):
    """Loïc conduit, Julien et un invité (badge) montent ; Julien paie le plein."""
    device = make_device(client, loic)
    dev = "/api/devices/%s" % device["id"]
    client.post(dev + "/members", headers=loic, json={"username": "julien"})
    client.put(dev + "/badges/111", headers=loic, json={"label": "Loic", "username": "loic"})
    client.put(dev + "/badges/222", headers=julien, json={"label": "Julien", "username": "julien"})
    client.put(dev + "/badges/333", headers=loic, json={"label": "Amandine"})
    box_sync(client, device, [trip(1, 100, "111", "222", "333"), trip(2, 50, "111")])
    people = {p["name"]: p["key"] for p in client.get(dev, headers=loic).json()["people"]}
    assert set(people) == {"Loïc", "Julien", "Amandine"}

    r = client.post(dev + "/entries", headers=julien,
                    json={"type": "fuel", "amount_cents": 9000, "payer": people["Julien"]})
    assert r.status_code == 201, r.text
    summary = client.get(dev + "/summary", headers=loic).json()
    balances = {b["name"]: b["cents"] for b in summary["balances"]}
    # 150 km pour 90 € : trajet à 3 = 60 € (20 chacun), trajet seul de Loïc = 30 €.
    assert balances == {"Loïc": -5000, "Amandine": -2000, "Julien": 7000}
    transfers = {(t["from"]["name"], t["to"]["name"]): t["amount_cents"] for t in summary["settlements"]}
    assert transfers == {("Loïc", "Julien"): 5000, ("Amandine", "Julien"): 2000}
    assert summary["pending_trips"] == 0

    # Remboursement enregistré puis supprimé par son auteur.
    r = client.post(dev + "/entries", headers=loic,
                    json={"type": "payment", "from": people["Loïc"], "to": people["Julien"], "amount_cents": 5000})
    entry_id = r.json()["id"]
    balances = {b["name"]: b["cents"] for b in client.get(dev + "/summary", headers=loic).json()["balances"]}
    assert "Loïc" not in balances
    assert client.delete(dev + "/entries/%d" % entry_id, headers=julien).status_code == 403
    assert client.delete(dev + "/entries/%d" % entry_id, headers=loic).status_code == 204


def test_trajet_apres_le_plein_reste_en_attente(client, loic):
    device = make_device(client, loic)
    dev = "/api/devices/%s" % device["id"]
    box_sync(client, device, [trip(1, 10, "111")])
    me = client.get("/api/me", headers=loic).json()["person"]
    client.post(dev + "/entries", headers=loic, json={"type": "fuel", "amount_cents": 1000, "payer": me})
    box_sync(client, device, [trip(2, 20, "111")])
    summary = client.get(dev + "/summary", headers=loic).json()
    assert summary["pending_trips"] == 1 and summary["pending_km"] == 20


def test_personne_inconnue_refusee(client, loic):
    device = make_device(client, loic)
    r = client.post("/api/devices/%s/entries" % device["id"], headers=loic,
                    json={"type": "fuel", "amount_cents": 1000, "payer": "u:999"})
    assert r.status_code == 400


def test_relais_bluetooth_par_l_app(client, loic, julien):
    device = make_device(client, loic)
    r = client.post("/api/devices/%s/relay" % device["id"], headers=loic, json={"events": [trip(1, 12, "9")]})
    assert r.json()["acked_seq"] == 1
    r = client.post("/api/devices/%s/relay" % device["id"], headers=julien, json={"events": [trip(2, 12, "9")]})
    assert r.status_code == 404
