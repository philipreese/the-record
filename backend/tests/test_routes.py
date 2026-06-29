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
    s.updated_count = 0
    s.deleted_count = 0
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
        # added/modified/deleted counts are all exposed
        body = res.json()
        self.assertIn("synced_count", body)
        self.assertIn("updated_count", body)
        self.assertIn("deleted_count", body)


class TestSyncRace(unittest.IsolatedAsyncioTestCase):
    """The asyncio.Lock guards the check-then-act so only one sync starts."""

    async def asyncSetUp(self) -> None:
        _reset_sync_state()

    async def asyncTearDown(self) -> None:
        _reset_sync_state()

    async def test_concurrent_starts_only_one_wins(self) -> None:
        from app.api.sync import start_sync

        async def call() -> str:
            res = await start_sync(
                background_tasks=BackgroundTasks(),
                mode="normal",
                x_sync_token="secret",
            )
            return res.status

        with mock.patch.dict(os.environ, {"SYNC_TOKEN": "secret"}), \
                mock.patch.object(sync_worker, "_run_sync"):
            results = await asyncio.gather(call(), call(), call())

        self.assertEqual(results.count("started"), 1)
        self.assertEqual(results.count("already_running"), 2)


class TestTrackStatsRoute(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    @mock.patch("app.api.listens.repo.get_track_stats")
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

    @mock.patch("app.api.listens.repo.get_track_stats_batch")
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

    @mock.patch("app.api.listens.repo.get_track_stats_batch")
    def test_track_stats_batch_rejects_oversized_payload(self, mock_get_stats_batch) -> None:
        from app.api.listens import _MAX_BATCH_TRACKS

        payload = [{"artist": f"A{i}", "title": f"T{i}"} for i in range(_MAX_BATCH_TRACKS + 1)]
        res = self.client.post("/api/track-stats/batch", json=payload)
        self.assertEqual(res.status_code, 422)
        mock_get_stats_batch.assert_not_called()


class TestTrendRoutes(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    @mock.patch("app.api.artists.repo.get_top_artist_trends")
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

    @mock.patch("app.api.artists.repo.get_artist_track_trends")
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


class TestPlayingNowBroadcaster(unittest.IsolatedAsyncioTestCase):
    """PlayingNowBroadcaster push and initial-state delivery (#195)."""

    async def test_subscribe_receives_cached_state_immediately(self) -> None:
        from app.playing_now_sse import PlayingNowBroadcaster

        broadcaster = PlayingNowBroadcaster()
        broadcaster._last = {"is_playing": False}

        gen = broadcaster.subscribe()
        chunk = await gen.__anext__()
        self.assertIn('"is_playing": false', chunk)
        await gen.aclose()

    async def test_subscribe_receives_broadcast(self) -> None:
        import json
        from app.playing_now_sse import PlayingNowBroadcaster

        broadcaster = PlayingNowBroadcaster()
        gen = broadcaster.subscribe()

        # The generator only registers its queue after the first __anext__() call.
        # Use create_task so pushing runs concurrently after the generator reaches q.get().
        async def feed() -> None:
            await asyncio.sleep(0)  # yield once so the generator can register its queue
            for q in list(broadcaster._queues):
                q.put_nowait({"is_playing": True, "artist": "Radiohead", "title": "Creep"})

        feed_task = asyncio.create_task(feed())
        chunk = await gen.__anext__()
        await feed_task
        await gen.aclose()

        data = json.loads(chunk.removeprefix("data: ").strip())
        self.assertTrue(data["is_playing"])
        self.assertEqual(data["artist"], "Radiohead")


class TestArtistGraphQL(unittest.TestCase):
    """GraphQL /api/graphql artist query (#193)."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    @mock.patch("app.graphql_schema.repo.get_artist_stats")
    def test_artist_query_returns_data(self, mock_stats) -> None:
        from app.schemas import (
            ArtistMonthlyTrend,
            ArtistStatsResponse,
            ArtistTopTrack,
            WrappedPeakDay,
        )

        mock_stats.return_value = ArtistStatsResponse(
            artist="Radiohead",
            total_plays=100,
            rank=1,
            top_tracks=[
                ArtistTopTrack(title="Creep", play_count=50, album="Pablo Honey"),
                ArtistTopTrack(title="Karma Police", play_count=30, album="OK Computer"),
            ],
            monthly_trends=[ArtistMonthlyTrend(month="2024-01", count=50)],
            peak_day=WrappedPeakDay(date="2024-01-15", plays=12),
            hourly={f"{h:02d}": 0 for h in range(24)},
            first_listen_ts=1000000,
            plays_since_discovery=100,
        )

        query = """
        {
          artist(name: "Radiohead") {
            artist
            totalPlays
            rank
            topAlbums { name playCount }
            monthlyTrends { month count }
            peakDay { date plays }
          }
        }
        """
        res = self.client.post("/api/graphql", json={"query": query})
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]["artist"]
        self.assertEqual(data["artist"], "Radiohead")
        self.assertEqual(data["totalPlays"], 100)
        self.assertEqual(data["rank"], 1)
        # top_albums derived from tracks
        album_names = [a["name"] for a in data["topAlbums"]]
        self.assertIn("Pablo Honey", album_names)
        self.assertIn("OK Computer", album_names)
        self.assertEqual(data["peakDay"]["date"], "2024-01-15")

    @mock.patch("app.graphql_schema.repo.get_artist_stats")
    def test_unknown_artist_returns_null(self, mock_stats) -> None:
        from app.schemas import ArtistStatsResponse

        mock_stats.return_value = ArtistStatsResponse(
            artist="Unknown",
            total_plays=0,
            rank=None,
            top_tracks=[],
            monthly_trends=[],
            peak_day=None,
            hourly={f"{h:02d}": 0 for h in range(24)},
        )

        res = self.client.post("/api/graphql", json={"query": '{ artist(name: "Unknown") { artist } }'})
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.json()["data"]["artist"])

    @mock.patch("app.graphql_schema.repo.get_artist_stats")
    def test_artist_query_exposes_total_track_count(self, mock_stats) -> None:
        from app.schemas import ArtistStatsResponse, ArtistTopTrack

        mock_stats.return_value = ArtistStatsResponse(
            artist="Radiohead",
            total_plays=50,
            total_track_count=3,
            rank=1,
            top_tracks=[
                ArtistTopTrack(title="Creep", play_count=25),
                ArtistTopTrack(title="Karma Police", play_count=15),
                ArtistTopTrack(title="Fake Plastic Trees", play_count=10),
            ],
            monthly_trends=[],
            peak_day=None,
            hourly={f"{h:02d}": 0 for h in range(24)},
        )
        query = "{ artist(name: \"Radiohead\") { totalPlays totalTrackCount } }"
        res = self.client.post("/api/graphql", json={"query": query})
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]["artist"]
        self.assertEqual(data["totalPlays"], 50)
        self.assertEqual(data["totalTrackCount"], 3)

    def test_graphiql_available(self) -> None:
        res = self.client.get("/api/graphql", headers={"Accept": "text/html"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.headers["content-type"])


class TestSyncWebSocket(unittest.TestCase):
    """WebSocket /api/ws/sync endpoint connectivity (#192)."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_ws_endpoint_accepts_connections(self) -> None:
        with self.client.websocket_connect("/api/ws/sync"):
            pass


class TestConnectionManager(unittest.IsolatedAsyncioTestCase):
    """ConnectionManager broadcast and dead-connection cleanup (#192)."""

    async def test_broadcast_delivers_to_connected_client(self) -> None:
        from unittest.mock import AsyncMock, MagicMock
        from app.ws import ConnectionManager

        mgr = ConnectionManager()
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()

        mgr._connections.append(mock_ws)
        await mgr.broadcast({"type": "sync_started", "mode": "normal"})

        mock_ws.send_json.assert_called_once_with({"type": "sync_started", "mode": "normal"})

    async def test_broadcast_drops_dead_connections(self) -> None:
        from unittest.mock import AsyncMock, MagicMock
        from app.ws import ConnectionManager

        mgr = ConnectionManager()
        dead_ws = MagicMock()
        dead_ws.send_json = AsyncMock(side_effect=Exception("connection lost"))

        mgr._connections.append(dead_ws)
        await mgr.broadcast({"type": "sync_complete"})

        self.assertEqual(len(mgr._connections), 0)


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


class TestListenRoutes(unittest.TestCase):
    """GET /api/listens/{id} and DELETE /api/listens/{id}."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    @mock.patch("app.services.cover_art.repo.get_cover_art_batch", return_value={})
    @mock.patch("app.api.corrections.repo.get_listen_with_originals")
    def test_get_listen_returns_entry(self, mock_get, _art) -> None:
        from app.schemas import ListenEntry
        mock_get.return_value = ListenEntry(
            id=1, artist="Radiohead", title="Creep", unix_ts=1000000, source="youtube_music"
        )
        res = self.client.get("/api/listens/1")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["id"], 1)
        self.assertEqual(body["artist"], "Radiohead")
        mock_get.assert_called_once_with(1)

    @mock.patch("app.api.corrections.repo.get_listen_with_originals", return_value=None)
    def test_get_listen_returns_404_for_unknown(self, _) -> None:
        res = self.client.get("/api/listens/99999")
        self.assertEqual(res.status_code, 404)

    @mock.patch("app.api.corrections.repo.delete_listen")
    @mock.patch("app.api.corrections.repo.get_listen_by_id")
    def test_delete_listen_returns_204(self, mock_get_raw, mock_delete) -> None:
        from app.schemas import ListenEntry
        mock_get_raw.return_value = ListenEntry(
            id=1, artist="Radiohead", title="Creep", unix_ts=1000000, source="youtube_music"
        )
        res = self.client.delete("/api/listens/1")
        self.assertEqual(res.status_code, 204)
        mock_delete.assert_called_once_with(1)

    @mock.patch("app.api.corrections.repo.get_listen_by_id", return_value=None)
    def test_delete_listen_returns_404_when_not_found(self, _) -> None:
        res = self.client.delete("/api/listens/99999")
        self.assertEqual(res.status_code, 404)


class TestListenCorrectionRoutes(unittest.TestCase):
    """POST /api/listens/{id}/correction and /correction/revert."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    @mock.patch("app.services.cover_art.repo.get_cover_art_batch", return_value={})
    @mock.patch("app.api.corrections.repo.get_listen_with_originals")
    @mock.patch("app.api.corrections.repo.save_listen_correction")
    @mock.patch("app.api.corrections.repo.get_listen_by_id")
    def test_post_correction_saves_changed_field(
        self, mock_raw, mock_save, mock_updated, _art
    ) -> None:
        from app.schemas import ListenEntry
        mock_raw.return_value = ListenEntry(
            id=1, artist="Radiohead", title="Creep", unix_ts=1000000, source="youtube_music"
        )
        mock_updated.return_value = ListenEntry(
            id=1, artist="Radiohead UK", title="Creep", unix_ts=1000000, source="youtube_music"
        )
        res = self.client.post("/api/listens/1/correction", json={"artist": "Radiohead UK"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["artist"], "Radiohead UK")
        mock_save.assert_called_once()

    @mock.patch("app.api.corrections.repo.get_listen_by_id", return_value=None)
    def test_post_correction_returns_404_for_unknown_listen(self, _) -> None:
        res = self.client.post("/api/listens/99999/correction", json={"artist": "X"})
        self.assertEqual(res.status_code, 404)

    @mock.patch("app.services.cover_art.repo.get_cover_art_batch", return_value={})
    @mock.patch("app.api.corrections.repo.get_listen_with_originals")
    @mock.patch("app.api.corrections.repo.delete_listen_correction")
    def test_revert_correction_removes_and_returns_raw(
        self, mock_delete, mock_get, _art
    ) -> None:
        from app.schemas import ListenEntry
        mock_get.return_value = ListenEntry(
            id=1, artist="Original Artist", title="Creep",
            unix_ts=1000000, source="youtube_music", has_listen_correction=False,
        )
        res = self.client.post("/api/listens/1/correction/revert")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["artist"], "Original Artist")
        mock_delete.assert_called_once_with(1)

    @mock.patch("app.api.corrections.repo.get_listen_with_originals", return_value=None)
    def test_revert_correction_returns_404_for_unknown(self, _) -> None:
        res = self.client.post("/api/listens/99999/correction/revert")
        self.assertEqual(res.status_code, 404)


class TestTrackCorrectionRoutes(unittest.TestCase):
    """POST /api/tracks/correction and /api/tracks/correction/revert."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    @mock.patch("app.services.cover_art.repo.get_cover_art_batch", return_value={})
    @mock.patch("app.api.corrections.repo.get_listen_with_originals")
    @mock.patch("app.api.corrections.repo.save_track_correction", return_value=42)
    @mock.patch("app.api.corrections.repo.get_representative_listen_id", return_value=1)
    def test_post_track_correction_returns_updated_listen(
        self, _rep, _save, mock_get, _art
    ) -> None:
        from app.schemas import ListenEntry
        mock_get.return_value = ListenEntry(
            id=1, artist="Radiohead", title="Creep", unix_ts=1000000,
            source="youtube_music", album="Pablo Honey",
        )
        req = {
            "corrected_artist": "Radiohead",
            "corrected_title": "Creep",
            "corrections": {"album": "Pablo Honey"},
        }
        res = self.client.post("/api/tracks/correction", json=req)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["album"], "Pablo Honey")

    @mock.patch("app.api.corrections.repo.save_track_correction", return_value=None)
    @mock.patch("app.api.corrections.repo.get_representative_listen_id", return_value=None)
    def test_post_track_correction_returns_404_when_no_listens(self, _, __) -> None:
        req = {
            "corrected_artist": "NoOne",
            "corrected_title": "NoTrack",
            "corrections": {"album": "X"},
        }
        res = self.client.post("/api/tracks/correction", json=req)
        self.assertEqual(res.status_code, 404)

    @mock.patch("app.services.cover_art.repo.get_cover_art_batch", return_value={})
    @mock.patch("app.api.corrections.repo.get_listen_with_originals")
    @mock.patch("app.api.corrections.repo.delete_track_correction")
    @mock.patch("app.api.corrections.repo.get_representative_listen_id_by_track_id", return_value=1)
    def test_revert_track_correction_deletes_and_returns_listen(
        self, _rep, mock_delete, mock_get, _art
    ) -> None:
        from app.schemas import ListenEntry
        mock_get.return_value = ListenEntry(
            id=1, artist="Radiohead", title="Creep", unix_ts=1000000, source="youtube_music"
        )
        req = {"track_id": 42, "corrected_artist": "Radiohead", "corrected_title": "Creep"}
        res = self.client.post("/api/tracks/correction/revert", json=req)
        self.assertEqual(res.status_code, 200)
        mock_delete.assert_called_once()


class TestTrackListensRoutes(unittest.TestCase):
    """GET and DELETE /api/tracks/listens."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    @mock.patch("app.services.cover_art.repo.get_cover_art_batch", return_value={})
    @mock.patch("app.api.corrections.repo.get_track_listens")
    def test_get_track_listens_returns_list(self, mock_get, _art) -> None:
        from app.schemas import ListenEntry
        mock_get.return_value = [
            ListenEntry(id=1, artist="Radiohead", title="Creep", unix_ts=1000000, source="youtube_music"),
            ListenEntry(id=2, artist="Radiohead", title="Creep", unix_ts=999000, source="last_fm"),
        ]
        res = self.client.get("/api/tracks/listens", params={"artist": "Radiohead", "title": "Creep"})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(len(body), 2)
        self.assertEqual(body[0]["artist"], "Radiohead")
        mock_get.assert_called_once_with("Radiohead", "Creep")

    @mock.patch("app.services.cover_art.repo.get_cover_art_batch", return_value={})
    @mock.patch("app.api.corrections.repo.get_track_listens", return_value=[])
    def test_get_track_listens_returns_empty_list_for_unknown(self, _, _art) -> None:
        res = self.client.get("/api/tracks/listens", params={"artist": "Nobody", "title": "Nothing"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

    @mock.patch("app.api.corrections.repo.delete_track_listens", return_value=5)
    def test_delete_track_listens_returns_204(self, mock_delete) -> None:
        res = self.client.delete("/api/tracks/listens", params={"artist": "Radiohead", "title": "Creep"})
        self.assertEqual(res.status_code, 204)
        mock_delete.assert_called_once_with("Radiohead", "Creep")

    @mock.patch("app.api.corrections.repo.delete_track_listens", return_value=0)
    def test_delete_track_listens_returns_404_when_not_found(self, _) -> None:
        res = self.client.delete("/api/tracks/listens", params={"artist": "Nobody", "title": "Nothing"})
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main()

