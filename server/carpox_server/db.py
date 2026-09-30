"""Base de données SQLite (un seul fichier, rien à installer sur le serveur)."""

import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    failed_logins INTEGER NOT NULL DEFAULT 0,
    locked_until INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);

-- Un boîtier = une voiture partagée par un groupe de personnes.
CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    token_hash TEXT NOT NULL,
    ble_pin TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    last_sync_at INTEGER
);

CREATE TABLE IF NOT EXISTS device_members (
    device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (device_id, user_id)
);

-- Badge RFID : un nom (invité) et éventuellement un compte.
CREATE TABLE IF NOT EXISTS badges (
    device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    uid TEXT NOT NULL,
    label TEXT NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    PRIMARY KEY (device_id, uid)
);

-- Tous les événements, dans l'ordre où ils comptent :
--   boîtier : (seq, 0)            trajets envoyés par le boîtier
--   app     : (dernier seq, 1)    pleins, frais, remboursements saisis dans l'app
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    source TEXT NOT NULL CHECK (source IN ('device', 'app')),
    seq INTEGER,
    order_seq INTEGER NOT NULL,
    order_sub INTEGER NOT NULL,
    type TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at INTEGER NOT NULL,
    UNIQUE (device_id, seq)
);
CREATE INDEX IF NOT EXISTS events_order ON events (device_id, order_seq, order_sub, id);
"""


def connect(path):
    conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init(path):
    conn = connect(path)
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


def now():
    return int(time.time())
