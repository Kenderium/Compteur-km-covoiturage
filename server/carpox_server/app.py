"""API du serveur CarpoX (FastAPI).

Lancer en local :  uvicorn carpox_server.main:app --reload
Variables d'environnement :
    CARPOX_DB           chemin de la base SQLite (défaut : carpox.sqlite3)
    CARPOX_INVITE_CODE  si défini, code demandé pour créer un compte
    CARPOX_APP_DIR      dossier de l'app web à servir (défaut : ../app)
    CARPOX_MAP_TILES    fond de carte des parcours, modèle d'URL {z}/{x}/{y}
                        (défaut : OpenStreetMap ; vide = parcours sans fond de carte)

Deux sortes d'accès pour les personnes :
- la session (connexion par mot de passe) : tout ce que l'app permet ;
- le jeton personnel (Home Assistant...) : lecture seule, révocable.
"""

import contextlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Annotated, List, Literal, Optional, Union
from urllib.parse import urlsplit

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi import Path as UrlPath
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from carpox_core.ledger import compute_ledger, settle
from carpox_core.costs import person_km
from carpox_core.fuel import fuel_status
from carpox_server import db, security

SESSION_DAYS = 30
MAX_LOGIN_FAILURES = 5
LOCKOUT_S = 15 * 60
MAX_BATCH = 200
MAX_TRACK_POINTS = 1000
MAX_API_TOKENS = 20
DEFAULT_MAP_TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"

# --- modèles ------------------------------------------------------------------

UID_PATTERN = r"^[0-9A-Za-z]{1,24}$"
PERSON_PATTERN = r"^(u:[0-9]+|b:[0-9A-Za-z]{1,24})$"


def Username():
    return Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")


def Uid():
    return Field(pattern=UID_PATTERN)


def Person():
    return Field(pattern=PERSON_PATTERN)


class RegisterIn(BaseModel):
    username: str = Username()
    password: str = Field(max_length=256)
    display_name: str = Field(min_length=1, max_length=32)
    invite_code: Optional[str] = None


class LoginIn(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=256)


class PasswordIn(BaseModel):
    old_password: str = Field(max_length=256)
    new_password: str = Field(max_length=256)


class DeviceIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class DeviceSettingsIn(BaseModel):
    """Réglages de la voiture par son propriétaire. Un champ absent reste tel quel,
    un champ à null est effacé."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=40)
    tank_l: Optional[float] = Field(default=None, gt=0, le=200)
    consumption_l_100km: Optional[float] = Field(default=None, ge=1, le=40)
    odometer_start_km: Optional[float] = Field(default=None, ge=0, le=2000000)


class ApiTokenIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class MemberIn(BaseModel):
    username: str = Field(max_length=64)


class BadgeIn(BaseModel):
    label: str = Field(min_length=1, max_length=16)
    username: Optional[str] = Field(default=None, max_length=64)


TrackPoint = Annotated[List[float], Field(min_length=2, max_length=2)]


class BoxEvent(BaseModel):
    seq: int = Field(ge=1)
    km: float = Field(ge=0, le=3000)
    start: Optional[int] = None
    end: Optional[int] = None
    gps_points: Optional[int] = None
    track: Optional[List[TrackPoint]] = Field(default=None, max_length=MAX_TRACK_POINTS)

    @field_validator("track")
    @classmethod
    def _valid_track(cls, track):
        for lat, lon in track or []:
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError("position GPS invalide")
        return track


class TripEvent(BoxEvent):
    """Trajet badgé : conducteur et passagers."""
    type: Literal["trip"]
    driver: str = Uid()
    passengers: List[Annotated[str, Uid()]] = Field(default_factory=list, max_length=12)
    temp_c: Optional[float] = None


class DriveEvent(BoxEvent):
    """Km roulés sans que personne n'ait badgé (le boîtier compte dès qu'il est allumé)."""
    type: Literal["drive"]


BoxEventIn = Annotated[Union[TripEvent, DriveEvent], Field(discriminator="type")]


class SyncIn(BaseModel):
    device_id: Optional[str] = None
    events: List[BoxEventIn] = Field(default_factory=list, max_length=MAX_BATCH)
    last_seq: Optional[int] = None


class FuelIn(BaseModel):
    type: Literal["fuel"]
    amount_cents: int = Field(gt=0, le=100000)
    payer: str = Person()
    distance_km: Optional[float] = Field(default=None, ge=0, le=5000)
    litres: Optional[float] = Field(default=None, gt=0, le=200)
    note: Optional[str] = Field(default=None, max_length=80)


class ExpenseIn(BaseModel):
    type: Literal["expense"]
    amount_cents: int = Field(gt=0, le=100000)
    payer: str = Person()
    shared_with: List[Annotated[str, Person()]] = Field(min_length=1, max_length=12)
    note: Optional[str] = Field(default=None, max_length=80)


class PaymentIn(BaseModel):
    type: Literal["payment"]
    amount_cents: int = Field(gt=0, le=100000)
    from_: str = Field(alias="from", pattern=PERSON_PATTERN)
    to: str = Person()
    note: Optional[str] = Field(default=None, max_length=80)


EntryIn = Annotated[Union[FuelIn, ExpenseIn, PaymentIn], Field(discriminator="type")]


# --- application -------------------------------------------------------------


def create_app(db_path=None, app_dir=None, invite_code=None, map_tiles=None):
    db_path = db_path or os.environ.get("CARPOX_DB", "carpox.sqlite3")
    if map_tiles is None:
        map_tiles = os.environ.get("CARPOX_MAP_TILES", DEFAULT_MAP_TILES)
    map_tiles = map_tiles.strip() or None
    tiles_origin = ""
    if map_tiles:
        parts = urlsplit(map_tiles)
        if parts.scheme != "https" or not parts.netloc:
            raise ValueError("CARPOX_MAP_TILES doit être une adresse https://")
        tiles_origin = " %s://%s" % (parts.scheme, parts.netloc)
    invite_code = invite_code if invite_code is not None else os.environ.get("CARPOX_INVITE_CODE") or None
    if app_dir is None:
        app_dir = os.environ.get("CARPOX_APP_DIR") or str(Path(__file__).resolve().parents[2] / "app")
    db.init(db_path).close()

    api = FastAPI(title="CarpoX", docs_url="/api/docs", openapi_url="/api/openapi.json")

    @api.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        if not request.url.path.startswith("/api/docs"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; img-src 'self' data:%s; style-src 'self'; script-src 'self'; "
                "connect-src 'self'; frame-ancestors 'none'" % tiles_origin)
        return response

    def get_db():
        conn = db.connect(db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _session_user(conn, token):
        return conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash = ? AND s.expires_at > ?",
            (security.token_hash(token), db.now())).fetchone()

    def current_user(authorization: Optional[str] = Header(default=None), conn=Depends(get_db)):
        """Session ouverte avec le mot de passe : lecture et écriture."""
        token = _bearer(authorization)
        row = _session_user(conn, token)
        if row is None:
            if token.startswith(security.API_TOKEN_PREFIX):
                raise HTTPException(403, "Ce jeton personnel est en lecture seule.")
            raise HTTPException(401, "Session expirée, reconnectez-vous.")
        return row

    def reader(authorization: Optional[str] = Header(default=None), conn=Depends(get_db)):
        """Session, ou jeton personnel en lecture seule (Home Assistant)."""
        token = _bearer(authorization)
        row = _session_user(conn, token)
        if row is not None:
            return {**dict(row), "via_api_token": False}
        api_token = conn.execute("SELECT id, user_id FROM api_tokens WHERE token_hash = ?",
                                 (security.token_hash(token),)).fetchone()
        if api_token is None:
            raise HTTPException(401, "Jeton inconnu ou révoqué.")
        conn.execute("UPDATE api_tokens SET last_used_at = ? WHERE id = ?", (db.now(), api_token["id"]))
        row = conn.execute("SELECT * FROM users WHERE id = ?", (api_token["user_id"],)).fetchone()
        return {**dict(row), "via_api_token": True}

    def _device_for(conn, device_id, user):
        row = conn.execute(
            "SELECT d.* FROM devices d LEFT JOIN device_members m ON m.device_id = d.id AND m.user_id = ? "
            "WHERE d.id = ? AND (d.owner_id = ? OR m.user_id IS NOT NULL)",
            (user["id"], device_id, user["id"])).fetchone()
        if row is None:
            raise HTTPException(404, "Voiture introuvable.")
        return row

    def member_device(device_id: str, user=Depends(current_user), conn=Depends(get_db)):
        return _device_for(conn, device_id, user)

    def readable_device(device_id: str, user=Depends(reader), conn=Depends(get_db)):
        return _device_for(conn, device_id, user)

    def owned_device(device=Depends(member_device), user=Depends(current_user)):
        if device["owner_id"] != user["id"]:
            raise HTTPException(403, "Réservé au propriétaire de la voiture.")
        return device

    # --- comptes ---------------------------------------------------------

    @api.post("/api/auth/register", status_code=201)
    def register(body: RegisterIn, conn=Depends(get_db)):
        if invite_code and body.invite_code != invite_code:
            raise HTTPException(403, "Code d'invitation incorrect.")
        problem = security.check_password_strength(body.password)
        if problem:
            raise HTTPException(400, problem)
        if body.password.lower() == body.username.lower():
            raise HTTPException(400, "Le mot de passe ne peut pas être le nom d'utilisateur.")
        try:
            cur = conn.execute(
                "INSERT INTO users (username, display_name, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (body.username, body.display_name.strip(), security.hash_password(body.password), db.now()))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Ce nom d'utilisateur est déjà pris.")
        return _new_session(conn, cur.lastrowid)

    @api.post("/api/auth/login")
    def login(body: LoginIn, conn=Depends(get_db)):
        user = conn.execute("SELECT * FROM users WHERE username = ?", (body.username,)).fetchone()
        if user is None:
            security.verify_password(body.password, security.DUMMY_HASH)
            raise HTTPException(401, "Identifiants incorrects.")
        if user["locked_until"] > db.now():
            raise HTTPException(429, "Trop d'essais. Réessayez dans quelques minutes.")
        if not security.verify_password(body.password, user["password_hash"]):
            failures = user["failed_logins"] + 1
            locked = db.now() + LOCKOUT_S if failures >= MAX_LOGIN_FAILURES else 0
            conn.execute("UPDATE users SET failed_logins = ?, locked_until = ? WHERE id = ?",
                         (0 if locked else failures, locked, user["id"]))
            raise HTTPException(401, "Identifiants incorrects.")
        conn.execute("UPDATE users SET failed_logins = 0, locked_until = 0 WHERE id = ?", (user["id"],))
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (db.now(),))
        return _new_session(conn, user["id"])

    @api.post("/api/auth/logout", status_code=204)
    def logout(authorization: Optional[str] = Header(default=None), conn=Depends(get_db)):
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (security.token_hash(_bearer(authorization)),))

    @api.get("/api/config")
    def public_config():
        """Réglages utiles à l'app avant connexion."""
        return {"map_tiles": map_tiles}

    @api.get("/api/me")
    def me(user=Depends(reader)):
        return {"id": user["id"], "username": user["username"], "display_name": user["display_name"],
                "person": "u:%d" % user["id"]}

    @api.post("/api/me/password", status_code=204)
    def change_password(body: PasswordIn, authorization: Optional[str] = Header(default=None),
                        user=Depends(current_user), conn=Depends(get_db)):
        if not security.verify_password(body.old_password, user["password_hash"]):
            raise HTTPException(401, "Ancien mot de passe incorrect.")
        problem = security.check_password_strength(body.new_password)
        if problem:
            raise HTTPException(400, problem)
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                     (security.hash_password(body.new_password), user["id"]))
        # Déconnecte les autres appareils.
        conn.execute("DELETE FROM sessions WHERE user_id = ? AND token_hash != ?",
                     (user["id"], security.token_hash(_bearer(authorization))))

    # --- jetons personnels (Home Assistant) ----------------------------------

    @api.get("/api/me/tokens")
    def list_api_tokens(user=Depends(current_user), conn=Depends(get_db)):
        return [dict(r) for r in conn.execute(
            "SELECT id, name, created_at, last_used_at FROM api_tokens WHERE user_id = ? ORDER BY id",
            (user["id"],))]

    @api.post("/api/me/tokens", status_code=201)
    def create_api_token(body: ApiTokenIn, user=Depends(current_user), conn=Depends(get_db)):
        count = conn.execute("SELECT COUNT(*) FROM api_tokens WHERE user_id = ?", (user["id"],)).fetchone()[0]
        if count >= MAX_API_TOKENS:
            raise HTTPException(400, "Trop de jetons. Révoquez ceux qui ne servent plus.")
        token = security.new_api_token()
        cur = conn.execute("INSERT INTO api_tokens (user_id, name, token_hash, created_at) VALUES (?, ?, ?, ?)",
                           (user["id"], body.name.strip(), security.token_hash(token), db.now()))
        return {"id": cur.lastrowid, "name": body.name.strip(), "token": token}

    @api.delete("/api/me/tokens/{token_id}", status_code=204)
    def revoke_api_token(token_id: int, user=Depends(current_user), conn=Depends(get_db)):
        cur = conn.execute("DELETE FROM api_tokens WHERE id = ? AND user_id = ?", (token_id, user["id"]))
        if cur.rowcount == 0:
            raise HTTPException(404, "Jeton introuvable.")

    # --- vue d'ensemble (Home Assistant, écran d'accueil) --------------------

    @api.get("/api/me/overview")
    def overview(user=Depends(reader), conn=Depends(get_db)):
        """Tout ce qui concerne ce compte, voiture par voiture, en un appel."""
        me_key = "u:%d" % user["id"]
        rows = conn.execute(
            "SELECT d.* FROM devices d JOIN device_members m ON m.device_id = d.id WHERE m.user_id = ? "
            "ORDER BY d.name", (user["id"],)).fetchall()
        cars = []
        totals = {"balance_cents": 0, "owes_cents": 0, "owed_cents": 0, "km": 0.0}
        for device in rows:
            car = _car_state(conn, device, user)
            mine = {
                "balance_cents": car["ledger"]["balances"].get(me_key, 0),
                "km": round(car["km_by_person"].get(me_key, 0.0), 1),
                "owes": [{"to": car["named"](t["to"]), "amount_cents": t["amount_cents"]}
                         for t in car["settlements"] if t["from"] == me_key],
                "owed": [{"from": car["named"](t["from"]), "amount_cents": t["amount_cents"]}
                         for t in car["settlements"] if t["to"] == me_key],
            }
            totals["balance_cents"] += mine["balance_cents"]
            totals["owes_cents"] += sum(t["amount_cents"] for t in mine["owes"])
            totals["owed_cents"] += sum(t["amount_cents"] for t in mine["owed"])
            totals["km"] += mine["km"]
            cars.append({
                "id": device["id"], "name": device["name"], "is_owner": device["owner_id"] == user["id"],
                "last_sync_at": device["last_sync_at"],
                "km": car["km"], "fuel": car["fuel"], "me": mine,
                "balances": car["balances"], "settlements": car["settlements_out"],
                "trips_count": car["trips_count"], "last_trip": car["last_trip"],
                "last_position": car["last_position"],
            })
        totals["km"] = round(totals["km"], 1)
        return {
            "user": {"id": user["id"], "username": user["username"], "display_name": user["display_name"],
                     "person": me_key},
            "generated_at": db.now(),
            "totals": totals,
            "cars": cars,
        }

    # --- voitures (boîtiers) --------------------------------------------

    @api.post("/api/devices", status_code=201)
    def create_device(body: DeviceIn, user=Depends(current_user), conn=Depends(get_db)):
        device_id = security.new_device_id()
        token = security.new_token()
        pin = security.new_ble_pin()
        conn.execute(
            "INSERT INTO devices (id, name, owner_id, token_hash, ble_pin, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (device_id, body.name.strip(), user["id"], security.token_hash(token), pin, db.now()))
        conn.execute("INSERT INTO device_members (device_id, user_id) VALUES (?, ?)", (device_id, user["id"]))
        return {"id": device_id, "name": body.name.strip(), "device_token": token, "ble_pin": pin}

    @api.get("/api/devices")
    def list_devices(user=Depends(reader), conn=Depends(get_db)):
        rows = conn.execute(
            "SELECT d.* FROM devices d JOIN device_members m ON m.device_id = d.id WHERE m.user_id = ? "
            "ORDER BY d.name", (user["id"],)).fetchall()
        return [_device_out(r, user) for r in rows]

    @api.get("/api/devices/{device_id}")
    def get_device(device=Depends(readable_device), user=Depends(reader), conn=Depends(get_db)):
        out = _device_out(device, user)
        out["members"] = [dict(r) for r in conn.execute(
            "SELECT u.id, u.username, u.display_name FROM device_members m JOIN users u ON u.id = m.user_id "
            "WHERE m.device_id = ? ORDER BY u.display_name", (device["id"],))]
        out["badges"] = [dict(r) for r in conn.execute(
            "SELECT b.uid, b.label, b.user_id, u.username FROM badges b LEFT JOIN users u ON u.id = b.user_id "
            "WHERE b.device_id = ? ORDER BY b.label", (device["id"],))]
        out["people"] = _people(conn, device["id"])
        return out

    @api.patch("/api/devices/{device_id}")
    def update_device(body: DeviceSettingsIn, device=Depends(owned_device), user=Depends(current_user),
                      conn=Depends(get_db)):
        changes = body.model_dump(exclude_unset=True)
        if "name" in changes:
            if changes["name"] is None or not changes["name"].strip():
                raise HTTPException(400, "La voiture doit garder un nom.")
            changes["name"] = changes["name"].strip()
        for column, value in changes.items():  # colonnes limitées aux champs du modèle
            conn.execute("UPDATE devices SET %s = ? WHERE id = ?" % column, (value, device["id"]))
        row = conn.execute("SELECT * FROM devices WHERE id = ?", (device["id"],)).fetchone()
        return _device_out(row, user)

    @api.post("/api/devices/{device_id}/token")
    def rotate_token(device=Depends(owned_device), conn=Depends(get_db)):
        token = security.new_token()
        conn.execute("UPDATE devices SET token_hash = ? WHERE id = ?", (security.token_hash(token), device["id"]))
        return {"device_token": token}

    @api.post("/api/devices/{device_id}/members", status_code=201)
    def add_member(body: MemberIn, device=Depends(owned_device), conn=Depends(get_db)):
        other = conn.execute("SELECT id FROM users WHERE username = ?", (body.username,)).fetchone()
        if other is None:
            raise HTTPException(404, "Utilisateur introuvable.")
        conn.execute("INSERT OR IGNORE INTO device_members (device_id, user_id) VALUES (?, ?)",
                     (device["id"], other["id"]))
        return {"ok": True}

    @api.delete("/api/devices/{device_id}/members/{user_id}", status_code=204)
    def remove_member(user_id: int, device=Depends(owned_device), conn=Depends(get_db)):
        if user_id == device["owner_id"]:
            raise HTTPException(400, "Le propriétaire ne peut pas être retiré.")
        conn.execute("DELETE FROM device_members WHERE device_id = ? AND user_id = ?", (device["id"], user_id))

    @api.put("/api/devices/{device_id}/badges/{uid}")
    def set_badge(body: BadgeIn, uid: str = UrlPath(pattern=UID_PATTERN), device=Depends(member_device), conn=Depends(get_db)):
        user_id = None
        if body.username:
            row = conn.execute(
                "SELECT u.id FROM users u JOIN device_members m ON m.user_id = u.id "
                "WHERE u.username = ? AND m.device_id = ?", (body.username, device["id"])).fetchone()
            if row is None:
                raise HTTPException(404, "Cette personne n'est pas membre de la voiture.")
            user_id = row["id"]
        conn.execute(
            "INSERT INTO badges (device_id, uid, label, user_id) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (device_id, uid) DO UPDATE SET label = excluded.label, user_id = excluded.user_id",
            (device["id"], uid, body.label.strip(), user_id))
        return {"ok": True}

    @api.delete("/api/devices/{device_id}/badges/{uid}", status_code=204)
    def delete_badge(uid: str, device=Depends(member_device), conn=Depends(get_db)):
        conn.execute("DELETE FROM badges WHERE device_id = ? AND uid = ?", (device["id"], uid))

    # --- synchronisation --------------------------------------------------

    @api.post("/api/device/sync")
    def device_sync(body: SyncIn, authorization: Optional[str] = Header(default=None), conn=Depends(get_db)):
        """Appelé par le boîtier en WiFi, authentifié par son jeton."""
        token = _bearer(authorization)
        device = conn.execute("SELECT * FROM devices WHERE token_hash = ?",
                              (security.token_hash(token),)).fetchone()
        if device is None or (body.device_id and body.device_id != device["id"]):
            raise HTTPException(401, "Boîtier inconnu.")
        return _ingest(conn, device, body.events, None)

    @api.post("/api/devices/{device_id}/relay")
    def relay_sync(body: SyncIn, device=Depends(member_device), user=Depends(current_user), conn=Depends(get_db)):
        """Même chose, mais relayé par l'app depuis le Bluetooth."""
        return _ingest(conn, device, body.events, user["id"])

    # --- pleins, frais, remboursements -----------------------------------

    @api.post("/api/devices/{device_id}/entries", status_code=201)
    def add_entry(body: EntryIn = Body(), device=Depends(member_device), user=Depends(current_user), conn=Depends(get_db)):
        entry = body.model_dump(by_alias=True, exclude_none=True)
        people = {p["key"] for p in _people(conn, device["id"])}
        refs = [entry.get("payer"), entry.get("from"), entry.get("to")] + entry.get("shared_with", [])
        for ref in refs:
            if ref is not None and ref not in people:
                raise HTTPException(400, "Personne inconnue pour cette voiture : %s" % ref)
        with _tx(conn):
            last = conn.execute("SELECT COALESCE(MAX(seq), 0) FROM events WHERE device_id = ?",
                                (device["id"],)).fetchone()[0]
            cur = conn.execute(
                "INSERT INTO events (device_id, source, seq, order_seq, order_sub, type, payload, created_by, "
                "created_at) VALUES (?, 'app', NULL, ?, 1, ?, ?, ?, ?)",
                (device["id"], last, entry["type"], json.dumps(entry), user["id"], db.now()))
        return {"id": cur.lastrowid}

    @api.delete("/api/devices/{device_id}/entries/{entry_id}", status_code=204)
    def delete_entry(entry_id: int, device=Depends(member_device), user=Depends(current_user),
                     conn=Depends(get_db)):
        row = conn.execute("SELECT * FROM events WHERE id = ? AND device_id = ? AND source = 'app'",
                           (entry_id, device["id"])).fetchone()
        if row is None:
            raise HTTPException(404, "Entrée introuvable.")
        if row["created_by"] != user["id"] and device["owner_id"] != user["id"]:
            raise HTTPException(403, "Seul l'auteur ou le propriétaire peut supprimer cette entrée.")
        conn.execute("DELETE FROM events WHERE id = ?", (entry_id,))

    @api.get("/api/devices/{device_id}/events")
    def list_events(limit: int = 100, device=Depends(readable_device), conn=Depends(get_db)):
        limit = max(1, min(limit, 500))
        names = _names(conn, device["id"])
        rows = conn.execute(
            "SELECT * FROM events WHERE device_id = ? ORDER BY order_seq DESC, order_sub DESC, id DESC LIMIT ?",
            (device["id"], limit)).fetchall()
        return [_event_out(r, names, _resolver(conn, device["id"])) for r in rows]

    @api.get("/api/devices/{device_id}/summary")
    def summary(device=Depends(readable_device), conn=Depends(get_db)):
        car = _car_state(conn, device)
        return {
            "balances": car["balances"],
            "settlements": car["settlements_out"],
            "pending_km": round(sum(t["km"] for t in car["ledger"]["pending_trips"]), 1),
            "pending_trips": len(car["ledger"]["pending_trips"]),
            "pending_untracked_km": round(car["ledger"]["pending_drive_km"], 1),
            "km_by_person": sorted(({**car["named"](k), "km": round(v, 1)} for k, v in car["km_by_person"].items()),
                                   key=lambda p: -p["km"]),
            "total_km": car["km"]["tracked"],
            "km": car["km"],
            "fuel": car["fuel"],
        }

    # --- historique des trajets et parcours -------------------------------

    @api.get("/api/devices/{device_id}/trips")
    def list_trips(limit: int = 50, before: Optional[int] = None, device=Depends(readable_device),
                   user=Depends(reader), conn=Depends(get_db)):
        """Trajets badgés et km sans badge, du plus récent au plus ancien (sans les parcours)."""
        limit = max(1, min(limit, 200))
        names = _names(conn, device["id"])
        resolve = _resolver(conn, device["id"])
        rows = conn.execute(
            "SELECT * FROM events WHERE device_id = ? AND type IN ('trip', 'drive') AND order_seq < ? "
            "ORDER BY order_seq DESC LIMIT ?",
            (device["id"], before if before is not None else 2**62, limit)).fetchall()
        return [_trip_out(r, names, resolve, device, user) for r in rows]

    @api.get("/api/devices/{device_id}/trips/{event_id}")
    def get_trip(event_id: int, device=Depends(readable_device), user=Depends(reader), conn=Depends(get_db)):
        """Un trajet avec son parcours GPS (liste de [lat, lon]).

        Le parcours n'est montré qu'au propriétaire et aux personnes à bord."""
        row = conn.execute("SELECT * FROM events WHERE id = ? AND device_id = ? AND type IN ('trip', 'drive')",
                           (event_id, device["id"])).fetchone()
        if row is None:
            raise HTTPException(404, "Trajet introuvable.")
        resolve = _resolver(conn, device["id"])
        out = _trip_out(row, _names(conn, device["id"]), resolve, device, user)
        out["track"] = (json.loads(row["payload"]).get("track") or []) if out["track_visible"] else []
        return out

    # --- app web ------------------------------------------------------------

    if app_dir and Path(app_dir).is_dir():
        api.mount("/", StaticFiles(directory=app_dir, html=True), name="app")

    return api


# --- fonctions internes ---------------------------------------------------------


def _bearer(authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentification requise.")
    return authorization[7:].strip()


def _new_session(conn, user_id):
    token = security.new_token()
    expires = db.now() + SESSION_DAYS * 86400
    conn.execute("INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                 (security.token_hash(token), user_id, db.now(), expires))
    return {"token": token, "expires_at": expires}


@contextlib.contextmanager
def _tx(conn):
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def _device_out(row, user):
    out = {"id": row["id"], "name": row["name"], "is_owner": row["owner_id"] == user["id"],
           "last_sync_at": row["last_sync_at"],
           "settings": {"tank_l": row["tank_l"], "consumption_l_100km": row["consumption_l_100km"],
                        "odometer_start_km": row["odometer_start_km"]}}
    # Le code Bluetooth ne sert qu'à l'app : un jeton en lecture seule ne le voit pas.
    if not (isinstance(user, dict) and user.get("via_api_token")):
        out["ble_pin"] = row["ble_pin"]
    return out


def _round(value, digits=1):
    return None if value is None else round(value, digits)


def _can_see_track(device, user, event):
    """Un parcours dit où les gens sont allés : seuls le propriétaire de la voiture
    et les personnes à bord le voient. Les km sans badge : le propriétaire seul."""
    if device["owner_id"] == user["id"]:
        return True
    if event["type"] != "trip":
        return False
    return "u:%d" % user["id"] in [event["driver"]] + event.get("passengers", [])


def _car_state(conn, device, user=None):
    """Soldes, km et carburant d'une voiture : ce que montrent l'app et Home Assistant."""
    resolve = _resolver(conn, device["id"])
    names = _names(conn, device["id"])
    rows = _ordered_events(conn, device["id"])
    events = [_resolved_event(r, resolve) for r in rows]
    ledger = compute_ledger(events)
    trips = [e for e in events if e["type"] == "trip"]
    tracked = sum(e["km"] for e in trips)
    untracked = sum(e["km"] for e in events if e["type"] == "drive")
    fuel = fuel_status(events, device["tank_l"], device["consumption_l_100km"])
    settlements = settle(ledger["balances"])

    def named(key):
        return {"key": key, "name": names.get(key, key)}

    last_fill = None
    for row, e in zip(rows, events):
        if e is fuel["last_fill"]:
            last_fill = {"at": row["created_at"], "litres": e.get("litres"), "amount_cents": e.get("amount_cents")}

    last_trip = last_position = None
    count = 0
    for row, e in zip(reversed(rows), reversed(events)):
        if e["type"] not in ("trip", "drive"):
            continue
        count += 1
        if last_trip is None:
            last_trip = _trip_out(row, names, resolve)
        if last_position is None and e.get("track") and user is not None and _can_see_track(device, user, e):
            lat, lon = e["track"][-1]
            last_position = {"lat": lat, "lon": lon, "at": e.get("end") or row["created_at"]}

    total = tracked + untracked
    return {
        "ledger": ledger,
        "named": named,
        "settlements": settlements,
        "balances": sorted(({**named(k), "cents": v} for k, v in ledger["balances"].items()),
                           key=lambda b: b["cents"]),
        "settlements_out": [{"from": named(t["from"]), "to": named(t["to"]), "amount_cents": t["amount_cents"]}
                            for t in settlements],
        "km_by_person": person_km(trips),
        "km": {
            "total": round(total, 1),
            "tracked": round(tracked, 1),
            "untracked": round(untracked, 1),
            "since_fill": round(fuel["km_since_fill"], 1),
            "odometer": _round(device["odometer_start_km"] + total if device["odometer_start_km"] is not None
                               else None, 0),
        },
        "fuel": {
            "tank_l": device["tank_l"],
            "consumption_l_100km": _round(fuel["consumption_l_100km"], 2),
            "consumption_source": fuel["consumption_source"],
            "measured_l_100km": _round(fuel["measured_l_100km"], 2),
            "remaining_l": _round(fuel["remaining_l"]),
            "remaining_pct": _round(fuel["remaining_pct"], 0),
            "range_km": _round(fuel["range_km"], 0),
            "last_fill": last_fill,
        },
        "trips_count": count,
        "last_trip": last_trip,
        "last_position": last_position,
    }


def _ingest(conn, device, events, user_id):
    """Enregistre les trajets reçus. Idempotent : un `seq` déjà connu est ignoré."""
    with _tx(conn):
        for e in events:
            payload = e.model_dump(exclude_none=True)
            conn.execute(
                "INSERT OR IGNORE INTO events (device_id, source, seq, order_seq, order_sub, type, payload, "
                "created_by, created_at) VALUES (?, 'device', ?, ?, 0, ?, ?, ?, ?)",
                (device["id"], e.seq, e.seq, e.type, json.dumps(payload), user_id, db.now()))
        conn.execute("UPDATE devices SET last_sync_at = ? WHERE id = ?", (db.now(), device["id"]))
        acked = conn.execute("SELECT COALESCE(MAX(seq), 0) FROM events WHERE device_id = ?",
                             (device["id"],)).fetchone()[0]
    badges = {r["uid"]: r["label"] for r in conn.execute(
        "SELECT uid, label FROM badges WHERE device_id = ?", (device["id"],))}
    return {"acked_seq": acked, "badges": badges, "server_time": db.now()}


def _resolver(conn, device_id):
    """Identifiant de personne : un badge lié à un compte compte comme ce compte."""
    links = {r["uid"]: r["user_id"] for r in conn.execute(
        "SELECT uid, user_id FROM badges WHERE device_id = ?", (device_id,))}

    def resolve(ref):
        if ref.startswith("b:"):
            uid = ref[2:]
        elif ref.startswith("u:"):
            return ref
        else:
            uid = ref  # uid brut venant du boîtier
        user_id = links.get(uid)
        return "u:%d" % user_id if user_id else "b:" + uid

    return resolve


def _people(conn, device_id):
    people = {}
    for r in conn.execute(
            "SELECT u.id, u.display_name FROM device_members m JOIN users u ON u.id = m.user_id "
            "WHERE m.device_id = ?", (device_id,)):
        people["u:%d" % r["id"]] = r["display_name"]
    for r in conn.execute("SELECT uid, label, user_id FROM badges WHERE device_id = ?", (device_id,)):
        if not r["user_id"]:
            people["b:" + r["uid"]] = r["label"]
    # Badges vus dans les trajets mais pas encore nommés.
    resolve = _resolver(conn, device_id)
    for r in conn.execute("SELECT payload FROM events WHERE device_id = ? AND type = 'trip'", (device_id,)):
        p = json.loads(r["payload"])
        for uid in [p["driver"]] + p.get("passengers", []):
            key = resolve(uid)
            if key not in people:
                people[key] = "Badge " + uid[-4:]
    return [{"key": k, "name": v} for k, v in sorted(people.items(), key=lambda kv: kv[1].lower())]


def _names(conn, device_id):
    return {p["key"]: p["name"] for p in _people(conn, device_id)}


def _ordered_events(conn, device_id):
    return conn.execute("SELECT * FROM events WHERE device_id = ? ORDER BY order_seq, order_sub, id",
                        (device_id,)).fetchall()


def _resolved_event(row, resolve):
    e = json.loads(row["payload"])
    e["type"] = row["type"]
    if e["type"] == "trip":
        e["driver"] = resolve(e["driver"])
        e["passengers"] = [resolve(p) for p in e.get("passengers", [])]
    for key in ("payer", "from", "to"):
        if key in e:
            e[key] = resolve(e[key])
    if "shared_with" in e:
        e["shared_with"] = [resolve(p) for p in e["shared_with"]]
    return e


def _event_out(row, names, resolve):
    e = _resolved_event(row, resolve)
    out = {"id": row["id"], "source": row["source"], "seq": row["seq"], "type": row["type"],
           "created_at": row["created_at"], "data": e}

    def name(key):
        return names.get(key, key)

    if "track" in e:
        out["data"]["track_points"] = len(e.pop("track"))
    if e["type"] == "trip":
        out["label"] = "%s + %d" % (name(e["driver"]), len(e.get("passengers", [])))
        out["people"] = [name(e["driver"])] + [name(p) for p in e.get("passengers", [])]
    elif e["type"] == "drive":
        out["label"] = "Sans badge"
        out["people"] = []
    elif e["type"] in ("fuel", "expense"):
        out["label"] = name(e["payer"])
    elif e["type"] == "payment":
        out["label"] = "%s → %s" % (name(e["from"]), name(e["to"]))
    return out



def _trip_out(row, names, resolve, device=None, user=None):
    """Résumé d'un trajet (badgé ou non) pour l'historique, sans le parcours."""
    e = _resolved_event(row, resolve)
    people = []
    if e["type"] == "trip":
        people = [names.get(k, k) for k in [e["driver"]] + e.get("passengers", [])]
    out = {"id": row["id"], "type": e["type"], "seq": row["seq"], "km": round(e["km"], 2),
           "start": e.get("start"), "end": e.get("end"), "received_at": row["created_at"],
           "people": people, "track_points": len(e.get("track") or [])}
    if user is not None:
        out["track_visible"] = _can_see_track(device, user, e)
    return out
