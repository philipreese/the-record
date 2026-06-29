from ._base import (
    Any,
    List,
    Optional,
    select,
    func,
    text,
    bindparam,
    get_engine,
    Listen,
    IS_POSTGRES,
    ListenEntry,
)


def deduplicate_listens() -> int:
    """
    Remove duplicate listens where the same artist and title are scrobbled
    within 60 seconds of each other. Keeps the entry with the lower ID.
    Returns the number of deleted duplicate rows.
    """
    with get_engine().begin() as conn:
        stmt = """
            DELETE FROM listens
            WHERE id IN (
                SELECT b.id
                FROM listens a
                JOIN listens b ON LOWER(a.artist) = LOWER(b.artist)
                              AND LOWER(a.title)  = LOWER(b.title)
                              AND a.id < b.id
                              AND abs(a.unix_ts - b.unix_ts) <= 60
            )
        """
        res = conn.execute(text(stmt))
        return res.rowcount


def apply_artist_corrections() -> int:
    """Bulk-update listens whose artist name matches a row in artist_corrections.

    Returns the number of rows updated. Safe to call after every sync — the
    corrections table survives mirror syncs, so cleaned data is always restored.
    """
    with get_engine().begin() as conn:
        if IS_POSTGRES:
            result = conn.execute(text("""
                UPDATE listens
                SET artist = ac.correct_name
                FROM artist_corrections ac
                WHERE LOWER(listens.artist) = LOWER(ac.wrong_name)
            """))
        else:
            result = conn.execute(text("""
                UPDATE listens
                SET artist = (
                    SELECT correct_name FROM artist_corrections
                    WHERE LOWER(wrong_name) = LOWER(listens.artist)
                    LIMIT 1
                )
                WHERE LOWER(artist) IN (SELECT LOWER(wrong_name) FROM artist_corrections)
            """))
        return result.rowcount


def get_listen_by_id(listen_id: int) -> Optional[ListenEntry]:
    """Fetch a single raw listen by primary key (bypasses corrected_listens view).

    Used by LB write-back to read the original values before they're overridden.
    Returns None if not found.
    """
    with get_engine().connect() as conn:
        row = conn.execute(
            select(
                Listen.id, Listen.artist, Listen.title, Listen.unix_ts,
                Listen.source, Listen.duration_secs, Listen.album, Listen.recording_mbid,
            ).where(Listen.id == listen_id)
        ).first()
    if not row:
        return None
    return ListenEntry(
        id=row.id, artist=row.artist, title=row.title, unix_ts=row.unix_ts,
        source=row.source, duration_secs=row.duration_secs, album=row.album,
        recording_mbid=row.recording_mbid,
    )


def get_listen_with_originals(listen_id: int) -> Optional[ListenEntry]:
    """Return the effective (corrected) listen alongside its raw original values.

    Populates has_listen_correction, has_track_correction, track_id, and
    original_* fields so the UI can show what was corrected and offer reverts.
    """
    with get_engine().connect() as conn:
        row = conn.execute(
            text("""
                SELECT
                    cl.id, cl.unix_ts, cl.source,
                    cl.artist, cl.title, cl.album, cl.duration_secs, cl.recording_mbid,
                    cl.has_listen_correction, cl.has_track_correction, cl.track_id,
                    l.artist  AS original_artist,
                    l.title   AS original_title,
                    l.album   AS original_album,
                    l.duration_secs AS original_duration_secs,
                    l.recording_mbid AS original_recording_mbid,
                    (SELECT COUNT(*) FROM corrected_listens cl2
                     WHERE LOWER(cl2.artist) = LOWER(cl.artist)
                       AND LOWER(cl2.title)  = LOWER(cl.title)) AS track_play_count,
                    CASE WHEN cac.manual_override THEN cac.original_url END AS original_cover_art_url
                FROM corrected_listens cl
                JOIN listens l ON l.id = cl.id
                LEFT JOIN cover_art_cache cac
                    ON cac.artist_folded = LOWER(TRIM(cl.artist))
                   AND cac.title_folded  = LOWER(TRIM(cl.title))
                WHERE cl.id = :id
            """),
            {"id": listen_id},
        ).first()
    if not row:
        return None
    any_correction = bool(row.has_listen_correction) or bool(row.has_track_correction)
    return ListenEntry(
        id=row.id, unix_ts=row.unix_ts, source=row.source,
        artist=row.artist, title=row.title, album=row.album,
        duration_secs=row.duration_secs, recording_mbid=row.recording_mbid,
        has_listen_correction=bool(row.has_listen_correction),
        has_track_correction=bool(row.has_track_correction),
        track_id=row.track_id,
        track_play_count=row.track_play_count,
        original_artist=row.original_artist if any_correction else None,
        original_title=row.original_title if any_correction else None,
        original_album=row.original_album if any_correction else None,
        original_duration_secs=row.original_duration_secs if any_correction else None,
        original_recording_mbid=row.original_recording_mbid if any_correction else None,
        original_cover_art_url=row.original_cover_art_url,
    )


def save_listen_correction(listen_id: int, corrections: dict[str, Any]) -> None:
    """Upsert a per-listen correction (wide schema).

    Keys in corrections must be a subset of: artist, title, album, duration_secs,
    recording_mbid. Pass "" (empty string) to explicitly clear a text field — do NOT
    convert "" to None before calling, since COALESCE("", x) returns "" (correct)
    while COALESCE(None, x) falls through (wrong).
    """
    fields = ["artist", "title", "album", "duration_secs", "recording_mbid"]
    params: dict[str, Any] = {"listen_id": listen_id}
    for f in fields:
        params[f] = corrections.get(f)  # None = don't touch this field

    with get_engine().begin() as conn:
        if IS_POSTGRES:
            conn.execute(
                text("""
                    INSERT INTO listen_corrections
                        (listen_id, artist, title, album, duration_secs, recording_mbid)
                    VALUES
                        (:listen_id, :artist, :title, :album, :duration_secs, :recording_mbid)
                    ON CONFLICT (listen_id) DO UPDATE SET
                        artist         = COALESCE(EXCLUDED.artist,         listen_corrections.artist),
                        title          = COALESCE(EXCLUDED.title,          listen_corrections.title),
                        album          = COALESCE(EXCLUDED.album,          listen_corrections.album),
                        duration_secs  = COALESCE(EXCLUDED.duration_secs,  listen_corrections.duration_secs),
                        recording_mbid = COALESCE(EXCLUDED.recording_mbid, listen_corrections.recording_mbid),
                        corrected_at   = now()
                """),
                params,
            )
        else:
            conn.execute(
                text("""
                    INSERT INTO listen_corrections
                        (listen_id, artist, title, album, duration_secs, recording_mbid)
                    VALUES
                        (:listen_id, :artist, :title, :album, :duration_secs, :recording_mbid)
                    ON CONFLICT (listen_id) DO UPDATE SET
                        artist         = COALESCE(EXCLUDED.artist,         listen_corrections.artist),
                        title          = COALESCE(EXCLUDED.title,          listen_corrections.title),
                        album          = COALESCE(EXCLUDED.album,          listen_corrections.album),
                        duration_secs  = COALESCE(EXCLUDED.duration_secs,  listen_corrections.duration_secs),
                        recording_mbid = COALESCE(EXCLUDED.recording_mbid, listen_corrections.recording_mbid),
                        corrected_at   = strftime('%Y-%m-%d %H:%M:%S', 'now')
                """),
                params,
            )


def delete_listen(listen_id: int) -> None:
    """Permanently delete a listen and its correction (if any) from the local DB."""
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM listen_corrections WHERE listen_id = :id"), {"id": listen_id})
        conn.execute(text("DELETE FROM listens WHERE id = :id"), {"id": listen_id})


def get_track_listens(artist: str, title: str) -> List[ListenEntry]:
    """Return all individual listens for a corrected (artist, title) pair, newest first."""
    with get_engine().connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    cl.id, cl.unix_ts, cl.source,
                    cl.artist, cl.title, cl.album, cl.duration_secs, cl.recording_mbid,
                    cl.has_listen_correction, cl.has_track_correction, cl.track_id,
                    l.artist  AS original_artist,
                    l.title   AS original_title,
                    l.album   AS original_album,
                    l.duration_secs AS original_duration_secs,
                    l.recording_mbid AS original_recording_mbid
                FROM corrected_listens cl
                JOIN listens l ON l.id = cl.id
                WHERE LOWER(cl.artist) = LOWER(:artist) AND LOWER(cl.title) = LOWER(:title)
                ORDER BY cl.unix_ts DESC
            """),
            {"artist": artist, "title": title},
        ).fetchall()
    return [
        ListenEntry(
            id=r.id, unix_ts=r.unix_ts, source=r.source,
            artist=r.artist, title=r.title, album=r.album,
            duration_secs=r.duration_secs, recording_mbid=r.recording_mbid,
            has_listen_correction=bool(r.has_listen_correction),
            has_track_correction=bool(r.has_track_correction),
            track_id=r.track_id,
            original_artist=r.original_artist if (r.has_listen_correction or r.has_track_correction) else None,
            original_title=r.original_title if (r.has_listen_correction or r.has_track_correction) else None,
            original_album=r.original_album if (r.has_listen_correction or r.has_track_correction) else None,
            original_duration_secs=r.original_duration_secs if (r.has_listen_correction or r.has_track_correction) else None,
            original_recording_mbid=r.original_recording_mbid if (r.has_listen_correction or r.has_track_correction) else None,
        )
        for r in rows
    ]


def delete_track_listens(artist: str, title: str) -> int:
    """Delete all listens for a corrected (artist, title) pair. Returns count deleted."""
    with get_engine().begin() as conn:
        ids = [
            r[0] for r in conn.execute(
                text("SELECT id FROM corrected_listens WHERE LOWER(artist) = LOWER(:a) AND LOWER(title) = LOWER(:t)"),
                {"a": artist, "t": title},
            ).fetchall()
        ]
        if not ids:
            return 0
        conn.execute(
            text("DELETE FROM listen_corrections WHERE listen_id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            ),
            {"ids": ids},
        )
        conn.execute(
            text("DELETE FROM listens WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            ),
            {"ids": ids},
        )
        # Clean up orphaned track_raw_keys and canonical_tracks
        conn.execute(text("""
            DELETE FROM track_raw_keys
            WHERE NOT EXISTS (
                SELECT 1 FROM listens
                WHERE listens.artist_raw_folded = track_raw_keys.artist_raw_folded
                  AND listens.title_raw_folded  = track_raw_keys.title_raw_folded
            )
        """))
        conn.execute(text("""
            DELETE FROM canonical_tracks
            WHERE NOT EXISTS (
                SELECT 1 FROM track_raw_keys WHERE track_raw_keys.canonical_track_id = canonical_tracks.id
            )
        """))
        return len(ids)


def delete_listen_correction(listen_id: int) -> None:
    """Delete the per-listen correction for a listen (revert to track correction or raw)."""
    with get_engine().begin() as conn:
        conn.execute(
            text("DELETE FROM listen_corrections WHERE listen_id = :id"),
            {"id": listen_id},
        )


def save_track_correction(
    corrected_artist: str,
    corrected_title: str,
    corrections: dict[str, Any],
    track_id: Optional[int] = None,
    recording_mbid: Optional[str] = None,
) -> Optional[int]:
    """Upsert a canonical track correction and map all matching raw keys to it.

    Lookup order: track_id → recording_mbid → artist/title fanout → create new.
    Returns the canonical_track_id.

    When no recording MBID is available, artist+title is treated as the best
    available approximation of logical track identity. Distinct recordings of the
    same title may be merged into one canonical_tracks row in that case.
    """
    ct_fields = {k: v for k, v in corrections.items()
                 if k in ("artist", "title", "album", "duration_secs", "recording_mbid")}
    new_mbid = ct_fields.get("recording_mbid") or recording_mbid

    with get_engine().begin() as conn:
        # --- Find or create the canonical_tracks row ---
        existing_id: Optional[int] = None

        if track_id is not None:
            row = conn.execute(
                text("SELECT id FROM canonical_tracks WHERE id = :id"),
                {"id": track_id},
            ).first()
            if row:
                existing_id = row.id

        if existing_id is None and new_mbid:
            row = conn.execute(
                text("SELECT id FROM canonical_tracks WHERE recording_mbid = :mbid"),
                {"mbid": new_mbid},
            ).first()
            if row:
                existing_id = row.id

        if existing_id is None:
            # Artist/title discovery: find if any existing canonical_track already maps
            # to the raw keys that currently resolve to corrected_artist/corrected_title.
            raw_key_row = conn.execute(
                text("""
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
            if raw_key_row:
                existing_id = raw_key_row.canonical_track_id

        if existing_id is not None:
            # Update existing canonical_tracks row
            set_parts = []
            update_params: dict[str, Any] = {"id": existing_id}
            for col in ("artist", "title", "album", "duration_secs", "recording_mbid"):
                if col in ct_fields:
                    set_parts.append(f"{col} = :{col}")
                    update_params[col] = ct_fields[col]
            if set_parts:
                if IS_POSTGRES:
                    set_parts.append("corrected_at = now()")
                else:
                    set_parts.append("corrected_at = strftime('%Y-%m-%d %H:%M:%S', 'now')")
                conn.execute(
                    text(f"UPDATE canonical_tracks SET {', '.join(set_parts)} WHERE id = :id"),
                    update_params,
                )
            canonical_track_id = existing_id
        else:
            # Create new canonical_tracks row
            ins_params: dict[str, Any] = {
                "artist": ct_fields.get("artist"),
                "title": ct_fields.get("title"),
                "album": ct_fields.get("album"),
                "duration_secs": ct_fields.get("duration_secs"),
                "recording_mbid": new_mbid,
            }
            if IS_POSTGRES:
                row = conn.execute(
                    text("""
                        INSERT INTO canonical_tracks
                            (artist, title, album, duration_secs, recording_mbid)
                        VALUES (:artist, :title, :album, :duration_secs, :recording_mbid)
                        RETURNING id
                    """),
                    ins_params,
                ).first()
                assert row is not None
                canonical_track_id = row.id
            else:
                conn.execute(
                    text("""
                        INSERT INTO canonical_tracks
                            (artist, title, album, duration_secs, recording_mbid)
                        VALUES (:artist, :title, :album, :duration_secs, :recording_mbid)
                    """),
                    ins_params,
                )
                canonical_track_id = conn.execute(
                    text("SELECT last_insert_rowid()")
                ).scalar()

        # --- Fan-out: upsert track_raw_keys for all matching raw identities ---
        raw_keys = conn.execute(
            text("""
                SELECT DISTINCT l.artist_raw_folded, l.title_raw_folded
                FROM corrected_listens cl
                JOIN listens l ON l.id = cl.id
                WHERE cl.artist = :artist AND cl.title = :title
            """),
            {"artist": corrected_artist, "title": corrected_title},
        ).fetchall()

        for rk in raw_keys:
            conn.execute(
                text("""
                    INSERT INTO track_raw_keys (canonical_track_id, artist_raw_folded, title_raw_folded)
                    VALUES (:ct_id, :af, :tf)
                    ON CONFLICT (artist_raw_folded, title_raw_folded)
                    DO UPDATE SET canonical_track_id = EXCLUDED.canonical_track_id
                """),
                {
                    "ct_id": canonical_track_id,
                    "af": rk.artist_raw_folded,
                    "tf": rk.title_raw_folded,
                },
            )

    return canonical_track_id


def delete_track_correction(
    corrected_artist: str,
    corrected_title: str,
    track_id: Optional[int] = None,
) -> None:
    """Delete the canonical track correction and its raw key mappings.

    If track_id is provided, deletes that row directly. Otherwise finds the
    canonical_track_id by querying corrected_listens for raw key matches.
    """
    with get_engine().begin() as conn:
        ct_id = track_id
        if ct_id is None:
            row = conn.execute(
                text("""
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
                ct_id = row.canonical_track_id

        if ct_id is not None:
            conn.execute(
                text("DELETE FROM track_raw_keys WHERE canonical_track_id = :id"),
                {"id": ct_id},
            )
            conn.execute(
                text("DELETE FROM canonical_tracks WHERE id = :id"),
                {"id": ct_id},
            )


def get_corrected_play_count(corrected_artist: str, corrected_title: str) -> int:
    """Count listens that currently resolve to the given corrected artist+title."""
    with get_engine().connect() as conn:
        return conn.execute(
            text("""
                SELECT COUNT(*) FROM corrected_listens
                WHERE artist = :artist AND title = :title
            """),
            {"artist": corrected_artist, "title": corrected_title},
        ).scalar() or 0


def get_representative_listen_id(corrected_artist: str, corrected_title: str) -> Optional[int]:
    """Return the most-recent listen id that currently resolves to the given track."""
    with get_engine().connect() as conn:
        row = conn.execute(
            text("""
                SELECT id FROM corrected_listens
                WHERE artist = :artist AND title = :title
                ORDER BY unix_ts DESC LIMIT 1
            """),
            {"artist": corrected_artist, "title": corrected_title},
        ).first()
    return row.id if row else None


def get_representative_listen_id_by_track_id(canonical_track_id: int) -> Optional[int]:
    """Return the most-recent listen id mapped to a canonical_track by its id.

    Used by revert endpoints to get a representative listen before deleting the
    canonical_tracks row (after which the raw-key join no longer resolves).
    """
    with get_engine().connect() as conn:
        row = conn.execute(
            text("""
                SELECT l.id FROM listens l
                JOIN track_raw_keys trk
                    ON trk.artist_raw_folded = l.artist_raw_folded
                   AND trk.title_raw_folded  = l.title_raw_folded
                WHERE trk.canonical_track_id = :ct_id
                ORDER BY l.unix_ts DESC LIMIT 1
            """),
            {"ct_id": canonical_track_id},
        ).first()
    return row.id if row else None
