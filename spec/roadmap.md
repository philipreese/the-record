# Roadmap — The Record

> Part of the [modular specification](README.md).
>
> Phase 1 (Recently Played Feed, Now Playing, and the hardening track) is tracked as GitHub issues, not here.
>
> Revised June 2026 after a roadmap review and codebase analysis: hardening issues added to Phase 1 (sync protection moved out of Phase 4, plus param validation, CI tests, Alembic baseline, logging), On This Day moved into Phase 2, migrations/routing made explicit prerequisites.

---

## Phase 2 — Chart Power-ups & Data Exploration

*Make the existing charts richer, searchable, and explorable with temporal depth.*

### Temporal Charts (Artists & Tracks Over Time)
A custom SVG streamgraph or stacked area chart showing top artists/tracks month-by-month over a selected year — built with Svelte's native SVG bindings, no chart library dependency.

**Progressive Reveal:**
- Level 1 (Canopy): Flowing streamgraph of top 5 artists for the year
- Level 2 (Bloom): Hover dims other streams, surfaces a micro-card with exact play counts
- Level 3 (Deep Dive): Click a stream to zoom the timeline onto that artist, splitting into their top 5 tracks over time

**Backend:** Prefer a single `GET /api/top-artist-trends` returning the top N artists with their monthly breakdowns in one query (N separate calls is the wrong shape for the streamgraph). The per-artist `GET /api/artist-trend?artist=...&range=...` falls out of Phase 3's artist stats work anyway.

### Drill-Down Zoom Transitions
Physical zoom interactions throughout the dashboard using Svelte's `crossfade` or the Web View Transitions API:
- **Heatmap cell → Daily Journal:** Click a heatmap cell to expand it into a timeline overlay showing all tracks played on that day (with precise timestamps and source)
- **Monthly bar → Weekly breakdown:** Click a month bar to zoom into a weekly breakdown

Once click becomes the primary chart interface, the suppressed a11y warnings on the SVG charts become functional bugs — drill-down targets must be keyboard-reachable.

### Top Charts Search & Pagination
Add search, pagination, and rank lookup to the existing top charts:
- `search`, `page`, `page_size` query params on `/api/top-artists` and `/api/top-tracks` (enum/bounds-validated per the pattern from the Phase 1 hardening issues)
- Rank lookup via SQL window function: `RANK() OVER (ORDER BY COUNT(*) DESC)`
- Frontend: search bar + paginator in `ChartsView.svelte`, showing absolute rank of any searched artist or track

### Track Durations
`minutes_listened` is currently `total_plays × 3.5` — an estimate presented as a stat. ListenBrainz's `track_metadata.additional_info` frequently carries `duration_ms`.

- Nullable `duration_secs` column on `listens` (a routine Alembic migration once the Phase 1 baseline is in)
- Populate during sync; fall back to the 3.5-minute estimate only for null rows
- Turns Wrapped's flagship stat honest and unlocks real minutes everywhere (per-artist stats in Phase 3, narrative engine claims)

### On This Day
(Moved up from Phase 3 — it has no Phase 3 dependencies and is the best retention feature in the roadmap.)

A small widget on the Overview showing what was playing on this exact calendar date in prior years (1, 2, 5 years ago). Matches the "archaeological" design language and encourages daily visits.

**Backend:** `GET /api/on-this-day` returning listens grouped by year for today's month-day.

### Export / Download
(Promoted from backlog — trivially cheap, disproportionately valuable for a self-hosted data tool.)

One endpoint streaming the listening history as CSV or JSON, with a download button in Settings.

### Sync Deletions
The current sync is additive-only — deletes on ListenBrainz are never reflected locally. Add reconciliation:
- New sync mode `reconcile` on `POST /api/sync?mode=reconcile`
- Range-scoped by default (last 30/90/365 days) to avoid full scans
- Backend fetches all LB listens for the range, diffs against local DB, deletes the surplus
- Settings UI: "Sync Deletions" button alongside the existing sync controls

**Constraints (must be in the issue when created):**
- The diff must use the same canonical listen identity as the dedup logic — `(unix_ts, artist.lower(), title.lower())` — or reconcile will mass-delete rows that differ only in casing. (Note: the post-sync dedup SQL is currently case-*sensitive* while the in-flight key is case-*insensitive*; unify before building deletion logic on top.)
- Reconcile must scope to `source LIKE 'listenbrainz%'` rows — imported YouTube/Takeout listens don't exist on LB and would otherwise be deleted wholesale.

### Dynamic Narrative Engine
Replace the hardcoded hero narrative text on the Overview and Wrapped cards:

**Option A — Template database (zero cost):** A curated JSON file of poetic templates keyed by data conditions (e.g., `streak_over_30`, `top_source_listenbrainz`, `new_peak_day`). Randomly selected at render time.

**Option B — LLM-generated (low cost):** Call an LLM with the user's stats as context; cache the result for the session. Generates novel summaries but adds latency and API cost.

Start with Option A; Option B can be layered on top as a settings toggle. The condition keys are effectively a small rules engine — evaluate specificity-first, then randomize among matches, so the most interesting *true* statement wins rather than a generic one.

### Stretch: Day-of-Week × Hour Punchcard
The classic 7×24 punchcard grid. The hourly heat clock shows *when in the day*; this shows *when in the week* ("Sunday morning listener"). Reuses the heatmap's cell-rendering approach.

---

## Phase 3 — Artist Explorer

*Transform artist names into deep-dive portals.*

### URL Routing & Deep Links (prerequisite — do first)
The current navigation is a single `activeTab` state variable: no shareable URLs, no back button, no history. Artist pages "opened by clicking any artist name anywhere in the app" demand addressable routes (`/artist/Boards%20of%20Canada`), and Phase 2's drill-down states (heatmap day, month → week) deserve URLs too.

A tiny hash-based router (or `svelte-routing`) is enough — this does not require SvelteKit. Retrofitting routing under a shipped ArtistView is much worse than scoping it first.

### Artist Detail Page
A new `ArtistView.svelte` opened by clicking any artist name anywhere in the app.

**Profile panel** (from MusicBrainz / Cover Art Archive / Wikipedia):
- Artist bio and disambiguation
- Cover photo / artist image
- Discography listing with album art

**Personal stats panel** (from local DB):
- Total plays and listening rank across all artists
- Listening trend chart (monthly plays for this artist)
- Top tracks by this artist
- Peak day, peak hour, listening streak
- Per-artist hourly heat clock

**Backend:** New endpoint `GET /api/artist/{name}/stats` returning personal listening stats. Separate proxy/cache layer for MusicBrainz lookups to avoid hammering their API.

### Discovery Timeline & Artist Anniversaries
`MIN(unix_ts) GROUP BY artist` is already in the data:
- First-listen events: "You discovered Caroline Polachek on March 3, 2022 — 412 plays since"
- Anniversaries feed the On This Day widget: "4 years since your first Mitski listen"
- Discovery date + rank shown on the Artist Detail page

---

## Phase 4 — Multi-Tenant & Privacy

*Transition from a personal single-user dashboard to a safely hosted multi-user app.*

> Sync route protection moved to the Phase 1 hardening issues (it protects today's deployment, not just the multi-user one). Schema changes here are routine Alembic migrations thanks to the Phase 1 baseline.

### Google OAuth2 Authentication
Full multi-user login flow:

1. Frontend "Login with Google" → Google OAuth consent screen
2. Google redirects back to FastAPI with an authorization code
3. FastAPI exchanges code for Google profile, registers user if new, issues a signed JWT
4. Frontend attaches `Authorization: Bearer <token>` to all API requests
5. FastAPI middleware validates the JWT and extracts `current_user_id` on every protected route

### Multi-Tenant Database Schema
- New `users` table: `id` (UUID PK), `email`, `google_id`, `listenbrainz_username`, `encrypted_lb_token`
- `listens` table gains `user_id` FK → `users.id`
- All repository queries gain a `user_id` filter: `.where(Listen.user_id == current_user_id)`
- Composite index: `(user_id, unix_ts)`
- ListenBrainz tokens encrypted at rest using `cryptography.Fernet`
- Sync state moves from the in-process global to a DB row (per-user sync status; multi-worker safe)

### ListenBrainz Account Linking
After login, users connect their ListenBrainz account from the Settings page:
- Input field for LB username + API token
- Backend validates the token against the LB API before saving
- Token is Fernet-encrypted before writing to the DB

### Scrobbler Privacy Toggle
(Promoted from backlog — belongs in the same milestone as multi-user.)

Per-user setting to make a profile public or private; private profiles return 404 to other users.

---

## Backlog / Future Ideas

These came up in planning but aren't yet scoped into a phase.

| Idea                                | Notes                                                                                                                                                                                          |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Listening Eras**                  | Auto-segment history into named chapters by detecting shifts in the dominant-artist distribution (e.g. month-over-month cosine distance on top-10 artist vectors). Rendered as labeled record sides: *"Side A: The Boards of Canada Winter (Nov 2023 – Feb 2024)."* The feature-sized version of the narrative engine. |
| **Gap Archaeology**                 | The heatmap shows presence; silence is data too. Detect multi-day gaps, render them as labeled lacunae ("14 days of silence — June 2024"), let the user annotate them ("moved apartments"). First user-authored data in the system — previews the multi-tenant model. |
| **On-Repeat Badges**                | Max same-track plays in a single day, all-time and per Wrapped period. "*Motion Sickness* — 19 plays on Oct 12, 2024." One `GROUP BY date, artist, title` query.                                  |
| **Wrapped Share Cards**             | Render the Wrapped summary to a downloadable PNG, client-side canvas — no backend, no social features (consistent with non-goals).                                                              |
| **Listening Concentration Index**   | Gini coefficient over artist play counts: 0 = "you listen to everything equally", 1 = "one artist". Trend it over time; pairs with Sonic Silhouette as the "shape of your taste" axis.          |
| **Vinyl Shelf**                     | Top albums as record spines on a shelf — width ∝ play count, spine art from Cover Art Archive. Needs Phase 3's MusicBrainz release data.                                                        |
| **Sonic Silhouette**                | Generated abstract SVG shape based on weekly listening metrics (morning vs evening, variety vs repeat). Changes over time.                                                                       |
| **Analog Static Loading Effect**    | Subtle monochrome static/dust animation on panels during sync, reinforcing the physical archive aesthetic.                                                                                       |

## Code health backlog

Remaining findings from the June 2026 codebase analysis not covered by the Phase 1 hardening issues. Pick these up opportunistically, or when the phase that makes them urgent approaches.

| Item | Notes | Bites when |
|---|---|---|
| **Chart keyboard accessibility** | `svelte-ignore a11y_*` suppressions on interactive SVGs in `Heatmap` and `HourlyHeatClock`; hover-only interactions have no keyboard equivalent. | Phase 2 drill-downs (also noted there) |
| **Dependency pins** | `fastapi`/`uvicorn`/`httpx` are `"*"` in `pixi.toml` — cap to current majors so a breaking bump can't arrive unreviewed via `pixi update`. | Next `pixi update` |
| **Docker image** | Pixi base image is conda-stack-sized; multi-stage build would cut Render cold-start pulls. Add a `HEALTHCHECK`. | Whenever deploys feel slow |
| **Route return types** | Handlers are annotated `-> Any`; real return types let `pyrefly` catch handler/schema drift statically (`response_model` only enforces at runtime). | Opportunistic |
| **Config module** | Centralize magic numbers: sync batch size (1000), backoff table, 2s inter-batch sleep, 60s dedup window, 3.5-min duration estimate. | Opportunistic |
| **Wrapped year range** | Hardcoded 2020–2026 in `WrappedView`; `/api/stats` already returns `first_year` — derive it. | January 2027 |
| **Dead code** | `get_db_connection()` in `db.py` appears unused by the app — verify and delete. | Opportunistic |
