from __future__ import annotations

import asyncio
import hmac
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

from .agent import Agent
from .chronoforge import ChronoForge, ChronoForgeError
from .config import Settings
from .genome import CausalGenomeEngine, GenomeError
from .llm import LLMError, OpenAICompatibleClient
from .memory import MemoryStore
from .models import (
    ApprovalDecision,
    ChatRequest,
    ChatResponse,
    ChronoForgeStartRequest,
    ChronoForgeStartResponse,
    ForgeGeneImportRequest,
    GeneAblationRequest,
    GeneContaminateRequest,
    GeneCreateRequest,
    FutureObservationRequest,
    InvariantCreateRequest,
    SessionSummary,
    TaskStartResponse,
    UniversePromoteRequest,
    UniverseStartRequest,
    UniverseStartResponse,
)
from .task_queue import TaskManager
from .tools import ToolRegistry
from .universes import UniverseError, UniverseLab


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.ensure_dirs()

    memory = MemoryStore(settings.database)
    llm = OpenAICompatibleClient(settings)
    tools = ToolRegistry(settings)
    agent = Agent(settings, llm, memory, tools)
    task_manager = TaskManager(agent, memory)
    universe_lab = UniverseLab(settings)
    genome = CausalGenomeEngine(
        settings,
        universe_lab=universe_lab,
    )
    chronoforge = ChronoForge(
        settings,
        universe_lab=universe_lab,
    )

    app = FastAPI(title="LR-Agent", version="1.0.0")
    web_index = Path(__file__).with_name("web") / "index.html"

    def token_valid(candidate: str | None) -> bool:
        if not settings.web_token:
            return True
        return bool(candidate) and hmac.compare_digest(candidate, settings.web_token)

    @app.middleware("http")
    async def require_api_token(request: Request, call_next):
        if not settings.web_token or request.url.path in {"/", "/favicon.ico"}:
            return await call_next(request)

        authorization = request.headers.get("authorization", "")
        candidate = (
            authorization[7:].strip()
            if authorization.lower().startswith("bearer ")
            else None
        )
        if not token_valid(candidate):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid LR-Agent web token"},
            )
        return await call_next(request)

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
            "max_concurrent_tasks": settings.max_concurrent_tasks,
            "approval_mode": settings.normalized_approval_mode,
            "web_auth_enabled": bool(settings.web_token),
        }

    @app.post("/api/tasks", response_model=TaskStartResponse)
    async def create_task(request: ChatRequest) -> TaskStartResponse:
        task_id = task_manager.submit(request)
        return TaskStartResponse(task_id=task_id, status="queued")

    @app.get("/api/tasks")
    async def tasks(limit: int = 50) -> list[dict[str, object]]:
        safe_limit = min(max(limit, 1), 200)
        return task_manager.list(safe_limit)

    @app.get("/api/tasks/{task_id}")
    async def task_detail(task_id: str) -> dict[str, object]:
        item = task_manager.get(task_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return item

    @app.get("/api/tasks/{task_id}/approvals")
    async def task_approvals(task_id: str) -> list[dict[str, object]]:
        if task_manager.get(task_id) is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task_manager.approvals(task_id)

    @app.post("/api/tasks/{task_id}/approvals/{approval_id}")
    async def decide_task_approval(
        task_id: str,
        approval_id: str,
        decision: ApprovalDecision,
    ) -> dict[str, object]:
        if task_manager.get(task_id) is None:
            raise HTTPException(status_code=404, detail="Task not found")
        accepted = task_manager.decide_approval(
            task_id,
            approval_id,
            approved=decision.approved,
        )
        if not accepted:
            raise HTTPException(
                status_code=409,
                detail="Approval is no longer pending or does not belong to this task",
            )
        return {
            "task_id": task_id,
            "approval_id": approval_id,
            "approved": decision.approved,
        }

    @app.post("/api/tasks/{task_id}/cancel")
    async def cancel_task(task_id: str) -> dict[str, object]:
        if task_manager.get(task_id) is None:
            raise HTTPException(status_code=404, detail="Task not found")
        cancelled = await task_manager.cancel(task_id)
        return {"task_id": task_id, "cancelled": cancelled}

    @app.websocket("/ws/tasks/{task_id}")
    async def task_events(websocket: WebSocket, task_id: str) -> None:
        if not token_valid(websocket.query_params.get("token")):
            await websocket.close(code=4401)
            return
        if task_manager.get(task_id) is None:
            await websocket.close(code=4404)
            return

        await websocket.accept()
        queue = task_manager.events.subscribe(task_id)
        history = task_manager.events.history(task_id)
        for event in history:
            await websocket.send_json(event)

        try:
            while True:
                event = await queue.get()
                await websocket.send_json(event)
                if event.get("type") == "finished":
                    break
        except WebSocketDisconnect:
            pass
        finally:
            task_manager.events.unsubscribe(task_id, queue)

    @app.get("/api/knowledge/stats")
    async def knowledge_stats() -> dict[str, object]:
        return await asyncio.to_thread(tools.knowledge.stats)

    @app.post("/api/knowledge/rebuild")
    async def knowledge_rebuild() -> dict[str, object]:
        return await tools.rebuild_knowledge()

    @app.get("/api/knowledge/search")
    async def knowledge_search(q: str, limit: int = 8) -> dict[str, object]:
        if not q.strip():
            raise HTTPException(status_code=400, detail="q cannot be empty")
        safe_limit = min(max(limit, 1), 50)
        return await tools.search_knowledge(q, safe_limit)

    @app.post("/api/chronoforge", response_model=ChronoForgeStartResponse)
    async def start_chronoforge(
        request: ChronoForgeStartRequest,
    ) -> ChronoForgeStartResponse:
        try:
            item = chronoforge.start(
                task=request.task,
                tournament_id=request.tournament_id,
                candidate_id=request.candidate_id,
                generations=request.generations,
                trajectories=request.trajectories,
            )
        except (ChronoForgeError, UniverseError, ValueError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return ChronoForgeStartResponse(
            run_id=str(item["id"]),
            status=str(item["status"]),
        )

    @app.get("/api/chronoforge")
    async def chronoforge_runs(limit: int = 100) -> list[dict[str, object]]:
        return chronoforge.list(min(max(limit, 1), 500))

    @app.get("/api/chronoforge/calibration")
    async def chronoforge_calibration() -> dict[str, object]:
        return chronoforge.calibration()

    @app.post("/api/chronoforge/observations")
    async def chronoforge_observation(
        request: FutureObservationRequest,
    ) -> dict[str, object]:
        try:
            return chronoforge.observe_future(
                category=request.category,
                note=request.note,
                source=request.source,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/chronoforge/{run_id}")
    async def chronoforge_run(run_id: str) -> dict[str, object]:
        item = chronoforge.get(run_id)
        if item is None:
            raise HTTPException(status_code=404, detail="ChronoForge run not found")
        return item

    @app.post("/api/chronoforge/{run_id}/cancel")
    async def cancel_chronoforge(run_id: str) -> dict[str, object]:
        if chronoforge.get(run_id) is None:
            raise HTTPException(status_code=404, detail="ChronoForge run not found")
        return {
            "run_id": run_id,
            "cancelled": await chronoforge.cancel(run_id),
        }

    @app.post("/api/universes", response_model=UniverseStartResponse)
    async def start_universe_tournament(
        request: UniverseStartRequest,
    ) -> UniverseStartResponse:
        item = universe_lab.start(
            request.task,
            candidates=request.candidates,
            evolve=request.evolve,
        )
        return UniverseStartResponse(
            tournament_id=str(item["id"]),
            status=str(item["status"]),
        )

    @app.get("/api/universes")
    async def universe_tournaments(limit: int = 30) -> list[dict[str, object]]:
        return universe_lab.list(min(max(limit, 1), 100))

    @app.get("/api/universes/{tournament_id}")
    async def universe_tournament(tournament_id: str) -> dict[str, object]:
        try:
            return universe_lab.get(tournament_id)
        except UniverseError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/universes/{tournament_id}/promote")
    async def promote_universe_candidate(
        tournament_id: str,
        request: UniversePromoteRequest,
    ) -> dict[str, object]:
        try:
            result = await universe_lab.promote(
                tournament_id,
                candidate_id=request.candidate_id,
                verify=request.verify,
            )
        except UniverseError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if not result.get("ok"):
            raise HTTPException(status_code=409, detail=result)
        return result

    @app.get("/api/genome/stats")
    async def genome_stats() -> dict[str, object]:
        return genome.stats()

    @app.get("/api/genome/genes")
    async def genome_genes(
        status: str | None = None,
        kind: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        return genome.store.list_genes(
            status=status,
            kind=kind,
            limit=min(max(limit, 1), 500),
        )

    @app.post("/api/genome/genes")
    async def create_genome_gene(
        request: GeneCreateRequest,
    ) -> dict[str, object]:
        try:
            return genome.create_gene(
                name=request.name,
                instruction=request.instruction,
                applicability=request.applicability,
                exclusions=request.exclusions,
                verifier=request.verifier,
                parent_ids=request.parent_ids,
                provenance={"source": "manual_api"},
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/genome/genes/{gene_id}")
    async def genome_gene(gene_id: str) -> dict[str, object]:
        item = genome.store.get_gene(gene_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Gene not found")
        item["evidence"] = genome.store.evidence_for_gene(gene_id, limit=200)
        return item

    @app.post("/api/genome/genes/{gene_id}/experiments")
    async def start_genome_experiment(
        gene_id: str,
        request: GeneAblationRequest,
    ) -> dict[str, object]:
        if genome.store.get_gene(gene_id) is None:
            raise HTTPException(status_code=404, detail="Gene not found")
        try:
            return genome.start_ablation(
                gene_id,
                request.task,
                trials=request.trials,
                falsification=request.falsification,
            )
        except (GenomeError, ValueError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/genome/jobs")
    async def genome_jobs(limit: int = 100) -> list[dict[str, object]]:
        return genome.list_jobs(min(max(limit, 1), 500))

    @app.get("/api/genome/jobs/{job_id}")
    async def genome_job(job_id: str) -> dict[str, object]:
        item = genome.get_job(job_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Genome experiment not found")
        return item

    @app.post("/api/genome/jobs/{job_id}/cancel")
    async def cancel_genome_job(job_id: str) -> dict[str, object]:
        if genome.get_job(job_id) is None:
            raise HTTPException(status_code=404, detail="Genome experiment not found")
        return {
            "job_id": job_id,
            "cancelled": await genome.cancel_job(job_id),
        }

    @app.post("/api/genome/genes/{gene_id}/contaminate")
    async def contaminate_gene(
        gene_id: str,
        request: GeneContaminateRequest,
    ) -> dict[str, object]:
        if genome.store.get_gene(gene_id) is None:
            raise HTTPException(status_code=404, detail="Gene not found")
        return genome.contaminate(
            gene_id,
            reason=request.reason,
            propagate=request.propagate,
        )

    @app.post("/api/universes/{tournament_id}/gene")
    async def import_forge_gene(
        tournament_id: str,
        request: ForgeGeneImportRequest,
    ) -> dict[str, object]:
        try:
            return genome.import_forge_winner(
                tournament_id,
                candidate_id=request.candidate_id,
                parent_ids=request.parent_ids,
            )
        except (GenomeError, UniverseError, ValueError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/invariants")
    async def invariants(
        status: str | None = "active",
        limit: int = 200,
    ) -> list[dict[str, object]]:
        return genome.store.list_invariants(
            status=status,
            limit=min(max(limit, 1), 500),
        )

    @app.post("/api/invariants")
    async def create_invariant(
        request: InvariantCreateRequest,
    ) -> dict[str, object]:
        try:
            return genome.register_invariant(
                name=request.name,
                description=request.description,
                commands=request.commands,
                source_gene_id=request.source_gene_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/invariants/check")
    async def check_invariants() -> dict[str, object]:
        return await genome.check_invariants()

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

    @app.get("/api/runs/{run_id}/snapshots")
    async def run_snapshots(run_id: str) -> list[dict[str, object]]:
        item = memory.get_run(run_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Run not found")
        snapshots = memory.list_run_snapshots(run_id)
        return [
            {
                "path": snapshot["path"],
                "original_kind": snapshot["original_kind"],
                "original_hash": snapshot["original_hash"],
                "final_kind": snapshot["final_kind"],
                "final_hash": snapshot["final_hash"],
                "created_at": snapshot["created_at"],
            }
            for snapshot in snapshots
        ]

    @app.post("/api/runs/{run_id}/rollback")
    async def rollback_run(run_id: str) -> dict[str, object]:
        item = memory.get_run(run_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if item.get("status") == "running":
            raise HTTPException(
                status_code=409,
                detail="Cannot roll back a run while it is still running",
            )
        return await agent.journal.rollback(run_id)

    @app.post("/api/runs/{run_id}/resume-task", response_model=TaskStartResponse)
    async def resume_run_task(run_id: str) -> TaskStartResponse:
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
        task_id = task_manager.submit(
            ChatRequest(
                message=prompt,
                session_id=str(item["session_id"]),
                mode=str(item["mode"]),
            )
        )
        return TaskStartResponse(task_id=task_id, status="queued")

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
