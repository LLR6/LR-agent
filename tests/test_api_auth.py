from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from lr_agent.api import create_app
from lr_agent.config import Settings


def _settings(tmp_path: Path, *, token: str = "") -> Settings:
    return Settings(
        workspace=tmp_path / "workspace",
        database=tmp_path / "memory.db",
        knowledge_database=tmp_path / "knowledge.db",
        web_token=token,
    )


def test_api_token_protects_api_but_not_index(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path, token="secret-token"))
    client = TestClient(app)

    assert client.get("/").status_code == 200

    denied = client.get("/api/health")
    assert denied.status_code == 401

    allowed = client.get(
        "/api/health",
        headers={"Authorization": "Bearer secret-token"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["web_auth_enabled"] is True


def test_websocket_requires_token_before_task_lookup(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path, token="secret-token"))
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/tasks/does-not-exist"):
            pass
    assert exc.value.code == 4401

    with pytest.raises(WebSocketDisconnect) as exc2:
        with client.websocket_connect(
            "/ws/tasks/does-not-exist?token=secret-token"
        ):
            pass
    assert exc2.value.code == 4404


def test_auth_is_optional_for_default_local_mode(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path, token=""))
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["web_auth_enabled"] is False
