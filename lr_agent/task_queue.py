from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from .agent import Agent
from .memory import MemoryStore
from .models import ChatRequest, ChatResponse


class EventBroker:
    def __init__(self, history_limit: int = 200):
        self.history_limit = history_limit
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._history: dict[str, list[dict[str, Any]]] = defaultdict(list)

    async def publish(self, task_id: str, event: dict[str, Any]) -> None:
        history = self._history[task_id]
        history.append(event)
        if len(history) > self.history_limit:
            del history[:-self.history_limit]

        for queue in list(self._subscribers.get(task_id, ())):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass

    def subscribe(self, task_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        self._subscribers[task_id].add(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        subscribers = self._subscribers.get(task_id)
        if not subscribers:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._subscribers.pop(task_id, None)

    def history(self, task_id: str) -> list[dict[str, Any]]:
        return list(self._history.get(task_id, ()))


class TaskManager:
    def __init__(self, agent: Agent, memory: MemoryStore):
        self.agent = agent
        self.memory = memory
        self.events = EventBroker()
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self.memory.mark_incomplete_tasks_interrupted()

    def submit(self, request: ChatRequest) -> str:
        task_id = self.memory.create_task_record(
            message=request.message,
            mode=request.mode,
            session_id=request.session_id,
        )
        handle = asyncio.create_task(
            self._execute(task_id, request),
            name=f"lr-agent-task-{task_id}",
        )
        self._tasks[task_id] = handle
        return task_id

    async def _execute(self, task_id: str, request: ChatRequest) -> None:
        self.memory.update_task_record(task_id, status="running")
        await self.events.publish(
            task_id,
            {
                "type": "status",
                "task_id": task_id,
                "status": "running",
            },
        )

        async def event_sink(event: dict[str, Any]) -> None:
            payload = dict(event)
            payload.setdefault("task_id", task_id)
            await self.events.publish(task_id, payload)

        try:
            response: ChatResponse = await self.agent.run(
                request.message,
                session_id=request.session_id,
                mode=request.mode,
                event_sink=event_sink,
            )
            result = response.model_dump()
            self.memory.update_task_record(
                task_id,
                status=response.status,
                session_id=response.session_id,
                run_id=response.run_id,
                result=result,
            )
            await self.events.publish(
                task_id,
                {
                    "type": "finished",
                    "task_id": task_id,
                    "status": response.status,
                    "result": result,
                },
            )
        except asyncio.CancelledError:
            self.memory.update_task_record(
                task_id,
                status="cancelled",
                error="Task was cancelled.",
            )
            await self.events.publish(
                task_id,
                {
                    "type": "finished",
                    "task_id": task_id,
                    "status": "cancelled",
                    "error": "Task was cancelled.",
                },
            )
            raise
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self.memory.update_task_record(
                task_id,
                status="failed",
                error=error,
            )
            await self.events.publish(
                task_id,
                {
                    "type": "finished",
                    "task_id": task_id,
                    "status": "failed",
                    "error": error,
                },
            )
        finally:
            self._tasks.pop(task_id, None)

    def get(self, task_id: str) -> dict[str, Any] | None:
        return self.memory.get_task_record(task_id)

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.memory.list_task_records(limit)

    async def cancel(self, task_id: str) -> bool:
        handle = self._tasks.get(task_id)
        if handle is None or handle.done():
            return False
        handle.cancel()
        try:
            await handle
        except asyncio.CancelledError:
            pass
        return True
