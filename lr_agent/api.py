from __future__ import annotations

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

    app = FastAPI(title="LR-Agent", version="0.1.0")
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
