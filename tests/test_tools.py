import asyncio
import sys
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
    assert "+++ b/src/demo.txt" in created["result"]["diff"]

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
    assert "-hello world" in changed["result"]["diff"]
    assert "+hello agent" in changed["result"]["diff"]

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


@pytest.mark.asyncio
async def test_github_write_is_blocked_by_default(registry: ToolRegistry) -> None:
    result = await registry.execute(
        "github_create_issue",
        {"repo": "octocat/Hello-World", "title": "should not be created"},
    )
    assert result["ok"] is False
    assert "GitHub writes are disabled" in result["error"]


@pytest.mark.asyncio
async def test_git_status_and_diff_are_read_only(registry: ToolRegistry) -> None:
    registry.settings.allowed_commands = "git,python"
    init = await registry.execute("run_command", {"argv": ["git", "init"]})
    assert init["ok"] is True
    await registry.execute(
        "write_file",
        {"path": "tracked.txt", "content": "first\n"},
    )
    await registry.execute(
        "run_command",
        {"argv": ["git", "add", "tracked.txt"]},
    )

    staged = await registry.execute("git_diff", {"staged": True})
    assert staged["ok"] is True
    assert "+first" in staged["result"]["stdout"]

    status = await registry.execute("git_status", {})
    assert status["ok"] is True
    assert "tracked.txt" in status["result"]["stdout"]


@pytest.mark.asyncio
async def test_command_cancellation_stops_subprocess(registry: ToolRegistry) -> None:
    registry.settings.allowed_commands = Path(sys.executable).name.replace(".exe", "")
    task = asyncio.create_task(
        registry.execute(
            "run_command",
            {
                "argv": [
                    sys.executable,
                    "-c",
                    "import time; time.sleep(30)",
                ],
                "timeout_s": 60,
            },
        )
    )
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=3)
