from pathlib import Path

import pytest

from lr_agent.config import Settings
from lr_agent.journal import WorkspaceJournal
from lr_agent.memory import MemoryStore
from lr_agent.tools import ToolRegistry


def _components(tmp_path: Path):
    settings = Settings(
        workspace=tmp_path / "workspace",
        database=tmp_path / "memory.db",
        knowledge_database=tmp_path / "knowledge.db",
        enable_run_snapshots=True,
        snapshot_max_file_bytes=1024 * 1024,
    )
    settings.ensure_dirs()
    memory = MemoryStore(settings.database)
    tools = ToolRegistry(settings)
    journal = WorkspaceJournal(settings, memory, tools)
    session_id = memory.create_session("rollback test")
    run_id = memory.start_run(
        session_id,
        mode="coder",
        task="edit files",
        plan=None,
    )
    return settings, memory, tools, journal, run_id


@pytest.mark.asyncio
async def test_rollback_restores_existing_file(tmp_path: Path) -> None:
    _settings, memory, tools, journal, run_id = _components(tmp_path)
    target = tools.root / "demo.txt"
    target.write_text("before\n", encoding="utf-8")

    async with tools.mutation_lock:
        paths = journal.capture_before(
            run_id,
            "write_file",
            {"path": "demo.txt", "content": "after\n", "overwrite": True},
        )
        result = await tools.execute(
            "write_file",
            {"path": "demo.txt", "content": "after\n", "overwrite": True},
        )
        assert result["ok"] is True
        journal.capture_after(run_id, paths)

    assert target.read_text(encoding="utf-8") == "after\n"
    rolled = await journal.rollback(run_id)
    assert rolled["rolled_back"] is True
    assert target.read_text(encoding="utf-8") == "before\n"
    assert memory.get_run(run_id)["status"] == "rolled_back"


@pytest.mark.asyncio
async def test_rollback_removes_new_file_and_created_parent(tmp_path: Path) -> None:
    _settings, _memory, tools, journal, run_id = _components(tmp_path)

    arguments = {
        "path": "new/nested.txt",
        "content": "created\n",
    }
    async with tools.mutation_lock:
        paths = journal.capture_before(run_id, "write_file", arguments)
        assert paths == ["new", "new/nested.txt"]
        result = await tools.execute("write_file", arguments)
        assert result["ok"] is True
        journal.capture_after(run_id, paths)

    assert (tools.root / "new/nested.txt").exists()
    rolled = await journal.rollback(run_id)
    assert rolled["rolled_back"] is True
    assert not (tools.root / "new/nested.txt").exists()
    assert not (tools.root / "new").exists()


@pytest.mark.asyncio
async def test_rollback_refuses_when_file_changed_after_run(tmp_path: Path) -> None:
    _settings, _memory, tools, journal, run_id = _components(tmp_path)
    target = tools.root / "demo.txt"
    target.write_text("before", encoding="utf-8")

    args = {"path": "demo.txt", "content": "after", "overwrite": True}
    async with tools.mutation_lock:
        paths = journal.capture_before(run_id, "write_file", args)
        result = await tools.execute("write_file", args)
        assert result["ok"] is True
        journal.capture_after(run_id, paths)

    target.write_text("external-change", encoding="utf-8")

    rolled = await journal.rollback(run_id)
    assert rolled["rolled_back"] is False
    assert rolled["conflicts"]
    assert rolled["conflicts"][0]["path"] == "demo.txt"
    assert target.read_text(encoding="utf-8") == "external-change"


def test_snapshot_limit_blocks_unsafe_large_mutation(tmp_path: Path) -> None:
    settings, memory, tools, _journal, run_id = _components(tmp_path)
    settings.snapshot_max_file_bytes = 4
    target = tools.root / "large.txt"
    target.write_text("12345", encoding="utf-8")
    journal = WorkspaceJournal(settings, memory, tools)

    with pytest.raises(Exception) as exc:
        journal.capture_before(
            run_id,
            "write_file",
            {"path": "large.txt", "content": "changed", "overwrite": True},
        )
    assert "above LR_AGENT_SNAPSHOT_MAX_FILE_BYTES" in str(exc.value)
