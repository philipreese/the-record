# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06-11

### Documentation
- **Modular spec**: Added `spec/` folder with `README.md`, `product.md`, `architecture.md`, `data-models.md`, and `standards.md`
- **GitHub workflow**: Established project board, branch/commit conventions, issue and PR process
- **CHANGELOG**: Initialized this file
- **`.env.example`**: Added example environment variable file

## [0.1.0] - 2026-06-11

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
