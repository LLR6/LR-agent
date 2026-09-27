from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .config import Settings


class EmbeddingError(RuntimeError):
    pass


class OpenAICompatibleEmbeddingClient:
    """Small OpenAI-compatible /embeddings client used by the local knowledge index."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = (
            settings.embedding_base_url.strip() or settings.base_url
        ).rstrip("/")
        self.api_key = settings.embedding_api_key.strip() or settings.api_key
        self.model = settings.embedding_model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        payload: dict[str, Any] = {
            "model": self.model,
            "input": texts,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        timeout = httpx.Timeout(self.settings.request_timeout_s)
        response: httpx.Response | None = None

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                attempt = 0
                while True:
                    response = await client.post(
                        f"{self.base_url}/embeddings",
                        headers=headers,
                        json=payload,
                    )
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
            raise EmbeddingError(f"Embedding endpoint request failed: {exc}") from exc

        if response is None:
            raise EmbeddingError("Embedding endpoint did not return a response.")
        if response.status_code >= 400:
            raise EmbeddingError(
                f"Embedding endpoint returned HTTP {response.status_code}: "
                f"{response.text[:2000]}"
            )

        try:
            data = response.json()
            items = data["data"]
            indexed: list[tuple[int, list[float]]] = []
            for position, item in enumerate(items):
                index = int(item.get("index", position))
                vector = item["embedding"]
                if not isinstance(vector, list) or not vector:
                    raise ValueError("empty embedding vector")
                indexed.append((index, [float(value) for value in vector]))
            indexed.sort(key=lambda pair: pair[0])
            vectors = [vector for _, vector in indexed]
        except (ValueError, KeyError, TypeError) as exc:
            raise EmbeddingError(
                f"Unexpected embedding response: {response.text[:2000]}"
            ) from exc

        if len(vectors) != len(texts):
            raise EmbeddingError(
                f"Embedding count mismatch: requested {len(texts)}, got {len(vectors)}"
            )
        dimensions = len(vectors[0])
        if dimensions == 0 or any(len(vector) != dimensions for vector in vectors):
            raise EmbeddingError("Embedding vectors have inconsistent dimensions.")
        return vectors
