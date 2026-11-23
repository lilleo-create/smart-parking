import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def database(path):
    db = sqlite3.connect(path, timeout=5)
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize(path, legacy):
    with database(path) as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS layout (
                id INTEGER PRIMARY KEY CHECK (id = 1), revision INTEGER NOT NULL,
                next_id INTEGER NOT NULL, spaces TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS space_numbers (
                space_id INTEGER PRIMARY KEY,
                number INTEGER NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT, first_seen REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS occupancy (
                space_id INTEGER PRIMARY KEY, vehicle_id INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS outbox (
                id INTEGER PRIMARY KEY, payload TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0
            );
        """)
        if not db.execute("SELECT 1 FROM layout").fetchone():
            polygons = json.loads(legacy.read_text()) if legacy.exists() else {}
            spaces = {i: points for i, points in enumerate(polygons.values(), 1)}
            db.execute("INSERT OR IGNORE INTO layout VALUES (1, 0, ?, ?)",
                       (len(spaces) + 1, json.dumps(spaces)))


def layout(db):
    revision, next_id, spaces = db.execute(
        "SELECT revision, next_id, spaces FROM layout WHERE id=1"
    ).fetchone()
    return revision, next_id, json.loads(spaces)


def space_numbers(db):
    return dict(db.execute("SELECT space_id, number FROM space_numbers"))


def occupancies(db):
    return dict(db.execute("SELECT space_id, vehicle_id FROM occupancy"))


def new_vehicle(db):
    return db.execute("INSERT INTO vehicles(first_seen) VALUES (?)", (time.time(),)).lastrowid


def set_occupant(db, space, previous, current):
    if previous == current:
        return
    if previous is not None:
        enqueue(db, "space.freed", space, previous)
    if current is None:
        db.execute("DELETE FROM occupancy WHERE space_id=?", (space,))
    else:
        db.execute("INSERT OR REPLACE INTO occupancy VALUES (?, ?)", (space, current))
        enqueue(db, "space.occupied", space, current)


def enqueue(db, event_type, space, vehicle):
    event = {
        "event_id": str(uuid.uuid4()),
        "type": event_type,
        "space_id": space,
        "vehicle_id": vehicle,
        "occurred_at": time.time(),
    }
    db.execute("INSERT INTO outbox(payload) VALUES (?)", (json.dumps(event),))


DB_PATH = Path("parking.sqlite3")
