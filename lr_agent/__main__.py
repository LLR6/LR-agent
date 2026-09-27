from __future__ import annotations

import asyncio

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel

from .agent import Agent
from .api import create_app
from .config import Settings
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
