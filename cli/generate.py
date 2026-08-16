"""
BharatBuild CLI — Project Generation
========================================
Streams AI code generation from the backend with a rich live display.

Public API
----------
    run_generation(app, prompt)       — interactive REPL entry point
    generate_headless(config, prompt) — non-interactive / CI entry point
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from cli.app import BharatBuildCLI

from cli.config import CLIConfig

console = Console()

# ── generation phases & colors ───────────────────────────────────────────────

_PHASE_STYLE: dict[str, str] = {
    "classify":   "dim cyan",
    "status":     "cyan",
    "planning":   "yellow",
    "thinking":   "blue",
    "writing":    "green",
    "file":       "bold green",
    "build":      "magenta",
    "run":        "magenta",
    "fix":        "red",
    "preview":    "bold green",
    "complete":   "bold green",
    "error":      "bold red",
    "text":       "white",
}

_PHASE_ICON: dict[str, str] = {
    "classify":   "🔍",
    "planning":   "📋",
    "thinking":   "🤔",
    "writing":    "✍",
    "file":       "📄",
    "build":      "🔨",
    "run":        "▶",
    "fix":        "🔧",
    "preview":    "🌐",
    "complete":   "✅",
    "error":      "✗",
    "status":     "⟳",
    "text":       "",
}


# ── GenerationSession tracks live state ─────────────────────────────────────

class GenerationSession:
    """Mutable state accumulated during one generation stream."""

    def __init__(self, prompt: str):
        self.prompt      = prompt
        self.project_id: Optional[str] = None
        self.files_done: list[str]     = []
        self.preview_url: Optional[str] = None
        self.errors: list[str]          = []
        self.start_time  = time.time()
        self.phase       = "starting"
        self.log_lines: list[str]       = []

    @property
    def elapsed(self) -> str:
        s = int(time.time() - self.start_time)
        return f"{s // 60:02d}:{s % 60:02d}"


# ── main entry points ────────────────────────────────────────────────────────

async def run_generation(app: "BharatBuildCLI", prompt: str) -> None:
    """Stream-generate a project and update app state."""
    from cli.client import BharatBuildClient, APIError
    from cli.auth import AuthManager

    AuthManager.require()

    session = GenerationSession(prompt)

    console.print()
    console.print(Rule("[bold cyan]BharatBuild AI — Generating[/bold cyan]", style="cyan"))
    console.print(f"[dim]Prompt:[/dim] {prompt}")
    console.print()

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )
    task_id = progress.add_task("[cyan]Generating…", total=None)

    with progress:
        try:
            async with BharatBuildClient(app.config) as client:

                # 1. Classify the prompt to pick the right endpoint
                classification = await client.classify_prompt(prompt)
                progress.update(task_id, description=f"[cyan]Mode: {classification}")

                # 2. Stream generation
                payload = _build_payload(app, prompt, classification)
                endpoint = _pick_endpoint(classification)

                async for event in client.stream_sse(endpoint, payload):
                    _handle_event(event, session, progress, task_id)

                    # Store project_id so app knows the active project
                    if session.project_id and not app.current_project_id:
                        app.current_project_id = session.project_id

        except APIError as exc:
            console.print(f"\n[red]✗ Generation failed: {exc.detail}[/red]")
            return
        except asyncio.CancelledError:
            console.print("\n[yellow]⚠ Generation cancelled.[/yellow]")
            return

    _print_summary(session)

    # Attach to app conversation so follow-up questions have context
    if session.files_done:
        app.messages.append(
            type("Message", (), {  # lightweight stand-in
                "role": "assistant",
                "content": f"Generated project with {len(session.files_done)} files.",
                "tool_calls": [],
                "token_usage": None,
            })()
        )


async def generate_headless(config: CLIConfig, prompt: str) -> None:
    """Non-interactive generation — prints JSON events to stdout."""
    import json
    from cli.client import BharatBuildClient, APIError

    async with BharatBuildClient(config) as client:
        classification = await client.classify_prompt(prompt)
        payload  = _build_payload_from_config(config, prompt, classification)
        endpoint = _pick_endpoint(classification)

        try:
            async for event in client.stream_sse(endpoint, payload):
                print(json.dumps(event), flush=True)
        except APIError as exc:
            print(json.dumps({"type": "error", "detail": exc.detail}))


# ── helpers ───────────────────────────────────────────────────────────────────

def _pick_endpoint(classification: str) -> str:
    """Map prompt classification to the correct streaming endpoint."""
    mapping = {
        "project_request": "/bolt/chat/stream",
        "small_task":      "/bolt/chat/stream",
        "general_question":"/streaming/stream",
        "debug":           "/streaming/stream",
    }
    return mapping.get(classification, "/bolt/chat/stream")


def _build_payload(app: "BharatBuildCLI", prompt: str, classification: str) -> dict:
    return {
        "message":    prompt,
        "project_id": app.current_project_id or "",
        "files":      [],
        "model":      app.config.model,
        "mode":       classification,
    }


def _build_payload_from_config(config: CLIConfig, prompt: str, classification: str) -> dict:
    return {
        "message": prompt,
        "files":   [],
        "model":   config.model,
        "mode":    classification,
    }


def _handle_event(
    event:    dict,
    session:  GenerationSession,
    progress: Progress,
    task_id:  TaskID,
) -> None:
    """Route a single SSE event to the correct display handler."""
    etype = event.get("type", "text")
    data  = event.get("data", event)

    if etype == "status":
        msg = data.get("message", str(data)) if isinstance(data, dict) else str(data)
        session.phase = "status"
        progress.update(task_id, description=f"[cyan]⟳ {msg}")

    elif etype in ("planning", "thinking"):
        msg = data.get("message", str(data)) if isinstance(data, dict) else str(data)
        session.phase = etype
        progress.update(task_id, description=f"[yellow]{_PHASE_ICON[etype]} {msg[:70]}")

    elif etype == "file":
        path = (data.get("path", "") if isinstance(data, dict) else "")
        lang = (data.get("language", "") if isinstance(data, dict) else "")
        content = (data.get("content", "") if isinstance(data, dict) else str(data))
        session.files_done.append(path)
        _print_file_block(path, lang, content)
        progress.update(
            task_id,
            description=f"[green]📄 {path}",
            advance=1,
            completed=len(session.files_done),
        )

    elif etype in ("build", "run"):
        line = data.get("line", data.get("message", str(data))) if isinstance(data, dict) else str(data)
        session.log_lines.append(line)
        session.phase = etype
        _print_log_line(etype, line)

    elif etype in ("preview_ready", "preview"):
        url = data.get("url", data.get("preview_url", "")) if isinstance(data, dict) else str(data)
        session.preview_url = url
        console.print(f"\n[bold green]🌐 Preview ready:[/bold green] [underline]{url}[/underline]")

    elif etype == "project_created":
        pid = data.get("project_id", "") if isinstance(data, dict) else ""
        if pid:
            session.project_id = pid
            console.print(f"[dim]Project ID: {pid}[/dim]")

    elif etype == "error":
        msg = data.get("message", str(data)) if isinstance(data, dict) else str(data)
        session.errors.append(msg)
        console.print(f"[red]✗ {msg}[/red]")

    elif etype == "complete":
        session.phase = "complete"
        progress.update(task_id, description="[bold green]✅ Complete")

    elif etype == "text":
        # Raw streamed text — print inline
        text = data.get("content", data.get("text", str(data))) if isinstance(data, dict) else str(data)
        console.print(text, end="", highlight=False)

    # unknown events are silently dropped


def _print_file_block(path: str, lang: str, content: str) -> None:
    """Print a generated file with syntax highlighting."""
    if not path:
        return
    ext_to_lang = {
        ".py":    "python",   ".ts": "typescript", ".tsx": "typescript",
        ".js":    "javascript",".jsx":"javascript",
        ".html":  "html",     ".css": "css",       ".json": "json",
        ".yaml":  "yaml",     ".yml": "yaml",      ".toml": "toml",
        ".md":    "markdown", ".sh":  "bash",       ".sql":  "sql",
        ".rs":    "rust",     ".go":  "go",         ".java": "java",
    }
    ext  = Path(path).suffix.lower()
    lang = lang or ext_to_lang.get(ext, "text")

    console.print()
    console.print(f"  [bold green]📄 {path}[/bold green]")
    if content and len(content) < 4000:
        try:
            syn = Syntax(
                content, lang,
                theme="monokai",
                line_numbers=False,
                word_wrap=True,
            )
            console.print(Panel(syn, border_style="dim", padding=(0, 1)))
        except Exception:
            console.print(Panel(content[:500] + ("…" if len(content) > 500 else ""),
                                border_style="dim"))
    elif content:
        console.print(f"  [dim]{len(content):,} bytes[/dim]")


def _print_log_line(phase: str, line: str) -> None:
    """Print a build/run log line."""
    line = line.rstrip()
    if not line:
        return
    icon  = _PHASE_ICON.get(phase, "")
    style = "magenta" if phase == "build" else "cyan"
    console.print(f"  [{style}]{icon}  {line}[/{style}]")


def _print_summary(session: GenerationSession) -> None:
    """Print generation summary after the stream ends."""
    console.print()
    console.print(Rule("[bold green]Generation Complete[/bold green]", style="green"))

    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="dim",   justify="right")
    t.add_column(style="white bold")

    t.add_row("Time",    session.elapsed)
    t.add_row("Files",   str(len(session.files_done)))

    if session.project_id:
        t.add_row("Project", session.project_id)

    if session.errors:
        t.add_row("Errors", Text(str(len(session.errors)), style="red"))

    if session.preview_url:
        t.add_row("Preview", Text(session.preview_url, style="underline green"))

    console.print(Panel(t, border_style="green"))

    if session.files_done:
        console.print("\n[dim]Generated files:[/dim]")
        for f in session.files_done:
            console.print(f"  [green]•[/green] {f}")

    console.print()
    console.print("[dim]Next steps:[/dim]  "
                  "[cyan]/run[/cyan] to start the sandbox  |  "
                  "[cyan]/fix[/cyan] to auto-fix errors  |  "
                  "[cyan]/ieee[/cyan] to generate documents")
    console.print()
