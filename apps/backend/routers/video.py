from time import perf_counter
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import JSONResponse

from apps.backend.config import Settings, get_settings
from apps.backend.services.video_service import (
    LocalVideoService,
    UnsupportedVideoTypeError,
    VideoAnalysisError,
    VideoFileTooLargeError,
)


router = APIRouter(prefix="/video", tags=["video"])


def get_video_service(settings: Settings = Depends(get_settings)) -> LocalVideoService:
    return LocalVideoService(settings)


@router.post("/analyze", response_model=None)
async def analyze_video(
    file: Annotated[UploadFile, File(...)],
    age_months: Annotated[int | None, Form()] = None,
    service: LocalVideoService = Depends(get_video_service),
) -> dict[str, Any] | JSONResponse:
    started_at = perf_counter()
    request_id = str(uuid4())

    try:
        result = await service.analyze_upload(file, age_months)
    except UnsupportedVideoTypeError as exc:
        return _error_response(
            request_id=request_id,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="Unsupported video content type.",
            details={"reason": "unsupported_video_type", "content_type": str(exc)},
            started_at=started_at,
        )
    except VideoFileTooLargeError:
        return _error_response(
            request_id=request_id,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="Video file exceeds the maximum allowed size.",
            details={"reason": "video_file_too_large"},
            started_at=started_at,
        )
    except VideoAnalysisError as exc:
        return _error_response(
            request_id=request_id,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="VIDEO_ANALYSIS_FAILED",
            message="Video analysis failed.",
            details={"error_type": type(exc).__name__},
            started_at=started_at,
        )

    duration_ms = round((perf_counter() - started_at) * 1000)
    return {
        "data": result.model_dump(mode="json"),
        "meta": {
            "request_id": request_id,
            "model_mode": "offline",
            "duration_ms": duration_ms,
        },
    }


def _error_response(
    request_id: str,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any],
    started_at: float,
) -> JSONResponse:
    duration_ms = round((perf_counter() - started_at) * 1000)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
            "meta": {
                "request_id": request_id,
                "duration_ms": duration_ms,
            },
        },
    )
