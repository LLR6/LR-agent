from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .research_manifest import validate_research_manifest


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_artifact_bundle(
    manifest: dict[str, Any],
    artifacts: list[str | Path],
) -> dict[str, Any]:
    validate_research_manifest(manifest)

    entries = []
    seen = set()
    for raw in artifacts:
        path = Path(raw)
        if not path.is_file():
            raise ValueError(f"artifact is not a file: {path}")
        resolved = str(path.resolve())
        if resolved in seen:
            raise ValueError(f"duplicate artifact path: {path}")
        seen.add(resolved)
        entries.append({
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })

    entries.sort(key=lambda x: x["path"])
    return {
        "schema": "lr-agent-artifact-bundle/v1",
        "manifest_sha256": canonical_json_sha256(manifest),
        "artifacts": entries,
        "bundle_sha256": canonical_json_sha256(entries),
    }
