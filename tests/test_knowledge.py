from pathlib import Path

from lr_agent.knowledge import KnowledgeIndex


def test_workspace_knowledge_index_and_search(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "alpha.py").write_text(
        "def calculate_checksum(data):\n"
        "    return sum(data) % 256\n"
        "\n"
        "# packet checksum verification\n",
        encoding="utf-8",
    )
    (workspace / "notes.md").write_text(
        "# Notes\nUse calculate_checksum before sending packets.\n",
        encoding="utf-8",
    )
    binary = workspace / "blob.bin"
    binary.write_bytes(b"abc\x00def")

    index = KnowledgeIndex(workspace, tmp_path / "knowledge.db")
    stats = index.rebuild()

    assert stats["indexed_files"] == 2
    assert stats["skipped_files"] == 1

    result = index.search("calculate_checksum")
    assert result["results"]
    paths = {item["path"] for item in result["results"]}
    assert "alpha.py" in paths or "notes.md" in paths

    persisted = index.stats()
    assert persisted["files"] == 2
    assert persisted["chunks"] >= 2


def test_knowledge_excludes_dependency_directories(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "node_modules" / "pkg").mkdir(parents=True)
    (workspace / "node_modules" / "pkg" / "index.js").write_text(
        "secret_dependency_marker",
        encoding="utf-8",
    )
    (workspace / "app.py").write_text("visible_marker", encoding="utf-8")

    index = KnowledgeIndex(workspace, tmp_path / "knowledge.db")
    index.rebuild()

    assert index.search("visible_marker")["results"]
    assert index.search("secret_dependency_marker")["results"] == []
