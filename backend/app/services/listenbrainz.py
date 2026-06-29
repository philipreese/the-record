import asyncio
import logging
from typing import Any

import httpx

from app.lb_client import get_lb_client
from app.schemas import ListenEntry
from app.services.cover_art import UA

logger = logging.getLogger(__name__)


async def lb_write_back(original: ListenEntry, updates: dict[str, Any]) -> None:
    """Async write-back to ListenBrainz. Best-effort, fire-and-forget."""
    from app.sync import LISTENBRAINZ_USERNAME, LISTENBRAINZ_TOKEN

    if not LISTENBRAINZ_USERNAME or not LISTENBRAINZ_TOKEN:
        return

    lb_headers = {
        "Authorization": f"Token {LISTENBRAINZ_TOKEN}",
        "User-Agent": UA,
    }

    if "recording_mbid" in updates:
        await _lb_submit_manual_mapping(original.unix_ts, updates["recording_mbid"], lb_headers)
    elif "artist" in updates or "title" in updates:
        await _lb_delete_and_resubmit(original, updates, lb_headers)


async def _lb_submit_manual_mapping(
    listened_at: int, recording_mbid: str, headers: dict
) -> bool:
    """Submit a manual MBID mapping to ListenBrainz for a specific listen timestamp."""
    try:
        client = get_lb_client()
        res = await client.post(
            "https://api.listenbrainz.org/1/metadata/submit_manual_mapping",
            headers=headers,
            json={"listened_at": listened_at, "recording_mbid": recording_mbid},
            timeout=httpx.Timeout(10.0),
        )
        if res.status_code not in (200, 201):
            logger.warning(
                "LB submit_manual_mapping returned %d for ts=%d mbid=%s",
                res.status_code, listened_at, recording_mbid,
            )
            return False
        return True
    except Exception as exc:
        logger.warning("LB submit_manual_mapping failed for ts=%d: %s", listened_at, exc)
        return False


async def _lb_delete_and_resubmit(
    original: ListenEntry, updates: dict[str, Any], headers: dict
) -> bool:
    """Delete a listen from LB and resubmit with corrected metadata.

    Aborts entirely if the listen can't be found on LB to avoid creating duplicates.
    """
    from app.sync import LISTENBRAINZ_USERNAME

    try:
        client = get_lb_client()

        # Step 1: find the recording_msid on LB by timestamp
        ts = original.unix_ts
        res = await client.get(
            f"https://api.listenbrainz.org/1/user/{LISTENBRAINZ_USERNAME}/listens",
            headers=headers,
            params={"max_ts": ts + 1, "min_ts": ts - 1, "count": 5},
            timeout=httpx.Timeout(10.0),
        )
        if res.status_code != 200:
            logger.warning("LB listens lookup returned %d for ts=%d", res.status_code, ts)
            return False

        lb_listens = res.json().get("payload", {}).get("listens", [])
        recording_msid = None
        for lb_listen in lb_listens:
            if lb_listen.get("listened_at") == ts:
                recording_msid = (
                    lb_listen.get("track_metadata", {})
                    .get("additional_info", {})
                    .get("recording_msid")
                )
                break

        if not recording_msid:
            logger.warning(
                "LB delete-and-resubmit aborted: listen ts=%d not found on LB (would create duplicate)",
                ts,
            )
            return False

        # Step 2: delete from LB
        del_res = await client.post(
            "https://api.listenbrainz.org/1/delete-listen",
            headers=headers,
            json={"listened_at": ts, "recording_msid": recording_msid},
            timeout=httpx.Timeout(10.0),
        )
        if del_res.status_code != 200:
            logger.warning("LB delete-listen returned %d for ts=%d", del_res.status_code, ts)
            return False

        # Step 3: resubmit with corrected metadata
        corrected_artist = updates.get("artist", original.artist)
        corrected_title = updates.get("title", original.title)
        corrected_album = updates.get("album", original.album)
        submit_payload = {
            "listen_type": "single",
            "payload": [{
                "listened_at": ts,
                "track_metadata": {
                    "artist_name": corrected_artist,
                    "track_name": corrected_title,
                    "release_name": corrected_album or "",
                    "additional_info": {
                        "submission_client": "the-record",
                    },
                },
            }],
        }
        sub_res = await client.post(
            "https://api.listenbrainz.org/1/submit-listens",
            headers=headers,
            json=submit_payload,
            timeout=httpx.Timeout(10.0),
        )
        if sub_res.status_code != 200:
            logger.warning("LB submit-listens returned %d for ts=%d", sub_res.status_code, ts)
            return False

        return True
    except Exception as exc:
        logger.warning("LB delete-and-resubmit failed for ts=%d: %s", original.unix_ts, exc)
        return False
