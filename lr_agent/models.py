from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=100_000)
    session_id: str | None = None
    mode: Literal["general", "coder", "research"] = "general"


class AgentStep(BaseModel):
    index: int
    tool: str
    arguments: dict[str, Any]
    ok: bool
    preview: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    steps: list[AgentStep]


class SessionSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
