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
    verify: bool = True


class GeneCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    instruction: str = Field(min_length=1, max_length=10_000)
    applicability: list[str] = []
    exclusions: list[str] = []
    verifier: list[dict[str, Any]] = []
    parent_ids: list[str] = []


class GeneAblationRequest(BaseModel):
    task: str = Field(min_length=1, max_length=100_000)
    trials: int = Field(default=1, ge=1, le=5)
    falsification: bool = False


class GeneContaminateRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    propagate: bool = True


class ForgeGeneImportRequest(BaseModel):
    candidate_id: str | None = None
    parent_ids: list[str] = []


class InvariantCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    commands: list[dict[str, Any]]
    source_gene_id: str | None = None


class ChronoForgeStartRequest(BaseModel):
    task: str = Field(default="", max_length=100_000)
    tournament_id: str | None = None
    candidate_id: str | None = None
    generations: int | None = Field(default=None, ge=1, le=10)
    trajectories: int | None = Field(default=None, ge=1, le=6)


class ChronoForgeStartResponse(BaseModel):
    run_id: str
    status: str


class FutureObservationRequest(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    note: str = Field(default="", max_length=5000)
    source: str = Field(default="reality", min_length=1, max_length=200)


class SessionSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
