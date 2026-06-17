import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional, Any

logger = logging.getLogger(__name__)

import httpx

from sqlalchemy import func, text
from app.db import get_session, get_engine, Listen
from app.repository import deduplicate_listens

LISTENBRAINZ_USERNAME = os.getenv("LISTENBRAINZ_USERNAME")
LISTENBRAINZ_TOKEN = os.getenv("LISTENBRAINZ_TOKEN")

@dataclass
class SyncState:
    running: bool = False
    mode: str = ""
    batches_fetched: int = 0
    synced_count: int = 0
    deleted_count: int = 0
    lb_total: int = 0
    local_total: int = 0
    error: Optional[str] = None
    finished: bool = False

_sync_state = SyncState()
_sync_lock = asyncio.Lock()

def _parse_duration(additional_info: dict) -> Optional[int]:
    """Return duration in whole seconds from LB additional_info.
    LB sends either duration_ms (milliseconds) or duration (seconds)."""
    raw_ms = additional_info.get("duration_ms")
    if raw_ms is not None:
        try:
            return int(float(raw_ms) / 1000)
        except (ValueError, TypeError):
            pass
    raw_s = additional_info.get("duration")
    if raw_s is not None:
        try:
            return int(float(raw_s))
        except (ValueError, TypeError):
            pass
    return None

async def _run_sync(mode: str) -> None:
    """
    Normal (incremental) sync: two-pass additive approach.
    Pass A (forward): fetch from newest LB entry down to the local watermark.
    Pass B (backfill): if LB total > local count, scan from oldest local ts downward.
    """

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
                logger.exception("LB listen-count fetch failed")

            _sync_state.lb_total = lb_total_count

            # 2. Load local state helper
            def load_local_state() -> tuple[int, int, int, set[tuple[int, str, str]]]:
                session = get_session()
                try:
                    local_cnt = session.query(func.count(Listen.id)).scalar() or 0
                    ts_row = session.query(func.max(Listen.unix_ts), func.min(Listen.unix_ts)).first()
                    lat_ts = ts_row[0] if ts_row and ts_row[0] is not None else 0
                    old_ts = ts_row[1] if ts_row and ts_row[1] is not None else 0
                    rows = session.query(Listen.unix_ts, Listen.artist, Listen.title).all()
                    loc_keys = {
                        (row.unix_ts, row.artist.lower(), row.title.lower()) for row in rows
                    }
                    return local_cnt, lat_ts, old_ts, loc_keys
                finally:
                    session.close()

            local_count, latest_ts, oldest_ts, local_keys = load_local_state()
            _sync_state.local_total = local_count

            batch_size = 1000
            new_listens: list[dict[str, Any]] = []

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
                            logger.warning("Transient error (%s), retrying in %ds (attempt %d/%d)", e, wait, attempt + 1, retries)
                            await asyncio.sleep(wait)
                        else:
                            _sync_state.error = f"ListenBrainz API unreachable after {retries} attempts: {e}"
                            return []
                    except httpx.HTTPStatusError as e:
                        _sync_state.error = f"ListenBrainz API error {e.response.status_code}: {e}"
                        return []
                    except Exception as e:
                        logger.exception("Unexpected error fetching LB page")
                        _sync_state.error = f"Unexpected error: {e}"
                        return []
                return []

            def persist_listens(listens_to_insert: list[dict[str, Any]]) -> None:
                if not listens_to_insert:
                    return
                listens_to_insert.sort(key=lambda x: x["unix_ts"])
                session = get_session()
                try:
                    objects = [
                        Listen(
                            artist=item["artist"],
                            title=item["title"],
                            unix_ts=item["unix_ts"],
                            source=item["source"],
                            duration_secs=item.get("duration_secs"),
                            album=item.get("album")
                        )
                        for item in listens_to_insert
                    ]
                    session.bulk_save_objects(objects)
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
                finally:
                    session.close()

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
                            additional_info = meta.get("additional_info") or {}
                            duration_secs = _parse_duration(additional_info)
                            album = meta.get("release_name")
                            if album and isinstance(album, str):
                                album = album.strip()
                                if not album:
                                    album = None
                            else:
                                album = None
                            new_listens.append({
                                "artist": artist,
                                "title": title,
                                "unix_ts": ts,
                                "source": "listenbrainz_sync",
                                "duration_secs": duration_secs,
                                "album": album
                            })
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
                local_count, latest_ts, oldest_ts, local_keys = load_local_state()
                _sync_state.local_total = local_count

            # Pass 2: Backfill (if LB total > local count, scan from oldest_ts downward)
            logger.debug("Pass 2 check: lb_total_count=%d, local_count=%d, oldest_ts=%d", lb_total_count, local_count, oldest_ts)
            if lb_total_count > local_count:
                missing_remaining = lb_total_count - local_count
                current_max_ts = oldest_ts
                logger.info("Pass 2 starting: missing_remaining=%d, current_max_ts=%s", missing_remaining, current_max_ts)
                while True:
                    listens = await _fetch_page(current_max_ts)
                    if not listens or _sync_state.error:
                        logger.warning("Pass 2 fetch returned no listens or error occurred. Error: %s", _sync_state.error)
                        break
                    _sync_state.batches_fetched += 1
                    logger.debug("Pass 2 fetched batch %d, count=%d", _sync_state.batches_fetched, len(listens))

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
                                additional_info = meta.get("additional_info") or {}
                                duration_secs = _parse_duration(additional_info)
                                album = meta.get("release_name")
                                if album and isinstance(album, str):
                                    album = album.strip()
                                    if not album:
                                        album = None
                                else:
                                    album = None
                                new_listens.append({
                                    "artist": artist,
                                    "title": title,
                                    "unix_ts": ts,
                                    "source": "listenbrainz_sync",
                                    "duration_secs": duration_secs,
                                    "album": album
                                })
                                local_keys.add(key)
                                missing_remaining -= 1

                    if missing_remaining <= 0 or len(listens) < batch_size:
                        logger.debug("Pass 2 stop condition met. missing_remaining=%d, len(listens)=%d", missing_remaining, len(listens))
                        break
                    current_max_ts = listens[-1].get("listened_at")
                    await asyncio.sleep(2)
            else:
                logger.debug("Pass 2 skipped: lb_total_count=%d <= local_count=%d", lb_total_count, local_count)

            # 5. Persist any remaining new entries
            if new_listens:
                persist_listens(new_listens)
                _sync_state.synced_count += len(new_listens)

            # 6. Post-sync cleanup for duplicate plays (e.g. from multiple scrobbler apps)
            deleted_dupes = deduplicate_listens()
            if deleted_dupes > 0:
                logger.info("Post-sync cleanup: removed %d duplicate play(s)", deleted_dupes)

            logger.info(
                "Done — fetched %d batch(es), inserted %d new play(s)",
                _sync_state.batches_fetched,
                _sync_state.synced_count,
            )

    except Exception as e:
        logger.exception("Sync crashed")
        _sync_state.error = f"Sync crashed: {e}"
    finally:
        _sync_state.running = False
        _sync_state.finished = True


async def _run_mirror() -> None:
    """
    Full mirror sync: make the local DB an exact copy of ListenBrainz.
    Fetches all LB pages (newest to oldest), inserts any rows missing locally,
    then deletes any local rows not found on LB.

    No source restriction — all local rows across all sources are compared
    against LB, since LB is treated as the single source of truth.

    Identity key: (unix_ts, artist.lower(), title.lower())
    """
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
            # 1. Fetch total count for progress display
            try:
                count_res = await client.get(
                    f"https://api.listenbrainz.org/1/user/{LISTENBRAINZ_USERNAME}/listen-count",
                    headers=headers,
                )
                count_res.raise_for_status()
                _sync_state.lb_total = count_res.json().get("payload", {}).get("count", 0)
            except Exception:
                logger.exception("LB listen-count fetch failed")

            # 2. Load all local rows: key -> id (all sources)
            session = get_session()
            try:
                rows = session.query(Listen.id, Listen.unix_ts, Listen.artist, Listen.title).all()
            finally:
                session.close()

            local_key_to_id: dict[tuple[int, str, str], int] = {
                (r.unix_ts, r.artist.lower(), r.title.lower()): r.id for r in rows
            }
            local_keys: set[tuple[int, str, str]] = set(local_key_to_id.keys())
            _sync_state.local_total = len(local_key_to_id)

            # 3. Fetch all LB pages and collect rows to insert
            lb_keys: set[tuple[int, str, str]] = set()
            new_listens: list[dict[str, Any]] = []
            batch_size = 1000
            current_max_ts: Optional[int] = None

            while True:
                url = (
                    f"https://api.listenbrainz.org/1/user/{LISTENBRAINZ_USERNAME}"
                    f"/listens?count={batch_size}"
                )
                if current_max_ts:
                    url += f"&max_ts={current_max_ts}"

                listens: list[dict[str, Any]] = []
                for attempt in range(5):
                    try:
                        response = await client.get(url, headers=headers)
                        if response.status_code == 429:
                            reset_in = response.headers.get("X-RateLimit-Reset-In", "5")
                            _sync_state.error = f"Rate-limited by ListenBrainz. Retry in {reset_in}s."
                            return
                        response.raise_for_status()
                        listens = response.json().get("payload", {}).get("listens", [])
                        break
                    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError) as e:
                        if attempt < 4:
                            wait = [5, 15, 30, 60, 120][attempt]
                            logger.warning("Transient error (%s), retrying in %ds", e, wait)
                            await asyncio.sleep(wait)
                        else:
                            _sync_state.error = f"ListenBrainz API unreachable after 5 attempts: {e}"
                            return
                    except Exception as e:
                        _sync_state.error = f"Unexpected error: {e}"
                        return

                if not listens:
                    break

                _sync_state.batches_fetched += 1
                for listen in listens:
                    ts = listen.get("listened_at")
                    if ts is None:
                        continue
                    meta = listen.get("track_metadata", {})
                    artist = meta.get("artist_name", "")
                    title = meta.get("track_name", "")
                    if not artist or not title:
                        continue
                    key: tuple[int, str, str] = (ts, artist.lower(), title.lower())
                    lb_keys.add(key)
                    if key not in local_keys:
                        additional_info = meta.get("additional_info") or {}
                        duration_secs = _parse_duration(additional_info)
                        album = meta.get("release_name")
                        if album and isinstance(album, str):
                            album = album.strip() or None
                        else:
                            album = None
                        new_listens.append({
                            "artist": artist,
                            "title": title,
                            "unix_ts": ts,
                            "source": "listenbrainz_sync",
                            "duration_secs": duration_secs,
                            "album": album,
                        })
                        local_keys.add(key)

                if len(listens) < batch_size:
                    break
                current_max_ts = listens[-1].get("listened_at")
                await asyncio.sleep(2)

        # 4. Insert missing rows
        if new_listens:
            new_listens.sort(key=lambda x: x["unix_ts"])
            session = get_session()
            try:
                session.bulk_save_objects([
                    Listen(
                        artist=item["artist"],
                        title=item["title"],
                        unix_ts=item["unix_ts"],
                        source=item["source"],
                        duration_secs=item.get("duration_secs"),
                        album=item.get("album"),
                    )
                    for item in new_listens
                ])
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
            _sync_state.synced_count = len(new_listens)
            logger.info("Mirror: inserted %d missing row(s)", len(new_listens))

        # 5. Dedup
        deleted_dupes = deduplicate_listens()
        if deleted_dupes > 0:
            logger.info("Mirror: post-sync dedup removed %d duplicate(s)", deleted_dupes)

        # 6. Delete surplus local rows (not on LB)
        surplus_ids = [row_id for key, row_id in local_key_to_id.items() if key not in lb_keys]
        if surplus_ids:
            with get_engine().begin() as conn:
                conn.execute(
                    text("DELETE FROM listens WHERE id IN :ids"),
                    {"ids": tuple(surplus_ids)},
                )
            _sync_state.deleted_count = len(surplus_ids)
            logger.info("Mirror: deleted %d surplus local row(s)", len(surplus_ids))
        else:
            logger.info("Mirror: no surplus rows — local DB matches ListenBrainz")

        logger.info(
            "Mirror done — %d batch(es), +%d inserted, -%d deleted",
            _sync_state.batches_fetched,
            _sync_state.synced_count,
            _sync_state.deleted_count,
        )

    except Exception as e:
        logger.exception("Mirror sync crashed")
        _sync_state.error = f"Mirror sync crashed: {e}"
    finally:
        _sync_state.running = False
        _sync_state.finished = True
