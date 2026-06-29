import hmac
import os
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, WebSocket, WebSocketDisconnect

import app.sync as sync_worker
from app.schemas import SyncStartResponse, SyncStatusResponse
from app.ws import manager as ws_manager

router = APIRouter()


@router.post("/sync", response_model=SyncStartResponse)
async def start_sync(
    background_tasks: BackgroundTasks,
    mode: Literal["normal", "mirror"] = Query("normal"),
    x_sync_token: Optional[str] = Header(None),
) -> SyncStartResponse:
    """Kick off a background sync with ListenBrainz and return immediately."""
    sync_token = os.getenv("SYNC_TOKEN")
    if not sync_token:
        raise HTTPException(status_code=503, detail="Sync endpoint is not configured.")
    if not x_sync_token or not hmac.compare_digest(x_sync_token, sync_token):
        raise HTTPException(status_code=401, detail="Invalid or missing X-Sync-Token.")

    async with sync_worker._sync_lock:
        if sync_worker._sync_state.running:
            return SyncStartResponse(
                status="already_running",
                message="A sync is already in progress. Poll /api/sync/status for updates.",
            )
        s = sync_worker._sync_state
        s.running = True
        s.mode = mode
        s.batches_fetched = 0
        s.synced_count = 0
        s.updated_count = 0
        s.deleted_count = 0
        s.lb_total = 0
        s.local_total = 0
        s.error = None
        s.finished = False

    if mode == "mirror":
        background_tasks.add_task(sync_worker._run_mirror)
    else:
        background_tasks.add_task(sync_worker._run_sync, mode)
    return SyncStartResponse(status="started", mode=mode)


@router.get("/sync/status", response_model=SyncStatusResponse)
def get_sync_status() -> SyncStatusResponse:
    """Return the current state of the background sync job."""
    s = sync_worker._sync_state
    return SyncStatusResponse(
        running=s.running,
        finished=s.finished,
        mode=s.mode,
        batches_fetched=s.batches_fetched,
        synced_count=s.synced_count,
        updated_count=s.updated_count,
        deleted_count=s.deleted_count,
        lb_total=s.lb_total,
        local_total=s.local_total,
        error=s.error,
    )


@router.websocket("/ws/sync")
async def sync_ws(websocket: WebSocket) -> None:
    """WebSocket endpoint that pushes sync lifecycle events to connected clients."""
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
