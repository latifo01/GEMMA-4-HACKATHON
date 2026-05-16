from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
from pathlib import Path
from typing import Any

import httpx


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class SmokeFailure(RuntimeError):
    pass


def ensure_gemma4_model(model_name: str | None) -> None:
    normalized = (model_name or "").lower()
    if "gemma-4" not in normalized and "gemma4" not in normalized:
        raise SmokeFailure(f"Expected a Gemma 4 model, got {model_name!r}.")


def validate_triage_result(
    payload: dict[str, Any],
    expected_mode: str,
    require_gemma4: bool = True,
) -> dict[str, Any]:
    data = payload.get("data") or {}
    model = data.get("model") or {}
    citations = data.get("citations") or []
    session_id = data.get("session_id")

    if not session_id:
        raise SmokeFailure("Triage result did not include a session_id.")
    if model.get("mode") != expected_mode:
        raise SmokeFailure(f"Triage used model mode {model.get('mode')!r}, expected {expected_mode!r}.")
    if require_gemma4:
        ensure_gemma4_model(model.get("name"))
    if not citations:
        raise SmokeFailure("Triage result did not include citations.")
    if not data.get("classification") or not data.get("triage_color"):
        raise SmokeFailure("Triage result did not include classification and triage_color.")

    return {
        "session_id": session_id,
        "classification": data["classification"],
        "triage_color": data["triage_color"],
        "model_mode": model["mode"],
        "model_name": model.get("name"),
        "citation_count": len(citations),
        "safety_flags": data.get("safety_flags") or [],
    }


def response_json(response: httpx.Response, step: str) -> dict[str, Any]:
    if response.status_code != 200:
        preview = response.text[:500]
        raise SmokeFailure(f"{step} failed with HTTP {response.status_code}: {preview}")
    return response.json()


def write_controlled_respiration_video(path: Path, respiratory_rate_bpm: float = 52.0) -> None:
    import cv2
    import numpy as np

    fps = 20.0
    duration_seconds = 10.0
    frame_size = (160, 120)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, frame_size)

    for frame_index in range(int(fps * duration_seconds)):
        elapsed_seconds = frame_index / fps
        phase = 2 * np.pi * (respiratory_rate_bpm / 60.0) * elapsed_seconds
        intensity = int(120 + 60 * np.sin(phase))
        frame = np.full((frame_size[1], frame_size[0], 3), 70, dtype=np.uint8)
        frame[36:96, 40:120] = intensity
        writer.write(frame)

    writer.release()


def infer_audio_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".webm":
        return "audio/webm"
    if suffix == ".wav":
        return "audio/wav"
    if suffix in {".mp3", ".mpeg"}:
        return "audio/mpeg"
    if suffix in {".mp4", ".m4a"}:
        return "audio/mp4"
    raise SmokeFailure(f"Unsupported audio fixture suffix: {path.suffix}")


def run_health_check(client: httpx.Client, expected_mode: str, require_gemma4: bool) -> dict[str, Any]:
    payload = response_json(client.get("/health"), "health")
    data = payload.get("data") or {}

    if expected_mode == "online" and not data.get("online_model_available"):
        raise SmokeFailure("Health reports online model unavailable.")
    if expected_mode == "offline" and not data.get("offline_model_available"):
        raise SmokeFailure("Health reports offline model unavailable.")
    if expected_mode == "online" and data.get("selected_model_mode") != "online":
        raise SmokeFailure(f"Health selected {data.get('selected_model_mode')!r}, expected 'online'.")
    if expected_mode == "online" and require_gemma4:
        ensure_gemma4_model(data.get("selected_model_name"))
    if not data.get("rag_index_available"):
        raise SmokeFailure("RAG index is missing. Run scripts/ingest_pdfs.py before smoke testing.")
    if not data.get("database_available"):
        raise SmokeFailure("Database directory is not available. Run scripts/setup_db.py.")

    return data


def run_audio_check(client: httpx.Client, audio_file: Path | None, source_language: str, transcript: str) -> str:
    if audio_file is None:
        return transcript

    with audio_file.open("rb") as file_handle:
        payload = response_json(
            client.post(
                "/audio/transcribe",
                data={"source_language": source_language},
                files={"file": (audio_file.name, file_handle, infer_audio_content_type(audio_file))},
            ),
            "audio transcription",
        )

    transcribed = (payload.get("data") or {}).get("transcript")
    if not transcribed:
        raise SmokeFailure("Audio transcription returned an empty transcript.")
    return transcribed


def run_video_check(client: httpx.Client, age_months: int) -> float | None:
    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = Path(temp_dir) / "controlled.avi"
        write_controlled_respiration_video(video_path)

        with video_path.open("rb") as file_handle:
            payload = response_json(
                client.post(
                    "/video/analyze",
                    data={"age_months": str(age_months)},
                    files={"file": (video_path.name, file_handle, "video/mp4")},
                ),
                "video analysis",
            )

    data = payload.get("data") or {}
    if data.get("respiratory_rate_bpm") is None:
        raise SmokeFailure(f"Video analysis returned uncertainty: {data.get('quality_flags')}")
    return float(data["respiratory_rate_bpm"])


def run_triage_check(
    client: httpx.Client,
    expected_mode: str,
    require_gemma4: bool,
    transcript: str,
    source_language: str,
    target_language: str,
    age_months: int,
    respiratory_rate_bpm: float | None,
) -> dict[str, Any]:
    payload = {
        "transcript": transcript,
        "source_language": source_language,
        "target_language": target_language,
        "model_mode": expected_mode,
        "patient": {"age_months": age_months, "sex": "unknown"},
        "measurements": {"respiratory_rate_bpm": respiratory_rate_bpm},
        "context": {
            "setting": "low_resource_clinic",
            "demo_goal": "Gemma 4 grounded pediatric triage smoke test",
        },
    }
    result = response_json(client.post("/triage/run", json=payload), "triage")
    return validate_triage_result(result, expected_mode, require_gemma4=require_gemma4)


def run_session_check(client: httpx.Client, session_id: str) -> None:
    payload = response_json(client.get(f"/sessions/{session_id}"), "session retrieval")
    data = payload.get("data") or {}
    if data.get("status") != "completed":
        raise SmokeFailure(f"Session {session_id} status is {data.get('status')!r}, expected 'completed'.")


def build_in_process_client(mode: str):
    from fastapi.testclient import TestClient

    from apps.backend.config import get_settings
    from apps.backend.database import create_database
    from apps.backend.main import create_app

    settings = get_settings()
    if mode == "offline":
        settings = settings.model_copy(update={"google_ai_api_key": None})

    asyncio.run(create_database(settings))
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def run_smoke(args: argparse.Namespace) -> dict[str, Any]:
    require_gemma4 = args.mode == "online" or not args.allow_non_gemma4_offline
    if args.base_url:
        client_context = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=args.timeout_seconds)
    else:
        client_context = build_in_process_client(args.mode)

    with client_context as client:
        health = run_health_check(client, args.mode, require_gemma4=require_gemma4)
        transcript = run_audio_check(client, args.audio_file, args.source_language, args.transcript)
        respiratory_rate_bpm = run_video_check(client, args.age_months)
        summary = run_triage_check(
            client=client,
            expected_mode=args.mode,
            require_gemma4=require_gemma4,
            transcript=transcript,
            source_language=args.source_language,
            target_language=args.target_language,
            age_months=args.age_months,
            respiratory_rate_bpm=respiratory_rate_bpm,
        )
        run_session_check(client, summary["session_id"])

    summary["health_model_name"] = health.get("selected_model_name")
    summary["respiratory_rate_bpm"] = respiratory_rate_bpm
    summary["gemma4_required"] = require_gemma4
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an end-to-end ImciFlow backend smoke test.")
    parser.add_argument("--mode", choices=["online", "offline"], required=True)
    parser.add_argument("--base-url", default=None, help="Use a running backend instead of in-process FastAPI.")
    parser.add_argument(
        "--allow-non-gemma4-offline",
        action="store_true",
        help="Allow a lightweight non-Gemma 4 Ollama model for local offline resilience checks only.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--audio-file", type=Path, default=None)
    parser.add_argument("--source-language", choices=["auto", "en", "fr", "ar-SD"], default="en")
    parser.add_argument("--target-language", choices=["en", "fr", "ar-SD"], default="en")
    parser.add_argument("--age-months", type=int, default=18)
    parser.add_argument(
        "--transcript",
        default="Mother says the child has cough and fast breathing. The child is able to drink.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = run_smoke(args)
    except SmokeFailure as exc:
        print(f"SMOKE FAILED: {exc}", file=sys.stderr)
        return 1

    print("SMOKE PASSED")
    print(f"mode={summary['model_mode']}")
    print(f"model={summary['model_name']}")
    print(f"gemma4_required={summary['gemma4_required']}")
    print(f"classification={summary['classification']}")
    print(f"triage_color={summary['triage_color']}")
    print(f"citations={summary['citation_count']}")
    print(f"respiratory_rate_bpm={summary['respiratory_rate_bpm']}")
    print(f"session_id={summary['session_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
