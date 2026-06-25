# Architecture — The Record

> Part of the [modular specification](README.md).

## Stack

| Concern | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, Uvicorn |
| ORM / persistence | SQLAlchemy 2.0, SQLite (local) or PostgreSQL via psycopg v3 |
| Migrations | Alembic — `backend/migrations/`; `env.py` uses `get_engine()` so `DATABASE_URL`/`DATABASE_PATH` drive both app and CLI |
| HTTP client (sync) | httpx (async) |
| Frontend | Svelte 5, TypeScript, Vite |
| Styling | Tailwind CSS + DaisyUI |
| Package manager | Pixi (conda-based) + npm |
| Type sync | OpenAPI schema → `npx openapi-typescript` → `frontend/src/services/api-types.ts` |

## Backend layer map

```
routes.py          — HTTP handlers with typed return annotations (→ SchemaType); request validation, background task dispatch; WebSocket route /api/ws/sync
    ↓
repository.py      — All SQL queries; returns typed Pydantic schema instances (not raw dicts)
    ↓
db.py              — SQLAlchemy engine/session setup, Listen model, init_db (runs alembic upgrade head)
db_helpers.py      — SQL dialect abstraction (date/hour/month expressions for SQLite vs PostgreSQL)
sync.py            — ListenBrainz sync worker (async, background); calls apply_artist_corrections() after every sync so corrections survive mirror syncs; broadcasts sync_started/sync_complete/sync_error via ws.py
ws.py              — WebSocket ConnectionManager singleton; tracks active connections, broadcasts JSON events; broadcast_sync_event() helper used by sync.py
narrative.py       — Template loading, condition evaluation, {token} interpolation; accepts StatsSummaryResponse/StreakStatsResponse, returns NarrativeResponse
schemas.py         — Pydantic request/response models shared across routes.py, repository.py, and narrative.py
migrations/        — Alembic env + versioned migration scripts; artist_corrections table seeded here (see data-models.md for the workflow)
```

**Source of truth:** [backend/app/](../backend/app/)

## Frontend layer map

```
api.ts             — openapi-fetch typed client over api-types.ts; retries idempotent GETs (6×2s) through cold starts and backend restarts
sync-socket.ts     — SyncSocket class; WebSocket client for /api/ws/sync with exponential-backoff auto-reconnect (1s→30s cap)
    ↓
store.svelte.ts    — AppCache class (Svelte 5 runes: $state); owns the response cache, sync orchestration + invalidation,
                     20s visibility-locked playing-now polling, and WebSocket sync event handling (poll every 2s as fallback)
router.svelte.ts   — Hash-based router (no library); parses #/path?params, exposes typed route + URLSearchParams,
                     navigate() with push/replace policy. URL is the single source of truth for all serializable view state.
    ↓
Views              — one per route (Overview, Charts, Wrapped, Recent, Artist, Blog index/post, Settings, NotFound)
    ↓
Components          — grouped by role (see the file tree for the current set):
  (root)           — standalone visualizations + modal overlays (heatmaps, hour clock, punchcard, bar/stream charts, day & week detail overlays)
  layout/          — app chrome + reusable primitives (header, navbar, sidebar, footer, dropdowns, date picker, spinner, NarrativeText — XSS-safe accent rendering)
  dashboard/       — small composable display pieces (stats grid, animated counter, wrapped card, listen row)
  overview/        — section blocks assembled onto the Overview page (*Section.svelte)
  settings/        — settings panels (theme selector, data-sync panel)
```

**Source of truth:** [frontend/src/](../frontend/src/)

## REST API

All routes are prefixed `/api`. See [backend/app/routes.py](../backend/app/routes.py) for the authoritative list.

| Method | Path | Query params | Response |
|---|---|---|---|
| GET | `/api/stats` | — | `StatsSummaryResponse` |
| GET | `/api/top-artists` | `range` (30/90/365/all), `limit` (default 15), `search` (optional), `page` (default 1), `page_size` (optional) | `TopArtistsResponse` |
| GET | `/api/top-tracks` | `range` (30/90/365/all), `limit` (default 15), `search` (optional), `page` (default 1), `page_size` (optional) | `TopTracksResponse` |
| GET | `/api/heatmap` | `year` (optional int) | `Record<string, int>` |
| GET | `/api/trends/hourly` | — | `Record<string, int>` |
| GET | `/api/trends/punchcard` | — | `Record<string, int>` (day-of-week × hour) |
| GET | `/api/trends/monthly` | — | `MonthlyTrendInfo[]` |
| GET | `/api/trends/monthly/{year}/{month}/weekly` | — | `WeeklyBreakdownItem[]` |
| GET | `/api/trends/streak` | — | `StreakStatsResponse` |
| GET | `/api/wrapped` | `year` (required), `quarter` (Q1–Q4, optional), `month` (M1–M12, optional) | `WrappedDataResponse` |
| POST | `/api/sync` | `mode` (normal/mirror, default normal); requires `X-Sync-Token` header | `SyncStartResponse` |
| GET | `/api/sync/status` | — | `SyncStatusResponse` |
| GET | `/api/recent` | `limit` (default 50, max 100), `before_ts`, `before_id` (cursor pagination), `anchor_date` (optional YYYY-MM-DD) | `ListenEntry[]` |
| GET | `/api/day/{date_str}` | path `date_str` (YYYY-MM-DD) | `ListenEntry[]` (chronological) |
| GET | `/api/on-this-day` | — | `OnThisDayResponse` (prior-year groups + discovery anniversaries) |
| GET | `/api/export` | `format` (csv/json, default csv), `range` (default all) | streaming file download |
| GET | `/api/track-stats` | `artist` (required), `title` (required), `album` (optional — includes null-album rows when provided) | `TrackStatsResponse` |
| POST | `/api/track-stats/batch` | Request body: `TrackBatchRequestItem[]` | `TrackBatchResponseItem[]` |
| GET | `/api/narrative` | `seed` (optional string — defaults to UTC date for daily stability) | `NarrativeResponse` |
| GET | `/api/playing-now` | — | `PlayingNowResponse` (LB live status + last-played fallback; cover art resolved via background asyncio task, non-blocking) |
| GET | `/api/last-played` | — | `PlayingNowResponse` (DB-only, no LB call — fast cold-start pre-population) |
| GET | `/api/top-artist-trends` | `year` (required int), `limit` (default 5) | `TopArtistTrendsResponse` |
| GET | `/api/artist-trend` | `artist` (required), `year` (required int), `limit` (default 5) | `ArtistTrendResponse` |
| GET | `/api/artist/stats` | `name` (required), `range` (30/90/365/all, default all) | `ArtistStatsResponse` |

### WebSocket endpoints

| Path | Protocol | Events pushed |
|---|---|---|
| `/api/ws/sync` | WebSocket (`ws://` / `wss://`) | `sync_started`, `sync_complete`, `sync_error` (JSON `{type, mode, inserted?, deleted?, message?}`) |

Clients connect once on page load (via `SyncSocket`) and receive push events for the duration of the session. The connection manager drops dead connections silently on next broadcast.

### Sync authentication

`POST /api/sync` is the only mutating route and is protected by a shared secret:

- The request must send header `X-Sync-Token` matching the `SYNC_TOKEN` environment variable, else `401`.
- If `SYNC_TOKEN` is unset on the server the route **fails closed** with `503` rather than running unauthenticated.
- `GET /api/sync/status` stays public (read-only). Public visitors without a token see the dashboard read-only; sync controls are hidden in the UI until a token is saved.

The frontend stores the token in `localStorage` (`syncToken`) via `AppCache.setSyncToken()` and attaches it in `triggerSync()`.

## Sync strategy

**Source of truth:** [backend/app/sync.py](../backend/app/sync.py)

### Modes

| Mode | Behavior | When to use |
|---|---|---|
| `normal` | Two-pass additive sync: Pass A fetches new scrobbles since the local watermark; Pass B backfills if LB total > local count. Always additive. | Daily updates |
| `mirror` | Fetches complete LB history, inserts any missing rows, then deletes any local rows not found on LB. Treats LB as the single source of truth. Takes ~15–20 minutes for large histories. | After deleting listens on LB, or to do a full authoritative resync |

### Deduplication

Duplicate key: `(unix_ts, artist.lower(), title.lower())`. Applied twice in **normal** sync:
1. **In-flight** — in-memory key set built before each pass; new entries are checked before inserting
2. **Post-sync** — `deduplicate_listens()` in `repository.py` runs after normal sync (when rows were inserted) to catch cross-session duplicates (e.g. same scrobble from two apps); uses `LOWER()` in the JOIN so rows differing only in casing are correctly merged

Mirror sync does **not** run `deduplicate_listens()` — LB is the authority on which listens are valid. Exact-key duplicates in the local DB are instead handled during the surplus-deletion pass: all IDs per key are tracked, the lowest id is kept, and extras are deleted.

### Retry / rate limiting

- Transient connection errors (`RemoteProtocolError`, `ReadTimeout`, `ConnectError`): up to 5 retries with backoff `[5, 15, 30, 60, 120]` seconds
- HTTP 429: sync halts and sets `error` state with retry-after hint

### Sync completion delivery

A soft background sync fires automatically on page load once the WebSocket connection is established (so `sync_complete` is guaranteed to arrive). Users can also trigger syncs manually from the Settings view.

In both cases the frontend posts to `POST /api/sync`. The backend pushes `sync_started` and `sync_complete` (or `sync_error`) events over `/api/ws/sync`. On receiving `sync_complete`, the store fetches the final status from `GET /api/sync/status` and runs the post-sync cache refresh.

`GET /api/sync/status` is also polled every 2 seconds as a fallback for environments where the WebSocket is unavailable. On `finished: true`, the poll loop is cleared and the same refresh path runs.

## Dev tasks

| Task | Command |
|---|---|
| Run backend + frontend | `pixi run dev` |
| Backend only | `pixi run dev-backend` |
| Frontend only | `pixi run dev-frontend` |
| Run tests | `pixi run test` |
| Lint | `pixi run lint` |
| Regenerate TS types from OpenAPI | `pixi run generate-api-types` |
| Run Alembic commands | `pixi run alembic <cmd>` (e.g. `upgrade head`, `current`, `stamp 001`) |

**Source of truth:** [pixi.toml](../pixi.toml)
