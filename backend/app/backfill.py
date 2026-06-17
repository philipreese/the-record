import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

import httpx
from sqlalchemy import select, update, or_

from app.db import get_session, Listen
from app.sync import LISTENBRAINZ_USERNAME, LISTENBRAINZ_TOKEN, _parse_duration

logger = logging.getLogger(__name__)

_UA = "the-record-dashboard-backfill/1.0"


@dataclass
class BackfillState:
    running: bool = False
    batches_fetched: int = 0
    rows_updated: int = 0
    rows_to_update: int = 0
    error: Optional[str] = None
    finished: bool = False


_backfill_state = BackfillState()
_backfill_lock = asyncio.Lock()


async def _run_backfill() -> None:
    if not LISTENBRAINZ_USERNAME or not LISTENBRAINZ_TOKEN:
        _backfill_state.error = "Credentials missing. Configure LISTENBRAINZ_USERNAME and LISTENBRAINZ_TOKEN."
        _backfill_state.running = False
        _backfill_state.finished = True
        return

    # Load all rows that have at least one null field.
    session = get_session()
    try:
        rows = session.execute(
            select(Listen.id, Listen.unix_ts, Listen.artist, Listen.title, Listen.duration_secs, Listen.album)
            .where(or_(Listen.duration_secs.is_(None), Listen.album.is_(None)))
        ).all()
    finally:
        session.close()

    if not rows:
        logger.info("Backfill: no rows need updating.")
        _backfill_state.rows_to_update = 0
        _backfill_state.finished = True
        _backfill_state.running = False
        return

    # Build lookup keyed by (unix_ts, artist_lower, title_lower) → list of row descriptors.
    # Multiple rows may share a timestamp, so we use lists.
    lookup: dict[tuple[int, str, str], list[dict[str, Any]]] = {}
    for r in rows:
        key = (r.unix_ts, r.artist.casefold(), r.title.casefold())
        lookup.setdefault(key, []).append({
            "id": r.id,
            "need_duration": r.duration_secs is None,
            "need_album": r.album is None,
        })

    oldest_ts = min(r.unix_ts for r in rows)
    _backfill_state.rows_to_update = len(rows)
    logger.info("Backfill: %d row(s) need updating; oldest ts=%d", len(rows), oldest_ts)

    headers = {
        "Authorization": f"Token {LISTENBRAINZ_TOKEN}",
        "User-Agent": _UA,
    }
    batch_size = 1000
    pending_updates: list[dict[str, Any]] = []

    def flush() -> None:
        if not pending_updates:
            return
        s = get_session()
        try:
            for upd in pending_updates:
                row_id = upd.pop("id")
                s.execute(update(Listen).where(Listen.id == row_id).values(**upd))
            s.commit()
            _backfill_state.rows_updated += len(pending_updates)
            logger.debug("Backfill: flushed %d update(s), total=%d", len(pending_updates), _backfill_state.rows_updated)
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()
        pending_updates.clear()

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            current_max_ts: Optional[int] = None

            while lookup:
                url = (
                    f"https://api.listenbrainz.org/1/user/{LISTENBRAINZ_USERNAME}"
                    f"/listens?count={batch_size}"
                )
                if current_max_ts:
                    url += f"&max_ts={current_max_ts}"

                listens: list[dict[str, Any]] = []
                for attempt in range(5):
                    try:
                        res = await client.get(url, headers=headers)
                        if res.status_code == 429:
                            reset_in = res.headers.get("X-RateLimit-Reset-In", "5")
                            _backfill_state.error = f"Rate-limited by ListenBrainz. Retry in {reset_in}s."
                            return
                        res.raise_for_status()
                        listens = res.json().get("payload", {}).get("listens", [])
                        break
                    except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError) as e:
                        if attempt < 4:
                            wait = [5, 15, 30, 60, 120][attempt]
                            logger.warning("Transient error (%s), retrying in %ds (attempt %d/5)", e, wait, attempt + 1)
                            await asyncio.sleep(wait)
                        else:
                            _backfill_state.error = f"ListenBrainz API unreachable after 5 attempts: {e}"
                            return
                    except httpx.HTTPStatusError as e:
                        _backfill_state.error = f"ListenBrainz API error {e.response.status_code}: {e}"
                        return
                    except Exception as e:
                        logger.exception("Unexpected error fetching LB page during backfill")
                        _backfill_state.error = f"Unexpected error: {e}"
                        return

                if not listens:
                    break

                _backfill_state.batches_fetched += 1
                stop = False

                for listen in listens:
                    ts = listen.get("listened_at")
                    if ts is None:
                        continue
                    if ts < oldest_ts:
                        stop = True
                        break
                    meta = listen.get("track_metadata", {})
                    artist = meta.get("artist_name") or ""
                    title = meta.get("track_name") or ""
                    key = (ts, artist.casefold(), title.casefold())
                    if key not in lookup:
                        continue

                    additional_info = meta.get("additional_info") or {}
                    new_duration = _parse_duration(additional_info)
                    raw_album = meta.get("release_name")
                    new_album: Optional[str] = raw_album.strip() if raw_album and raw_album.strip() else None

                    for entry in lookup[key]:
                        upd: dict[str, Any] = {"id": entry["id"]}
                        if entry["need_duration"] and new_duration is not None:
                            upd["duration_secs"] = new_duration
                        if entry["need_album"] and new_album is not None:
                            upd["album"] = new_album
                        if len(upd) > 1:
                            pending_updates.append(upd)

                    del lookup[key]
                    if len(pending_updates) >= 500:
                        flush()

                if stop or len(listens) < batch_size:
                    break
                current_max_ts = listens[-1].get("listened_at")
                await asyncio.sleep(2)

        flush()
        logger.info(
            "Backfill done: %d row(s) updated, %d batch(es) fetched, %d row(s) unmatched",
            _backfill_state.rows_updated,
            _backfill_state.batches_fetched,
            len(lookup),
        )
    except Exception as e:
        logger.exception("Backfill crashed")
        _backfill_state.error = f"Backfill crashed: {e}"
    finally:
        _backfill_state.running = False
        _backfill_state.finished = True
