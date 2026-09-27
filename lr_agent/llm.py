from __future__ import annotations

from typing import Any

import httpx

from .config import Settings


class LLMError(RuntimeError):
    pass


class OpenAICompatibleClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.base_url.rstrip("/")

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        *,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"

        timeout = httpx.Timeout(self.settings.request_timeout_s)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise LLMError(f"Model endpoint request failed: {exc}") from exc

        if response.status_code >= 400:
            body = response.text[:2000]
            raise LLMError(
                f"Model endpoint returned HTTP {response.status_code}: {body}"
            )

        try:
            data = response.json()
            message = data["choices"][0]["message"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError(
                f"Unexpected model response: {response.text[:2000]}"
            ) from exc

        if not isinstance(message, dict):
            raise LLMError("Model response message is not an object.")
        return message
