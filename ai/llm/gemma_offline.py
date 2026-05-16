import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ai.llm.router import LLMResponse, parse_json_object


class GemmaOfflineClient:
    model_mode = "offline"

    def __init__(
        self,
        base_url: str,
        model_name: str,
        timeout_seconds: float,
        generation_timeout_seconds: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.generation_timeout_seconds = generation_timeout_seconds or timeout_seconds
        self.transport = transport

    async def healthcheck(self) -> bool:
        try:
            async with self._client() as client:
                response = await client.get(f"{self.base_url}/api/tags")
        except httpx.HTTPError:
            return False

        return response.status_code == 200

    async def generate_text(self, prompt: str, temperature: float = 0.0) -> LLMResponse:
        payload = await self._generate(
            {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature},
            }
        )

        return LLMResponse(
            text=str(payload.get("response", "")),
            model_mode=self.model_mode,
            model_name=self.model_name,
            raw=payload,
        )

    async def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> LLMResponse:
        payload = await self._generate(
            {
                "model": self.model_name,
                "prompt": prompt,
                "format": response_schema,
                "stream": False,
                "options": {"temperature": temperature},
            }
        )
        text = str(payload.get("response", ""))

        return LLMResponse(
            text=text,
            model_mode=self.model_mode,
            model_name=self.model_name,
            parsed_json=parse_json_object(text),
            raw=payload,
        )

    async def stream_text(self, prompt: str, temperature: float = 0.0) -> AsyncIterator[str]:
        async with self._client(self.generation_timeout_seconds) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": True,
                    "options": {"temperature": temperature},
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    text = chunk.get("response")
                    if text:
                        yield str(text)

    async def _generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with self._client(self.generation_timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            return response.json()

    def _client(self, timeout_seconds: float | None = None) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=timeout_seconds or self.timeout_seconds, transport=self.transport)
