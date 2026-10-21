import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services import can_service

router = APIRouter(prefix="/sse", tags=["sse"])


@router.get("/can-stream")
async def can_stream() -> StreamingResponse:
    async def event_generator():
        async for frame in can_service.subscribe_sse():
            data = frame.model_dump_json()
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
