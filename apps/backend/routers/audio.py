from time import perf_counter
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import JSONResponse

from apps.backend.config import Settings, get_settings
from apps.backend.schemas.audio import LanguageCode
from apps.backend.services.whisper_service import (
    AudioFileTooLargeError,
    AudioTranscriptionError,
    LocalWhisperService,
    UnsupportedAudioTypeError,
)


router = APIRouter(prefix="/audio", tags=["audio"])


def get_whisper_service(settings: Settings = Depends(get_settings)) -> LocalWhisperService:
    return LocalWhisperService(settings)


@router.post("/transcribe", response_model=None)
async def transcribe_audio(
    file: Annotated[UploadFile, File(...)],
    source_language: Annotated[LanguageCode, Form()] = "auto",
    service: LocalWhisperService = Depends(get_whisper_service),
) -> dict[str, Any] | JSONResponse:
    started_at = perf_counter()
    request_id = str(uuid4())

    try:
        result = await service.transcribe_upload(file, source_language)
    except UnsupportedAudioTypeError as exc:
        return _error_response(
            request_id=request_id,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="Unsupported audio content type.",
            details={"reason": "unsupported_audio_type", "content_type": str(exc)},
            started_at=started_at,
        )
    except AudioFileTooLargeError:
        return _error_response(
            request_id=request_id,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="Audio file exceeds the maximum allowed size.",
            details={"reason": "audio_file_too_large"},
            started_at=started_at,
        )
    except AudioTranscriptionError as exc:
        return _error_response(
            request_id=request_id,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="TRANSCRIPTION_FAILED",
            message="Audio transcription failed.",
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
