from fastapi import APIRouter, HTTPException

from app.schemas.can import (
    CanConnectRequest,
    CanSendRequest,
    CanStatusResponse,
    PeriodicTaskInfo,
)
from app.services import can_service

router = APIRouter(prefix="/can", tags=["can"])


@router.post("/connect", response_model=CanStatusResponse)
async def connect(cfg: CanConnectRequest) -> CanStatusResponse:
    try:
        can_service.connect(cfg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection failed: {e}") from e
    return can_service.get_status()


@router.post("/disconnect", response_model=CanStatusResponse)
async def disconnect() -> CanStatusResponse:
    can_service.disconnect()
    return can_service.get_status()


@router.get("/status", response_model=CanStatusResponse)
async def status() -> CanStatusResponse:
    return can_service.get_status()


@router.post("/send")
async def send_frame(req: CanSendRequest) -> dict:
    try:
        if req.interval_ms > 0:
            task_id = can_service.start_periodic(
                req.message_id, req.is_extended_id, req.signals, req.interval_ms
            )
            return {"status": "periodic_started", "task_id": task_id}
        else:
            can_service.send_once(req.message_id, req.is_extended_id, req.signals)
            return {"status": "sent"}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Send failed: {e}") from e


@router.delete("/periodic/{task_id}")
async def stop_periodic(task_id: str) -> dict:
    ok = can_service.stop_periodic(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "stopped", "task_id": task_id}


@router.get("/periodic", response_model=list[PeriodicTaskInfo])
async def list_periodic() -> list[PeriodicTaskInfo]:
    return can_service.list_periodic_tasks()
