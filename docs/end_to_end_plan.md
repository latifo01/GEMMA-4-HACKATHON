# Backend End-to-End Plan

## Objective

Build and validate the backend before frontend implementation. The backend must support a full
clinical decision-support demo from transcript or audio input to grounded triage output.

## End-to-End Scenario

Input:

- A nurse receives a caregiver speaking Sudanese Arabic, French, or English.
- The nurse chooses online, offline, or automatic mode, then records audio or enters a transcript.
- Optional video is uploaded to estimate respiratory rate.

Backend output:

- Transcript.
- Extracted symptoms.
- Respiratory-rate interpretation.
- IMCI color classification.
- Grounded recommendations with citations.
- Translated caregiver explanation.
- Audit session record.

## Online Flow

1. Backend starts with `.env`.
2. `/health` verifies the Google API key and online Gemma model availability.
3. Audio is transcribed locally.
4. Triage calls the LLM router.
5. LLM router selects online Gemma.
6. RAG service returns context from local indexes.
7. Deterministic tools compute safety-critical classifications.
8. Verification enforces safety rules.
9. Backend stores the session and returns output.

Success criteria:

- `/health` reports `selected_model_mode: online`.
- `/triage/run` returns classification, citations, and translated output.
- No frontend is required to prove this path.

## Offline Flow

1. Backend starts without using the online API path.
2. `/health` checks Ollama at `OLLAMA_BASE_URL`.
3. The request sets `model_mode: offline`.
4. LLM router selects the configured offline model.
4. The same triage request runs through the same agent pipeline.
5. Backend returns a result with `model.mode: offline`.

Success criteria:

- `/health` reports `selected_model_mode: offline`.
- `/triage/run` uses the same API contract as online mode.
- The frontend uses the same triage endpoint for online and offline mode, changing only
  `model_mode`.

## Required Backend Commands

Create virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```powershell
pip install -r apps/backend/requirements.txt
```

Build RAG index:

```powershell
python scripts/ingest_pdfs.py
```

Initialize database:

```powershell
python scripts/setup_db.py
```

Run backend:

```powershell
uvicorn apps.backend.main:app --reload --host 0.0.0.0 --port 8000
```

Run backend tests:

```powershell
pytest apps/backend/tests ai/tests tests/integration
```

## Backend Validation Order

1. Configuration loads from `.env`.
2. `/health` returns structured status.
3. Database initialization succeeds.
4. Deterministic clinical tools pass unit tests.
5. RAG ingestion creates an index.
6. RAG query returns citations.
7. LLM router returns a JSON response in online mode.
8. LLM router returns a JSON response in offline mode.
9. `/triage/run` returns a complete result from text input.
10. `/audio/transcribe` returns a transcript.
11. `/video/analyze` returns respiratory support data or explicit uncertainty.
12. `/sessions/{session_id}` returns the stored audit record.

## Demo Readiness Criteria

- One command starts the backend locally.
- One command builds the RAG index.
- One smoke test verifies online mode.
- One smoke test verifies offline mode when Ollama is running.
- The API contract is stable enough for frontend implementation.
