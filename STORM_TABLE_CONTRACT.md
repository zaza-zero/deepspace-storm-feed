# Storm Table Contract

What one clean row of the `deepspace_storms` table looks like. The table is filled
by the DeepSpace Storm Feed from NASA DONKI's geomagnetic storm (GST) endpoint
(`https://api.nasa.gov/DONKI/GST`) and replaces the hand-filled DeepSpace Watch
table. This contract covers geomagnetic storms only.

## What one row means

One row is one geomagnetic storm event as NASA DONKI reports it. For example, the
May 2024 reference pull (`data/donki_gst_2024-05-01_to_2024-05-31.json`) produced
5 rows, one per storm. A storm is one event however many Kp readings it has, so its
Kp readings are summarised onto its row (`peak_kp`, `kp_reading_count`) and never
become extra rows. The feed re-fetches an overlapping 30-day window every run, so
the same storm comes back many times. It is still the same event and stays one row.

## Columns

Every column in the table is listed here. There are no other columns.

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `gst_id` | text | yes | NASA's identifier for the storm (DONKI `gstID`), e.g. `2024-05-10T15:00:00-GST-001`. Unique across the table. |
| `start_time_utc` | timestamptz | yes | When the storm began (DONKI `startTime`). |
| `peak_kp` | numeric(3,2) | yes | Highest Kp reading for the storm (max of `allKpIndex[].kpIndex`), from 0.00 to 9.00. |
| `peak_kp_observed_time_utc` | timestamptz | yes | When the peak Kp was observed (`observedTime` of that reading). If several readings tie, the earliest one. |
| `kp_reading_count` | integer | yes | How many Kp readings NASA logged for the storm (length of `allKpIndex`). |
| `severity` | text | yes | One of `none`, `G1-minor`, `G2-moderate`, `G3-strong`, `G4-severe`, `G5-extreme`, set from `peak_kp` by the table below. |
| `link` | text | no | NASA's page for the event (DONKI `link`). Blank if NASA did not send one. |
| `submission_time_utc` | timestamptz | no | When NASA logged the event (DONKI `submissionTime`). Blank if NASA did not send one. |
| `ingested_at_utc` | timestamptz | yes | When our job last wrote this row. Not when the storm happened. |

## Severity tiers

`severity` is derived from `peak_kp` on the way in, never typed by hand. The tiers
follow the NOAA G-scale. Each boundary is an exact Kp number: a tier includes its
lower number and stops just below the next one. The tiers do not overlap and cover
the whole Kp scale from 0 to 9 with no gaps, so a fractional reading such as 6.67
falls into exactly one tier.

| Peak Kp | Rule | `severity` |
| --- | --- | --- |
| under 5 | `0 <= peak_kp < 5` | `none` |
| 5 up to but not including 6 | `5 <= peak_kp < 6` | `G1-minor` |
| 6 up to but not including 7 | `6 <= peak_kp < 7` | `G2-moderate` |
| 7 up to but not including 8 | `7 <= peak_kp < 8` | `G3-strong` |
| 8 up to but not including 9 | `8 <= peak_kp < 9` | `G4-severe` |
| exactly 9 | `peak_kp = 9` | `G5-extreme` |

A `peak_kp` outside 0 to 9 is invalid. The loader rejects that row instead of
guessing a tier. These six labels are the only values `severity` may hold.

Examples from the May 2024 reference file: peak Kp 9.0 is `G5-extreme`; 6.67, 6.33
and 6.0 are all `G2-moderate`.

## Unique key

`gst_id` alone identifies a row. The table has a uniqueness constraint on it
(the primary key). That constraint is **what prevents duplicate rows on
re-ingestion**: a re-run over the same days cannot add a second copy of the same
storm. A repeated `gst_id` means the same storm was fetched again, either because
the 30-day windows overlap or because the job retried.

The rule: **same `gst_id`, one row. The newest fetch overwrites the old one, and
`ingested_at_utc` moves forward with it.** The load runs as an upsert on `gst_id`
(`INSERT ... ON CONFLICT (gst_id) DO UPDATE`). A matching row is updated in place,
and a new `gst_id` is inserted. This also picks up NASA's own revisions to an event.
Loading the same file twice leaves the row count unchanged.

## How timestamps are stored

Every time column is stored in Coordinated Universal Time (UTC, the single global
clock) in ISO-8601 format, for example `2024-05-10T15:00:00Z`. That is all four of
them:

- `start_time_utc`
- `peak_kp_observed_time_utc`
- `submission_time_utc`
- `ingested_at_utc`

DONKI sends its times in UTC with a `Z` suffix (e.g. `2024-05-10T15:00Z`). Any value
that arrives with a local offset or no zone marker is converted to UTC in the
loading step, before anything is written. `ingested_at_utc` is taken from the
loader's UTC clock. Nothing is converted on the way out. Anything reading this table
gets UTC and can shift it for display if it needs to. Any timestamp column added
later must also be UTC and must be added to this list.

**Freshness rule:** the "data is X hours old" figure for DeepSpace Watch is the number
of whole hours between the largest `ingested_at_utc` in the table and the current
UTC time. Under 24 hours means today's run happened. 24 hours or more means the run
was missed, and the page shows a stale warning.
