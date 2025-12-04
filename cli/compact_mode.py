"""
BharatBuild CLI Compact Mode

Minimal UI mode for reduced output:
  /compact on    Enable compact mode
  /compact off   Disable compact mode
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from rich.console import Console
from rich.text import Text


class OutputMode(str, Enum):
    """Output mode settings"""
    FULL = "full"           # Full verbose output
    COMPACT = "compact"     # Minimal output
    QUIET = "quiet"         # Only essential output
    JSON = "json"           # JSON output for scripting


@dataclass
class CompactModeSettings:
    """Settings for compact mode"""
    show_thinking: bool = False
    show_tool_calls: bool = False
    show_file_contents: bool = False
    show_command_output: bool = True
    show_progress: bool = True
    show_token_usage: bool = False
    show_timestamps: bool = False
    show_icons: bool = True
    max_output_lines: int = 10
    truncate_paths: bool = True
    single_line_status: bool = True


# Preset configurations
MODE_PRESETS = {
    OutputMode.FULL: CompactModeSettings(
        show_thinking=True,
        show_tool_calls=True,
        show_file_contents=True,
        show_command_output=True,
        show_progress=True,
        show_token_usage=True,
        show_timestamps=True,
        show_icons=True,
        max_output_lines=50,
        truncate_paths=False,
        single_line_status=False
    ),
    OutputMode.COMPACT: CompactModeSettings(
        show_thinking=False,
        show_tool_calls=False,
        show_file_contents=False,
        show_command_output=True,
        show_progress=True,
        show_token_usage=False,
        show_timestamps=False,
        show_icons=True,
        max_output_lines=10,
        truncate_paths=True,
        single_line_status=True
    ),
    OutputMode.QUIET: CompactModeSettings(
        show_thinking=False,
        show_tool_calls=False,
        show_file_contents=False,
        show_command_output=False,
        show_progress=False,
        show_token_usage=False,
        show_timestamps=False,
        show_icons=False,
        max_output_lines=5,
        truncate_paths=True,
        single_line_status=True
    ),
}


class CompactModeManager:
    """
    Manages output modes and compact display.

    Usage:
        manager = CompactModeManager(console)

        # Enable compact mode
        manager.set_mode(OutputMode.COMPACT)

        # Check settings
        if manager.settings.show_tool_calls:
            # Show tool call...

        # Render in appropriate mode
        manager.print_status("Processing files...")
        manager.print_file_created("src/app.py")
    """

    def __init__(self, console: Console):
        self.console = console
        self._mode = OutputMode.FULL
        self._settings = MODE_PRESETS[OutputMode.FULL]
        self._custom_settings: Optional[CompactModeSettings] = None

    @property
    def mode(self) -> OutputMode:
        """Get current output mode"""
        return self._mode

    @property
    def settings(self) -> CompactModeSettings:
        """Get current settings"""
        return self._custom_settings or self._settings

    def set_mode(self, mode: OutputMode):
        """Set output mode"""
        self._mode = mode
        self._settings = MODE_PRESETS.get(mode, MODE_PRESETS[OutputMode.FULL])
        self._custom_settings = None

        mode_descriptions = {
            OutputMode.FULL: "Full verbose output enabled",
            OutputMode.COMPACT: "Compact mode enabled - minimal output",
            OutputMode.QUIET: "Quiet mode enabled - essential output only",
            OutputMode.JSON: "JSON output mode enabled"
        }

        self.console.print(f"[green]✓ {mode_descriptions.get(mode, 'Mode changed')}[/green]")

    def set_custom_settings(self, **kwargs):
        """Set custom settings"""
        if self._custom_settings is None:
            self._custom_settings = CompactModeSettings(**vars(self._settings))

        for key, value in kwargs.items():
            if hasattr(self._custom_settings, key):
                setattr(self._custom_settings, key, value)

    def toggle_compact(self) -> bool:
        """Toggle between full and compact mode"""
        if self._mode == OutputMode.COMPACT:
            self.set_mode(OutputMode.FULL)
            return False
        else:
            self.set_mode(OutputMode.COMPACT)
            return True

    def is_compact(self) -> bool:
        """Check if in compact mode"""
        return self._mode in (OutputMode.COMPACT, OutputMode.QUIET)

    # ==================== Output Methods ====================

    def print_status(self, message: str, icon: str = ""):
        """Print status message respecting mode settings"""
        if not self.settings.show_progress:
            return

        if self.settings.single_line_status:
            # Single line, overwrite previous
            if self.settings.show_icons and icon:
                self.console.print(f"\r{icon} {message}", end="")
            else:
                self.console.print(f"\r{message}", end="")
        else:
            if self.settings.show_icons and icon:
                self.console.print(f"{icon} {message}")
            else:
                self.console.print(message)

    def print_thinking(self, message: str):
        """Print thinking/reasoning message"""
        if not self.settings.show_thinking:
            return

        if self.is_compact():
            self.console.print(f"[dim]{message[:50]}...[/dim]")
        else:
            self.console.print(f"[dim italic]{message}[/dim italic]")

    def print_tool_call(self, tool_name: str, args: Dict[str, Any] = None):
        """Print tool call information"""
        if not self.settings.show_tool_calls:
            return

        if self.is_compact():
            self.console.print(f"[magenta]⚡ {tool_name}[/magenta]")
        else:
            self.console.print(f"\n[bold magenta]⚡ {tool_name}[/bold magenta]")
            if args:
                for key, value in args.items():
                    display_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                    self.console.print(f"  [dim]{key}:[/dim] {display_value}")

    def print_file_created(self, path: str, lines: int = 0):
        """Print file creation message"""
        display_path = self._truncate_path(path) if self.settings.truncate_paths else path

        if self.is_compact():
            icon = "✓" if self.settings.show_icons else ""
            self.console.print(f"[green]{icon} {display_path}[/green]")
        else:
            lines_info = f" ({lines} lines)" if lines else ""
            self.console.print(f"[green]✓ Created: {display_path}{lines_info}[/green]")

    def print_file_modified(self, path: str, additions: int = 0, deletions: int = 0):
        """Print file modification message"""
        display_path = self._truncate_path(path) if self.settings.truncate_paths else path

        if self.is_compact():
            icon = "~" if self.settings.show_icons else ""
            self.console.print(f"[yellow]{icon} {display_path}[/yellow]")
        else:
            changes = ""
            if additions or deletions:
                changes = f" ([green]+{additions}[/green] [red]-{deletions}[/red])"
            self.console.print(f"[yellow]~ Modified: {display_path}{changes}[/yellow]")

    def print_file_deleted(self, path: str):
        """Print file deletion message"""
        display_path = self._truncate_path(path) if self.settings.truncate_paths else path

        if self.is_compact():
            icon = "✗" if self.settings.show_icons else ""
            self.console.print(f"[red]{icon} {display_path}[/red]")
        else:
            self.console.print(f"[red]✗ Deleted: {display_path}[/red]")

    def print_command(self, command: str, output: str = "", exit_code: int = 0):
        """Print command execution"""
        if self.is_compact():
            icon = "✓" if exit_code == 0 else "✗"
            color = "green" if exit_code == 0 else "red"
            self.console.print(f"[{color}]{icon} $ {command[:40]}{'...' if len(command) > 40 else ''}[/{color}]")
        else:
            self.console.print(f"\n[bold cyan]$[/bold cyan] {command}")

            if self.settings.show_command_output and output:
                lines = output.strip().splitlines()
                max_lines = self.settings.max_output_lines

                for line in lines[:max_lines]:
                    self.console.print(f"  {line}")

                if len(lines) > max_lines:
                    self.console.print(f"  [dim]... ({len(lines) - max_lines} more lines)[/dim]")

            if exit_code == 0:
                self.console.print("[green]✓ Success[/green]")
            else:
                self.console.print(f"[red]✗ Exit code: {exit_code}[/red]")

    def print_content(self, content: str, title: str = ""):
        """Print content (file contents, responses, etc.)"""
        if not self.settings.show_file_contents and not title:
            return

        lines = content.splitlines()
        max_lines = self.settings.max_output_lines

        if self.is_compact() and len(lines) > max_lines:
            # Truncate
            for line in lines[:max_lines]:
                self.console.print(line)
            self.console.print(f"[dim]... ({len(lines) - max_lines} more lines)[/dim]")
        else:
            self.console.print(content)

    def print_tokens(self, input_tokens: int, output_tokens: int, cost: float = 0):
        """Print token usage"""
        if not self.settings.show_token_usage:
            return

        total = input_tokens + output_tokens

        if self.is_compact():
            self.console.print(f"[dim]{total:,} tokens[/dim]")
        else:
            self.console.print(
                f"[dim]Tokens: {total:,} (in: {input_tokens:,}, out: {output_tokens:,})"
                + (f" · ${cost:.4f}" if cost else "") + "[/dim]"
            )

    def print_error(self, message: str):
        """Print error message (always shown)"""
        self.console.print(f"[red]✗ {message}[/red]")

    def print_warning(self, message: str):
        """Print warning message"""
        if self._mode == OutputMode.QUIET:
            return
        self.console.print(f"[yellow]⚠ {message}[/yellow]")

    def print_success(self, message: str):
        """Print success message"""
        if self.is_compact():
            self.console.print(f"[green]✓ {message}[/green]")
        else:
            self.console.print(f"\n[bold green]✓ {message}[/bold green]")

    def print_info(self, message: str):
        """Print info message"""
        if self._mode == OutputMode.QUIET:
            return

        if self.is_compact():
            self.console.print(f"[dim]{message}[/dim]")
        else:
            self.console.print(f"[blue]ℹ {message}[/blue]")

    def _truncate_path(self, path: str, max_length: int = 40) -> str:
        """Truncate path for compact display"""
        if len(path) <= max_length:
            return path

        parts = path.replace('\\', '/').split('/')

        if len(parts) <= 2:
            return "..." + path[-(max_length - 3):]

        # Keep first and last parts
        return f"{parts[0]}/.../{parts[-1]}"

    # ==================== Display ====================

    def show_current_mode(self):
        """Show current mode settings"""
        settings = self.settings

        self.console.print(f"\n[bold cyan]Output Mode: {self._mode.value}[/bold cyan]\n")

        settings_display = [
            ("Show thinking", settings.show_thinking),
            ("Show tool calls", settings.show_tool_calls),
            ("Show file contents", settings.show_file_contents),
            ("Show command output", settings.show_command_output),
            ("Show progress", settings.show_progress),
            ("Show token usage", settings.show_token_usage),
            ("Show timestamps", settings.show_timestamps),
            ("Show icons", settings.show_icons),
            ("Truncate paths", settings.truncate_paths),
            ("Single line status", settings.single_line_status),
            ("Max output lines", settings.max_output_lines),
        ]

        for name, value in settings_display:
            if isinstance(value, bool):
                status = "[green]on[/green]" if value else "[red]off[/red]"
            else:
                status = str(value)
            self.console.print(f"  {name}: {status}")

    def show_help(self):
        """Show help for compact mode"""
        help_text = """
[bold cyan]Output Modes[/bold cyan]

Control how much output is displayed.

[bold]Commands:[/bold]
  [green]/compact[/green]          Toggle compact mode
  [green]/compact on[/green]       Enable compact mode
  [green]/compact off[/green]      Disable compact mode
  [green]/mode full[/green]        Full verbose output
  [green]/mode compact[/green]     Minimal output
  [green]/mode quiet[/green]       Essential output only

[bold]Modes:[/bold]
  • full    - All output, verbose
  • compact - Minimal, single-line status
  • quiet   - Only errors and results

[bold]Settings:[/bold]
  /set show_thinking true/false
  /set show_tool_calls true/false
  /set show_file_contents true/false
  /set max_output_lines 10
"""
        self.console.print(Text.from_markup(help_text))
