"""
BharatBuild CLI — Core Application (REPL)
==========================================
Kiro-style interactive loop wiring together:
  • InputHandler      — prompt_toolkit session with Tab autocomplete
  • StreamingMarkdownRenderer — live safe-flush markdown streaming
  • ToolConfirmer     — Allow / Deny / Cancel permission dialogs
  • SlashCommandHandler — all /commands
  • BharatBuildClient — SSE streaming API client

Entry points
------------
  BharatBuildCLI.run()        — interactive REPL (blocking)
  BharatBuildCLI.run_once()   — single-shot / headless
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from cli.config import CLIConfig
from cli.commands import SlashCommandHandler
from cli.input_handler import InputHandler
from cli.stream_renderer import StreamingMarkdownRenderer
from cli.tool_confirm import ToolConfirmer, Permission


# ── message model ─────────────────────────────────────────────────────────────

@dataclass
class Message:
    role:        str
    content:     str
    timestamp:   float          = field(default_factory=time.time)
    tool_calls:  List[Any]      = field(default_factory=list)
    token_usage: Optional[Dict] = None


# ── main CLI class ────────────────────────────────────────────────────────────

class BharatBuildCLI:
    """Interactive REPL — the heart of the BharatBuild CLI."""

    def __init__(self, config: CLIConfig):
        self.config              = config
        self.console             = Console()
        self.messages: List[Message] = []

        # sub-systems
        self.command_handler = SlashCommandHandler(self)
        self.input_handler   = InputHandler(self)
        self.stream_renderer = StreamingMarkdownRenderer(self.console)
        self.tool_confirmer  = ToolConfirmer(config)

        # state
        self.current_project_id: Optional[str] = None
        self.total_tokens   = 0
        self.total_cost     = 0.0
        self._running       = True

    # ── banner ────────────────────────────────────────────────────────────────

    def _print_header(self) -> None:
        self.console.print(
            "\n[bold cyan]╭────────────────────────────────────────────────────╮[/bold cyan]\n"
            "[bold cyan]│[/bold cyan]   [bold white]BharatBuild AI[/bold white]  "
            "[dim]v1.0.0[/dim]                           [bold cyan]│[/bold cyan]\n"
            "[bold cyan]│[/bold cyan]   [dim]AI-powered code generation · India[/dim]         "
            "[bold cyan]│[/bold cyan]\n"
            "[bold cyan]╰────────────────────────────────────────────────────╯[/bold cyan]\n"
        )

    def _print_welcome(self) -> None:
        from cli.auth import AuthManager

        self.console.clear()
        self._print_header()

        cwd = Path(self.config.working_directory).resolve()
        self.console.print(f"  [dim]📁[/dim]  [bold]Directory:[/bold] [green]{cwd}[/green]")
        self.console.print(f"  [dim]🤖[/dim]  [bold]Model:[/bold]     [cyan]{self.config.model}[/cyan]")
        self.console.print(f"  [dim]🔒[/dim]  [bold]Mode:[/bold]      [dim]{self.config.permission_mode}[/dim]")

        creds = AuthManager.load()
        if creds:
            self.console.print(
                f"  [dim]👤[/dim]  [bold]Logged in:[/bold] "
                f"[green]{creds.name}[/green] [dim]({creds.tier})[/dim]"
            )
        else:
            self.console.print(
                "  [dim]⚠[/dim]   [yellow]Not logged in.[/yellow]  "
                "Run [cyan]bharatbuild login[/cyan] first."
            )

        self.console.print()
        self.input_handler.print_hint()

    # ── AI streaming reply ────────────────────────────────────────────────────

    async def _stream_reply(self, prompt: str) -> None:
        """Send a message to the AI and stream the response with live rendering."""
        from cli.client import BharatBuildClient, APIError

        self.messages.append(Message(role="user", content=prompt))

        payload = {
            "message":    prompt,
            "project_id": self.current_project_id or "",
            "files":      [],
            "model":      self.config.model,
            "history": [
                {"role": m.role, "content": m.content}
                for m in self.messages[-10:]
            ],
        }

        reply_parts: List[str] = []

        self.stream_renderer.start()

        try:
            async with BharatBuildClient(self.config) as client:
                async for event in client.stream_sse("/bolt/chat/stream", payload):
                    etype = event.get("type", "text")
                    data  = event.get("data", event)

                    if etype == "text":
                        chunk = (
                            data.get("content", data.get("text", ""))
                            if isinstance(data, dict) else str(data)
                        )
                        if chunk:
                            self.stream_renderer.push(chunk)
                            reply_parts.append(chunk)

                    elif etype == "status":
                        msg = (data.get("message", "") if isinstance(data, dict)
                               else str(data))
                        if msg:
                            self.console.print(f"[dim cyan]⟳ {msg}[/dim cyan]")

                    elif etype == "tool_call":
                        # tool confirmation dialog
                        tool_name = (data.get("tool", data.get("name", ""))
                                     if isinstance(data, dict) else "")
                        tool_desc = (data.get("description", "")
                                     if isinstance(data, dict) else "")
                        tool_input = (data.get("input", data.get("arguments", {}))
                                      if isinstance(data, dict) else {})

                        perm = await self.tool_confirmer.ask(
                            tool_name   = tool_name,
                            description = tool_desc,
                            tool_input  = tool_input,
                        )

                        if perm == Permission.CANCEL:
                            self.console.print("[yellow]⚠ Turn cancelled.[/yellow]")
                            break

                        if perm in (Permission.DENY_ONCE, Permission.DENY_ALWAYS):
                            self.console.print(f"[yellow]⊘ Tool {tool_name} denied.[/yellow]")

                    elif etype == "complete":
                        break

                    elif etype == "error":
                        msg = (data.get("message", str(data))
                               if isinstance(data, dict) else str(data))
                        self.stream_renderer.finish()
                        self.console.print(f"[red]✗ {msg}[/red]")
                        return

        except APIError as exc:
            self.stream_renderer.finish()
            self.console.print(f"\n[red]✗ API error: {exc.detail}[/red]")
            return
        except asyncio.CancelledError:
            self.stream_renderer.finish()
            self.console.print("\n[yellow]⚠ Cancelled.[/yellow]")
            return

        self.stream_renderer.finish()

        full_reply = "".join(reply_parts)
        if full_reply:
            self.messages.append(Message(role="assistant", content=full_reply))
            self.total_tokens += len(full_reply.split())

    # ── REPL loop ─────────────────────────────────────────────────────────────

    async def run(self) -> None:
        """Start the interactive REPL loop — blocks until exit."""
        self._print_welcome()
        self.input_handler.setup()

        while self._running:
            try:
                user_input = await self.input_handler.prompt()
            except (EOFError, KeyboardInterrupt):
                self.console.print("\n[dim]Goodbye! 👋[/dim]\n")
                break

            if user_input is None:
                self.console.print("\n[dim]Goodbye! 👋[/dim]\n")
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            # slash commands
            if SlashCommandHandler.is_command(user_input):
                await self.command_handler.handle(user_input)
                continue

            # bare convenience words
            if user_input.lower() in ("login",):
                await self.command_handler.handle("/login")
                continue
            if user_input.lower() in ("logout",):
                await self.command_handler.handle("/logout")
                continue
            if user_input.lower() in ("exit", "quit", "bye"):
                await self.command_handler.handle("/exit")
                continue

            # send to AI
            await self._stream_reply(user_input)

    # ── single-shot mode ──────────────────────────────────────────────────────

    async def run_once(self, prompt: str) -> None:
        """Run a single prompt and exit — for CI / scripting."""
        from cli.generate import run_generation, generate_headless
        from cli.client  import BharatBuildClient

        if self.config.non_interactive:
            await generate_headless(self.config, prompt)
            return

        try:
            async with BharatBuildClient(self.config) as client:
                classification = await client.classify_prompt(prompt)
        except Exception:
            classification = "project_request"

        if classification in ("project_request", "small_task"):
            await run_generation(self, prompt)
        else:
            self.input_handler.setup()
            await self._stream_reply(prompt)

    # ── /login helper (called from command handler) ───────────────────────────

    async def do_login(self) -> None:
        from cli.auth import interactive_login, AuthManager
        creds = await interactive_login(self.config)
        if creds:
            AuthManager.inject_into_config(self.config, creds)
            self.tool_confirmer.reset_session_memory()
