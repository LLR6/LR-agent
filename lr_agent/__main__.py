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
        response = await agent.run(text, session_id=session_id, mode=mode)
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
