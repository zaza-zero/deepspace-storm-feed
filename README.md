# DeepSpace Storm Feed

The first piece of an automated space-weather feed. `fetch_storms.py` pulls every
**geomagnetic storm (GST)** event that NASA's DONKI service logged in the **last 30 days**,
saves NASA's reply exactly as it was sent, and reports what it found.

## Why this exists

The legacy **DeepSpace Watch** table is filled by hand, so it is always behind.
Right now its data is **one day old**, and it falls further behind every day nobody
updates it. This feed replaces that manual step with a fetch anyone can rerun (and a
scheduler can run later), always covering the latest 30 days.

## Latest run: results

Run on **2026-09-25** with `NASA_API_KEY=DEMO_KEY`:

```
NASA DONKI geomagnetic storm (GST) fetch
Date range (UTC): 2026-08-26 to 2026-09-25 (30 days)
Events pulled:    0
Raw response saved to: data/donki_gst_2026-08-26_to_2026-09-25.json
```

| What | Value |
|---|---|
| Window (UTC) | 2026-08-26 → 2026-09-25, 30 days |
| Geomagnetic storms found | **0** |
| NASA's raw reply | `[]` in [`data/donki_gst_2026-08-26_to_2026-09-25.json`](data/donki_gst_2026-08-26_to_2026-09-25.json) |
| Terminal output (as run) | [`output/run_output.txt`](output/run_output.txt) |

### What "0 events" means

The request succeeded. NASA answered with an empty list (`[]`), which is DONKI's
way of saying **no geomagnetic storm was recorded in this window**. It is a real
reading, not an error: if the key or the request were wrong, NASA would return an
error message instead of a list, and the script would stop without saving a file.

For the DeepSpace Watch table this is still useful: it confirms a quiet 30 days,
which the manual table could not tell us with any confidence.

### Reference sample: proof the feed returns real records

Because the live window came back empty, the same script was also run once over a
window with known storms, May 2024 (the "Gannon" storm, Kp 9). This is **reference
data only**, not the current feed:

```bash
python3 fetch_storms.py --start 2024-05-01 --end 2024-05-31 | tee output/reference_run_output.txt
```

The raw reply is saved unchanged to `data/donki_gst_2024-05-01_to_2024-05-31.json`,
and the terminal output to `output/reference_run_output.txt`. Without
`--start/--end`, the script always uses the computed 30-day window ending today.

**Result: 5 geomagnetic storms.** Every record in the raw file carries an event ID,
a UTC start time and Kp strength readings (each with its own UTC `observedTime`):

| Event ID (`gstID`) | Start (UTC) | Kp readings | Peak Kp |
|---|---|---|---|
| `2024-05-02T15:00:00-GST-001` | 2024-05-02 15:00 | 2 | 6.67 |
| `2024-05-10T15:00:00-GST-001` | 2024-05-10 15:00 | 13 | **9.0** (Gannon storm) |
| `2024-05-12T21:00:00-GST-001` | 2024-05-12 21:00 | 3 | 6.33 |
| `2024-05-16T06:00:00-GST-001` | 2024-05-16 06:00 | 1 | 6.0 |
| `2024-05-17T18:00:00-GST-001` | 2024-05-17 18:00 | 1 | 6.0 |

This shows the empty live result above is a quiet month, not a broken request.

### What each event contains when storms occur

When the window does contain storms, every record in the saved file carries these
fields straight from NASA (nothing is renamed or removed):

| Field | Meaning |
|---|---|
| `gstID` | Unique event identifier, e.g. `2026-09-01T09:00:00-GST-001` |
| `startTime` | When the storm began, in UTC |
| `allKpIndex[].kpIndex` | Storm strength on the Kp scale (5 = minor … 9 = extreme) |
| `allKpIndex[].observedTime` | UTC time of each Kp reading |
| `linkedEvents` | Related solar events (e.g. the CME that caused it) |
| `link` | NASA's page for the event |

And the terminal report lists one line per storm under the count:

```
Events pulled:    1
  <gstID>  start=<startTime UTC>  Kp=[<kpIndex readings>]
```

## How it works

1. Works out the window from today's UTC date: today minus 30 days → today. No dates are hardcoded.
2. Calls `https://api.nasa.gov/DONKI/GST` for that window.
3. Saves the raw JSON response, byte for byte, to `data/donki_gst_<start>_to_<end>.json`.
4. Prints the event count, the date range, and one line per event.

## Run it

Requires Python 3.9+ and no third-party packages.

```bash
export NASA_API_KEY=DEMO_KEY   # or your own key from https://api.nasa.gov
mkdir -p output && python3 fetch_storms.py | tee output/run_output.txt
```

The key is read from the `NASA_API_KEY` environment variable only. It is never
written into code or committed, and `.env` is git-ignored.
