"""
BharatBuild CLI Status Line

Display contextual information at terminal bottom:
  /statusline         Configure status line
  /statusline on      Enable status line
  /statusline off     Disable status line
"""

import os
import subprocess
import platform
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.style import Style
from rich.text import Text


@dataclass
class StatusLineConfig:
    """Status line configuration"""
    enabled: bool = True
    show_model: bool = True
    show_directory: bool = True
    show_git_branch: bool = True
    show_token_count: bool = True
    show_cost: bool = False
    show_time: bool = False
    position: str = "bottom"  # bottom, top
    style: str = "default"  # default, minimal, detailed
    refresh_interval: int = 5  # seconds


class StatusLineManager:
    """
    Manages the CLI status line display.

    Features:
    - Model name display
    - Working directory
    - Git branch
    - Token count
    - Cost tracking
    - Customizable position and style

    Usage:
        manager = StatusLineManager(console, config_dir)

        # Get current status line
        status = manager.get_status_line()

        # Configure
        manager.configure()

        # Enable/disable
        manager.set_enabled(True)
    """

    def __init__(
        self,
        console: Console,
        config_dir: Path = None,
        project_dir: Path = None
    ):
        self.console = console
        self.config_dir = config_dir or Path.home() / ".bharatbuild"
        self.project_dir = project_dir or Path.cwd()

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self._config = StatusLineConfig()
        self._load_config()

        # Runtime state
        self._current_model: str = "claude-3-sonnet"
        self._token_count: int = 0
        self._cost: float = 0.0

    def _load_config(self):
        """Load status line configuration"""
        config_file = self.config_dir / "statusline.json"

        if config_file.exists():
            try:
                with open(config_file) as f:
                    data = json.load(f)

                self._config = StatusLineConfig(
                    enabled=data.get("enabled", True),
                    show_model=data.get("show_model", True),
                    show_directory=data.get("show_directory", True),
                    show_git_branch=data.get("show_git_branch", True),
                    show_token_count=data.get("show_token_count", True),
                    show_cost=data.get("show_cost", False),
                    show_time=data.get("show_time", False),
                    position=data.get("position", "bottom"),
                    style=data.get("style", "default"),
                    refresh_interval=data.get("refresh_interval", 5)
                )
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load statusline config: {e}[/yellow]")

    def _save_config(self):
        """Save status line configuration"""
        config_file = self.config_dir / "statusline.json"

        with open(config_file, 'w') as f:
            json.dump(asdict(self._config), f, indent=2)

    # ==================== Status Line Generation ====================

    def get_status_line(self) -> str:
        """Generate the current status line"""
        if not self._config.enabled:
            return ""

        parts = []

        # Model
        if self._config.show_model:
            model_short = self._current_model.split("-")[-1] if "-" in self._current_model else self._current_model
            parts.append(f"[cyan]{model_short}[/cyan]")

        # Directory
        if self._config.show_directory:
            dir_name = self.project_dir.name
            parts.append(f"[blue]{dir_name}[/blue]")

        # Git branch
        if self._config.show_git_branch:
            branch = self._get_git_branch()
            if branch:
                parts.append(f"[magenta]{branch}[/magenta]")

        # Token count
        if self._config.show_token_count and self._token_count > 0:
            parts.append(f"[yellow]{self._token_count:,} tokens[/yellow]")

        # Cost
        if self._config.show_cost and self._cost > 0:
            parts.append(f"[green]${self._cost:.4f}[/green]")

        # Time
        if self._config.show_time:
            time_str = datetime.now().strftime("%H:%M")
            parts.append(f"[dim]{time_str}[/dim]")

        # Join parts based on style
        if self._config.style == "minimal":
            separator = " "
        elif self._config.style == "detailed":
            separator = " | "
        else:
            separator = " · "

        return separator.join(parts)

    def _get_git_branch(self) -> Optional[str]:
        """Get current git branch"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=2
            )

            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        return None

    def render_status_line(self):
        """Render the status line to console"""
        if not self._config.enabled:
            return

        status = self.get_status_line()
        if status:
            self.console.print(f"\n[dim]─[/dim] {status} [dim]─[/dim]")

    # ==================== State Updates ====================

    def set_model(self, model: str):
        """Update current model"""
        self._current_model = model

    def set_token_count(self, count: int):
        """Update token count"""
        self._token_count = count

    def add_tokens(self, count: int):
        """Add to token count"""
        self._token_count += count

    def set_cost(self, cost: float):
        """Update cost"""
        self._cost = cost

    def add_cost(self, cost: float):
        """Add to cost"""
        self._cost += cost

    def set_project_dir(self, path: Path):
        """Update project directory"""
        self.project_dir = path

    # ==================== Configuration ====================

    def set_enabled(self, enabled: bool):
        """Enable or disable status line"""
        self._config.enabled = enabled
        self._save_config()

        if enabled:
            self.console.print("[green]✓ Status line enabled[/green]")
        else:
            self.console.print("[green]✓ Status line disabled[/green]")

    def configure(self):
        """Interactive configuration"""
        self.console.print("\n[bold cyan]Status Line Configuration[/bold cyan]\n")

        # Show current settings
        self._show_current_config()

        self.console.print("\n[bold]Configure:[/bold]")
        self.console.print("  [cyan]1.[/cyan] Toggle components")
        self.console.print("  [cyan]2.[/cyan] Change style")
        self.console.print("  [cyan]3.[/cyan] Change position")
        self.console.print("  [cyan]4.[/cyan] Reset to defaults")
        self.console.print("  [cyan]5.[/cyan] Back")

        choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "5"], default="5")

        if choice == "1":
            self._configure_components()
        elif choice == "2":
            self._configure_style()
        elif choice == "3":
            self._configure_position()
        elif choice == "4":
            self._reset_config()

    def _show_current_config(self):
        """Show current configuration"""
        table = Table(show_header=True, header_style="bold")
        table.add_column("Setting")
        table.add_column("Value")

        settings = [
            ("Enabled", self._config.enabled),
            ("Show Model", self._config.show_model),
            ("Show Directory", self._config.show_directory),
            ("Show Git Branch", self._config.show_git_branch),
            ("Show Token Count", self._config.show_token_count),
            ("Show Cost", self._config.show_cost),
            ("Show Time", self._config.show_time),
            ("Position", self._config.position),
            ("Style", self._config.style)
        ]

        for name, value in settings:
            if isinstance(value, bool):
                display = "[green]Yes[/green]" if value else "[red]No[/red]"
            else:
                display = str(value)
            table.add_row(name, display)

        self.console.print(table)

        # Preview
        self.console.print("\n[bold]Preview:[/bold]")
        preview = self.get_status_line()
        self.console.print(f"  {preview}")

    def _configure_components(self):
        """Configure which components to show"""
        self.console.print("\n[bold]Toggle Components[/bold]\n")

        self._config.show_model = Confirm.ask("Show model?", default=self._config.show_model)
        self._config.show_directory = Confirm.ask("Show directory?", default=self._config.show_directory)
        self._config.show_git_branch = Confirm.ask("Show git branch?", default=self._config.show_git_branch)
        self._config.show_token_count = Confirm.ask("Show token count?", default=self._config.show_token_count)
        self._config.show_cost = Confirm.ask("Show cost?", default=self._config.show_cost)
        self._config.show_time = Confirm.ask("Show time?", default=self._config.show_time)

        self._save_config()
        self.console.print("\n[green]✓ Components updated[/green]")

    def _configure_style(self):
        """Configure status line style"""
        self.console.print("\n[bold]Select Style[/bold]\n")
        self.console.print("  [cyan]1.[/cyan] default - Standard separators (·)")
        self.console.print("  [cyan]2.[/cyan] minimal - Space separated")
        self.console.print("  [cyan]3.[/cyan] detailed - Pipe separated (|)")

        choice = Prompt.ask("Select", choices=["1", "2", "3"], default="1")

        style_map = {"1": "default", "2": "minimal", "3": "detailed"}
        self._config.style = style_map[choice]

        self._save_config()
        self.console.print(f"\n[green]✓ Style set to: {self._config.style}[/green]")

    def _configure_position(self):
        """Configure status line position"""
        self.console.print("\n[bold]Select Position[/bold]\n")
        self.console.print("  [cyan]1.[/cyan] bottom - Below prompt")
        self.console.print("  [cyan]2.[/cyan] top - Above prompt")

        choice = Prompt.ask("Select", choices=["1", "2"], default="1")

        self._config.position = "bottom" if choice == "1" else "top"

        self._save_config()
        self.console.print(f"\n[green]✓ Position set to: {self._config.position}[/green]")

    def _reset_config(self):
        """Reset to default configuration"""
        if Confirm.ask("Reset status line to defaults?", default=False):
            self._config = StatusLineConfig()
            self._save_config()
            self.console.print("[green]✓ Reset to defaults[/green]")

    # ==================== Command Handler ====================

    def cmd_statusline(self, args: str = ""):
        """Handle /statusline command"""
        if not args:
            self.configure()
            return

        arg = args.lower().strip()

        if arg == "on":
            self.set_enabled(True)
        elif arg == "off":
            self.set_enabled(False)
        elif arg == "toggle":
            self.set_enabled(not self._config.enabled)
        elif arg == "show":
            self.render_status_line()
        elif arg == "help":
            self.show_help()
        else:
            self.console.print(f"[yellow]Unknown option: {arg}[/yellow]")
            self.show_help()

    def show_help(self):
        """Show help for statusline command"""
        help_text = """
[bold cyan]Status Line Commands[/bold cyan]

Display contextual information in terminal.

[bold]Commands:[/bold]
  [green]/statusline[/green]           Interactive configuration
  [green]/statusline on[/green]        Enable status line
  [green]/statusline off[/green]       Disable status line
  [green]/statusline toggle[/green]    Toggle status line
  [green]/statusline show[/green]      Show current status line

[bold]Components:[/bold]
  • Model name
  • Working directory
  • Git branch
  • Token count
  • Cost (optional)
  • Time (optional)

[bold]Styles:[/bold]
  • default  - Standard separators (·)
  • minimal  - Space separated
  • detailed - Pipe separated (|)
"""
        self.console.print(help_text)


# Factory function
def get_statusline_manager(
    console: Console = None,
    config_dir: Path = None,
    project_dir: Path = None
) -> StatusLineManager:
    """Get status line manager instance"""
    return StatusLineManager(
        console=console or Console(),
        config_dir=config_dir,
        project_dir=project_dir
    )
