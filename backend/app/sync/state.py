import asyncio
from dataclasses import dataclass
from typing import Optional


@dataclass
class SyncState:
    running: bool = False
    mode: str = ""
    batches_fetched: int = 0
    synced_count: int = 0
    updated_count: int = 0
    deleted_count: int = 0
    lb_total: int = 0
    local_total: int = 0
    error: Optional[str] = None
    finished: bool = False


_sync_state = SyncState()
_sync_lock = asyncio.Lock()
