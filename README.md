# DeepSpace Storm Feed

The first piece of an automated space-weather feed. `fetch_storms.py` pulls every
**geomagnetic storm (GST)** event NASA's DONKI service logged in the **last 30 days**
and saves NASA's reply exactly as it was sent.

## Why this exists

The legacy **DeepSpace Watch** table is filled by hand, so it is always behind:
right now its data is **one day old**, and it goes further out of date each day
nobody updates it. This script replaces that manual step with a fetch that anyone
(or a scheduler, later) can rerun.

## What it does

1. Works out the window from today's UTC date: today minus 30 days → today. No dates are hardcoded.
2. Calls `https://api.nasa.gov/DONKI/GST` for that window.
3. Saves the raw JSON response, byte for byte, to `data/donki_gst_<start>_to_<end>.json`.
4. Prints how many events were pulled and the date range. Each event line shows its ID (`gstID`), UTC start time (`startTime`) and storm strength (`kpIndex` readings).

## Run it

Requires Python 3.9+ and no third-party packages.

```bash
export NASA_API_KEY=DEMO_KEY   # or your own key from https://api.nasa.gov
python3 fetch_storms.py
```

The key is read from the `NASA_API_KEY` environment variable only. It is never
written into code or committed. `.env` is git-ignored.

## Latest run

The terminal output of the most recent run is committed in
[`output/run_output.txt`](output/run_output.txt). It shows the event count and the
exact date range. It was captured with:

```bash
mkdir -p output && python3 fetch_storms.py | tee output/run_output.txt
```
