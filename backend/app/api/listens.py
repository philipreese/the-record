import csv
import io
import json
from typing import List, Literal, Optional

from fastapi import APIRouter, Path, Query
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

import app.repository as repo
from app.schemas import (
    ListenEntry,
    OnThisDayResponse,
    TrackBatchRequestItem,
    TrackBatchResponseItem,
    TrackStatsResponse,
)
from app.services.cover_art import populate_cover_art

router = APIRouter()

# Upper bound on the batch endpoint: each pair expands into an OR/AND clause in the
# query, so an unbounded list would build a pathological statement. The UI only ever
# requests stats for the listens currently on screen, well under this cap.
_MAX_BATCH_TRACKS = 500


@router.get("/recent", response_model=List[ListenEntry])
async def read_recent(
    limit: int = Query(50, ge=1, le=100),
    before_ts: Optional[int] = Query(None),
    before_id: Optional[int] = Query(None),
    anchor_date: Optional[str] = Query(None),
) -> list[ListenEntry]:
    listens = await run_in_threadpool(
        repo.get_recent_listens, limit=limit, before_ts=before_ts,
        before_id=before_id, anchor_date=anchor_date,
    )
    populate_cover_art(listens)
    return listens


@router.get("/track-stats", response_model=TrackStatsResponse)
def read_track_stats(
    artist: str = Query(...),
    title: str = Query(...),
    album: Optional[str] = Query(None),
) -> TrackStatsResponse:
    album_val = album.strip() if album and album.strip() else None
    play_count, duration = repo.get_track_stats(artist=artist, title=title, album=album_val)
    return TrackStatsResponse(play_count=play_count, duration_secs=duration)


@router.post("/track-stats/batch", response_model=List[TrackBatchResponseItem])
def read_track_stats_batch(tracks: List[TrackBatchRequestItem]) -> list[TrackBatchResponseItem]:
    from fastapi import HTTPException
    if len(tracks) > _MAX_BATCH_TRACKS:
        raise HTTPException(
            status_code=422,
            detail=f"Too many tracks in one batch (max {_MAX_BATCH_TRACKS}).",
        )
    track_dicts = [{"artist": t.artist, "title": t.title} for t in tracks]
    return repo.get_track_stats_batch(track_dicts)


@router.get("/on-this-day", response_model=OnThisDayResponse)
async def read_on_this_day() -> OnThisDayResponse:
    from datetime import datetime
    today = datetime.now()
    response = await run_in_threadpool(repo.get_on_this_day, today.month, today.day)
    for group in response.groups:
        populate_cover_art(group.listens)
    return response


@router.get("/export")
def export_listens(
    format: Literal["csv", "json"] = Query("csv"),
    range: str = Query("all"),
) -> StreamingResponse:
    rows = repo.get_export_data(range_days=range)

    if format == "json":
        content = json.dumps(rows, ensure_ascii=False, indent=2)
        filename = f"listening-history-{range}.json"
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    filename = f"listening-history-{range}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/day/{date_str}", response_model=List[ListenEntry])
def read_day_listens(
    date_str: str = Path(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> list[ListenEntry]:
    return repo.get_listens_by_day(date_str)
