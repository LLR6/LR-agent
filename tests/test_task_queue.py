import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from lr_agent.memory import MemoryStore
from lr_agent.models import ChatRequest, ChatResponse
from lr_agent.task_queue import TaskManager


class FakeAgent:
    async def run(
        self,
        message,
        *,
        session_id=None,
        mode="general",
        event_sink=None,
        approval_handler=None,
    ):
        if event_sink:
            await event_sink({"type": "plan", "plan": {"goal": message, "steps": [], "success_criteria": []}})
            await event_sink(
                {
                    "type": "tool_step",
                    "step": {
                        "index": 1,
                        "tool": "fake",
                        "arguments": {},
                        "ok": True,
                        "preview": "ok",
                    },
                }
            )
        await asyncio.sleep(0)
        return ChatResponse(
            session_id=session_id or "session-1",
            run_id="run-1",
            status="completed",
            answer="done",
            steps=[],
            plan=None,
            review=None,
        )


@pytest.mark.asyncio
async def test_background_task_completes_and_persists(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.db")
    manager = TaskManager(FakeAgent(), store)

    task_id = manager.submit(
        ChatRequest(message="background work", mode="coder")
    )

    for _ in range(50):
        item = manager.get(task_id)
        assert item is not None
        if item["status"] == "completed":
            break
        await asyncio.sleep(0.01)
    else:
        pytest.fail("background task did not complete")

    item = manager.get(task_id)
    assert item is not None
    assert item["run_id"] == "run-1"
    assert item["result"]["answer"] == "done"

    events = manager.events.history(task_id)
    assert any(event["type"] == "status" for event in events)
    assert any(event["type"] == "plan" for event in events)
    assert any(event["type"] == "tool_step" for event in events)
    assert events[-1]["type"] == "finished"


def test_restart_marks_incomplete_tasks_interrupted(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.db")
    task_id = store.create_task_record(
        message="unfinished",
        mode="coder",
        session_id=None,
    )
    store.update_task_record(task_id, status="running")

    TaskManager(FakeAgent(), store)

    item = store.get_task_record(task_id)
    assert item is not None
    assert item["status"] == "interrupted"


@pytest.mark.asyncio
async def test_task_approval_roundtrip(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.db")
    manager = TaskManager(FakeAgent(), store)
    task_id = store.create_task_record(
        message="approval test",
        mode="coder",
        session_id=None,
    )

    pending = asyncio.create_task(
        manager.request_approval(
            task_id,
            tool="write_file",
            arguments={"path": "x.txt", "content": "hello"},
            preview="+++ b/x.txt\n+hello",
        )
    )

    approval_id = None
    for _ in range(50):
        items = manager.approvals(task_id)
        if items:
            approval_id = items[0]["id"]
            break
        await asyncio.sleep(0.01)
    assert approval_id is not None

    assert manager.decide_approval(
        task_id,
        approval_id,
        approved=True,
    ) is True
    assert await pending is True

    item = store.get_approval(approval_id)
    assert item is not None
    assert item["status"] == "approved"


class BlockingAgent:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(
            max_concurrent_tasks=1,
            approval_timeout_s=1.0,
        )
        self.gate = asyncio.Event()
        self.started: list[str] = []

    async def run(
        self,
        message,
        *,
        session_id=None,
        mode="general",
        event_sink=None,
        approval_handler=None,
    ):
        self.started.append(message)
        if message == "first":
            await self.gate.wait()
        return ChatResponse(
            session_id=session_id or f"session-{message}",
            run_id=f"run-{message}",
            status="completed",
            answer=message,
            steps=[],
            plan=None,
            review=None,
        )


@pytest.mark.asyncio
async def test_bounded_queue_keeps_second_task_queued_and_cancellable(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.db")
    agent = BlockingAgent()
    manager = TaskManager(agent, store)

    first = manager.submit(ChatRequest(message="first", mode="coder"))
    second = manager.submit(ChatRequest(message="second", mode="coder"))

    for _ in range(50):
        first_item = manager.get(first)
        second_item = manager.get(second)
        if (
            first_item is not None
            and first_item["status"] == "running"
            and second_item is not None
            and second_item["status"] == "queued"
        ):
            break
        await asyncio.sleep(0.01)
    else:
        pytest.fail("expected first task running and second task queued")

    assert await manager.cancel(second) is True
    second_item = manager.get(second)
    assert second_item is not None
    assert second_item["status"] == "cancelled"
    assert agent.started == ["first"]

    agent.gate.set()
    for _ in range(50):
        first_item = manager.get(first)
        if first_item is not None and first_item["status"] == "completed":
            break
        await asyncio.sleep(0.01)
    else:
        pytest.fail("first task did not complete after releasing gate")
