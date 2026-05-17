# Backend Deployment Strategy

## Objective

Prepare the backend for fast, stable, reproducible demo deployment while preserving a clean path
to production.

## Environment Management

Files:

- `.env` for local secrets. This file is never committed.
- `.env.example` for public variable names.
- `apps/backend/config.py` for typed settings validation.

Required variables:

```txt
GOOGLE_AI_API_KEY
GEMMA_ONLINE_MODEL
OLLAMA_BASE_URL
DOCKER_OLLAMA_BASE_URL
GEMMA_OFFLINE_MODEL
OLLAMA_GENERATION_TIMEOUT_SECONDS
CHROMA_PATH
DB_PATH
WHISPER_MODEL_NAME
AUDIO_TEMP_DIR
VIDEO_TEMP_DIR
APP_ENV
BACKEND_PORT
FRONTEND_ORIGIN
```

Validation:

- Application startup must fail only for truly required settings.
- Missing online API key must not fail startup if offline mode is available.
- `/health` must expose model availability without exposing secrets.
- `GEMMA_ONLINE_MODEL` must point to a Gemma 4 variant for submission smoke tests.
- `GEMMA_OFFLINE_MODEL` should point to a local Gemma 4 variant when hardware allows it. On a
  constrained laptop, it may point to a smaller Ollama model only for local resilience checks.
- `OLLAMA_BASE_URL` is for local Python runs. `DOCKER_OLLAMA_BASE_URL` is for Compose and should
  usually stay `http://host.docker.internal:11434` on Windows.
- Keep `OLLAMA_HEALTH_TIMEOUT_SECONDS` short, but use a longer
  `OLLAMA_GENERATION_TIMEOUT_SECONDS` for slow local CPU inference.

## Docker Strategy

Backend image:

- Base image: Python slim.
- Install system dependencies for PyMuPDF, OpenCV headless, and faster-whisper.
- Install Python dependencies from `apps/backend/requirements.txt`.
- Copy `apps/`, `ai/`, and `scripts/`.
- Mount `dataset/` and `data/` as volumes for local demo.

Compose services:

| Service | Purpose |
|---|---|
| `backend` | FastAPI API server |
| `chroma` | Optional ChromaDB server if local embedded Chroma is not used |
| `ollama` | Optional external local service, usually run outside Docker on Windows |

Selected MVP deployment:

- Run backend in Docker.
- Use mounted `data/` for ChromaDB and SQLite.
- Use host Ollama through `host.docker.internal`.

Reason:

- Simpler Windows development.
- Faster demo recovery.
- Avoids GPU passthrough complexity in Docker.

## Deployment Workflow

Local backend:

```powershell
.\scripts\run_backend.ps1
```

Docker backend:

```powershell
docker compose up --build backend
```

RAG preparation:

```powershell
python scripts/ingest_pdfs.py
```

Database preparation:

```powershell
python scripts/setup_db.py
```

Smoke test:

```powershell
python scripts/smoke_test.py --mode online
python scripts/smoke_test.py --mode offline
python scripts/smoke_test.py --mode offline --allow-non-gemma4-offline
python scripts/smoke_test.py --mode online --base-url http://localhost:8000
```

The smoke test is intentionally Gemma 4-first. Online mode always fails if `/health` or
`/triage/run` reports a non-Gemma 4 model. Offline mode also requires Gemma 4 by default, but
`--allow-non-gemma4-offline` can be used on low-power machines to verify Ollama fallback mechanics
without claiming that run as the Gemma 4 submission proof. All smoke modes still require RAG,
citations, and completed audit session storage.

The final UI should expose the same three model choices supported by `/triage/run`:

- `auto`: use online Gemma 4 when available, otherwise local Ollama;
- `online`: require online Gemma 4;
- `offline`: require local inference for low-connectivity settings.

## CI/CD Recommendations

Minimal GitHub Actions workflow:

1. Install Python.
2. Install backend dependencies.
3. Run formatting check.
4. Run unit tests.
5. Run backend API tests.
6. Build Docker image.

Recommended checks:

```txt
ruff check
pytest apps/backend/tests ai/tests
docker build -f apps/backend/Dockerfile .
```

Do not run full RAG ingestion in every CI job unless document fixtures are small. Use small
fixtures for CI and full ingestion for release or demo preparation.

## Cloud Deployment Options

Option 1: Single VM.

- Best for hackathon demo.
- Run backend with Docker Compose.
- Store ChromaDB and SQLite on attached disk.
- Use online Gemma API for model calls.

Option 2: Cloud Run or container app.

- Good for quick public backend deployment.
- Requires external persistent storage or prebuilt index artifact.
- Offline Ollama mode is not suitable unless using a GPU-capable service.

Option 3: Kubernetes.

- Not recommended for the hackathon MVP.
- Useful later for separate API, ingestion, workers, vector DB, and monitoring.

Selected demo option:

- Google Cloud Run backend plus Vercel frontend.

Reason:

- Stable public HTTPS backend URL for the jury.
- Strong alignment with the Google/Gemma 4 project story.
- Easy rollback through Cloud Run revisions and Vercel deployments.
- Local Docker Compose remains the recovery path for development and emergency demos.

Primary execution guide:

- `docs/cloud_run_deployment.md`

## Monitoring and Logging

Required logs:

- `request_id`
- endpoint
- status code
- duration
- selected model mode
- selected model name
- RAG retrieval count
- top citation source names
- safety flags
- error code when present

Do not log:

- API keys.
- Raw audio.
- Full caregiver transcript in production logs.
- Full patient identifying information.

Metrics:

- Request latency by endpoint.
- Model latency.
- Retrieval latency.
- Reranking latency.
- Transcription latency.
- Error count by code.
- Model availability state.

Production path:

- Add OpenTelemetry.
- Export logs to cloud logging.
- Export metrics to Prometheus or managed monitoring.

## Reproducibility

Required artifacts:

- `requirements.txt` pinned or bounded.
- `.env.example`.
- Dockerfile.
- RAG ingestion script.
- Smoke test script.
- Retrieval evaluation fixtures.

Backend demo is reproducible when:

- A clean machine can install dependencies.
- The same PDFs produce the same `chunk_id` values.
- Smoke tests pass in online mode.
- Offline fallback mechanics pass when Ollama is running. For submission-grade offline proof,
  `GEMMA_OFFLINE_MODEL` must still be a local Gemma 4 tag.
