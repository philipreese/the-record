# Product — The Record

> Part of the [modular specification](README.md).

## Vision

A self-hosted dashboard that gives you a complete, unified view of your music listening history — aggregated from multiple sources, queryable over any time range, and visualized as trends, heatmaps, and periodic wrapped reviews.

## Supported sources

| Source         | Import method                                     |
| -------------- | ------------------------------------------------- |
| ListenBrainz   | Live background sync (incremental or full rescan) |
| YouTube Music  | Historical export import script                   |
| Google Takeout | Historical export import script                   |

## Core features

- **Stats summary** — total listens, unique artists/tracks, days active, average plays/day, most-used source
- **Top charts** — top artists and tracks, filterable by time range (30 / 90 / 365 days / all time); live search and pagination
- **Calendar heatmap** — daily play counts laid out as a GitHub-style calendar, by year
- **Hourly heat clock** — play distribution across hours of the day (24-hour ring)
- **Punchcard chart** — day-of-week × hour heat grid showing when in the week listening tends to happen
- **Monthly bar chart** — chronological monthly play counts
- **Temporal streamgraph** — top 5 artists month-by-month for a selected year, rendered as a custom SVG streamgraph; hover to highlight a stream with exact counts, click to drill into that artist's top 5 tracks over time
- **Artist Explorer** — dedicated per-artist page: total plays, all-time rank, discovery date, peak day, and hourly listening shape, plus a monthly-trend chart and a sortable, paginated track list (album, duration, first/last heard) alongside a log-scale per-track play-count chart. Reached by clicking an artist anywhere they appear
- **Listening streaks** — current and longest consecutive daily listening streaks
- **On This Day** — plays from the same calendar date in prior years, surfaced on the Overview; discovery anniversaries fed from first-listen dates
- **Wrapped reviews** — Spotify Wrapped-style aggregation by year, quarter, or month: total plays, top artist, top track, peak day, minutes listened, on-repeat peak (most replayed track in a single day)
- **Journal** — chronological recent-plays feed with expandable per-listen detail panels (album, duration, inline play count for that track); date-jump control to seek to any point in history
- **Narrative engine** — Dynamically generated plain-language copy across the Overview, Wrapped cards, sidebar, and section headers. Drawn from a curated JSON template database (441 templates, 84 keys) evaluated against streak and stats conditions (specificity-first: the most specific true condition wins over a generic fallback). Seeded by UTC date for stable daily randomization; manual rotation available from Settings. Accent phrases rendered via `NarrativeText.svelte` using `[[...]]` delimiters — no `{@html}`, XSS-safe.
- **Export** — Download full listening history as CSV or JSON, with optional time-range filter, from the Settings page
- **Background sync** — ListenBrainz sync runs in the background; the UI polls for progress without blocking. Reconcile mode detects and removes plays deleted upstream.
- **Writing** — Rendered Markdown blog posts at `/blog` (index) and `/blog/:slug` (post). Posts live in `frontend/src/content/blog/` with YAML frontmatter (title, slug, date, blurb); parsed and rendered client-side via `marked`. Sidebar nav entry highlighted for both views.

## Non-goals

- Social features (following, sharing, activity feeds)
- Music recommendations or discovery
- Playlist management or playback
- Real-time scrobbling (the app reads history, it does not capture it)
- Last.fm integration
