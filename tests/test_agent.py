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
