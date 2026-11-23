import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def snapshot_from_status(status):
    return {
        "observed_at": status["updated_at"],
        "spots": [
            {"id": int(spot_id), "number": status["numbers"].get(spot_id, int(spot_id)),
             "occupied": vehicle_id is not None}
            for spot_id, vehicle_id in status["spaces"].items()
        ],
    }


def publish(status_path, url, token):
    opener = build_opener(NoRedirect)
    sent = None
    latest_error = None
    while True:
        started = time.monotonic()
        try:
            snapshot = snapshot_from_status(json.loads(status_path.read_text(encoding="utf-8")))
            observed = snapshot["observed_at"]
            if sent != observed and time.time() - 10 < observed <= time.time() + 5:
                request = Request(url, json.dumps(snapshot).encode(), {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }, method="POST")
                with opener.open(request, timeout=3) as response:
                    if response.status != 200:
                        raise ValueError(f"Unexpected HTTP status {response.status}")
                sent = observed
                if latest_error:
                    print("Доставка снимков восстановлена.", file=sys.stderr, flush=True)
                    latest_error = None
        except (OSError, URLError, KeyError, TypeError, ValueError) as exc:
            error = str(exc)
            if error != latest_error:
                print(f"Снимок не отправлен: {error}", file=sys.stderr, flush=True)
                latest_error = error
        time.sleep(max(0, 1 - (time.monotonic() - started)))


def main():
    parser = argparse.ArgumentParser(description="Отправлять снимки статусов трекера в API парковки")
    parser.add_argument("--status", type=Path, default=Path("output/status.json"))
    parser.add_argument("--url", default=os.getenv("PARKING_API_URL"))
    parser.add_argument("--token-file", type=Path)
    args = parser.parse_args()
    token = args.token_file.read_text(encoding="utf-8").strip() if args.token_file else os.getenv("PARKING_API_TOKEN")
    url = urlsplit(args.url or "")
    if not url.hostname or (url.scheme != "https" and not (
        url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}
    )):
        parser.error("Укажи адрес HTTPS через --url или PARKING_API_URL")
    if not token:
        parser.error("Передай токен через --token-file или PARKING_API_TOKEN")
    try:
        publish(args.status, args.url, token)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
