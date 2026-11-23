import json
import math
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from store import DB_PATH, database, initialize, layout, occupancies, set_occupant, space_numbers


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def deliver(url, token):
    opener = build_opener(NoRedirect)
    delay = 1
    while True:
        with database(DB_PATH) as db:
            event = db.execute(
                "SELECT id, payload FROM outbox WHERE delivered=0 ORDER BY id LIMIT 1"
            ).fetchone()
        if event is None:
            time.sleep(1)
            continue
        row_id, payload = event
        headers = {
            "Content-Type": "application/json",
            "Idempotency-Key": json.loads(payload)["event_id"],
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            with opener.open(Request(url, payload.encode(), headers, method="POST"), timeout=5) as response:
                if not 200 <= response.status < 300:
                    raise ValueError(f"HTTP {response.status}")
        except (OSError, URLError, ValueError) as exc:
            print(f"Webhook delivery failed: {exc}", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 60)
            continue
        with database(DB_PATH) as db:
            db.execute("UPDATE outbox SET delivered=1 WHERE id=?", (row_id,))
        delay = 1


def rectangle(points):
    if not isinstance(points, list) or len(points) != 4:
        raise ValueError("Expected [left, top, right, bottom]")
    if not all(type(p) in (int, float) and 0 <= p <= 1 and math.isfinite(p) for p in points):
        raise ValueError("Coordinates must be between 0 and 1")
    left, top, right, bottom = points
    if right - left < .005 or bottom - top < .005:
        raise ValueError("Rectangle is too small")
    return [[left, top], [right, top], [right, bottom], [left, bottom]]


class Handler(BaseHTTPRequestHandler):
    def log_request(self, code="-", size="-"):
        if str(code) != "200":
            super().log_request(code, size)

    def send_data(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, code, data):
        self.send_data(code, json.dumps(data).encode(), "application/json")

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/layout":
            with database(DB_PATH) as db:
                db.execute("BEGIN")
                revision, _, spaces = layout(db)
                numbers = space_numbers(db)
            self.send_json(200, {"revision": revision, "spaces": spaces, "numbers": numbers})
            return
        files = {
            "/": ("view.html", "text/html; charset=utf-8"),
            "/frame.jpg": ("output/frame.jpg", "image/jpeg"),
            "/raw.jpg": ("output/raw.jpg", "image/jpeg"),
            "/status.json": ("output/status.json", "application/json"),
        }
        if path not in files:
            self.send_error(404)
            return
        name, mime = files[path]
        try:
            body = Path(name).read_bytes()
        except FileNotFoundError:
            self.send_error(404)
            return
        self.send_data(200, body, mime)

    def do_PUT(self):
        if self.path != "/api/layout":
            self.send_error(404)
            return
        if self.headers.get_content_type() != "application/json":
            self.send_error(415)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                raise ValueError("Invalid body size")
            data = json.loads(self.rfile.read(length))
            entries = data["spaces"]
            if not isinstance(entries, list) or len(entries) > 200:
                raise ValueError("Expected a list of up to 200 spaces")
            entries = [(entry.get("id"), rectangle(entry["bounds"]), entry.get("number")) for entry in entries]
            for _, _, number in entries:
                if number is not None and (type(number) is not int or not 1 <= number <= 999999):
                    raise ValueError("Номер места должен быть целым числом от 1 до 999999.")
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            self.send_json(400, {"error": str(exc)})
            return

        try:
            with database(DB_PATH) as db:
                db.execute("BEGIN IMMEDIATE")
                revision, next_id, old = layout(db)
                if data.get("revision") != revision:
                    self.send_json(409, {"error": "Разметка изменилась. Откройте редактор заново."})
                    return
                spaces = {}
                previous_numbers = space_numbers(db)
                numbers = {}
                used_numbers = set()
                for space_id, polygon, number in entries:
                    if space_id is None:
                        space_id = next_id
                        next_id += 1
                    elif type(space_id) is not int or str(space_id) not in old or space_id in spaces:
                        raise ValueError("Invalid or duplicate space ID")
                    spaces[space_id] = polygon
                    if number is not None:
                        if number in used_numbers:
                            raise ValueError(f"Номер {number} уже используется.")
                        numbers[space_id] = number
                        used_numbers.add(number)
                for space_id in spaces.keys() - numbers.keys():
                    number = previous_numbers.get(space_id, space_id)
                    if number in used_numbers:
                        number = next(candidate for candidate in range(1, len(spaces) + 1)
                                      if candidate not in used_numbers)
                    numbers[space_id] = number
                    used_numbers.add(number)
                for space_id, vehicle in occupancies(db).items():
                    if old.get(str(space_id)) != spaces.get(space_id):
                        set_occupant(db, space_id, vehicle, None)
                db.execute("DELETE FROM space_numbers")
                db.executemany("INSERT INTO space_numbers VALUES (?, ?)", numbers.items())
                revision += 1
                db.execute("UPDATE layout SET revision=?, next_id=?, spaces=? WHERE id=1",
                           (revision, next_id, json.dumps(spaces)))
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
            return
        self.send_json(200, {"revision": revision, "spaces": spaces, "numbers": numbers})


def main():
    initialize(DB_PATH, Path("spaces.json"))
    url = os.getenv("PARKING_WEBHOOK_URL")
    if url:
        if not url.startswith(("https://", "http://")):
            raise ValueError("PARKING_WEBHOOK_URL must be an HTTP(S) URL")
        threading.Thread(target=deliver, args=(url, os.getenv("PARKING_WEBHOOK_TOKEN")), daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()


if __name__ == "__main__":
    main()
