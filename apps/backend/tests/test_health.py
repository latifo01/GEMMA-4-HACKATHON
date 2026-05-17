from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

import apps.backend.routers.health as health_router
from apps.backend.config import Settings, get_settings
from apps.backend.main import create_app


@contextmanager
def health_client(settings: Settings) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def make_settings(tmp_path: Path, google_ai_api_key: str | None = None) -> Settings:
    return Settings(
        GOOGLE_AI_API_KEY=google_ai_api_key,
        GEMMA_ONLINE_MODEL="test-online-model",
        OLLAMA_BASE_URL="http://localhost:11434",
        GEMMA_OFFLINE_MODEL="test-offline-model",
        OLLAMA_HEALTH_TIMEOUT_SECONDS=0.01,
        CHROMA_PATH=tmp_path / "chroma",
        DB_PATH=tmp_path / "imciflow.db",
    )


def patch_ollama(monkeypatch, available: bool) -> None:
    async def fake_check_ollama_available(settings: Settings) -> bool:
        return available

    monkeypatch.setattr(health_router, "check_ollama_available", fake_check_ollama_available)


def test_health_selects_online_model_when_api_key_exists(monkeypatch, tmp_path):
    settings = make_settings(tmp_path, google_ai_api_key="test-secret")
    settings.chroma_path.mkdir()
    (settings.chroma_path / "chroma.sqlite3").write_text("", encoding="utf-8")
    patch_ollama(monkeypatch, available=False)

    with health_client(settings) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["online_model_available"] is True
    assert payload["data"]["offline_model_available"] is False
    assert payload["data"]["selected_model_mode"] == "online"
    assert payload["data"]["selected_model_name"] == "test-online-model"
    assert payload["data"]["rag_index_available"] is True
    assert payload["data"]["database_available"] is True
    assert payload["meta"]["model_mode"] == "online"
    assert payload["meta"]["request_id"]


def test_health_selects_offline_model_when_online_missing(monkeypatch, tmp_path):
    settings = make_settings(tmp_path)
    patch_ollama(monkeypatch, available=True)

    with health_client(settings) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["online_model_available"] is False
    assert payload["data"]["offline_model_available"] is True
    assert payload["data"]["selected_model_mode"] == "offline"
    assert payload["data"]["selected_model_name"] == "test-offline-model"
    assert payload["meta"]["model_mode"] == "offline"


def test_health_reports_unavailable_without_crashing(monkeypatch, tmp_path):
    settings = make_settings(tmp_path)
    patch_ollama(monkeypatch, available=False)

    with health_client(settings) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["selected_model_mode"] == "unavailable"
    assert payload["data"]["selected_model_name"] is None
    assert payload["meta"]["model_mode"] == "unavailable"


def test_settings_normalizes_placeholder_api_key(tmp_path):
    settings = make_settings(tmp_path, google_ai_api_key="your_google_ai_key_here")

    assert settings.google_ai_api_key is None


def test_health_reports_embedded_evidence_when_chroma_directory_is_empty(monkeypatch, tmp_path):
    settings = make_settings(tmp_path)
    settings.chroma_path.mkdir()
    patch_ollama(monkeypatch, available=False)

    with health_client(settings) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["rag_index_available"] is True
