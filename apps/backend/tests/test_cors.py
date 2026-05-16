from fastapi.testclient import TestClient

from apps.backend.config import get_settings
from apps.backend.main import create_app


def test_frontend_origin_is_allowed_for_preflight(monkeypatch) -> None:
    origins = "http://localhost:5173,https://gemma-4-hackathon.vercel.app"
    monkeypatch.setenv("FRONTEND_ORIGIN", origins)
    get_settings.cache_clear()

    try:
        client = TestClient(create_app())

        for origin in origins.split(","):
            response = client.options(
                "/health",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "bypass-tunnel-reminder",
                },
            )

            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == origin
    finally:
        get_settings.cache_clear()
