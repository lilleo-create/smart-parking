import argparse
import hmac
import json
import mimetypes
import os
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from parking_plan import spatial_plan


LIVE_ID = "open-lot"
SNAPSHOT_TTL = 15
MAX_BODY = 64 * 1024
PARKINGS = [
    (LIVE_ID, "Парковка на макете", "Камера Raspberry Pi", "Москва, университетский макет", 55.769, 37.589),
    ("courtyard", "Двор жилого комплекса", "Придомовая парковка", "Москва, демоадрес 2", 55.758, 37.599),
    ("business", "Парковка бизнес-центра", "Корпоративная парковка", "Москва, демоадрес 3", 55.765, 37.616),
]
DEMO_FREE = {
    "courtyard": {"A2", "B2", "D1", "F1", "G2"},
    "business": {"A1", "A2", "A3", "B3", "C2", "D3", "E1", "F2", "G3", "H2"},
}


def iso_time(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec="milliseconds")


def make_spot(spot_id, label, index, row_size):
    row = index // row_size
    return {
        "id": spot_id,
        "label": label,
        "section": str(row // 2 + 1),
        "row": chr(ord("A") + row) if row < 26 else str(row + 1),
        "position": index % row_size + 1,
    }


def demo_spots():
    return [
        make_spot(label, label, index, 3)
        for index, label in enumerate(f"{row}{col}" for row in "ABCDEFGH" for col in range(1, 4))
    ]


class SnapshotStore:
    def __init__(self, path):
        self.path = path
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS snapshot (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    observed_at REAL NOT NULL,
                    spots TEXT NOT NULL
                )
            """)

    def read(self):
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute("SELECT observed_at, spots FROM snapshot WHERE id = 1").fetchone()
        return (row[0], json.loads(row[1])) if row else (0, [])

    def write(self, observed_at, spots):
        with closing(sqlite3.connect(self.path)) as db, db:
            result = db.execute("""
                INSERT INTO snapshot VALUES (1, ?, ?)
                ON CONFLICT (id) DO UPDATE SET observed_at = excluded.observed_at, spots = excluded.spots
                WHERE excluded.observed_at > snapshot.observed_at
            """, (observed_at, json.dumps(spots)))
        return result.rowcount == 1


def parse_snapshot(payload, now):
    observed_at = payload["observed_at"]
    spots = payload["spots"]
    if type(observed_at) not in (int, float) or not now - SNAPSHOT_TTL < observed_at <= now + 5:
        raise ValueError("observed_at must be a recent Unix timestamp in seconds")
    if not isinstance(spots, list) or len(spots) > 200:
        raise ValueError("spots must be a list with at most 200 entries")
    spot_ids, labels = set(), set()
    result = []
    for spot in spots:
        spot_id, number, occupied = spot["id"], spot["number"], spot["occupied"]
        if type(spot_id) is not int or not 1 <= spot_id <= 2**53 - 1 or spot_id in spot_ids:
            raise ValueError("Each spot needs a unique positive numeric id")
        if type(number) is not int or not 1 <= number <= 999999 or number in labels:
            raise ValueError("Each spot needs a unique number between 1 and 999999")
        if type(occupied) is not bool:
            raise ValueError("occupied must be boolean")
        spot_ids.add(spot_id)
        labels.add(number)
        entry = {"id": f"camera-{spot_id}", "number": number, "occupied": occupied}
        if "bounds" in spot:
            bounds = spot["bounds"]
            if (not isinstance(bounds, list) or len(bounds) != 4
                    or any(type(value) not in (int, float) or not 0 <= value <= 1 for value in bounds)):
                raise ValueError("Expected normalized bounds [left, top, right, bottom]")
            left, top, right, bottom = bounds
            if left >= right or top >= bottom:
                raise ValueError("Bounds must have positive width and height")
            entry["bounds"] = bounds
        result.append(entry)
    with_bounds = sum("bounds" in spot for spot in result)
    if 0 < with_bounds < len(result):
        raise ValueError("Include bounds for every spot or omit them for all spots")
    return observed_at, sorted(result, key=lambda spot: spot["number"])


def make_listings(store, now):
    observed, camera_spots = store.read()
    listings = {}
    for parking_id, name, kind, address, lat, lon in PARKINGS:
        live = parking_id == LIVE_ID
        if live:
            if camera_spots and "bounds" in camera_spots[0]:
                spots = spatial_plan(camera_spots)
            else:
                spots = [make_spot(spot["id"], str(spot["number"]), index, 6)
                         for index, spot in enumerate(camera_spots)]
            statuses = {spot["id"]: "occupied" if spot["occupied"] else "free" for spot in camera_spots}
            timestamp = observed
        else:
            spots = demo_spots()
            statuses = {spot["id"]: "free" if spot["id"] in DEMO_FREE[parking_id] else "occupied"
                        for spot in spots}
            timestamp = now
        if timestamp + SNAPSHOT_TTL <= now:
            statuses = {spot["id"]: "unknown" for spot in spots}
        listings[parking_id] = {
            "parking": {
                "id": parking_id, "name": name, "kind": kind, "address": address,
                "entrance": {"lat": lat, "lon": lon}, "spots": spots, "live": live,
            },
            "snapshot": {
                "parkingId": parking_id, "observedAt": iso_time(timestamp),
                "validUntil": iso_time(timestamp + SNAPSHOT_TTL), "statuses": statuses,
            },
        }
    return listings


class Handler(BaseHTTPRequestHandler):
    def send_body(self, status, body, content_type, cache="no-store"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_json(self, status, data):
        self.send_body(status, json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path == "/healthz":
            self.server.store.read()
            self.send_json(200, {"status": "ok"})
        elif path == "/api/parkings" or path.startswith("/api/parkings/"):
            listings = make_listings(self.server.store, time.time())
            if path == "/api/parkings":
                self.send_json(200, list(listings.values()))
                return
            parts = path.removeprefix("/api/parkings/").split("/")
            listing = listings.get(parts[0])
            if listing and len(parts) == 1:
                self.send_json(200, listing["parking"])
            elif listing and parts[1:] == ["occupancy"]:
                self.send_json(200, listing["snapshot"])
            else:
                self.send_json(404, {"error": "Parking not found"})
        elif path == "/api" or path.startswith("/api/"):
            self.send_json(404, {"error": "Route not found"})
        else:
            self.serve_frontend(path)

    def serve_frontend(self, path):
        if "\0" in path:
            self.send_error(404)
            return
        root = self.server.frontend
        target = (root / path.lstrip("/")).resolve()
        if not target.is_relative_to(root):
            self.send_error(404)
            return
        if not target.is_file() and not Path(path).suffix and not path.startswith("/assets/"):
            target = root / "index.html"
        if not target.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        cache = "public, max-age=31536000, immutable" if path.startswith("/assets/") else "no-cache"
        self.send_body(200, target.read_bytes(), content_type, cache)

    def do_POST(self):
        if self.path != "/api/tracker/snapshot":
            self.send_json(404, {"error": "Route not found"})
            return
        expected = b"Bearer " + self.server.token.encode()
        provided = self.headers.get("Authorization", "").encode()
        if not hmac.compare_digest(expected, provided):
            self.send_json(401, {"error": "Invalid tracker token"})
            return
        if self.headers.get_content_type() != "application/json":
            self.send_json(415, {"error": "Expected application/json"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                self.send_json(413, {"error": "Invalid body size"})
                return
            observed_at, spots = parse_snapshot(json.loads(self.rfile.read(length)), time.time())
        except (KeyError, TypeError, ValueError) as exc:
            self.send_json(400, {"error": str(exc)})
            return
        accepted = self.server.store.write(observed_at, spots)
        self.send_json(200, {"accepted": accepted})

    def setup(self):
        self.request.settimeout(5)
        super().setup()

    def log_request(self, code="-", size="-"):
        if str(code) not in {"200", "304"}:
            super().log_request(code, size)


def make_server(address, frontend, database, token):
    if not token:
        raise ValueError("PARKING_API_TOKEN is required")
    store = SnapshotStore(database)
    server = ThreadingHTTPServer(address, Handler)
    server.frontend = frontend.resolve()
    server.store = store
    server.token = token
    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8284)
    parser.add_argument("--frontend", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args()
    with make_server(("127.0.0.1", args.port), args.frontend, args.db, os.getenv("PARKING_API_TOKEN")) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
