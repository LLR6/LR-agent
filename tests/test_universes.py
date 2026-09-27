from pathlib import Path

import pytest

from lr_agent.config import Settings
from lr_agent.models import AgentStep, ChatResponse, ReviewReport
from lr_agent.tools import ToolRegistry
from lr_agent.universes import UniverseLab


async def fake_runner(settings: Settings, prompt: str) -> ChatResponse:
    target = settings.workspace / "app.py"
    if "Surgical Minimalist" in prompt:
        target.write_text("value = 'surgical-fix'\n", encoding="utf-8")
        steps = [
            AgentStep(
                index=1,
                tool="run_command",
                arguments={"argv": ["pytest"]},
                ok=True,
                preview='{"ok":true,"result":{"returncode":0,"stdout":"1 passed"}}',
            )
        ]
        answer = "surgical candidate verified"
    else:
        target.write_text("value = 'alternate-fix'\n", encoding="utf-8")
        steps = []
        answer = "alternate candidate"

    return ChatResponse(
        session_id="session",
        run_id="run",
        status="completed",
        answer=answer,
        steps=steps,
        plan=None,
        review=ReviewReport(
            passed=True,
            summary="candidate completed",
            problems=[],
            next_actions=[],
        ),
    )


@pytest.mark.asyncio
async def test_counterfactual_tournament_is_isolated_and_promotes_winner(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "app.py"
    source.write_text("value = 'original'\n", encoding="utf-8")

    settings = Settings(
        workspace=workspace,
        database=tmp_path / "memory.db",
        knowledge_database=tmp_path / "knowledge.db",
        universe_root=tmp_path / "universes",
        universe_candidates=2,
    )
    settings.ensure_dirs()
    lab = UniverseLab(settings, agent_runner=fake_runner)

    tournament = await lab.run("fix app", candidates=2, evolve=False)

    assert tournament["status"] == "completed"
    assert tournament["winner_id"] == "surgical"
    assert source.read_text(encoding="utf-8") == "value = 'original'\n"

    surgical = next(
        item for item in tournament["candidates"] if item["id"] == "surgical"
    )
    alternate = next(
        item for item in tournament["candidates"] if item["id"] == "root-cause"
    )
    assert surgical["evidence"]["verification_passes"] == 1
    assert surgical["evidence"]["score"] > alternate["evidence"]["score"]

    promoted = await lab.promote(tournament["id"])
    assert promoted["ok"] is True
    assert promoted["candidate_id"] == "surgical"
    assert source.read_text(encoding="utf-8") == "value = 'surgical-fix'\n"


@pytest.mark.asyncio
async def test_promotion_refuses_to_overwrite_post_tournament_changes(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "app.py"
    source.write_text("value = 'original'\n", encoding="utf-8")

    settings = Settings(
        workspace=workspace,
        database=tmp_path / "memory.db",
        knowledge_database=tmp_path / "knowledge.db",
        universe_root=tmp_path / "universes",
        universe_candidates=2,
    )
    settings.ensure_dirs()
    lab = UniverseLab(settings, agent_runner=fake_runner)
    tournament = await lab.run("fix app", candidates=2, evolve=False)

    source.write_text("value = 'newer-human-change'\n", encoding="utf-8")
    promoted = await lab.promote(tournament["id"])

    assert promoted["ok"] is False
    assert promoted["conflicts"]
    assert promoted["conflicts"][0]["path"] == "app.py"
    assert source.read_text(encoding="utf-8") == "value = 'newer-human-change'\n"


@pytest.mark.asyncio
async def test_shadow_mode_blocks_remote_git_push(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    settings = Settings(
        workspace=workspace,
        database=tmp_path / "memory.db",
        knowledge_database=tmp_path / "knowledge.db",
        shadow_mode=True,
        allowed_commands="git",
    )
    settings.ensure_dirs()
    registry = ToolRegistry(settings)

    result = await registry.execute(
        "run_command",
        {"argv": ["git", "push", "origin", "main"]},
    )

    assert result["ok"] is False
    assert "External write command blocked" in result["error"]
