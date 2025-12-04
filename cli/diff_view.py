"""
BharatBuild CLI Diff View

Shows diff preview before file edits:
╭─ Changes to src/app.py ─────────────────────╮
│  10 │ - old line                            │
│  10 │ + new line                            │
│  11 │   unchanged line                      │
╰─────────────────────────────────────────────╯
"""

import difflib
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.table import Table
from rich.box import ROUNDED


class DiffType(str, Enum):
    """Types of diff lines"""
    ADDED = "added"
    REMOVED = "removed"
    UNCHANGED = "unchanged"
    HEADER = "header"
    HUNK = "hunk"


@dataclass
class DiffLine:
    """A line in a diff"""
    line_type: DiffType
    content: str
    old_line_num: Optional[int] = None
    new_line_num: Optional[int] = None


@dataclass
class DiffStats:
    """Statistics for a diff"""
    additions: int = 0
    deletions: int = 0
    changes: int = 0


class DiffRenderer:
    """
    Renders diffs in various formats.

    Usage:
        renderer = DiffRenderer(console)

        # Show unified diff
        renderer.show_unified_diff(old_content, new_content, "src/app.py")

        # Show side-by-side diff
        renderer.show_side_by_side(old_content, new_content)

        # Show inline diff with context
        renderer.show_inline_diff(old_content, new_content, context=3)
    """

    def __init__(self, console: Console):
        self.console = console

    def compute_diff(
        self,
        old_content: str,
        new_content: str,
        context: int = 3
    ) -> Tuple[List[DiffLine], DiffStats]:
        """
        Compute diff between two contents.

        Returns list of DiffLines and statistics.
        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff_lines = []
        stats = DiffStats()

        # Generate unified diff
        diff = list(difflib.unified_diff(
            old_lines,
            new_lines,
            lineterm='',
            n=context
        ))

        old_line_num = 0
        new_line_num = 0

        for line in diff:
            if line.startswith('---') or line.startswith('+++'):
                diff_lines.append(DiffLine(
                    line_type=DiffType.HEADER,
                    content=line.rstrip()
                ))
            elif line.startswith('@@'):
                diff_lines.append(DiffLine(
                    line_type=DiffType.HUNK,
                    content=line.rstrip()
                ))
                # Parse hunk header to get line numbers
                # Format: @@ -start,count +start,count @@
                parts = line.split()
                if len(parts) >= 3:
                    old_info = parts[1]  # -start,count
                    new_info = parts[2]  # +start,count
                    try:
                        old_line_num = int(old_info.split(',')[0][1:])
                        new_line_num = int(new_info.split(',')[0][1:])
                    except (ValueError, IndexError):
                        pass
            elif line.startswith('+'):
                diff_lines.append(DiffLine(
                    line_type=DiffType.ADDED,
                    content=line[1:].rstrip(),
                    new_line_num=new_line_num
                ))
                stats.additions += 1
                new_line_num += 1
            elif line.startswith('-'):
                diff_lines.append(DiffLine(
                    line_type=DiffType.REMOVED,
                    content=line[1:].rstrip(),
                    old_line_num=old_line_num
                ))
                stats.deletions += 1
                old_line_num += 1
            elif line.startswith(' '):
                diff_lines.append(DiffLine(
                    line_type=DiffType.UNCHANGED,
                    content=line[1:].rstrip(),
                    old_line_num=old_line_num,
                    new_line_num=new_line_num
                ))
                old_line_num += 1
                new_line_num += 1

        stats.changes = stats.additions + stats.deletions
        return diff_lines, stats

    def show_unified_diff(
        self,
        old_content: str,
        new_content: str,
        path: str,
        context: int = 3,
        show_line_numbers: bool = True
    ):
        """
        Show unified diff in a panel.

        ╭─ Changes to src/app.py (+5 -3) ─────────────────╮
        │ @@ -10,5 +10,7 @@                               │
        │  10 │   unchanged line                         │
        │  11 │ - removed line                           │
        │  11 │ + added line                             │
        ╰─────────────────────────────────────────────────╯
        """
        diff_lines, stats = self.compute_diff(old_content, new_content, context)

        if not diff_lines:
            self.console.print(f"[dim]No changes in {path}[/dim]")
            return

        # Build content
        content_lines = []

        for diff_line in diff_lines:
            if diff_line.line_type == DiffType.HEADER:
                continue  # Skip file headers
            elif diff_line.line_type == DiffType.HUNK:
                content_lines.append(f"[cyan]{diff_line.content}[/cyan]")
            elif diff_line.line_type == DiffType.ADDED:
                line_num = f"{diff_line.new_line_num:4}" if show_line_numbers and diff_line.new_line_num else "    "
                content_lines.append(f"[green]{line_num} │ + {diff_line.content}[/green]")
            elif diff_line.line_type == DiffType.REMOVED:
                line_num = f"{diff_line.old_line_num:4}" if show_line_numbers and diff_line.old_line_num else "    "
                content_lines.append(f"[red]{line_num} │ - {diff_line.content}[/red]")
            elif diff_line.line_type == DiffType.UNCHANGED:
                line_num = f"{diff_line.new_line_num:4}" if show_line_numbers and diff_line.new_line_num else "    "
                content_lines.append(f"[dim]{line_num} │   {diff_line.content}[/dim]")

        content = "\n".join(content_lines)

        # Build title with stats
        stats_text = f"[green]+{stats.additions}[/green] [red]-{stats.deletions}[/red]"
        title = f"Changes to [cyan]{path}[/cyan] ({stats_text})"

        panel = Panel(
            Text.from_markup(content),
            title=title,
            border_style="yellow",
            box=ROUNDED,
            padding=(0, 1)
        )

        self.console.print(panel)

    def show_side_by_side(
        self,
        old_content: str,
        new_content: str,
        path: str = "",
        width: int = 40
    ):
        """
        Show side-by-side diff.

        ╭─ src/app.py ────────────────────────────────────╮
        │ Old                      │ New                  │
        │──────────────────────────┼──────────────────────│
        │ old line                 │ new line             │
        ╰─────────────────────────────────────────────────╯
        """
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()

        # Use SequenceMatcher for alignment
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

        table = Table(
            title=f"[bold]{path}[/bold]" if path else None,
            show_header=True,
            header_style="bold",
            box=ROUNDED,
            padding=(0, 1)
        )

        table.add_column("Old", style="dim", width=width, overflow="fold")
        table.add_column("New", width=width, overflow="fold")

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for i in range(i2 - i1):
                    table.add_row(
                        old_lines[i1 + i][:width],
                        new_lines[j1 + i][:width]
                    )
            elif tag == 'replace':
                max_lines = max(i2 - i1, j2 - j1)
                for i in range(max_lines):
                    old_text = old_lines[i1 + i][:width] if i < i2 - i1 else ""
                    new_text = new_lines[j1 + i][:width] if i < j2 - j1 else ""
                    table.add_row(
                        f"[red]{old_text}[/red]",
                        f"[green]{new_text}[/green]"
                    )
            elif tag == 'delete':
                for i in range(i2 - i1):
                    table.add_row(
                        f"[red]{old_lines[i1 + i][:width]}[/red]",
                        ""
                    )
            elif tag == 'insert':
                for i in range(j2 - j1):
                    table.add_row(
                        "",
                        f"[green]{new_lines[j1 + i][:width]}[/green]"
                    )

        self.console.print(table)

    def show_inline_diff(
        self,
        old_content: str,
        new_content: str,
        path: str = "",
        context: int = 3
    ):
        """
        Show inline diff with word-level highlighting.
        """
        diff_lines, stats = self.compute_diff(old_content, new_content, context)

        if not diff_lines:
            self.console.print(f"[dim]No changes[/dim]")
            return

        # Title
        if path:
            stats_text = f"[green]+{stats.additions}[/green] [red]-{stats.deletions}[/red]"
            self.console.print(f"\n[bold]{path}[/bold] {stats_text}")

        # Show diff lines
        for diff_line in diff_lines:
            if diff_line.line_type == DiffType.HEADER:
                continue
            elif diff_line.line_type == DiffType.HUNK:
                self.console.print(f"[cyan]{diff_line.content}[/cyan]")
            elif diff_line.line_type == DiffType.ADDED:
                self.console.print(f"[green]+{diff_line.content}[/green]")
            elif diff_line.line_type == DiffType.REMOVED:
                self.console.print(f"[red]-{diff_line.content}[/red]")
            elif diff_line.line_type == DiffType.UNCHANGED:
                self.console.print(f"[dim] {diff_line.content}[/dim]")

    def show_summary(
        self,
        old_content: str,
        new_content: str,
        path: str
    ):
        """
        Show brief diff summary.

        src/app.py: +5 -3 (8 lines changed)
        """
        _, stats = self.compute_diff(old_content, new_content)

        self.console.print(
            f"[cyan]{path}[/cyan]: "
            f"[green]+{stats.additions}[/green] "
            f"[red]-{stats.deletions}[/red] "
            f"[dim]({stats.changes} lines changed)[/dim]"
        )

    def show_word_diff(
        self,
        old_line: str,
        new_line: str
    ) -> Text:
        """
        Show word-level diff between two lines.

        Returns Rich Text with highlighted changes.
        """
        old_words = old_line.split()
        new_words = new_line.split()

        matcher = difflib.SequenceMatcher(None, old_words, new_words)
        result = Text()

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                result.append(' '.join(old_words[i1:i2]) + ' ')
            elif tag == 'replace':
                result.append(' '.join(old_words[i1:i2]) + ' ', style="red strike")
                result.append(' '.join(new_words[j1:j2]) + ' ', style="green")
            elif tag == 'delete':
                result.append(' '.join(old_words[i1:i2]) + ' ', style="red strike")
            elif tag == 'insert':
                result.append(' '.join(new_words[j1:j2]) + ' ', style="green")

        return result


class DiffPreview:
    """
    Interactive diff preview before applying changes.

    Usage:
        preview = DiffPreview(console)
        approved = await preview.show(old_content, new_content, path)
        if approved:
            # Apply changes...
    """

    def __init__(self, console: Console):
        self.console = console
        self.renderer = DiffRenderer(console)

    async def show(
        self,
        old_content: str,
        new_content: str,
        path: str,
        show_full: bool = False
    ) -> bool:
        """
        Show diff preview and ask for approval.

        Returns True if approved, False otherwise.
        """
        from rich.prompt import Confirm

        # Show diff
        if show_full:
            self.renderer.show_unified_diff(old_content, new_content, path)
        else:
            # Show summary first
            _, stats = self.renderer.compute_diff(old_content, new_content)

            if stats.changes == 0:
                self.console.print(f"[dim]No changes to {path}[/dim]")
                return True

            self.console.print()
            self.console.print(
                f"[bold yellow]📝 Changes to {path}:[/bold yellow] "
                f"[green]+{stats.additions}[/green] [red]-{stats.deletions}[/red]"
            )

            # Show preview of first few changes
            diff_lines, _ = self.renderer.compute_diff(old_content, new_content, context=2)

            preview_lines = []
            count = 0
            for line in diff_lines:
                if line.line_type in (DiffType.ADDED, DiffType.REMOVED):
                    if line.line_type == DiffType.ADDED:
                        preview_lines.append(f"  [green]+ {line.content[:60]}[/green]")
                    else:
                        preview_lines.append(f"  [red]- {line.content[:60]}[/red]")
                    count += 1
                    if count >= 6:
                        preview_lines.append(f"  [dim]... and {stats.changes - 6} more changes[/dim]")
                        break

            for line in preview_lines:
                self.console.print(line)

            self.console.print()

        # Ask for approval
        return Confirm.ask("[yellow]Apply these changes?[/yellow]", default=True)


def create_diff_renderer(console: Console) -> DiffRenderer:
    """Create a diff renderer"""
    return DiffRenderer(console)


def create_diff_preview(console: Console) -> DiffPreview:
    """Create a diff preview"""
    return DiffPreview(console)
