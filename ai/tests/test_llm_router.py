import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from ai.llm.gemma_offline import GemmaOfflineClient
from ai.llm.router import LLMResponse, LLMRouter, ModelUnavailableError, parse_json_object
from apps.backend.config import Settings


class FakeClient:
    def __init__(self, model_mode: str, model_name: str, available: bool) -> None:
        self.model_mode = model_mode
        self.model_name = model_name
        self.available = available
        self.generate_text_calls = 0

    async def healthcheck(self) -> bool:
        return self.available

    async def generate_text(self, prompt: str, temperature: float = 0.0) -> LLMResponse:
        self.generate_text_calls += 1
        return LLMResponse(
            text=f"{self.model_mode}:{prompt}",
            model_mode=self.model_mode,
            model_name=self.model_name,
        )

    async def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> LLMResponse:
        return LLMResponse(
            text='{"ok": true}',
            model_mode=self.model_mode,
            model_name=self.model_name,
            parsed_json={"ok": True},
        )

    async def stream_text(self, prompt: str, temperature: float = 0.0) -> AsyncIterator[str]:
        yield self.model_mode
        yield prompt


def make_settings(tmp_path: Path, google_ai_api_key: str | None) -> Settings:
    return Settings(
        GOOGLE_AI_API_KEY=google_ai_api_key,
        GEMMA_ONLINE_MODEL="online-test",
        OLLAMA_BASE_URL="http://localhost:11434",
        GEMMA_OFFLINE_MODEL="offline-test",
        OLLAMA_HEALTH_TIMEOUT_SECONDS=0.01,
        CHROMA_PATH=tmp_path / "chroma",
        DB_PATH=tmp_path / "imciflow.db",
    )


def test_parse_json_object_accepts_extra_text_around_model_output():
    parsed = parse_json_object('Here is JSON:\n```json\n{"ok": true}\n```\nDone.')

    assert parsed == {"ok": True}


@pytest.mark.asyncio
async def test_router_selects_online_when_api_key_exists_and_healthcheck_succeeds(tmp_path):
    online = FakeClient("online", "online-test", available=True)
    offline = FakeClient("offline", "offline-test", available=True)
    router = LLMRouter(make_settings(tmp_path, google_ai_api_key="secret"), online, offline)

    response = await router.generate_text("hello")

    assert response.model_mode == "online"
    assert response.model_name == "online-test"
    assert response.text == "online:hello"
    assert online.generate_text_calls == 1
    assert offline.generate_text_calls == 0


@pytest.mark.asyncio
async def test_router_falls_back_to_offline_when_online_unavailable(tmp_path):
    online = FakeClient("online", "online-test", available=False)
    offline = FakeClient("offline", "offline-test", available=True)
    router = LLMRouter(make_settings(tmp_path, google_ai_api_key="secret"), online, offline)

    response = await router.generate_text("hello")

    assert response.model_mode == "offline"
    assert response.model_name == "offline-test"
    assert response.text == "offline:hello"


@pytest.mark.asyncio
async def test_router_honors_explicit_offline_preference(tmp_path):
    online = FakeClient("online", "online-test", available=True)
    offline = FakeClient("offline", "offline-test", available=True)
    router = LLMRouter(
        make_settings(tmp_path, google_ai_api_key="secret"),
        online,
        offline,
        preferred_mode="offline",
    )

    response = await router.generate_text("hello")

    assert response.model_mode == "offline"
    assert response.model_name == "offline-test"
    assert online.generate_text_calls == 0


@pytest.mark.asyncio
async def test_router_does_not_fallback_when_explicit_online_is_unavailable(tmp_path):
    online = FakeClient("online", "online-test", available=False)
    offline = FakeClient("offline", "offline-test", available=True)
    router = LLMRouter(
        make_settings(tmp_path, google_ai_api_key="secret"),
        online,
        offline,
        preferred_mode="online",
    )

    with pytest.raises(ModelUnavailableError) as exc_info:
        await router.generate_text("hello")

    assert exc_info.value.requested_mode == "online"
    assert offline.generate_text_calls == 0


@pytest.mark.asyncio
async def test_router_uses_offline_when_online_key_is_missing(tmp_path):
    online = FakeClient("online", "online-test", available=True)
    offline = FakeClient("offline", "offline-test", available=True)
    router = LLMRouter(make_settings(tmp_path, google_ai_api_key=None), online, offline)

    response = await router.generate_json("{}", {"type": "object"})

    assert response.model_mode == "offline"
    assert response.parsed_json == {"ok": True}
    assert online.generate_text_calls == 0


@pytest.mark.asyncio
async def test_router_raises_typed_error_when_no_provider_is_available(tmp_path):
    online = FakeClient("online", "online-test", available=False)
    offline = FakeClient("offline", "offline-test", available=False)
    router = LLMRouter(make_settings(tmp_path, google_ai_api_key="secret"), online, offline)

    with pytest.raises(ModelUnavailableError) as exc_info:
        await router.generate_text("hello")

    assert exc_info.value.code == "MODEL_UNAVAILABLE"


@pytest.mark.asyncio
async def test_router_streams_from_selected_provider(tmp_path):
    online = FakeClient("online", "online-test", available=False)
    offline = FakeClient("offline", "offline-test", available=True)
    router = LLMRouter(make_settings(tmp_path, google_ai_api_key="secret"), online, offline)

    chunks = [chunk async for chunk in router.stream_text("hello")]

    assert chunks == ["offline", "hello"]


@pytest.mark.asyncio
async def test_offline_client_uses_ollama_generate_contract():
    requests: list[dict[str, Any]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "gemma4:e4b-it"}]})

        payload = json.loads(request.content.decode("utf-8"))
        requests.append(payload)
        return httpx.Response(200, json={"response": '{"ok": true}', "done": True})

    transport = httpx.MockTransport(handler)
    client = GemmaOfflineClient(
        base_url="http://ollama.test",
        model_name="gemma4:e4b-it",
        timeout_seconds=1.0,
        transport=transport,
    )

    assert await client.healthcheck() is True
    response = await client.generate_json("return json", {"type": "object"})

    assert response.model_mode == "offline"
    assert response.parsed_json == {"ok": True}
    assert requests[0]["model"] == "gemma4:e4b-it"
    assert requests[0]["prompt"] == "return json"
    assert requests[0]["format"] == {"type": "object"}
    assert requests[0]["stream"] is False
