import asyncio
import json
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 15


class PlayingNowBroadcaster:
    """Server-side poll loop that pushes playing-now state to all SSE clients."""

    def __init__(self) -> None:
        self._last: dict | None = None
        self._queues: list[asyncio.Queue[dict]] = []
        self._task: asyncio.Task | None = None
        self._fetch: Callable[[], Awaitable[dict]] | None = None

    def start(self, fetch: Callable[[], Awaitable[dict]]) -> None:
        """Start the background poll loop. fetch() must return a JSON-serialisable dict."""
        self._fetch = fetch
        self._task = asyncio.get_event_loop().create_task(self._poll_loop())

    async def _poll_loop(self) -> None:
        while True:
            if self._fetch is not None:
                try:
                    data = await self._fetch()
                    self._last = data
                    for q in list(self._queues):
                        try:
                            q.put_nowait(data)
                        except asyncio.QueueFull:
                            pass
                    logger.debug(
                        "playing-now broadcast to %d SSE client(s)", len(self._queues)
                    )
                except Exception:
                    logger.exception("playing-now poll error")
            await asyncio.sleep(_POLL_INTERVAL)

    async def subscribe(self) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted lines. Cleans up on client disconnect (CancelledError)."""
        q: asyncio.Queue[dict] = asyncio.Queue(maxsize=5)
        self._queues.append(q)
        logger.debug("SSE client connected; total=%d", len(self._queues))
        try:
            # Send cached state immediately so the client doesn't wait up to 15s.
            if self._last is not None:
                yield f"data: {json.dumps(self._last)}\n\n"
            while True:
                data = await q.get()
                yield f"data: {json.dumps(data)}\n\n"
        finally:
            try:
                self._queues.remove(q)
            except ValueError:
                pass
            logger.debug("SSE client disconnected; total=%d", len(self._queues))


broadcaster = PlayingNowBroadcaster()
