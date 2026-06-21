import sys
import os
import json
import logging
import asyncio
import argparse
import difflib
import httpx

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPTS_DIR)
sys.path.append(BACKEND_DIR)

from app.db import get_session, Listen
from app.utils import clean_artist, clean_title
from sqlalchemy import select, update, and_, func

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("backfill")

_UA = "the-record-backfill/1.0 (https://github.com/philipreese/the-record)"

RESULTS_FILE = os.path.join(SCRIPTS_DIR, "backfill_results.json")
FAILURES_FILE = os.path.join(SCRIPTS_DIR, "backfill_failures.json")

HIGH_CONFIDENCE = 0.8

# Lower index = more preferred release type
_RELEASE_TYPE_RANK = ["Album", "Single", "EP", "Broadcast", "Other", "Compilation", ""]

# Secondary types that indicate a non-original release — penalised within the same primary type
_SECONDARY_PENALTY = frozenset({"Live", "Compilation", "Remix", "Demo", "Mixtape/Street"})

CHECKPOINT_INTERVAL = 500


def _lucene_escape(s: str) -> str:
    return s.replace('"', '\\"')


def _similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _rel_rank(rel: dict) -> int:
    """Rank a single release: lower = more preferred.

    Primary type dominates; secondary types (Live, Remix, Demo…) add a
    tie-breaking penalty so an original studio Album always beats a Live Album.
    """
    rg = rel.get("release-group", {})
    primary = rg.get("primary-type", "")
    secondary = set(rg.get("secondary-types", []))
    try:
        base = _RELEASE_TYPE_RANK.index(primary)
    except ValueError:
        base = len(_RELEASE_TYPE_RANK) - 1
    penalty = 1 if secondary & _SECONDARY_PENALTY else 0
    # Multiply base by 2 so primary type always beats a secondary-type penalty
    return base * 2 + penalty


def _release_type_score(rec: dict) -> int:
    """Return the best (lowest) release rank across all releases on a recording."""
    releases = rec.get("releases", [])
    if not releases:
        return (len(_RELEASE_TYPE_RANK) - 1) * 2
    return min(_rel_rank(rel) for rel in releases)


def _score_candidate(rec: dict, query_artist: str, query_title: str) -> float:
    rec_title = rec.get("title", "")
    artist_credits = rec.get("artist-credit", [])
    rec_artist = artist_credits[0].get("name", "") if artist_credits else ""
    title_sim = _similarity(rec_title, query_title)
    artist_sim = _similarity(rec_artist, query_artist)
    has_duration = 1.0 if rec.get("length") else 0.0
    type_penalty = _release_type_score(rec) / ((len(_RELEASE_TYPE_RANK) - 1) * 2)
    return title_sim * 0.4 + artist_sim * 0.4 + has_duration * 0.1 + (1.0 - type_penalty) * 0.1


def _pick_best(recordings: list[dict], query_artist: str, query_title: str) -> tuple[dict | None, float]:
    if not recordings:
        return None, 0.0
    scored = [(rec, _score_candidate(rec, query_artist, query_title)) for rec in recordings]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0]


def _extract_metadata(rec: dict) -> tuple[int | None, str | None]:
    duration_ms = rec.get("length")
    duration_secs = int(duration_ms / 1000) if duration_ms else None
    releases = rec.get("releases", [])
    if not releases:
        return duration_secs, None
    best_release = min(releases, key=_rel_rank)
    return duration_secs, best_release.get("title")


async def _query_mb(client: httpx.AsyncClient, query_artist: str, query_title: str) -> list[dict]:
    url = "https://musicbrainz.org/ws/2/recording"
    params = {
        "query": f'recording:"{_lucene_escape(query_title)}" AND artist:"{_lucene_escape(query_artist)}"',
        "fmt": "json",
        "limit": "5",
        "inc": "releases release-groups artist-credits",
    }
    retries = 3
    delay = 2.0
    for attempt in range(retries):
        try:
            r = await client.get(url, params=params, headers={"User-Agent": _UA}, timeout=15.0)
            if r.status_code == 200:
                return r.json().get("recordings", [])
            if r.status_code in (429, 503):
                logger.warning("MB returned %d. Retrying in %.1fs... (%d/%d)", r.status_code, delay, attempt + 1, retries)
                await asyncio.sleep(delay)
                delay *= 2.0
            else:
                logger.warning("MB returned status %d for %r / %r", r.status_code, query_artist, query_title)
                break
        except Exception as e:
            logger.error("Error querying MB for %r / %r: %s", query_artist, query_title, e)
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2.0
            else:
                break
    return []


def _write_checkpoint(results: list[dict], failures: list[dict]) -> None:
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    if failures:
        with open(FAILURES_FILE, "w", encoding="utf-8") as f:
            json.dump(failures, f, indent=2, ensure_ascii=False)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill duration/album metadata from MusicBrainz.",
    )
    parser.add_argument(
        "--reverify",
        action="store_true",
        help=(
            "Re-query ALL tracks (not just those missing data) to verify and correct "
            "existing metadata. High-confidence results (>= 0.8) are auto-applied; "
            "lower-confidence results are flagged in backfill_results.json for review."
        ),
    )
    parser.add_argument(
        "--confirm-updates",
        action="store_true",
        help=(
            "Actually apply metadata updates (overwriting existing non-null albums/durations) "
            "rather than just flagging them for review in backfill_results.json."
        ),
    )
    return parser.parse_args()


async def main(reverify: bool = False, confirm_updates: bool = False) -> None:
    session = get_session()
    results: list[dict] = []
    failures: list[dict] = []
    done: set[tuple[str, str]] = set()

    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, encoding="utf-8") as f:
                results = json.load(f)
            done = {(r["artist"], r["title"]) for r in results}
            logger.info("Resume: loaded %d existing result(s)", len(results))
        except (json.JSONDecodeError, KeyError):
            logger.warning("Could not load existing results — starting fresh")

    if os.path.exists(FAILURES_FILE):
        try:
            with open(FAILURES_FILE, encoding="utf-8") as f:
                failures = json.load(f)
        except (json.JSONDecodeError, KeyError):
            pass

    try:
        mode = "reverify (all tracks)" if reverify else "fill missing only"
        logger.info("Mode: %s", mode)

        stmt = (
            select(
                Listen.artist,
                Listen.title,
                func.max(Listen.duration_secs).label("cur_duration"),
                func.max(Listen.album).label("cur_album"),
            )
            .group_by(Listen.artist, Listen.title)
        )
        if not reverify:
            stmt = stmt.where((Listen.duration_secs.is_(None)) | (Listen.album.is_(None)))

        tracks = session.execute(stmt).all()
        logger.info("Found %d unique track(s) to process", len(tracks))

        if not tracks:
            logger.info("Nothing to do.")
            return

        processed_this_run = 0
        async with httpx.AsyncClient() as client:
            for i, track in enumerate(tracks):
                raw_artist = str(track.artist)
                raw_title = str(track.title)

                if (raw_artist, raw_title) in done:
                    logger.info("[%d/%d] SKIP (already processed): %r - %r", i + 1, len(tracks), raw_artist, raw_title)
                    continue

                cur_duration: int | None = track.cur_duration
                cur_album: str | None = track.cur_album
                c_artist = clean_artist(raw_artist)
                c_title = clean_title(raw_title)
                logger.info("[%d/%d] %r - %r", i + 1, len(tracks), raw_artist, raw_title)

                # Raw query
                raw_recs = await _query_mb(client, raw_artist, raw_title)
                await asyncio.sleep(1.2)
                raw_best, raw_score = _pick_best(raw_recs, raw_artist, raw_title)

                # Clean query — skip duplicate call if nothing changed
                if c_artist == raw_artist and c_title == raw_title:
                    clean_best, clean_score = raw_best, raw_score
                else:
                    clean_recs = await _query_mb(client, c_artist, c_title)
                    await asyncio.sleep(1.2)
                    clean_best, clean_score = _pick_best(clean_recs, c_artist, c_title)

                # Pick winner
                needs_review = False
                chosen: dict | None = None
                chosen_by: str | None = None
                chosen_score = 0.0

                if raw_best is None and clean_best is None:
                    failures.append({"artist": raw_artist, "title": raw_title})
                    logger.info("--> No results from either query")
                    results.append({
                        "artist": raw_artist, "title": raw_title,
                        "cleaned_artist": c_artist, "cleaned_title": c_title,
                        "raw_score": 0.0, "clean_score": 0.0,
                        "chosen_by": None, "chosen_score": 0.0, "action": "failed",
                        "existing_album": cur_album, "existing_duration_secs": cur_duration,
                        "chosen_recording": None, "chosen_album": None, "chosen_duration_secs": None,
                        "needs_review": False,
                    })
                    processed_this_run += 1
                    if processed_this_run % CHECKPOINT_INTERVAL == 0:
                        _write_checkpoint(results, failures)
                        logger.info("Checkpoint: %d results written", len(results))
                    continue
                elif clean_best is None or raw_score > clean_score + 0.1:
                    chosen, chosen_by, chosen_score = raw_best, "raw", raw_score
                    needs_review = True  # raw winning over clean is unexpected
                    logger.info("--> Raw wins (%.2f vs clean %.2f) [review]", raw_score, clean_score)
                else:
                    chosen, chosen_by, chosen_score = clean_best, "clean", clean_score
                    logger.info("--> Clean wins (%.2f)", clean_score)

                # Flag when raw/clean return different recordings with similar scores
                if (raw_best and clean_best
                        and raw_best.get("id") != clean_best.get("id")
                        and abs(raw_score - clean_score) < 0.05):
                    needs_review = True
                    logger.info("--> Different recordings, similar scores [review]")

                new_duration, new_album = _extract_metadata(chosen)  # type: ignore[arg-type]
                values: dict = {}
                action: str

                if chosen_score >= HIGH_CONFIDENCE:
                    album_same = cur_album == new_album
                    dur_close = (
                        cur_duration is not None
                        and new_duration is not None
                        and abs(cur_duration - new_duration) <= 5
                    )
                    if cur_album is None and cur_duration is None:
                        action = "filled"
                    elif album_same and dur_close:
                        action = "verified"
                    elif album_same and cur_duration is None:
                        # Album already correct but duration was never filled — write it
                        action = "filled"
                    else:
                        action = "updated"
                        # Flag album changes so they're easy to audit
                        if cur_album is not None and cur_album != new_album:
                            needs_review = True
                            logger.info("--> Album changed: %r -> %r [review]", cur_album, new_album)

                    if action != "verified":
                        if action == "updated" and not confirm_updates:
                            # Skip committing this update to the DB unless confirmed by user
                            needs_review = True
                            action = "skipped_update"
                            logger.info("--> Album/duration update skipped (requires --confirm-updates) [review]")
                        else:
                            if new_duration is not None:
                                values["duration_secs"] = new_duration
                            if new_album is not None:
                                values["album"] = new_album
                else:
                    action = "skipped"
                    needs_review = True
                    logger.info("--> Low confidence (%.2f), skipping update [review]", chosen_score)

                if values:
                    session.execute(
                        update(Listen)
                        .where(and_(Listen.artist == raw_artist, Listen.title == raw_title))
                        .values(**values)
                    )
                    session.commit()
                    logger.info("--> %s: duration=%s, album=%r", action.upper(), new_duration, new_album)
                elif action == "verified":
                    logger.info("--> VERIFIED (no change needed)")

                results.append({
                    "artist": raw_artist,
                    "title": raw_title,
                    "cleaned_artist": c_artist,
                    "cleaned_title": c_title,
                    "raw_score": round(raw_score, 4),
                    "clean_score": round(clean_score, 4),
                    "chosen_by": chosen_by,
                    "chosen_score": round(chosen_score, 4),
                    "action": action,
                    "existing_album": cur_album,
                    "existing_duration_secs": cur_duration,
                    "chosen_recording": chosen.get("title") if chosen else None,  # type: ignore[union-attr]
                    "chosen_album": new_album,
                    "chosen_duration_secs": new_duration,
                    "needs_review": needs_review,
                })
                processed_this_run += 1
                if processed_this_run % CHECKPOINT_INTERVAL == 0:
                    _write_checkpoint(results, failures)
                    logger.info("Checkpoint: %d results written", len(results))

    finally:
        session.close()

    _write_checkpoint(results, failures)

    action_counts: dict[str, int] = {}
    for r in results:
        a = str(r["action"])
        action_counts[a] = action_counts.get(a, 0) + 1
    review_count = sum(1 for r in results if r["needs_review"])
    logger.info("Summary: %s | needs_review: %d", action_counts, review_count)
    logger.info("Wrote %d result(s) to %s", len(results), RESULTS_FILE)
    if failures:
        logger.info("Wrote %d failure(s) to %s", len(failures), FAILURES_FILE)
    else:
        logger.info("No failures.")


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(main(reverify=args.reverify, confirm_updates=args.confirm_updates))
