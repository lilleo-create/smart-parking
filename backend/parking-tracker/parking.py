import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np


from store import DB_PATH, database, initialize, layout, new_vehicle, occupancies, set_occupant, space_numbers


def publish_frame(output, frame, name="frame"):
    temp = output / f".{name}.jpg"
    if not cv2.imwrite(str(temp), frame):
        raise OSError("Could not write preview frame")
    temp.replace(output / f"{name}.jpg")


def track(args, capture):
    from ultralytics import YOLO

    initialize(args.db, args.spaces)
    revision = -1
    known_vehicles = {}
    pending = {}
    model = YOLO(args.model)
    frames = 0
    while args.frames == 0 or frames < args.frames:
        frame = capture()
        height, width = frame.shape[:2]
        result = model.track(
            frame, persist=True, tracker="bytetrack.yaml", device="cpu",
            imgsz=args.size, classes=args.classes, verbose=False,
        )[0]
        with database(args.db) as db:
            db.execute("BEGIN")
            current_revision, _, polygons = layout(db)
            if current_revision != revision:
                spaces = {int(name): np.asarray(points, dtype=np.float32) for name, points in polygons.items()}
                numbers = space_numbers(db)
                confirmed = dict.fromkeys(spaces)
                confirmed.update(occupancies(db))
                pending.clear()
                revision = current_revision

        candidates = {}
        preview = frame.copy()
        if result.boxes.id is not None:
            for bounds, track_id in zip(result.boxes.xyxy.tolist(), result.boxes.id.int().tolist()):
                if track_id not in known_vehicles:
                    with database(args.db) as db:
                        known_vehicles[track_id] = new_vehicle(db)
                vehicle = known_vehicles[track_id]
                x1, y1, x2, y2 = bounds
                center = ((x1 + x2) / (2 * width), (y1 + y2) / (2 * height))
                matches = [
                    (cv2.pointPolygonTest(polygon, center, True), name)
                    for name, polygon in spaces.items()
                ]
                if matches:
                    distance, name = max(matches)
                    if distance >= 0 and (name not in candidates or distance > candidates[name][0]):
                        candidates[name] = (distance, vehicle)
                cv2.rectangle(preview, (int(x1), int(y1)), (int(x2), int(y2)), (255, 180, 65), 2)
                cv2.putText(preview, f"#{vehicle}", (int(x1), max(18, int(y1) - 4)),
                            cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 180, 65), 2)

        now = time.monotonic()
        changes = {}
        for name in spaces:
            candidate = candidates.get(name, (None, None))[1]
            if candidate == confirmed[name]:
                pending.pop(name, None)
                continue
            previous, started = pending.get(name, (candidate, now))
            if previous != candidate:
                started = now
            pending[name] = (candidate, started)
            if now - started >= args.settle:
                changes[name] = candidate

        if changes:
            with database(args.db) as db:
                db.execute("BEGIN IMMEDIATE")
                if layout(db)[0] != revision:
                    continue
                for name, candidate in changes.items():
                    set_occupant(db, name, confirmed[name], candidate)
                    confirmed[name] = candidate
                    pending.pop(name)

        for name, polygon in spaces.items():
            points = np.rint(polygon * [width - 1, height - 1]).astype(np.int32)
            occupant = confirmed[name]
            color = (70, 200, 70) if occupant is None else (60, 65, 245)
            number = numbers.get(name, name)
            label = f"{number}: FREE" if occupant is None else f"{number}: #{occupant}"
            cv2.polylines(preview, [points], True, color, 2)
            x, y = points[0]
            cv2.putText(preview, label, (int(x), max(18, int(y))),
                        cv2.FONT_HERSHEY_SIMPLEX, .55, color, 2)

        publish_frame(args.output, frame, "raw")
        publish_frame(args.output, preview)
        status = {
            "configured": bool(spaces), "spaces": confirmed, "numbers": numbers, "updated_at": time.time(),
        }
        temp = args.output / ".status.json"
        temp.write_text(json.dumps(status, ensure_ascii=False) + "\n")
        temp.replace(args.output / "status.json")
        frames += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", help="Video file, stream URL, or USB camera index. Default: CSI camera.")
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--spaces", type=Path, default=Path("spaces.json"))
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--classes", type=int, nargs="+", default=[2, 5, 7])
    parser.add_argument("--size", type=int, default=640)
    parser.add_argument("--settle", type=float, default=2)
    parser.add_argument("--frames", type=int, default=0)
    parser.add_argument("--snapshot", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cv2.setNumThreads(2)

    if args.source is None:
        from picamera2 import Picamera2

        camera = Picamera2()
        camera.configure(camera.create_video_configuration(
            main={"size": (1280, 960), "format": "RGB888"},
        ))
        camera.start()

        def capture():
            job = camera.capture_array(wait=False)
            try:
                return camera.wait(job, timeout=5)
            except TimeoutError as exc:
                raise TimeoutError("CSI camera did not deliver a frame within 5 seconds") from exc

        close = camera.close
    else:
        source = int(args.source) if args.source.isdecimal() else args.source
        video = cv2.VideoCapture(source)
        if not video.isOpened():
            parser.error(f"Could not open {source}")

        def capture():
            ok, frame = video.read()
            if not ok:
                raise EOFError("Video source stopped delivering frames")
            return frame

        close = video.release

    try:
        if args.snapshot:
            publish_frame(args.output, capture())
        else:
            track(args, capture)
    except KeyboardInterrupt:
        pass
    except EOFError:
        if args.source is None or not Path(args.source).is_file():
            raise
    finally:
        close()


if __name__ == "__main__":
    main()
