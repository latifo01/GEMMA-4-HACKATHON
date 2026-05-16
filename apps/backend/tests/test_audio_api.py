from pathlib import Path

from fastapi.testclient import TestClient

from apps.backend.config import Settings, get_settings
from apps.backend.main import create_app
from apps.backend.routers.audio import get_whisper_service
from apps.backend.services.whisper_service import LocalWhisperService


class FakeTranscriber:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, str]] = []
        self.path_existed_during_call = False

    def __call__(self, file_path: Path, source_language: str) -> dict:
        self.calls.append((file_path, source_language))
        self.path_existed_during_call = file_path.exists()
        return {
            "transcript": "Bonjour, l'enfant tousse.",
            "detected_language": source_language,
            "duration_seconds": 1.25,
            "segments": [
                {
                    "start_seconds": 0.0,
                    "end_seconds": 1.25,
                    "text": "Bonjour, l'enfant tousse.",
                }
            ],
        }


def make_settings(tmp_path: Path, max_size: int = 25 * 1024 * 1024) -> Settings:
    return Settings(
        GOOGLE_AI_API_KEY=None,
        GEMMA_ONLINE_MODEL="test-online-model",
        OLLAMA_BASE_URL="http://localhost:11434",
        GEMMA_OFFLINE_MODEL="test-offline-model",
        OLLAMA_HEALTH_TIMEOUT_SECONDS=0.01,
        CHROMA_PATH=tmp_path / "chroma",
        DB_PATH=tmp_path / "imciflow.db",
        WHISPER_MODEL_NAME="test-whisper",
        AUDIO_TEMP_DIR=tmp_path / "audio_tmp",
        AUDIO_MAX_FILE_SIZE_BYTES=max_size,
    )


def make_app(settings: Settings, transcriber: FakeTranscriber):
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_whisper_service] = lambda: LocalWhisperService(settings, transcriber)
    return app


def audio_files(content: bytes, content_type: str = "audio/wav"):
    return {"file": ("sample.wav", content, content_type)}


def assert_temp_dir_empty(path: Path) -> None:
    if path.exists():
        assert list(path.iterdir()) == []


def test_audio_transcribe_returns_transcript_and_deletes_temp_file(tmp_path):
    settings = make_settings(tmp_path)
    transcriber = FakeTranscriber()
    app = make_app(settings, transcriber)

    with TestClient(app) as client:
        response = client.post(
            "/audio/transcribe",
            data={"source_language": "fr"},
            files=audio_files(b"fake wav bytes"),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["transcript"] == "Bonjour, l'enfant tousse."
    assert payload["data"]["detected_language"] == "fr"
    assert payload["data"]["duration_seconds"] == 1.25
    assert payload["data"]["segments"][0]["start_seconds"] == 0.0
    assert payload["meta"]["model_mode"] == "offline"
    assert payload["meta"]["request_id"]
    assert transcriber.calls
    assert transcriber.path_existed_during_call is True
    assert_temp_dir_empty(settings.audio_temp_dir)


def test_audio_transcribe_rejects_unsupported_file_type(tmp_path):
    settings = make_settings(tmp_path)
    transcriber = FakeTranscriber()
    app = make_app(settings, transcriber)

    with TestClient(app) as client:
        response = client.post(
            "/audio/transcribe",
            files=audio_files(b"not audio", content_type="text/plain"),
        )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["details"]["reason"] == "unsupported_audio_type"
    assert transcriber.calls == []
    assert_temp_dir_empty(settings.audio_temp_dir)


def test_audio_transcribe_rejects_oversized_file(tmp_path):
    settings = make_settings(tmp_path, max_size=4)
    transcriber = FakeTranscriber()
    app = make_app(settings, transcriber)

    with TestClient(app) as client:
        response = client.post(
            "/audio/transcribe",
            files=audio_files(b"12345"),
        )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["details"]["reason"] == "audio_file_too_large"
    assert transcriber.calls == []
    assert_temp_dir_empty(settings.audio_temp_dir)
