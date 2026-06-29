# Data Models — The Record

> Part of the [modular specification](README.md).

## Listen (database entity)

The only persisted entity. All analytics are derived from this table.

```typescript
interface Listen {
  id: number;           // auto-increment primary key
  artist: string;       // indexed
  title: string;
  unix_ts: number;      // Unix timestamp, indexed
  source: string;       // "listenbrainz" | "listenbrainz_sync" | "youtube" | "google_takeout" | "unknown"
  duration_secs?: number | null;  // populated from LB track_metadata.additional_info.duration_ms; null for pre-LB imports
  album?: string | null;          // populated from LB track_metadata.release_name; null for pre-LB imports (e.g. YT Music)
  recording_mbid?: string | null; // MusicBrainz Recording ID from LB additional_info.recording_mbid; canonical track identity across artist-credit variants. Null until a Full Reconstruction backfills it
}
```

**Source of truth:** [backend/app/db.py](../backend/app/db.py)

## Correction system (database entities)

Three-layer override model. Priority order (highest first): per-listen correction → per-track correction → raw listen.

### listen_corrections

Per-listen overrides. A row here beats every other source for that single listen.

```typescript
interface ListenCorrection {
  listen_id: number;          // FK → listens.id (primary key)
  artist?: string | null;     // overrides listens.artist when set
  title?: string | null;
  album?: string | null;
  duration_secs?: number | null;
  recording_mbid?: string | null;
  corrected_at: Date;
}
```

An empty string (`""`) explicitly clears a field (sets it to blank). `null` means "no override — fall through to the next layer".

### canonical_tracks + track_raw_keys

Per-track corrections. A single canonical definition maps to any number of raw (artist, title) variants.

```typescript
interface CanonicalTrack {
  id: number;
  artist: string;
  title: string;
  album?: string | null;
  duration_secs?: number | null;
  recording_mbid?: string | null;
  corrected_at: Date;
}

interface TrackRawKey {
  artist_raw_folded: string;  // LOWER(TRIM(raw artist)) — composite PK
  title_raw_folded: string;   // LOWER(TRIM(raw title))  — composite PK
  canonical_track_id: number; // FK → canonical_tracks.id
}
```

### corrected_listens (view)

The central read model. All analytics and API responses use this view rather than the raw `listens` table.

```sql
SELECT
  l.id, l.unix_ts, l.source,
  COALESCE(lc.artist,  ct.artist,  l.artist)        AS artist,
  COALESCE(lc.title,   ct.title,   l.title)         AS title,
  COALESCE(lc.album,   ct.album,   l.album)         AS album,
  COALESCE(lc.duration_secs, ct.duration_secs, l.duration_secs) AS duration_secs,
  COALESCE(lc.recording_mbid, ct.recording_mbid, l.recording_mbid) AS recording_mbid,
  (lc.listen_id IS NOT NULL) AS has_listen_correction,
  (trk.canonical_track_id IS NOT NULL) AS has_track_correction,
  trk.canonical_track_id AS track_id
FROM listens l
LEFT JOIN listen_corrections lc ON lc.listen_id = l.id
LEFT JOIN track_raw_keys trk
    ON trk.artist_raw_folded = l.artist_raw_folded
   AND trk.title_raw_folded  = l.title_raw_folded
LEFT JOIN canonical_tracks ct ON ct.id = trk.canonical_track_id
```

**Source of truth:** `backend/migrations/versions/017_*` and `018_*`

## Cover art cache (database entity)

Persistent URL cache keyed on the corrected (artist, title) pair. Populated during the 17-hour pre-fetch and on-demand via the cover-art route.

```typescript
interface CoverArtCache {
  artist_folded: string;      // LOWER(TRIM(corrected_artist)) — composite PK
  title_folded: string;       // LOWER(TRIM(corrected_title))  — composite PK
  url: string | null;         // current resolved cover art URL
  manual_override: boolean;   // sticky: once true, auto-resolution will not overwrite url
  original_url: string | null; // first-ever URL before any manual override
}
```

**Upsert semantics** (`ON CONFLICT DO UPDATE`):

| Field | Behavior |
|---|---|
| `url` | Updated to new value, **unless** `manual_override = true` (manual URL preserved) |
| `manual_override` | `old OR new` — once set true it never reverts |
| `original_url` | `COALESCE(existing, new_url)` — set on first insert, never overwritten |

**`backfill_original_cover_art.py`**: one-off script for rows where `manual_override = true AND original_url IS NULL` (listens manually corrected before migration 019 introduced the column). Queries the iTunes Search API and sets `original_url` without touching `url` or `manual_override`. Run once after deploying migration 019, or after manually overriding art for a batch of tracks.

**Source of truth:** `backend/app/db.py` (`CoverArtCache`), migrations 009, 010, 019

## ArtistCorrections (database entity)

Stores known artist name mismatches introduced by scrobblers that submit metadata verbatim from the source (e.g. YouTube Music often omits punctuation). After every sync, `apply_artist_corrections()` in `repository.py` bulk-updates any `listens` rows whose `artist` matches a `wrong_name` entry.

```typescript
interface ArtistCorrection {
  id: number;            // auto-increment primary key
  wrong_name: string;    // UNIQUE — the string as submitted by the scrobbler
  correct_name: string;  // canonical MusicBrainz / official name
  created_at: Date;
}
```

**Source of truth:** `artist_corrections` table; seeded and updated via Alembic migrations.

### Adding a new correction

1. Create a new Alembic migration (e.g. `009_add_artist_correction_foo.py`):
   ```python
   def upgrade() -> None:
       op.execute("INSERT INTO artist_corrections (wrong_name, correct_name) VALUES ('Wrong Name', 'Correct Name')")
       op.execute("UPDATE listens SET artist = 'Correct Name' WHERE artist = 'Wrong Name'")

   def downgrade() -> None:
       op.execute("UPDATE listens SET artist = 'Wrong Name' WHERE artist = 'Correct Name'")
       op.execute("DELETE FROM artist_corrections WHERE wrong_name = 'Wrong Name'")
   ```
2. Run `pixi run alembic upgrade head` locally, then deploy — Alembic applies it to prod on startup.

**Do not** add `INSERT` rows to an already-applied migration — Alembic tracks the current revision and will not re-run it.

## Pydantic request/response schemas

Every endpoint's request and response model is defined in one place — read it there rather than
duplicating each field here.

**Source of truth:** [backend/app/schemas.py](../backend/app/schemas.py)

The current surface, grouped by area:

- **Summary & charts** — `StatsSummaryResponse`; `TopArtistsResponse` / `TopTracksResponse` (each wraps `items` + `total_count` for pagination) with `ArtistInfo` / `TrackInfo`; `MonthlyTrendInfo`; `WeeklyBreakdownItem`; `StreakStatsResponse`
- **Listens** — `ListenEntry` (the API shape of a corrected listen — see below); `TrackStatsResponse`; `TrackBatchRequestItem` / `TrackBatchResponseItem`
- **Corrections** — `ListenCorrectionRequest`; `TrackCorrectionRequest`; `TrackRevertRequest`
- **Wrapped** — `WrappedDataResponse` and its parts (`WrappedArtist`, `WrappedTrack`, `WrappedPeakDay`, `OnRepeatPeak`)
- **Artist Explorer** — `ArtistStatsResponse` (totals, rank, `top_tracks`, `monthly_trends`, `peak_day`, `hourly`, discovery, `total_track_count`); `TopArtistTrendsResponse` / `ArtistTrendResponse` with `ArtistTrendSeries` / `TrackTrendSeries`
- **On This Day** — `OnThisDayResponse` (prior-year `groups` + `anniversaries`), `OnThisDayGroup`, `ArtistAnniversary`
- **Now playing** — `PlayingNowResponse` (live status with a `last_played` DB fallback), `LastPlayedEntry`
- **Sync** — `SyncStartResponse`, `SyncStatusResponse`
- **Narrative** — `NarrativeResponse`
- **Cover art** — `CoverArtResult`; `CoverArtSearchResponse`
- **MusicBrainz** — `MBRecordingResult`; `MBSearchResponse`

### ListenEntry — key fields

`ListenEntry` reflects the **corrected** view of a listen (from `corrected_listens`), not the raw row. Correction-related fields:

| Field | Type | Description |
|---|---|---|
| `id` | `int` | DB primary key |
| `artist`, `title`, `album`, `duration_secs`, `recording_mbid` | effective values | After applying listen and/or track corrections |
| `has_listen_correction` | `bool` | A per-listen correction row exists |
| `has_track_correction` | `bool` | A canonical track correction applies |
| `track_id` | `int \| null` | `canonical_tracks.id` when a track correction applies |
| `original_artist`, `original_title`, `original_album`, `original_duration_secs`, `original_recording_mbid` | `string \| null` | Raw listen values — only populated when a correction exists and they differ from the effective value |
| `original_cover_art_url` | `string \| null` | Pre-override art URL from `cover_art_cache.original_url` — only set when `manual_override = true` on that cache row |
| `cover_art_url` | `string \| null` | Resolved art URL (populated by `_populate_cover_art` in the route layer, not stored in `listens`) |
| `track_play_count` | `int \| null` | All-time play count for this track (populated on demand) |

### ArtistStatsResponse — key fields

| Field | Type | Description |
|---|---|---|
| `total_plays` | `int` | Plays in the requested time range |
| `total_track_count` | `int` | Distinct corrected titles in the requested time range |
| `rank` | `int \| null` | All-time global rank (ignores time range) |
| `top_tracks` | `ArtistTopTrack[]` | Each entry includes `representative_listen_id` — the most-recent listen ID for that track, used to open the MetadataCorrectionDrawer |

Invariants worth knowing:

- `NarrativeResponse` splits keys into `plain` (no accent markers) and `rich` (`[[...]]` markers — render via `NarrativeText`, never `{@html}`).
- `SyncStatusResponse` counts are distinct: `synced_count` = rows inserted, `updated_count` = rows modified (mirror metadata / `recording_mbid` backfill), `deleted_count` = mirror surplus removed.
- `duration_secs` / `album` / `recording_mbid` are nullable for pre-LB imports (see the `Listen` entity above).
- `original_*` fields on `ListenEntry` are only populated by `get_listen_with_originals` (the single-listen fetch path). Batch list endpoints do not populate them.

## Environment config

**Source of truth:** [backend/app/db.py](../backend/app/db.py), [backend/app/sync.py](../backend/app/sync.py), [backend/app/main.py](../backend/app/main.py)

| Variable                | Default                       | Purpose                                                                                                                                      |
| ----------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `DATABASE_URL`          | _(unset)_                     | PostgreSQL connection string. If set, overrides SQLite. Schemes `postgres://` and `postgresql://` are normalized to `postgresql+psycopg://`. |
| `DATABASE_PATH`         | `backend/history.db`          | Path to SQLite file. Ignored when `DATABASE_URL` is set.                                                                                     |
| `JSON_PATH`             | `backend/merged_history.json` | Path to bootstrap JSON for initial DB population.                                                                                            |
| `TZ`                    | _(unset)_                     | Timezone applied to PostgreSQL sessions (`SET timezone=…`). No effect on SQLite.                                                             |
| `LISTENBRAINZ_USERNAME` | _(required for sync)_         | ListenBrainz account username.                                                                                                               |
| `LISTENBRAINZ_TOKEN`    | _(required for sync)_         | ListenBrainz user token.                                                                                                                     |
| `SYNC_TOKEN`            | _(required to enable sync)_   | Shared secret guarding `POST /api/sync`. Requests must send a matching `X-Sync-Token` header. If unset, the route fails closed with `503`. Set this in the Render service env. |
| `LOG_LEVEL`             | `INFO`                        | Python logging level for `app.*` loggers (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Set to `DEBUG` on Render when diagnosing issues. |
