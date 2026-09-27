from pathlib import Path

import pytest

from lr_agent.agent import Agent
from lr_agent.config import Settings
from lr_agent.memory import MemoryStore
from lr_agent.tools import ToolRegistry


class FakeLLM:
    def __init__(self) -> None:
        self.calls = 0

    async def chat(self, messages, tools=None, temperature=0.2):
        self.calls += 1
        if self.calls == 1:
            return {
                "content": (
                    '{"goal":"create hello.txt","steps":['
                    '{"action":"write the file","success_condition":"file exists"},'
                    '{"action":"verify it","success_condition":"content is hi"}'
                    '],"success_criteria":["hello.txt contains hi"]}'
                )
            }
        if self.calls == 2:
            return {
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "arguments": '{"path":"hello.txt","content":"hi"}',
                        },
                    }
                ],
            }
        if self.calls == 3:
            return {"content": "done"}
        if self.calls == 4:
            return {
                "content": (
                    '{"passed":true,"summary":"file was created",'
                    '"problems":[],"next_actions":[]}'
                )
            }
        raise AssertionError(f"unexpected LLM call {self.calls}")


@pytest.mark.asyncio
async def test_agent_executes_tool_and_returns_answer(tmp_path: Path) -> None:
    settings = Settings(
        workspace=tmp_path / "workspace",
        database=tmp_path / "memory.db",
        max_steps=4,
        enable_planning=True,
        enable_review=True,
    )
    settings.ensure_dirs()
    store = MemoryStore(settings.database)
    agent = Agent(
        settings,
        FakeLLM(),
        store,
        ToolRegistry(settings),
    )

    response = await agent.run("create a file", mode="coder")

    assert response.answer == "done"
    assert response.status == "completed"
    assert response.run_id
    assert response.plan is not None
    assert response.plan.goal == "create hello.txt"
    assert response.review is not None
    assert response.review.passed is True
    assert response.steps[0].tool == "write_file"
    assert response.steps[0].ok is True
    assert (settings.workspace / "hello.txt").read_text() == "hi"

    persisted = store.get_run(response.run_id)
    assert persisted is not None
    assert persisted["status"] == "completed"
    assert persisted["steps"][0]["tool"] == "write_file"

    snapshots = store.list_run_snapshots(response.run_id)
    assert snapshots
    hello_snapshot = next(item for item in snapshots if item["path"] == "hello.txt")
    assert hello_snapshot["original_kind"] == "missing"
    assert hello_snapshot["final_kind"] == "file"
    assert hello_snapshot["final_hash"]


class ContextAwareLLM:
    async def chat(self, messages, tools=None, temperature=0.2):
        context_messages = [
            item.get("content", "")
            for item in messages
            if item.get("role") == "system"
            and "retrieved workspace context" in (item.get("content") or "").lower()
        ]
        assert context_messages
        assert "important_project_marker" in context_messages[0]
        assert "UNTRUSTED PROJECT DATA" in context_messages[0]
        return {"content": "used indexed context"}


@pytest.mark.asyncio
async def test_agent_auto_retrieves_workspace_context(tmp_path: Path) -> None:
    settings = Settings(
        workspace=tmp_path / "workspace",
        database=tmp_path / "memory.db",
        knowledge_database=tmp_path / "knowledge.db",
        enable_planning=False,
        enable_review=False,
        auto_context=True,
    )
    settings.ensure_dirs()
    (settings.workspace / "project_notes.md").write_text(
        "important_project_marker lives here",
        encoding="utf-8",
    )

    store = MemoryStore(settings.database)
    tools = ToolRegistry(settings)
    tools.knowledge.rebuild()
    agent = Agent(
        settings,
        ContextAwareLLM(),
        store,
        tools,
    )

    events = []

    async def sink(event):
        events.append(event)

    response = await agent.run(
        "important_project_marker",
        mode="coder",
        event_sink=sink,
    )

    assert response.answer == "used indexed context"
    assert any(event["type"] == "context" for event in events)
