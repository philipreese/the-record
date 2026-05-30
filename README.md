# The Record 🎧

**The Record** is a self-hosted dashboard for syncing, archiving, and analyzing your music listening history. Powered by SQLAlchemy, it merges scrobbles from ListenBrainz and play histories from other sources (e.g. YouTube Music / Google Takeout) into a unified database (supporting both local SQLite and remote PostgreSQL), offering custom listening trends, activity heatmaps, and Spotify-Wrapped style periodic reviews.

---

## 🏗 Project Layout

- `backend/` — FastAPI Python backend managing SQLite/PostgreSQL, synchronization threads, and REST API endpoints.
- `frontend/` — Svelte 5 single-page application built with Vite, TypeScript, Tailwind CSS, and DaisyUI.
- `pixi.toml` — Converted developer environments and tasks (backend/frontend dependencies, tests, linters).

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have the following installed:
- [Pixi](https://pixi.sh/) (Universal package manager for Conda/Python dependencies)
- [Node.js](https://nodejs.org/) (Version 18+)

### 2. Configure Environment
Create a `.env` file in the root of the project:
```env
LISTENBRAINZ_USERNAME="your_username"
LISTENBRAINZ_TOKEN="your_token"  # Optional, required for syncing private data

# Database (Optional, defaults to local SQLite backend/history.db if omitted)
# DATABASE_URL="postgresql://user:password@host/dbname?sslmode=require"

# Timezone (Optional, defaults to UTC on containers or local system time on host)
# TZ="America/New_York"
```

### 3. Run the App
Start both frontend and backend development servers concurrently:
```bash
pixi run dev
```
Open [http://localhost:5173](http://localhost:5173) to see the dashboard.

---

## 🛠 Developer Commands

Use Pixi to run standard development operations:

- `pixi run dev` — Run both servers concurrently.
- `pixi run dev-backend` — Start only the FastAPI backend server (reloadable).
- `pixi run dev-frontend` — Start only the Svelte frontend development server.
- `pixi run test` — Run the Python test suite.
- `pixi run lint` — Lint and typecheck both the backend (Pyrefly) and the frontend (svelte-check).
- `pixi run generate-api-types` — Regenerate frontend TypeScript types from the backend OpenAPI schema.