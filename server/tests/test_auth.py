import sqlite3

from carpox_server import security
from carpox_server.app import create_app
from fastapi.testclient import TestClient

from conftest import register


def test_hash_mot_de_passe():
    h = security.hash_password("un mot de passe")
    assert h.startswith("scrypt$") and "un mot de passe" not in h
    assert security.verify_password("un mot de passe", h)
    assert not security.verify_password("autre chose", h)
    assert security.hash_password("un mot de passe") != h  # sel différent


def test_inscription_connexion_deconnexion(client):
    headers = register(client, "loic", "Loïc")
    assert client.get("/api/me", headers=headers).json()["display_name"] == "Loïc"
    r = client.post("/api/auth/login", json={"username": "LOIC", "password": "correct-horse-battery"})
    assert r.status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/me", headers=headers).status_code == 401


def test_mot_de_passe_trop_faible_et_doublon(client):
    r = client.post("/api/auth/register", json={"username": "a1b", "password": "court", "display_name": "A"})
    assert r.status_code == 400
    register(client, "loic")
    r = client.post("/api/auth/register",
                    json={"username": "Loic", "password": "correct-horse-battery", "display_name": "X"})
    assert r.status_code == 409


def test_blocage_apres_trop_d_essais(client):
    register(client, "loic")
    for _ in range(5):
        r = client.post("/api/auth/login", json={"username": "loic", "password": "mauvais-mot-de-passe"})
        assert r.status_code == 401
    r = client.post("/api/auth/login", json={"username": "loic", "password": "correct-horse-battery"})
    assert r.status_code == 429


def test_utilisateur_inconnu_meme_message(client):
    r = client.post("/api/auth/login", json={"username": "personne", "password": "x" * 12})
    assert r.status_code == 401 and r.json()["detail"] == "Identifiants incorrects."


def test_la_base_ne_contient_ni_mot_de_passe_ni_jeton(client, tmp_path):
    headers = register(client, "loic")
    token = headers["Authorization"][7:]
    conn = sqlite3.connect(tmp_path / "test.sqlite3")
    dump = "\n".join(conn.iterdump())
    assert "correct-horse-battery" not in dump
    assert token not in dump


def test_changement_de_mot_de_passe_deconnecte_les_autres(client):
    a = register(client, "loic")
    b = {"Authorization": "Bearer " + client.post(
        "/api/auth/login", json={"username": "loic", "password": "correct-horse-battery"}).json()["token"]}
    r = client.post("/api/me/password", headers=a,
                    json={"old_password": "correct-horse-battery", "new_password": "un-nouveau-secret"})
    assert r.status_code == 204
    assert client.get("/api/me", headers=a).status_code == 200
    assert client.get("/api/me", headers=b).status_code == 401


def test_code_d_invitation(tmp_path):
    c = TestClient(create_app(str(tmp_path / "db.sqlite3"), app_dir="", invite_code="covoit2026"))
    body = {"username": "loic", "password": "correct-horse-battery", "display_name": "L"}
    assert c.post("/api/auth/register", json=body).status_code == 403
    assert c.post("/api/auth/register", json={**body, "invite_code": "covoit2026"}).status_code == 201


def test_en_tetes_de_securite(client):
    r = client.get("/api/me")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
