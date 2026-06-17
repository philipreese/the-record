"""Shared httpx.AsyncClient for all ListenBrainz API calls.

A single persistent client with connection pooling avoids opening a new
TCP+TLS connection to api.listenbrainz.org on every request. Without this,
concurrent callers (sync + playing-now poll) each open their own connection
and can hit LB's per-IP connection limit, causing ConnectTimeout.
"""
import httpx

_client: httpx.AsyncClient | None = None


def get_lb_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=15.0, read=15.0, write=10.0, pool=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
    return _client


async def close_lb_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None
