# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.3](https://github.com/philipreese/the-record/compare/v0.5.2...v0.5.3) (2026-06-16)


### Bug Fixes

* **frontend:** Fix mobile navbar, header sizing, counter re-animation, and period tab visibility ([2c63542](https://github.com/philipreese/the-record/commit/2c6354259c6eff31c975f9be57a2bab676fe2e91))


### Documentation

* **spec:** Update frontend component tree and remove completed view decomposition backlog item ([0c252c5](https://github.com/philipreese/the-record/commit/0c252c50f78773580cc09f2a1b23240f5b4aa777))


### Miscellaneous

* **frontend:** Decompose all views into focused sub-components ([e942a73](https://github.com/philipreese/the-record/commit/e942a731da557002f7892876da14e774bf539100))

## [0.5.2](https://github.com/philipreese/the-record/compare/v0.5.1...v0.5.2) (2026-06-16)


### Documentation

* **spec:** Document LOG_LEVEL env var in data-models and .env.example ([6d458d5](https://github.com/philipreese/the-record/commit/6d458d52df6a75db5b2b97d759c684999d9e8047))


### Miscellaneous

* **logging:** Replace print() with logging module in sync, db, and routes ([1928e7a](https://github.com/philipreese/the-record/commit/1928e7aee05a8c8f44486d30e10ff4db2874b184))

## [0.5.1](https://github.com/philipreese/the-record/compare/v0.5.0...v0.5.1) (2026-06-16)


### Bug Fixes

* **ci:** Bump deploy workflow to Node 24 to match lock file ([3c6f688](https://github.com/philipreese/the-record/commit/3c6f6889f4dbdd7842a235405973f5be0d777e02))

## [0.5.0](https://github.com/philipreese/the-record/compare/v0.4.2...v0.5.0) (2026-06-16)


### Features

* **backend:** Add GET /api/playing-now endpoint with last-played fallback ([5180600](https://github.com/philipreese/the-record/commit/518060070fa321fcf6b62a69849b7934a6dbcd3f))
* **frontend:** Add Now Playing widget with visibility-locked polling and album art mood color ([c7ed8f8](https://github.com/philipreese/the-record/commit/c7ed8f86ed4a816a1bdabf711d560487e99f0143))


### Bug Fixes

* **backend:** Add session cache and MB text-search fallback for cover art ([553ccd1](https://github.com/philipreese/the-record/commit/553ccd1b93d6aeb442eb5d82f0fec7cc5bd8fbc8))
* **backend:** Resolve direct CAA URL and fall back to recording_mbid for cover art ([f470dab](https://github.com/philipreese/the-record/commit/f470dabeebf81b2ec5ad18cb4b5921756f8b7990))
* **backend:** Resolve last-played art, fix UA, stop caching failed art lookups ([66285ce](https://github.com/philipreese/the-record/commit/66285ce160b6723948a2304f0757124c76f74d5e))
* **frontend:** Fix Now Playing widget — compact art, CORS, ambient color ([e52d764](https://github.com/philipreese/the-record/commit/e52d7643c414087557fb0f36419e39ad4ae64bc8))
* **frontend:** Harden now-playing polling — cold start, grace period, immediate sync ([1c3c767](https://github.com/philipreese/the-record/commit/1c3c7674288e03fe751dff571f4e6f270d0fd1e2))
* **frontend:** Harden now-playing widget color, art, and resilience ([f9f5439](https://github.com/philipreese/the-record/commit/f9f543995c80d0c96cecc38bbdf008a6ec4d4f56))
* **frontend:** Live dynamic color in settings chip; extract accent in store ([c813bb6](https://github.com/philipreese/the-record/commit/c813bb6bc8ead659aa23184855c5a212092adfc7))
* **frontend:** Persist dynamic accent across refresh and theme switches ([7dfaac5](https://github.com/philipreese/the-record/commit/7dfaac5c011fc9c9d3db9afbf4fabb40831a363c))
* **frontend:** Show art and ambient color for last-played, fix soft sync reload ([63b0eaf](https://github.com/philipreese/the-record/commit/63b0eafafbfe39defbfec1e48ef3d894678cc72c))
* **frontend:** Silence eslint no-unused-expressions in NowPlaying effect ([2b4e857](https://github.com/philipreese/the-record/commit/2b4e857aaf1b808242f50b1eb92a9751c17cee53))


### Tests

* **frontend:** Update retry tests for 6x2s retry parameters ([b01cc18](https://github.com/philipreese/the-record/commit/b01cc1893308c04478a0b8c4d8e6760d1307b731))


### Miscellaneous

* Add gitattributes to normalize line endings to LF ([161dff2](https://github.com/philipreese/the-record/commit/161dff28eeb403aa916de3d36d018fa688ac78ae))
* **ci:** Bump Node to 24 to match local npm 11 lock file; update architecture doc ([4b64ae7](https://github.com/philipreese/the-record/commit/4b64ae7ab03cd1f8b10a7f62e4af7ce3b72dc775))
* **ci:** Split test task into test-backend and test-frontend ([9966f1a](https://github.com/philipreese/the-record/commit/9966f1a0c4e69b13e99ff43e740cb9e78f82704a))
* **frontend:** Add eslint-plugin-tailwindcss for Tailwind v4 linting ([e0154a1](https://github.com/philipreese/the-record/commit/e0154a101bdb01fb4c7e04c199ea4f7501253dd9))
* **frontend:** Replace arbitrary px/rem values with Tailwind shorthands ([3735bea](https://github.com/philipreese/the-record/commit/3735bea06a29f0a6afcb5e6bde422c9013ef7b65))

## [0.4.2](https://github.com/philipreese/the-record/compare/v0.4.1...v0.4.2) (2026-06-15)


### Code Refactoring

* **frontend:** Make keyed view caches reactively refetch on invalidation ([bab35cc](https://github.com/philipreese/the-record/commit/bab35cc703a4738a67ea01087859c9f92ad327b1))


### Continuous Integration

* **frontend:** Run vitest in CI and refresh stale roadmap/CI docs ([078844b](https://github.com/philipreese/the-record/commit/078844b2a75720fee02fa98a36afff6373e29fb7))


### Miscellaneous

* **frontend:** Dedupe in-flight charts and heatmap fetches ([1e18b7d](https://github.com/philipreese/the-record/commit/1e18b7d6ba45bcd043e089ce97de500d3434b256))
* **frontend:** Retry cold-start GETs and dedupe in-flight wrapped fetches ([bb3affc](https://github.com/philipreese/the-record/commit/bb3affce23457654b2417ab55ceb3390a223388a))

## [0.4.1](https://github.com/philipreese/the-record/compare/v0.4.0...v0.4.1) (2026-06-15)


### Bug Fixes

* **api:** Require X-Sync-Token on POST /api/sync and fix sync-state race ([878601f](https://github.com/philipreese/the-record/commit/878601f15f6872a6698e8968f902eee9d12083a3))
* **frontend:** Clarify the sync token is a server secret, not the ListenBrainz token ([95b89bc](https://github.com/philipreese/the-record/commit/95b89bca5aa250f4aecc5227cc56908efd2d8182))
* **frontend:** Point dev API proxy at 127.0.0.1 instead of localhost ([231ec9b](https://github.com/philipreese/the-record/commit/231ec9b0c244f6dee53bd8022fc9840cad616f2f))


### Documentation

* Add Git Workflow, Environment, Svelte, and Deployment rules to CLAUDE.md ([6fd400a](https://github.com/philipreese/the-record/commit/6fd400a940216ae15389a4a28b4ec29ec80bcbb4))
* **spec:** Document SYNC_TOKEN auth on POST /api/sync ([8e434de](https://github.com/philipreese/the-record/commit/8e434deecd5df55fe9bebe4f6eabad9bf62f7cc6))


### Tests

* **api:** Add route tests for sync token auth and start-sync race ([ecdd449](https://github.com/philipreese/the-record/commit/ecdd449dbca953dcef9b7ec9f4cd7de9c127b11d))
* **frontend:** Add vitest harness with sync token unit tests ([a712350](https://github.com/philipreese/the-record/commit/a7123500dd2d2b6060bc962aa1901173a549b81f))


### Miscellaneous

* **api:** Regenerate OpenAPI spec and types for X-Sync-Token header ([1962ba1](https://github.com/philipreese/the-record/commit/1962ba1920d427d29a4a77e6a94d5e4b8e45d3a0))
* **frontend:** Add ESLint + Prettier and resolve lint and format issues ([3b115e8](https://github.com/philipreese/the-record/commit/3b115e83c6128f36904c00dd6b1df21687feff2a))

## [0.4.0](https://github.com/philipreese/the-record/compare/v0.3.6...v0.4.0) (2026-06-15)


### Features

* Add recently played journal view with cursor-based pagination ([59cdfca](https://github.com/philipreese/the-record/commit/59cdfca22ac1834596ad4fac3df6d3e347f332b4))


### Bug Fixes

* **frontend:** Fix source label mapping and extract listen helpers to shared util ([4f41fcc](https://github.com/philipreese/the-record/commit/4f41fccd044691524b486237947f6e9f9aeaf523))
* **frontend:** Re-fetch journal on sync invalidation while view is mounted ([c3d77dc](https://github.com/philipreese/the-record/commit/c3d77dc56e276262e927de2c13756d9c9bbd5001))
* **frontend:** Re-fetch stats after sync so sidebar updates immediately ([0dea592](https://github.com/philipreese/the-record/commit/0dea5925b607972c1b7b96277b2161bd48079171))


### Documentation

* **spec:** Add CI and release-please setup guide ([8d086b5](https://github.com/philipreese/the-record/commit/8d086b5ffa5ff362591b45af33f3179a58796fde))


### Miscellaneous

* **frontend:** Apply canonical Tailwind class names ([02536b4](https://github.com/philipreese/the-record/commit/02536b4cd6b4a24e11438f87571dead98b83971f))

## [0.3.6](https://github.com/philipreese/the-record/compare/v0.3.5...v0.3.6) (2026-06-13)


### Bug Fixes

* **ci:** Use PAT for auto-merge so release PR merge triggers workflows ([ca15105](https://github.com/philipreese/the-record/commit/ca15105d93acd1acfd24c6b488d15c09a102c13b))

## [0.3.5](https://github.com/philipreese/the-record/compare/v0.3.4...v0.3.5) (2026-06-13)


### Bug Fixes

* **ci:** Pass --repo to gh pr merge so it works without a checkout ([af0d02c](https://github.com/philipreese/the-record/commit/af0d02cb6f91e5f31cab3a0f4d3530d3a30c2ec0))

## [0.3.4](https://github.com/philipreese/the-record/compare/v0.3.3...v0.3.4) (2026-06-13)


### Bug Fixes

* **ci:** Use PAT for release-please so Release PR triggers CI ([a50e02a](https://github.com/philipreese/the-record/commit/a50e02abae7b0dad0a506e0545c791ad254b4908))

## [0.3.3](https://github.com/philipreese/the-record/compare/v0.3.2...v0.3.3) (2026-06-13)


### Bug Fixes

* **ci:** Extract PR number from release-please JSON output; use rebase merge ([9ba2597](https://github.com/philipreese/the-record/commit/9ba25977090c6d561d6dabf3f69db6322d6f8085))
* **ci:** Remove Windows-only python-interpreter-path from pyrefly.toml ([c844406](https://github.com/philipreese/the-record/commit/c844406b3b5a157408321b6cb7f5d8ca7b94e540))
* **ci:** Use packages block in release-please-config for correct manifest matching ([6a2f001](https://github.com/philipreese/the-record/commit/6a2f001c8ea7669700829b3667897b1950fce86f))
* **ci:** Use TOML updater with correct jsonpath for pixi.toml version ([ac5e024](https://github.com/philipreese/the-record/commit/ac5e024bbe1e94a67c86cf16c38945b885e2a511))
* **tests:** Dispose SQLAlchemy engine in tearDown to prevent SQLite lock ([c4595c0](https://github.com/philipreese/the-record/commit/c4595c03226b224cf3753bf42ce82e5ce752f3fd))


### Documentation

* **changelog:** Add [Unreleased] entries for issue 21 ([3732c03](https://github.com/philipreese/the-record/commit/3732c036cf063df4266d71a04d1e8df1a55449f3))
* **spec:** Remove manual changelog step; release-please auto-generates from commits ([eb6c296](https://github.com/philipreese/the-record/commit/eb6c2960dd2008523b744526efd4e6300b39d59d))


### Continuous Integration

* Run backend tests, pyrefly, and svelte-check on pull requests ([b622576](https://github.com/philipreese/the-record/commit/b62257607ffd7955333e7a66765cb69c3d8a3add))

## [Unreleased]

## [0.3.2] - 2026-06-12

### Added
- **Alembic migrations**: Migration framework adopted (`backend/migrations/`); `env.py` wired to `get_engine()` so `DATABASE_URL`/`DATABASE_PATH` drive migrations and app identically
- **Baseline migration (001)**: Captures current `listens` schema for fresh deployments; existing deployments stamp with `pixi run alembic stamp 001`
- **Dedup index migration (002)**: Composite `idx_listens_dedup (artist, title, unix_ts)` supporting the post-sync dedup self-join in `repository.deduplicate_listens()`
- **`pixi run alembic`**: Task alias for `python -m alembic --config backend/alembic.ini` — works from any working directory
- **`scripts/set-issue-status.ps1`**: Helper to move a GitHub project board item to any status via `gh project item-edit`

### Changed
- **`init_db()`**: Now runs `alembic upgrade head` instead of `Base.metadata.create_all()` — schema is always migration-controlled
- **PostgreSQL engine**: `pool_pre_ping=True, pool_recycle=300` added to survive Neon serverless suspend/resume
- **Issue workflow**: `spec/standards.md` updated with "move to In Progress" step and project board field ID reference

## [0.3.1] - 2026-06-12

### Changed
- **API validation**: All query params now constrained with `Literal` types and `Query` bounds — invalid input returns 422 instead of 500 or silently misbehaving (`range`, `limit`, `quarter`, `month`, `mode`, `year`)
- **Frontend type safety**: Regenerated `api-types.ts` with tighter union types; extracted `TimeRange`, `WrappedQuarter`, `WrappedMonth`, `SyncMode` from the `paths` interface into `api.ts` function signatures for end-to-end TypeScript enforcement through to Svelte components

## [0.3.0] - 2026-06-11

### Documentation
- **Roadmap**: Added `spec/roadmap.md` covering Phases 2–4 (chart power-ups, artist explorer, multi-tenant auth), a Code Health backlog from the June 2026 codebase analysis, and a note that Phase 1 (features + hardening) is tracked as GitHub issues
- **AI agent config**: Added `CLAUDE.md` (project-level workspace instructions) and `GEMINI.md`

### Added
- **Verify script**: Added `scripts/verify-project.ps1` — standardized multi-runtime project verification script with secret scanning, git/commit convention checks, and auto-detection for Pixi, Node, Python, .NET, and Go environments

### Planning
- **GitHub issues #19–#25**: Opened Phase 1 feature issues (recently played journal #24, now playing widget #25) and hardening issues (sync token + race fix #19, param validation #20, CI tests #21, Alembic migrations #22, structured logging #23) with native GitHub dependency links

## [0.2.0] - 2026-06-11

### Documentation
- **Modular spec**: Added `spec/` folder with `README.md`, `product.md`, `architecture.md`, `data-models.md`, and `standards.md`
- **GitHub workflow**: Established project board, branch/commit conventions, issue and PR process
- **CHANGELOG**: Initialized this file
- **`.env.example`**: Added example environment variable file

## [0.1.0] - 2026-05-30

### Added
- **Phase 1 — Data pipeline**: Pixi environment setup, `merge_history.py` to consolidate ListenBrainz and Google Takeout/YouTube Music exports, and `import_listenbrainz.py` for incremental scrobble imports
- **Phase 2 — Dashboard**: FastAPI + Svelte 5/TypeScript dashboard with stats summary, calendar heatmap, hourly heat clock, streak tracker, top artists/tracks, monthly trends, and Wrapped/periodic reviews
- **ListenBrainz sync**: Background async sync worker with normal mode (two-pass forward + backfill) and full rescan mode; deduplication by `(unix_ts, artist, title)` tuple; retry with exponential backoff; rate-limit handling
- **Dual database support**: SQLAlchemy ORM layer supporting both local SQLite and remote PostgreSQL (Neon) via `DATABASE_URL`; SQL dialect abstraction in `db_helpers.py`
- **Frontend state and caching**: Svelte 5 runes-based `AppCache` store with per-endpoint response caching and full invalidation on sync completion
- **OpenAPI type sync**: `generate-api-types` task generates TypeScript types from the backend OpenAPI schema; frontend API client typed against generated output
- **Settings & sync UI**: Tabbed settings view with normal and full sync options; sidebar sync status indicator; auto-sync on page load
- **Visual design system**: Adaptive memory design with CSS variable theming, Catppuccin tokens, animated counters, scroll-driven reveals, and clock-drawing animation
- **Sticky navigation and layout polish**: Sticky navbar, page footer, responsive header sizing, heatmap label realignments
- **Deployment**: Render blueprint (`render.yaml`), Dockerfile with Pixi, GitHub Pages deploy pipeline, and `TZ` environment variable support for PostgreSQL session timezone
