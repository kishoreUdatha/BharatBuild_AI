"""
Response Renderer - Handles terminal output rendering

Provides rich, syntax-highlighted output similar to Claude Code.
Features:
- Consistent theming with Claude Code style
- Syntax highlighting for 50+ languages
- Beautiful panels, tables, and progress bars
- Streaming markdown support
"""

import os
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.rule import Rule
from rich.padding import Padding
from rich.box import ROUNDED, DOUBLE, SIMPLE

from cli.config import CLIConfig
from cli.theme import CLITheme, ThemeMode, CLIIcons, BoxChars, get_icons
from cli.spinners import (
    MessageRotator,
    get_thinking_message,
    get_message_for_action,
    get_completion_message,
    SPINNER_FRAMES
)


# Language detection based on file extension
LANGUAGE_MAP = {
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.html': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.json': 'json',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
    '.md': 'markdown',
    '.sql': 'sql',
    '.sh': 'bash',
    '.bash': 'bash',
    '.zsh': 'bash',
    '.ps1': 'powershell',
    '.bat': 'batch',
    '.cmd': 'batch',
    '.go': 'go',
    '.rs': 'rust',
    '.rb': 'ruby',
    '.java': 'java',
    '.kt': 'kotlin',
    '.scala': 'scala',
    '.c': 'c',
    '.cpp': 'cpp',
    '.h': 'c',
    '.hpp': 'cpp',
    '.cs': 'csharp',
    '.php': 'php',
    '.swift': 'swift',
    '.r': 'r',
    '.R': 'r',
    '.xml': 'xml',
    '.vue': 'vue',
    '.svelte': 'svelte',
    '.dockerfile': 'dockerfile',
    '.makefile': 'makefile',
    '.env': 'bash',
    '.gitignore': 'gitignore',
}


class ResponseRenderer:
    """Renders responses in the terminal with rich formatting"""

    def __init__(self, console: Console, config: CLIConfig):
        self.console = console
        self.config = config
        self._streaming_buffer = ""
        self.theme = CLITheme(ThemeMode(config.theme) if config.theme != "auto" else ThemeMode.AUTO)
        self.icons = get_icons()
        self.messages = MessageRotator()  # Rotating loading messages

    def _get_language(self, path: str) -> str:
        """Detect language from file path"""
        ext = Path(path).suffix.lower()
        name = Path(path).name.lower()

        # Check by filename first
        if name == 'dockerfile':
            return 'dockerfile'
        if name == 'makefile':
            return 'makefile'
        if name.startswith('.env'):
            return 'bash'

        return LANGUAGE_MAP.get(ext, 'text')

    def render_file(self, path: str, content: str, show_line_numbers: bool = True):
        """Render a file with syntax highlighting"""
        language = self._get_language(path)

        # Create syntax-highlighted code
        syntax = Syntax(
            content,
            language,
            theme=self.config.syntax_theme,
            line_numbers=show_line_numbers,
            word_wrap=True
        )

        # Wrap in panel
        panel = Panel(
            syntax,
            title=f"[bold]{path}[/bold]",
            border_style="green",
            padding=(0, 1)
        )

        self.console.print(panel)

    def render_diff(self, path: str, old_content: str, new_content: str):
        """Render a diff between old and new content"""
        import difflib

        diff = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}"
        )

        diff_text = ''.join(diff)

        if diff_text:
            syntax = Syntax(diff_text, "diff", theme=self.config.syntax_theme)
            panel = Panel(
                syntax,
                title=f"[bold]Changes: {path}[/bold]",
                border_style="yellow"
            )
            self.console.print(panel)

    def render_command_result(self, command: str, result):
        """Render command execution result"""
        # Command header
        self.console.print(f"\n[bold cyan]$[/bold cyan] {command}")

        # Output
        if result.stdout:
            self.console.print(result.stdout, end="")

        # Errors
        if result.stderr and result.exit_code != 0:
            self.console.print(f"[red]{result.stderr}[/red]", end="")

        # Status
        if result.exit_code == 0:
            self.console.print(f"[dim]✓ Completed in {result.duration:.2f}s[/dim]")
        else:
            self.console.print(f"[red]✗ Exit code: {result.exit_code} ({result.duration:.2f}s)[/red]")

    def render_streaming_content(self, content: str):
        """Render streaming content (called repeatedly)"""
        # Buffer content for markdown rendering
        self._streaming_buffer += content

        # For now, just print raw content
        # TODO: Implement proper markdown streaming
        self.console.print(content, end="")

    def flush_streaming_buffer(self):
        """Flush the streaming buffer and render markdown"""
        if self._streaming_buffer:
            # Try to render as markdown
            try:
                md = Markdown(self._streaming_buffer)
                self.console.print()  # New line
                self.console.print(md)
            except Exception:
                # Fallback to plain text
                self.console.print(self._streaming_buffer)

            self._streaming_buffer = ""

    def render_markdown(self, content: str):
        """Render markdown content"""
        md = Markdown(content)
        self.console.print(md)

    def render_plan(self, tasks: list):
        """Render a task plan"""
        table = Table(title="📋 Execution Plan", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Task", style="white")
        table.add_column("Status", justify="center", width=10)

        for i, task in enumerate(tasks, 1):
            title = task.get("title", task.get("name", ""))
            status = task.get("status", "pending")

            if status == "complete":
                status_icon = "[green]✓[/green]"
            elif status == "in_progress":
                status_icon = "[yellow]⟳[/yellow]"
            else:
                status_icon = "[dim]○[/dim]"

            table.add_row(str(i), title, status_icon)

        self.console.print(table)

    def render_files_created(self, files: list):
        """Render list of created files"""
        if not files:
            return

        self.console.print("\n[bold green]📁 Files Created:[/bold green]")
        for f in files:
            self.console.print(f"  [green]✓[/green] {f}")

    def render_error(self, message: str, details: Optional[str] = None):
        """Render an error message"""
        error_panel = Panel(
            f"[bold red]{message}[/bold red]" +
            (f"\n\n[dim]{details}[/dim]" if details else ""),
            title="[red]Error[/red]",
            border_style="red"
        )
        self.console.print(error_panel)

    def render_warning(self, message: str):
        """Render a warning message"""
        self.console.print(f"[yellow]⚠️  {message}[/yellow]")

    def render_success(self, message: str):
        """Render a success message"""
        self.console.print(f"[green]✅ {message}[/green]")

    def render_info(self, message: str):
        """Render an info message"""
        self.console.print(f"[blue]ℹ️  {message}[/blue]")

    def render_thinking(self, message: str = "Thinking..."):
        """Render thinking indicator"""
        return self.console.status(f"[bold cyan]{message}[/bold cyan]", spinner="dots")

    def render_progress(self, tasks: list):
        """Render progress bar for tasks"""
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        )
        return progress

    def render_token_usage(self, usage: Dict[str, Any]):
        """Render token usage information"""
        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        table.add_row("Input tokens", str(usage.get("input_tokens", 0)))
        table.add_row("Output tokens", str(usage.get("output_tokens", 0)))
        table.add_row("Total tokens", str(usage.get("total_tokens", 0)))

        if "cost" in usage:
            table.add_row("Cost", f"${usage['cost']:.4f}")

        self.console.print(table)

    def render_help(self, commands: Dict[str, str]):
        """Render help information"""
        table = Table(title="Available Commands", show_header=True, header_style="bold cyan")
        table.add_column("Command", style="green")
        table.add_column("Description")

        for cmd, desc in commands.items():
            table.add_row(cmd, desc)

        self.console.print(table)

    def render_config(self, config: Dict[str, Any]):
        """Render configuration"""
        table = Table(title="Configuration", show_header=True, header_style="bold cyan")
        table.add_column("Setting", style="green")
        table.add_column("Value")

        for key, value in config.items():
            if isinstance(value, (list, dict)):
                value = str(value)
            table.add_row(key, str(value))

        self.console.print(table)

    def clear(self):
        """Clear the console"""
        self.console.clear()

    # ==================== Claude Code Style Methods ====================

    def render_welcome_banner(self, version: str = "1.0.0"):
        """Render Claude Code style welcome banner"""
        banner = f"""
[bold cyan]╭──────────────────────────────────────────────────────────╮[/bold cyan]
[bold cyan]│[/bold cyan]                                                          [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan]   [bold white]BharatBuild AI[/bold white] [dim]v{version}[/dim]                              [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan]   [dim]Claude Code Style CLI for AI-driven development[/dim]    [bold cyan]│[/bold cyan]
[bold cyan]│[/bold cyan]                                                          [bold cyan]│[/bold cyan]
[bold cyan]╰──────────────────────────────────────────────────────────╯[/bold cyan]
"""
        self.console.print(banner)

    def render_prompt_header(self, cwd: str, git_branch: Optional[str] = None):
        """Render the prompt header with path and git info"""
        parts = []
        parts.append(f"[bold cyan]❯[/bold cyan]")
        parts.append(f"[green]{cwd}[/green]")

        if git_branch:
            parts.append(f"[dim]on[/dim] [magenta]{git_branch}[/magenta]")

        self.console.print(" ".join(parts))

    def render_agent_status(self, agent_name: str, status: str, message: str = ""):
        """Render agent status like Claude Code"""
        status_icons = {
            "thinking": f"[yellow]{self.icons.thinking}[/yellow]",
            "working": f"[cyan]◐[/cyan]",
            "complete": f"[green]{self.icons.success}[/green]",
            "error": f"[red]{self.icons.error}[/red]",
        }

        icon = status_icons.get(status, "[dim]○[/dim]")
        self.console.print(f"  {icon} [bold]{agent_name}[/bold] {message}")

    def render_file_operation(self, operation: str, path: str, status: str = "success"):
        """Render file operation (create, update, delete)"""
        op_styles = {
            "create": ("[green]+[/green]", "Created"),
            "update": ("[yellow]~[/yellow]", "Updated"),
            "delete": ("[red]-[/red]", "Deleted"),
            "read": ("[blue]○[/blue]", "Read"),
        }

        icon, label = op_styles.get(operation, ("[dim]○[/dim]", operation))

        if status == "success":
            self.console.print(f"  {icon} {label}: [cyan]{path}[/cyan]")
        else:
            self.console.print(f"  [red]{self.icons.error}[/red] Failed: [dim]{path}[/dim]")

    def render_command_execution(self, command: str, cwd: Optional[str] = None):
        """Render command being executed"""
        self.console.print()
        if cwd:
            self.console.print(f"[dim]{cwd}[/dim]")
        self.console.print(f"[bold cyan]$[/bold cyan] {command}")

    def render_step(self, step_num: int, total: int, title: str, status: str = "pending"):
        """Render a workflow step"""
        status_styles = {
            "pending": "[dim]○[/dim]",
            "running": "[yellow]◐[/yellow]",
            "complete": "[green]●[/green]",
            "error": "[red]✗[/red]",
            "skipped": "[dim]⊘[/dim]",
        }

        icon = status_styles.get(status, "[dim]○[/dim]")
        progress = f"[dim]({step_num}/{total})[/dim]"

        self.console.print(f"  {icon} {progress} {title}")

    def render_code_block(self, code: str, language: str = "python", title: Optional[str] = None):
        """Render a code block with syntax highlighting"""
        syntax = Syntax(
            code,
            language,
            theme="dracula",  # Claude Code uses similar dark theme
            line_numbers=True,
            word_wrap=True
        )

        panel = Panel(
            syntax,
            title=f"[bold cyan]{title}[/bold cyan]" if title else None,
            border_style="cyan",
            box=ROUNDED,
            padding=(0, 1)
        )

        self.console.print(panel)

    def render_diff_block(self, path: str, additions: int, deletions: int, preview: str = ""):
        """Render a diff summary block"""
        stats = f"[green]+{additions}[/green] [red]-{deletions}[/red]"

        self.console.print(f"\n[bold]{path}[/bold] {stats}")
        if preview:
            for line in preview.split("\n")[:5]:
                if line.startswith("+"):
                    self.console.print(f"[green]{line}[/green]")
                elif line.startswith("-"):
                    self.console.print(f"[red]{line}[/red]")
                else:
                    self.console.print(f"[dim]{line}[/dim]")

    def render_tool_call(self, tool_name: str, params: Dict[str, Any] = None):
        """Render a tool being called"""
        self.console.print(f"\n[bold magenta]⚡ {tool_name}[/bold magenta]")
        if params:
            for key, value in params.items():
                display_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                self.console.print(f"  [dim]{key}:[/dim] {display_value}")

    def render_tool_result(self, success: bool, message: str = ""):
        """Render tool result"""
        if success:
            self.console.print(f"[green]{self.icons.success} {message or 'Success'}[/green]")
        else:
            self.console.print(f"[red]{self.icons.error} {message or 'Failed'}[/red]")

    def render_thinking(self, message: str = None, action: str = "think"):
        """
        Render thinking indicator with rotating messages.

        Args:
            message: Custom message (if None, uses rotating messages)
            action: Action type for contextual messages
        """
        if message is None:
            message = self.messages.for_action(action)

        return self.console.status(
            f"[bold cyan]{message}[/bold cyan]",
            spinner="dots",
            spinner_style="cyan"
        )

    def render_generating(self, message: str = None):
        """Render generating indicator with rotating messages"""
        if message is None:
            message = self.messages.generating()

        return self.console.status(
            f"[bold yellow]⚡ {message}[/bold yellow]",
            spinner="dots2",
            spinner_style="yellow"
        )

    def render_analyzing(self, message: str = None):
        """Render analyzing indicator"""
        if message is None:
            message = self.messages.analyzing()

        return self.console.status(
            f"[bold blue]🔍 {message}[/bold blue]",
            spinner="dots",
            spinner_style="blue"
        )

    def render_building(self, message: str = None):
        """Render building indicator"""
        if message is None:
            message = self.messages.building()

        return self.console.status(
            f"[bold magenta]🔨 {message}[/bold magenta]",
            spinner="dots2",
            spinner_style="magenta"
        )

    def render_searching(self, message: str = None):
        """Render searching indicator"""
        if message is None:
            message = self.messages.searching()

        return self.console.status(
            f"[bold cyan]🔍 {message}[/bold cyan]",
            spinner="dots",
            spinner_style="cyan"
        )

    def render_fixing(self, message: str = None):
        """Render fixing/debugging indicator"""
        if message is None:
            message = self.messages.fixing()

        return self.console.status(
            f"[bold yellow]🔧 {message}[/bold yellow]",
            spinner="dots",
            spinner_style="yellow"
        )

    def render_completion(self, message: str = None):
        """Render completion message"""
        if message is None:
            message = self.messages.completion()

        self.console.print(f"[bold green]✓ {message}[/bold green]")

    def render_section_header(self, title: str, icon: str = ""):
        """Render a section header"""
        self.console.print()
        self.console.print(Rule(f"[bold cyan]{icon} {title}[/bold cyan]", style="cyan"))

    def render_project_summary(self, project_name: str, files_count: int, lines_count: int = 0):
        """Render project generation summary"""
        panel_content = f"""
[bold white]{project_name}[/bold white]

[green]{self.icons.success}[/green] {files_count} files generated
[blue]{self.icons.code}[/blue] {lines_count:,} lines of code
"""
        panel = Panel(
            panel_content,
            title="[bold green]✨ Project Created[/bold green]",
            border_style="green",
            box=ROUNDED
        )
        self.console.print(panel)

    def render_cost_summary(self, input_tokens: int, output_tokens: int, cost: float):
        """Render token usage and cost summary"""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Label", style="dim")
        table.add_column("Value", justify="right")

        table.add_row("Input tokens", f"[cyan]{input_tokens:,}[/cyan]")
        table.add_row("Output tokens", f"[cyan]{output_tokens:,}[/cyan]")
        table.add_row("Total cost", f"[green]${cost:.4f}[/green]")

        self.console.print(table)

    def render_keyboard_hint(self, hints: Dict[str, str]):
        """Render keyboard shortcuts hint"""
        hint_parts = []
        for key, action in hints.items():
            hint_parts.append(f"[dim]{key}[/dim] {action}")

        self.console.print("  ".join(hint_parts))

    def render_divider(self, style: str = "dim"):
        """Render a horizontal divider"""
        self.console.print(Rule(style=style))

    def render_compact_file_tree(self, files: list, max_show: int = 10):
        """Render a compact file tree"""
        self.console.print(f"\n[bold]{self.icons.folder} Files:[/bold]")

        for i, f in enumerate(files[:max_show]):
            if isinstance(f, dict):
                path = f.get("path", str(f))
            else:
                path = str(f)

            icon = self.icons.folder if "/" in path or "\\" in path else self.icons.file
            self.console.print(f"  [dim]{icon}[/dim] {path}")

        if len(files) > max_show:
            remaining = len(files) - max_show
            self.console.print(f"  [dim]... and {remaining} more files[/dim]")

    # ==================== Claude Code Progress Status ====================

    def format_tokens(self, tokens: int) -> str:
        """Format token count for display (1.8k, 2.3k, etc.)"""
        if tokens >= 1000:
            return f"{tokens / 1000:.1f}k"
        return str(tokens)

    def format_elapsed(self, seconds: float) -> str:
        """Format elapsed time for display"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins}m"


class ProgressStatus:
    """
    Claude Code style progress status with elapsed time and token count.

    Shows: ⠋ Calculating… (esc to interrupt · 47s · ↓ 1.8k tokens)

    Usage:
        with renderer.progress_status() as status:
            # Do work...
            status.update_tokens(1500)
            status.update_message("Generating code...")
    """

    def __init__(
        self,
        console: Console,
        messages: MessageRotator,
        initial_message: str = None,
        action: str = "think",
        show_escape_hint: bool = True
    ):
        self.console = console
        self.messages = messages
        self.action = action
        self.show_escape_hint = show_escape_hint

        # State
        self._message = initial_message or messages.for_action(action)
        self._tokens = 0
        self._start_time = None
        self._running = False
        self._spinner_idx = 0
        self._lock = threading.Lock()
        self._thread = None

        # Spinner frames
        self._spinner_frames = SPINNER_FRAMES["dots"]

    def _format_status_line(self) -> str:
        """Format the complete status line"""
        spinner = self._spinner_frames[self._spinner_idx % len(self._spinner_frames)]

        # Calculate elapsed time
        elapsed = time.time() - self._start_time if self._start_time else 0
        elapsed_str = self._format_elapsed(elapsed)

        # Build status parts
        parts = []

        if self.show_escape_hint:
            parts.append("esc to interrupt")

        parts.append(elapsed_str)

        if self._tokens > 0:
            token_str = self._format_tokens(self._tokens)
            parts.append(f"↓ {token_str} tokens")

        status_info = " · ".join(parts)

        return f"[cyan]{spinner}[/cyan] [bold cyan]{self._message}[/bold cyan] [dim]({status_info})[/dim]"

    def _format_tokens(self, tokens: int) -> str:
        """Format token count"""
        if tokens >= 1000:
            return f"{tokens / 1000:.1f}k"
        return str(tokens)

    def _format_elapsed(self, seconds: float) -> str:
        """Format elapsed time"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins}m"

    def _update_loop(self):
        """Background thread to update spinner and time"""
        while self._running:
            with self._lock:
                # Clear line and rewrite
                self.console.print(f"\r{self._format_status_line()}", end="")
                self._spinner_idx += 1
            time.sleep(0.1)  # 100ms refresh rate

    def update_message(self, message: str):
        """Update the status message"""
        with self._lock:
            self._message = message

    def update_tokens(self, tokens: int):
        """Update the token count"""
        with self._lock:
            self._tokens = tokens

    def add_tokens(self, tokens: int):
        """Add to the token count"""
        with self._lock:
            self._tokens += tokens

    def rotate_message(self):
        """Rotate to next contextual message"""
        with self._lock:
            self._message = self.messages.for_action(self.action)

    def start(self):
        """Start the progress display"""
        self._start_time = time.time()
        self._running = True
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the progress display"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.5)
        # Clear the line
        self.console.print("\r" + " " * 100 + "\r", end="")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


class LiveProgressStatus:
    """
    Alternative implementation using Rich's Live for cleaner rendering.

    Shows: ⠋ Calculating… (esc to interrupt · 47s · ↓ 1.8k tokens)
    """

    def __init__(
        self,
        console: Console,
        messages: MessageRotator,
        initial_message: str = None,
        action: str = "think",
        show_escape_hint: bool = True
    ):
        self.console = console
        self.messages = messages
        self.action = action
        self.show_escape_hint = show_escape_hint

        # State
        self._message = initial_message or messages.for_action(action)
        self._tokens = 0
        self._start_time = None
        self._spinner_idx = 0
        self._lock = threading.Lock()

        # Spinner frames
        self._spinner_frames = SPINNER_FRAMES["dots"]

        # Rich Live display
        self._live = None
        self._update_thread = None
        self._running = False

    def _get_renderable(self) -> Text:
        """Get the renderable for Live display"""
        spinner = self._spinner_frames[self._spinner_idx % len(self._spinner_frames)]

        # Calculate elapsed time
        elapsed = time.time() - self._start_time if self._start_time else 0
        elapsed_str = self._format_elapsed(elapsed)

        # Build status parts
        parts = []

        if self.show_escape_hint:
            parts.append("esc to interrupt")

        parts.append(elapsed_str)

        if self._tokens > 0:
            token_str = self._format_tokens(self._tokens)
            parts.append(f"↓ {token_str} tokens")

        status_info = " · ".join(parts)

        # Create Rich Text object
        text = Text()
        text.append(f"{spinner} ", style="cyan")
        text.append(self._message, style="bold cyan")
        text.append(f" ({status_info})", style="dim")

        return text

    def _format_tokens(self, tokens: int) -> str:
        if tokens >= 1000:
            return f"{tokens / 1000:.1f}k"
        return str(tokens)

    def _format_elapsed(self, seconds: float) -> str:
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins}m"

    def _update_loop(self):
        """Background thread to update display"""
        while self._running:
            with self._lock:
                self._spinner_idx += 1
                if self._live:
                    self._live.update(self._get_renderable())
            time.sleep(0.1)

    def update_message(self, message: str):
        """Update the status message"""
        with self._lock:
            self._message = message

    def update_tokens(self, tokens: int):
        """Update the token count"""
        with self._lock:
            self._tokens = tokens

    def add_tokens(self, tokens: int):
        """Add to the token count"""
        with self._lock:
            self._tokens += tokens

    def rotate_message(self):
        """Rotate to next contextual message"""
        with self._lock:
            self._message = self.messages.for_action(self.action)

    def start(self):
        """Start the progress display"""
        self._start_time = time.time()
        self._running = True
        self._live = Live(
            self._get_renderable(),
            console=self.console,
            refresh_per_second=10,
            transient=True
        )
        self._live.start()
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()

    def stop(self):
        """Stop the progress display"""
        self._running = False
        if self._update_thread:
            self._update_thread.join(timeout=0.5)
        if self._live:
            self._live.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


# Add factory method to ResponseRenderer
def _create_progress_status(self, message: str = None, action: str = "think", show_escape_hint: bool = True) -> LiveProgressStatus:
    """
    Create a Claude Code style progress status.

    Usage:
        with renderer.progress_status() as status:
            async for chunk in stream:
                status.add_tokens(chunk.tokens)

        # Or with custom message:
        with renderer.progress_status("Generating code...", action="generate") as status:
            ...
    """
    return LiveProgressStatus(
        console=self.console,
        messages=self.messages,
        initial_message=message,
        action=action,
        show_escape_hint=show_escape_hint
    )

# Monkey-patch to add method (cleaner than modifying class definition)
ResponseRenderer.progress_status = _create_progress_status
