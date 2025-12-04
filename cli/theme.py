"""
BharatBuild CLI Theme - Claude Code inspired styling

Provides consistent colors, icons, and formatting across the CLI.
Supports dark/light modes and colorblind-friendly options.
"""

from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum

from rich.console import Console
from rich.theme import Theme
from rich.style import Style


class ThemeMode(str, Enum):
    DARK = "dark"
    LIGHT = "light"
    DARK_COLORBLIND = "dark_colorblind"
    LIGHT_COLORBLIND = "light_colorblind"
    AUTO = "auto"


@dataclass
class CLIColors:
    """Color definitions for the CLI"""
    # Primary colors
    primary: str = "#00D9FF"      # Cyan - main accent
    secondary: str = "#FF6B6B"    # Coral - secondary accent
    success: str = "#4ADE80"      # Green
    warning: str = "#FBBF24"      # Yellow/Amber
    error: str = "#EF4444"        # Red
    info: str = "#60A5FA"         # Blue

    # Text colors
    text: str = "#E5E5E5"         # Light gray
    text_muted: str = "#A3A3A3"   # Muted gray
    text_dim: str = "#737373"     # Dim gray

    # UI colors
    border: str = "#404040"       # Border color
    background: str = "#1A1A1A"   # Background
    highlight: str = "#2D2D2D"    # Highlighted background

    # Syntax colors
    keyword: str = "#FF79C6"      # Pink
    string: str = "#F1FA8C"       # Yellow
    number: str = "#BD93F9"       # Purple
    comment: str = "#6272A4"      # Gray-blue
    function: str = "#50FA7B"     # Green
    variable: str = "#8BE9FD"     # Cyan
    operator: str = "#FF79C6"     # Pink


@dataclass
class CLIIcons:
    """Icon/emoji definitions for consistent visual language"""
    # Status icons
    success: str = "✓"
    error: str = "✗"
    warning: str = "⚠"
    info: str = "ℹ"
    pending: str = "○"
    running: str = "◐"
    complete: str = "●"

    # Action icons
    file: str = "📄"
    folder: str = "📁"
    code: str = "💻"
    terminal: str = "❯"
    git: str = "󰊢"  # Nerd font git icon, fallback below
    search: str = "🔍"
    settings: str = "⚙"
    save: str = "💾"
    delete: str = "🗑"

    # Process icons
    thinking: str = "🤔"
    generating: str = "⚡"
    building: str = "🔨"
    testing: str = "🧪"
    deploying: str = "🚀"

    # Status indicators
    online: str = "🟢"
    offline: str = "🔴"
    reconnecting: str = "🟡"

    # Misc
    sparkle: str = "✨"
    rocket: str = "🚀"
    check: str = "✅"
    cross: str = "❌"
    arrow_right: str = "→"
    arrow_down: str = "↓"
    bullet: str = "•"


# Dark theme (default) - Claude Code inspired
DARK_THEME = CLIColors(
    primary="#00D9FF",
    secondary="#FF6B6B",
    success="#4ADE80",
    warning="#FBBF24",
    error="#EF4444",
    info="#60A5FA",
    text="#E5E5E5",
    text_muted="#A3A3A3",
    text_dim="#737373",
    border="#404040",
    background="#1A1A1A",
    highlight="#2D2D2D",
)

# Light theme
LIGHT_THEME = CLIColors(
    primary="#0891B2",
    secondary="#DC2626",
    success="#16A34A",
    warning="#CA8A04",
    error="#DC2626",
    info="#2563EB",
    text="#171717",
    text_muted="#525252",
    text_dim="#737373",
    border="#D4D4D4",
    background="#FFFFFF",
    highlight="#F5F5F5",
)

# Colorblind-friendly dark theme
DARK_COLORBLIND_THEME = CLIColors(
    primary="#0077BB",      # Blue
    secondary="#EE7733",    # Orange
    success="#009988",      # Teal
    warning="#EE7733",      # Orange
    error="#CC3311",        # Red
    info="#0077BB",         # Blue
    text="#E5E5E5",
    text_muted="#A3A3A3",
    text_dim="#737373",
    border="#404040",
    background="#1A1A1A",
    highlight="#2D2D2D",
)

# Colorblind-friendly light theme
LIGHT_COLORBLIND_THEME = CLIColors(
    primary="#0077BB",
    secondary="#EE7733",
    success="#009988",
    warning="#EE7733",
    error="#CC3311",
    info="#0077BB",
    text="#171717",
    text_muted="#525252",
    text_dim="#737373",
    border="#D4D4D4",
    background="#FFFFFF",
    highlight="#F5F5F5",
)


def get_theme_colors(mode: ThemeMode) -> CLIColors:
    """Get color scheme for a theme mode"""
    themes = {
        ThemeMode.DARK: DARK_THEME,
        ThemeMode.LIGHT: LIGHT_THEME,
        ThemeMode.DARK_COLORBLIND: DARK_COLORBLIND_THEME,
        ThemeMode.LIGHT_COLORBLIND: LIGHT_COLORBLIND_THEME,
    }

    if mode == ThemeMode.AUTO:
        # Try to detect terminal background
        # Default to dark if can't detect
        return DARK_THEME

    return themes.get(mode, DARK_THEME)


def create_rich_theme(colors: CLIColors) -> Theme:
    """Create a Rich theme from CLIColors"""
    return Theme({
        # Primary styles
        "primary": Style(color=colors.primary),
        "secondary": Style(color=colors.secondary),
        "success": Style(color=colors.success),
        "warning": Style(color=colors.warning),
        "error": Style(color=colors.error),
        "info": Style(color=colors.info),

        # Text styles
        "text": Style(color=colors.text),
        "text.muted": Style(color=colors.text_muted),
        "text.dim": Style(color=colors.text_dim),

        # Component styles
        "prompt": Style(color=colors.primary, bold=True),
        "prompt.path": Style(color=colors.success),
        "prompt.git": Style(color=colors.secondary),

        # Status styles
        "status.success": Style(color=colors.success),
        "status.error": Style(color=colors.error),
        "status.warning": Style(color=colors.warning),
        "status.info": Style(color=colors.info),
        "status.pending": Style(color=colors.text_dim),

        # File styles
        "file.name": Style(color=colors.text),
        "file.path": Style(color=colors.text_muted),
        "file.size": Style(color=colors.text_dim),
        "file.created": Style(color=colors.success),
        "file.modified": Style(color=colors.warning),
        "file.deleted": Style(color=colors.error),

        # Code styles
        "code.keyword": Style(color=colors.keyword),
        "code.string": Style(color=colors.string),
        "code.number": Style(color=colors.number),
        "code.comment": Style(color=colors.comment),
        "code.function": Style(color=colors.function),

        # Panel styles
        "panel.border": Style(color=colors.border),
        "panel.title": Style(color=colors.primary, bold=True),

        # Progress styles
        "progress.description": Style(color=colors.text),
        "progress.percentage": Style(color=colors.primary),
        "progress.bar.complete": Style(color=colors.success),
        "progress.bar.finished": Style(color=colors.success),

        # Table styles
        "table.header": Style(color=colors.primary, bold=True),
        "table.row": Style(color=colors.text),
        "table.row.dim": Style(color=colors.text_dim),

        # Markdown styles
        "markdown.h1": Style(color=colors.primary, bold=True),
        "markdown.h2": Style(color=colors.primary, bold=True),
        "markdown.code": Style(color=colors.success),
        "markdown.link": Style(color=colors.info, underline=True),

        # AI/Agent styles
        "agent.name": Style(color=colors.primary, bold=True),
        "agent.thinking": Style(color=colors.text_muted, italic=True),
        "agent.action": Style(color=colors.warning),
        "agent.result": Style(color=colors.success),

        # Diff styles
        "diff.added": Style(color=colors.success),
        "diff.removed": Style(color=colors.error),
        "diff.changed": Style(color=colors.warning),
    })


class CLITheme:
    """
    Theme manager for BharatBuild CLI.

    Usage:
        theme = CLITheme(ThemeMode.DARK)
        console = theme.create_console()

        # Use styled output
        console.print("Success!", style="success")
        console.print(theme.icons.check + " Done")
    """

    def __init__(self, mode: ThemeMode = ThemeMode.AUTO):
        self.mode = mode
        self.colors = get_theme_colors(mode)
        self.icons = CLIIcons()
        self.rich_theme = create_rich_theme(self.colors)

    def create_console(self, **kwargs) -> Console:
        """Create a Rich console with theme applied"""
        return Console(theme=self.rich_theme, **kwargs)

    def style(self, text: str, style_name: str) -> str:
        """Apply a style to text"""
        return f"[{style_name}]{text}[/{style_name}]"

    def success(self, text: str) -> str:
        return f"[success]{self.icons.success} {text}[/success]"

    def error(self, text: str) -> str:
        return f"[error]{self.icons.error} {text}[/error]"

    def warning(self, text: str) -> str:
        return f"[warning]{self.icons.warning} {text}[/warning]"

    def info(self, text: str) -> str:
        return f"[info]{self.icons.info} {text}[/info]"

    def primary(self, text: str) -> str:
        return f"[primary]{text}[/primary]"

    def muted(self, text: str) -> str:
        return f"[text.muted]{text}[/text.muted]"

    def dim(self, text: str) -> str:
        return f"[text.dim]{text}[/text.dim]"


# Default theme instance
default_theme = CLITheme(ThemeMode.DARK)


# Convenience functions
def get_icons() -> CLIIcons:
    """Get default icons"""
    return default_theme.icons


def get_colors() -> CLIColors:
    """Get default colors"""
    return default_theme.colors


# Box drawing characters for panels (Claude Code style)
class BoxChars:
    """Box drawing characters for Claude Code style panels"""
    # Single line
    TOP_LEFT = "╭"
    TOP_RIGHT = "╮"
    BOTTOM_LEFT = "╰"
    BOTTOM_RIGHT = "╯"
    HORIZONTAL = "─"
    VERTICAL = "│"

    # Double line (for emphasis)
    D_TOP_LEFT = "╔"
    D_TOP_RIGHT = "╗"
    D_BOTTOM_LEFT = "╚"
    D_BOTTOM_RIGHT = "╝"
    D_HORIZONTAL = "═"
    D_VERTICAL = "║"

    # Progress bars
    PROGRESS_FULL = "█"
    PROGRESS_HALF = "▌"
    PROGRESS_EMPTY = "░"

    # Spinners
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    DOTS_FRAMES = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]


# ANSI escape codes for true color support
def rgb(r: int, g: int, b: int) -> str:
    """Generate ANSI escape code for RGB color"""
    return f"\033[38;2;{r};{g};{b}m"


def bg_rgb(r: int, g: int, b: int) -> str:
    """Generate ANSI escape code for RGB background color"""
    return f"\033[48;2;{r};{g};{b}m"


def reset() -> str:
    """Reset ANSI formatting"""
    return "\033[0m"
