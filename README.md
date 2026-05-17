# ImciFlow

ImciFlow is a visual and multilingual clinical decision-support backend for pediatric triage in
low-resource crisis settings. The project focuses on English, French, and Sudanese Arabic intake,
IMCI-grounded reasoning, offline resilience, and auditable safety checks.

The triage API supports explicit model mode selection: `auto`, `online`, or `offline`. This keeps
Gemma 4 online as the primary proof path while preserving an offline architecture for deployments
with local inference in low-connectivity settings.

## Current Phase

The project has entered the frontend implementation phase. A Vite React TypeScript frontend now
connects to the validated backend and follows `docs/implementation_frontend_plan.md`.

Validated:

- Frontend build passes.
- Frontend API service tests pass.
- Backend CORS preflight test passes for the local frontend origin.
- Online Gemma 4 smoke test passed end to end.
- Local Ollama fallback smoke test passed with a lightweight model and explicit non-Gemma 4 flag.
- Docker Compose runtime smoke test passed against `http://localhost:8000`.
- Unit and API test suite passed.
- Docker backend image build passed.

Primary demo deployment:

- Backend on Google Cloud Run.
- Frontend on Vercel via GitHub.
- Gemma 4 online as the primary demo route, with offline mode presented as the field-resilience
  architecture.

Next product phase:

- Deploy the backend on Google Cloud Run, point Vercel to the Cloud Run URL, then improve clinical
  extraction quality, RAG relevance, and first-response latency before the jury rehearsal.

Completed backend phases:

- Phase 1: FastAPI foundation, typed settings, and `/health`.
- Phase 2: SQLite session audit storage and `/sessions/{session_id}`.
- Phase 3: deterministic clinical tools.
- Phase 4: online/offline LLM router.
- Phase 5: citation-ready RAG ingestion and retrieval over local IMCI PDFs.
- Phase 5.1: FastEmbed multilingual text embeddings, rendered page-image chunks, and CLIP
  visual embeddings for chart-heavy IMCI pages.
- Phase 6: intake, symptom extraction, RAG retrieval, deterministic IMCI reasoning, safety
  verification, and translation.
- Phase 7: `POST /triage/run` with session audit persistence.
- Phase 8: `POST /audio/transcribe` with local Whisper transcription and temporary file cleanup.
- Phase 9: `POST /video/analyze` returns supportive respiratory-rate evidence for Gemma triage.
- Phase 10: Gemma 4-first smoke tests, Docker packaging, and backend demo readiness checks.

Frontend implementation can start. The Gemma 4 proof path remains the online smoke test; local
offline is an optional resilience check for this machine.

## Core Documents

- `docs/architecture.md`
- `docs/api_contract.md`
- `docs/rag_system_design.md`
- `docs/backend_implementation_plan.md`
- `docs/end_to_end_plan.md`
- `docs/deployment.md`
- `docs/cloud_run_deployment.md`
- `docs/render_deployment.md`
- `docs/medical_safety.md`
- `docs/implementation_frontend_plan.md`

## Frontend

Local setup:

```powershell
cd apps/frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

Expected local URLs:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

Vercel settings:

- Framework preset: `Vite`
- Root directory: `apps/frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_BASE_URL=https://YOUR_CLOUD_RUN_URL`

The backend must allow the deployed Vercel origin with `FRONTEND_ORIGIN`.

## Runtime Modes

- Online mode: Gemma 4 through the configured external API.
- Offline mode: local Gemma 4 model through Ollama.

## Safety Position

ImciFlow is not an autonomous diagnostic system. It is a decision-support tool for healthcare
workers. Final clinical decisions remain with qualified medical staff.
