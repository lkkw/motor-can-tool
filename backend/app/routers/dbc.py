from fastapi import APIRouter, HTTPException, UploadFile

from app.schemas.dbc import DbcParseResponse
from app.services import dbc_service

router = APIRouter(prefix="/dbc", tags=["dbc"])


@router.post("/upload", response_model=DbcParseResponse)
async def upload_dbc(file: UploadFile) -> DbcParseResponse:
    if not file.filename or not file.filename.endswith(".dbc"):
        raise HTTPException(status_code=400, detail="Please upload a valid .dbc file")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    try:
        return dbc_service.parse_dbc(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse DBC: {e}") from e


@router.get("/messages", response_model=DbcParseResponse | None)
async def get_messages() -> DbcParseResponse | None:
    return dbc_service.get_current_response()
