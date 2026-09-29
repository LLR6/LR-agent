from __future__ import annotations

from typing import Any


SECRET_KEYS = {"api_key", "apikey", "token", "password", "secret", "access_token"}


class ResearchManifestError(ValueError):
    pass


def _require_text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResearchManifestError(f"{path} must be a non-empty string")
    return value.strip()


def _scan_secrets(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key).lower()
            if key_text in SECRET_KEYS and child not in (None, "", "[REDACTED]"):
                raise ResearchManifestError(
                    f"{path}.{key}: secret-like values must not be stored in research manifests"
                )
            _scan_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_secrets(child, f"{path}[{index}]")


def validate_research_manifest(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ResearchManifestError("manifest must be a JSON object")
    if data.get("schema") != "lr-agent-research-run/v1":
        raise ResearchManifestError("unsupported research manifest schema")

    snapshot = data.get("snapshot")
    if not isinstance(snapshot, dict):
        raise ResearchManifestError("snapshot must be an object")
    _require_text(snapshot.get("repository"), "snapshot.repository")
    commit = _require_text(snapshot.get("commit"), "snapshot.commit")
    if len(commit) < 7:
        raise ResearchManifestError("snapshot.commit must identify a concrete commit")

    task = data.get("task")
    if not isinstance(task, dict):
        raise ResearchManifestError("task must be an object")
    _require_text(task.get("id"), "task.id")
    _require_text(task.get("description"), "task.description")

    agent = data.get("agent")
    if not isinstance(agent, dict):
        raise ResearchManifestError("agent must be an object")
    _require_text(agent.get("model"), "agent.model")
    _require_text(agent.get("scaffold"), "agent.scaffold")

    condition = data.get("condition")
    if not isinstance(condition, dict):
        raise ResearchManifestError("condition must be an object")
    _require_text(condition.get("name"), "condition.name")

    repeats = data.get("repeats")
    if not isinstance(repeats, int) or repeats < 1:
        raise ResearchManifestError("repeats must be an integer >= 1")

    outputs = data.get("outputs")
    if not isinstance(outputs, dict):
        raise ResearchManifestError("outputs must be an object")
    _require_text(outputs.get("directory"), "outputs.directory")

    _scan_secrets(data)
    return data
