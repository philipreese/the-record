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
- **Top charts** — top artists and tracks, filterable by time range (30 / 90 / 365 days / all time)
- **Calendar heatmap** — daily play counts laid out as a GitHub-style calendar, by year
- **Hourly heat clock** — play distribution across hours of the day (24-hour ring)
- **Monthly bar chart** — chronological monthly play counts
- **Listening streaks** — current and longest consecutive daily listening streaks
- **Wrapped reviews** — Spotify Wrapped-style aggregation by year, quarter, or month: total plays, top artist, top track, peak day, minutes listened
- **Background sync** — ListenBrainz sync runs in the background; the UI polls for progress without blocking

## Non-goals

- Social features (following, sharing, activity feeds)
- Music recommendations or discovery
- Playlist management or playback
- Real-time scrobbling (the app reads history, it does not capture it)
- Last.fm integration
