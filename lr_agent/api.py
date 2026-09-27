from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .agent import Agent
from .config import Settings
from .llm import LLMError, OpenAICompatibleClient
from .memory import MemoryStore
from .models import ChatRequest, ChatResponse, SessionSummary
from .tools import ToolRegistry


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.ensure_dirs()

    memory = MemoryStore(settings.database)
    llm = OpenAICompatibleClient(settings)
    tools = ToolRegistry(settings)
    agent = Agent(settings, llm, memory, tools)

    app = FastAPI(title="LR-Agent", version="0.2.0")
    web_index = Path(__file__).with_name("web") / "index.html"

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(web_index)

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        return {
            "ok": True,
            "model": settings.model,
            "base_url": settings.base_url,
            "workspace": str(settings.workspace.resolve()),
            "max_steps": settings.max_steps,
        }

    @app.get("/api/sessions", response_model=list[SessionSummary])
    async def sessions() -> list[dict[str, str]]:
        return memory.list_sessions()

    @app.get("/api/runs")
    async def runs(limit: int = 50) -> list[dict[str, object]]:
        safe_limit = min(max(limit, 1), 200)
        return memory.list_runs(safe_limit)

    @app.get("/api/runs/{run_id}")
    async def run_detail(run_id: str) -> dict[str, object]:
        item = memory.get_run(run_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return item

    @app.post("/api/runs/{run_id}/resume", response_model=ChatResponse)
    async def resume_run(run_id: str) -> ChatResponse:
        item = memory.get_run(run_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Run not found")

        evidence = {
            "previous_run_id": run_id,
            "previous_status": item.get("status"),
            "original_task": item.get("task"),
            "plan": item.get("plan"),
            "review": item.get("review"),
            "steps": (item.get("steps") or [])[-20:],
            "previous_answer": item.get("answer"),
        }
        prompt = (
            "Resume this previous LR-Agent run. Re-check current workspace state before "
            "assuming earlier state is still valid. Continue unresolved work, use tools "
            "for verification, and do not merely summarize the old run.\n\n"
            + json.dumps(evidence, ensure_ascii=False)
        )
        try:
            return await agent.run(
                prompt,
                session_id=str(item["session_id"]),
                mode=str(item["mode"]),
            )
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.get("/api/sessions/{session_id}/messages")
    async def session_messages(session_id: str) -> list[dict[str, str]]:
        if not memory.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        return memory.get_messages(session_id)

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        try:
            return await agent.run(
                request.message,
                session_id=request.session_id,
                mode=request.mode,
            )
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"{type(exc).__name__}: {exc}",
            ) from exc

    return app


app = create_app()
