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

## Pydantic request/response schemas

Every endpoint's request and response model is defined in one place — read it there rather than
duplicating each field here.

**Source of truth:** [backend/app/schemas.py](../backend/app/schemas.py)

The current surface, grouped by area:

- **Summary & charts** — `StatsSummaryResponse`; `TopArtistsResponse` / `TopTracksResponse` (each wraps `items` + `total_count` for pagination) with `ArtistInfo` / `TrackInfo`; `MonthlyTrendInfo`; `WeeklyBreakdownItem`; `StreakStatsResponse`
- **Listens** — `ListenEntry` (the API shape of a `Listen`); `TrackStatsResponse`; `TrackBatchRequestItem` / `TrackBatchResponseItem`
- **Wrapped** — `WrappedDataResponse` and its parts (`WrappedArtist`, `WrappedTrack`, `WrappedPeakDay`, `OnRepeatPeak`)
- **Artist Explorer** — `ArtistStatsResponse` (totals, rank, `top_tracks`, `monthly_trends`, `peak_day`, `hourly`, discovery); `TopArtistTrendsResponse` / `ArtistTrendResponse` with `ArtistTrendSeries` / `TrackTrendSeries`
- **On This Day** — `OnThisDayResponse` (prior-year `groups` + `anniversaries`), `OnThisDayGroup`, `ArtistAnniversary`
- **Now playing** — `PlayingNowResponse` (live status with a `last_played` DB fallback), `LastPlayedEntry`
- **Sync** — `SyncStartResponse`, `SyncStatusResponse`
- **Narrative** — `NarrativeResponse`

Invariants worth knowing:

- `NarrativeResponse` splits keys into `plain` (no accent markers) and `rich` (`[[...]]` markers — render via `NarrativeText`, never `{@html}`).
- `SyncStatusResponse` counts are distinct: `synced_count` = rows inserted, `updated_count` = rows modified (mirror metadata / `recording_mbid` backfill), `deleted_count` = mirror surplus removed.
- `duration_secs` / `album` / `recording_mbid` are nullable for pre-LB imports (see the `Listen` entity above).

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
