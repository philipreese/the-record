import asyncio
import os
import sys
import unittest
from unittest import mock

# Adjust path to import backend modules
tests_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(tests_dir)
sys.path.append(backend_dir)

# Hermetic tests: neutralize DATABASE_URL before importing project code, which
# calls load_dotenv() at import (app.main here). A populated local .env would
# otherwise point the tests at PRODUCTION. Empty = SQLite; load_dotenv's default
# override=False won't replace an already-set key.
os.environ["DATABASE_URL"] = ""

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

    @mock.patch("app.routes.repo.get_track_stats_batch")
    def test_track_stats_batch_endpoint(self, mock_get_stats_batch) -> None:
        mock_get_stats_batch.return_value = [
            {"artist": "Radiohead", "title": "Creep", "play_count": 5, "duration_secs": 200},
            {"artist": "Mitski", "title": "Nobody", "play_count": 10, "duration_secs": 190},
        ]

        payload = [
            {"artist": "Radiohead", "title": "Creep"},
            {"artist": "Mitski", "title": "Nobody"},
        ]
        res = self.client.post("/api/track-stats/batch", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [
            {"artist": "Radiohead", "title": "Creep", "play_count": 5, "duration_secs": 200},
            {"artist": "Mitski", "title": "Nobody", "play_count": 10, "duration_secs": 190},
        ])
        mock_get_stats_batch.assert_called_once_with([
            {"artist": "Radiohead", "title": "Creep"},
            {"artist": "Mitski", "title": "Nobody"},
        ])


class TestTrendRoutes(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    @mock.patch("app.routes.repo.get_top_artist_trends")
    def test_top_artist_trends_route(self, mock_get_trends) -> None:
        mock_get_trends.return_value = {
            "year": 2026,
            "trends": [
                {
                    "artist": "Radiohead",
                    "play_count": 10,
                    "monthly_counts": [{"month": "2026-01", "count": 10}]
                }
            ]
        }

        res = self.client.get("/api/top-artist-trends", params={"year": 2026, "limit": 5})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {
            "year": 2026,
            "trends": [
                {
                    "artist": "Radiohead",
                    "play_count": 10,
                    "monthly_counts": [{"month": "2026-01", "count": 10}]
                }
            ]
        })
        mock_get_trends.assert_called_once_with(year=2026, limit=5)

    @mock.patch("app.routes.repo.get_artist_track_trends")
    def test_artist_track_trends_route(self, mock_get_trends) -> None:
        mock_get_trends.return_value = {
            "artist": "Radiohead",
            "year": 2026,
            "trends": [
                {
                    "track": "Creep",
                    "play_count": 10,
                    "monthly_counts": [{"month": "2026-01", "count": 10}]
                }
            ]
        }

        res = self.client.get("/api/artist-trend", params={"artist": "Radiohead", "year": 2026, "limit": 5})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {
            "artist": "Radiohead",
            "year": 2026,
            "trends": [
                {
                    "track": "Creep",
                    "play_count": 10,
                    "monthly_counts": [{"month": "2026-01", "count": 10}]
                }
            ]
        })
        mock_get_trends.assert_called_once_with(artist="Radiohead", year=2026, limit=5)

    def test_artist_trend_empty_artist(self) -> None:
        res = self.client.get("/api/artist-trend", params={"artist": "  ", "year": 2026})
        self.assertEqual(res.status_code, 400)


class TestExtractRecordingMbid(unittest.TestCase):
    """recording_mbid resolution prefers LB's mbid_mapping over additional_info (#156)."""

    def test_prefers_mbid_mapping(self) -> None:
        meta = {
            "mbid_mapping": {"recording_mbid": "MAPPED"},
            "additional_info": {"recording_mbid": "SUBMITTED"},
        }
        self.assertEqual(sync_worker._extract_recording_mbid(meta), "MAPPED")

    def test_falls_back_to_additional_info(self) -> None:
        meta = {"additional_info": {"recording_mbid": "SUBMITTED"}}
        self.assertEqual(sync_worker._extract_recording_mbid(meta), "SUBMITTED")

    def test_empty_mbid_mapping_falls_back(self) -> None:
        meta = {"mbid_mapping": {}, "additional_info": {"recording_mbid": "SUBMITTED"}}
        self.assertEqual(sync_worker._extract_recording_mbid(meta), "SUBMITTED")

    def test_none_when_absent(self) -> None:
        self.assertIsNone(sync_worker._extract_recording_mbid({"additional_info": {}}))
        self.assertIsNone(sync_worker._extract_recording_mbid({}))


if __name__ == "__main__":
    unittest.main()

