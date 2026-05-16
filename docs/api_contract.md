# Backend API Contract

## Scope

This document defines the backend API contract before frontend implementation. All endpoints
return JSON unless explicitly documented as streaming.

## Shared Conventions

Base path for local development:

```txt
http://localhost:8000
```

Successful response envelope for non-streaming endpoints:

```json
{
  "data": {},
  "meta": {
    "request_id": "string",
    "model_mode": "online|offline|unavailable",
    "duration_ms": 0
  }
}
```

Error response envelope:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  },
  "meta": {
    "request_id": "string"
  }
}
```

## Error Codes

| Code | HTTP Status | Meaning |
|---|---:|---|
| `VALIDATION_ERROR` | 422 | Request body or file input is invalid |
| `MODEL_UNAVAILABLE` | 503 | No online or offline model is available |
| `RAG_INDEX_MISSING` | 503 | Vector index has not been built |
| `TRANSCRIPTION_FAILED` | 500 | Audio transcription failed |
| `VIDEO_ANALYSIS_FAILED` | 500 | Video processing failed |
| `TRIAGE_VERIFICATION_FAILED` | 500 | Safety verification failed |
| `SESSION_NOT_FOUND` | 404 | Requested session does not exist |

## GET /health

Purpose:

- Verify backend availability.
- Verify configured model mode.
- Verify RAG index availability.
- Verify database availability.

Response:

```json
{
  "data": {
    "status": "ok",
    "version": "0.1.0",
    "online_model_available": true,
    "offline_model_available": false,
    "selected_model_mode": "online",
    "selected_model_name": "models/gemma-4-26b-a4b-it",
    "rag_index_available": true,
    "database_available": true
  },
  "meta": {
    "request_id": "uuid",
    "model_mode": "online",
    "duration_ms": 12
  }
}
```

Validation criteria:

- Returns HTTP 200 when backend and database are available.
- Returns `selected_model_mode: unavailable` when no model is reachable, without crashing.

## POST /audio/transcribe

Purpose:

- Convert uploaded audio to text using local transcription.

Request:

- `multipart/form-data`
- Field `file`: audio file.
- Field `source_language`: optional `en`, `fr`, `ar-SD`, or `auto`.

Constraints:

- Accepted content types: `audio/webm`, `audio/wav`, `audio/mpeg`, `audio/mp4`.
- Maximum duration: 120 seconds for demo.
- Maximum file size: 25 MB for demo.

Response:

```json
{
  "data": {
    "transcript": "The child has fever and fast breathing.",
    "detected_language": "en",
    "duration_seconds": 14.2,
    "segments": [
      {
        "start_seconds": 0.0,
        "end_seconds": 4.1,
        "text": "The child has fever."
      }
    ]
  },
  "meta": {
    "request_id": "uuid",
    "model_mode": "offline",
    "duration_ms": 1800
  }
}
```

## POST /video/analyze

Purpose:

- Estimate respiratory rate from a short chest movement video.

Request:

- `multipart/form-data`
- Field `file`: video file.
- Field `age_months`: optional integer.

Constraints:

- Accepted content types: `video/mp4`, `video/webm`, `video/quicktime`.
- Recommended duration: 15 to 30 seconds.
- Maximum file size: 80 MB for demo.
- `respiratory_rate_bpm` may be `null` when the video signal is insufficient.

Response:

```json
{
  "data": {
    "respiratory_rate_bpm": 52.0,
    "confidence": 0.72,
    "frames_analyzed": 450,
    "duration_seconds": 20.0,
    "quality_flags": [
      "stable_camera",
      "sufficient_motion_signal"
    ],
    "notes": "Respiratory rate is estimated from video motion and requires clinical confirmation."
  },
  "meta": {
    "request_id": "uuid",
    "model_mode": "offline",
    "duration_ms": 2400
  }
}
```

## POST /triage/run

Purpose:

- Run the complete IMCI-guided triage workflow.

Request:

```json
{
  "session_id": "optional-uuid",
  "transcript": "Mother says the child is coughing and breathing fast.",
  "source_language": "auto",
  "target_language": "fr",
  "model_mode": "auto",
  "patient": {
    "age_months": 18,
    "sex": "unknown"
  },
  "measurements": {
    "respiratory_rate_bpm": 52.0,
    "temperature_celsius": null
  },
  "context": {
    "setting": "low_resource_clinic",
    "country": "Sudan"
  }
}
```

Request validation:

- `transcript` is required.
- `target_language` must be one of `en`, `fr`, `ar-SD`.
- `model_mode` is optional and must be one of `auto`, `online`, or `offline`.
- `auto` lets the backend choose online Gemma 4 first, then offline.
- `online` requires the configured online Gemma 4 provider.
- `offline` requires the configured local Ollama provider and is intended for low-connectivity
  deployments such as clinics or refugee camps with a local inference machine.
- `age_months` is optional but produces `missing_information` when absent.
- `respiratory_rate_bpm` is optional but required for full pneumonia classification.

Response:

```json
{
  "data": {
    "session_id": "uuid",
    "triage_color": "YELLOW",
    "classification": "PNEUMONIA",
    "human_review_required": true,
    "extracted_symptoms": {
      "cough": true,
      "fever": true,
      "chest_indrawing": false,
      "stridor": false,
      "unable_to_drink": false,
      "convulsions": false,
      "lethargy_or_unconscious": false
    },
    "missing_information": [],
    "tool_results": [
      {
        "tool_name": "calculate_respiratory_rate",
        "result": {
          "is_fast_breathing": true,
          "threshold_bpm": 40
        }
      }
    ],
    "reasoning": "The child has cough and fast breathing for age without danger signs.",
    "recommendations": [
      "Treat according to local IMCI pneumonia protocol.",
      "Advise caregiver to return immediately if danger signs appear."
    ],
    "translated_output": "L'enfant presente une toux et une respiration rapide pour son age.",
    "safety_flags": [],
    "citations": [
      {
        "source": "imci-chart-booklet.pdf",
        "page": 12,
        "chunk_id": "imci-chart-booklet-p12-c03",
        "relevance_score": 0.86,
        "quote": "Short excerpt used for grounding."
      }
    ],
    "model": {
      "mode": "online",
      "name": "models/gemma-4-26b-a4b-it"
    }
  },
  "meta": {
    "request_id": "uuid",
    "model_mode": "online",
    "duration_ms": 3500
  }
}
```

## POST /triage/run/stream

Purpose:

- Run triage with SSE progress events.

Content type:

```txt
text/event-stream
```

Events:

```txt
event: node_started
data: {"node":"symptom_extraction"}

event: node_completed
data: {"node":"symptom_extraction"}

event: token
data: {"token":"The child has"}

event: result
data: {"session_id":"uuid","triage_color":"YELLOW"}

event: error
data: {"code":"MODEL_UNAVAILABLE","message":"No model available"}
```

## GET /sessions/{session_id}

Purpose:

- Retrieve an audited triage session.

Response:

```json
{
  "data": {
    "session_id": "uuid",
    "status": "completed",
    "created_at": "2026-05-15T10:00:00Z",
    "updated_at": "2026-05-15T10:00:03Z",
    "request": {},
    "result": {},
    "errors": []
  },
  "meta": {
    "request_id": "uuid",
    "model_mode": "online",
    "duration_ms": 20
  }
}
```

## Backend API Validation Checklist

- OpenAPI schema generated without errors.
- Pydantic rejects invalid language codes.
- Pydantic rejects unsupported file content types.
- `/health` handles model unavailable state without process failure.
- `/triage/run` returns citations for clinical recommendations.
- `/triage/run` returns `human_review_required: true`.
- `/triage/run/stream` emits final `result` or `error` event.
