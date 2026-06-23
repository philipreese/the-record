import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional, Any

logger = logging.getLogger(__name__)

import httpx

from sqlalchemy import func, text, bindparam, update
from app.db import get_session, get_engine, Listen
from app.repository import deduplicate_listens
from app.utils import clean_artist, clean_title

LISTENBRAINZ_USERNAME = os.getenv("LISTENBRAINZ_USERNAME")
LISTENBRAINZ_TOKEN = os.getenv("LISTENBRAINZ_TOKEN")

@dataclass
class SyncState:
    running: bool = False
    mode: str = ""
    batches_fetched: int = 0
    synced_count: int = 0
    updated_count: int = 0
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

def _extract_recording_mbid(meta: dict) -> Optional[str]:
    """Resolve a track's MusicBrainz Recording ID from LB track_metadata.

    Prefer LB's own server-side match in mbid_mapping (populated for ~most
    listens, including import-sourced ones); fall back to a submitter-provided
    value in additional_info."""
    mapped = (meta.get("mbid_mapping") or {}).get("recording_mbid")
    if mapped:
        return mapped
    return (meta.get("additional_info") or {}).get("recording_mbid")

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

            local_count, latest_ts, oldest_ts, local_keys = await asyncio.to_thread(load_local_state)
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
                            album=item.get("album"),
                            recording_mbid=item.get("recording_mbid"),
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
                        artist = clean_artist(artist)
                        title = clean_title(title)
                        key = (ts, artist.lower(), title.lower())
                        if key not in local_keys:
                            additional_info = meta.get("additional_info") or {}
                            duration_secs = _parse_duration(additional_info)
                            recording_mbid = _extract_recording_mbid(meta)
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
                                "album": album,
                                "recording_mbid": recording_mbid,
                            })
                            local_keys.add(key)

                if stop_scan or len(listens) < batch_size:
                    break
                current_max_ts = listens[-1].get("listened_at")
                await asyncio.sleep(2)

            # Persist Pass 1 results before checking Pass 2
            if new_listens:
                await asyncio.to_thread(persist_listens, new_listens)
                _sync_state.synced_count += len(new_listens)
                new_listens.clear()
                local_count, latest_ts, oldest_ts, local_keys = await asyncio.to_thread(load_local_state)
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
                            artist = clean_artist(artist)
                            title = clean_title(title)
                            key = (ts, artist.lower(), title.lower())
                            if key not in local_keys:
                                additional_info = meta.get("additional_info") or {}
                                duration_secs = _parse_duration(additional_info)
                                recording_mbid = _extract_recording_mbid(meta)
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
                                    "album": album,
                                    "recording_mbid": recording_mbid,
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
                await asyncio.to_thread(persist_listens, new_listens)
                _sync_state.synced_count += len(new_listens)

            # 6. Post-sync cleanup: only needed when new rows were inserted, since
            # duplicates can only arise from fresh inserts (two scrobbler apps
            # submitting the same listen with slightly different timestamps).
            if _sync_state.synced_count > 0:
                deleted_dupes = await asyncio.to_thread(deduplicate_listens)
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
    Fetches all LB pages (newest to oldest), inserts missing rows incrementally,
    backfills missing duration/album metadata, then deletes any local rows not
    found on LB (including exact-key duplicates, keeping the lowest id).

    No source restriction — all local rows are compared against LB.
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
            # 1. Fetch total count for progress display (retry on transient failures)
            count_url = f"https://api.listenbrainz.org/1/user/{LISTENBRAINZ_USERNAME}/listen-count"
            for _attempt in range(3):
                try:
                    count_res = await client.get(count_url, headers=headers)
                    count_res.raise_for_status()
                    _sync_state.lb_total = count_res.json().get("payload", {}).get("count", 0)
                    break
                except Exception as e:
                    if _attempt < 2:
                        logger.warning("LB listen-count fetch failed (%s), retrying...", e)
                        await asyncio.sleep(5)
                    else:
                        logger.exception("LB listen-count fetch failed after 3 attempts")

            # 2. Load all local rows: key -> list of (id, duration_secs, album).
            # A list per key handles exact duplicates (same ts/artist/title) correctly —
            # a plain dict silently drops all but one id for duplicate keys.
            def _load_local() -> dict[tuple[int, str, str], list[tuple[int, Optional[int], Optional[str], Optional[str]]]]:
                session = get_session()
                try:
                    rows = session.query(
                        Listen.id, Listen.unix_ts, Listen.artist, Listen.title,
                        Listen.duration_secs, Listen.album, Listen.recording_mbid,
                    ).all()
                    result: dict[tuple[int, str, str], list[tuple[int, Optional[int], Optional[str], Optional[str]]]] = {}
                    for r in rows:
                        key = (r.unix_ts, r.artist.lower(), r.title.lower())
                        result.setdefault(key, []).append((r.id, r.duration_secs, r.album, r.recording_mbid))
                    return result
                finally:
                    session.close()

            local_key_to_entries = await asyncio.to_thread(_load_local)
            local_key_set: set[tuple[int, str, str]] = set(local_key_to_entries.keys())
            _sync_state.local_total = sum(len(v) for v in local_key_to_entries.values())

            # 3. Fetch all LB pages; insert missing rows after each page so the
            # synced_count counter updates live rather than only at the end.
            lb_keys: set[tuple[int, str, str]] = set()
            lb_metadata: dict[tuple[int, str, str], tuple[Optional[int], Optional[str], Optional[str]]] = {}
            seen_new_keys: set[tuple[int, str, str]] = set()
            batch_size = 1000
            current_max_ts: Optional[int] = None

            def _insert_batch(rows: list[dict[str, Any]]) -> None:
                rows.sort(key=lambda x: x["unix_ts"])
                session = get_session()
                try:
                    for i in range(0, len(rows), 5000):
                        chunk = rows[i:i + 5000]
                        session.bulk_save_objects([
                            Listen(
                                artist=item["artist"],
                                title=item["title"],
                                unix_ts=item["unix_ts"],
                                source=item["source"],
                                duration_secs=item.get("duration_secs"),
                                album=item.get("album"),
                                recording_mbid=item.get("recording_mbid"),
                            )
                            for item in chunk
                        ])
                        session.flush()
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
                finally:
                    session.close()

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
                page_new: list[dict[str, Any]] = []

                for listen in listens:
                    ts = listen.get("listened_at")
                    if ts is None:
                        continue
                    meta = listen.get("track_metadata", {})
                    artist = meta.get("artist_name", "")
                    title = meta.get("track_name", "")
                    if not artist or not title:
                        continue

                    additional_info = meta.get("additional_info") or {}
                    duration_secs = _parse_duration(additional_info)
                    recording_mbid = _extract_recording_mbid(meta)
                    album = meta.get("release_name")
                    if album and isinstance(album, str):
                        album = album.strip() or None
                    else:
                        album = None

                    key: tuple[int, str, str] = (ts, artist.lower(), title.lower())
                    lb_keys.add(key)
                    lb_metadata[key] = (duration_secs, album, recording_mbid)

                    if key not in local_key_set and key not in seen_new_keys:
                        page_new.append({
                            "artist": artist,
                            "title": title,
                            "unix_ts": ts,
                            "source": "listenbrainz_sync",
                            "duration_secs": duration_secs,
                            "album": album,
                            "recording_mbid": recording_mbid,
                        })
                        seen_new_keys.add(key)

                if page_new:
                    await asyncio.to_thread(_insert_batch, page_new)
                    _sync_state.synced_count += len(page_new)

                if len(listens) < batch_size:
                    break
                current_max_ts = listens[-1].get("listened_at")
                await asyncio.sleep(2)

        # 4. Compute surplus IDs and metadata updates now that lb_keys is complete.
        surplus_ids: list[int] = []
        update_rows: list[tuple[int, Optional[int], Optional[str], Optional[str]]] = []

        for key, entries in local_key_to_entries.items():
            entries_sorted = sorted(entries, key=lambda e: e[0])  # lowest id = canonical

            if key in lb_keys:
                # Keep the canonical row; any extras are exact duplicates → delete.
                surplus_ids.extend(e[0] for e in entries_sorted[1:])

                # Backfill duration/album/recording_mbid on the canonical row if LB
                # has them and we don't.
                canonical_id, local_dur, local_alb, local_mbid = entries_sorted[0]
                lb_dur, lb_alb, lb_mbid = lb_metadata.get(key, (None, None, None))
                new_dur = lb_dur if local_dur is None and lb_dur is not None else local_dur
                new_alb = lb_alb if local_alb is None and lb_alb is not None else local_alb
                new_mbid = lb_mbid if local_mbid is None and lb_mbid is not None else local_mbid
                if new_dur != local_dur or new_alb != local_alb or new_mbid != local_mbid:
                    update_rows.append((canonical_id, new_dur, new_alb, new_mbid))
            else:
                # Key not on LB → delete all local copies regardless of count.
                surplus_ids.extend(e[0] for e in entries_sorted)

        # 5. Execute metadata updates
        if update_rows:
            def _update(rows: list[tuple[int, Optional[int], Optional[str], Optional[str]]]) -> None:
                # ORM bulk update by primary key, chunked and committed per chunk.
                # A per-row loop here meant ~50k round-trips in one transaction over
                # the remote Postgres connection, which took 15+ min and risked the
                # whole thing timing out and rolling back. executemany batches make
                # it seconds; chunked commits keep locks short and persist progress.
                session = get_session()
                try:
                    for i in range(0, len(rows), 5000):
                        chunk = rows[i:i + 5000]
                        session.execute(
                            update(Listen),
                            [
                                {
                                    "id": row_id,
                                    "duration_secs": duration,
                                    "album": album,
                                    "recording_mbid": recording_mbid,
                                }
                                for row_id, duration, album, recording_mbid in chunk
                            ],
                        )
                        session.commit()
                except Exception:
                    session.rollback()
                    raise
                finally:
                    session.close()

            await asyncio.to_thread(_update, update_rows)
            _sync_state.updated_count = len(update_rows)
            logger.info("Mirror: backfilled metadata for %d row(s)", len(update_rows))

        # 6. Delete surplus rows in chunks to avoid SQLite's bound-variable limit (~999).
        if surplus_ids:
            def _delete(ids: list[int]) -> None:
                with get_engine().begin() as conn:
                    for i in range(0, len(ids), 900):
                        chunk = ids[i:i + 900]
                        conn.execute(
                            text("DELETE FROM listens WHERE id IN :ids").bindparams(
                                bindparam("ids", expanding=True)
                            ),
                            {"ids": chunk},
                        )

            await asyncio.to_thread(_delete, surplus_ids)
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


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    # Module-level os.getenv() ran before load_dotenv — re-read now
    LISTENBRAINZ_USERNAME = os.getenv("LISTENBRAINZ_USERNAME")
    LISTENBRAINZ_TOKEN = os.getenv("LISTENBRAINZ_TOKEN")

    parser = argparse.ArgumentParser(description="Run ListenBrainz sync standalone")
    parser.add_argument("--mode", choices=["normal", "mirror"], default="normal")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s",
                        stream=__import__("sys").stdout)

    _sync_state.running = True
    _sync_state.finished = False

    asyncio.run(_run_sync(args.mode) if args.mode == "normal" else _run_mirror())

    if _sync_state.error:
        print(f"ERROR: {_sync_state.error}")
        raise SystemExit(1)
    print(f"Done — inserted {_sync_state.synced_count} new play(s), deleted {_sync_state.deleted_count}")
