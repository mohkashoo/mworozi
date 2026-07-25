"""Shared SQLite database layer — used by app.py (dashboard) and run.py (tracking server + watchdog)."""

import os
import sqlite3
import threading

DB_PATH = os.environ.get("EMBER_DB", "ember.db")
_lock = threading.Lock()

_conn: sqlite3.Connection | None = None


def _init():
    global _conn
    if _conn is not None:
        return
    with _lock:
        if _conn is not None:
            return
        _conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA busy_timeout=30000")
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS events ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "timestamp TEXT NOT NULL,"
            "type TEXT NOT NULL,"
            "target TEXT,"
            "ip TEXT DEFAULT '',"
            "ua TEXT DEFAULT ''"
            ")"
        )
        _conn.commit()


def insert(ts, ev_type, target, ip="", ua=""):
    _init()
    with _lock:
        _conn.execute(
            "INSERT INTO events (timestamp, type, target, ip, ua) VALUES (?, ?, ?, ?, ?)",
            (ts, ev_type, target, ip, ua),
        )
        _conn.commit()


def query(limit=500):
    _init()
    with _lock:
        rows = _conn.execute(
            "SELECT timestamp, type, target, ip, ua FROM events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [(r[0], r[1], r[2], r[3], r[4]) for r in rows]


def count():
    _init()
    with _lock:
        return _conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]


def count_by_type(ev_type):
    _init()
    with _lock:
        return _conn.execute("SELECT COUNT(*) FROM events WHERE type=?", (ev_type,)).fetchone()[0]


def clear():
    _init()
    with _lock:
        _conn.execute("DELETE FROM events")
        _conn.commit()
