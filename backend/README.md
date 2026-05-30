# The Record - Backend Services 🐍

This directory contains the FastAPI-powered Python backend. Powered by SQLAlchemy, it handles scrobble database management in SQLite or PostgreSQL, runs background data synchronization jobs with ListenBrainz, and exposes REST endpoints for the frontend client.

---

## 🏗 Architecture

The backend code is organized into a modular FastAPI application layout:

- **API Routes**: Exposes REST endpoints for stats, top charts, heatmaps, and reviews.
- **Repository Layer**: Encapsulates database queries using SQLAlchemy Core/ORM expressions, isolating database interactions from route logic and supporting multiple SQL dialects (SQLite and PostgreSQL).
- **Pydantic Validation**: Models request/response structures to enforce validation constraints and auto-generate OpenAPI documentation.
- **Background Synchronization**: Launches isolated background threads to fetch and deduplicate scrobbles without blocking incoming HTTP requests.

---

## 🚀 Getting Started

Ensure you have [Pixi](https://pixi.sh/) installed, then run:

### Start Backend Development Server
```bash
pixi run dev-backend
```
The server will run on [http://127.0.0.1:8000](http://127.0.0.1:8000). You can explore the interactive API docs at `/docs`.

---

## 🛠 Admin & Utility Scripts

We provide CLI tools under `backend/scripts/` to manage database records:

- `import_listenbrainz.py` — Run a manual command-line sync to fetch ListenBrainz scrobbles.
- `merge_history.py` — Parse and import historical data (such as Google Takeout export files) and merge duplicate scrobbles.
- `delete_listenbrainz.py` — Truncate the database (resets all plays).

---

## 🧪 Testing and Type Safety

### Run Unit Tests
```bash
pixi run test
```

### Static Analysis
Verify backend type annotations using the Pyrefly checker:
```bash
pixi run lint
```
