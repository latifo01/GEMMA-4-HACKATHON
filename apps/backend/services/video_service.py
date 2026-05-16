from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

import asyncio
from fastapi import UploadFile

from apps.backend.config import Settings
from apps.backend.schemas.video import VideoAnalysisData


ACCEPTED_VIDEO_CONTENT_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
}
READ_CHUNK_SIZE_BYTES = 1024 * 1024

VideoAnalyzer = Callable[[Path, int | None], VideoAnalysisData | dict[str, Any]]


class UnsupportedVideoTypeError(ValueError):
    pass


class VideoFileTooLargeError(ValueError):
    pass


class VideoAnalysisError(RuntimeError):
    pass


class LocalVideoService:
    def __init__(self, settings: Settings, analyzer: VideoAnalyzer | None = None) -> None:
        self.settings = settings
        self._analyzer = analyzer

    async def analyze_upload(self, file: UploadFile, age_months: int | None) -> VideoAnalysisData:
        self._validate_content_type(file.content_type)
        temp_path = await self._save_upload(file)

        try:
            result = await asyncio.to_thread(self._analyze_file, temp_path, age_months)
            return VideoAnalysisData.model_validate(result)
        except VideoAnalysisError:
            raise
        except Exception as exc:
            raise VideoAnalysisError("Video analysis failed.") from exc
        finally:
            temp_path.unlink(missing_ok=True)

    def _validate_content_type(self, content_type: str | None) -> None:
        if content_type not in ACCEPTED_VIDEO_CONTENT_TYPES:
            raise UnsupportedVideoTypeError(content_type or "missing")

    async def _save_upload(self, file: UploadFile) -> Path:
        self.settings.video_temp_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(file.filename or "").suffix or ".video"
        temp_path = self.settings.video_temp_dir / f"{uuid4().hex}{suffix}"
        bytes_written = 0

        try:
            with temp_path.open("wb") as output:
                while chunk := await file.read(READ_CHUNK_SIZE_BYTES):
                    bytes_written += len(chunk)
                    if bytes_written > self.settings.video_max_file_size_bytes:
                        raise VideoFileTooLargeError(str(bytes_written))
                    output.write(chunk)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise
        finally:
            await file.close()

        return temp_path

    def _analyze_file(self, file_path: Path, age_months: int | None) -> VideoAnalysisData | dict[str, Any]:
        if self._analyzer is not None:
            return self._analyzer(file_path, age_months)

        return self._estimate_respiration_from_video(file_path)

    def _estimate_respiration_from_video(self, file_path: Path) -> dict[str, Any]:
        import cv2
        import numpy as np

        capture = cv2.VideoCapture(str(file_path))
        if not capture.isOpened():
            return self._uncertain_result("unable_to_read_video", 0, 0.0)

        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        if fps <= 1.0:
            fps = 30.0

        signal: list[float] = []
        frames_analyzed = 0

        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break

                frames_analyzed += 1
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                height, width = gray.shape
                region = gray[int(height * 0.30) : int(height * 0.80), int(width * 0.20) : int(width * 0.80)]
                region = cv2.resize(region, (96, 96))
                region = cv2.GaussianBlur(region, (5, 5), 0)
                signal.append(float(np.mean(region)))
        finally:
            capture.release()

        duration_seconds = frames_analyzed / fps if fps else 0.0
        if frames_analyzed < 10 or len(signal) < 5:
            return self._uncertain_result("insufficient_frames", frames_analyzed, duration_seconds)
        if duration_seconds > self.settings.video_max_duration_seconds:
            return self._uncertain_result("video_too_long", frames_analyzed, duration_seconds)

        values = np.array(signal, dtype=float)
        if float(np.ptp(values)) < 0.5:
            return self._uncertain_result("insufficient_motion_signal", frames_analyzed, duration_seconds)

        centered = values - np.mean(values)
        frequencies = np.fft.rfftfreq(centered.size, d=1.0 / fps)
        spectrum = np.abs(np.fft.rfft(centered))
        breathing_band = (frequencies >= 0.25) & (frequencies <= 1.2)
        if not np.any(breathing_band):
            return self._uncertain_result("insufficient_motion_signal", frames_analyzed, duration_seconds)

        band_frequencies = frequencies[breathing_band]
        band_spectrum = spectrum[breathing_band]
        peak_index = int(np.argmax(band_spectrum))
        peak = float(band_spectrum[peak_index])
        total = float(np.sum(band_spectrum))
        if total <= 0:
            return self._uncertain_result("insufficient_motion_signal", frames_analyzed, duration_seconds)

        confidence = max(0.0, min(1.0, peak / total))
        respiratory_rate_bpm = float(band_frequencies[peak_index] * 60.0)
        if confidence < 0.15:
            return self._uncertain_result("low_confidence_motion_signal", frames_analyzed, duration_seconds)

        return {
            "respiratory_rate_bpm": round(respiratory_rate_bpm, 1),
            "confidence": round(confidence, 2),
            "frames_analyzed": frames_analyzed,
            "duration_seconds": round(duration_seconds, 2),
            "quality_flags": ["central_motion_signal", "sufficient_motion_signal"],
            "notes": "Respiratory rate is supportive evidence and requires clinical confirmation.",
        }

    def _uncertain_result(self, reason: str, frames_analyzed: int, duration_seconds: float) -> dict[str, Any]:
        return {
            "respiratory_rate_bpm": None,
            "confidence": 0.0,
            "frames_analyzed": frames_analyzed,
            "duration_seconds": round(duration_seconds, 2),
            "quality_flags": [reason],
            "notes": "Unable to estimate respiratory rate from this video.",
        }
