import json

import pytest

from lr_agent.research_artifacts import build_artifact_bundle, canonical_json_sha256


MANIFEST = {
    "schema": "lr-agent-research-run/v1",
    "snapshot": {"repository": "owner/repo", "commit": "abcdef012345"},
    "task": {"id": "t1", "description": "test task"},
    "agent": {"model": "model-x", "scaffold": "LR-Agent"},
    "condition": {"name": "baseline"},
    "repeats": 3,
    "outputs": {"directory": "artifacts/t1"},
}


def test_canonical_manifest_hash_ignores_key_order():
    reordered = json.loads(json.dumps(MANIFEST))
    reordered = dict(reversed(list(reordered.items())))
    assert canonical_json_sha256(MANIFEST) == canonical_json_sha256(reordered)


def test_bundle_hashes_retained_artifacts(tmp_path):
    a = tmp_path / "result.json"
    b = tmp_path / "trace.txt"
    a.write_text('{"ok":true}\n', encoding="utf-8")
    b.write_text("tool trace\n", encoding="utf-8")
    bundle = build_artifact_bundle(MANIFEST, [b, a])
    assert bundle["schema"] == "lr-agent-artifact-bundle/v1"
    assert len(bundle["manifest_sha256"]) == 64
    assert len(bundle["bundle_sha256"]) == 64
    assert [x["path"] for x in bundle["artifacts"]] == sorted([str(a), str(b)])
    assert all(len(x["sha256"]) == 64 for x in bundle["artifacts"])


def test_bundle_rejects_duplicate_paths(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        build_artifact_bundle(MANIFEST, [p, p])
