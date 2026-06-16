import asyncio
import os
import sys
import unittest
from unittest import mock

# Adjust path to import backend modules
tests_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(tests_dir)
sys.path.append(backend_dir)

from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

import app.sync as sync_worker
from app.main import app


def _reset_sync_state() -> None:
    s = sync_worker._sync_state
    s.running = False
    s.mode = ""
    s.batches_fetched = 0
    s.synced_count = 0
    s.lb_total = 0
    s.local_total = 0
    s.error = None
    s.finished = False


class TestSyncAuth(unittest.TestCase):
    """POST /api/sync token enforcement (issue #19 acceptance criteria)."""

    def setUp(self) -> None:
        # Plain instantiation does not run the lifespan, so no DB bootstrap.
        self.client = TestClient(app)
        _reset_sync_state()
        # Replace the background sync with a no-op so no network calls happen.
        self._patcher = mock.patch.object(sync_worker, "_run_sync")
        self._patcher.start()

    def tearDown(self) -> None:
        self._patcher.stop()
        _reset_sync_state()

    def test_missing_token_returns_401(self) -> None:
        with mock.patch.dict(os.environ, {"SYNC_TOKEN": "secret"}):
            res = self.client.post("/api/sync")
        self.assertEqual(res.status_code, 401)

    def test_wrong_token_returns_401(self) -> None:
        with mock.patch.dict(os.environ, {"SYNC_TOKEN": "secret"}):
            res = self.client.post("/api/sync", headers={"X-Sync-Token": "nope"})
        self.assertEqual(res.status_code, 401)

    def test_unset_token_returns_503(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SYNC_TOKEN", None)
            res = self.client.post("/api/sync", headers={"X-Sync-Token": "anything"})
        self.assertEqual(res.status_code, 503)

    def test_valid_token_starts(self) -> None:
        with mock.patch.dict(os.environ, {"SYNC_TOKEN": "secret"}):
            res = self.client.post("/api/sync", headers={"X-Sync-Token": "secret"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "started")

    def test_already_running_returns_already_running(self) -> None:
        sync_worker._sync_state.running = True
        with mock.patch.dict(os.environ, {"SYNC_TOKEN": "secret"}):
            res = self.client.post("/api/sync", headers={"X-Sync-Token": "secret"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "already_running")

    def test_status_endpoint_stays_public(self) -> None:
        res = self.client.get("/api/sync/status")
        self.assertEqual(res.status_code, 200)


class TestSyncRace(unittest.IsolatedAsyncioTestCase):
    """The asyncio.Lock guards the check-then-act so only one sync starts."""

    async def asyncSetUp(self) -> None:
        _reset_sync_state()

    async def asyncTearDown(self) -> None:
        _reset_sync_state()

    async def test_concurrent_starts_only_one_wins(self) -> None:
        from app.routes import start_sync

        async def call() -> str:
            res = await start_sync(
                background_tasks=BackgroundTasks(),
                mode="normal",
                x_sync_token="secret",
            )
            return res["status"]

        with mock.patch.dict(os.environ, {"SYNC_TOKEN": "secret"}), \
                mock.patch.object(sync_worker, "_run_sync"):
            results = await asyncio.gather(call(), call(), call())

        self.assertEqual(results.count("started"), 1)
        self.assertEqual(results.count("already_running"), 2)


class TestTrackStatsRoute(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    @mock.patch("app.routes.repo.get_track_stats")
    def test_track_stats_endpoint(self, mock_get_stats) -> None:
        mock_get_stats.return_value = (5, 200)

        # Call without album
        res = self.client.get("/api/track-stats", params={"artist": "Radiohead", "title": "Creep"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"play_count": 5, "duration_secs": 200})
        mock_get_stats.assert_called_with(artist="Radiohead", title="Creep", album=None)

        # Call with album
        res = self.client.get("/api/track-stats", params={"artist": "Radiohead", "title": "Creep", "album": "Pablo Honey"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"play_count": 5, "duration_secs": 200})
        mock_get_stats.assert_called_with(artist="Radiohead", title="Creep", album="Pablo Honey")


if __name__ == "__main__":
    unittest.main()
