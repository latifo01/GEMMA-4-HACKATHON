# Backend Architecture

## Scope

This document defines the backend-first architecture for ImciFlow. It does not define frontend
implementation details. The frontend will only consume the API contracts described in
`docs/api_contract.md` after backend validation.

## Explicit Assumptions

- The local `.env` file already exists and contains valid external API credentials.
- The initial production demo runs on one machine or one small cloud instance.
- The backend is the system boundary for clinical reasoning, model orchestration, RAG, storage,
  audio transcription, video analysis, and API exposure.
- The frontend is not implemented until the backend API, tests, and local demo path are validated.
- The project uses Python for backend and AI services because FastAPI, PyMuPDF, ChromaDB,
  sentence-transformers, Whisper, OpenCV, and LangGraph integrate cleanly in one runtime.
- Clinical safety rules are implemented as deterministic Python tools where possible. The LLM
  is used for language understanding, summarization, translation, and grounded reasoning, not as
  the only source of medical decision logic.

## System Goals

- Provide a backend that can run online with Gemma 4 API and offline with local Gemma 4 through Ollama.
- Let the product choose `auto`, `online`, or `offline` per triage run, so the final interface can
  expose connectivity mode as an explicit user decision.
- Support multilingual intake in English, French, and Sudanese Arabic.
- Ground triage reasoning in IMCI source documents.
- Return auditable outputs with citations, extracted symptoms, deterministic tool results, and
  safety warnings.
- Keep deployment simple enough for a hackathon demo while preserving production-grade structure.

## Non-Goals For The Backend Validation Phase

- No frontend implementation.
- No authentication system unless required for deployment.
- No multi-tenant user management.
- No hospital information system integration.
- No automatic final diagnosis. The backend returns decision support only.

## High-Level Components

| Component | Role | Responsibilities | Main Dependencies |
|---|---|---|---|
| FastAPI application | Public backend API | Request validation, routing, error handling, CORS, lifecycle hooks | FastAPI, Uvicorn, Pydantic |
| Settings layer | Runtime configuration | Load `.env`, validate required variables, expose typed settings | pydantic-settings, python-dotenv |
| LLM router | Model selection | Select Gemma online or Ollama offline, expose a shared generation interface | google-genai or google-generativeai, httpx |
| Agent pipeline | Clinical workflow orchestration | Intake validation, symptom extraction, retrieval, reasoning, verification, translation | LangGraph or direct service pipeline |
| RAG service | Grounded retrieval | Ingest documents, create multimodal indexes, retrieve and rerank context | PyMuPDF, ChromaDB, sentence-transformers, optional CLIP/SigLIP |
| Deterministic clinical tools | Rule-based safety layer | Respiratory thresholds, danger signs, dehydration scoring, referral rules | Pure Python, pytest |
| Audio service | Speech-to-text | Transcribe uploaded audio locally for demo and offline use | faster-whisper |
| Video service | Visual respiratory support | Estimate respiratory rate from short chest videos, return confidence | OpenCV, NumPy, SciPy, optional MediaPipe |
| Session service | Persistence and audit | Store request, extracted symptoms, model mode, citations, output, errors | SQLite, SQLAlchemy, aiosqlite |
| Observability layer | Debug and monitoring | Structured logs, request IDs, latency metrics, model mode traces | Python logging, optional OpenTelemetry |

## Backend Folder Responsibilities

```txt
apps/backend/
  main.py                 FastAPI app creation and router registration.
  config.py               Typed environment settings.
  database.py             Async database engine and session factory.
  routers/                HTTP boundaries only. No business logic.
  schemas/                Request and response DTOs.
  services/               Backend services for audio, video, sessions.

ai/
  agent/                  Triage workflow orchestration.
  llm/                    Online/offline model clients and router.
  rag/                    Ingestion, embeddings, vector store, reranking.
  tools/                  Deterministic clinical tools.
  prompts/                Versioned prompts loaded by the agent.
```

## Data Flow: Text Triage

1. Client calls `POST /triage/run` with transcript, target language, optional age, optional
   respiratory rate, and optional session ID.
2. FastAPI validates the request with Pydantic.
3. Session service creates an audit record with status `running`.
4. Agent intake node normalizes language, validates required fields, and records missing data.
5. Symptom extraction node calls the LLM router with the symptom extraction prompt.
6. Extracted symptoms are validated against a strict JSON schema.
7. RAG retrieval receives a structured query built from symptoms, age, and chief complaint.
8. RAG service retrieves hybrid text and visual context, reranks candidates, and returns compact
   citations.
9. IMCI reasoning node calls deterministic clinical tools and asks the LLM to produce grounded
   reasoning using retrieved context and tool results.
10. Verification node checks that danger signs and referral rules are not contradicted.
11. Translation node generates output in the requested language when needed.
12. Session service stores final output, citations, tool calls, model mode, and latency.
13. API returns a structured result or streams progress through SSE.

## Data Flow: Audio Intake

1. Client uploads audio to `POST /audio/transcribe`.
2. Backend validates file size, content type, and duration limits.
3. Audio service stores the upload in a temporary directory.
4. faster-whisper transcribes locally.
5. Backend returns transcript, detected language, duration, and confidence if available.
6. Temporary audio is deleted after processing unless debug retention is explicitly enabled.

## Data Flow: Video Respiratory Support

1. Client uploads a short chest movement video to `POST /video/analyze`.
2. Backend validates file size, content type, and duration limits.
3. Video service samples frames at a fixed frame rate.
4. Motion signal is extracted from a chest region or detected keypoints.
5. Signal processing estimates breaths per minute and confidence.
6. API returns respiratory rate, confidence, frames analyzed, and uncertainty notes.
7. The triage endpoint treats video-derived respiratory rate as supportive evidence, not as a
   mandatory clinical fact.

## Online and Offline Model Routing

Mode policy:

1. `auto`: use online Gemma 4 when available, otherwise use the configured local Ollama provider.
2. `online`: require the configured online Gemma 4 provider and fail safely if unavailable.
3. `offline`: require the configured local Ollama provider and fail safely if unavailable.

The router exposes a single interface:

- `generate_json(prompt, schema, temperature)`
- `generate_text(prompt, temperature)`
- `stream_text(prompt, temperature)`
- `healthcheck()`

This prevents API-specific logic from leaking into routers or agent nodes.

## Architecture Decisions

| Decision | Selected Option | Alternatives | Reason |
|---|---|---|---|
| API framework | FastAPI | Flask, Django REST | Strong Pydantic integration, async support, clear OpenAPI docs |
| Local database | SQLite with SQLAlchemy async | Postgres | Faster demo setup, enough for single-node prototype, easy migration path |
| Vector database | ChromaDB local persistent store | FAISS, Qdrant, Weaviate | Simple local deployment, Python-native, persistent, enough for demo |
| RAG ingestion | Precomputed indexes | Runtime PDF parsing | Lower latency and reproducible retrieval |
| Clinical rules | Deterministic tools | LLM-only decisions | Safer, testable, auditable |
| Model routing | Backend-managed router | Frontend model selection | Keeps model policy centralized and auditable |
| Streaming | SSE | WebSocket | Simpler for one-way progress and result streaming |

## Scalability Path

The MVP runs in one backend process. The production path is:

1. Move SQLite to Postgres.
2. Move ChromaDB local persistence to Qdrant or managed vector storage.
3. Run ingestion as a separate job.
4. Add Redis for model response caching and task queues.
5. Move audio and video processing to background workers.
6. Add authentication and audit log retention policies.

## Safety Boundaries

- The backend must never state that it replaces a clinician.
- Every triage output must include `human_review_required: true`.
- Every high-risk output must include `safety_flags`.
- Missing critical fields must be returned as explicit `missing_information`.
- Citations are required for clinical recommendations.
- Deterministic tool outputs override conflicting LLM text.
