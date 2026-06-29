import asyncio
import os
import re
import sys
import unittest
from unittest import mock

import httpx
import respx

tests_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(tests_dir)
sys.path.append(backend_dir)

os.environ["DATABASE_URL"] = ""

import app.sync as sync_worker

_COUNT_URL = "https://api.listenbrainz.org/1/user/testuser/listen-count"
_LISTENS_RE = re.compile(r"https://api\.listenbrainz\.org/1/user/testuser/listens")


def _to_thread_se(fn, *args, **kwargs):
    """Side-effect for asyncio.to_thread mocks: cleanup functions return 0, others return an insert-result tuple."""
    if getattr(fn, "__name__", "") in ("apply_artist_corrections", "deduplicate_listens"):
        return 0
    return (0, 0, 0, set())


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


class TestSyncResilienceNormal(unittest.IsolatedAsyncioTestCase):
    """_fetch_page retry/backoff/429 behaviour in normal (_run_sync) mode."""

    async def asyncSetUp(self) -> None:
        _reset_sync_state()
        sync_worker._sync_state.running = True

    async def asyncTearDown(self) -> None:
        _reset_sync_state()

    @respx.mock
    async def test_429_halts_and_sets_error(self) -> None:
        respx.get(_COUNT_URL).mock(
            return_value=httpx.Response(200, json={"payload": {"count": 0}})
        )
        respx.get(_LISTENS_RE).mock(
            return_value=httpx.Response(429, headers={"X-RateLimit-Reset-In": "10"})
        )
        with mock.patch.dict(os.environ, {"LISTENBRAINZ_USERNAME": "testuser", "LISTENBRAINZ_TOKEN": "testtoken"}), \
             mock.patch("asyncio.to_thread", new_callable=mock.AsyncMock, side_effect=_to_thread_se), \
             mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
            await sync_worker._run_sync("normal")

        self.assertIsNotNone(sync_worker._sync_state.error)
        self.assertIn("Rate-limited", sync_worker._sync_state.error)
        self.assertIn("10", sync_worker._sync_state.error)
        self.assertTrue(sync_worker._sync_state.finished)

    @respx.mock
    async def test_transient_connect_error_retries_then_succeeds(self) -> None:
        respx.get(_COUNT_URL).mock(
            return_value=httpx.Response(200, json={"payload": {"count": 0}})
        )
        calls: list[int] = []

        def listens_side_effect(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            if len(calls) <= 2:
                raise httpx.ConnectError("connection refused")
            return httpx.Response(200, json={"payload": {"listens": []}})

        respx.get(_LISTENS_RE).mock(side_effect=listens_side_effect)

        sleep_calls: list[float] = []

        async def record_sleep(secs: float) -> None:
            sleep_calls.append(secs)

        with mock.patch.dict(os.environ, {"LISTENBRAINZ_USERNAME": "testuser", "LISTENBRAINZ_TOKEN": "testtoken"}), \
             mock.patch("asyncio.to_thread", new_callable=mock.AsyncMock, side_effect=_to_thread_se), \
             mock.patch("asyncio.sleep", side_effect=record_sleep):
            await sync_worker._run_sync("normal")

        self.assertIsNone(sync_worker._sync_state.error)
        self.assertEqual(sleep_calls, [5, 15])

    @respx.mock
    async def test_exhausted_retries_sets_error(self) -> None:
        respx.get(_COUNT_URL).mock(
            return_value=httpx.Response(200, json={"payload": {"count": 0}})
        )

        def always_fail(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        respx.get(_LISTENS_RE).mock(side_effect=always_fail)

        sleep_calls: list[float] = []

        async def record_sleep(secs: float) -> None:
            sleep_calls.append(secs)

        with mock.patch.dict(os.environ, {"LISTENBRAINZ_USERNAME": "testuser", "LISTENBRAINZ_TOKEN": "testtoken"}), \
             mock.patch("asyncio.to_thread", new_callable=mock.AsyncMock, side_effect=_to_thread_se), \
             mock.patch("asyncio.sleep", side_effect=record_sleep):
            await sync_worker._run_sync("normal")

        self.assertIsNotNone(sync_worker._sync_state.error)
        self.assertIn("unreachable after 5 attempts", sync_worker._sync_state.error)
        # 5 attempts → 4 sleeps (no sleep after the final attempt)
        self.assertEqual(sleep_calls, [5, 15, 30, 60])


class TestSyncResilienceMirror(unittest.IsolatedAsyncioTestCase):
    """429 behaviour in _run_mirror (mirror mode)."""

    async def asyncSetUp(self) -> None:
        _reset_sync_state()
        sync_worker._sync_state.running = True

    async def asyncTearDown(self) -> None:
        _reset_sync_state()

    @respx.mock
    async def test_429_halts_mirror_and_sets_error(self) -> None:
        respx.get(_COUNT_URL).mock(
            return_value=httpx.Response(200, json={"payload": {"count": 0}})
        )
        respx.get(_LISTENS_RE).mock(
            return_value=httpx.Response(429, headers={"X-RateLimit-Reset-In": "30"})
        )
        with mock.patch.dict(os.environ, {"LISTENBRAINZ_USERNAME": "testuser", "LISTENBRAINZ_TOKEN": "testtoken"}), \
             mock.patch("asyncio.to_thread", new_callable=mock.AsyncMock, return_value={}), \
             mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
            await sync_worker._run_mirror()

        self.assertIsNotNone(sync_worker._sync_state.error)
        self.assertIn("Rate-limited", sync_worker._sync_state.error)
        self.assertIn("30", sync_worker._sync_state.error)
        self.assertTrue(sync_worker._sync_state.finished)


if __name__ == "__main__":
    unittest.main()
