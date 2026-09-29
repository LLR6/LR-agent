from __future__ import annotations

import pytest

from lr_agent.research_manifest import ResearchManifestError, validate_research_manifest


BASE = {
    "schema": "lr-agent-research-run/v1",
    "snapshot": {"repository": "owner/repo", "commit": "abcdef012345"},
    "task": {"id": "t1", "description": "test task"},
    "agent": {"model": "model-x", "scaffold": "LR-Agent"},
    "condition": {"name": "baseline"},
    "repeats": 3,
    "outputs": {"directory": "artifacts/t1"},
}


def test_research_manifest_accepts_minimal_reproducible_run():
    assert validate_research_manifest(dict(BASE))["repeats"] == 3


def test_research_manifest_rejects_secret_values():
    item = dict(BASE)
    item["agent"] = {"model": "model-x", "scaffold": "LR-Agent", "api_key": "secret-value"}
    with pytest.raises(ResearchManifestError):
        validate_research_manifest(item)


def test_research_manifest_requires_concrete_snapshot():
    item = dict(BASE)
    item["snapshot"] = {"repository": "owner/repo", "commit": "main"}
    with pytest.raises(ResearchManifestError):
        validate_research_manifest(item)
