from __future__ import annotations

import asyncio
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
        temperature: float | None = 0.2,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"

        timeout = httpx.Timeout(self.settings.request_timeout_s)
        temperature_fallback_used = False
        response: httpx.Response | None = None

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                attempt = 0
                while True:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )

                    body_lower = response.text.lower()
                    if (
                        response.status_code == 400
                        and "temperature" in payload
                        and "temperature" in body_lower
                        and not temperature_fallback_used
                    ):
                        payload.pop("temperature", None)
                        temperature_fallback_used = True
                        continue

                    retryable = response.status_code == 429 or response.status_code >= 500
                    if retryable and attempt < self.settings.model_retries:
                        delay = min(2**attempt, 4)
                        retry_after = response.headers.get("retry-after")
                        if retry_after:
                            try:
                                delay = min(max(float(retry_after), 0.0), 10.0)
                            except ValueError:
                                pass
                        attempt += 1
                        await asyncio.sleep(delay)
                        continue
                    break
        except httpx.HTTPError as exc:
            raise LLMError(f"Model endpoint request failed: {exc}") from exc

        if response is None:
            raise LLMError("Model endpoint did not return a response.")

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
