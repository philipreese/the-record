# backend/scripts

Operational and maintenance scripts for the-record. All scripts are run via pixi:

```
pixi run python backend/scripts/<script>.py
```

---

## Ordering constraint

**Never run `sync.py` between a delete and an import.** `sync.py` pulls the current state of ListenBrainz into the local DB — if LB is mid-cleanup (dirty entries deleted, clean entries not yet imported), sync will write stale/missing data back to the DB.

Safe order for any LB cleanup operation:

```
export_db_to_history.py --confirm   # mirror DB → merged_history.json
delete_listenbrainz.py              # remove stale/dirty entries from LB
import_listenbrainz.py --skip-dedup # import clean entries to LB
clean_listenbrainz_scrobbles.py     # catch any remaining dirty scrobbles on LB
sync.py                             # now safe — LB and DB are in sync
```

---

## Scripts

### Data ingestion

**`merge_history.py`**
One-time script. Merges a YouTube Music `watch-history.json` takeout export with
Last.fm scrobble history, deduplicates, and writes `backend/merged_history.json`.
Run this when bootstrapping a new history or adding a fresh YT Music takeout.

---

### DB metadata

**`clean_database_metadata.py`**
Applies `clean_artist` / `clean_title` (strips feat. credits, country suffixes,
video tags) to all rows in `history.db`, then deduplicates. Dry run by default;
`--confirm` to apply. Run before any LB sync after a bulk artist/title correction.

**`backfill_metadata.py`**
Queries MusicBrainz to fill `album` and `duration_secs` for tracks missing that
data. Uses a dual raw/clean query strategy and scores candidates by title
similarity, artist similarity, release type, and duration presence.

```
python backfill_metadata.py              # fill tracks missing album or duration
python backfill_metadata.py --reverify   # re-query all tracks, flag changed data
```

Writes `backfill_results.json` (one entry per unique track with action codes) and
`backfill_failures.json` (tracks MB returned no results for). Checkpoint/resume is
built in — safe to interrupt and restart.

Action codes in results:
| Code | Meaning |
|---|---|
| `verified` | MB match confirms existing data — no change |
| `filled` | Album/duration was null — filled automatically |
| `updated` | High-confidence match with different data — applied |
| `skipped_update` | High-confidence match with different data — deferred (no `--confirm-updates`) |
| `skipped` | Low-confidence match — not applied |
| `failed` | MB returned no results |

---

### Backfill review

These three scripts form a review loop after `backfill_metadata.py --reverify`.

**`apply_skipped_updates.py`**
Reviews `skipped_update` and `skipped` entries from `backfill_results.json`.
Generates `skipped_updates_review.csv` for human review, then applies decisions.

```
python apply_skipped_updates.py --generate-csv     # write review CSV
# edit skipped_updates_review.csv
python apply_skipped_updates.py --apply-csv        # dry run
python apply_skipped_updates.py --apply-csv --confirm
```

Decisions per row: `accept` (apply MB's values), `reject` (leave unchanged),
`fix` (use `fix_album`/`fix_duration_secs`/`fix_artist`/`fix_title` overrides),
`delete` (remove all listens for this track from DB).

When `fix_artist` or `fix_title` is set, album/duration are cleared so
`backfill_metadata.py` re-queries MB with the corrected name.

**`generate_review_csv.py`**
Generates `failure_review.csv` from `backfill_failures.json` for manual triage.
Pre-marks known junk (VEVO channels, ambient channels, label channels) as `delete`.

```
python generate_review_csv.py
# edit failure_review.csv
python apply_review_decisions.py --confirm
```

**`apply_review_decisions.py`**
Applies decisions from `failure_review.csv`. Decisions: `keep` (no action),
`delete` (remove all listens), `fix` (rename artist/title in DB for backfill
retry). Writes `fix_retry.json` with corrected entries; run
`backfill_metadata.py` afterward to fill those tracks.

Reads CSV with automatic encoding detection (handles both UTF-8 and
Windows-1252/CP1252, since Excel on Windows may re-save with the latter).

**`fix_failure_entries.py`**
Older batch-cleanup script for well-known junk patterns in `backfill_failures.json`
(VEVO channels, label channels, specific junk artists). Superseded by the
`generate_review_csv.py` / `apply_review_decisions.py` workflow for manual review,
but retained for reference and its `JUNK_ARTISTS` / `LABEL_ARTISTS` lists, which
inform the pre-marking logic in `generate_review_csv.py`.

---

### ListenBrainz sync

**`export_db_to_history.py`**
Exports `history.db` to `backend/merged_history.json` — an exact mirror of the DB.
Run this after all DB cleanup is complete and before the LB cleanup steps, so that
`delete_listenbrainz.py` has an accurate keep set.

```
python export_db_to_history.py           # dry run — prints row count
python export_db_to_history.py --confirm # write merged_history.json
```

**`delete_listenbrainz.py`**
Deletes plays from ListenBrainz that exist in `import_checkpoint.pkl` (previously
submitted) but not in `merged_history.json` (the current clean keep set). Uses a
window-paging algorithm to fetch LB listens and delete them one at a time. Rate-limit
aware; saves progress after each batch so it can be safely interrupted and resumed.

**`import_listenbrainz.py`**
Imports entries from `merged_history.json` that are not already in
`import_checkpoint.pkl`. Batches of up to 1,000 per LB API request. Rate-limit aware.

```
python import_listenbrainz.py              # normal mode (with Pano de-dup check)
python import_listenbrainz.py --skip-dedup # use after export_db_to_history.py
```

`--skip-dedup` bypasses the local-DB de-dup check. Use it whenever
`merged_history.json` was generated by `export_db_to_history.py` (i.e. it IS the DB),
because the de-dup check would otherwise flag every entry as "already scrobbled by
Pano" and import nothing. Without `--skip-dedup` (the default), the script skips
entries that appear in the local DB within ±60 seconds, guarding against
double-importing plays already submitted by Pano Scrobbler.

**`clean_listenbrainz_scrobbles.py`**
Scans all scrobbles on LB, identifies entries where `clean_artist`/`clean_title`
would produce a different value (featuring credits, video tags, etc.), deletes the
dirty scrobble, and resubmits the clean version. Updates `import_checkpoint.pkl`.
Idempotent — safe to run multiple times; a second run finds nothing dirty and exits.

---

### Dev tooling

**`run_dev.py`**
Starts the FastAPI development server.

**`generate_openapi.py`**
Generates `openapi.json` from the FastAPI app's schema. Run after adding or
changing API endpoints.

---

## Checkpoint files

| File | Purpose |
|---|---|
| `backend/import_checkpoint.pkl` | Set of `(unix_ts, artist, title)` tuples submitted to LB. Source of truth for what's on LB. Updated by `import_listenbrainz.py`, `delete_listenbrainz.py`, and `clean_listenbrainz_scrobbles.py`. |
| `backend/merged_history.json` | Consolidated listen history. Either merged from source exports (`merge_history.py`) or mirrored from DB (`export_db_to_history.py`). Input to the LB import/delete scripts. |
| `backend/scripts/backfill_results.json` | Per-track MB lookup results with action codes. Read by `apply_skipped_updates.py`. |
| `backend/scripts/backfill_failures.json` | Tracks for which MB returned no results. Read by `generate_review_csv.py`. |
| `backend/scripts/skipped_updates_review.csv` | Human-edited review file for `apply_skipped_updates.py`. |
| `backend/scripts/failure_review.csv` | Human-edited review file for `apply_review_decisions.py`. |
| `backend/scripts/fix_retry.json` | Corrected entries written by `apply_review_decisions.py` for backfill retry. |
