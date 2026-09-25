"""Fetch the last 30 days of geomagnetic storm events from NASA DONKI.

Reads the API key from the NASA_API_KEY environment variable, saves NASA's
response byte for byte under data/, and prints the event count and the window.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

DONKI_GST_URL = "https://api.nasa.gov/DONKI/GST"
WINDOW_DAYS = 30
DATA_DIR = Path(__file__).parent / "data"


def compute_window(today=None):
    """Return (start, end) dates covering the last WINDOW_DAYS days, in UTC."""
    end = today or datetime.now(timezone.utc).date()
    return end - timedelta(days=WINDOW_DAYS), end


def fetch_raw(start, end, api_key):
    """Return NASA's response body exactly as sent."""
    query = urllib.parse.urlencode(
        {"startDate": start.isoformat(), "endDate": end.isoformat(), "api_key": api_key}
    )
    with urllib.request.urlopen(f"{DONKI_GST_URL}?{query}", timeout=60) as resp:
        return resp.read()


def main():
    api_key = os.environ.get("NASA_API_KEY")
    if not api_key:
        sys.exit("NASA_API_KEY is not set. Example: export NASA_API_KEY=DEMO_KEY")

    start, end = compute_window()
    raw = fetch_raw(start, end, api_key)

    DATA_DIR.mkdir(exist_ok=True)
    out_path = DATA_DIR / f"donki_gst_{start.isoformat()}_to_{end.isoformat()}.json"
    out_path.write_bytes(raw)

    body = raw.strip()
    events = json.loads(body) if body else []

    print("NASA DONKI geomagnetic storm (GST) fetch")
    print(f"Date range (UTC): {start.isoformat()} to {end.isoformat()} ({WINDOW_DAYS} days)")
    print(f"Events pulled:    {len(events)}")
    for event in events:
        kp = [k.get("kpIndex") for k in event.get("allKpIndex", [])]
        print(f"  {event.get('gstID')}  start={event.get('startTime')}  Kp={kp}")
    print(f"Raw response saved to: {out_path.relative_to(Path(__file__).parent)}")


if __name__ == "__main__":
    main()
