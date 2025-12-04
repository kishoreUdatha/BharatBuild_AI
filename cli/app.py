"""
BharatBuild AI CLI - Core Application

This is the main CLI application that provides a Claude Code-like experience.
"""

import asyncio
import os
import sys
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass, field

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, Confirm

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML

from cli.config import CLIConfig
from cli.tools import ToolExecutor
from cli.renderer import ResponseRenderer
from cli.session import SessionManager
from cli.commands import SlashCommandHandler


@dataclass
class Message:
    """Represents a conversation message"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    token_usage: Optional[Dict[str, int]] = None


class BharatBuildCLI:
    """Main CLI Application"""

    def __init__(self, config: CLIConfig):
        self.config = config
        self.console = Console()
        self.messages: List[Message] = []
        self.session_manager = SessionManager(config)
        self.tool_executor = ToolExecutor(config, self.console)
        self.renderer = ResponseRenderer(self.console, config)
        self.command_handler = SlashCommandHandler(self)
        self.current_project_id: Optional[str] = None
        self.total_tokens = 0
        self.total_cost = 0.0
        self._running = True

        # Key bindings for prompt_toolkit
        self.key_bindings = self._create_key_bindings()

        # Prompt style - Claude Code inspired
        self.prompt_style = Style.from_dict({
            'prompt': '#00D9FF bold',      # Cyan prompt symbol
            'path': '#4ADE80',              # Green path
            'git': '#FF79C6',               # Pink/magenta git branch
            'user': '#E5E5E5',              # Light text for user input
        })

    def _create_key_bindings(self) -> KeyBindings:
        """Create keyboard shortcuts"""
        kb = KeyBindings()

        @kb.add('c-l')
        def clear_screen(event):
            """Clear screen"""
            self.console.clear()
            self._print_header()

        @kb.add('c-c')
        def cancel(event):
            """Cancel current input"""
            event.app.current_buffer.reset()

        @kb.add('escape', 'escape')
        def undo(event):
            """Undo last operation"""
            self.console.print("[yellow]Undo not yet implemented[/yellow]")

        return kb

    def _print_header(self):
        """Print Claude Code style CLI header"""
        # Beautiful banner like Claude Code
        banner = """
[bold cyan]╭──────────────────────────────────────────────────────────╮[/bold cyan]
[bold cyan]│[/bold cyan]                                                          [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan]   [bold white]BharatBuild AI[/bold white] [dim]v1.0.0[/dim]                              [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan]   [dim]Claude Code Style CLI for AI-driven development[/dim]    [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan]                                                          [bold cyan]│[/bold cyan]
[bold cyan]╰──────────────────────────────────────────────────────────╯[/bold cyan]
"""
        self.console.print(banner)

    def _print_welcome(self):
        """Print welcome message with Claude Code styling"""
        self.console.clear()
        self._print_header()

        # Working directory with icon
        cwd = Path(self.config.working_directory).resolve()
        self.console.print(f"  [dim]📁[/dim] [bold]Working directory:[/bold] [green]{cwd}[/green]")

        # Model info
        model_display = {
            "haiku": "Claude 3.5 Haiku [dim](fast)[/dim]",
            "sonnet": "Claude 3.5 Sonnet [dim](balanced)[/dim]",
            "opus": "Claude 3 Opus [dim](powerful)[/dim]"
        }
        self.console.print(f"  [dim]🤖[/dim] [bold]Model:[/bold] [cyan]{model_display.get(self.config.model, self.config.model)}[/cyan]")

        # Git branch if available
        git_branch = self._get_git_branch()
        if git_branch:
            self.console.print(f"  [dim]󰊢[/dim]  [bold]Branch:[/bold] [magenta]{git_branch}[/magenta]")

        # Check for existing session
        if self.config.continue_session and self.session_manager.has_session():
            self.console.print(f"\n  [yellow]📜 Resuming previous session...[/yellow]")
            self.messages = self.session_manager.load_session()
            self.console.print(f"  [dim]   Loaded {len(self.messages)} messages[/dim]")

        # Keyboard shortcuts hint
        self.console.print()
        self.console.print("[dim]  Ctrl+C[/dim] cancel  [dim]Ctrl+L[/dim] clear  [dim]/help[/dim] commands  [dim]/quit[/dim] exit")
        self.console.print()

    def _get_git_branch(self) -> str:
        """Get current git branch if in a git repo"""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                cwd=self.config.working_directory,
                timeout=2
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return ""

    def _get_prompt_text(self) -> HTML:
        """Get Claude Code style prompt text with path and git"""
        cwd = Path(self.config.working_directory).name or "~"
        git_branch = self._get_git_branch()

        if git_branch:
            return HTML(f'<prompt>❯</prompt> <path>{cwd}</path> <git>({git_branch})</git> ')
        return HTML(f'<prompt>❯</prompt> <path>{cwd}</path> ')

    async def run_interactive(self):
        """Run interactive REPL mode"""
        self._print_welcome()

        # Create prompt session with history
        session = PromptSession(
            history=FileHistory(self.config.history_file),
            auto_suggest=AutoSuggestFromHistory(),
            key_bindings=self.key_bindings,
            style=self.prompt_style,
            multiline=False,
            enable_history_search=True
        )

        while self._running:
            try:
                # Get user input
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: session.prompt(self._get_prompt_text())
                )

                # Skip empty input
                if not user_input.strip():
                    continue

                # Handle slash commands
                if user_input.startswith('/'):
                    await self.command_handler.handle(user_input)
                    continue

                # Handle bash mode (! prefix)
                if user_input.startswith('!'):
                    await self._execute_bash(user_input[1:])
                    continue

                # Process natural language prompt
                await self._process_prompt(user_input)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use /quit to exit or Ctrl+D[/yellow]")
                continue
            except EOFError:
                break

        # Save session on exit
        self.session_manager.save_session(self.messages)
        self._print_goodbye()

    async def run_single(self, prompt: str):
        """Run a single prompt and exit"""
        if self.config.output_format == "json":
            # JSON output mode
            result = await self._process_prompt_json(prompt)
            print(json.dumps(result, indent=2))
        else:
            # Normal text output
            await self._process_prompt(prompt)

    async def _process_prompt(self, prompt: str):
        """Process a natural language prompt"""
        # Add user message
        user_msg = Message(role="user", content=prompt)
        self.messages.append(user_msg)

        # Track tokens for this request
        self._current_tokens = 0

        # Show Claude Code style progress status
        try:
            with self.renderer.progress_status(action="think") as progress_status:
                self._progress_status = progress_status  # Store reference for token updates

                # Call orchestrator
                async for event in self._stream_response(prompt):
                    await self._handle_event(event, progress_status)

                self._progress_status = None

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Interrupted[/yellow]")
        except Exception as e:
            self.console.print(f"\n[red]Error: {e}[/red]")
            if self.config.verbose:
                import traceback
                self.console.print(traceback.format_exc())

    async def _process_prompt_json(self, prompt: str) -> Dict[str, Any]:
        """Process prompt and return JSON result"""
        result = {
            "prompt": prompt,
            "response": "",
            "tool_calls": [],
            "files_created": [],
            "files_modified": [],
            "commands_executed": [],
            "token_usage": {},
            "cost": 0.0
        }

        async for event in self._stream_response(prompt):
            if event.get("type") == "content":
                result["response"] += event.get("content", "")
            elif event.get("type") == "file_operation":
                if event.get("operation") == "create":
                    result["files_created"].append(event.get("path"))
                elif event.get("operation") == "modify":
                    result["files_modified"].append(event.get("path"))
            elif event.get("type") == "command_execute":
                result["commands_executed"].append(event.get("command"))
            elif event.get("type") == "complete":
                result["token_usage"] = event.get("data", {}).get("usage", {})

        return result

    async def _stream_response(self, prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream response from orchestrator"""
        import httpx

        url = f"{self.config.api_base_url}/orchestrator/execute"

        # Build auth headers
        headers = {
            "Content-Type": "application/json"
        }
        if self.config.auth_token:
            headers["Authorization"] = f"Bearer {self.config.auth_token}"
        if self.config.user_id:
            headers["X-User-ID"] = self.config.user_id
        if self.config.user_email:
            headers["X-User-Email"] = self.config.user_email

        payload = {
            "user_request": prompt,
            "project_id": self.current_project_id or "cli-project",
            "workflow_name": "bolt_standard",
            "user_id": self.config.user_id,  # Include user ID in payload
            "metadata": {
                "model": self.config.model,
                "source": "cli",
                "user_name": self.config.user_name,
                "user_email": self.config.user_email,
                "working_directory": self.config.working_directory
            }
        }

        # Add streaming headers
        headers["Accept"] = "text/event-stream"

        # Use auth token (from login) or api_key (legacy)
        if not headers.get("Authorization") and self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"API error {response.status_code}: {error_text.decode()}")

                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk

                    # Parse SSE events
                    while "\n\n" in buffer:
                        event_str, buffer = buffer.split("\n\n", 1)

                        for line in event_str.split("\n"):
                            if line.startswith("data: "):
                                try:
                                    data = json.loads(line[6:])
                                    yield data
                                except json.JSONDecodeError:
                                    continue

    async def _handle_event(self, event: Dict[str, Any], progress_status=None):
        """Handle a streaming event - Claude Code style"""
        event_type = event.get("type")
        data = event.get("data", {})
        agent = event.get("agent", "")

        # Update token count if available
        if progress_status and "tokens" in data:
            progress_status.add_tokens(data.get("tokens", 0))

        # ==================== Claude Code Style Event Handlers ====================

        if event_type == "connected":
            self.console.print("[dim]⚡ Connected to BharatBuild AI[/dim]")

        elif event_type == "status":
            message = data.get("message", "")
            if progress_status:
                progress_status.update_message(message)
            else:
                self.console.print(f"[dim]{message}[/dim]")

        elif event_type == "agent_start":
            # Claude Code style: Show agent starting with icon
            agent_name = data.get("name", agent)
            description = data.get("description", "")
            attempt = data.get("attempt", 1)
            agent_icons = {"planner": "🧠", "writer": "✏️", "verifier": "🔍", "fixer": "🔧", "runner": "▶️", "documenter": "📄", "bolt_instant": "⚡"}
            icon = agent_icons.get(str(agent).lower(), "🤖")
            self.console.print()
            self.console.print(f"[bold cyan]{icon} {agent_name}[/bold cyan]")
            if description:
                self.console.print(f"   [dim]{description}[/dim]")
            if attempt > 1:
                self.console.print(f"   [yellow]Retry attempt {attempt}[/yellow]")

        elif event_type == "agent_complete":
            agent_name = data.get("name", agent)
            success = data.get("success", True)
            if success:
                self.console.print(f"[green]   ✓ {agent_name} completed[/green]")
            else:
                self.console.print(f"[red]   ✗ {agent_name} failed[/red]")

        elif event_type == "thinking_step":
            step_detail = data.get("step", data.get("detail", ""))
            user_visible = data.get("user_visible", True)
            if user_visible and step_detail:
                icon = data.get("icon", "◐")
                if progress_status:
                    progress_status.update_message(step_detail)
                else:
                    self.console.print(f"   [cyan]{icon}[/cyan] {step_detail}")

        elif event_type == "plan_created":
            # Claude Code style: Show plan with task tree
            tasks = data.get("tasks", [])
            files = data.get("files", [])
            project_name = data.get("project_name", "")
            self.console.print()
            if project_name:
                self.console.print(f"[bold white]📦 {project_name}[/bold white]")
            self.console.print("[bold cyan]📋 Execution Plan[/bold cyan]")
            self.console.print()
            if tasks:
                for i, task in enumerate(tasks, 1):
                    title = task.get("title", task.get("name", ""))
                    self.console.print(f"  [dim]{i}.[/dim] {title}")
            if files:
                self.console.print()
                self.console.print(f"[bold cyan]📁 Files to create ({len(files)})[/bold cyan]")
                for f in files[:10]:
                    path = f.get("path", str(f))
                    self.console.print(f"  [dim]•[/dim] {path}")
                if len(files) > 10:
                    self.console.print(f"  [dim]... and {len(files) - 10} more files[/dim]")
            self.console.print()

        elif event_type == "file_operation":
            # Claude Code style: Show Write tool call
            path = data.get("path", event.get("path", ""))
            operation = data.get("operation", event.get("operation", "write"))
            op_status = data.get("status", event.get("operation_status", ""))
            content = data.get("content", event.get("file_content", ""))
            if op_status in ("in_progress", "start"):
                self.console.print()
                self.console.print(f"[bold magenta]⚡ Write[/bold magenta]")
                self.console.print(f"   [dim]path:[/dim] {path}")
            elif op_status in ("complete", "end") and content:
                if self.config.permission_mode == "auto" or await self._confirm_file_operation(operation, path):
                    await self.tool_executor.write_file(path, content)
                    self.console.print(f"[green]   ✓ Wrote {path}[/green]")

        elif event_type == "file_start":
            path = data.get("path", event.get("path", ""))
            self.console.print()
            self.console.print(f"[bold magenta]⚡ Write[/bold magenta]")
            self.console.print(f"   [dim]path:[/dim] {path}")

        elif event_type == "file_content":
            content = data.get("content", event.get("content", ""))
            if content and progress_status:
                progress_status.add_tokens(len(content) // 4)

        elif event_type == "file_complete":
            path = data.get("path", event.get("path", ""))
            content = data.get("content", data.get("full_content", event.get("full_content", "")))
            if content:
                if self.config.permission_mode == "auto" or await self._confirm_file_operation("create", path):
                    await self.tool_executor.write_file(path, content)
                    self.console.print(f"[green]   ✓ Wrote {path}[/green]")

        elif event_type == "command_execute":
            # Claude Code style: Bash tool call
            command = data.get("command", event.get("command", ""))
            if command:
                self.console.print()
                self.console.print(f"[bold magenta]⚡ Bash[/bold magenta]")
                self.console.print(f"   [dim]command:[/dim] {command}")
                if self.config.permission_mode == "auto" or await self._confirm_bash(command):
                    result = await self.tool_executor.execute_bash(command)
                    if result.stdout:
                        for line in result.stdout.split('\n')[:10]:
                            self.console.print(f"   {line}")
                    if result.exit_code == 0:
                        self.console.print(f"[green]   ✓ Command completed[/green]")
                    else:
                        self.console.print(f"[red]   ✗ Exit code: {result.exit_code}[/red]")

        elif event_type == "command_output":
            output = data.get("output", "")
            if output:
                self.console.print(f"   {output}", end="")

        elif event_type == "commands":
            commands = data.get("commands", event.get("commands", []))
            for cmd in commands:
                self.console.print()
                self.console.print(f"[bold magenta]⚡ Bash[/bold magenta]")
                self.console.print(f"   [dim]command:[/dim] {cmd}")
                if self.config.permission_mode == "auto" or await self._confirm_bash(cmd):
                    result = await self.tool_executor.execute_bash(cmd)
                    if result.exit_code == 0:
                        self.console.print(f"[green]   ✓ Command completed[/green]")
                    else:
                        self.console.print(f"[red]   ✗ Exit code: {result.exit_code}[/red]")

        elif event_type == "content":
            # Claude Code style: Streaming AI response
            content = data.get("content", event.get("content", ""))
            if content:
                if progress_status:
                    progress_status.add_tokens(len(content) // 4)
                self.console.print(content, end="")

        elif event_type == "verification_result":
            success = data.get("success", False)
            issues = data.get("issues", [])
            self.console.print()
            if success:
                self.console.print("[green]   ✓ Verification passed[/green]")
            else:
                self.console.print("[yellow]   ⚠ Verification found issues:[/yellow]")
                for issue in issues[:5]:
                    self.console.print(f"   [dim]•[/dim] {issue}")

        elif event_type == "token_update":
            if progress_status:
                progress_status.update_tokens(data.get("tokens", 0))

        elif event_type == "warning":
            self.console.print(f"[yellow]   ⚠ {data.get('message', '')}[/yellow]")

        elif event_type == "error":
            error_msg = data.get("error", data.get("message", "Unknown error"))
            self.console.print(f"\n[red]❌ Error: {error_msg}[/red]")

        elif event_type == "complete":
            message = data.get("message", "")
            usage = data.get("usage", {})
            files_created = data.get("files_created", 0)
            download_url = data.get("download_url", "")
            if progress_status and usage:
                progress_status.update_tokens(usage.get("total_tokens", 0))
            # Final summary - Claude Code style
            self.console.print()
            self.console.print("[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold green]")
            self.console.print(f"[bold green]✓ {message or 'Workflow completed'}[/bold green]")
            if files_created:
                self.console.print(f"[dim]   Files created: {files_created}[/dim]")
            if download_url:
                self.console.print(f"[dim]   Download: {download_url}[/dim]")
            if usage:
                self.total_tokens += usage.get("total_tokens", 0)
                input_t = usage.get("input_tokens", 0)
                output_t = usage.get("output_tokens", 0)
                total_t = usage.get("total_tokens", input_t + output_t)
                self.console.print(f"[dim]   Tokens: {total_t:,} (in: {input_t:,}, out: {output_t:,})[/dim]")
            self.console.print("[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold green]")

    async def _confirm_file_operation(self, operation: str, path: str) -> bool:
        """Ask user to confirm file operation"""
        if self.config.permission_mode == "deny":
            return False
        if self.config.permission_mode == "auto":
            return True
        if self.config.non_interactive:
            return True

        return Confirm.ask(f"[yellow]Allow {operation} {path}?[/yellow]")

    async def _confirm_bash(self, command: str) -> bool:
        """Ask user to confirm bash command"""
        if self.config.permission_mode == "deny":
            return False
        if self.config.permission_mode == "auto":
            return True
        if self.config.non_interactive:
            return True

        self.console.print(f"[yellow]Command:[/yellow] {command}")
        return Confirm.ask("[yellow]Execute?[/yellow]")

    async def _execute_bash(self, command: str):
        """Execute bash command directly"""
        result = await self.tool_executor.execute_bash(command)
        self.renderer.render_command_result(command, result)

    def _print_goodbye(self):
        """Print goodbye message"""
        self.console.print("\n[cyan]Thanks for using BharatBuild AI! 👋[/cyan]")
        if self.total_tokens > 0:
            self.console.print(f"[dim]Total tokens used: {self.total_tokens}[/dim]")

    def quit(self):
        """Quit the CLI"""
        self._running = False
