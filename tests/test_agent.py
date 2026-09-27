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
        return {"content": "done"}


@pytest.mark.asyncio
async def test_agent_executes_tool_and_returns_answer(tmp_path: Path) -> None:
    settings = Settings(
        workspace=tmp_path / "workspace",
        database=tmp_path / "memory.db",
        max_steps=4,
    )
    settings.ensure_dirs()
    agent = Agent(
        settings,
        FakeLLM(),
        MemoryStore(settings.database),
        ToolRegistry(settings),
    )

    response = await agent.run("create a file", mode="coder")

    assert response.answer == "done"
    assert response.steps[0].tool == "write_file"
    assert response.steps[0].ok is True
    assert (settings.workspace / "hello.txt").read_text() == "hi"
