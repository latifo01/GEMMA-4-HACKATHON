# Demo Script

## Goal

Show that the backend can support multilingual pediatric triage in a crisis setting with online
and offline model routing.

## Three-Minute Structure

### 0:00-0:25 Problem

A nurse receives a caregiver who speaks a different language. The clinic has limited staff,
limited internet, and limited time to search paper IMCI protocols.

### 0:25-0:55 Intake

The nurse dictates through the microphone, uploads audio, or enters a transcript. The backend
transcribes audio locally when file upload is used.

### 0:55-1:25 Clinical Extraction

The backend extracts symptoms, patient age, respiratory information, and missing information.

### 1:25-1:55 Grounded Reasoning

The RAG service retrieves IMCI context. Deterministic tools compute respiratory thresholds and
danger sign flags. The model produces grounded reasoning with citations.

### 1:55-2:25 Output

The interface shows the triage decision first, then immediate actions, Gemma 4 synthesis, IMCI
evidence, safety flags, and translated caregiver explanation.

### 2:25-2:50 Offline Resilience

The online API path is disabled. The same backend API uses Ollama through the LLM router.

### 2:50-3:00 Closing

The demo emphasizes decision support, auditability, multilingual access, and resilience.

## Backend Proof Points

- `/health` shows selected model mode.
- `/audio/transcribe` works locally.
- `/triage/run` returns grounded output.
- `/sessions/{session_id}` returns the audit record.
- `scripts/evaluate_clinical_cases.py` currently reports `15/15` deterministic IMCI demo cases
  passing.
- Cloud Run packages the Chroma IMCI index and rendered page images for the public demo.
- The frontend consumes `/triage/run/stream`, so the progress trace reflects real backend node
  events rather than a local timer.

## Honest Demo Language

- Say "live backend reasoning trace" for the node progress UI.
- Say "offline-ready architecture" for the public Vercel demo, then show the local Ollama path as a
  separate field deployment proof.
- Say "clinical decision support" and never "autonomous diagnosis".
