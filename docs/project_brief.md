# Project Brief

ImciFlow is a backend-first clinical decision-support project for pediatric triage in crisis
settings. It combines multilingual intake, local speech transcription, optional respiratory video
analysis, IMCI-grounded RAG, deterministic clinical tools, and online/offline Gemma 4 routing.

The project prioritizes a validated backend before frontend implementation.

Key backend goals:

- stable FastAPI API;
- online Gemma 4 API support;
- offline Gemma 4 support through Ollama;
- reproducible RAG ingestion;
- multimodal retrieval support for text, tables, diagrams, charts, and page images;
- deterministic safety tools;
- auditable session storage;
- deployment-ready Docker strategy.
