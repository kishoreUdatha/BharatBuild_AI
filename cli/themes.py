"""
BharatBuild CLI Advanced Theme Customization

Customize the CLI appearance:
  /theme list         List available themes
  /theme set <name>   Set theme
  /theme customize    Create custom theme
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme
from rich.style import Style
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax


@dataclass
class ColorScheme:
    """Color scheme definition"""
    # Primary colors
    primary: str = "#6366f1"      # Indigo
    secondary: str = "#8b5cf6"    # Purple
    accent: str = "#06b6d4"       # Cyan

    # Semantic colors
    success: str = "#22c55e"      # Green
    warning: str = "#eab308"      # Yellow
    error: str = "#ef4444"        # Red
    info: str = "#3b82f6"         # Blue

    # Text colors
    text: str = "#e2e8f0"         # Light gray
    text_dim: str = "#64748b"     # Slate
    text_muted: str = "#475569"   # Darker slate

    # Background colors
    bg: str = "#0f172a"           # Dark blue
    bg_subtle: str = "#1e293b"    # Slightly lighter
    bg_highlight: str = "#334155" # Highlight

    # Code colors
    code_keyword: str = "#c084fc"  # Purple
    code_string: str = "#86efac"   # Green
    code_number: str = "#fbbf24"   # Amber
    code_comment: str = "#64748b"  # Gray
    code_function: str = "#38bdf8" # Sky


@dataclass
class ThemeConfig:
    """Complete theme configuration"""
    name: str
    description: str = ""
    colors: ColorScheme = field(default_factory=ColorScheme)

    # Component styles
    panel_border: str = "rounded"  # rounded, square, double, heavy, none
    panel_title_align: str = "left"  # left, center, right

    # Status bar
    show_status_bar: bool = True
    status_bar_position: str = "bottom"  # top, bottom

    # Prompt
    prompt_symbol: str = ">"
    prompt_color: str = "primary"

    # Output
    show_timestamps: bool = False
    show_icons: bool = True
    compact_output: bool = False

    # Code blocks
    code_theme: str = "monokai"  # pygments theme
    line_numbers: bool = True


# Built-in themes
BUILTIN_THEMES: Dict[str, ThemeConfig] = {
    "default": ThemeConfig(
        name="default",
        description="Default BharatBuild theme",
        colors=ColorScheme()
    ),

    "dark": ThemeConfig(
        name="dark",
        description="Dark theme with high contrast",
        colors=ColorScheme(
            primary="#818cf8",
            secondary="#a78bfa",
            bg="#000000",
            bg_subtle="#111111",
            text="#ffffff"
        )
    ),

    "light": ThemeConfig(
        name="light",
        description="Light theme for bright environments",
        colors=ColorScheme(
            primary="#4f46e5",
            secondary="#7c3aed",
            bg="#ffffff",
            bg_subtle="#f8fafc",
            bg_highlight="#f1f5f9",
            text="#1e293b",
            text_dim="#475569",
            text_muted="#94a3b8"
        )
    ),

    "ocean": ThemeConfig(
        name="ocean",
        description="Cool ocean blues",
        colors=ColorScheme(
            primary="#0ea5e9",
            secondary="#06b6d4",
            accent="#14b8a6",
            bg="#0c1222",
            bg_subtle="#172033",
            success="#2dd4bf",
            text="#e0f2fe"
        )
    ),

    "forest": ThemeConfig(
        name="forest",
        description="Natural green tones",
        colors=ColorScheme(
            primary="#22c55e",
            secondary="#10b981",
            accent="#84cc16",
            bg="#0f1f14",
            bg_subtle="#1a2e1f",
            text="#dcfce7"
        )
    ),

    "sunset": ThemeConfig(
        name="sunset",
        description="Warm sunset colors",
        colors=ColorScheme(
            primary="#f97316",
            secondary="#fb923c",
            accent="#fbbf24",
            bg="#1c1008",
            bg_subtle="#2d1a10",
            error="#dc2626",
            text="#fef3c7"
        )
    ),

    "nord": ThemeConfig(
        name="nord",
        description="Nord color palette",
        colors=ColorScheme(
            primary="#88c0d0",
            secondary="#81a1c1",
            accent="#8fbcbb",
            success="#a3be8c",
            warning="#ebcb8b",
            error="#bf616a",
            bg="#2e3440",
            bg_subtle="#3b4252",
            text="#eceff4",
            text_dim="#d8dee9"
        ),
        code_theme="nord"
    ),

    "dracula": ThemeConfig(
        name="dracula",
        description="Dracula color scheme",
        colors=ColorScheme(
            primary="#bd93f9",
            secondary="#ff79c6",
            accent="#8be9fd",
            success="#50fa7b",
            warning="#ffb86c",
            error="#ff5555",
            bg="#282a36",
            bg_subtle="#44475a",
            text="#f8f8f2",
            text_dim="#6272a4"
        ),
        code_theme="dracula"
    ),

    "minimal": ThemeConfig(
        name="minimal",
        description="Minimal monochrome theme",
        colors=ColorScheme(
            primary="#a1a1aa",
            secondary="#71717a",
            accent="#d4d4d8",
            success="#a1a1aa",
            warning="#a1a1aa",
            error="#a1a1aa",
            bg="#18181b",
            bg_subtle="#27272a",
            text="#fafafa",
            text_dim="#71717a"
        ),
        show_icons=False,
        panel_border="square"
    ),

    "hacker": ThemeConfig(
        name="hacker",
        description="Matrix-style green on black",
        colors=ColorScheme(
            primary="#00ff00",
            secondary="#00cc00",
            accent="#00ff00",
            success="#00ff00",
            warning="#ffff00",
            error="#ff0000",
            bg="#000000",
            bg_subtle="#001100",
            text="#00ff00",
            text_dim="#008800"
        ),
        prompt_symbol="$",
        code_theme="monokai"
    ),
}


class ThemeManager:
    """
    Manages CLI themes.

    Usage:
        manager = ThemeManager(console, config_dir)

        # List themes
        manager.list_themes()

        # Set theme
        manager.set_theme("dracula")

        # Get Rich theme
        rich_theme = manager.get_rich_theme()
    """

    def __init__(self, console: Console, config_dir: Path = None):
        self.console = console
        self.config_dir = config_dir or Path.home() / ".bharatbuild"
        self.themes_dir = self.config_dir / "themes"
        self.config_file = self.config_dir / "theme_config.json"

        # Create directories
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.themes_dir.mkdir(exist_ok=True)

        # Load themes
        self._themes: Dict[str, ThemeConfig] = dict(BUILTIN_THEMES)
        self._load_custom_themes()

        # Current theme
        self._current_theme: str = "default"
        self._load_current_theme()

    def _load_custom_themes(self):
        """Load custom themes from disk"""
        for theme_file in self.themes_dir.glob("*.json"):
            try:
                with open(theme_file) as f:
                    data = json.load(f)

                colors = ColorScheme(**data.get("colors", {}))
                theme = ThemeConfig(
                    name=data["name"],
                    description=data.get("description", ""),
                    colors=colors,
                    panel_border=data.get("panel_border", "rounded"),
                    panel_title_align=data.get("panel_title_align", "left"),
                    show_status_bar=data.get("show_status_bar", True),
                    prompt_symbol=data.get("prompt_symbol", ">"),
                    prompt_color=data.get("prompt_color", "primary"),
                    show_timestamps=data.get("show_timestamps", False),
                    show_icons=data.get("show_icons", True),
                    compact_output=data.get("compact_output", False),
                    code_theme=data.get("code_theme", "monokai"),
                    line_numbers=data.get("line_numbers", True)
                )

                self._themes[theme.name] = theme

            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load theme {theme_file.name}: {e}[/yellow]")

    def _load_current_theme(self):
        """Load current theme setting"""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    data = json.load(f)
                self._current_theme = data.get("current_theme", "default")
            except Exception:
                pass

    def _save_current_theme(self):
        """Save current theme setting"""
        with open(self.config_file, 'w') as f:
            json.dump({"current_theme": self._current_theme}, f)

    # ==================== Theme Operations ====================

    def get_theme(self, name: str = None) -> ThemeConfig:
        """Get a theme by name"""
        name = name or self._current_theme
        return self._themes.get(name, BUILTIN_THEMES["default"])

    def get_current_theme(self) -> ThemeConfig:
        """Get current active theme"""
        return self.get_theme(self._current_theme)

    def set_theme(self, name: str) -> bool:
        """Set the active theme"""
        if name not in self._themes:
            self.console.print(f"[red]Theme not found: {name}[/red]")
            self.console.print("[dim]Use /theme list to see available themes[/dim]")
            return False

        self._current_theme = name
        self._save_current_theme()

        # Apply theme
        self._apply_theme()

        self.console.print(f"[green]✓ Theme set to: {name}[/green]")
        return True

    def _apply_theme(self):
        """Apply current theme to console"""
        # This would update the console's theme
        # In practice, you'd need to recreate the console or update styles
        pass

    def get_rich_theme(self) -> Theme:
        """Get Rich Theme object for current theme"""
        theme = self.get_current_theme()
        colors = theme.colors

        return Theme({
            "primary": Style(color=colors.primary),
            "secondary": Style(color=colors.secondary),
            "accent": Style(color=colors.accent),
            "success": Style(color=colors.success),
            "warning": Style(color=colors.warning),
            "error": Style(color=colors.error),
            "info": Style(color=colors.info),
            "text": Style(color=colors.text),
            "text.dim": Style(color=colors.text_dim),
            "text.muted": Style(color=colors.text_muted),
            "code.keyword": Style(color=colors.code_keyword),
            "code.string": Style(color=colors.code_string),
            "code.number": Style(color=colors.code_number),
            "code.comment": Style(color=colors.code_comment),
            "code.function": Style(color=colors.code_function),
        })

    def get_style(self, name: str) -> str:
        """Get a style color from current theme"""
        theme = self.get_current_theme()
        colors = theme.colors

        style_map = {
            "primary": colors.primary,
            "secondary": colors.secondary,
            "accent": colors.accent,
            "success": colors.success,
            "warning": colors.warning,
            "error": colors.error,
            "info": colors.info,
            "text": colors.text,
            "dim": colors.text_dim,
            "muted": colors.text_muted,
        }

        return style_map.get(name, colors.text)

    # ==================== Custom Themes ====================

    def create_theme(
        self,
        name: str,
        base: str = "default",
        description: str = ""
    ) -> Optional[ThemeConfig]:
        """Create a new custom theme"""
        if not name or "/" in name or "\\" in name:
            self.console.print("[red]Invalid theme name[/red]")
            return None

        if name in BUILTIN_THEMES:
            self.console.print("[red]Cannot overwrite built-in themes[/red]")
            return None

        # Get base theme
        base_theme = self._themes.get(base, BUILTIN_THEMES["default"])

        # Create new theme
        new_theme = ThemeConfig(
            name=name,
            description=description or f"Custom theme based on {base}",
            colors=ColorScheme(**asdict(base_theme.colors)),
            panel_border=base_theme.panel_border,
            panel_title_align=base_theme.panel_title_align,
            show_status_bar=base_theme.show_status_bar,
            prompt_symbol=base_theme.prompt_symbol,
            prompt_color=base_theme.prompt_color,
            show_timestamps=base_theme.show_timestamps,
            show_icons=base_theme.show_icons,
            compact_output=base_theme.compact_output,
            code_theme=base_theme.code_theme,
            line_numbers=base_theme.line_numbers
        )

        self._themes[name] = new_theme
        self._save_theme(new_theme)

        self.console.print(f"[green]✓ Created theme: {name}[/green]")
        return new_theme

    def edit_theme(self, name: str) -> bool:
        """Edit a custom theme interactively"""
        if name in BUILTIN_THEMES:
            self.console.print("[yellow]Cannot edit built-in themes. Create a custom theme first.[/yellow]")
            return False

        if name not in self._themes:
            self.console.print(f"[red]Theme not found: {name}[/red]")
            return False

        theme = self._themes[name]

        self.console.print(f"\n[bold cyan]Editing Theme: {name}[/bold cyan]\n")

        # Edit colors
        self.console.print("[bold]Colors (press Enter to keep current):[/bold]")

        colors = theme.colors
        colors.primary = Prompt.ask("Primary", default=colors.primary)
        colors.secondary = Prompt.ask("Secondary", default=colors.secondary)
        colors.accent = Prompt.ask("Accent", default=colors.accent)
        colors.success = Prompt.ask("Success", default=colors.success)
        colors.warning = Prompt.ask("Warning", default=colors.warning)
        colors.error = Prompt.ask("Error", default=colors.error)
        colors.bg = Prompt.ask("Background", default=colors.bg)
        colors.text = Prompt.ask("Text", default=colors.text)

        # Edit other settings
        self.console.print("\n[bold]Settings:[/bold]")
        theme.show_icons = Confirm.ask("Show icons?", default=theme.show_icons)
        theme.compact_output = Confirm.ask("Compact output?", default=theme.compact_output)
        theme.prompt_symbol = Prompt.ask("Prompt symbol", default=theme.prompt_symbol)

        self._save_theme(theme)
        self.console.print(f"\n[green]✓ Theme updated: {name}[/green]")

        return True

    def delete_theme(self, name: str) -> bool:
        """Delete a custom theme"""
        if name in BUILTIN_THEMES:
            self.console.print("[red]Cannot delete built-in themes[/red]")
            return False

        if name not in self._themes:
            self.console.print(f"[red]Theme not found: {name}[/red]")
            return False

        if name == self._current_theme:
            self.console.print("[yellow]Cannot delete current theme. Switch first.[/yellow]")
            return False

        if not Confirm.ask(f"Delete theme '{name}'?"):
            return False

        # Delete file
        theme_file = self.themes_dir / f"{name}.json"
        if theme_file.exists():
            theme_file.unlink()

        del self._themes[name]

        self.console.print(f"[green]✓ Deleted theme: {name}[/green]")
        return True

    def _save_theme(self, theme: ThemeConfig):
        """Save theme to disk"""
        theme_file = self.themes_dir / f"{theme.name}.json"

        data = {
            "name": theme.name,
            "description": theme.description,
            "colors": asdict(theme.colors),
            "panel_border": theme.panel_border,
            "panel_title_align": theme.panel_title_align,
            "show_status_bar": theme.show_status_bar,
            "prompt_symbol": theme.prompt_symbol,
            "prompt_color": theme.prompt_color,
            "show_timestamps": theme.show_timestamps,
            "show_icons": theme.show_icons,
            "compact_output": theme.compact_output,
            "code_theme": theme.code_theme,
            "line_numbers": theme.line_numbers
        }

        with open(theme_file, 'w') as f:
            json.dump(data, f, indent=2)

    def export_theme(self, name: str, path: Path = None) -> bool:
        """Export theme to file"""
        if name not in self._themes:
            self.console.print(f"[red]Theme not found: {name}[/red]")
            return False

        theme = self._themes[name]
        export_path = path or Path.cwd() / f"{name}_theme.json"

        data = {
            "name": theme.name,
            "description": theme.description,
            "colors": asdict(theme.colors),
        }

        with open(export_path, 'w') as f:
            json.dump(data, f, indent=2)

        self.console.print(f"[green]✓ Exported to {export_path}[/green]")
        return True

    def import_theme(self, path: Path) -> Optional[ThemeConfig]:
        """Import theme from file"""
        if not path.exists():
            self.console.print(f"[red]File not found: {path}[/red]")
            return None

        try:
            with open(path) as f:
                data = json.load(f)

            name = data["name"]

            if name in BUILTIN_THEMES:
                name = f"{name}_custom"
                data["name"] = name

            if name in self._themes:
                if not Confirm.ask(f"Theme '{name}' exists. Overwrite?"):
                    return None

            colors = ColorScheme(**data.get("colors", {}))
            theme = ThemeConfig(
                name=name,
                description=data.get("description", ""),
                colors=colors
            )

            self._themes[name] = theme
            self._save_theme(theme)

            self.console.print(f"[green]✓ Imported theme: {name}[/green]")
            return theme

        except Exception as e:
            self.console.print(f"[red]Error importing theme: {e}[/red]")
            return None

    # ==================== Display ====================

    def list_themes(self):
        """List all available themes"""
        table = Table(title="Available Themes", show_header=True, header_style="bold cyan")
        table.add_column("", width=3)
        table.add_column("Name")
        table.add_column("Description")
        table.add_column("Type")

        for name, theme in sorted(self._themes.items()):
            indicator = "[green]►[/green]" if name == self._current_theme else " "
            theme_type = "[dim]built-in[/dim]" if name in BUILTIN_THEMES else "custom"

            table.add_row(
                indicator,
                f"[bold]{name}[/bold]",
                theme.description[:40],
                theme_type
            )

        self.console.print(table)
        self.console.print(f"\n[dim]Current: {self._current_theme}[/dim]")

    def preview_theme(self, name: str):
        """Preview a theme"""
        if name not in self._themes:
            self.console.print(f"[red]Theme not found: {name}[/red]")
            return

        theme = self._themes[name]
        colors = theme.colors

        self.console.print(f"\n[bold]Theme Preview: {name}[/bold]\n")

        # Color swatches
        self.console.print(f"[{colors.primary}]██[/{colors.primary}] Primary")
        self.console.print(f"[{colors.secondary}]██[/{colors.secondary}] Secondary")
        self.console.print(f"[{colors.accent}]██[/{colors.accent}] Accent")
        self.console.print(f"[{colors.success}]██[/{colors.success}] Success")
        self.console.print(f"[{colors.warning}]██[/{colors.warning}] Warning")
        self.console.print(f"[{colors.error}]██[/{colors.error}] Error")

        # Sample panel
        self.console.print("")
        panel = Panel(
            f"[{colors.text}]This is sample text in the theme.[/{colors.text}]\n"
            f"[{colors.text_dim}]This is dimmed text.[/{colors.text_dim}]",
            title=f"[{colors.primary}]Sample Panel[/{colors.primary}]",
            border_style=colors.primary
        )
        self.console.print(panel)

        # Sample code
        code = '''def hello():
    """Say hello"""
    print("Hello, World!")
'''
        syntax = Syntax(code, "python", theme=theme.code_theme, line_numbers=theme.line_numbers)
        self.console.print(syntax)

    def show_current(self):
        """Show current theme details"""
        theme = self.get_current_theme()
        colors = theme.colors

        content_lines = []
        content_lines.append(f"[bold]Name:[/bold] {theme.name}")
        content_lines.append(f"[bold]Description:[/bold] {theme.description}")
        content_lines.append("")

        content_lines.append("[bold]Colors:[/bold]")
        content_lines.append(f"  Primary: [{colors.primary}]██[/{colors.primary}] {colors.primary}")
        content_lines.append(f"  Secondary: [{colors.secondary}]██[/{colors.secondary}] {colors.secondary}")
        content_lines.append(f"  Accent: [{colors.accent}]██[/{colors.accent}] {colors.accent}")

        content_lines.append("")
        content_lines.append("[bold]Settings:[/bold]")
        content_lines.append(f"  Icons: {'Yes' if theme.show_icons else 'No'}")
        content_lines.append(f"  Compact: {'Yes' if theme.compact_output else 'No'}")
        content_lines.append(f"  Code theme: {theme.code_theme}")

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title="[bold cyan]Current Theme[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

    def show_help(self):
        """Show theme help"""
        help_text = """
[bold cyan]Theme Commands[/bold cyan]

Customize the CLI appearance.

[bold]Commands:[/bold]
  [green]/theme[/green]              Show current theme
  [green]/theme list[/green]         List all themes
  [green]/theme set <name>[/green]   Set theme
  [green]/theme preview <n>[/green]  Preview a theme
  [green]/theme create <n>[/green]   Create custom theme
  [green]/theme edit <name>[/green]  Edit custom theme
  [green]/theme delete <n>[/green]   Delete custom theme
  [green]/theme export <n>[/green]   Export theme to file
  [green]/theme import <f>[/green]   Import theme from file

[bold]Built-in Themes:[/bold]
  • default  - Default BharatBuild theme
  • dark     - High contrast dark
  • light    - Light theme
  • ocean    - Cool blues
  • forest   - Natural greens
  • sunset   - Warm colors
  • nord     - Nord palette
  • dracula  - Dracula scheme
  • minimal  - Monochrome
  • hacker   - Matrix green

[bold]Examples:[/bold]
  /theme set dracula
  /theme preview nord
  /theme create mytheme --base ocean
"""
        self.console.print(help_text)
