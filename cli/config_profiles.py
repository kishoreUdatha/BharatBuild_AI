"""
BharatBuild CLI Configuration Profiles

Manage multiple configuration profiles:
  /profile list       List profiles
  /profile use <n>    Switch profile
  /profile create     Create new profile
  /profile delete     Delete profile
"""

import os
import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm


@dataclass
class Profile:
    """A configuration profile"""
    name: str
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: str = ""

    # API Settings
    api_key: str = ""
    model: str = "claude-3-sonnet-20240229"
    max_tokens: int = 4096
    temperature: float = 0.7

    # Behavior
    auto_save: bool = True
    confirm_writes: bool = True
    confirm_bash: bool = True
    sound_enabled: bool = True

    # Display
    theme: str = "default"
    compact_mode: bool = False
    show_tokens: bool = True
    show_cost: bool = True

    # Advanced
    timeout: int = 120
    max_retries: int = 3
    proxy: str = ""
    custom_headers: Dict[str, str] = field(default_factory=dict)


# Built-in profile presets
PROFILE_PRESETS = {
    "default": Profile(
        name="default",
        description="Default balanced configuration",
        model="claude-3-sonnet-20240229",
        max_tokens=4096,
        temperature=0.7,
    ),
    "fast": Profile(
        name="fast",
        description="Fast responses with Haiku model",
        model="claude-3-haiku-20240307",
        max_tokens=2048,
        temperature=0.5,
        compact_mode=True,
    ),
    "quality": Profile(
        name="quality",
        description="High quality with Opus model",
        model="claude-3-opus-20240229",
        max_tokens=8192,
        temperature=0.8,
    ),
    "coding": Profile(
        name="coding",
        description="Optimized for coding tasks",
        model="claude-3-sonnet-20240229",
        max_tokens=4096,
        temperature=0.3,
        confirm_writes=True,
        confirm_bash=True,
    ),
    "creative": Profile(
        name="creative",
        description="Creative writing and brainstorming",
        model="claude-3-opus-20240229",
        max_tokens=8192,
        temperature=1.0,
    ),
}


class ProfileManager:
    """
    Manages configuration profiles.

    Usage:
        manager = ProfileManager(console, config_dir)

        # List profiles
        manager.list_profiles()

        # Switch profile
        manager.use_profile("coding")

        # Create profile
        manager.create_profile("my-profile", base="default")

        # Get current config
        config = manager.get_current_config()
    """

    def __init__(self, console: Console, config_dir: Path = None):
        self.console = console
        self.config_dir = config_dir or Path.home() / ".bharatbuild"
        self.profiles_dir = self.config_dir / "profiles"

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(exist_ok=True)

        # Load state
        self._current_profile: str = "default"
        self._profiles: Dict[str, Profile] = {}
        self._load_profiles()

    def _load_profiles(self):
        """Load all profiles"""
        # Load built-in presets first
        for name, profile in PROFILE_PRESETS.items():
            self._profiles[name] = profile

        # Load custom profiles from disk
        for profile_file in self.profiles_dir.glob("*.json"):
            try:
                with open(profile_file) as f:
                    data = json.load(f)
                profile = Profile(**data)
                self._profiles[profile.name] = profile
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load profile {profile_file.name}: {e}[/yellow]")

        # Load current profile setting
        state_file = self.config_dir / "profile_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                self._current_profile = state.get("current", "default")
            except Exception:
                pass

    def _save_profile(self, profile: Profile):
        """Save a profile to disk"""
        profile_file = self.profiles_dir / f"{profile.name}.json"
        with open(profile_file, 'w') as f:
            json.dump(asdict(profile), f, indent=2)

    def _save_state(self):
        """Save current profile state"""
        state_file = self.config_dir / "profile_state.json"
        with open(state_file, 'w') as f:
            json.dump({"current": self._current_profile}, f)

    # ==================== Profile Operations ====================

    def list_profiles(self):
        """List all available profiles"""
        table = Table(title="Configuration Profiles", show_header=True, header_style="bold cyan")
        table.add_column("", width=3)
        table.add_column("Name")
        table.add_column("Description")
        table.add_column("Model")
        table.add_column("Type")

        for name, profile in sorted(self._profiles.items()):
            # Current indicator
            indicator = "[green]►[/green]" if name == self._current_profile else " "

            # Profile type
            if name in PROFILE_PRESETS:
                ptype = "[dim]built-in[/dim]"
            else:
                ptype = "custom"

            # Model short name
            model_short = profile.model.split("-")[2] if "-" in profile.model else profile.model

            table.add_row(
                indicator,
                f"[bold]{name}[/bold]",
                profile.description[:40],
                model_short,
                ptype
            )

        self.console.print(table)
        self.console.print(f"\n[dim]Current: {self._current_profile}[/dim]")

    def get_profile(self, name: str) -> Optional[Profile]:
        """Get a profile by name"""
        return self._profiles.get(name)

    def get_current_profile(self) -> Profile:
        """Get current active profile"""
        return self._profiles.get(self._current_profile, PROFILE_PRESETS["default"])

    def get_current_config(self) -> Dict[str, Any]:
        """Get current profile as config dict"""
        profile = self.get_current_profile()
        return asdict(profile)

    def use_profile(self, name: str) -> bool:
        """Switch to a profile"""
        if name not in self._profiles:
            self.console.print(f"[red]Profile not found: {name}[/red]")
            self.console.print("[dim]Use /profile list to see available profiles[/dim]")
            return False

        self._current_profile = name
        self._save_state()

        # Update last used
        profile = self._profiles[name]
        profile.last_used = datetime.now().isoformat()
        if name not in PROFILE_PRESETS:
            self._save_profile(profile)

        self.console.print(f"[green]✓ Switched to profile: {name}[/green]")
        self._show_profile_summary(profile)

        return True

    def create_profile(
        self,
        name: str,
        base: str = "default",
        description: str = "",
        interactive: bool = False
    ) -> Optional[Profile]:
        """Create a new profile"""
        # Check if name is valid
        if not name or "/" in name or "\\" in name:
            self.console.print("[red]Invalid profile name[/red]")
            return None

        # Check if exists
        if name in self._profiles:
            self.console.print(f"[red]Profile already exists: {name}[/red]")
            return None

        # Get base profile
        base_profile = self._profiles.get(base, PROFILE_PRESETS["default"])

        # Create new profile
        new_profile = Profile(
            name=name,
            description=description or f"Custom profile based on {base}",
            api_key=base_profile.api_key,
            model=base_profile.model,
            max_tokens=base_profile.max_tokens,
            temperature=base_profile.temperature,
            auto_save=base_profile.auto_save,
            confirm_writes=base_profile.confirm_writes,
            confirm_bash=base_profile.confirm_bash,
            sound_enabled=base_profile.sound_enabled,
            theme=base_profile.theme,
            compact_mode=base_profile.compact_mode,
            show_tokens=base_profile.show_tokens,
            show_cost=base_profile.show_cost,
            timeout=base_profile.timeout,
            max_retries=base_profile.max_retries,
            proxy=base_profile.proxy,
        )

        # Interactive configuration
        if interactive:
            new_profile = self._configure_profile_interactive(new_profile)

        # Save profile
        self._profiles[name] = new_profile
        self._save_profile(new_profile)

        self.console.print(f"[green]✓ Created profile: {name}[/green]")

        return new_profile

    def _configure_profile_interactive(self, profile: Profile) -> Profile:
        """Configure profile interactively"""
        self.console.print("\n[bold cyan]Configure Profile[/bold cyan]\n")

        # Description
        profile.description = Prompt.ask("Description", default=profile.description)

        # Model
        model_choice = Prompt.ask(
            "Model",
            choices=["haiku", "sonnet", "opus"],
            default="sonnet"
        )
        model_map = {
            "haiku": "claude-3-haiku-20240307",
            "sonnet": "claude-3-sonnet-20240229",
            "opus": "claude-3-opus-20240229"
        }
        profile.model = model_map[model_choice]

        # Max tokens
        profile.max_tokens = int(Prompt.ask("Max tokens", default=str(profile.max_tokens)))

        # Temperature
        profile.temperature = float(Prompt.ask("Temperature (0-1)", default=str(profile.temperature)))

        # Behavior
        profile.confirm_writes = Confirm.ask("Confirm file writes?", default=profile.confirm_writes)
        profile.confirm_bash = Confirm.ask("Confirm bash commands?", default=profile.confirm_bash)
        profile.compact_mode = Confirm.ask("Compact mode?", default=profile.compact_mode)

        return profile

    def edit_profile(self, name: str) -> bool:
        """Edit an existing profile"""
        if name not in self._profiles:
            self.console.print(f"[red]Profile not found: {name}[/red]")
            return False

        if name in PROFILE_PRESETS:
            self.console.print("[yellow]Cannot edit built-in profiles. Create a custom profile instead.[/yellow]")
            return False

        profile = self._profiles[name]
        profile = self._configure_profile_interactive(profile)
        self._save_profile(profile)

        self.console.print(f"[green]✓ Updated profile: {name}[/green]")
        return True

    def delete_profile(self, name: str) -> bool:
        """Delete a profile"""
        if name not in self._profiles:
            self.console.print(f"[red]Profile not found: {name}[/red]")
            return False

        if name in PROFILE_PRESETS:
            self.console.print("[red]Cannot delete built-in profiles[/red]")
            return False

        if name == self._current_profile:
            self.console.print("[yellow]Cannot delete current profile. Switch to another first.[/yellow]")
            return False

        # Confirm deletion
        if not Confirm.ask(f"Delete profile '{name}'?"):
            return False

        # Delete file
        profile_file = self.profiles_dir / f"{name}.json"
        if profile_file.exists():
            profile_file.unlink()

        del self._profiles[name]

        self.console.print(f"[green]✓ Deleted profile: {name}[/green]")
        return True

    def duplicate_profile(self, source: str, new_name: str) -> Optional[Profile]:
        """Duplicate a profile"""
        if source not in self._profiles:
            self.console.print(f"[red]Source profile not found: {source}[/red]")
            return None

        return self.create_profile(new_name, base=source)

    def export_profile(self, name: str, path: Path = None) -> bool:
        """Export a profile to a file"""
        if name not in self._profiles:
            self.console.print(f"[red]Profile not found: {name}[/red]")
            return False

        profile = self._profiles[name]
        export_path = path or Path.cwd() / f"{name}_profile.json"

        with open(export_path, 'w') as f:
            json.dump(asdict(profile), f, indent=2)

        self.console.print(f"[green]✓ Exported to {export_path}[/green]")
        return True

    def import_profile(self, path: Path, new_name: str = None) -> Optional[Profile]:
        """Import a profile from a file"""
        if not path.exists():
            self.console.print(f"[red]File not found: {path}[/red]")
            return None

        try:
            with open(path) as f:
                data = json.load(f)

            # Override name if specified
            if new_name:
                data["name"] = new_name

            profile = Profile(**data)

            # Check for conflicts
            if profile.name in self._profiles:
                if not Confirm.ask(f"Profile '{profile.name}' exists. Overwrite?"):
                    return None

            self._profiles[profile.name] = profile
            self._save_profile(profile)

            self.console.print(f"[green]✓ Imported profile: {profile.name}[/green]")
            return profile

        except Exception as e:
            self.console.print(f"[red]Error importing profile: {e}[/red]")
            return None

    # ==================== Display ====================

    def show_profile(self, name: str = None):
        """Show profile details"""
        name = name or self._current_profile
        profile = self._profiles.get(name)

        if not profile:
            self.console.print(f"[red]Profile not found: {name}[/red]")
            return

        self._show_profile_summary(profile, detailed=True)

    def _show_profile_summary(self, profile: Profile, detailed: bool = False):
        """Display profile summary"""
        content_lines = []

        content_lines.append(f"[bold]Name:[/bold] {profile.name}")
        content_lines.append(f"[bold]Description:[/bold] {profile.description}")
        content_lines.append("")

        # Model info
        model_short = profile.model.split("-")[2] if "-" in profile.model else profile.model
        content_lines.append(f"[bold]Model:[/bold] {model_short}")
        content_lines.append(f"[bold]Max Tokens:[/bold] {profile.max_tokens}")
        content_lines.append(f"[bold]Temperature:[/bold] {profile.temperature}")

        if detailed:
            content_lines.append("")
            content_lines.append("[bold]Behavior:[/bold]")
            content_lines.append(f"  Auto-save: {'Yes' if profile.auto_save else 'No'}")
            content_lines.append(f"  Confirm writes: {'Yes' if profile.confirm_writes else 'No'}")
            content_lines.append(f"  Confirm bash: {'Yes' if profile.confirm_bash else 'No'}")
            content_lines.append(f"  Sounds: {'Yes' if profile.sound_enabled else 'No'}")

            content_lines.append("")
            content_lines.append("[bold]Display:[/bold]")
            content_lines.append(f"  Theme: {profile.theme}")
            content_lines.append(f"  Compact mode: {'Yes' if profile.compact_mode else 'No'}")
            content_lines.append(f"  Show tokens: {'Yes' if profile.show_tokens else 'No'}")

            if profile.proxy:
                content_lines.append("")
                content_lines.append(f"[bold]Proxy:[/bold] {profile.proxy}")

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title=f"[bold cyan]Profile: {profile.name}[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

    def show_help(self):
        """Show profile help"""
        help_text = """
[bold cyan]Profile Commands[/bold cyan]

Manage configuration profiles.

[bold]Commands:[/bold]
  [green]/profile[/green]              List all profiles
  [green]/profile list[/green]         List all profiles
  [green]/profile use <name>[/green]   Switch to profile
  [green]/profile show [name][/green]  Show profile details
  [green]/profile create <n>[/green]   Create new profile
  [green]/profile edit <name>[/green]  Edit profile
  [green]/profile delete <n>[/green]   Delete profile
  [green]/profile export <n>[/green]   Export to file
  [green]/profile import <f>[/green]   Import from file

[bold]Built-in Profiles:[/bold]
  • default  - Balanced configuration (Sonnet)
  • fast     - Quick responses (Haiku)
  • quality  - Best quality (Opus)
  • coding   - Optimized for code
  • creative - Creative writing

[bold]Examples:[/bold]
  /profile use coding
  /profile create my-profile --base default
  /profile export coding ./coding.json
"""
        self.console.print(help_text)
