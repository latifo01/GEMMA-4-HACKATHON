from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.database import get_db_session
from apps.backend.services.session_service import (
    SessionNotFoundError,
    get_session,
    serialize_session,
)


router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/{session_id}", response_model=None)
async def read_session(
    session_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any] | JSONResponse:
    started_at = perf_counter()
    request_id = str(uuid4())

    try:
        audit_session = await get_session(db_session, session_id)
    except SessionNotFoundError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": "Requested session does not exist.",
                    "details": {"session_id": session_id},
                },
                "meta": {"request_id": request_id},
            },
        )

    duration_ms = round((perf_counter() - started_at) * 1000)
    data = serialize_session(audit_session)

    return {
        "data": data,
        "meta": {
            "request_id": request_id,
            "model_mode": data["model_mode"] or "unavailable",
            "duration_ms": duration_ms,
        },
    }
