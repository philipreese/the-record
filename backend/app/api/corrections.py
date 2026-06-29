import asyncio
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Path
from starlette.concurrency import run_in_threadpool

import app.repository as repo
from app.schemas import ListenCorrectionRequest, ListenEntry, TrackCorrectionRequest, TrackRevertRequest
from app.services.cover_art import (
    art_key,
    cover_art_cache,
    manual_override_art_keys,
    populate_cover_art,
)
from app.services.listenbrainz import lb_write_back

router = APIRouter()


@router.get("/listens/{listen_id}", response_model=ListenEntry)
async def get_listen(
    listen_id: int = Path(..., ge=1),
) -> ListenEntry:
    entry = await run_in_threadpool(repo.get_listen_with_originals, listen_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Listen not found")
    populate_cover_art([entry])
    return entry


@router.delete("/listens/{listen_id}", status_code=204)
async def delete_listen(
    listen_id: int = Path(..., ge=1),
) -> None:
    raw = await run_in_threadpool(repo.get_listen_by_id, listen_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Listen not found")
    await run_in_threadpool(repo.delete_listen, listen_id)


@router.post("/listens/{listen_id}/correction", response_model=ListenEntry)
async def correct_listen(
    listen_id: int = Path(..., ge=1),
    correction: ListenCorrectionRequest = Body(...),
) -> ListenEntry:
    listen = await run_in_threadpool(repo.get_listen_by_id, listen_id)
    if not listen:
        raise HTTPException(status_code=404, detail="Listen not found")

    # Only include fields that actually changed from the raw listens values.
    # Pass "" as-is (do NOT convert to None) — COALESCE("", x) returns "" which
    # is the correct way to explicitly clear a field via the corrected_listens view.
    db_updates: dict[str, Any] = {}
    if correction.artist is not None and correction.artist != listen.artist:
        db_updates["artist"] = correction.artist
    if correction.title is not None and correction.title != listen.title:
        db_updates["title"] = correction.title
    if correction.album is not None and correction.album != (listen.album or ""):
        db_updates["album"] = correction.album
    if correction.duration_secs is not None and correction.duration_secs != listen.duration_secs:
        db_updates["duration_secs"] = correction.duration_secs
    if correction.recording_mbid is not None and correction.recording_mbid != (listen.recording_mbid or ""):
        db_updates["recording_mbid"] = correction.recording_mbid

    # Cover art is separate — stored in cover_art_cache, not in listen_corrections
    new_artist = db_updates.get("artist", listen.artist)
    new_title = db_updates.get("title", listen.title)
    new_art_key = art_key(new_artist, new_title)
    raw_art = correction.cover_art_url  # None = no change; "" = clear
    art_changed = raw_art is not None and raw_art != cover_art_cache.get(new_art_key)

    if not db_updates and not art_changed:
        result = await run_in_threadpool(repo.get_listen_with_originals, listen_id)
        if result:
            populate_cover_art([result])
        return result or listen

    if db_updates:
        await run_in_threadpool(repo.save_listen_correction, listen_id, db_updates)

    if art_changed:
        effective_art: Optional[str] = raw_art or None
        cover_art_cache[new_art_key] = effective_art
        if effective_art:
            manual_override_art_keys.add(new_art_key)
        af = new_artist.casefold().strip()
        tf = new_title.casefold().strip()
        await run_in_threadpool(repo.upsert_cover_art, af, tf, effective_art, True)

    # LB write-back: fire-and-forget
    if db_updates:
        asyncio.get_running_loop().create_task(lb_write_back(listen, db_updates))

    updated = await run_in_threadpool(repo.get_listen_with_originals, listen_id)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to fetch updated listen")
    populate_cover_art([updated])
    return updated


@router.post("/listens/{listen_id}/correction/revert", response_model=ListenEntry)
async def revert_listen_correction(
    listen_id: int = Path(..., ge=1),
) -> ListenEntry:
    current = await run_in_threadpool(repo.get_listen_with_originals, listen_id)
    if not current:
        raise HTTPException(status_code=404, detail="Listen not found")

    await run_in_threadpool(repo.delete_listen_correction, listen_id)

    # LB write-back: if artist or title was corrected, resubmit with raw (original) values.
    if current.has_listen_correction:
        raw = await run_in_threadpool(repo.get_listen_by_id, listen_id)
        if raw:
            revert_updates: dict[str, Any] = {}
            if current.artist != raw.artist:
                revert_updates["artist"] = raw.artist
            if current.title != raw.title:
                revert_updates["title"] = raw.title
            if revert_updates:
                asyncio.get_running_loop().create_task(lb_write_back(current, revert_updates))

    result = await run_in_threadpool(repo.get_listen_with_originals, listen_id)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to fetch reverted listen")
    populate_cover_art([result])
    return result


@router.post("/tracks/correction", response_model=ListenEntry)
async def correct_track(
    body: TrackCorrectionRequest = Body(...),
) -> ListenEntry:
    corrected_artist = body.corrected_artist or ""
    corrected_title = body.corrected_title or ""

    corrections = dict(body.corrections)
    raw_art_val = corrections.pop("cover_art_url", None)
    raw_art: Optional[str] = str(raw_art_val) if isinstance(raw_art_val, str) else None
    new_artist = str(corrections.get("artist") or corrected_artist)
    new_title = str(corrections.get("title") or corrected_title)
    mbid_val = corrections.get("recording_mbid")
    correction_mbid: Optional[str] = str(mbid_val) if isinstance(mbid_val, str) else None

    # Capture representative listen id BEFORE saving (fanout changes the view)
    rep_id = await run_in_threadpool(
        repo.get_representative_listen_id, corrected_artist, corrected_title
    ) if corrected_artist and corrected_title else None

    await run_in_threadpool(
        repo.save_track_correction,
        corrected_artist, corrected_title, corrections,
        body.track_id, correction_mbid,
    )

    if raw_art is not None:
        new_art_key = art_key(new_artist, new_title)
        effective_art: Optional[str] = raw_art or None
        cover_art_cache[new_art_key] = effective_art
        if effective_art:
            manual_override_art_keys.add(new_art_key)
        af = new_artist.casefold().strip()
        tf = new_title.casefold().strip()
        await run_in_threadpool(repo.upsert_cover_art, af, tf, effective_art, True)

    if not rep_id:
        raise HTTPException(status_code=404, detail="No listens found for this track")
    result = await run_in_threadpool(repo.get_listen_with_originals, rep_id)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to fetch updated listen")
    populate_cover_art([result])
    return result


@router.post("/tracks/correction/revert", response_model=ListenEntry)
async def revert_track_correction(
    body: TrackRevertRequest = Body(...),
) -> ListenEntry:
    track_id = body.track_id
    corrected_artist = body.corrected_artist or ""
    corrected_title = body.corrected_title or ""

    # Resolve track_id if not provided
    if not track_id and corrected_artist and corrected_title:
        from app.db import get_engine as _get_engine
        from sqlalchemy import text as _text
        with _get_engine().connect() as conn:
            row = conn.execute(
                _text("""
                    SELECT trk.canonical_track_id
                    FROM corrected_listens cl
                    JOIN listens l ON l.id = cl.id
                    JOIN track_raw_keys trk
                        ON trk.artist_raw_folded = l.artist_raw_folded
                       AND trk.title_raw_folded  = l.title_raw_folded
                    WHERE cl.artist = :artist AND cl.title = :title
                    LIMIT 1
                """),
                {"artist": corrected_artist, "title": corrected_title},
            ).first()
        if row:
            track_id = row.canonical_track_id

    if not track_id:
        raise HTTPException(status_code=404, detail="No track correction found")

    # Get a representative listen BEFORE deletion (the join won't work after)
    rep_id = await run_in_threadpool(repo.get_representative_listen_id_by_track_id, track_id)

    await run_in_threadpool(
        repo.delete_track_correction, corrected_artist, corrected_title, track_id
    )

    if not rep_id:
        raise HTTPException(status_code=404, detail="No listens found for this track")
    result = await run_in_threadpool(repo.get_listen_with_originals, rep_id)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to fetch reverted listen")
    populate_cover_art([result])
    return result


@router.get("/tracks/listens", response_model=list[ListenEntry])
async def get_track_listens(artist: str, title: str) -> list[ListenEntry]:
    listens = await run_in_threadpool(repo.get_track_listens, artist, title)
    populate_cover_art(listens)
    return listens


@router.delete("/tracks/listens", status_code=204)
async def delete_track_listens(artist: str, title: str) -> None:
    n = await run_in_threadpool(repo.delete_track_listens, artist, title)
    if n == 0:
        raise HTTPException(status_code=404, detail="No listens found for this track")
