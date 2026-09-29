"""Serve the production app without exposing backend files or hiding API errors."""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class FrontendFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        response = await super().get_response(path, scope)
        if path in (".", "index.html", "sw.js", "manifest.webmanifest"):
            response.headers["Cache-Control"] = "no-cache"
        return response


def mount_frontend(app: FastAPI, directory: str | None) -> None:
    if not directory:
        return
    dist = Path(directory).resolve()
    required = ("index.html", "manifest.webmanifest", "sw.js", "offline.html", "icon-192.png", "icon-512.png")
    if any(not (dist / name).is_file() for name in required):
        raise RuntimeError("Music production frontend is missing assets; build it before startup")

    @app.get("/healthz", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.mount("/", FrontendFiles(directory=dist, html=True), name="frontend")
