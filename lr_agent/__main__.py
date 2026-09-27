from __future__ import annotations

import asyncio
import shlex

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel

from .agent import Agent
from .api import create_app
from .chronoforge import ChronoForge, ChronoForgeError
from .config import Settings
from .genome import CausalGenomeEngine, GenomeError
from .journal import WorkspaceJournal
from .llm import LLMError, OpenAICompatibleClient
from .memory import MemoryStore
from .tools import ToolRegistry
from .universes import UniverseError, UniverseLab

cli = typer.Typer(help="LR-Agent local autonomous assistant")
console = Console()


async def _terminal_approval(
    tool: str,
    arguments: dict[str, object],
    preview: str,
) -> bool:
    console.print(Panel(preview or str(arguments), title=f"Approval required · {tool}"))
    answer = console.input("[bold yellow]Approve this action? [y/N]: [/bold yellow]").strip().lower()
    return answer in {"y", "yes"}


def _build_agent(settings: Settings) -> Agent:
    settings.ensure_dirs()
    return Agent(
        settings,
        OpenAICompatibleClient(settings),
        MemoryStore(settings.database),
        ToolRegistry(settings),
    )


@cli.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Listen address"),
    port: int = typer.Option(8765, help="Listen port"),
) -> None:
    """Start the local web UI and API."""
    settings = Settings()
    normalized_host = host.strip().lower()
    loopback_hosts = {"127.0.0.1", "localhost", "::1"}
    if (
        normalized_host not in loopback_hosts
        and not settings.web_token
        and not settings.allow_remote_without_token
    ):
        console.print(
            "[red]Refusing to expose LR-Agent without authentication.[/red]\n"
            "Set LR_AGENT_WEB_TOKEN or explicitly set "
            "LR_AGENT_ALLOW_REMOTE_WITHOUT_TOKEN=true."
        )
        raise typer.Exit(code=2)

    app = create_app(settings)
    console.print(f"[bold]LR-Agent[/bold] -> http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


@cli.command()
def chat(
    prompt: str | None = typer.Argument(None, help="Optional one-shot prompt"),
    mode: str = typer.Option("general", help="general | coder | research"),
) -> None:
    """Run a one-shot or interactive terminal chat."""
    settings = Settings()
    agent = _build_agent(settings)

    async def one(text: str, session_id: str | None) -> str:
        response = await agent.run(
            text,
            session_id=session_id,
            mode=mode,
            approval_handler=_terminal_approval,
        )
        if response.steps:
            console.print(
                Panel(
                    "\n".join(
                        f"{step.index}. {step.tool} -> {'OK' if step.ok else 'FAIL'}"
                        for step in response.steps
                    ),
                    title="Tools",
                )
            )
        console.print(Panel(response.answer, title="LR-Agent"))
        return response.session_id

    if prompt:
        asyncio.run(one(prompt, None))
        return

    session_id: str | None = None
    console.print("[bold]Interactive mode[/bold]. Type /exit to quit.")
    while True:
        try:
            text = console.input("[bold cyan]you> [/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower() in {"/exit", "/quit"}:
            break
        try:
            session_id = asyncio.run(one(text, session_id))
        except LLMError as exc:
            console.print(f"[red]{exc}[/red]")


@cli.command("index")
def index_workspace() -> None:
    """Build or rebuild the persistent workspace knowledge index."""
    settings = Settings()
    settings.ensure_dirs()
    tools = ToolRegistry(settings)
    result = asyncio.run(tools.rebuild_knowledge())
    console.print(
        Panel(
            "\n".join(
                [
                    f"files: {result['indexed_files']}",
                    f"chunks: {result['indexed_chunks']}",
                    f"skipped: {result['skipped_files']}",
                    f"fts5: {result['fts_enabled']}",
                    f"embeddings: {result.get('embedded_chunks', 0)}",
                    f"embedding_model: {result.get('embedding_model', 'disabled')}",
                    f"root: {result['root']}",
                ]
            ),
            title="Knowledge index",
        )
    )


@cli.command("search")
def search_knowledge(
    query: str = typer.Argument(..., help="Knowledge search query"),
    limit: int = typer.Option(8, help="Maximum results"),
) -> None:
    """Search the persistent workspace knowledge index."""
    settings = Settings()
    settings.ensure_dirs()
    tools = ToolRegistry(settings)
    result = asyncio.run(
        tools.search_knowledge(query, limit=min(max(limit, 1), 50))
    )
    console.print(f"[bold]mode:[/bold] {result['mode']}")
    if not result["results"]:
        console.print("[yellow]No results.[/yellow]")
        return
    for item in result["results"]:
        console.print(
            Panel(
                item["snippet"],
                title=f"{item['path']}:{item['line_start']}-{item['line_end']}",
            )
        )


@cli.command("forge")
def forge(
    task: str = typer.Argument(..., help="Coding task to solve in parallel shadow universes"),
    candidates: int = typer.Option(3, min=2, max=4, help="Parallel candidate count"),
    evolve: bool = typer.Option(
        False,
        "--evolve",
        help="Run one extra strategy evolved from first-round evidence",
    ),
    promote: bool = typer.Option(
        False,
        "--promote",
        help="Promote the evidence-score winner after confirmation",
    ),
) -> None:
    """Run Counterfactual Forge: isolated competing coding agents + evidence ranking."""
    settings = Settings()
    settings.ensure_dirs()
    lab = UniverseLab(settings)

    console.print(
        Panel(
            (
                f"task: {task}\n"
                f"candidates: {candidates}\n"
                f"evolve: {evolve}\n\n"
                "Each candidate runs in an isolated shadow copy. "
                "Remote writes are blocked in shadow mode."
            ),
            title="Counterfactual Forge",
        )
    )

    tournament = asyncio.run(
        lab.run(task, candidates=candidates, evolve=evolve)
    )
    if tournament["status"] != "completed":
        console.print(f"[red]Forge failed:[/red] {tournament.get('error')}")
        raise typer.Exit(code=1)

    for item in sorted(
        tournament["candidates"],
        key=lambda value: float(value["evidence"]["score"]),
        reverse=True,
    ):
        winner = " ★ WINNER" if item["id"] == tournament["winner_id"] else ""
        evidence = item["evidence"]
        console.print(
            Panel(
                "\n".join(
                    [
                        f"score: {evidence['score']}",
                        f"status: {item['status']}",
                        f"verified checks: {evidence['verification_passes']}",
                        f"tool failures: {evidence['tool_failures']}",
                        f"changed files: {evidence['changed_files']}",
                        f"review passed: {evidence['review_passed']}",
                    ]
                ),
                title=f"{item['strategy']['name']}{winner}",
            )
        )

    console.print(f"tournament_id: [bold]{tournament['id']}[/bold]")
    console.print(f"winner: [bold]{tournament['winner_id']}[/bold]")

    if promote:
        answer = console.input(
            "[bold yellow]Promote the winner into the real workspace? [y/N]: [/bold yellow]"
        ).strip().lower()
        if answer not in {"y", "yes"}:
            console.print("Promotion cancelled. Shadow universes were preserved.")
            return
        result = asyncio.run(lab.promote(tournament["id"]))
        if not result["ok"]:
            console.print("[red]Promotion blocked by workspace conflicts.[/red]")
            for conflict in result["conflicts"]:
                console.print(f"[red]{conflict['path']}[/red]")
            raise typer.Exit(code=2)
        console.print(
            Panel(
                "\n".join(result["applied"]) or "No file changes",
                title="Winner promoted",
            )
        )


@cli.command("forge-list")
def forge_list(limit: int = typer.Option(20, help="Recent tournaments")) -> None:
    """List Counterfactual Forge tournaments."""
    settings = Settings()
    settings.ensure_dirs()
    lab = UniverseLab(settings)
    items = lab.list(limit)
    if not items:
        console.print("[yellow]No forge tournaments yet.[/yellow]")
        return
    for item in items:
        console.print(
            f"[bold]{item['id']}[/bold]  {item['status']}  "
            f"winner={item.get('winner_id') or '-'}  {item['task'][:70]}"
        )


@cli.command("forge-promote")
def forge_promote(
    tournament_id: str = typer.Argument(..., help="Counterfactual tournament id"),
    candidate_id: str | None = typer.Option(
        None,
        help="Candidate id; defaults to evidence-score winner",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Promote one counterfactual candidate after conflict checking."""
    settings = Settings()
    settings.ensure_dirs()
    lab = UniverseLab(settings)
    try:
        item = lab.get(tournament_id)
    except UniverseError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    selected = candidate_id or item.get("winner_id")
    if not yes:
        console.print(
            f"Selected candidate: [bold]{selected}[/bold]\n"
            "Promotion refuses to overwrite files changed since the tournament baseline."
        )
        answer = console.input("[bold]Continue? [y/N]: [/bold]").strip().lower()
        if answer not in {"y", "yes"}:
            console.print("Cancelled.")
            return

    try:
        result = asyncio.run(
            lab.promote(tournament_id, candidate_id=candidate_id)
        )
    except UniverseError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    if not result["ok"]:
        console.print("[red]Promotion blocked by conflicts.[/red]")
        for conflict in result["conflicts"]:
            console.print(f"[red]{conflict['path']}[/red]")
        raise typer.Exit(code=2)

    console.print(
        Panel(
            "\n".join(result["applied"]) or "No file changes",
            title=f"Promoted {result['candidate_id']}",
        )
    )


def _print_chrono_report(report: dict[str, object]) -> None:
    metrics = report.get("metrics") or {}
    half_life = metrics.get("predicted_half_life") or {}
    half_life_text = (
        f">{half_life.get('generation')}"
        if half_life.get("censored")
        else str(half_life.get("generation"))
    )
    console.print(
        Panel(
            "\n".join(
                [
                    f"temporal survival: {metrics.get('temporal_survival')}",
                    f"maintenance cost: {metrics.get('future_maintenance_cost')}",
                    f"option value: {metrics.get('maintenance_option_value')}",
                    f"invariant survival: {metrics.get('invariant_survival')}",
                    f"dependency robustness: {metrics.get('dependency_robustness')}",
                    f"patch surface stability: {metrics.get('patch_surface_stability')}",
                    f"predicted half-life (repo generations): {half_life_text}",
                ]
            ),
            title="ChronoForge Life Report",
        )
    )
    curve = report.get("survival_curve") or []
    if curve:
        console.print(
            "survival curve: "
            + " → ".join(
                f"g{item['generation']}={float(item['survival_rate']):.2f}"
                for item in curve
            )
        )
    deaths = report.get("death_modes") or {}
    if deaths:
        console.print("death modes: " + str(deaths))


@cli.command("chrono")
def chrono(
    task: str = typer.Argument(
        "",
        help="Patch intent / future-aging target. Optional when using a Forge tournament.",
    ),
    tournament_id: str | None = typer.Option(
        None,
        "--tournament-id",
        help="Age a completed Counterfactual Forge tournament candidate.",
    ),
    candidate_id: str | None = typer.Option(
        None,
        "--candidate-id",
        help="Forge candidate id; defaults to winner.",
    ),
    generations: int | None = typer.Option(
        None,
        min=1,
        max=10,
        help="Sequential future generations per trajectory.",
    ),
    trajectories: int | None = typer.Option(
        None,
        min=1,
        max=6,
        help="Independent future timelines.",
    ),
) -> None:
    """Age the current project or a Forge patch through synthetic future generations."""
    settings = Settings()
    settings.ensure_dirs()
    engine = ChronoForge(settings)
    try:
        report = asyncio.run(
            engine.run(
                task=task,
                tournament_id=tournament_id,
                candidate_id=candidate_id,
                generations=generations,
                trajectories=trajectories,
            )
        )
    except (ChronoForgeError, UniverseError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    _print_chrono_report(report)


@cli.command("chrono-list")
def chrono_list(limit: int = typer.Option(30, help="Recent ChronoForge runs")) -> None:
    """List prospective software-aging experiments."""
    settings = Settings()
    settings.ensure_dirs()
    engine = ChronoForge(settings)
    items = engine.list(min(max(limit, 1), 500))
    if not items:
        console.print("[yellow]No ChronoForge runs yet.[/yellow]")
        return
    for item in items:
        metrics = (item.get("report") or {}).get("metrics") or {}
        console.print(
            f"[bold]{item['id']}[/bold]  {item['status']}  "
            f"g={item['generations']} x t={item['trajectories']}  "
            f"survival={metrics.get('temporal_survival', '-')}  "
            f"{item['task'][:70]}"
        )


@cli.command("chrono-show")
def chrono_show(run_id: str = typer.Argument(..., help="ChronoForge run id")) -> None:
    """Show one ChronoForge life report."""
    settings = Settings()
    settings.ensure_dirs()
    engine = ChronoForge(settings)
    item = engine.get(run_id)
    if item is None:
        console.print(f"[red]ChronoForge run not found: {run_id}[/red]")
        raise typer.Exit(code=1)
    console.print(
        Panel(
            (
                f"status: {item['status']}\n"
                f"source: {item['source_type']} {item.get('source_ref') or ''}\n"
                f"task: {item['task']}\n"
                f"error: {item.get('error') or '-'}"
            ),
            title=f"ChronoForge · {run_id}",
        )
    )
    if item.get("report") and item["status"] == "completed":
        _print_chrono_report(item["report"])


@cli.command("chrono-observe")
def chrono_observe(
    category: str = typer.Argument(..., help="Observed future category"),
    note: str = typer.Argument(..., help="What actually changed in the real project"),
    source: str = typer.Option("reality", help="Observation source label"),
) -> None:
    """Feed a real later project event back into the Future Model calibration store."""
    settings = Settings()
    settings.ensure_dirs()
    engine = ChronoForge(settings)
    try:
        observation = engine.observe_future(
            category=category,
            note=note,
            source=source,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2)
    console.print(
        Panel(
            (
                f"id: {observation['id']}\n"
                f"category: {observation['category']}\n"
                f"note: {observation['note']}\n"
                f"calibration: {engine.calibration()['weights']}"
            ),
            title="Future observation recorded",
        )
    )


@cli.command("genome-stats")
def genome_stats() -> None:
    """Show Causal Genome and Invariant DNA statistics."""
    settings = Settings()
    settings.ensure_dirs()
    engine = CausalGenomeEngine(settings)
    stats = engine.stats()
    console.print(Panel(str(stats), title="Causal Genome"))


@cli.command("genome-list")
def genome_list(
    status: str | None = typer.Option(
        None,
        help="Optional status filter: quarantine | active | contested | contaminated | retired",
    ),
    kind: str | None = typer.Option(
        None,
        help="Optional kind filter: strategy | anti",
    ),
    limit: int = typer.Option(50, help="Maximum genes"),
) -> None:
    """List strategy genes and anti-genes."""
    settings = Settings()
    settings.ensure_dirs()
    engine = CausalGenomeEngine(settings)
    items = engine.store.list_genes(
        status=status,
        kind=kind,
        limit=min(max(limit, 1), 500),
    )
    if not items:
        console.print("[yellow]No genes matched.[/yellow]")
        return
    for item in items:
        console.print(
            Panel(
                "\n".join(
                    [
                        f"id: {item['id']}",
                        f"kind/status: {item['kind']} / {item['status']}",
                        f"confidence: {item['confidence']:.3f}",
                        f"effect(avg): {item['average_effect']:.2f}",
                        (
                            "evidence: "
                            f"+{item['positive_count']} "
                            f"-{item['negative_count']} "
                            f"~{item['neutral_count']}"
                        ),
                        f"instruction: {item['instruction'][:500]}",
                    ]
                ),
                title=item["name"],
            )
        )


@cli.command("genome-add")
def genome_add(
    name: str = typer.Argument(..., help="Gene name"),
    instruction: str = typer.Argument(..., help="Strategy instruction"),
    applies_to: list[str] = typer.Option(
        [],
        "--applies-to",
        help="Applicability clue; may be repeated",
    ),
    excludes: list[str] = typer.Option(
        [],
        "--exclude",
        help="Known exclusion/boundary; may be repeated",
    ),
) -> None:
    """Create a quarantined strategy gene manually."""
    settings = Settings()
    settings.ensure_dirs()
    engine = CausalGenomeEngine(settings)
    gene = engine.create_gene(
        name=name,
        instruction=instruction,
        applicability=applies_to,
        exclusions=excludes,
        provenance={"source": "manual_cli"},
    )
    console.print(
        Panel(
            f"id: {gene['id']}\nstatus: {gene['status']}",
            title=f"Gene created · {gene['name']}",
        )
    )


@cli.command("genome-import")
def genome_import(
    tournament_id: str = typer.Argument(..., help="Completed Forge tournament id"),
    candidate_id: str | None = typer.Option(
        None,
        help="Candidate id; defaults to Forge winner",
    ),
) -> None:
    """Import a Forge candidate into genome quarantine without pretending it is causal proof."""
    settings = Settings()
    settings.ensure_dirs()
    engine = CausalGenomeEngine(settings)
    try:
        gene = engine.import_forge_winner(
            tournament_id,
            candidate_id=candidate_id,
        )
    except GenomeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    console.print(
        Panel(
            (
                f"id: {gene['id']}\n"
                f"status: {gene['status']}\n"
                "Forge success is provenance only. Run genome-ablate before activation."
            ),
            title=f"Imported gene · {gene['name']}",
        )
    )


def _print_ablation(result: dict[str, object]) -> None:
    gene = result.get("gene") or {}
    console.print(
        Panel(
            "\n".join(
                [
                    f"gene: {gene.get('name', '-')}",
                    f"status: {gene.get('status', '-')}",
                    f"confidence: {float(gene.get('confidence', 0)):.3f}",
                    f"average effect: {gene.get('average_effect', '-')}",
                    f"trials completed: {result.get('trials_completed')}",
                    f"average trial effect: {result.get('average_trial_effect')}",
                    f"anti-genes created/reused: {len(result.get('anti_genes') or [])}",
                ]
            ),
            title=str(result.get("experiment_type", "ablation")),
        )
    )
    for item in result.get("experiments") or []:
        console.print(
            f"trial {item.get('trial')}: {item.get('status')} "
            f"effect={item.get('effect', '-')} outcome={item.get('outcome', '-')}"
        )


@cli.command("genome-ablate")
def genome_ablate(
    gene_id: str = typer.Argument(..., help="Gene id"),
    task: str = typer.Argument(..., help="Real coding task for treatment-vs-control test"),
    trials: int = typer.Option(1, min=1, max=5, help="Independent ablation trials"),
) -> None:
    """Run a treatment-vs-control Counterfactual Forge ablation for one gene."""
    settings = Settings()
    settings.ensure_dirs()
    engine = CausalGenomeEngine(settings)
    try:
        result = asyncio.run(
            engine.ablate(
                gene_id,
                task,
                trials=trials,
                falsification=False,
            )
        )
    except GenomeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    _print_ablation(result)


@cli.command("genome-falsify")
def genome_falsify(
    gene_id: str = typer.Argument(..., help="Gene id"),
    task: str = typer.Argument(..., help="Task/context used to attack the gene"),
    trials: int = typer.Option(1, min=1, max=5, help="Falsification trials"),
) -> None:
    """Actively try to falsify a strategy gene in counterfactual shadow universes."""
    settings = Settings()
    settings.ensure_dirs()
    engine = CausalGenomeEngine(settings)
    try:
        result = asyncio.run(
            engine.falsify(
                gene_id,
                task,
                trials=trials,
            )
        )
    except GenomeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    _print_ablation(result)


@cli.command("genome-contaminate")
def genome_contaminate(
    gene_id: str = typer.Argument(..., help="Gene id"),
    reason: str = typer.Argument(..., help="Why this gene is no longer trusted"),
    no_propagate: bool = typer.Option(
        False,
        "--no-propagate",
        help="Do not contaminate descendants",
    ),
) -> None:
    """Mark a gene contaminated and, by default, propagate distrust through descendants."""
    settings = Settings()
    settings.ensure_dirs()
    engine = CausalGenomeEngine(settings)
    result = engine.contaminate(
        gene_id,
        reason=reason,
        propagate=not no_propagate,
    )
    console.print(
        Panel(
            "\n".join(result["affected_gene_ids"]),
            title=f"Contaminated · {len(result['affected_gene_ids'])} genes",
        )
    )


@cli.command("invariant-list")
def invariant_list() -> None:
    """List active Invariant DNA."""
    settings = Settings()
    settings.ensure_dirs()
    engine = CausalGenomeEngine(settings)
    items = engine.store.list_invariants(status="active", limit=500)
    if not items:
        console.print("[yellow]No active invariants.[/yellow]")
        return
    for item in items:
        console.print(
            Panel(
                (
                    f"id: {item['id']}\n"
                    f"description: {item['description']}\n"
                    f"commands: {item['commands']}\n"
                    f"last check: {item['last_status'] or 'never'}"
                ),
                title=item["name"],
            )
        )


@cli.command("invariant-add")
def invariant_add(
    name: str = typer.Argument(..., help="Invariant name"),
    description: str = typer.Argument(..., help="What must remain true"),
    command: list[str] = typer.Option(
        ...,
        "--command",
        help='Executable check, e.g. --command "pytest tests/test_auth.py"; repeatable',
    ),
) -> None:
    """Add executable project Invariant DNA."""
    settings = Settings()
    settings.ensure_dirs()
    commands: list[dict[str, object]] = []
    for value in command:
        argv = shlex.split(value)
        if not argv:
            console.print("[red]Invariant command cannot be empty.[/red]")
            raise typer.Exit(code=2)
        commands.append({"argv": argv, "cwd": "."})

    engine = CausalGenomeEngine(settings)
    try:
        invariant = engine.register_invariant(
            name=name,
            description=description,
            commands=commands,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2)
    console.print(
        Panel(
            f"id: {invariant['id']}\ncommands: {invariant['commands']}",
            title=f"Invariant DNA · {invariant['name']}",
        )
    )


@cli.command("invariant-check")
def invariant_check() -> None:
    """Execute all active Invariant DNA checks in the real workspace."""
    settings = Settings()
    settings.ensure_dirs()
    engine = CausalGenomeEngine(settings)
    result = asyncio.run(engine.check_invariants())
    for item in result["results"]:
        state = "[green]PASS[/green]" if item["passed"] else "[red]FAIL[/red]"
        console.print(f"{state}  {item['name']}")
    if result["passed"] is False:
        raise typer.Exit(code=2)


@cli.command("tasks")
def tasks(limit: int = typer.Option(20, help="Number of recent tasks to show")) -> None:
    """Show persisted background tasks."""
    settings = Settings()
    settings.ensure_dirs()
    store = MemoryStore(settings.database)
    items = store.list_task_records(min(max(limit, 1), 200))
    if not items:
        console.print("[yellow]No persisted tasks yet.[/yellow]")
        return
    for item in items:
        console.print(
            f"[bold]{item['id']}[/bold]  {item['status']}  "
            f"{item['mode']}  {item['message'][:80]}"
        )


@cli.command()
def runs(limit: int = typer.Option(20, help="Number of recent runs to show")) -> None:
    """Show persisted agent runs."""
    settings = Settings()
    settings.ensure_dirs()
    store = MemoryStore(settings.database)
    items = store.list_runs(min(max(limit, 1), 200))
    if not items:
        console.print("[yellow]No persisted runs yet.[/yellow]")
        return
    for item in items:
        console.print(
            f"[bold]{item['id']}[/bold]  {item['status']}  "
            f"{item['mode']}  {item['task'][:80]}"
        )


@cli.command()
def resume(run_id: str = typer.Argument(..., help="Persisted run id")) -> None:
    """Resume a previous run using its stored plan and tool evidence."""
    settings = Settings()
    settings.ensure_dirs()
    store = MemoryStore(settings.database)
    item = store.get_run(run_id)
    if item is None:
        console.print(f"[red]Run not found: {run_id}[/red]")
        raise typer.Exit(code=1)

    evidence = {
        "previous_run_id": run_id,
        "previous_status": item.get("status"),
        "original_task": item.get("task"),
        "plan": item.get("plan"),
        "review": item.get("review"),
        "steps": (item.get("steps") or [])[-20:],
        "previous_answer": item.get("answer"),
    }
    import json

    prompt = (
        "Resume this previous LR-Agent run. Re-check current workspace state before "
        "assuming earlier state is still valid. Continue unresolved work, use tools "
        "for verification, and do not merely summarize the old run.\n\n"
        + json.dumps(evidence, ensure_ascii=False)
    )
    agent = Agent(
        settings,
        OpenAICompatibleClient(settings),
        store,
        ToolRegistry(settings),
    )

    async def execute() -> None:
        response = await agent.run(
            prompt,
            session_id=str(item["session_id"]),
            mode=str(item["mode"]),
            approval_handler=_terminal_approval,
        )
        console.print(Panel(response.answer, title=f"LR-Agent · {response.status}"))
        console.print(f"run_id: {response.run_id}")

    try:
        asyncio.run(execute())
    except LLMError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)


@cli.command()
def rollback(
    run_id: str = typer.Argument(..., help="Persisted run id"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Restore direct file-tool changes from a completed run."""
    settings = Settings()
    settings.ensure_dirs()
    store = MemoryStore(settings.database)
    if store.get_run(run_id) is None:
        console.print(f"[red]Run not found: {run_id}[/red]")
        raise typer.Exit(code=1)

    if not yes:
        console.print(
            "[yellow]Rollback covers direct LR-Agent file tools only. "
            "run_command/build-script side effects are not included.[/yellow]"
        )
        answer = console.input("[bold]Continue? [y/N]: [/bold]").strip().lower()
        if answer not in {"y", "yes"}:
            console.print("Cancelled.")
            return

    tools = ToolRegistry(settings)
    journal = WorkspaceJournal(settings, store, tools)
    result = asyncio.run(journal.rollback(run_id))
    if result["rolled_back"]:
        console.print(
            Panel(
                "\n".join(result["restored"]) or "No paths",
                title="Rollback completed",
            )
        )
        return

    console.print(f"[yellow]{result['message']}[/yellow]")
    for conflict in result.get("conflicts", []):
        console.print(
            f"[red]{conflict['path']}[/red] "
            f"expected={conflict['expected_kind']} current={conflict['current_kind']}"
        )
    raise typer.Exit(code=2)


@cli.command()
def doctor() -> None:
    """Check local configuration and verify the model endpoint with a tiny request."""
    settings = Settings()
    settings.ensure_dirs()
    console.print(f"Model: [bold]{settings.model}[/bold]")
    console.print(f"Endpoint: {settings.base_url}")
    console.print(f"Workspace: {settings.workspace.resolve()}")
    console.print(
        "API key: "
        + ("[green]configured[/green]" if settings.api_key else "[yellow]empty[/yellow]")
    )

    async def probe() -> None:
        client = OpenAICompatibleClient(settings)
        message = await client.chat(
            [{"role": "user", "content": "Reply with exactly: OK"}],
            tools=None,
            temperature=0,
        )
        console.print(f"Model response: {message.get('content', '')}")

    try:
        asyncio.run(probe())
        console.print("[green]Doctor check passed.[/green]")
    except Exception as exc:
        console.print(f"[red]Doctor check failed: {type(exc).__name__}: {exc}[/red]")
        raise typer.Exit(code=1)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
