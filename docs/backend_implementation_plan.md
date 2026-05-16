# Backend Implementation Plan

## Objective

Implement the backend in incremental phases. Each phase has explicit files, dependencies,
commands, tests, validation criteria, and success criteria.

## Phase 0: Repository Hygiene

Objective:

- Ensure backend work starts from a clean, reproducible baseline.

Files to create or update:

- `.gitignore`
- `.env.example`
- `README.md`
- `docs/architecture.md`
- `docs/api_contract.md`
- `docs/rag_system_design.md`
- `docs/backend_implementation_plan.md`

Dependencies:

- Git.
- Python 3.11 or 3.12.

Commands:

```powershell
git status --short
python --version
```

Tests:

- No runtime tests.

Validation:

- Secrets are not tracked.
- Dataset binaries are ignored.
- Backend plan exists before code implementation.

Success criteria:

- A developer can understand the backend plan without asking for missing steps.

## Phase 1: Backend Foundation

Objective:

- Create a minimal FastAPI backend with typed settings and health checks.

Files to create or update:

- `apps/backend/requirements.txt`
- `apps/backend/main.py`
- `apps/backend/config.py`
- `apps/backend/routers/health.py`
- `apps/backend/tests/test_health.py`

Dependencies:

```txt
fastapi
uvicorn[standard]
pydantic
pydantic-settings
python-dotenv
httpx
pytest
pytest-asyncio
```

Commands:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r apps/backend/requirements.txt
uvicorn apps.backend.main:app --reload --port 8000
pytest apps/backend/tests/test_health.py
```

Tests:

- Health endpoint returns status.
- Settings load from environment.
- Missing optional model providers do not crash the app.

Validation:

- `GET /health` returns the response defined in `docs/api_contract.md`.

Success criteria:

- Backend starts locally.
- Health endpoint is stable and typed.

## Phase 2: Database and Session Audit

Objective:

- Store triage sessions and audit records.

Files to create or update:

- `apps/backend/database.py`
- `apps/backend/schemas/session.py`
- `apps/backend/services/session_service.py`
- `apps/backend/routers/sessions.py`
- `scripts/setup_db.py`
- `apps/backend/tests/test_sessions.py`

Dependencies:

```txt
sqlalchemy
aiosqlite
```

Commands:

```powershell
python scripts/setup_db.py
pytest apps/backend/tests/test_sessions.py
```

Tests:

- Create session.
- Update session status.
- Retrieve session by ID.
- Return 404 for missing session.

Validation:

- SQLite database is created at `DB_PATH`.
- Session records include request, result, errors, timestamps, and model mode.

Success criteria:

- Every triage run can be audited.

## Phase 3: Deterministic Clinical Tools

Objective:

- Implement testable clinical decision support primitives before LLM reasoning.

Files to create or update:

- `ai/tools/calculate_respiratory_rate.py`
- `ai/tools/classify_pneumonia.py`
- `ai/tools/detect_danger_signs.py`
- `ai/tools/assess_dehydration.py`
- `ai/tools/generate_referral.py`
- `ai/tests/test_clinical_tools.py`

Dependencies:

- Pure Python.
- pytest.

Commands:

```powershell
pytest ai/tests/test_clinical_tools.py
```

Tests:

- Fast breathing threshold for age under 2 months.
- Fast breathing threshold for age 2 to 11 months.
- Fast breathing threshold for age 12 to 59 months.
- Chest indrawing produces high-risk classification.
- General danger signs produce high-risk safety flags.
- Missing age returns explicit uncertainty.

Validation:

- Tool outputs are JSON-serializable.
- Tool results include inputs, outputs, and rationale.

Success criteria:

- Safety-critical rules are covered by tests before agent integration.

## Phase 4: LLM Router

Objective:

- Create a single model interface for online Gemma and offline Ollama.

Files to create or update:

- `ai/llm/router.py`
- `ai/llm/gemma_online.py`
- `ai/llm/gemma_offline.py`
- `ai/tests/test_llm_router.py`

Dependencies:

```txt
google-genai
httpx
tenacity
```

Commands:

```powershell
pytest ai/tests/test_llm_router.py
```

Tests:

- Online mode selected when API key exists and healthcheck succeeds.
- Offline mode selected when online is unavailable and Ollama responds.
- Unavailable mode returns typed error.
- Router exposes the same interface for both providers.

Validation:

- Provider-specific details do not leak into agent nodes.

Success criteria:

- Switching online/offline does not change API contracts.

## Phase 5: RAG Ingestion and Retrieval

Objective:

- Build a reproducible, citation-ready RAG index.

Files to create or update:

- `ai/rag/ingest.py`
- `ai/rag/embeddings.py`
- `ai/rag/vectorstore.py`
- `scripts/ingest_pdfs.py`
- `ai/tests/test_rag_ingestion.py`
- `ai/tests/test_rag_retrieval.py`
- `tests/fixtures/rag_eval_cases.json`

Dependencies:

```txt
chromadb
PyMuPDF
sentence-transformers
Pillow
numpy
torch
transformers
```

Commands:

```powershell
python scripts/ingest_pdfs.py
pytest ai/tests/test_rag_ingestion.py ai/tests/test_rag_retrieval.py
```

Tests:

- PDF pages are extracted with metadata.
- Text chunks include source and page.
- Table chunks are preserved.
- Page-image embeddings are created when visual model is available.
- Retrieval returns expected sources for curated evaluation cases.

Validation:

- `data/chroma/` is populated.
- Retrieval returns citations with stable `chunk_id`.

Success criteria:

- RAG is accurate enough for pneumonia demo and safe no-answer cases.

## Phase 6: Agent Pipeline

Objective:

- Orchestrate intake, symptom extraction, retrieval, reasoning, verification, and translation.

Files to create or update:

- `ai/agent/state.py`
- `ai/agent/graph.py`
- `ai/agent/nodes/intake.py`
- `ai/agent/nodes/symptom_extraction.py`
- `ai/agent/nodes/rag_retrieval.py`
- `ai/agent/nodes/imci_reasoning.py`
- `ai/agent/nodes/verification.py`
- `ai/agent/nodes/translation.py`
- `ai/prompts/*.txt`
- `ai/tests/test_agent_pipeline.py`

Dependencies:

```txt
langgraph
jsonschema
```

Commands:

```powershell
pytest ai/tests/test_agent_pipeline.py
```

Tests:

- Intake normalizes language.
- Symptom extraction returns valid JSON.
- Retrieval receives structured query.
- Reasoning includes citations.
- Verification catches contradictory low-risk output when danger signs exist.
- Translation preserves clinical terms.

Validation:

- Agent returns one final typed triage result.

Success criteria:

- The full backend triage workflow works from text input.

## Phase 7: Triage API

Objective:

- Expose the agent pipeline through stable HTTP endpoints.

Files to create or update:

- `apps/backend/schemas/triage.py`
- `apps/backend/routers/triage.py`
- `apps/backend/tests/test_triage_api.py`

Dependencies:

- Existing backend and AI dependencies.

Commands:

```powershell
pytest apps/backend/tests/test_triage_api.py
```

Tests:

- Valid request returns complete result.
- Invalid language returns 422.
- Missing model returns 503.
- High-risk symptoms return safety flags.
- Session is persisted.

Validation:

- `POST /triage/run` matches `docs/api_contract.md`.

Success criteria:

- Backend can support frontend triage integration.

## Phase 8: Audio Transcription API

Objective:

- Add local audio transcription.

Files to create or update:

- `apps/backend/schemas/audio.py`
- `apps/backend/services/whisper_service.py`
- `apps/backend/routers/audio.py`
- `apps/backend/tests/test_audio_api.py`

Dependencies:

```txt
faster-whisper
python-multipart
```

Commands:

```powershell
pytest apps/backend/tests/test_audio_api.py
```

Tests:

- Reject unsupported file type.
- Reject oversized file.
- Return transcript for valid fixture.
- Delete temporary files after processing.

Validation:

- `POST /audio/transcribe` returns transcript response contract.

Success criteria:

- Audio can feed the text triage workflow.

## Phase 9: Video Respiratory Support API

Objective:

- Add optional respiratory rate estimation from short video.

Files to create or update:

- `apps/backend/schemas/video.py`
- `apps/backend/services/video_service.py`
- `apps/backend/routers/video.py`
- `apps/backend/tests/test_video_api.py`

Dependencies:

```txt
opencv-python-headless
scipy
numpy
```

Commands:

```powershell
pytest apps/backend/tests/test_video_api.py
```

Tests:

- Reject unsupported file type.
- Return uncertainty for low-quality video.
- Return respiratory rate for controlled fixture.

Validation:

- Video output is clearly marked as supportive, not definitive.

Success criteria:

- Respiratory rate can be passed into `/triage/run`.

## Phase 10: Backend Smoke Tests and Demo Packaging

Objective:

- Prove the backend works end-to-end before frontend work starts.

Files to create or update:

- `scripts/smoke_test.py`
- `docker-compose.yml`
- `apps/backend/Dockerfile`
- `docs/deployment.md`

Dependencies:

- Docker Desktop.
- Ollama for offline demo.

Commands:

```powershell
python scripts/smoke_test.py --mode online
python scripts/smoke_test.py --mode offline
docker compose up --build
```

Tests:

- Online smoke test.
- Offline smoke test.
- Docker healthcheck.

Validation:

- Backend is demo-ready without frontend.

Success criteria:

- Frontend implementation can start only after this phase is complete.

