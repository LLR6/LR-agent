from pathlib import Path

import pytest

from lr_agent.config import Settings
from lr_agent.embeddings import OpenAICompatibleEmbeddingClient


class DummyResponse:
    def __init__(self, status_code, text, data=None, headers=None):
        self.status_code = status_code
        self.text = text
        self._data = data
        self.headers = headers or {}

    def json(self):
        return self._data


class FakeAsyncClient:
    responses = []
    payloads = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers=None, json=None):
        self.__class__.payloads.append((url, headers, json))
        return self.__class__.responses.pop(0)


@pytest.mark.asyncio
async def test_embedding_client_preserves_input_order(monkeypatch, tmp_path: Path) -> None:
    FakeAsyncClient.responses = [
        DummyResponse(
            200,
            "ok",
            {
                "data": [
                    {"index": 1, "embedding": [0.0, 1.0]},
                    {"index": 0, "embedding": [1.0, 0.0]},
                ]
            },
        )
    ]
    FakeAsyncClient.payloads = []
    monkeypatch.setattr("lr_agent.embeddings.httpx.AsyncClient", FakeAsyncClient)

    settings = Settings(
        workspace=tmp_path / "workspace",
        database=tmp_path / "memory.db",
        embedding_base_url="http://embedding.test/v1",
        embedding_api_key="secret",
        embedding_model="embed-test",
    )
    client = OpenAICompatibleEmbeddingClient(settings)
    vectors = await client.embed(["first", "second"])

    assert vectors == [[1.0, 0.0], [0.0, 1.0]]
    url, headers, payload = FakeAsyncClient.payloads[0]
    assert url == "http://embedding.test/v1/embeddings"
    assert headers["Authorization"] == "Bearer secret"
    assert payload["model"] == "embed-test"
    assert payload["input"] == ["first", "second"]


@pytest.mark.asyncio
async def test_embedding_client_retries_server_error(monkeypatch, tmp_path: Path) -> None:
    FakeAsyncClient.responses = [
        DummyResponse(500, "temporary"),
        DummyResponse(
            200,
            "ok",
            {"data": [{"index": 0, "embedding": [1.0, 2.0, 3.0]}]},
        ),
    ]
    FakeAsyncClient.payloads = []
    monkeypatch.setattr("lr_agent.embeddings.httpx.AsyncClient", FakeAsyncClient)

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr("lr_agent.embeddings.asyncio.sleep", no_sleep)

    settings = Settings(
        workspace=tmp_path / "workspace",
        database=tmp_path / "memory.db",
        embedding_base_url="http://embedding.test/v1",
        embedding_model="embed-test",
        model_retries=1,
    )
    vectors = await OpenAICompatibleEmbeddingClient(settings).embed(["hello"])

    assert vectors == [[1.0, 2.0, 3.0]]
    assert len(FakeAsyncClient.payloads) == 2
