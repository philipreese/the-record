# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
