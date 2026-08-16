"""
BharatBuild CLI — Slash Commands
===================================
All /commands available inside the interactive REPL.

Registry
--------
    COMMANDS : dict[str, Command]   — keyed by name (without leading /)
    SlashCommandHandler.handle()    — dispatch a raw "/foo args" string

Adding a new command
--------------------
    1. Define an async function  _cmd_yourname(app, args)
    2. Register it with @register("yourname", help="…")
"""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Awaitable, Callable, Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from cli.app import BharatBuildCLI

console = Console()

# ── registry ──────────────────────────────────────────────────────────────────

@dataclass
class Command:
    name:    str
    help:    str
    handler: Callable[["BharatBuildCLI", str], Awaitable[None]]
    aliases: List[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


COMMANDS: Dict[str, Command] = {}


def register(name: str, help: str, aliases: Optional[List[str]] = None):
    """Decorator: register an async function as a slash command."""
    def decorator(fn: Callable):
        cmd = Command(name=name, help=help, handler=fn, aliases=aliases or [])
        COMMANDS[name] = cmd
        for alias in cmd.aliases:
            COMMANDS[alias] = cmd
        return fn
    return decorator


# ── handler class ─────────────────────────────────────────────────────────────

class SlashCommandHandler:
    """Dispatch /commands entered in the REPL."""

    def __init__(self, app: "BharatBuildCLI"):
        self.app = app

    async def handle(self, raw: str) -> bool:
        """
        Parse and execute a slash command.
        Returns True if handled (caller should NOT send to AI),
        False if not a slash command.
        """
        raw = raw.strip()
        if not raw.startswith("/"):
            return False

        parts = raw[1:].split(None, 1)
        name  = parts[0].lower()
        args  = parts[1] if len(parts) > 1 else ""

        cmd = COMMANDS.get(name)
        if cmd is None:
            console.print(f"[red]Unknown command: /{name}[/red]  "
                          f"Type [cyan]/help[/cyan] for a list.")
            return True

        try:
            await cmd.handler(self.app, args)
        except Exception as exc:
            console.print(f"[red]Command /{name} failed:[/red] {exc}")

        return True

    @staticmethod
    def is_command(text: str) -> bool:
        return text.strip().startswith("/")


# ── /help ─────────────────────────────────────────────────────────────────────

@register("help", help="Show all available commands", aliases=["h", "?"])
async def _cmd_help(app: "BharatBuildCLI", args: str):
    t = Table(title="Available Slash Commands", box=None, show_header=True,
              header_style="bold cyan")
    t.add_column("Command",     style="cyan bold", no_wrap=True)
    t.add_column("Description", style="white")

    seen: set = set()
    for cmd in sorted(COMMANDS.values(), key=lambda c: c.name):
        if cmd.name in seen:
            continue
        seen.add(cmd.name)
        aliases = f"  [dim]({', '.join('/' + a for a in cmd.aliases)})[/dim]" if cmd.aliases else ""
        t.add_row(f"/{cmd.name}{aliases}", cmd.help)

    console.print()
    console.print(t)
    console.print()
    console.print("[dim]Tip: anything that isn't a /command is sent to the AI.[/dim]")
    console.print()


# ── /clear ────────────────────────────────────────────────────────────────────

@register("clear", help="Clear the conversation history and screen", aliases=["cls"])
async def _cmd_clear(app: "BharatBuildCLI", args: str):
    app.messages.clear()
    app.console.clear()
    app._print_header()
    console.print("[dim]Conversation cleared.[/dim]")


# ── /exit  ────────────────────────────────────────────────────────────────────

@register("exit", help="Exit BharatBuild CLI", aliases=["quit", "q", "bye"])
async def _cmd_exit(app: "BharatBuildCLI", args: str):
    app._running = False
    console.print("\n[dim]Goodbye! 👋[/dim]\n")


# ── /status ───────────────────────────────────────────────────────────────────

@register("status", help="Show current session status (model, tokens, project)")
async def _cmd_status(app: "BharatBuildCLI", args: str):
    from cli.auth import AuthManager

    creds = AuthManager.load()

    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="dim",        justify="right")
    t.add_column(style="bold white")

    t.add_row("Model",    app.config.model)
    t.add_row("API URL",  app.config.api_base_url)
    t.add_row("Turns",    f"{len(app.messages)} messages")
    t.add_row("Tokens",   f"{app.total_tokens:,}")
    t.add_row("Dir",      str(Path(app.config.working_directory).resolve()))

    if creds:
        t.add_row("User",  f"{creds.name} ({creds.email})")
        t.add_row("Plan",  creds.tier.upper())
    else:
        t.add_row("Auth",  "[red]Not logged in[/red]")

    if app.current_project_id:
        t.add_row("Project", app.current_project_id)

    console.print(Panel(t, title="[cyan]Status[/cyan]", border_style="cyan"))


# ── /whoami ───────────────────────────────────────────────────────────────────

@register("whoami", help="Show logged-in account details", aliases=["me"])
async def _cmd_whoami(app: "BharatBuildCLI", args: str):
    from cli.auth import AuthManager, print_whoami
    creds = AuthManager.require()
    print_whoami(creds)


# ── /model ────────────────────────────────────────────────────────────────────

@register("model", help="Switch AI model  (haiku | sonnet | opus)")
async def _cmd_model(app: "BharatBuildCLI", args: str):
    valid = {"haiku", "sonnet", "opus"}
    name  = args.strip().lower()

    if not name:
        console.print(f"[cyan]Current model:[/cyan] [bold]{app.config.model}[/bold]")
        console.print(f"[dim]Available: {', '.join(sorted(valid))}[/dim]")
        return

    if name not in valid:
        console.print(f"[red]Unknown model '{name}'.[/red]  Choose: {', '.join(sorted(valid))}")
        return

    app.config.model = name
    console.print(f"[green]✓ Model switched to [bold]{name}[/bold][/green]")


# ── /mode ─────────────────────────────────────────────────────────────────────

@register("mode", help="Switch permission mode  (ask | auto | deny)")
async def _cmd_mode(app: "BharatBuildCLI", args: str):
    valid = {"ask", "auto", "deny"}
    mode  = args.strip().lower()

    if not mode:
        console.print(f"[cyan]Current mode:[/cyan] [bold]{app.config.permission_mode}[/bold]")
        return

    if mode not in valid:
        console.print(f"[red]Unknown mode '{mode}'.[/red]  Choose: {', '.join(sorted(valid))}")
        return

    app.config.permission_mode = mode
    console.print(f"[green]✓ Permission mode set to [bold]{mode}[/bold][/green]")


# ── /project ──────────────────────────────────────────────────────────────────

@register("project", help="Show or set current project  (/project [id])", aliases=["proj"])
async def _cmd_project(app: "BharatBuildCLI", args: str):
    from cli.client import BharatBuildClient, APIError

    project_id = args.strip()
    if not project_id:
        if app.current_project_id:
            console.print(f"[cyan]Current project:[/cyan] [bold]{app.current_project_id}[/bold]")
        else:
            console.print("[dim]No project selected.  Run [cyan]/projects[/cyan] to list them.[/dim]")
        return

    with console.status(f"[cyan]Fetching project {project_id}…[/cyan]", spinner="dots"):
        try:
            async with BharatBuildClient(app.config) as client:
                proj = await client.get_project(project_id)
        except APIError as exc:
            console.print(f"[red]✗ {exc.detail}[/red]")
            return

    app.current_project_id = project_id
    console.print(f"[green]✓ Switched to project:[/green] [bold]{proj.get('title', project_id)}[/bold]")


# ── /projects ─────────────────────────────────────────────────────────────────

@register("projects", help="List your projects", aliases=["ls", "list"])
async def _cmd_projects(app: "BharatBuildCLI", args: str):
    from cli.projects import list_projects
    await list_projects(app.config)


# ── /new ──────────────────────────────────────────────────────────────────────

@register("new", help="Create & generate a new project  (/new <description>)", aliases=["generate", "gen"])
async def _cmd_new(app: "BharatBuildCLI", args: str):
    if not args.strip():
        console.print("[yellow]Usage:[/yellow]  /new <project description>")
        return
    from cli.generate import run_generation
    await run_generation(app, args.strip())


# ── /fix ──────────────────────────────────────────────────────────────────────

@register("fix", help="Auto-fix errors in the current project")
async def _cmd_fix(app: "BharatBuildCLI", args: str):
    if not app.current_project_id:
        console.print("[yellow]No active project.  Run [cyan]/projects[/cyan] to select one.[/yellow]")
        return

    from cli.client import BharatBuildClient, APIError

    with console.status("[cyan]Requesting auto-fix…[/cyan]", spinner="dots"):
        try:
            async with BharatBuildClient(app.config) as client:
                resp = await client.post(
                    f"/execution/{app.current_project_id}/fix",
                    {"project_id": app.current_project_id, "description": args or "fix all errors"},
                )
            console.print(f"[green]✓ Fix initiated:[/green] {resp.get('message', 'OK')}")
        except APIError as exc:
            console.print(f"[red]✗ {exc.detail}[/red]")


# ── /run ──────────────────────────────────────────────────────────────────────

@register("run", help="Run (execute) the current project in a Docker sandbox")
async def _cmd_run(app: "BharatBuildCLI", args: str):
    if not app.current_project_id:
        console.print("[yellow]No active project.  Select one with [cyan]/project <id>[/cyan].[/yellow]")
        return

    from cli.client import BharatBuildClient, APIError
    console.print(f"[cyan]▶ Starting project {app.current_project_id}…[/cyan]")
    try:
        async with BharatBuildClient(app.config) as client:
            async for event in client.stream_sse(
                f"/execution/{app.current_project_id}/start",
                {"project_id": app.current_project_id},
            ):
                _render_execution_event(event)
    except APIError as exc:
        console.print(f"[red]✗ {exc.detail}[/red]")


# ── /stop ─────────────────────────────────────────────────────────────────────

@register("stop", help="Stop the running Docker container for the current project")
async def _cmd_stop(app: "BharatBuildCLI", args: str):
    if not app.current_project_id:
        console.print("[yellow]No active project.[/yellow]")
        return

    from cli.client import BharatBuildClient, APIError
    with console.status("[cyan]Stopping container…[/cyan]", spinner="dots"):
        try:
            async with BharatBuildClient(app.config) as client:
                resp = await client.post(f"/execution/{app.current_project_id}/stop", {})
            console.print(f"[green]✓ Stopped.[/green] {resp.get('message', '')}")
        except APIError as exc:
            console.print(f"[red]✗ {exc.detail}[/red]")


# ── /preview ──────────────────────────────────────────────────────────────────

@register("preview", help="Get the live preview URL for the current project")
async def _cmd_preview(app: "BharatBuildCLI", args: str):
    if not app.current_project_id:
        console.print("[yellow]No active project.[/yellow]")
        return

    base = app.config.api_base_url.replace("/api/v1", "")
    url  = f"{base}/preview/{app.current_project_id}/"
    console.print(f"[cyan]Preview URL:[/cyan] [bold underline]{url}[/bold underline]")
    try:
        import webbrowser
        webbrowser.open(url)
        console.print("[dim]Opened in browser.[/dim]")
    except Exception:
        pass


# ── /tokens ───────────────────────────────────────────────────────────────────

@register("tokens", help="Show your token balance", aliases=["balance", "credits"])
async def _cmd_tokens(app: "BharatBuildCLI", args: str):
    from cli.client import BharatBuildClient

    with console.status("[cyan]Fetching balance…[/cyan]", spinner="dots"):
        async with BharatBuildClient(app.config) as client:
            data = await client.token_balance()

    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="dim",   justify="right")
    t.add_column(style="bold white")

    balance = data.get("balance", data.get("tokens_remaining", "N/A"))
    used    = data.get("tokens_used", data.get("used", "N/A"))
    limit   = data.get("monthly_limit", data.get("limit", "N/A"))

    t.add_row("Balance",       str(balance))
    t.add_row("Used (month)",  str(used))
    t.add_row("Limit (month)", str(limit))

    console.print(Panel(t, title="[cyan]Token Balance[/cyan]", border_style="cyan"))


# ── /doctor ───────────────────────────────────────────────────────────────────

@register("doctor", help="Diagnose connectivity and configuration issues")
async def _cmd_doctor(app: "BharatBuildCLI", args: str):
    from cli.doctor import run_doctor
    await run_doctor(app.config)


# ── /cd ───────────────────────────────────────────────────────────────────────

@register("cd", help="Change working directory  (/cd <path>)")
async def _cmd_cd(app: "BharatBuildCLI", args: str):
    target = Path(args.strip()).expanduser() if args.strip() else Path.home()
    if not target.exists():
        console.print(f"[red]✗ Directory not found: {target}[/red]")
        return
    if not target.is_dir():
        console.print(f"[red]✗ Not a directory: {target}[/red]")
        return
    os.chdir(target)
    app.config.working_directory = str(target)
    console.print(f"[green]✓ Changed to:[/green] [bold]{target.resolve()}[/bold]")


# ── /pwd ──────────────────────────────────────────────────────────────────────

@register("pwd", help="Print current working directory")
async def _cmd_pwd(app: "BharatBuildCLI", args: str):
    console.print(f"[cyan]{Path(app.config.working_directory).resolve()}[/cyan]")


# ── /history ──────────────────────────────────────────────────────────────────

@register("history", help="Show conversation history")
async def _cmd_history(app: "BharatBuildCLI", args: str):
    if not app.messages:
        console.print("[dim]No messages yet.[/dim]")
        return

    limit = int(args.strip()) if args.strip().isdigit() else 10
    recent = app.messages[-limit:]
    for msg in recent:
        role_style = "cyan" if msg.role == "user" else "green"
        prefix     = "You" if msg.role == "user" else "AI "
        preview    = msg.content[:120].replace("\n", " ")
        if len(msg.content) > 120:
            preview += "…"
        console.print(f"[{role_style}]{prefix}[/{role_style}]  {preview}")


# ── /save ─────────────────────────────────────────────────────────────────────

@register("save", help="Save current session to a file  (/save [filename])")
async def _cmd_save(app: "BharatBuildCLI", args: str):
    import json as _json
    filename = args.strip() or "session.json"
    path = Path(filename)
    data = [{"role": m.role, "content": m.content} for m in app.messages]
    path.write_text(_json.dumps(data, indent=2))
    console.print(f"[green]✓ Session saved to [bold]{path.resolve()}[/bold][/green]")


# ── /import ───────────────────────────────────────────────────────────────────

@register("import", help="Import an existing project folder  (/import <path>)")
async def _cmd_import(app: "BharatBuildCLI", args: str):
    from cli.projects import import_project
    path = args.strip()
    if not path:
        console.print("[yellow]Usage:[/yellow]  /import <path-to-project>")
        return
    await import_project(app.config, Path(path))


# ── /ieee ─────────────────────────────────────────────────────────────────────

@register("ieee", help="Generate IEEE academic documents for the current project",
          aliases=["ieee-auto", "docs"])
async def _cmd_ieee(app: "BharatBuildCLI", args: str):
    if not app.current_project_id:
        console.print("[yellow]No active project.  Select one with [cyan]/project <id>[/cyan].[/yellow]")
        return

    from cli.client import BharatBuildClient, APIError
    doc_types = args.strip().split() if args.strip() else ["srs", "uml", "report", "ppt"]

    console.print(f"[cyan]Generating documents: {', '.join(doc_types)}…[/cyan]")
    try:
        async with BharatBuildClient(app.config) as client:
            for doc_type in doc_types:
                with console.status(f"[cyan]  Generating {doc_type.upper()}…[/cyan]", spinner="dots"):
                    resp = await client.post(
                        f"/documents/generate/{app.current_project_id}",
                        {"doc_type": doc_type},
                    )
                console.print(f"  [green]✓ {doc_type.upper()}[/green]  {resp.get('file_url', '')}")
    except APIError as exc:
        console.print(f"[red]✗ {exc.detail}[/red]")


# ── /config ───────────────────────────────────────────────────────────────────

@register("config", help="Show or set config values  (/config [key] [value])")
async def _cmd_config(app: "BharatBuildCLI", args: str):
    parts = args.strip().split(None, 1)

    if not parts:
        # Show all
        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column(style="dim", justify="right")
        t.add_column(style="white")
        for k, v in vars(app.config).items():
            if "token" in k.lower() or "password" in k.lower():
                v = "***"
            t.add_row(k, str(v))
        console.print(Panel(t, title="[cyan]Config[/cyan]", border_style="cyan"))
        return

    key = parts[0]
    if len(parts) == 1:
        val = getattr(app.config, key, "[not found]")
        console.print(f"[cyan]{key}[/cyan] = [bold]{val}[/bold]")
        return

    val = parts[1]
    if hasattr(app.config, key):
        # cast to existing type
        existing = getattr(app.config, key)
        try:
            if isinstance(existing, bool):
                val = val.lower() in ("1", "true", "yes")
            elif isinstance(existing, int):
                val = int(val)
            setattr(app.config, key, val)
            console.print(f"[green]✓ {key} = {val}[/green]")
        except Exception as exc:
            console.print(f"[red]✗ Could not set {key}: {exc}[/red]")
    else:
        console.print(f"[red]✗ Unknown config key: {key}[/red]")


# ── /login ────────────────────────────────────────────────────────────────────

@register("login", help="Login to BharatBuild")
async def _cmd_login(app: "BharatBuildCLI", args: str):
    await app.do_login()


# ── /logout ───────────────────────────────────────────────────────────────────

@register("logout", help="Logout and clear credentials")
async def _cmd_logout(app: "BharatBuildCLI", args: str):
    from cli.auth import AuthManager
    AuthManager.logout()
    console.print("[green]✓ Logged out.[/green]")


# ── /version ──────────────────────────────────────────────────────────────────

@register("version", help="Show CLI version", aliases=["ver"])
async def _cmd_version(app: "BharatBuildCLI", args: str):
    console.print("[bold cyan]BharatBuild CLI[/bold cyan]  [dim]v1.0.0[/dim]")


# ── internal helpers ──────────────────────────────────────────────────────────

def _render_execution_event(event: dict) -> None:
    """Pretty-print a Docker execution SSE event."""
    etype = event.get("type", "")
    data  = event.get("data", event)

    if etype in ("log", "stdout", "stderr"):
        line = data.get("line", data.get("message", str(data)))
        style = "red" if etype == "stderr" else "white"
        console.print(f"[{style}]{line}[/{style}]")

    elif etype == "status":
        msg = data.get("message", str(data))
        console.print(f"[cyan]▷ {msg}[/cyan]")

    elif etype in ("preview_ready", "preview"):
        url = data.get("url", data.get("preview_url", ""))
        console.print(f"[bold green]✓ Preview ready:[/bold green] [underline]{url}[/underline]")

    elif etype == "error":
        msg = data.get("message", str(data))
        console.print(f"[red]✗ Error: {msg}[/red]")

    elif etype == "complete":
        console.print("[bold green]✓ Execution complete[/bold green]")
