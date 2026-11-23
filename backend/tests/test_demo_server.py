import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BACKEND = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND), str(BACKEND / "parking-tracker")]

from demo_server import make_server
from publish_snapshot import snapshot_from_status


class ParkingApiTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / "index.html").write_text("Smart Parking", encoding="utf-8")
        self.server = make_server(("127.0.0.1", 0), root, root / "test.sqlite3", "test-only")
        worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(worker.join, 2)
        self.addCleanup(self.server.shutdown)

    def request(self, path, snapshot=None, token="test-only"):
        data, headers = None, {}
        if snapshot is not None:
            data = json.dumps(snapshot).encode()
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        request = Request(f"http://127.0.0.1:{self.server.server_port}{path}", data, headers)
        with urlopen(request, timeout=3) as response:
            return json.load(response)

    def post(self, snapshot, token="test-only"):
        return self.request("/api/tracker/snapshot", snapshot, token)

    def test_layout_and_status_follow_camera(self):
        parkings = self.request("/api/parkings")
        self.assertEqual(len(parkings), 3)
        self.assertEqual(parkings[0]["parking"]["spots"], [])
        self.assertIn("free", parkings[1]["snapshot"]["statuses"].values())
        observed = time.time() - 2
        camera_status = {"updated_at": observed, "numbers": {"2": 30, "8": 1}, "spaces": {"2": 55, "8": None}}
        first = snapshot_from_status(camera_status)
        self.assertTrue(self.post(first)["accepted"])
        camera_status["updated_at"] += 1
        camera_status["numbers"]["8"] = 4
        camera_status["spaces"] = {"8": 99, "10": None}
        self.assertTrue(self.post(snapshot_from_status(camera_status))["accepted"])
        self.assertFalse(self.post(first)["accepted"])
        plan = self.request("/api/parkings/open-lot")
        self.assertEqual([(s["id"], s["label"]) for s in plan["spots"]], [("camera-8", "4"), ("camera-10", "10")])
        path = "/api/parkings/open-lot/occupancy"
        self.assertEqual(self.request(path)["statuses"], {"camera-8": "occupied", "camera-10": "free"})
        with patch("demo_server.time.time", return_value=observed + 20):
            self.assertEqual(set(self.request(path)["statuses"].values()), {"unknown"})
            self.assertEqual(self.request("/api/parkings/open-lot")["spots"], plan["spots"])

    def test_unauthorized_and_invalid_snapshots_are_rejected(self):
        snapshot = {"observed_at": time.time(), "spots": [{"id": 1, "number": 1, "occupied": False}]}
        with self.assertRaises(HTTPError) as error:
            self.post(snapshot, "wrong")
        self.assertEqual(error.exception.code, 401)
        snapshot["spots"].append({"id": 2, "number": 1, "occupied": True})
        with self.assertRaises(HTTPError) as error:
            self.post(snapshot)
        self.assertEqual(error.exception.code, 400)
        self.assertEqual(self.request("/api/parkings/open-lot/occupancy")["statuses"], {})


if __name__ == "__main__":
    unittest.main()
