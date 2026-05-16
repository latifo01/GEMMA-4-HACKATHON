from time import perf_counter
from typing import Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends

from apps.backend.config import Settings, get_settings


router = APIRouter(tags=["health"])


async def check_ollama_available(settings: Settings) -> bool:
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_health_timeout_seconds) as client:
            response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
    except httpx.HTTPError:
        return False

    return response.status_code == 200


def check_rag_index_available(settings: Settings) -> bool:
    return settings.chroma_path.exists() and settings.chroma_path.is_dir() and any(settings.chroma_path.iterdir())


def check_database_available(settings: Settings) -> bool:
    return settings.db_path.parent.exists()


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    started_at = perf_counter()
    request_id = str(uuid4())

    online_model_available = settings.google_ai_api_key is not None
    offline_model_available = await check_ollama_available(settings)

    if online_model_available:
        selected_model_mode = "online"
        selected_model_name = settings.gemma_online_model
    elif offline_model_available:
        selected_model_mode = "offline"
        selected_model_name = settings.gemma_offline_model
    else:
        selected_model_mode = "unavailable"
        selected_model_name = None

    duration_ms = round((perf_counter() - started_at) * 1000)

    return {
        "data": {
            "status": "ok",
            "version": settings.app_version,
            "online_model_available": online_model_available,
            "offline_model_available": offline_model_available,
            "selected_model_mode": selected_model_mode,
            "selected_model_name": selected_model_name,
            "rag_index_available": check_rag_index_available(settings),
            "database_available": check_database_available(settings),
        },
        "meta": {
            "request_id": request_id,
            "model_mode": selected_model_mode,
            "duration_ms": duration_ms,
        },
    }
