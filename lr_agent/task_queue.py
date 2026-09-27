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
        max_concurrent = int(
            getattr(getattr(agent, "settings", None), "max_concurrent_tasks", 2)
        )
        self._semaphore = asyncio.Semaphore(max(1, max_concurrent))
        self._approval_futures: dict[str, asyncio.Future[bool]] = {}
        self._approval_tasks: dict[str, str] = {}
        self.approval_timeout_s = float(
            getattr(getattr(agent, "settings", None), "approval_timeout_s", 600.0)
        )
        self.memory.mark_incomplete_tasks_interrupted()
        self.memory.mark_pending_approvals_expired()

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
        acquired = False

        async def event_sink(event: dict[str, Any]) -> None:
            payload = dict(event)
            payload.setdefault("task_id", task_id)
            await self.events.publish(task_id, payload)

        async def approval_handler(
            tool: str,
            arguments: dict[str, Any],
            preview: str,
        ) -> bool:
            return await self.request_approval(
                task_id,
                tool=tool,
                arguments=arguments,
                preview=preview,
            )

        try:
            await self.events.publish(
                task_id,
                {
                    "type": "status",
                    "task_id": task_id,
                    "status": "queued",
                },
            )

            await self._semaphore.acquire()
            acquired = True

            self.memory.update_task_record(task_id, status="running")
            await self.events.publish(
                task_id,
                {
                    "type": "status",
                    "task_id": task_id,
                    "status": "running",
                },
            )

            response: ChatResponse = await self.agent.run(
                request.message,
                session_id=request.session_id,
                mode=request.mode,
                event_sink=event_sink,
                approval_handler=approval_handler,
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
            if acquired:
                self._semaphore.release()

    async def request_approval(
        self,
        task_id: str,
        *,
        tool: str,
        arguments: dict[str, Any],
        preview: str,
    ) -> bool:
        approval_id = self.memory.create_approval(
            task_id=task_id,
            tool=tool,
            arguments=arguments,
            preview=preview,
        )
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()
        self._approval_futures[approval_id] = future
        self._approval_tasks[approval_id] = task_id

        await self.events.publish(
            task_id,
            {
                "type": "approval_required",
                "task_id": task_id,
                "approval": {
                    "id": approval_id,
                    "tool": tool,
                    "arguments": arguments,
                    "preview": preview,
                    "status": "pending",
                },
            },
        )

        status = "denied"
        try:
            approved = await asyncio.wait_for(
                future,
                timeout=self.approval_timeout_s,
            )
            status = "approved" if approved else "denied"
            return approved
        except asyncio.TimeoutError:
            status = "expired"
            return False
        finally:
            self.memory.update_approval_status(approval_id, status)
            self._approval_futures.pop(approval_id, None)
            self._approval_tasks.pop(approval_id, None)
            await self.events.publish(
                task_id,
                {
                    "type": "approval_resolved",
                    "task_id": task_id,
                    "approval_id": approval_id,
                    "status": status,
                },
            )

    def decide_approval(
        self,
        task_id: str,
        approval_id: str,
        *,
        approved: bool,
    ) -> bool:
        item = self.memory.get_approval(approval_id)
        if (
            item is None
            or item["task_id"] != task_id
            or item["status"] != "pending"
        ):
            return False

        future = self._approval_futures.get(approval_id)
        if future is None or future.done():
            return False
        future.set_result(approved)
        return True

    def approvals(self, task_id: str) -> list[dict[str, Any]]:
        return self.memory.list_approvals(task_id)

    def get(self, task_id: str) -> dict[str, Any] | None:
        return self.memory.get_task_record(task_id)

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.memory.list_task_records(limit)

    async def cancel(self, task_id: str) -> bool:
        for approval_id, approval_task_id in list(self._approval_tasks.items()):
            if approval_task_id != task_id:
                continue
            future = self._approval_futures.get(approval_id)
            if future is not None and not future.done():
                future.set_result(False)

        handle = self._tasks.get(task_id)
        if handle is None or handle.done():
            return False
        handle.cancel()
        try:
            await handle
        except asyncio.CancelledError:
            pass
        return True
