"""
BharatBuild CLI — Tool Permission Confirmation
================================================
Kiro/Goose-style interactive permission dialog shown before the AI
executes any tool that touches files, runs shell commands, or calls
external APIs.

Mirrors Goose's prompt_tool_confirmation() in session/mod.rs.

Permission levels
-----------------
  ALLOW_ONCE    — allow this single call only
  ALWAYS_ALLOW  — always allow this tool (saved to session)
  DENY_ONCE     — deny this single call
  DENY_ALWAYS   — always deny this tool (saved to session)
  CANCEL        — cancel the AI response entirely

Usage
-----
    confirmer = ToolConfirmer(config)

    result = await confirmer.ask(
        tool_name   = "shell",
        description = "rm -rf /tmp/old-build",
        tool_input  = {"command": "rm -rf /tmp/old-build"},
    )

    if result == Permission.CANCEL:
        # abort the agent turn
        ...
    elif result in (Permission.DENY_ONCE, Permission.DENY_ALWAYS):
        # skip this tool call
        ...
    else:
        # proceed
        ...
"""

from __future__ import annotations

import json
from enum import Enum, auto
from typing import Any, Dict, Optional, Set

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from cli.config import CLIConfig


# ── permission enum ───────────────────────────────────────────────────────────

class Permission(str, Enum):
    ALLOW_ONCE   = "allow_once"
    ALWAYS_ALLOW = "always_allow"
    DENY_ONCE    = "deny_once"
    DENY_ALWAYS  = "deny_always"
    CANCEL       = "cancel"


# ── tool risk levels ──────────────────────────────────────────────────────────

class RiskLevel(Enum):
    LOW    = "low"      # read-only ops
    MEDIUM = "medium"   # write / network
    HIGH   = "high"     # destructive / shell

_TOOL_RISK: dict[str, RiskLevel] = {
    # low risk
    "read":           RiskLevel.LOW,
    "list_dir":       RiskLevel.LOW,
    "search":         RiskLevel.LOW,
    "grep":           RiskLevel.LOW,
    "glob":           RiskLevel.LOW,
    "get_project":    RiskLevel.LOW,
    "list_projects":  RiskLevel.LOW,
    # medium risk
    "write":          RiskLevel.MEDIUM,
    "edit":           RiskLevel.MEDIUM,
    "create_file":    RiskLevel.MEDIUM,
    "upload":         RiskLevel.MEDIUM,
    "web_fetch":      RiskLevel.MEDIUM,
    "web_search":     RiskLevel.MEDIUM,
    # high risk
    "shell":          RiskLevel.HIGH,
    "bash":           RiskLevel.HIGH,
    "exec":           RiskLevel.HIGH,
    "run":            RiskLevel.HIGH,
    "delete":         RiskLevel.HIGH,
    "delete_project": RiskLevel.HIGH,
    "docker_run":     RiskLevel.HIGH,
    "container_exec": RiskLevel.HIGH,
}

def _risk(tool_name: str) -> RiskLevel:
    local = tool_name.rsplit("__", 1)[-1].lower()
    return _TOOL_RISK.get(local, RiskLevel.MEDIUM)

_RISK_COLOR = {
    RiskLevel.LOW:    "green",
    RiskLevel.MEDIUM: "yellow",
    RiskLevel.HIGH:   "red",
}

_RISK_LABEL = {
    RiskLevel.LOW:    "LOW RISK",
    RiskLevel.MEDIUM: "MEDIUM RISK",
    RiskLevel.HIGH:   "HIGH RISK",
}


# ── ToolConfirmer ─────────────────────────────────────────────────────────────

class ToolConfirmer:
    """
    Manages tool permission decisions for a CLI session.

    Remembers ALWAYS_ALLOW / DENY_ALWAYS decisions so the user is not
    re-prompted for tools they've already approved.
    """

    def __init__(self, config: CLIConfig):
        self.config          = config
        self._always_allow:  Set[str] = set()
        self._always_deny:   Set[str] = set()
        self._console        = Console()

    # ── main entry ────────────────────────────────────────────────────────────

    async def ask(
        self,
        tool_name:   str,
        description: str = "",
        tool_input:  Optional[Dict[str, Any]] = None,
    ) -> Permission:
        """
        Show the confirmation dialog for a tool call.

        Returns Permission without prompting if the tool has an
        existing ALWAYS_ALLOW / DENY_ALWAYS decision.
        """
        # permission mode overrides
        mode = self.config.permission_mode
        if mode == "auto":
            return Permission.ALLOW_ONCE
        if mode == "deny":
            return Permission.DENY_ONCE

        # session memory
        key = _tool_key(tool_name)
        if key in self._always_allow:
            return Permission.ALLOW_ONCE
        if key in self._always_deny:
            return Permission.DENY_ONCE

        # interactive prompt
        perm = self._show_dialog(tool_name, description, tool_input)

        if perm == Permission.ALWAYS_ALLOW:
            self._always_allow.add(key)
        elif perm == Permission.DENY_ALWAYS:
            self._always_deny.add(key)

        return perm

    def reset_session_memory(self) -> None:
        """Clear all ALWAYS_* decisions (call on /clear or /new)."""
        self._always_allow.clear()
        self._always_deny.clear()

    # ── dialog rendering ──────────────────────────────────────────────────────

    def _show_dialog(
        self,
        tool_name:   str,
        description: str,
        tool_input:  Optional[Dict[str, Any]],
    ) -> Permission:
        """Render the permission panel and collect user choice."""
        risk       = _risk(tool_name)
        risk_color = _RISK_COLOR[risk]
        risk_label = _RISK_LABEL[risk]

        # ── header ────────────────────────────────────────────────────────────
        self._console.print()
        header = Text()
        header.append("  ● Tool Request  ", style="bold white")
        header.append(f"[{risk_label}]", style=f"bold {risk_color}")

        # ── info table ────────────────────────────────────────────────────────
        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column(style="dim",   justify="right")
        t.add_column(style="white bold")

        local_name = tool_name.rsplit("__", 1)[-1]
        ext_name   = tool_name.rsplit("__", 1)[0] if "__" in tool_name else ""

        t.add_row("Tool",      local_name)
        if ext_name:
            t.add_row("Extension", ext_name)
        if description:
            preview = description[:120] + ("…" if len(description) > 120 else "")
            t.add_row("Action",    preview)

        self._console.print(Panel(t, title=header, border_style=risk_color))

        # ── tool input preview ────────────────────────────────────────────────
        if tool_input:
            self._show_input_preview(tool_name, tool_input, risk_color)

        # ── menu ──────────────────────────────────────────────────────────────
        return self._show_menu(risk)

    def _show_input_preview(
        self,
        tool_name:  str,
        tool_input: Dict[str, Any],
        color:      str,
    ) -> None:
        """Show a syntax-highlighted preview of the tool input."""
        local = tool_name.rsplit("__", 1)[-1].lower()

        if local in ("shell", "bash", "exec", "run"):
            cmd = tool_input.get("command", tool_input.get("cmd", ""))
            if cmd:
                self._console.print(
                    Syntax(str(cmd), "bash", theme="monokai",
                           background_color="default")
                )
        elif local in ("write", "edit", "create_file"):
            path = tool_input.get("path", "")
            content = tool_input.get("content", "")
            if path:
                self._console.print(f"  [dim]file:[/dim] [bold]{path}[/bold]")
            if content:
                preview = content[:300]
                lang    = _ext_to_lang(Path(path).suffix if path else "")
                self._console.print(
                    Syntax(preview + ("…" if len(content) > 300 else ""),
                           lang, theme="monokai", background_color="default")
                )
        else:
            # generic JSON preview
            try:
                preview = json.dumps(tool_input, indent=2)[:400]
                self._console.print(
                    Syntax(preview, "json", theme="monokai",
                           background_color="default")
                )
            except Exception:
                pass

    def _show_menu(self, risk: RiskLevel) -> Permission:
        """Show numbered options and return the chosen Permission."""
        self._console.print()
        self._console.print("  [bold]Allow this tool call?[/bold]")
        self._console.print()

        options = [
            ("1", "Allow once",    Permission.ALLOW_ONCE,   "green"),
            ("2", "Always allow",  Permission.ALWAYS_ALLOW, "green"),
            ("3", "Deny once",     Permission.DENY_ONCE,    "yellow"),
            ("4", "Always deny",   Permission.DENY_ALWAYS,  "yellow"),
            ("5", "Cancel turn",   Permission.CANCEL,       "red"),
        ]

        for key, label, _, color in options:
            self._console.print(
                f"  [{color}]{key}[/{color}]  {label}"
            )

        self._console.print()

        while True:
            try:
                choice = Prompt.ask(
                    "  [bold cyan]Choice[/bold cyan]",
                    choices=["1", "2", "3", "4", "5"],
                    default="1",
                )
            except (KeyboardInterrupt, EOFError):
                return Permission.CANCEL

            for key, _, perm, _ in options:
                if choice == key:
                    return perm

            self._console.print("[red]Please enter 1-5[/red]")


# ── helpers ───────────────────────────────────────────────────────────────────

def _tool_key(tool_name: str) -> str:
    """Normalise a tool name for memory lookup."""
    return tool_name.lower().strip()


def _ext_to_lang(ext: str) -> str:
    mapping = {
        ".py": "python",   ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript",".jsx":"javascript",  ".html": "html",
        ".css": "css",     ".json": "json",       ".yaml": "yaml",
        ".yml": "yaml",    ".toml": "toml",       ".md": "markdown",
        ".sh":  "bash",    ".sql": "sql",         ".rs": "rust",
        ".go":  "go",      ".java": "java",
    }
    return mapping.get(ext.lower(), "text")


# need Path for _show_input_preview
from pathlib import Path
