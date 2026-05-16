# Product Brief

## Vision

ImciFlow supports nurses in crisis and low-resource care settings where language barriers,
limited staffing, and limited internet access can delay pediatric triage.

The system helps healthcare workers understand caregiver input in English, French, or Sudanese
Arabic, extract key symptoms, retrieve relevant IMCI guidance, and produce a visual triage result
with citations and safety flags.

## Problem

Clinical teams may face:

- shortage of staff who can communicate across Sudanese Arabic, French, and English;
- limited time to navigate paper IMCI protocols during urgent care;
- unreliable internet access;
- difficulty documenting respiratory signs and danger signs consistently;
- need to explain decisions to caregivers in a language they understand.

## Solution

ImciFlow provides a backend-first clinical decision-support pipeline:

1. Receive transcript, audio, or optional respiratory video.
2. Transcribe audio locally when needed.
3. Extract symptoms with a structured LLM prompt.
4. Retrieve relevant IMCI evidence through RAG.
5. Run deterministic clinical tools for safety-critical rules.
6. Generate a grounded triage output.
7. Translate the explanation for the target user.
8. Store an auditable session record.

## MVP Focus

The backend MVP focuses on pediatric IMCI triage, especially:

- general danger signs;
- cough or difficult breathing;
- pneumonia-related respiratory thresholds;
- diarrhea and dehydration as an extension path;
- fever and nutrition as extension paths.

## Demo Story

The demo should show a nurse receiving caregiver input in one language, getting structured
clinical support in another language, and receiving an IMCI-grounded triage output with clear
safety flags and citations.

