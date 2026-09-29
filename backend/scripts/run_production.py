"""Run Music from a built frontend and an explicitly selected existing database."""
import argparse
import os
from pathlib import Path

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve Music privately on loopback")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8741)
    args = parser.parse_args()
    database = args.database.resolve()
    repo = Path(__file__).resolve().parents[2]
    # Protected invariant: a typo must never silently create an empty history database.
    if not database.is_file():
        parser.error("The selected history database does not exist")
    dist = repo / "frontend" / "dist"
    if not (dist / "index.html").is_file():
        parser.error("Build the frontend before starting Music")
    os.environ["DATABASE_URL"] = ""
    os.environ["DATABASE_PATH"] = str(database)
    os.environ["FRONTEND_DIST"] = str(dist)
    uvicorn.run("app.main:app", app_dir=str(repo / "backend"), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
