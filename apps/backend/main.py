from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.backend.config import get_settings
from apps.backend.routers.audio import router as audio_router
from apps.backend.routers.health import router as health_router
from apps.backend.routers.sessions import router as sessions_router
from apps.backend.routers.triage import router as triage_router
from apps.backend.routers.video import router as video_router


def create_app() -> FastAPI:
    settings = get_settings()
    cors_origins = [origin.strip() for origin in settings.frontend_origin.split(",") if origin.strip()]

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "bypass-tunnel-reminder"],
    )
    app.include_router(audio_router)
    app.include_router(health_router)
    app.include_router(sessions_router)
    app.include_router(triage_router)
    app.include_router(video_router)
    return app


app = create_app()
