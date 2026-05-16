# Kaggle Writeup Draft

## Title

ImciFlow: Multilingual and Offline-Ready Pediatric Triage Support for Crisis Clinics

## Summary

ImciFlow is a backend-first clinical decision-support system for pediatric triage in low-resource
settings. It combines multilingual intake, local transcription, IMCI-grounded retrieval,
deterministic safety tools, and online/offline Gemma 4 routing.

## Technical Architecture

The backend is built around FastAPI, typed settings, a model router, a RAG service, deterministic
clinical tools, an agent pipeline, and auditable session storage.

## Use of Gemma

Gemma 4 is used for structured symptom extraction, grounded reasoning, and multilingual
explanation. The backend can use an online Gemma 4 API provider or a local Gemma 4 model through
the same router interface.

## RAG Grounding

IMCI documents are ingested into persistent vector indexes with metadata for source, page, chunk
type, section, and content hash. Retrieval supports text, tables, and page-image chunks, followed
by reranking and citation-aware context injection.

## Safety

The system is not autonomous diagnosis software. It is a decision-support backend. Deterministic
clinical tools handle safety-critical rules, and every output requires human review.

## Demo

The demo shows a multilingual caregiver interaction, grounded triage output, citations, and an
offline mode fallback.
