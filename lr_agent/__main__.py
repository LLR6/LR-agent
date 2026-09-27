from __future__ import annotations

import asyncio

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel

from .agent import Agent
from .api import create_app
from .config import Settings
from .llm import LLMError, OpenAICompatibleClient
from .memory import MemoryStore
from .tools import ToolRegistry

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
