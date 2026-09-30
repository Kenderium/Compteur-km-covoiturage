"""API du serveur CarpoX (FastAPI).

Lancer en local :  uvicorn carpox_server.main:app --reload
Variables d'environnement :
    CARPOX_DB           chemin de la base SQLite (défaut : carpox.sqlite3)
    CARPOX_INVITE_CODE  si défini, code demandé pour créer un compte
    CARPOX_APP_DIR      dossier de l'app web à servir (défaut : ../app)
"""

import contextlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Annotated, List, Literal, Optional, Union

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi import Path as UrlPath
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from carpox_core.ledger import compute_ledger, settle
from carpox_core.costs import person_km
from carpox_server import db, security

SESSION_DAYS = 30
MAX_LOGIN_FAILURES = 5
LOCKOUT_S = 15 * 60
MAX_BATCH = 200

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


class MemberIn(BaseModel):
    username: str = Field(max_length=64)


class BadgeIn(BaseModel):
    label: str = Field(min_length=1, max_length=16)
    username: Optional[str] = Field(default=None, max_length=64)


class TripEvent(BaseModel):
    seq: int = Field(ge=1)
    type: Literal["trip"]
    km: float = Field(ge=0, le=3000)
    driver: str = Uid()
    passengers: List[Annotated[str, Uid()]] = Field(default_factory=list, max_length=12)
    start: Optional[int] = None
    end: Optional[int] = None
    temp_c: Optional[float] = None
    gps_points: Optional[int] = None


class SyncIn(BaseModel):
    device_id: Optional[str] = None
    events: List[TripEvent] = Field(default_factory=list, max_length=MAX_BATCH)
    last_seq: Optional[int] = None


class FuelIn(BaseModel):
    type: Literal["fuel"]
    amount_cents: int = Field(gt=0, le=100000)
    payer: str = Person()
    distance_km: Optional[float] = Field(default=None, ge=0, le=5000)
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


def create_app(db_path=None, app_dir=None, invite_code=None):
    db_path = db_path or os.environ.get("CARPOX_DB", "carpox.sqlite3")
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
                "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
                "connect-src 'self'; frame-ancestors 'none'")
        return response

    def get_db():
        conn = db.connect(db_path)
        try:
            yield conn
        finally:
            conn.close()

    def current_user(authorization: Optional[str] = Header(default=None), conn=Depends(get_db)):
        token = _bearer(authorization)
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash = ? AND s.expires_at > ?",
            (security.token_hash(token), db.now())).fetchone()
        if row is None:
            raise HTTPException(401, "Session expirée, reconnectez-vous.")
        return row

    def member_device(device_id: str, user=Depends(current_user), conn=Depends(get_db)):
        row = conn.execute(
            "SELECT d.* FROM devices d LEFT JOIN device_members m ON m.device_id = d.id AND m.user_id = ? "
            "WHERE d.id = ? AND (d.owner_id = ? OR m.user_id IS NOT NULL)",
            (user["id"], device_id, user["id"])).fetchone()
        if row is None:
            raise HTTPException(404, "Voiture introuvable.")
        return row

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

    @api.get("/api/me")
    def me(user=Depends(current_user)):
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
    def list_devices(user=Depends(current_user), conn=Depends(get_db)):
        rows = conn.execute(
            "SELECT d.* FROM devices d JOIN device_members m ON m.device_id = d.id WHERE m.user_id = ? "
            "ORDER BY d.name", (user["id"],)).fetchall()
        return [_device_out(r, user) for r in rows]

    @api.get("/api/devices/{device_id}")
    def get_device(device=Depends(member_device), user=Depends(current_user), conn=Depends(get_db)):
        out = _device_out(device, user)
        out["members"] = [dict(r) for r in conn.execute(
            "SELECT u.id, u.username, u.display_name FROM device_members m JOIN users u ON u.id = m.user_id "
            "WHERE m.device_id = ? ORDER BY u.display_name", (device["id"],))]
        out["badges"] = [dict(r) for r in conn.execute(
            "SELECT b.uid, b.label, b.user_id, u.username FROM badges b LEFT JOIN users u ON u.id = b.user_id "
            "WHERE b.device_id = ? ORDER BY b.label", (device["id"],))]
        out["people"] = _people(conn, device["id"])
        return out

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
    def list_events(limit: int = 100, device=Depends(member_device), conn=Depends(get_db)):
        limit = max(1, min(limit, 500))
        names = _names(conn, device["id"])
        rows = conn.execute(
            "SELECT * FROM events WHERE device_id = ? ORDER BY order_seq DESC, order_sub DESC, id DESC LIMIT ?",
            (device["id"], limit)).fetchall()
        return [_event_out(r, names, _resolver(conn, device["id"])) for r in rows]

    @api.get("/api/devices/{device_id}/summary")
    def summary(device=Depends(member_device), conn=Depends(get_db)):
        resolve = _resolver(conn, device["id"])
        names = _names(conn, device["id"])
        events = [_resolved_event(r, resolve) for r in _ordered_events(conn, device["id"])]
        ledger = compute_ledger(events)
        trips = [e for e in events if e["type"] == "trip"]

        def named(key):
            return {"key": key, "name": names.get(key, key)}

        return {
            "balances": sorted(({**named(k), "cents": v} for k, v in ledger["balances"].items()),
                               key=lambda b: b["cents"]),
            "settlements": [{"from": named(t["from"]), "to": named(t["to"]), "amount_cents": t["amount_cents"]}
                            for t in settle(ledger["balances"])],
            "pending_km": round(sum(t["km"] for t in ledger["pending_trips"]), 1),
            "pending_trips": len(ledger["pending_trips"]),
            "km_by_person": sorted(({**named(k), "km": round(v, 1)} for k, v in person_km(trips).items()),
                                   key=lambda p: -p["km"]),
            "total_km": round(sum(t["km"] for t in trips), 1),
        }

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
           "ble_pin": row["ble_pin"], "last_sync_at": row["last_sync_at"]}
    return out


def _ingest(conn, device, events, user_id):
    """Enregistre les trajets reçus. Idempotent : un `seq` déjà connu est ignoré."""
    with _tx(conn):
        for e in events:
            payload = e.model_dump(exclude_none=True)
            conn.execute(
                "INSERT OR IGNORE INTO events (device_id, source, seq, order_seq, order_sub, type, payload, "
                "created_by, created_at) VALUES (?, 'device', ?, ?, 0, 'trip', ?, ?, ?)",
                (device["id"], e.seq, e.seq, json.dumps(payload), user_id, db.now()))
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

    if e["type"] == "trip":
        out["label"] = "%s + %d" % (name(e["driver"]), len(e.get("passengers", [])))
        out["people"] = [name(e["driver"])] + [name(p) for p in e.get("passengers", [])]
    elif e["type"] in ("fuel", "expense"):
        out["label"] = name(e["payer"])
    elif e["type"] == "payment":
        out["label"] = "%s → %s" % (name(e["from"]), name(e["to"]))
    return out

