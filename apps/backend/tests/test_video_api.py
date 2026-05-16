import asyncio
from pathlib import Path
from io import BytesIO

from fastapi.testclient import TestClient
from starlette.datastructures import Headers, UploadFile

from apps.backend.config import Settings, get_settings
from apps.backend.main import create_app
from apps.backend.routers.video import get_video_service
from apps.backend.services.video_service import LocalVideoService


class FakeAnalyzer:
    def __init__(self, low_quality: bool = False) -> None:
        self.low_quality = low_quality
        self.calls: list[tuple[Path, int | None]] = []
        self.path_existed_during_call = False

    def __call__(self, file_path: Path, age_months: int | None) -> dict:
        self.calls.append((file_path, age_months))
        self.path_existed_during_call = file_path.exists()
        if self.low_quality:
            return {
                "respiratory_rate_bpm": None,
                "confidence": 0.0,
                "frames_analyzed": 2,
                "duration_seconds": 0.2,
                "quality_flags": ["insufficient_motion_signal"],
                "notes": "Unable to estimate respiratory rate from this video.",
            }

        return {
            "respiratory_rate_bpm": 52.0,
            "confidence": 0.72,
            "frames_analyzed": 450,
            "duration_seconds": 20.0,
            "quality_flags": ["stable_camera", "sufficient_motion_signal"],
            "notes": "Respiratory rate is supportive evidence and requires clinical confirmation.",
        }


def make_settings(tmp_path: Path, max_size: int = 80 * 1024 * 1024) -> Settings:
    return Settings(
        GOOGLE_AI_API_KEY=None,
        GEMMA_ONLINE_MODEL="test-online-model",
        OLLAMA_BASE_URL="http://localhost:11434",
        GEMMA_OFFLINE_MODEL="test-offline-model",
        OLLAMA_HEALTH_TIMEOUT_SECONDS=0.01,
        CHROMA_PATH=tmp_path / "chroma",
        DB_PATH=tmp_path / "imciflow.db",
        VIDEO_TEMP_DIR=tmp_path / "video_tmp",
        VIDEO_MAX_FILE_SIZE_BYTES=max_size,
    )


def make_app(settings: Settings, analyzer: FakeAnalyzer):
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_video_service] = lambda: LocalVideoService(settings, analyzer)
    return app


def video_files(content: bytes, content_type: str = "video/mp4"):
    return {"file": ("sample.mp4", content, content_type)}


def assert_temp_dir_empty(path: Path) -> None:
    if path.exists():
        assert list(path.iterdir()) == []


def write_controlled_respiration_video(path: Path, respiratory_rate_bpm: float = 48.0) -> None:
    import cv2
    import numpy as np

    fps = 20.0
    duration_seconds = 10.0
    frame_size = (160, 120)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, frame_size)

    for frame_index in range(int(fps * duration_seconds)):
        elapsed_seconds = frame_index / fps
        phase = 2 * np.pi * (respiratory_rate_bpm / 60.0) * elapsed_seconds
        intensity = int(120 + 60 * np.sin(phase))
        frame = np.full((frame_size[1], frame_size[0], 3), 70, dtype=np.uint8)
        frame[36:96, 40:120] = intensity
        writer.write(frame)

    writer.release()


def test_video_analyze_returns_respiratory_support_data_and_deletes_temp_file(tmp_path):
    settings = make_settings(tmp_path)
    analyzer = FakeAnalyzer()
    app = make_app(settings, analyzer)

    with TestClient(app) as client:
        response = client.post(
            "/video/analyze",
            data={"age_months": "18"},
            files=video_files(b"fake mp4 bytes"),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["respiratory_rate_bpm"] == 52.0
    assert payload["data"]["confidence"] == 0.72
    assert payload["data"]["frames_analyzed"] == 450
    assert "supportive evidence" in payload["data"]["notes"]
    assert payload["meta"]["model_mode"] == "offline"
    assert payload["meta"]["request_id"]
    assert analyzer.calls[0][1] == 18
    assert analyzer.path_existed_during_call is True
    assert_temp_dir_empty(settings.video_temp_dir)


def test_video_service_estimates_respiratory_rate_from_controlled_fixture(tmp_path):
    settings = make_settings(tmp_path)
    source_path = tmp_path / "controlled.avi"
    write_controlled_respiration_video(source_path, respiratory_rate_bpm=48.0)
    upload = UploadFile(
        file=BytesIO(source_path.read_bytes()),
        filename="controlled.avi",
        headers=Headers({"content-type": "video/mp4"}),
    )

    data = asyncio.run(LocalVideoService(settings).analyze_upload(upload, age_months=18))

    assert data.respiratory_rate_bpm is not None
    assert abs(data.respiratory_rate_bpm - 48.0) <= 6.0
    assert data.confidence > 0.3
    assert "sufficient_motion_signal" in data.quality_flags
    assert_temp_dir_empty(settings.video_temp_dir)


def test_video_analyze_rejects_unsupported_file_type(tmp_path):
    settings = make_settings(tmp_path)
    analyzer = FakeAnalyzer()
    app = make_app(settings, analyzer)

    with TestClient(app) as client:
        response = client.post(
            "/video/analyze",
            files=video_files(b"not video", content_type="text/plain"),
        )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["details"]["reason"] == "unsupported_video_type"
    assert analyzer.calls == []
    assert_temp_dir_empty(settings.video_temp_dir)


def test_video_analyze_rejects_oversized_file(tmp_path):
    settings = make_settings(tmp_path, max_size=4)
    analyzer = FakeAnalyzer()
    app = make_app(settings, analyzer)

    with TestClient(app) as client:
        response = client.post(
            "/video/analyze",
            files=video_files(b"12345"),
        )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["details"]["reason"] == "video_file_too_large"
    assert analyzer.calls == []
    assert_temp_dir_empty(settings.video_temp_dir)


def test_video_analyze_returns_uncertainty_for_low_quality_video(tmp_path):
    settings = make_settings(tmp_path)
    analyzer = FakeAnalyzer(low_quality=True)
    app = make_app(settings, analyzer)

    with TestClient(app) as client:
        response = client.post(
            "/video/analyze",
            files=video_files(b"low quality bytes"),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["respiratory_rate_bpm"] is None
    assert payload["data"]["confidence"] == 0.0
    assert "insufficient_motion_signal" in payload["data"]["quality_flags"]
    assert "Unable to estimate" in payload["data"]["notes"]
    assert_temp_dir_empty(settings.video_temp_dir)
