from pathlib import Path

import pytest

from lr_agent.config import Settings
from lr_agent.tools import ToolRegistry


@pytest.fixture()
def registry(tmp_path: Path) -> ToolRegistry:
    settings = Settings(
        workspace=tmp_path / "workspace",
        database=tmp_path / "data.db",
        allowed_commands="python",
    )
    settings.ensure_dirs()
    return ToolRegistry(settings)


@pytest.mark.asyncio
async def test_file_write_read_replace(registry: ToolRegistry) -> None:
    created = await registry.execute(
        "write_file",
        {"path": "src/demo.txt", "content": "hello world"},
    )
    assert created["ok"] is True

    read = await registry.execute("read_file", {"path": "src/demo.txt"})
    assert read["result"]["content"] == "hello world"

    changed = await registry.execute(
        "replace_in_file",
        {
            "path": "src/demo.txt",
            "old": "world",
            "new": "agent",
            "expected_count": 1,
        },
    )
    assert changed["ok"] is True

    read2 = await registry.execute("read_file", {"path": "src/demo.txt"})
    assert read2["result"]["content"] == "hello agent"


@pytest.mark.asyncio
async def test_workspace_escape_is_blocked(registry: ToolRegistry) -> None:
    result = await registry.execute("read_file", {"path": "../../etc/passwd"})
    assert result["ok"] is False
    assert "escapes workspace" in result["error"]


@pytest.mark.asyncio
async def test_non_allowlisted_command_is_blocked(registry: ToolRegistry) -> None:
    result = await registry.execute(
        "run_command",
        {"argv": ["definitely-not-allowed", "--version"]},
    )
    assert result["ok"] is False
    assert "not allowlisted" in result["error"]


@pytest.mark.asyncio
async def test_search_files(registry: ToolRegistry) -> None:
    await registry.execute(
        "write_file",
        {"path": "src/a.py", "content": "alpha\nneedle here\nomega\n"},
    )
    result = await registry.execute(
        "search_files",
        {"query": "NEEDLE", "path": "src", "glob": "*.py"},
    )
    assert result["ok"] is True
    assert result["result"]["matches"][0]["path"] == "src/a.py"
    assert result["result"]["matches"][0]["line"] == 2
