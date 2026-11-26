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

    def test_camera_plan_aligns_jitter_and_retains_the_aisles(self):
        observed = time.time() - 1
        camera_status = {
            "updated_at": observed,
            "numbers": {"2": 80, "5": 30, "7": 4, "9": 7, "11": 60},
            "spaces": {"2": None, "5": 12, "7": None, "9": 21, "11": None},
            "bounds": {
                "2": [0.10, 0.12, 0.20, 0.21],
                "5": [0.24, 0.14, 0.36, 0.24],
                "7": [0.64, 0.13, 0.74, 0.22],
                "9": [0.26, 0.46, 0.37, 0.56],
                "11": [0.65, 0.48, 0.76, 0.58],
            },
        }
        self.assertTrue(self.post(snapshot_from_status(camera_status))["accepted"])
        path = "/api/parkings/open-lot"
        plan = self.request(path)["spots"]
        self.assertEqual([(s["label"], s["planRow"], s["position"]) for s in plan], [
            ("80", 1, 1), ("30", 1, 2), ("4", 1, 4), ("7", 3, 2), ("60", 3, 4),
        ])
        camera_status["updated_at"] += 0.5
        camera_status["bounds"]["2"] = [0.10, 0.47, 0.20, 0.57]
        self.assertTrue(self.post(snapshot_from_status(camera_status))["accepted"])
        moved_plan = self.request(path)["spots"]
        self.assertEqual([(s["id"], s["planRow"], s["position"]) for s in moved_plan], [
            ("camera-5", 1, 2), ("camera-7", 1, 4), ("camera-2", 3, 1),
            ("camera-9", 3, 2), ("camera-11", 3, 4),
        ])
        with patch("demo_server.time.time", return_value=observed + 20):
            self.assertEqual(self.request(path)["spots"], moved_plan)
            self.assertEqual(set(self.request(path + "/occupancy")["statuses"].values()), {"unknown"})

    def test_overlapping_bounds_leave_every_spot_visible(self):
        bounds = [0.1, 0.2, 0.3, 0.4]
        self.post({"observed_at": time.time(), "spots": [
            {"id": 10, "number": 22, "occupied": False, "bounds": bounds},
            {"id": 20, "number": 7, "occupied": True, "bounds": bounds},
        ]})
        plan = self.request("/api/parkings/open-lot")["spots"]
        self.assertEqual([(s["id"], s["planRow"], s["position"]) for s in plan], [
            ("camera-10", 1, 1), ("camera-20", 1, 2),
        ])

    def test_invalid_or_incomplete_bounds_keep_previous_layout(self):
        observed = time.time() - 1
        previous = {"id": 1, "number": 1, "occupied": True, "bounds": [0.1, 0.2, 0.3, 0.4]}
        self.post({"observed_at": observed, "spots": [previous]})
        for bounds in ([-0.1, 0.2, 0.3, 0.4], [0.3, 0.2, 0.1, 0.4], [True, 0, 1, 1], None):
            with self.subTest(bounds=bounds), self.assertRaises(HTTPError) as error:
                self.post({"observed_at": observed + 0.5, "spots": [{**previous, "bounds": bounds}]})
            self.assertEqual(error.exception.code, 400)
        with self.assertRaises(HTTPError) as error:
            self.post({"observed_at": observed + 0.5, "spots": [
                previous, {"id": 2, "number": 2, "occupied": True},
            ]})
        self.assertEqual(error.exception.code, 400)
        plan = self.request("/api/parkings/open-lot")["spots"]
        self.assertEqual([(s["id"], s["planRow"]) for s in plan], [("camera-1", 1)])


if __name__ == "__main__":
    unittest.main()
