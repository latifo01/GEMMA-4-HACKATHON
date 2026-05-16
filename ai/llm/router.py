from collections.abc import AsyncIterator
from dataclasses import dataclass
import json
from typing import Any, Literal, Protocol

from apps.backend.config import Settings


ModelModePreference = Literal["auto", "online", "offline"]


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model_mode: str
    model_name: str
    parsed_json: dict[str, Any] | None = None
    raw: dict[str, Any] | None = None


class ModelUnavailableError(Exception):
    code = "MODEL_UNAVAILABLE"

    def __init__(self, requested_mode: ModelModePreference = "auto") -> None:
        self.requested_mode = requested_mode
        super().__init__(f"No model provider is available for requested mode: {requested_mode}.")


class LLMClient(Protocol):
    model_mode: str
    model_name: str

    async def healthcheck(self) -> bool:
        ...

    async def generate_text(self, prompt: str, temperature: float = 0.0) -> LLMResponse:
        ...

    async def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> LLMResponse:
        ...

    def stream_text(self, prompt: str, temperature: float = 0.0) -> AsyncIterator[str]:
        ...


class LLMRouter:
    def __init__(
        self,
        settings: Settings,
        online_client: LLMClient | None = None,
        offline_client: LLMClient | None = None,
        preferred_mode: ModelModePreference = "auto",
    ) -> None:
        self.settings = settings
        self.online_client = online_client
        self.offline_client = offline_client
        self.preferred_mode = preferred_mode

    def set_preferred_mode(self, preferred_mode: ModelModePreference) -> None:
        self.preferred_mode = preferred_mode

    def _online_client(self) -> LLMClient | None:
        if self.settings.google_ai_api_key is None:
            return None
        if self.online_client is not None:
            return self.online_client

        from ai.llm.gemma_online import GemmaOnlineClient

        self.online_client = GemmaOnlineClient(
            api_key=self.settings.google_ai_api_key,
            model_name=self.settings.gemma_online_model,
        )
        return self.online_client

    def _offline_client(self) -> LLMClient:
        if self.offline_client is not None:
            return self.offline_client

        from ai.llm.gemma_offline import GemmaOfflineClient

        self.offline_client = GemmaOfflineClient(
            base_url=self.settings.ollama_base_url,
            model_name=self.settings.gemma_offline_model,
            timeout_seconds=self.settings.ollama_health_timeout_seconds,
            generation_timeout_seconds=self.settings.ollama_generation_timeout_seconds,
        )
        return self.offline_client

    async def select_client(self) -> LLMClient:
        if self.preferred_mode == "online":
            online_client = self._online_client()
            if online_client is not None and await self._is_available(online_client):
                return online_client
            raise ModelUnavailableError("online")

        if self.preferred_mode == "offline":
            offline_client = self._offline_client()
            if await self._is_available(offline_client):
                return offline_client
            raise ModelUnavailableError("offline")

        online_client = self._online_client()
        if online_client is not None and await self._is_available(online_client):
            return online_client

        offline_client = self._offline_client()
        if await self._is_available(offline_client):
            return offline_client

        raise ModelUnavailableError("auto")

    async def healthcheck(self) -> dict[str, Any]:
        online_client = self._online_client()
        online_available = False
        if online_client is not None:
            online_available = await self._is_available(online_client)

        offline_client = self._offline_client()
        offline_available = await self._is_available(offline_client)

        if online_available:
            selected_mode = "online"
            selected_name = online_client.model_name if online_client is not None else None
        elif offline_available:
            selected_mode = "offline"
            selected_name = offline_client.model_name
        else:
            selected_mode = "unavailable"
            selected_name = None

        return {
            "online_model_available": online_available,
            "offline_model_available": offline_available,
            "selected_model_mode": selected_mode,
            "selected_model_name": selected_name,
        }

    async def generate_text(self, prompt: str, temperature: float = 0.0) -> LLMResponse:
        client = await self.select_client()
        return await client.generate_text(prompt, temperature)

    async def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> LLMResponse:
        client = await self.select_client()
        return await client.generate_json(prompt, response_schema, temperature)

    async def stream_text(self, prompt: str, temperature: float = 0.0) -> AsyncIterator[str]:
        client = await self.select_client()
        async for chunk in client.stream_text(prompt, temperature):
            yield chunk

    async def _is_available(self, client: LLMClient) -> bool:
        try:
            return await client.healthcheck()
        except Exception:
            return False


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    decoder = json.JSONDecoder()

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        if start == -1:
            raise
        parsed, _ = decoder.raw_decode(stripped[start:])

    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object from model output.")
    return parsed
