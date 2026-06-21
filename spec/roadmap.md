# Roadmap — The Record

> Part of the [modular specification](README.md).
>
> Phases 1 and 2 are complete.
>
> Revised June 2026 after a roadmap review and codebase analysis: hardening issues added to Phase 1 (sync protection moved out of Phase 4, plus param validation, CI tests, Alembic baseline, logging), On This Day moved into Phase 2, migrations/routing made explicit prerequisites.

---


## Phase 3 — Artist Explorer

*Transform artist names into deep-dive portals.*

### Writing / Blog Posts ✓ complete — PR #141
Markdown-rendered blog posts served from `frontend/src/content/blog/`. Index view at `/blog`, individual post at `/blog/:slug`. Frontmatter (title, slug, date, blurb) parsed client-side; `marked` handles HTML rendering with scoped prose styles. Sidebar "Writing" nav entry (pencil icon) active-highlighted for both route types. Router extended with `blog` and `blog-post` route variants.

### URL Routing & Deep Links ✓ complete — PR #137
Hash-based router (`services/router.svelte.ts`) ships all five tabs as addressable `#/path?params` URLs. Overlay states (heatmap day, month → week), year selectors, charts range/search, and Wrapped period are all serialized to query params and survive reload and back-button navigation. Artist route (`#/artist/:name`) is stubbed and ready for Phase 3. A 404 view handles unrecognised paths.

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

| Idea                              | Issue | Notes                                                                                                                                                                                                                                                                                                                  |
| --------------------------------- | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Listening Eras**                | #42   | Auto-segment history into named chapters by detecting shifts in the dominant-artist distribution (e.g. month-over-month cosine distance on top-10 artist vectors). Rendered as labeled record sides: *"Side A: The Boards of Canada Winter (Nov 2023 – Feb 2024)."* The feature-sized version of the narrative engine. |
| **Gap Archaeology**               | #43   | The heatmap shows presence; silence is data too. Detect multi-day gaps, render them as labeled lacunae ("14 days of silence — June 2024"), let the user annotate them ("moved apartments"). First user-authored data in the system — previews the multi-tenant model.                                                  |
| **Wrapped Share Cards**           | #45   | Render the Wrapped summary to a downloadable PNG, client-side canvas — no backend, no social features (consistent with non-goals).                                                                                                                                                                                     |
| **Listening Concentration Index** | #46   | Gini coefficient over artist play counts: 0 = "you listen to everything equally", 1 = "one artist". Trend it over time; pairs with Sonic Silhouette as the "shape of your taste" axis.                                                                                                                                 |
| **Vinyl Shelf**                   | #47   | Top albums as record spines on a shelf — width ∝ play count, spine art from Cover Art Archive. Needs Phase 3's MusicBrainz release data.                                                                                                                                                                               |
| **Sonic Silhouette**              | #48   | Generated abstract SVG shape based on weekly listening metrics (morning vs evening, variety vs repeat). Changes over time.                                                                                                                                                                                             |
| **Analog Static Loading Effect**  | #49   | Subtle monochrome static/dust animation on panels during sync, reinforcing the physical archive aesthetic.                                                                                                                                                                                                             |

## Code health backlog

Remaining findings from the June 2026 codebase analysis not covered by the Phase 1 hardening issues. Pick these up opportunistically, or when the phase that makes them urgent approaches.

| Item                                        | Issue | Notes                                                                                                                                               | Bites when              |
| ------------------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| **PunchcardChart keyboard accessibility**   | #133  | `svelte-ignore a11y_no_static_element_interactions` on each SVG `<rect>` (168 cells); hover-only, no keyboard equivalent. Proper fix needs grouped `role="grid"` navigation — non-trivial. `Heatmap`, `HourlyHeatClock`, and modal backdrops are clean. | Opportunistic |
| **Dependency pins**                         | #53   | `fastapi`/`uvicorn`/`httpx` are `"*"` in `pixi.toml` — cap to current majors so a breaking bump can't arrive unreviewed via `pixi update`.          | Next `pixi update`      |
| **Docker image**                            | #54   | Pixi base image is conda-stack-sized; multi-stage build would cut Render cold-start pulls. Add a `HEALTHCHECK`.                                     | Whenever deploys feel slow |
| **Route return types**                      | #55   | Handlers are annotated `-> Any`; real return types let `pyrefly` catch handler/schema drift statically (`response_model` only enforces at runtime). | Opportunistic           |
| **Config module**                           | #56   | Centralize magic numbers: sync batch size (1000), backoff table, 2s inter-batch sleep, 60s dedup window, 3.5-min duration estimate.                 | Opportunistic           |
| **Wrapped year range**                      | #57   | Hardcoded 2020–2026 in `WrappedView`; `/api/stats` already returns `first_year` — derive it.                                                        | January 2027            |
| **Dead code**                               | #58   | `get_db_connection()` in `db.py` appears unused by the app — verify and delete.                                                                     | Opportunistic           |
