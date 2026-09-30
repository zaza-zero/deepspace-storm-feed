# Storm Table Contract: `deepspace_storms`

The table the DeepSpace Storm Feed loads from NASA DONKI's geomagnetic storm
(GST) endpoint. **One row per storm event.** Anything that writes to or reads
from this table follows this contract.

Source: `https://api.nasa.gov/DONKI/GST`, saved by `fetch_storms.py` under `data/`.

## Columns

Every column in the table is listed here. There are no other columns.

| # | Column | Type | Nullable | Source field (DONKI) | Meaning |
|---|---|---|---|---|---|
| 1 | `gst_id` | `TEXT` | NOT NULL | `gstID` | NASA's event ID, e.g. `2024-05-10T15:00:00-GST-001`. **Unique event identifier** (see below). |
| 2 | `start_time_utc` | `TIMESTAMPTZ` | NOT NULL | `startTime` | When the storm began. |
| 3 | `peak_kp` | `NUMERIC(3,2)` | NOT NULL | max of `allKpIndex[].kpIndex` | Highest Kp reading for the storm, 0.00 to 9.00. |
| 4 | `peak_kp_observed_time_utc` | `TIMESTAMPTZ` | NOT NULL | `allKpIndex[].observedTime` of the peak reading | When the peak Kp was observed. The earliest one if several readings tie. |
| 5 | `kp_reading_count` | `INTEGER` | NOT NULL | length of `allKpIndex` | How many Kp readings NASA logged for the storm. |
| 6 | `severity` | `TEXT` | NOT NULL | derived from `peak_kp` | Severity tier label: one of the six labels in the Severity tiers table below. |
| 7 | `link` | `TEXT` | NULL | `link` | NASA's page for the event. |
| 8 | `submission_time_utc` | `TIMESTAMPTZ` | NULL | `submissionTime` | When NASA logged the event. |
| 9 | `ingested_at_utc` | `TIMESTAMPTZ` | NOT NULL | set by the loader | When our loader last wrote this row. |

## Unique event identifier: `gst_id`

`gst_id` is the table's primary key (`PRIMARY KEY (gst_id)`). It is **what
prevents duplicate rows on re-ingestion**. The feed re-fetches an overlapping
30-day window on every run, so the same storm arrives many times. The loader
must upsert on `gst_id` (`INSERT ... ON CONFLICT (gst_id) DO UPDATE`), so that
re-loading a storm updates its one existing row and never inserts a second one.
Running the loader twice on the same file must leave the row count unchanged.

## Timestamps: all UTC

**All timestamps are stored in UTC.** This covers every timestamp column in the
table, with no exceptions:

- `start_time_utc`
- `peak_kp_observed_time_utc`
- `submission_time_utc`
- `ingested_at_utc`

DONKI sends times as UTC with a `Z` suffix (e.g. `2024-05-10T15:00Z`). The loader
stores them as UTC unchanged and never converts them to a local time zone.
`ingested_at_utc` is taken from the loader's UTC clock (`now() AT TIME ZONE 'UTC'`
/ `datetime.now(timezone.utc)`). Any timestamp column added later must also be UTC
and must be added to this list.

## Severity tiers (Kp cut-offs)

`severity` is derived from `peak_kp` using the NOAA G-scale. Each boundary is an
exact Kp number. The lower bound is included and the upper bound is excluded, so
the tiers cover the whole Kp scale (0 to 9) with no gaps and no overlaps.
Fractional readings such as 6.67 fall into exactly one tier.

| `severity` label | Kp range | Rule |
|---|---|---|
| `none` | 0 to below 5 | `0 <= peak_kp < 5` |
| `G1-minor` | 5 to below 6 | `5 <= peak_kp < 6` |
| `G2-moderate` | 6 to below 7 | `6 <= peak_kp < 7` |
| `G3-strong` | 7 to below 8 | `7 <= peak_kp < 8` |
| `G4-severe` | 8 to below 9 | `8 <= peak_kp < 9` |
| `G5-extreme` | exactly 9 | `peak_kp = 9` |

A `peak_kp` outside 0 to 9 is invalid, and the loader rejects that row instead of
guessing a tier. These six labels are the only allowed values of `severity`
(`CHECK (severity IN ('none','G1-minor','G2-moderate','G3-strong','G4-severe','G5-extreme'))`).

Worked examples from the May 2024 reference file: peak Kp 9.0 → `G5-extreme`;
6.67 → `G2-moderate`; 6.33 → `G2-moderate`; 6.0 → `G2-moderate`.
