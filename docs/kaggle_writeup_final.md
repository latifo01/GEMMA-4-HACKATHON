# ImciFlow: Gemma 4 Clinical Triage Support for Low-Resource Pediatric Care

## Subtitle

An offline-ready, multilingual, IMCI-grounded decision-support system for crisis clinics.

## Track

Health & Sciences

## Project Links

- Live demo: https://gemma-4-hackathon.vercel.app
- Public code repository: https://github.com/latifo01/GEMMA-4-HACKATHON.git
- Video: add the public YouTube link before submission

## Summary

ImciFlow is a clinical decision-support application for pediatric triage in low-resource settings:
rural clinics, humanitarian sites, mobile health units, and refugee-camp environments where
connectivity, specialist access, and time are constrained. The product goal is not to replace a
clinician. It is to help a health worker move from an unstructured caregiver report to an auditable,
grounded, safety-aware IMCI triage recommendation.

The system uses Gemma 4 as the primary reasoning interface for multilingual clinical signal
extraction and caregiver-facing explanation. Around the model, ImciFlow adds deterministic IMCI
safety tools, retrieval over clinical guidance, audio and video intake, online/offline routing, and
session auditability. The key design principle is that safety-critical rules are not left to a
free-form model answer: Gemma 4 reads and structures the case, while deterministic tools enforce
danger signs, respiratory thresholds, dehydration logic, fever context, and human-review boundaries.

## Problem

In many crisis clinics, the first clinical decision is made under pressure: a caregiver may describe
symptoms in a different language, the health worker may have limited pediatric specialization, and
the relevant IMCI chart may be buried in a document or unavailable offline. The cost of missing a
general danger sign is high. The cost of overbuilding a fragile cloud-only AI system is also high.

ImciFlow addresses this with a simple workflow:

1. capture symptoms by text, microphone dictation, audio upload, or respiratory video;
2. extract clinical signals with Gemma 4;
3. retrieve IMCI evidence from indexed guideline material;
4. apply deterministic clinical tools;
5. return actions, reasoning, citations, safety flags, and an audit record.

## Architecture

The frontend is a Vite React TypeScript application deployed on Vercel. It opens directly into the
triage workspace: case intake on the left, decision output on the right. The interface emphasizes
one primary action, live backend progress, and a decision-first result layout.

The backend is a FastAPI service deployed on Google Cloud Run. It exposes:

- `/health` for model, database, and RAG availability;
- `/triage/run` for full triage execution;
- `/triage/run/stream` for live SSE progress events;
- `/audio/transcribe` for local Whisper transcription;
- `/video/analyze` for respiratory-rate support from short videos;
- `/sessions/{session_id}` for audit retrieval.

The AI pipeline is organized as explicit stages:

1. intake normalization;
2. Gemma 4 symptom extraction;
3. IMCI RAG retrieval;
4. deterministic IMCI reasoning;
5. safety verification;
6. translation and caregiver explanation.

The model router supports three modes: `online`, `offline`, and `auto`. Online mode uses Gemma 4
through the configured external API. Offline mode uses the same interface through Ollama for local
field deployments. The public Cloud Run demo uses online Gemma 4; the offline path is demonstrated
as a deployment architecture for low-connectivity environments.

## How Gemma 4 Is Used

Gemma 4 is central, but deliberately bounded.

First, it turns multilingual free text into structured clinical signals: cough, fever, poor
feeding, vomiting, lethargy, chest indrawing, dehydration signs, and module hints. Second, it
supports multilingual output so the health worker can communicate recommendations to caregivers in
English, French, or Sudanese Arabic. Third, it operates inside a live streamed pipeline so judges can
see the system progress from extraction to evidence retrieval to safety checks.

The important technical choice is separation of roles. Gemma 4 handles language and clinical
interpretation; deterministic Python tools enforce non-negotiable IMCI logic. For example, if Gemma
4 extracts inability to drink or lethargy, the danger-sign tool escalates the case to PINK urgent
review. Generated text cannot downgrade that result.

## Retrieval and Grounding

ImciFlow indexes IMCI material into Chroma with metadata for source, page, chunk type, section, and
content hash. The ingestion pipeline supports text chunks and rendered page-image chunks. For
chart-heavy pages, the system can use visual embeddings so the retrieval layer is not limited to
plain paragraphs. The Cloud Run image packages the local Chroma index and rendered IMCI page images,
so the public demo returns real citations rather than a paper-thin fallback.

The frontend displays IMCI evidence with source, page, relevance, and page preview when available.
This makes the output inspectable: the jury can see not just what the system recommends, but which
guideline evidence it used.

## Safety Design

ImciFlow is clinical decision support only. Every result explicitly requires human review.

Safety is implemented at system level:

- deterministic danger-sign detection;
- age-specific respiratory-rate thresholds;
- pneumonia, dehydration, and fever assessment tools;
- missing-information reporting;
- citation-aware output;
- safety flags;
- session audit persistence.

The latest output format is case-specific rather than generic. For a child with fever, cough, fast
breathing, difficulty feeding, and lethargy, the system does not merely say "follow local protocol."
It states the specific danger signs, explains why the case is escalated, shows the respiratory rule
when a rate is available, lists immediate actions, and records the audit trail.

## Evaluation

The repository includes a deterministic clinical evaluation script:

```bash
python scripts/evaluate_clinical_cases.py
```

The current suite reports `15/15 passed`. It covers general danger signs, cough or difficult
breathing, pneumonia, dehydration, fever, vague complaints, and French intake. The tests are
deliberately deterministic: they validate the clinical safety layer without paying for model calls or
depending on network latency.

The broader automated suite currently passes across backend, AI tools, API routes, frontend tests,
frontend build, E2E Playwright, Docker build, and Cloud Run deployment. The public backend health
check reports Gemma 4 online availability, RAG availability, and database availability.

## Challenges and Design Choices

The largest challenge was avoiding a prototype that looked impressive but behaved like a black-box
symptom checker. We chose a more disciplined architecture: Gemma 4 for language intelligence, RAG
for grounding, deterministic Python for safety, and audit records for accountability.

Another challenge was deployment realism. A laptop cannot be assumed to run the largest Gemma 4
model locally. ImciFlow therefore separates architecture from hardware: the public demo uses Cloud
Run and online Gemma 4, while the same router supports an Ollama offline deployment for field
adaptability.

Finally, latency and demo credibility mattered. We added SSE progress, Cloud Run warm instances,
packaged RAG indexes, and a decision-first UI so the system feels responsive and explainable during
a three-minute judging window.

## Why This Matters

ImciFlow demonstrates a practical pattern for high-stakes AI: open-model intelligence wrapped in
retrieval, deterministic safety, transparent evidence, and offline-ready deployment. It is not a
chatbot for diagnosis. It is a grounded clinical copilot for the first minutes of pediatric triage
when the right question, in the right language, can change the outcome.
