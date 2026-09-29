import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.web import mount_frontend


class TestFrontendServing(unittest.TestCase):
    def test_requires_complete_build(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "index.html").write_text("Music", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                mount_frontend(FastAPI(), directory)

    def test_static_boundaries_and_api_routes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory) / "dist"
            dist.mkdir()
            for name in ("index.html", "manifest.webmanifest", "sw.js", "offline.html", "icon-192.png", "icon-512.png"):
                (dist / name).write_text("Music", encoding="utf-8")
            (Path(directory) / ".env").write_text("private", encoding="utf-8")
            app = FastAPI()
            @app.get("/api/example")
            def example() -> dict[str, bool]:
                return {"ok": True}
            mount_frontend(app, str(dist))
            client = TestClient(app)
            self.assertEqual(client.get("/").text, "Music")
            self.assertEqual(client.get("/healthz").json(), {"status": "ok"})
            self.assertEqual(client.get("/api/example").json(), {"ok": True})
            for path in ("/api/missing", "/.env", "/%2e%2e/.env", "/history.db"):
                self.assertEqual(client.get(path).status_code, 404)
            self.assertEqual(client.get("/sw.js").headers["cache-control"], "no-cache")


if __name__ == "__main__":
    unittest.main()
