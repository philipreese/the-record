import asyncio
import os
import traceback
from dataclasses import dataclass
from typing import Optional, Any

import httpx

from app.db import get_db_connection
from app.repository import deduplicate_listens

LISTENBRAINZ_USERNAME = os.getenv("LISTENBRAINZ_USERNAME")
LISTENBRAINZ_TOKEN = os.getenv("LISTENBRAINZ_TOKEN")

@dataclass
class SyncState:
    running: bool = False
    mode: str = ""
    batches_fetched: int = 0
    synced_count: int = 0
    lb_total: int = 0
    local_total: int = 0
    error: Optional[str] = None
    finished: bool = False

_sync_state = SyncState()

async def _run_sync(mode: str) -> None:
    """
    Long-running async sync task. Runs in the background so the HTTP response
    can be returned immediately. Updates _sync_state throughout.

    Strategy:
    - "full"   : scan every page from LB (newest→oldest), deduplicate against local DB.
    - "normal" : two-pass approach —
        Pass A (backfill): if LB has more entries than local DB, jump directly to
          MIN(local unix_ts) and fetch only entries older than that. This avoids
          re-scanning the 45k already-known recent records.
        Pass B (forward): fast scan from newest LB entry down to MAX(local unix_ts)
          to capture any brand-new scrobbles added since the last sync.
    """
    global _sync_state

    if not LISTENBRAINZ_USERNAME or not LISTENBRAINZ_TOKEN:
        _sync_state.error = "Credentials missing. Configure LISTENBRAINZ_USERNAME and LISTENBRAINZ_TOKEN."
        _sync_state.running = False
        _sync_state.finished = True
        return

    headers = {
        "Authorization": f"Token {LISTENBRAINZ_TOKEN}",
        "User-Agent": "the-record-dashboard-sync/1.0",
    }
    _timeout = httpx.Timeout(60.0)

    try:
        async with httpx.AsyncClient(timeout=_timeout) as client:
            # 1. Fetch total count from ListenBrainz
            lb_total_count = 0
            try:
                count_url = f"https://api.listenbrainz.org/1/user/{LISTENBRAINZ_USERNAME}/listen-count"
                count_res = await client.get(count_url, headers=headers)
                count_res.raise_for_status()
                lb_total_count = count_res.json().get("payload", {}).get("count", 0)
            except Exception:
                traceback.print_exc()

            _sync_state.lb_total = lb_total_count

            # 2. Load local state helper
            def load_local_state() -> tuple[int, int, int, set[tuple[int, str, str]]]:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM listens")
                local_cnt = cursor.fetchone()[0]
                cursor.execute("SELECT MAX(unix_ts), MIN(unix_ts) FROM listens")
                ts_row = cursor.fetchone()
                lat_ts = ts_row[0] if ts_row and ts_row[0] is not None else 0
                old_ts = ts_row[1] if ts_row and ts_row[1] is not None else 0
                cursor.execute("SELECT unix_ts, artist, title FROM listens")
                loc_keys = {
                    (row[0], row[1].lower(), row[2].lower()) for row in cursor.fetchall()
                }
                conn.close()
                return local_cnt, lat_ts, old_ts, loc_keys

            local_count, latest_ts, oldest_ts, local_keys = load_local_state()
            _sync_state.local_total = local_count

            batch_size = 1000
            new_listens: list[tuple[str, str, int, str]] = []

            async def _fetch_page(max_ts: Optional[int], retries: int = 5) -> list[dict[str, Any]]:
                """
                Fetch one batch from LB using the shared connection client.
                Retries up to `retries` times on transient connection errors.
                Returns the listen list or [] if a terminal error occurs.
                """
                url = (
                    f"https://api.listenbrainz.org/1/user/{LISTENBRAINZ_USERNAME}"
                    f"/listens?count={batch_size}"
                )
                if max_ts:
                    url += f"&max_ts={max_ts}"
                for attempt in range(retries):
                    try:
                        response = await client.get(url, headers=headers)
                        if response.status_code == 429:
                            reset_in = response.headers.get("X-RateLimit-Reset-In", "5")
                            _sync_state.error = f"Rate-limited by ListenBrainz. Retry in {reset_in}s."
                            return []
                        response.raise_for_status()
                        return response.json().get("payload", {}).get("listens", [])
                    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError) as e:
                        if attempt < retries - 1:
                            wait = [5, 15, 30, 60, 120][attempt]  # generous backoff for LB rate limiting/connection issues
                            print(f"[sync] Transient error ({e}), retrying in {wait}s (attempt {attempt + 1}/{retries})")
                            await asyncio.sleep(wait)
                        else:
                            _sync_state.error = f"ListenBrainz API unreachable after {retries} attempts: {e}"
                            return []
                    except httpx.HTTPStatusError as e:
                        _sync_state.error = f"ListenBrainz API error {e.response.status_code}: {e}"
                        return []
                    except Exception as e:
                        traceback.print_exc()
                        _sync_state.error = f"Unexpected error: {e}"
                        return []
                return []

            def persist_listens(listens_to_insert: list[tuple[str, str, int, str]]) -> None:
                if not listens_to_insert:
                    return
                listens_to_insert.sort(key=lambda x: x[2])
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.executemany(
                    "INSERT INTO listens (artist, title, unix_ts, source) VALUES (?, ?, ?, ?)",
                    listens_to_insert,
                )
                conn.commit()
                conn.close()

            full_mode = (mode == "full")

            if full_mode:
                current_max_ts: Optional[int] = None
                while True:
                    listens = await _fetch_page(current_max_ts)
                    if not listens or _sync_state.error:
                        break
                    _sync_state.batches_fetched += 1

                    for listen in listens:
                        ts = listen.get("listened_at")
                        if ts is None:
                            continue
                        meta = listen.get("track_metadata", {})
                        artist = meta.get("artist_name")
                        title = meta.get("track_name")
                        if artist and title:
                            key = (ts, artist.lower(), title.lower())
                            if key not in local_keys:
                                new_listens.append((artist, title, ts, "listenbrainz_sync"))
                                local_keys.add(key)

                    if len(listens) < batch_size:
                        break
                    current_max_ts = listens[-1].get("listened_at")
                    await asyncio.sleep(2)
            else:
                # Normal mode: Two passes
                # Pass 1: Forward Sync (scan newest down to latest_ts)
                current_max_ts = None
                stop_scan = False
                while True:
                    listens = await _fetch_page(current_max_ts)
                    if not listens or _sync_state.error:
                        break
                    _sync_state.batches_fetched += 1

                    for listen in listens:
                        ts = listen.get("listened_at")
                        if ts is None:
                            continue

                        # Stop once we hit the most recent local listen watermark
                        if ts <= latest_ts:
                            stop_scan = True
                            break

                        meta = listen.get("track_metadata", {})
                        artist = meta.get("artist_name")
                        title = meta.get("track_name")
                        if artist and title:
                            key = (ts, artist.lower(), title.lower())
                            if key not in local_keys:
                                new_listens.append((artist, title, ts, "listenbrainz_sync"))
                                local_keys.add(key)

                    if stop_scan or len(listens) < batch_size:
                        break
                    current_max_ts = listens[-1].get("listened_at")
                    await asyncio.sleep(2)

                # Persist Pass 1 results before checking Pass 2
                if new_listens:
                    persist_listens(new_listens)
                    _sync_state.synced_count += len(new_listens)
                    new_listens.clear()
                    # Reload counts
                    local_count, latest_ts, oldest_ts, local_keys = load_local_state()
                    _sync_state.local_total = local_count

                # Pass 2: Backfill Sync (if a gap remains, scan from oldest_ts downwards)
                print(f"[sync] Pass 2 check: lb_total_count={lb_total_count}, local_count={local_count}, oldest_ts={oldest_ts}")
                if lb_total_count > local_count:
                    missing_remaining = lb_total_count - local_count
                    current_max_ts = oldest_ts
                    print(f"[sync] Pass 2 starting: missing_remaining={missing_remaining}, current_max_ts={current_max_ts}")
                    while True:
                        listens = await _fetch_page(current_max_ts)
                        if not listens or _sync_state.error:
                            print(f"[sync] Pass 2 fetch returned no listens or error occurred. Error: {_sync_state.error}")
                            break
                        _sync_state.batches_fetched += 1
                        print(f"[sync] Pass 2 fetched batch {_sync_state.batches_fetched}, count={len(listens)}")

                        for listen in listens:
                            ts = listen.get("listened_at")
                            if ts is None:
                                continue

                            meta = listen.get("track_metadata", {})
                            artist = meta.get("artist_name")
                            title = meta.get("track_name")
                            if artist and title:
                                key = (ts, artist.lower(), title.lower())
                                if key not in local_keys:
                                    new_listens.append((artist, title, ts, "listenbrainz_sync"))
                                    local_keys.add(key)
                                    missing_remaining -= 1

                        if missing_remaining <= 0 or len(listens) < batch_size:
                            print(f"[sync] Pass 2 stop condition met. missing_remaining={missing_remaining}, len(listens)={len(listens)}")
                            break
                        current_max_ts = listens[-1].get("listened_at")
                        await asyncio.sleep(2)
                else:
                    print("[sync] Pass 2 skipped because condition not met.")

            # 5. Persist any remaining new entries
            if new_listens:
                persist_listens(new_listens)
                _sync_state.synced_count += len(new_listens)

            # 6. Post-sync cleanup for duplicate plays (e.g. from multiple scrobbler apps)
            deleted_dupes = deduplicate_listens()
            if deleted_dupes > 0:
                print(f"[sync] Post-sync cleanup: Removed {deleted_dupes} duplicate play(s).")

            print(
                f"[sync] Done — fetched {_sync_state.batches_fetched} batch(es), "
                f"inserted {_sync_state.synced_count} new play(s)."
            )

    except Exception as e:
        traceback.print_exc()
        _sync_state.error = f"Sync crashed: {e}"
    finally:
        _sync_state.running = False
        _sync_state.finished = True
