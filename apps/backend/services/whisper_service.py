from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

import asyncio
from fastapi import UploadFile

from apps.backend.config import Settings
from apps.backend.schemas.audio import AudioTranscriptionData, LanguageCode


ACCEPTED_AUDIO_CONTENT_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/mpeg",
    "audio/mp4",
}
READ_CHUNK_SIZE_BYTES = 1024 * 1024

Transcriber = Callable[[Path, LanguageCode], AudioTranscriptionData | dict[str, Any]]


class UnsupportedAudioTypeError(ValueError):
    pass


class AudioFileTooLargeError(ValueError):
    pass


class AudioTranscriptionError(RuntimeError):
    pass


class LocalWhisperService:
    def __init__(self, settings: Settings, transcriber: Transcriber | None = None) -> None:
        self.settings = settings
        self._transcriber = transcriber
        self._model: Any | None = None

    async def transcribe_upload(
        self,
        file: UploadFile,
        source_language: LanguageCode,
    ) -> AudioTranscriptionData:
        self._validate_content_type(file.content_type)
        temp_path = await self._save_upload(file)

        try:
            result = await asyncio.to_thread(self._transcribe_file, temp_path, source_language)
            return AudioTranscriptionData.model_validate(result)
        except AudioTranscriptionError:
            raise
        except Exception as exc:
            raise AudioTranscriptionError("Audio transcription failed.") from exc
        finally:
            temp_path.unlink(missing_ok=True)

    def _validate_content_type(self, content_type: str | None) -> None:
        if content_type not in ACCEPTED_AUDIO_CONTENT_TYPES:
            raise UnsupportedAudioTypeError(content_type or "missing")

    async def _save_upload(self, file: UploadFile) -> Path:
        self.settings.audio_temp_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(file.filename or "").suffix or ".audio"
        temp_path = self.settings.audio_temp_dir / f"{uuid4().hex}{suffix}"
        bytes_written = 0

        try:
            with temp_path.open("wb") as output:
                while chunk := await file.read(READ_CHUNK_SIZE_BYTES):
                    bytes_written += len(chunk)
                    if bytes_written > self.settings.audio_max_file_size_bytes:
                        raise AudioFileTooLargeError(str(bytes_written))
                    output.write(chunk)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise
        finally:
            await file.close()

        return temp_path

    def _transcribe_file(self, file_path: Path, source_language: LanguageCode) -> AudioTranscriptionData | dict[str, Any]:
        if self._transcriber is not None:
            return self._transcriber(file_path, source_language)

        model = self._get_model()
        whisper_language = self._to_whisper_language(source_language)
        options: dict[str, Any] = {"vad_filter": True}
        if whisper_language is not None:
            options["language"] = whisper_language

        segments_iterable, info = model.transcribe(str(file_path), **options)
        segments = [
            {
                "start_seconds": float(segment.start),
                "end_seconds": float(segment.end),
                "text": segment.text.strip(),
            }
            for segment in segments_iterable
        ]
        transcript = " ".join(segment["text"] for segment in segments if segment["text"]).strip()

        return {
            "transcript": transcript,
            "detected_language": getattr(info, "language", None) or whisper_language or "auto",
            "duration_seconds": float(getattr(info, "duration", 0.0) or 0.0),
            "segments": segments,
        }

    def _get_model(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.settings.whisper_model_name,
                device=self.settings.whisper_device,
                compute_type=self.settings.whisper_compute_type,
            )

        return self._model

    def _to_whisper_language(self, source_language: LanguageCode) -> str | None:
        if source_language == "auto":
            return None
        if source_language == "ar-SD":
            return "ar"
        return source_language
