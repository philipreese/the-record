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
routes.py          — HTTP handlers, request validation, background task dispatch
    ↓
repository.py      — All SQL queries (stats, charts, heatmap, trends, streak, wrapped)
    ↓
db.py              — SQLAlchemy engine/session setup, Listen model, init_db (runs alembic upgrade head)
db_helpers.py      — SQL dialect abstraction (date/hour/month expressions for SQLite vs PostgreSQL)
sync.py            — ListenBrainz sync worker (async, background)
schemas.py         — Pydantic request/response models
migrations/        — Alembic env + versioned migration scripts
```

**Source of truth:** [backend/app/](../backend/app/)

## Frontend layer map

```
api.ts             — Fetch wrapper, typed against api-types.ts; retries idempotent GETs (6×2s) through cold starts and backend restarts
    ↓
store.svelte.ts    — AppCache class (Svelte 5 runes: $state); owns the response cache, sync orchestration + invalidation,
                     and 20s visibility-locked playing-now polling (with baseline data recovery on reconnect)
    ↓
Views              — OverviewView, ChartsView, WrappedView, SettingsView, RecentView
    ↓
Components
  layout/          — PageHeader, Navbar, Sidebar, PeriodSelector, LoadingSpinner, ScrollNavButton, SelectDropdown
  dashboard/       — Heatmap, HourlyHeatClock, MonthlyBarChart, StreakTracker, StatsGrid,
                     AnimatedCounter, NowPlaying, WrappedCard, ListenRow
  overview/        — HeatmapSection, DiurnalSection, TelemetrySection, RecentScrobblesSection
  settings/        — ThemeSelector, DataSyncPanel
```

**Source of truth:** [frontend/src/](../frontend/src/)

## REST API

All routes are prefixed `/api`. See [backend/app/routes.py](../backend/app/routes.py) for the authoritative list.

| Method | Path | Query params | Response |
|---|---|---|---|
| GET | `/api/stats` | — | `StatsSummaryResponse` |
| GET | `/api/top-artists` | `range` (30/90/365/all), `limit` (default 15) | `ArtistInfo[]` |
| GET | `/api/top-tracks` | `range` (30/90/365/all), `limit` (default 15) | `TrackInfo[]` |
| GET | `/api/heatmap` | `year` (optional int) | `Record<string, int>` |
| GET | `/api/trends/hourly` | — | `Record<string, int>` |
| GET | `/api/trends/monthly` | — | `MonthlyTrendInfo[]` |
| GET | `/api/trends/streak` | — | `StreakStatsResponse` |
| GET | `/api/wrapped` | `year` (required), `quarter` (Q1–Q4, optional), `month` (M1–M12, optional) | `WrappedDataResponse` |
| POST | `/api/sync` | `mode` (normal/full, default normal); requires `X-Sync-Token` header | `SyncStartResponse` |
| GET | `/api/sync/status` | — | `SyncStatusResponse` |
| GET | `/api/playing-now` | — | `PlayingNowResponse` (LB live status + last-played fallback + cover art) |
| GET | `/api/last-played` | — | `PlayingNowResponse` (DB-only, no LB call — fast cold-start pre-population) |

### Sync authentication

`POST /api/sync` is the only mutating route and is protected by a shared secret:

- The request must send header `X-Sync-Token` matching the `SYNC_TOKEN` environment variable, else `401`.
- If `SYNC_TOKEN` is unset on the server the route **fails closed** with `503` rather than running unauthenticated.
- `GET /api/sync/status` stays public (read-only). Public visitors without a token see the dashboard read-only; sync controls are hidden in the UI until a token is saved.

The frontend stores the token in `localStorage` (`syncToken`) via `AppCache.setSyncToken()` and attaches it in `triggerSync()`.

## Sync strategy

**Source of truth:** [backend/app/sync.py](../backend/app/sync.py)

### Modes

| Mode | Behavior |
|---|---|
| `normal` | Two-pass: Pass A fetches new scrobbles since the local watermark (forward); Pass B backfills if LB total > local count (jumpsto oldest local timestamp and scans backward) |
| `full` | Single pass scanning all LB pages newest→oldest, deduplicating against local DB in memory |

### Deduplication

Duplicate key: `(unix_ts, artist.lower(), title.lower())`. Applied twice:
1. **In-flight** — in-memory key set built before each pass; new entries are checked before inserting
2. **Post-sync** — `deduplicate_listens()` in `repository.py` runs after every sync to catch cross-session duplicates (e.g. same scrobble from two apps)

### Retry / rate limiting

- Transient connection errors (`RemoteProtocolError`, `ReadTimeout`, `ConnectError`): up to 5 retries with backoff `[5, 15, 30, 60, 120]` seconds
- HTTP 429: sync halts and sets `error` state with retry-after hint

### API polling

The frontend posts to `POST /api/sync`, then polls `GET /api/sync/status` every 2 seconds via `AppCache.runSync()`. On `finished: true`, cache is invalidated so all views refetch fresh data.

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
