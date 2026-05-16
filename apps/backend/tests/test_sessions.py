import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.backend.config import Settings, get_settings
from apps.backend.database import build_sqlite_url, create_database, get_sessionmaker
from apps.backend.main import create_app
from apps.backend.services.session_service import (
    SessionNotFoundError,
    create_session,
    get_session,
    serialize_session,
    update_session,
)


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        GOOGLE_AI_API_KEY=None,
        GEMMA_ONLINE_MODEL="test-online-model",
        OLLAMA_BASE_URL="http://localhost:11434",
        GEMMA_OFFLINE_MODEL="test-offline-model",
        OLLAMA_HEALTH_TIMEOUT_SECONDS=0.01,
        CHROMA_PATH=tmp_path / "chroma",
        DB_PATH=tmp_path / "imciflow.db",
    )


async def seed_database(settings: Settings) -> str:
    await create_database(settings)
    sessionmaker = get_sessionmaker(build_sqlite_url(settings.db_path))

    async with sessionmaker() as db_session:
        audit_session = await create_session(
            db_session=db_session,
            request_payload={"transcript": "Child has cough and fast breathing."},
            model_mode="online",
        )
        return audit_session.session_id


@pytest.mark.asyncio
async def test_create_update_and_retrieve_session(tmp_path):
    settings = make_settings(tmp_path)
    await create_database(settings)
    sessionmaker = get_sessionmaker(build_sqlite_url(settings.db_path))

    async with sessionmaker() as db_session:
        created = await create_session(
            db_session=db_session,
            request_payload={"transcript": "Child has cough."},
            model_mode="online",
        )

        assert created.status == "running"
        assert created.request_json == {"transcript": "Child has cough."}
        assert created.result_json is None
        assert created.errors_json == []

        updated = await update_session(
            db_session=db_session,
            session_id=created.session_id,
            status="completed",
            result_payload={"triage_color": "YELLOW"},
            errors=[],
            model_mode="offline",
        )

        loaded = await get_session(db_session, created.session_id)
        serialized = serialize_session(loaded)

    assert updated.status == "completed"
    assert serialized["session_id"] == created.session_id
    assert serialized["status"] == "completed"
    assert serialized["model_mode"] == "offline"
    assert serialized["request"] == {"transcript": "Child has cough."}
    assert serialized["result"] == {"triage_color": "YELLOW"}
    assert serialized["errors"] == []
    assert serialized["created_at"]
    assert serialized["updated_at"]


@pytest.mark.asyncio
async def test_get_session_raises_for_missing_session(tmp_path):
    settings = make_settings(tmp_path)
    await create_database(settings)
    sessionmaker = get_sessionmaker(build_sqlite_url(settings.db_path))

    async with sessionmaker() as db_session:
        with pytest.raises(SessionNotFoundError):
            await get_session(db_session, "missing-session-id")


def test_session_api_returns_record(tmp_path):
    settings = make_settings(tmp_path)
    session_id = asyncio.run(seed_database(settings))
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as client:
        response = client.get(f"/sessions/{session_id}")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["session_id"] == session_id
    assert payload["data"]["status"] == "running"
    assert payload["data"]["request"] == {"transcript": "Child has cough and fast breathing."}
    assert payload["data"]["result"] is None
    assert payload["data"]["errors"] == []
    assert payload["meta"]["model_mode"] == "online"
    assert payload["meta"]["request_id"]


def test_session_api_returns_404_for_missing_session(tmp_path):
    settings = make_settings(tmp_path)
    asyncio.run(create_database(settings))
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as client:
        response = client.get("/sessions/missing-session-id")

    app.dependency_overrides.clear()

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "SESSION_NOT_FOUND"
    assert payload["error"]["details"]["session_id"] == "missing-session-id"
    assert payload["meta"]["request_id"]

