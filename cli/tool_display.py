"""
BharatBuild CLI Tool Display - Claude Code Style Tool Use Boxes

Shows beautiful boxes for each tool operation:
╭─ Read file ─────────────────────────────────╮
│ src/app.py                                  │
╰─────────────────────────────────────────────╯
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.table import Table
from rich.box import ROUNDED, HEAVY, DOUBLE
from rich.padding import Padding


class ToolType(str, Enum):
    """Types of tools that can be displayed"""
    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    BASH = "bash"
    SEARCH = "search"
    GLOB = "glob"
    GREP = "grep"
    LIST = "list"
    DELETE = "delete"
    MOVE = "move"
    COPY = "copy"
    MKDIR = "mkdir"
    THINK = "think"
    WEB_FETCH = "web_fetch"
    WEB_SEARCH = "web_search"


@dataclass
class ToolDisplayConfig:
    """Configuration for tool display"""
    icon: str
    title: str
    border_style: str
    title_style: str


# Tool display configurations
TOOL_CONFIGS: Dict[ToolType, ToolDisplayConfig] = {
    ToolType.READ: ToolDisplayConfig(
        icon="📖",
        title="Read",
        border_style="blue",
        title_style="bold blue"
    ),
    ToolType.WRITE: ToolDisplayConfig(
        icon="📝",
        title="Write",
        border_style="green",
        title_style="bold green"
    ),
    ToolType.EDIT: ToolDisplayConfig(
        icon="✏️",
        title="Edit",
        border_style="yellow",
        title_style="bold yellow"
    ),
    ToolType.BASH: ToolDisplayConfig(
        icon="❯",
        title="Bash",
        border_style="cyan",
        title_style="bold cyan"
    ),
    ToolType.SEARCH: ToolDisplayConfig(
        icon="🔍",
        title="Search",
        border_style="magenta",
        title_style="bold magenta"
    ),
    ToolType.GLOB: ToolDisplayConfig(
        icon="📁",
        title="Glob",
        border_style="blue",
        title_style="bold blue"
    ),
    ToolType.GREP: ToolDisplayConfig(
        icon="🔎",
        title="Grep",
        border_style="magenta",
        title_style="bold magenta"
    ),
    ToolType.LIST: ToolDisplayConfig(
        icon="📋",
        title="List",
        border_style="blue",
        title_style="bold blue"
    ),
    ToolType.DELETE: ToolDisplayConfig(
        icon="🗑️",
        title="Delete",
        border_style="red",
        title_style="bold red"
    ),
    ToolType.MOVE: ToolDisplayConfig(
        icon="📦",
        title="Move",
        border_style="yellow",
        title_style="bold yellow"
    ),
    ToolType.COPY: ToolDisplayConfig(
        icon="📋",
        title="Copy",
        border_style="cyan",
        title_style="bold cyan"
    ),
    ToolType.MKDIR: ToolDisplayConfig(
        icon="📁",
        title="Create Directory",
        border_style="green",
        title_style="bold green"
    ),
    ToolType.THINK: ToolDisplayConfig(
        icon="💭",
        title="Thinking",
        border_style="dim",
        title_style="bold dim"
    ),
    ToolType.WEB_FETCH: ToolDisplayConfig(
        icon="🌐",
        title="Web Fetch",
        border_style="cyan",
        title_style="bold cyan"
    ),
    ToolType.WEB_SEARCH: ToolDisplayConfig(
        icon="🔍",
        title="Web Search",
        border_style="magenta",
        title_style="bold magenta"
    ),
}


class ToolDisplayRenderer:
    """
    Renders Claude Code style tool use boxes.

    Usage:
        renderer = ToolDisplayRenderer(console)

        # Show read operation
        renderer.show_read("src/app.py", content="...")

        # Show write operation
        renderer.show_write("src/utils.py", lines_added=45)

        # Show bash command
        renderer.show_bash("npm install express", output="...")
    """

    def __init__(self, console: Console):
        self.console = console

    def _create_tool_panel(
        self,
        tool_type: ToolType,
        content: Any,
        subtitle: Optional[str] = None,
        expanded: bool = False
    ) -> Panel:
        """Create a tool panel with consistent styling"""
        config = TOOL_CONFIGS.get(tool_type, TOOL_CONFIGS[ToolType.READ])

        title = f"{config.icon} {config.title}"
        if subtitle:
            title = f"{title} · {subtitle}"

        return Panel(
            content,
            title=f"[{config.title_style}]{title}[/{config.title_style}]",
            border_style=config.border_style,
            box=ROUNDED,
            padding=(0, 1),
            expand=expanded
        )

    def show_read(
        self,
        path: str,
        content: Optional[str] = None,
        lines: Optional[int] = None,
        show_content: bool = False,
        language: Optional[str] = None
    ):
        """
        Show read file operation.

        ╭─ 📖 Read · src/app.py ──────────────────╮
        │ 125 lines                               │
        ╰─────────────────────────────────────────╯
        """
        if show_content and content:
            # Detect language from extension
            if not language:
                ext = path.split('.')[-1] if '.' in path else 'text'
                lang_map = {
                    'py': 'python', 'js': 'javascript', 'ts': 'typescript',
                    'jsx': 'javascript', 'tsx': 'typescript', 'json': 'json',
                    'yaml': 'yaml', 'yml': 'yaml', 'md': 'markdown',
                    'html': 'html', 'css': 'css', 'sql': 'sql',
                    'sh': 'bash', 'bash': 'bash', 'rs': 'rust', 'go': 'go'
                }
                language = lang_map.get(ext, 'text')

            syntax = Syntax(
                content[:2000] + ("..." if len(content) > 2000 else ""),
                language,
                theme="dracula",
                line_numbers=True,
                word_wrap=True
            )
            display_content = syntax
        else:
            line_info = f"{lines} lines" if lines else ""
            if content:
                line_info = f"{len(content.splitlines())} lines"
            display_content = Text(f"[dim]{path}[/dim]\n{line_info}" if line_info else f"[dim]{path}[/dim]")

        panel = self._create_tool_panel(
            ToolType.READ,
            display_content,
            subtitle=path
        )
        self.console.print(panel)

    def show_write(
        self,
        path: str,
        content: Optional[str] = None,
        lines_added: int = 0,
        lines_removed: int = 0,
        show_content: bool = False,
        language: Optional[str] = None
    ):
        """
        Show write file operation.

        ╭─ 📝 Write · src/utils.py ───────────────╮
        │ +45 lines                               │
        ╰─────────────────────────────────────────╯
        """
        if show_content and content:
            if not language:
                ext = path.split('.')[-1] if '.' in path else 'text'
                lang_map = {
                    'py': 'python', 'js': 'javascript', 'ts': 'typescript',
                    'json': 'json', 'yaml': 'yaml', 'md': 'markdown'
                }
                language = lang_map.get(ext, 'text')

            syntax = Syntax(
                content[:1500] + ("..." if len(content) > 1500 else ""),
                language,
                theme="dracula",
                line_numbers=True
            )
            display_content = syntax
        else:
            stats = []
            if lines_added > 0:
                stats.append(f"[green]+{lines_added}[/green]")
            if lines_removed > 0:
                stats.append(f"[red]-{lines_removed}[/red]")

            if content and not stats:
                stats.append(f"[green]+{len(content.splitlines())} lines[/green]")

            stat_text = " ".join(stats) if stats else "[dim]created[/dim]"
            display_content = Text.from_markup(stat_text)

        panel = self._create_tool_panel(
            ToolType.WRITE,
            display_content,
            subtitle=path
        )
        self.console.print(panel)

    def show_edit(
        self,
        path: str,
        old_content: Optional[str] = None,
        new_content: Optional[str] = None,
        lines_changed: int = 0,
        description: Optional[str] = None
    ):
        """
        Show edit file operation with diff preview.

        ╭─ ✏️ Edit · src/app.py ──────────────────╮
        │ -5 +8 lines                             │
        │                                         │
        │ - old line                              │
        │ + new line                              │
        ╰─────────────────────────────────────────╯
        """
        content_parts = []

        # Stats line
        if old_content and new_content:
            old_lines = len(old_content.splitlines())
            new_lines = len(new_content.splitlines())
            content_parts.append(f"[red]-{old_lines}[/red] [green]+{new_lines}[/green] lines")
        elif lines_changed:
            content_parts.append(f"[yellow]~{lines_changed}[/yellow] lines changed")

        if description:
            content_parts.append(f"[dim]{description}[/dim]")

        # Show mini diff preview
        if old_content and new_content:
            import difflib
            diff = list(difflib.unified_diff(
                old_content.splitlines()[:5],
                new_content.splitlines()[:5],
                lineterm=""
            ))

            if len(diff) > 2:  # Skip header lines
                diff_preview = []
                for line in diff[2:8]:  # Show max 6 diff lines
                    if line.startswith('+'):
                        diff_preview.append(f"[green]{line}[/green]")
                    elif line.startswith('-'):
                        diff_preview.append(f"[red]{line}[/red]")
                    else:
                        diff_preview.append(f"[dim]{line}[/dim]")

                if diff_preview:
                    content_parts.append("")
                    content_parts.extend(diff_preview)

        display_content = Text.from_markup("\n".join(content_parts))

        panel = self._create_tool_panel(
            ToolType.EDIT,
            display_content,
            subtitle=path
        )
        self.console.print(panel)

    def show_bash(
        self,
        command: str,
        output: Optional[str] = None,
        exit_code: int = 0,
        duration: Optional[float] = None,
        show_output: bool = True
    ):
        """
        Show bash command execution.

        ╭─ ❯ Bash ────────────────────────────────╮
        │ $ npm install express                   │
        │                                         │
        │ added 50 packages in 2.5s               │
        ╰─────────────────────────────────────────╯
        """
        content_parts = []

        # Command line
        content_parts.append(f"[bold cyan]$[/bold cyan] {command}")

        # Output
        if show_output and output:
            content_parts.append("")
            # Truncate long output
            output_lines = output.strip().splitlines()
            if len(output_lines) > 15:
                display_output = "\n".join(output_lines[:12])
                display_output += f"\n[dim]... ({len(output_lines) - 12} more lines)[/dim]"
            else:
                display_output = output.strip()
            content_parts.append(display_output)

        # Status line
        status_parts = []
        if exit_code == 0:
            status_parts.append("[green]✓[/green]")
        else:
            status_parts.append(f"[red]✗ exit {exit_code}[/red]")

        if duration:
            status_parts.append(f"[dim]{duration:.2f}s[/dim]")

        if status_parts:
            content_parts.append("")
            content_parts.append(" ".join(status_parts))

        display_content = Text.from_markup("\n".join(content_parts))

        panel = self._create_tool_panel(
            ToolType.BASH,
            display_content
        )
        self.console.print(panel)

    def show_search(
        self,
        query: str,
        results: List[Dict[str, Any]] = None,
        total_matches: int = 0
    ):
        """
        Show search operation.

        ╭─ 🔍 Search · "authenticate" ────────────╮
        │ Found 5 matches in 3 files              │
        │                                         │
        │ src/auth.py:45                          │
        │ src/middleware.py:23                    │
        ╰─────────────────────────────────────────╯
        """
        content_parts = []

        # Summary
        if results:
            files = len(set(r.get('file', '') for r in results))
            content_parts.append(f"Found [cyan]{total_matches or len(results)}[/cyan] matches in [cyan]{files}[/cyan] files")
        else:
            content_parts.append(f"[dim]Searching for: {query}[/dim]")

        # Results preview
        if results:
            content_parts.append("")
            for result in results[:8]:
                file_path = result.get('file', '')
                line_num = result.get('line', '')
                preview = result.get('preview', '')[:50]

                if line_num:
                    content_parts.append(f"[cyan]{file_path}:{line_num}[/cyan]")
                else:
                    content_parts.append(f"[cyan]{file_path}[/cyan]")

                if preview:
                    content_parts.append(f"  [dim]{preview}[/dim]")

            if len(results) > 8:
                content_parts.append(f"[dim]... and {len(results) - 8} more[/dim]")

        display_content = Text.from_markup("\n".join(content_parts))

        panel = self._create_tool_panel(
            ToolType.SEARCH,
            display_content,
            subtitle=f'"{query}"'
        )
        self.console.print(panel)

    def show_glob(
        self,
        pattern: str,
        files: List[str] = None,
        total: int = 0
    ):
        """Show glob/file search operation"""
        content_parts = []

        if files:
            content_parts.append(f"Found [cyan]{total or len(files)}[/cyan] files")
            content_parts.append("")
            for f in files[:10]:
                content_parts.append(f"  [dim]📄[/dim] {f}")
            if len(files) > 10:
                content_parts.append(f"  [dim]... and {len(files) - 10} more[/dim]")
        else:
            content_parts.append(f"[dim]Pattern: {pattern}[/dim]")

        display_content = Text.from_markup("\n".join(content_parts))

        panel = self._create_tool_panel(
            ToolType.GLOB,
            display_content,
            subtitle=pattern
        )
        self.console.print(panel)

    def show_thinking(
        self,
        thoughts: str,
        title: str = "Thinking"
    ):
        """
        Show extended thinking display.

        ╭─ 💭 Thinking ───────────────────────────╮
        │ Let me analyze the codebase...          │
        │ I see there are 3 main modules...       │
        │ The best approach would be...           │
        ╰─────────────────────────────────────────╯
        """
        # Word wrap thoughts
        lines = []
        for line in thoughts.split('\n'):
            if len(line) > 60:
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line) + len(word) + 1 <= 60:
                        current_line += (" " if current_line else "") + word
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)
            else:
                lines.append(line)

        display_content = Text("\n".join(lines), style="dim italic")

        panel = self._create_tool_panel(
            ToolType.THINK,
            display_content,
            subtitle=title if title != "Thinking" else None
        )
        self.console.print(panel)

    def show_web_fetch(
        self,
        url: str,
        status: str = "fetching",
        content_preview: Optional[str] = None
    ):
        """Show web fetch operation"""
        content_parts = []

        content_parts.append(f"[cyan]{url}[/cyan]")

        if status == "fetching":
            content_parts.append("[dim]Fetching...[/dim]")
        elif status == "success":
            content_parts.append("[green]✓ Fetched successfully[/green]")
            if content_preview:
                content_parts.append("")
                content_parts.append(f"[dim]{content_preview[:200]}...[/dim]")
        elif status == "error":
            content_parts.append("[red]✗ Failed to fetch[/red]")

        display_content = Text.from_markup("\n".join(content_parts))

        panel = self._create_tool_panel(
            ToolType.WEB_FETCH,
            display_content
        )
        self.console.print(panel)

    def show_web_search(
        self,
        query: str,
        results: List[Dict[str, str]] = None
    ):
        """Show web search operation"""
        content_parts = []

        if results:
            content_parts.append(f"Found [cyan]{len(results)}[/cyan] results")
            content_parts.append("")
            for r in results[:5]:
                title = r.get('title', 'Untitled')[:50]
                url = r.get('url', '')
                content_parts.append(f"  [bold]{title}[/bold]")
                content_parts.append(f"  [dim]{url}[/dim]")
        else:
            content_parts.append(f"[dim]Searching: {query}[/dim]")

        display_content = Text.from_markup("\n".join(content_parts))

        panel = self._create_tool_panel(
            ToolType.WEB_SEARCH,
            display_content,
            subtitle=f'"{query}"'
        )
        self.console.print(panel)

    def show_delete(self, path: str, confirmed: bool = False):
        """Show delete operation"""
        if confirmed:
            content = Text.from_markup(f"[red]Deleted: {path}[/red]")
        else:
            content = Text.from_markup(f"[yellow]Will delete: {path}[/yellow]")

        panel = self._create_tool_panel(
            ToolType.DELETE,
            content,
            subtitle=path
        )
        self.console.print(panel)

    def show_mkdir(self, path: str):
        """Show directory creation"""
        content = Text.from_markup(f"[green]Created directory: {path}[/green]")

        panel = self._create_tool_panel(
            ToolType.MKDIR,
            content,
            subtitle=path
        )
        self.console.print(panel)


# Convenience function
def create_tool_display(console: Console) -> ToolDisplayRenderer:
    """Create a tool display renderer"""
    return ToolDisplayRenderer(console)
