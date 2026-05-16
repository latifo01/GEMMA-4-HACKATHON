import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from apps.backend.config import Settings, get_settings
from apps.backend.database import build_sqlite_url, create_database, get_sessionmaker
from apps.backend.main import create_app
from apps.backend.routers.triage import get_agent_pipeline
from apps.backend.services.session_service import get_session, serialize_session


class FakePipeline:
    def __init__(self) -> None:
        self.last_request = None

    async def run(self, request):
        self.last_request = request
        return {
            "triage_color": "YELLOW",
            "classification": "PNEUMONIA",
            "human_review_required": True,
            "extracted_symptoms": {"cough": True},
            "missing_information": [],
            "tool_results": [{"tool_name": "classify_pneumonia"}],
            "reasoning": "Grounded reasoning.",
            "recommendations": ["Treat according to local IMCI protocol."],
            "translated_output": "PNEUMONIA: translated output.",
            "safety_flags": [],
            "citations": [
                {
                    "source": "imci-chart-booklet.pdf",
                    "page": 6,
                    "chunk_id": "c1",
                    "relevance_score": 0.9,
                    "quote": "Cough or difficult breathing.",
                }
            ],
            "model": {"mode": "online", "name": "fake-gemma"},
            "errors": [],
        }


class FailingPipeline:
    async def run(self, request):
        raise RuntimeError("pipeline failed")


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        GOOGLE_AI_API_KEY=None,
        GEMMA_ONLINE_MODEL="test-online-model",
        OLLAMA_BASE_URL="http://localhost:11434",
        GEMMA_OFFLINE_MODEL="test-offline-model",
        OLLAMA_HEALTH_TIMEOUT_SECONDS=0.01,
        CHROMA_PATH=tmp_path / "chroma",
        DB_PATH=tmp_path / "imciflow.db",
        RAG_TEXT_EMBEDDING_PROVIDER="lexical",
        RAG_IMAGE_EMBEDDING_PROVIDER="lexical",
    )


def make_app(settings: Settings, pipeline):
    asyncio.run(create_database(settings))
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_agent_pipeline] = lambda: pipeline
    return app


def test_triage_api_returns_complete_result_and_persists_session(tmp_path):
    settings = make_settings(tmp_path)
    pipeline = FakePipeline()
    app = make_app(settings, pipeline)

    with TestClient(app) as client:
        response = client.post(
            "/triage/run",
            json={
                "transcript": "The child has cough and fast breathing.",
                "source_language": "en",
                "target_language": "fr",
                "model_mode": "offline",
                "patient": {"age_months": 18},
                "measurements": {"respiratory_rate_bpm": 52},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    session_id = payload["data"]["session_id"]
    assert payload["data"]["classification"] == "PNEUMONIA"
    assert payload["data"]["triage_color"] == "YELLOW"
    assert payload["data"]["human_review_required"] is True
    assert payload["data"]["citations"]
    assert payload["meta"]["model_mode"] == "online"
    assert payload["meta"]["request_id"]
    assert pipeline.last_request.model_mode == "offline"

    sessionmaker = get_sessionmaker(build_sqlite_url(settings.db_path))

    async def load_session():
        async with sessionmaker() as db_session:
            return serialize_session(await get_session(db_session, session_id))

    audit_record = asyncio.run(load_session())
    assert audit_record["status"] == "completed"
    assert audit_record["request"]["transcript"] == "The child has cough and fast breathing."
    assert audit_record["request"]["model_mode"] == "offline"
    assert audit_record["result"]["classification"] == "PNEUMONIA"


def test_triage_api_rejects_invalid_target_language(tmp_path):
    settings = make_settings(tmp_path)
    app = make_app(settings, FakePipeline())

    with TestClient(app) as client:
        response = client.post(
            "/triage/run",
            json={
                "transcript": "The child has cough.",
                "target_language": "es",
            },
        )

    assert response.status_code == 422


def test_triage_api_rejects_invalid_model_mode(tmp_path):
    settings = make_settings(tmp_path)
    app = make_app(settings, FakePipeline())

    with TestClient(app) as client:
        response = client.post(
            "/triage/run",
            json={
                "transcript": "The child has cough.",
                "model_mode": "edge",
            },
        )

    assert response.status_code == 422


def test_triage_api_persists_failed_session(tmp_path):
    settings = make_settings(tmp_path)
    app = make_app(settings, FailingPipeline())

    with TestClient(app) as client:
        response = client.post(
            "/triage/run",
            json={
                "transcript": "The child has cough.",
                "target_language": "en",
            },
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "TRIAGE_VERIFICATION_FAILED"
    assert payload["error"]["details"]["session_id"]

    sessionmaker = get_sessionmaker(build_sqlite_url(settings.db_path))

    async def load_session():
        async with sessionmaker() as db_session:
            return serialize_session(await get_session(db_session, payload["error"]["details"]["session_id"]))

    audit_record = asyncio.run(load_session())
    assert audit_record["status"] == "failed"
    assert audit_record["errors"][0]["code"] == "TRIAGE_VERIFICATION_FAILED"
