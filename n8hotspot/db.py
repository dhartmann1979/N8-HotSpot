"""
One SQLite database holds everything: settings, users, sessions, audit log,
heard calls (last heard + statistics) and the DMR ID list.
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable, List

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,            -- JSON
    updated_at REAL NOT NULL,
    updated_by TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'viewer',   -- admin | viewer
    display_name  TEXT NOT NULL DEFAULT '',
    disabled      INTEGER NOT NULL DEFAULT 0,
    default_pw    INTEGER NOT NULL DEFAULT 0,       -- still the factory password
    created_at    REAL NOT NULL,
    last_login    REAL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    ip         TEXT NOT NULL DEFAULT '',
    user_agent TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS audit (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       REAL NOT NULL,
    action   TEXT NOT NULL,
    username TEXT NOT NULL DEFAULT '',
    detail   TEXT NOT NULL DEFAULT '',
    ip       TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS calls (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        REAL NOT NULL,                 -- start of the call
    end_ts    REAL,
    source    TEXT NOT NULL,                 -- rf | network
    slot      INTEGER NOT NULL,
    src_id    INTEGER,
    callsign  TEXT NOT NULL DEFAULT '',
    dst_id    INTEGER,
    grp       INTEGER NOT NULL DEFAULT 1,
    is_data   INTEGER NOT NULL DEFAULT 0,
    duration  REAL NOT NULL DEFAULT 0,
    ber       REAL,
    loss      REAL,
    rssi      INTEGER,
    result    TEXT NOT NULL DEFAULT 'end'    -- end | lost | timeout
);
CREATE INDEX IF NOT EXISTS calls_ts ON calls(ts);
CREATE TABLE IF NOT EXISTS dmrids (
    id       INTEGER PRIMARY KEY,
    callsign TEXT NOT NULL,
    name     TEXT NOT NULL DEFAULT '',
    city     TEXT NOT NULL DEFAULT '',
    country  TEXT NOT NULL DEFAULT ''
);
"""


class DB:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False, isolation_level=None, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.executescript(SCHEMA)

    def q(self, sql: str, args: Iterable[Any] = ()) -> List[sqlite3.Row]:
        with self.lock:
            return self.conn.execute(sql, tuple(args)).fetchall()

    def x(self, sql: str, args: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self.lock:
            return self.conn.execute(sql, tuple(args))

    def many(self, sql: str, rows: Iterable[Iterable[Any]]) -> None:
        with self.lock:
            self.conn.execute("BEGIN")
            try:
                self.conn.executemany(sql, rows)
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise
