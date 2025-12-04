"""
BharatBuild CLI Hooks System

Enables pre/post command hooks:
  /hooks add pre-commit "npm test"
  /hooks add post-file-write "prettier --write"
  /hooks list
"""

import os
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class HookEvent(str, Enum):
    """Events that can trigger hooks"""
    # Session events
    SESSION_START = "session_start"
    SESSION_END = "session_end"

    # Prompt events
    PRE_PROMPT = "pre_prompt"       # Before sending to AI
    POST_PROMPT = "post_prompt"     # After receiving response

    # File events
    PRE_FILE_READ = "pre_file_read"
    POST_FILE_READ = "post_file_read"
    PRE_FILE_WRITE = "pre_file_write"
    POST_FILE_WRITE = "post_file_write"
    PRE_FILE_DELETE = "pre_file_delete"
    POST_FILE_DELETE = "post_file_delete"

    # Command events
    PRE_BASH = "pre_bash"           # Before running bash command
    POST_BASH = "post_bash"         # After bash command

    # Git events
    PRE_GIT_COMMIT = "pre_git_commit"
    POST_GIT_COMMIT = "post_git_commit"

    # Tool events
    PRE_TOOL_CALL = "pre_tool_call"
    POST_TOOL_CALL = "post_tool_call"


class HookType(str, Enum):
    """Types of hooks"""
    SHELL = "shell"         # Shell command
    PYTHON = "python"       # Python function path
    BUILTIN = "builtin"     # Built-in hook


@dataclass
class HookResult:
    """Result of hook execution"""
    success: bool
    output: str = ""
    error: str = ""
    duration: float = 0.0
    should_continue: bool = True  # Whether to proceed with the operation


@dataclass
class Hook:
    """A hook configuration"""
    name: str
    event: HookEvent
    hook_type: HookType
    command: str                # Shell command or python path
    enabled: bool = True
    timeout: int = 30          # Timeout in seconds
    blocking: bool = True      # Whether to wait for completion
    fail_on_error: bool = False  # Stop operation if hook fails
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    env: Dict[str, str] = field(default_factory=dict)
    patterns: List[str] = field(default_factory=list)  # File patterns for file events


class HooksManager:
    """
    Manages hooks for CLI events.

    Usage:
        manager = HooksManager(console, working_dir, config_dir)

        # Add a hook
        manager.add_hook("format", HookEvent.POST_FILE_WRITE, "prettier --write {file}")

        # Execute hooks for an event
        results = await manager.execute_hooks(HookEvent.POST_FILE_WRITE, {"file": "src/app.js"})

        # List hooks
        manager.list_hooks()
    """

    def __init__(
        self,
        console: Console,
        working_dir: Path,
        config_dir: Optional[Path] = None
    ):
        self.console = console
        self.working_dir = working_dir
        self.config_dir = config_dir or (Path.home() / ".bharatbuild" / "hooks")
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self._hooks: Dict[str, Hook] = {}
        self._python_hooks: Dict[str, Callable] = {}

        # Load saved hooks
        self._load_hooks()

        # Register built-in hooks
        self._register_builtin_hooks()

    def _load_hooks(self):
        """Load hooks from configuration"""
        # Load from global config
        global_file = self.config_dir / "hooks.json"
        if global_file.exists():
            self._load_hooks_file(global_file)

        # Load from project config
        project_file = self.working_dir / ".bharatbuild" / "hooks.json"
        if project_file.exists():
            self._load_hooks_file(project_file)

    def _load_hooks_file(self, path: Path):
        """Load hooks from a file"""
        try:
            with open(path) as f:
                data = json.load(f)

            for name, hook_data in data.get("hooks", {}).items():
                self._hooks[name] = Hook(
                    name=name,
                    event=HookEvent(hook_data["event"]),
                    hook_type=HookType(hook_data.get("type", "shell")),
                    command=hook_data["command"],
                    enabled=hook_data.get("enabled", True),
                    timeout=hook_data.get("timeout", 30),
                    blocking=hook_data.get("blocking", True),
                    fail_on_error=hook_data.get("fail_on_error", False),
                    description=hook_data.get("description", ""),
                    env=hook_data.get("env", {}),
                    patterns=hook_data.get("patterns", [])
                )

        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not load hooks from {path}: {e}[/yellow]")

    def _save_hooks(self):
        """Save hooks to configuration"""
        config_file = self.config_dir / "hooks.json"

        try:
            data = {"hooks": {}}
            for name, hook in self._hooks.items():
                if hook.hook_type != HookType.BUILTIN:
                    data["hooks"][name] = {
                        "event": hook.event.value,
                        "type": hook.hook_type.value,
                        "command": hook.command,
                        "enabled": hook.enabled,
                        "timeout": hook.timeout,
                        "blocking": hook.blocking,
                        "fail_on_error": hook.fail_on_error,
                        "description": hook.description,
                        "env": hook.env,
                        "patterns": hook.patterns
                    }

            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not save hooks: {e}[/yellow]")

    def _register_builtin_hooks(self):
        """Register built-in hooks"""
        # These are example built-in hooks that can be enabled
        pass

    # ==================== Hook Management ====================

    def add_hook(
        self,
        name: str,
        event: HookEvent,
        command: str,
        hook_type: HookType = HookType.SHELL,
        description: str = "",
        timeout: int = 30,
        blocking: bool = True,
        fail_on_error: bool = False,
        patterns: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None
    ) -> bool:
        """Add a new hook"""
        if name in self._hooks:
            self.console.print(f"[yellow]Hook '{name}' already exists. Use update to modify.[/yellow]")
            return False

        self._hooks[name] = Hook(
            name=name,
            event=event,
            hook_type=hook_type,
            command=command,
            description=description,
            timeout=timeout,
            blocking=blocking,
            fail_on_error=fail_on_error,
            patterns=patterns or [],
            env=env or {}
        )

        self._save_hooks()
        self.console.print(f"[green]✓ Added hook '{name}' for {event.value}[/green]")

        return True

    def remove_hook(self, name: str) -> bool:
        """Remove a hook"""
        if name not in self._hooks:
            self.console.print(f"[red]Hook '{name}' not found[/red]")
            return False

        hook = self._hooks[name]
        if hook.hook_type == HookType.BUILTIN:
            self.console.print(f"[red]Cannot remove built-in hook '{name}'[/red]")
            return False

        del self._hooks[name]
        self._save_hooks()
        self.console.print(f"[green]✓ Removed hook '{name}'[/green]")

        return True

    def enable_hook(self, name: str) -> bool:
        """Enable a hook"""
        if name not in self._hooks:
            self.console.print(f"[red]Hook '{name}' not found[/red]")
            return False

        self._hooks[name].enabled = True
        self._save_hooks()
        self.console.print(f"[green]✓ Enabled hook '{name}'[/green]")

        return True

    def disable_hook(self, name: str) -> bool:
        """Disable a hook"""
        if name not in self._hooks:
            self.console.print(f"[red]Hook '{name}' not found[/red]")
            return False

        self._hooks[name].enabled = False
        self._save_hooks()
        self.console.print(f"[green]✓ Disabled hook '{name}'[/green]")

        return True

    def get_hooks_for_event(self, event: HookEvent) -> List[Hook]:
        """Get all enabled hooks for an event"""
        return [
            hook for hook in self._hooks.values()
            if hook.event == event and hook.enabled
        ]

    def register_python_hook(self, name: str, func: Callable[[Dict[str, Any]], Awaitable[HookResult]]):
        """Register a Python function as a hook handler"""
        self._python_hooks[name] = func

    # ==================== Hook Execution ====================

    async def execute_hooks(
        self,
        event: HookEvent,
        context: Dict[str, Any],
        show_output: bool = True
    ) -> List[HookResult]:
        """
        Execute all hooks for an event.

        Args:
            event: The event type
            context: Context variables available to hooks
            show_output: Whether to show hook output

        Returns:
            List of HookResults
        """
        hooks = self.get_hooks_for_event(event)
        results = []

        for hook in hooks:
            # Check file patterns for file events
            if hook.patterns and "file" in context:
                file_path = context["file"]
                import fnmatch
                if not any(fnmatch.fnmatch(file_path, p) for p in hook.patterns):
                    continue

            if show_output:
                self.console.print(f"[dim]Running hook: {hook.name}...[/dim]")

            result = await self._execute_hook(hook, context)
            results.append(result)

            if show_output and result.output:
                self.console.print(f"[dim]{result.output}[/dim]")

            if not result.success and result.error:
                self.console.print(f"[yellow]Hook error: {result.error}[/yellow]")

            if not result.should_continue:
                break

        return results

    async def _execute_hook(self, hook: Hook, context: Dict[str, Any]) -> HookResult:
        """Execute a single hook"""
        import time
        start_time = time.time()

        try:
            if hook.hook_type == HookType.SHELL:
                result = await self._execute_shell_hook(hook, context)
            elif hook.hook_type == HookType.PYTHON:
                result = await self._execute_python_hook(hook, context)
            elif hook.hook_type == HookType.BUILTIN:
                result = await self._execute_builtin_hook(hook, context)
            else:
                result = HookResult(success=False, error=f"Unknown hook type: {hook.hook_type}")

        except asyncio.TimeoutError:
            result = HookResult(success=False, error="Hook timed out")
        except Exception as e:
            result = HookResult(success=False, error=str(e))

        result.duration = time.time() - start_time

        # Determine if we should continue
        if not result.success and hook.fail_on_error:
            result.should_continue = False

        return result

    async def _execute_shell_hook(self, hook: Hook, context: Dict[str, Any]) -> HookResult:
        """Execute a shell command hook"""
        # Substitute variables in command
        command = hook.command
        for key, value in context.items():
            command = command.replace(f"{{{key}}}", str(value))
            command = command.replace(f"${key}", str(value))

        # Build environment
        env = os.environ.copy()
        env.update(hook.env)
        for key, value in context.items():
            env[f"HOOK_{key.upper()}"] = str(value)

        try:
            if hook.blocking:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.working_dir),
                    env=env
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=hook.timeout
                    )

                    return HookResult(
                        success=process.returncode == 0,
                        output=stdout.decode() if stdout else "",
                        error=stderr.decode() if stderr else ""
                    )

                except asyncio.TimeoutError:
                    process.kill()
                    raise

            else:
                # Non-blocking - fire and forget
                subprocess.Popen(
                    command,
                    shell=True,
                    cwd=str(self.working_dir),
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return HookResult(success=True)

        except Exception as e:
            return HookResult(success=False, error=str(e))

    async def _execute_python_hook(self, hook: Hook, context: Dict[str, Any]) -> HookResult:
        """Execute a Python function hook"""
        if hook.command not in self._python_hooks:
            return HookResult(success=False, error=f"Python hook '{hook.command}' not registered")

        func = self._python_hooks[hook.command]

        try:
            return await func(context)
        except Exception as e:
            return HookResult(success=False, error=str(e))

    async def _execute_builtin_hook(self, hook: Hook, context: Dict[str, Any]) -> HookResult:
        """Execute a built-in hook"""
        # Built-in hooks would be implemented here
        return HookResult(success=True)

    # ==================== Display ====================

    def list_hooks(self, event: Optional[HookEvent] = None):
        """Display configured hooks"""
        hooks = list(self._hooks.values())

        if event:
            hooks = [h for h in hooks if h.event == event]

        if not hooks:
            self.console.print("[dim]No hooks configured[/dim]")
            return

        table = Table(title="Hooks", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="cyan")
        table.add_column("Event")
        table.add_column("Type")
        table.add_column("Command")
        table.add_column("Status")

        for hook in sorted(hooks, key=lambda h: (h.event.value, h.name)):
            status = "[green]enabled[/green]" if hook.enabled else "[dim]disabled[/dim]"

            table.add_row(
                hook.name,
                hook.event.value,
                hook.hook_type.value,
                hook.command[:30] + "..." if len(hook.command) > 30 else hook.command,
                status
            )

        self.console.print(table)

    def show_hook(self, name: str):
        """Show details of a specific hook"""
        hook = self._hooks.get(name)

        if not hook:
            self.console.print(f"[red]Hook '{name}' not found[/red]")
            return

        info_lines = []
        info_lines.append(f"[bold]Name:[/bold] {hook.name}")
        info_lines.append(f"[bold]Event:[/bold] {hook.event.value}")
        info_lines.append(f"[bold]Type:[/bold] {hook.hook_type.value}")
        info_lines.append(f"[bold]Command:[/bold] {hook.command}")
        info_lines.append(f"[bold]Enabled:[/bold] {'Yes' if hook.enabled else 'No'}")
        info_lines.append(f"[bold]Blocking:[/bold] {'Yes' if hook.blocking else 'No'}")
        info_lines.append(f"[bold]Fail on error:[/bold] {'Yes' if hook.fail_on_error else 'No'}")
        info_lines.append(f"[bold]Timeout:[/bold] {hook.timeout}s")

        if hook.description:
            info_lines.append(f"[bold]Description:[/bold] {hook.description}")

        if hook.patterns:
            info_lines.append(f"[bold]Patterns:[/bold] {', '.join(hook.patterns)}")

        if hook.env:
            info_lines.append(f"[bold]Environment:[/bold]")
            for k, v in hook.env.items():
                info_lines.append(f"  {k}={v}")

        content = "\n".join(info_lines)

        panel = Panel(
            Text.from_markup(content),
            title=f"[bold cyan]Hook: {name}[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

    def show_help(self):
        """Show help for hooks"""
        help_text = """
[bold cyan]Hooks System[/bold cyan]

Run custom commands before/after CLI operations.

[bold]Commands:[/bold]
  [green]/hooks list[/green]              List all hooks
  [green]/hooks add <name> <event> <cmd>[/green]  Add a hook
  [green]/hooks remove <name>[/green]     Remove a hook
  [green]/hooks enable <name>[/green]     Enable a hook
  [green]/hooks disable <name>[/green]    Disable a hook
  [green]/hooks show <name>[/green]       Show hook details

[bold]Events:[/bold]
  • session_start/end      Session lifecycle
  • pre/post_prompt        Before/after AI response
  • pre/post_file_write    Before/after file writes
  • pre/post_file_delete   Before/after file deletes
  • pre/post_bash          Before/after bash commands
  • pre/post_git_commit    Before/after git commits

[bold]Variables:[/bold]
  Hooks receive context variables:
  • {file} - File path for file events
  • {command} - Command for bash events
  • {prompt} - User prompt for prompt events

[bold]Examples:[/bold]
  /hooks add format post_file_write "prettier --write {file}" --patterns "*.js,*.ts"
  /hooks add test pre_git_commit "npm test" --fail-on-error
  /hooks add lint post_prompt "eslint src/"
"""
        panel = Panel(
            Text.from_markup(help_text),
            title="[bold]Hooks Help[/bold]",
            border_style="cyan"
        )
        self.console.print(panel)


# ==================== Common Hook Templates ====================

HOOK_TEMPLATES = {
    "prettier": {
        "event": "post_file_write",
        "command": "prettier --write {file}",
        "patterns": ["*.js", "*.ts", "*.jsx", "*.tsx", "*.json", "*.css"],
        "description": "Format files with Prettier"
    },
    "eslint": {
        "event": "post_file_write",
        "command": "eslint --fix {file}",
        "patterns": ["*.js", "*.ts", "*.jsx", "*.tsx"],
        "description": "Lint files with ESLint"
    },
    "black": {
        "event": "post_file_write",
        "command": "black {file}",
        "patterns": ["*.py"],
        "description": "Format Python files with Black"
    },
    "isort": {
        "event": "post_file_write",
        "command": "isort {file}",
        "patterns": ["*.py"],
        "description": "Sort Python imports with isort"
    },
    "test-on-commit": {
        "event": "pre_git_commit",
        "command": "npm test",
        "fail_on_error": True,
        "description": "Run tests before commit"
    }
}


def get_hook_template(name: str) -> Optional[Dict[str, Any]]:
    """Get a hook template"""
    return HOOK_TEMPLATES.get(name)


def list_hook_templates() -> List[str]:
    """List available hook templates"""
    return list(HOOK_TEMPLATES.keys())
