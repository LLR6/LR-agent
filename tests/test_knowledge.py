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


def test_hybrid_search_can_surface_semantic_match(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "network.py").write_text(
        "def verify_packet_checksum(data):\n    return True\n",
        encoding="utf-8",
    )
    (workspace / "database.py").write_text(
        "def open_database_connection():\n    return None\n",
        encoding="utf-8",
    )

    index = KnowledgeIndex(workspace, tmp_path / "knowledge.db")
    index.rebuild()
    chunks = index.embedding_inputs()
    vectors = []
    for item in chunks:
        vector = [1.0, 0.0] if item["path"] == "network.py" else [0.0, 1.0]
        vectors.append((item["id"], vector))
    index.replace_embeddings(model="test-embed", records=vectors)

    result = index.hybrid_search(
        "validate transport integrity",
        [1.0, 0.0],
        model="test-embed",
        limit=1,
        vector_weight=1.0,
    )

    assert result["mode"].startswith("hybrid:")
    assert result["results"][0]["path"] == "network.py"
    assert result["results"][0]["vector_score"] > 0.99


def test_rebuild_clears_stale_embeddings(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "a.txt").write_text("alpha", encoding="utf-8")

    index = KnowledgeIndex(workspace, tmp_path / "knowledge.db")
    index.rebuild()
    chunk = index.embedding_inputs()[0]
    index.replace_embeddings(model="test-embed", records=[(chunk["id"], [1.0, 0.0])])
    assert index.stats()["embeddings"] == 1

    (workspace / "a.txt").write_text("beta", encoding="utf-8")
    index.rebuild()

    assert index.stats()["embeddings"] == 0
