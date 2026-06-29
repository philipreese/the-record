import asyncio
import logging
from typing import Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

import app.repository as repo
from app.schemas import CoverArtResult, CoverArtSearchResponse, MBRecordingResult, MBSearchResponse
from app.services.cover_art import (
    UA,
    art_key,
    bg_resolve_art,
    cover_art_cache,
    is_art_in_flight,
    manual_override_art_keys,
    schedule_art,
    set_art_in_flight,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_mb_semaphore = asyncio.Semaphore(1)


class _CoverArtItem(BaseModel):
    id: int
    artist: str
    title: str
    recording_mbid: Optional[str] = None


@router.post("/cover-art", response_model=Dict[str, Optional[str]])
async def get_cover_art(items: List[_CoverArtItem]) -> Dict[str, Optional[str]]:
    """Return cached cover art URLs and schedule background resolution for misses."""
    result: Dict[str, Optional[str]] = {}
    mem_misses: list[_CoverArtItem] = []
    for item in items[:100]:
        key = art_key(item.artist, item.title)
        if key in cover_art_cache:
            result[str(item.id)] = cover_art_cache[key]
        else:
            mem_misses.append(item)

    if mem_misses:
        db_hits = await run_in_threadpool(
            repo.get_cover_art_batch, [art_key(i.artist, i.title) for i in mem_misses]
        )
        for item in mem_misses:
            key = art_key(item.artist, item.title)
            if key in db_hits:
                url, is_override = db_hits[key]
                cover_art_cache[key] = url
                if is_override:
                    manual_override_art_keys.add(key)
                result[str(item.id)] = url
            else:
                result[str(item.id)] = None
                if not is_art_in_flight(key) and key not in manual_override_art_keys:
                    set_art_in_flight(key, True)
                    schedule_art(bg_resolve_art(item.artist, item.title, None, item.recording_mbid, None))

    return result


@router.get("/mb/search", response_model=MBSearchResponse)
async def search_musicbrainz(
    artist: str = Query(...),
    title: str = Query(...),
) -> MBSearchResponse:
    """Proxy MusicBrainz recording search, rate-limited to one request at a time."""
    query = f'artist:"{artist.strip()}" AND recording:"{title.strip()}"'
    try:
        async with asyncio.wait_for(
            _mb_semaphore.acquire(), timeout=10.0
        ) if False else _mb_semaphore:
            async with httpx.AsyncClient(headers={"User-Agent": UA}) as client:
                res = await client.get(
                    "https://musicbrainz.org/ws/2/recording",
                    params={"query": query, "fmt": "json", "limit": "10"},
                    timeout=httpx.Timeout(10.0),
                )
        if res.status_code != 200:
            raise HTTPException(status_code=502, detail=f"MusicBrainz returned {res.status_code}")
        data = res.json()
        results: list[MBRecordingResult] = []
        for rec in data.get("recordings", []):
            artist_credit = " & ".join(
                ac.get("artist", {}).get("name", "") or ac.get("name", "")
                for ac in rec.get("artist-credit", [])
                if isinstance(ac, dict)
            )
            release = None
            release_date = None
            release_mbid = None
            releases = rec.get("releases", [])
            if releases:
                release = releases[0].get("title")
                release_date = releases[0].get("date")
                release_mbid = releases[0].get("id")
            results.append(MBRecordingResult(
                mbid=rec.get("id", ""),
                title=rec.get("title", ""),
                artist_credit=artist_credit,
                release=release,
                release_date=release_date,
                length_ms=rec.get("length"),
                release_mbid=release_mbid,
            ))
        return MBSearchResponse(results=results)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="MusicBrainz search timed out")
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("MusicBrainz search failed: %s", exc)
        raise HTTPException(status_code=502, detail="MusicBrainz search failed")


@router.get("/cover-art/search", response_model=CoverArtSearchResponse)
async def search_cover_art(
    artist: str = Query(...),
    album: str = Query(""),
    recording_mbid: str = Query(""),
) -> CoverArtSearchResponse:
    """Return MB releases with CAA cover art URLs for a given artist+album or recording MBID."""
    try:
        async with _mb_semaphore:
            async with httpx.AsyncClient(headers={"User-Agent": UA}) as client:
                if recording_mbid.strip():
                    res = await client.get(
                        f"https://musicbrainz.org/ws/2/recording/{recording_mbid.strip()}",
                        params={"inc": "releases", "fmt": "json"},
                        timeout=httpx.Timeout(10.0),
                    )
                    if res.status_code != 200:
                        raise HTTPException(status_code=502, detail=f"MusicBrainz returned {res.status_code}")
                    releases = res.json().get("releases", [])
                else:
                    query_parts = [f'artist:"{artist.strip()}"']
                    if album.strip():
                        query_parts.append(f'release:"{album.strip()}"')
                    res = await client.get(
                        "https://musicbrainz.org/ws/2/release",
                        params={"query": " AND ".join(query_parts), "fmt": "json", "limit": "12", "inc": "artist-credits"},
                        timeout=httpx.Timeout(10.0),
                    )
                    if res.status_code != 200:
                        raise HTTPException(status_code=502, detail=f"MusicBrainz returned {res.status_code}")
                    releases = res.json().get("releases", [])

        results: list[CoverArtResult] = []
        seen: set[str] = set()
        for r in releases:
            mbid = r.get("id", "")
            if not mbid or mbid in seen:
                continue
            seen.add(mbid)
            ac_list = r.get("artist-credit", [])
            artist_credit = " & ".join(
                ac.get("artist", {}).get("name", "") or ac.get("name", "")
                for ac in ac_list
                if isinstance(ac, dict)
            )
            results.append(CoverArtResult(
                release_mbid=mbid,
                release_title=r.get("title", ""),
                artist_credit=artist_credit,
                date=r.get("date") or None,
            ))
            if len(results) >= 12:
                break

        return CoverArtSearchResponse(results=results)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Cover art search failed: %s", exc)
        raise HTTPException(status_code=502, detail="Cover art search failed")
