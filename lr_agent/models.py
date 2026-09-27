from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=100_000)
    session_id: str | None = None
    mode: Literal["general", "coder", "research"] = "general"


class PlanItem(BaseModel):
    action: str
    success_condition: str = ""


class AgentPlan(BaseModel):
    goal: str
    steps: list[PlanItem]
    success_criteria: list[str] = []


class ReviewReport(BaseModel):
    passed: bool
    summary: str
    problems: list[str] = []
    next_actions: list[str] = []


class AgentStep(BaseModel):
    index: int
    tool: str
    arguments: dict[str, Any]
    ok: bool
    preview: str


class ChatResponse(BaseModel):
    session_id: str
    run_id: str
    status: str
    answer: str
    steps: list[AgentStep]
    plan: AgentPlan | None = None
    review: ReviewReport | None = None


class ApprovalDecision(BaseModel):
    approved: bool


class TaskStartResponse(BaseModel):
    task_id: str
    status: str


class TaskSummary(BaseModel):
    id: str
    status: str
    message: str
    mode: str
    session_id: str | None = None
    run_id: str | None = None
    error: str | None = None
    created_at: str
    updated_at: str


class UniverseStartRequest(BaseModel):
    task: str = Field(min_length=1, max_length=100_000)
    candidates: int = Field(default=3, ge=2, le=4)
    evolve: bool = False


class UniverseStartResponse(BaseModel):
    tournament_id: str
    status: str


class UniversePromoteRequest(BaseModel):
    candidate_id: str | None = None


class SessionSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
