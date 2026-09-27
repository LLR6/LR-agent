from pathlib import Path

import pytest

from lr_agent.config import Settings
from lr_agent.llm import OpenAICompatibleClient


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
        self.__class__.payloads.append(json.copy())
        return self.__class__.responses.pop(0)


@pytest.mark.asyncio
async def test_temperature_compatibility_fallback(monkeypatch, tmp_path: Path) -> None:
    FakeAsyncClient.responses = [
        DummyResponse(400, "Unsupported parameter: temperature"),
        DummyResponse(
            200,
            "ok",
            {"choices": [{"message": {"role": "assistant", "content": "OK"}}]},
        ),
    ]
    FakeAsyncClient.payloads = []
    monkeypatch.setattr("lr_agent.llm.httpx.AsyncClient", FakeAsyncClient)

    settings = Settings(
        workspace=tmp_path / "workspace",
        database=tmp_path / "memory.db",
        api_key="test",
    )
    result = await OpenAICompatibleClient(settings).chat(
        [{"role": "user", "content": "hi"}],
        temperature=0.2,
    )

    assert result["content"] == "OK"
    assert "temperature" in FakeAsyncClient.payloads[0]
    assert "temperature" not in FakeAsyncClient.payloads[1]


@pytest.mark.asyncio
async def test_retry_on_server_error(monkeypatch, tmp_path: Path) -> None:
    FakeAsyncClient.responses = [
        DummyResponse(500, "temporary"),
        DummyResponse(
            200,
            "ok",
            {"choices": [{"message": {"role": "assistant", "content": "OK"}}]},
        ),
    ]
    FakeAsyncClient.payloads = []
    monkeypatch.setattr("lr_agent.llm.httpx.AsyncClient", FakeAsyncClient)

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr("lr_agent.llm.asyncio.sleep", no_sleep)

    settings = Settings(
        workspace=tmp_path / "workspace",
        database=tmp_path / "memory.db",
        api_key="test",
        model_retries=1,
    )
    result = await OpenAICompatibleClient(settings).chat(
        [{"role": "user", "content": "hi"}],
        temperature=None,
    )

    assert result["content"] == "OK"
    assert len(FakeAsyncClient.payloads) == 2
