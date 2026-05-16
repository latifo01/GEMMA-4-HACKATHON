from collections.abc import AsyncIterator
from typing import Any

from ai.llm.router import LLMResponse, parse_json_object


class GemmaOnlineClient:
    model_mode = "online"

    def __init__(self, api_key: str, model_name: str) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self._client: Any | None = None

    async def healthcheck(self) -> bool:
        try:
            await self.generate_text("Reply with OK.", temperature=0.0)
        except Exception:
            return False
        return True

    async def generate_text(self, prompt: str, temperature: float = 0.0) -> LLMResponse:
        response = await self._google_client().aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={"temperature": temperature},
        )

        return LLMResponse(
            text=response.text or "",
            model_mode=self.model_mode,
            model_name=self.model_name,
        )

    async def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> LLMResponse:
        response = await self._google_client().aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "temperature": temperature,
                "response_mime_type": "application/json",
                "response_json_schema": response_schema,
            },
        )
        text = response.text or ""

        return LLMResponse(
            text=text,
            model_mode=self.model_mode,
            model_name=self.model_name,
            parsed_json=parse_json_object(text),
        )

    async def stream_text(self, prompt: str, temperature: float = 0.0) -> AsyncIterator[str]:
        chunks = await self._google_client().aio.models.generate_content_stream(
            model=self.model_name,
            contents=prompt,
            config={"temperature": temperature},
        )
        async for chunk in chunks:
            if chunk.text:
                yield chunk.text

    def _google_client(self) -> Any:
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client
