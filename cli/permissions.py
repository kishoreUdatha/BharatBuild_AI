"""
BharatBuild CLI Permissions System

Claude Code style permission prompts with memory:
  Allow Write to src/app.py?
    (y)es  (n)o  (a)lways  (d)on't allow this session
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt


class PermissionType(str, Enum):
    """Types of permissions"""
    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    DELETE = "delete"
    EXECUTE = "execute"  # Bash commands
    NETWORK = "network"  # Web fetch/search
    MCP = "mcp"  # MCP tool access


class PermissionResponse(str, Enum):
    """User responses to permission prompts"""
    YES = "yes"           # Allow this once
    NO = "no"             # Deny this once
    ALWAYS = "always"     # Always allow this type
    NEVER = "never"       # Never allow this type (this session)
    ALWAYS_FILE = "always_file"  # Always allow for this specific file


@dataclass
class PermissionRule:
    """A permission rule with memory"""
    permission_type: PermissionType
    pattern: str  # File path pattern or command pattern
    response: PermissionResponse
    created_at: datetime = field(default_factory=datetime.now)
    expires_session: bool = True  # Reset on new session


@dataclass
class PermissionState:
    """Current permission state"""
    # Always allow rules (persist across sessions)
    always_allow: Dict[PermissionType, Set[str]] = field(default_factory=dict)

    # Always deny rules (session only)
    always_deny: Dict[PermissionType, Set[str]] = field(default_factory=dict)

    # Type-level rules
    allow_all_type: Set[PermissionType] = field(default_factory=set)
    deny_all_type: Set[PermissionType] = field(default_factory=set)

    # History of decisions
    history: list = field(default_factory=list)


class PermissionManager:
    """
    Manages permissions with Claude Code style prompts.

    Usage:
        pm = PermissionManager(console)

        # Check permission (will prompt if needed)
        if await pm.check_permission(PermissionType.WRITE, "src/app.py"):
            # Write file...

        # Check bash command
        if await pm.check_bash_permission("rm -rf node_modules"):
            # Execute command...
    """

    def __init__(
        self,
        console: Console,
        config_dir: Optional[Path] = None,
        auto_allow: bool = False,
        auto_deny: bool = False
    ):
        self.console = console
        self.config_dir = config_dir or Path.home() / ".bharatbuild"
        self.auto_allow = auto_allow
        self.auto_deny = auto_deny

        # Initialize state
        self.state = PermissionState()

        # Load persisted rules
        self._load_rules()

        # Dangerous patterns that always require confirmation
        self.dangerous_patterns = {
            PermissionType.EXECUTE: [
                r"rm\s+-rf",
                r"rm\s+-r",
                r"rmdir",
                r"del\s+/[sS]",
                r"format\s+",
                r"mkfs",
                r"dd\s+if=",
                r">\s*/dev/",
                r"chmod\s+777",
                r"sudo\s+",
                r"curl.*\|\s*sh",
                r"wget.*\|\s*sh",
            ],
            PermissionType.DELETE: [
                r"\.env",
                r"\.git",
                r"node_modules",
                r"__pycache__",
            ],
            PermissionType.WRITE: [
                r"\.env",
                r"\.git/",
                r"id_rsa",
                r"\.pem$",
                r"password",
                r"secret",
            ]
        }

    def _load_rules(self):
        """Load persisted permission rules"""
        rules_file = self.config_dir / "permissions.json"
        if rules_file.exists():
            try:
                with open(rules_file) as f:
                    data = json.load(f)

                # Load always allow rules
                for ptype, patterns in data.get("always_allow", {}).items():
                    self.state.always_allow[PermissionType(ptype)] = set(patterns)

            except Exception:
                pass  # Ignore errors, start fresh

    def _save_rules(self):
        """Save permission rules"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        rules_file = self.config_dir / "permissions.json"

        data = {
            "always_allow": {
                ptype.value: list(patterns)
                for ptype, patterns in self.state.always_allow.items()
            }
        }

        with open(rules_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _is_dangerous(self, permission_type: PermissionType, target: str) -> bool:
        """Check if operation matches dangerous patterns"""
        import re

        patterns = self.dangerous_patterns.get(permission_type, [])
        for pattern in patterns:
            if re.search(pattern, target, re.IGNORECASE):
                return True
        return False

    def _check_rules(self, permission_type: PermissionType, target: str) -> Optional[bool]:
        """Check if existing rules apply. Returns None if no rule matches."""
        # Check type-level rules
        if permission_type in self.state.allow_all_type:
            return True
        if permission_type in self.state.deny_all_type:
            return False

        # Check specific patterns - always allow
        if permission_type in self.state.always_allow:
            for pattern in self.state.always_allow[permission_type]:
                if self._matches_pattern(target, pattern):
                    return True

        # Check specific patterns - always deny (session)
        if permission_type in self.state.always_deny:
            for pattern in self.state.always_deny[permission_type]:
                if self._matches_pattern(target, pattern):
                    return False

        return None

    def _matches_pattern(self, target: str, pattern: str) -> bool:
        """Check if target matches pattern (supports glob-like matching)"""
        import fnmatch
        return fnmatch.fnmatch(target, pattern) or target == pattern

    def _get_permission_display(self, permission_type: PermissionType, target: str) -> Tuple[str, str]:
        """Get display text for permission prompt"""
        type_displays = {
            PermissionType.READ: ("Read", "📖"),
            PermissionType.WRITE: ("Write to", "📝"),
            PermissionType.EDIT: ("Edit", "✏️"),
            PermissionType.DELETE: ("Delete", "🗑️"),
            PermissionType.EXECUTE: ("Execute", "❯"),
            PermissionType.NETWORK: ("Access", "🌐"),
            PermissionType.MCP: ("Use MCP tool", "🔌"),
        }

        action, icon = type_displays.get(permission_type, ("Access", "🔒"))
        return action, icon

    async def prompt_permission(
        self,
        permission_type: PermissionType,
        target: str,
        context: Optional[str] = None
    ) -> PermissionResponse:
        """
        Show permission prompt and get user response.

        ╭─ Permission Required ───────────────────╮
        │                                         │
        │  Allow Write to src/app.py?             │
        │                                         │
        │  (y)es  (n)o  (a)lways  (d)on't allow   │
        │                                         │
        ╰─────────────────────────────────────────╯
        """
        action, icon = self._get_permission_display(permission_type, target)

        # Check if dangerous
        is_dangerous = self._is_dangerous(permission_type, target)

        # Build prompt content
        content_lines = []
        content_lines.append("")

        if is_dangerous:
            content_lines.append(f"[bold red]⚠️  DANGEROUS OPERATION[/bold red]")
            content_lines.append("")

        content_lines.append(f"[bold]{icon} {action} [cyan]{target}[/cyan]?[/bold]")

        if context:
            content_lines.append("")
            content_lines.append(f"[dim]{context}[/dim]")

        content_lines.append("")

        # Options
        if is_dangerous:
            content_lines.append("[dim](y)es[/dim]  [dim](n)o[/dim]")
        else:
            content_lines.append("[dim](y)es[/dim]  [dim](n)o[/dim]  [dim](a)lways[/dim]  [dim](d)on't allow this session[/dim]")

        content_lines.append("")

        # Create panel
        border_style = "red" if is_dangerous else "yellow"
        panel = Panel(
            Text.from_markup("\n".join(content_lines)),
            title="[bold yellow]Permission Required[/bold yellow]",
            border_style=border_style
        )

        self.console.print(panel)

        # Get response
        valid_responses = ['y', 'n']
        if not is_dangerous:
            valid_responses.extend(['a', 'd'])

        while True:
            response = Prompt.ask(
                "[yellow]Choice[/yellow]",
                choices=valid_responses,
                default='n'
            )

            if response == 'y':
                return PermissionResponse.YES
            elif response == 'n':
                return PermissionResponse.NO
            elif response == 'a':
                return PermissionResponse.ALWAYS
            elif response == 'd':
                return PermissionResponse.NEVER

    async def check_permission(
        self,
        permission_type: PermissionType,
        target: str,
        context: Optional[str] = None
    ) -> bool:
        """
        Check if operation is allowed. Prompts user if needed.

        Returns True if allowed, False if denied.
        """
        # Auto modes
        if self.auto_allow:
            return True
        if self.auto_deny:
            return False

        # Check existing rules
        rule_result = self._check_rules(permission_type, target)
        if rule_result is not None:
            return rule_result

        # Prompt user
        response = await self.prompt_permission(permission_type, target, context)

        # Handle response
        if response == PermissionResponse.YES:
            self._record_decision(permission_type, target, True)
            return True

        elif response == PermissionResponse.NO:
            self._record_decision(permission_type, target, False)
            return False

        elif response == PermissionResponse.ALWAYS:
            # Add to always allow
            if permission_type not in self.state.always_allow:
                self.state.always_allow[permission_type] = set()
            self.state.always_allow[permission_type].add(target)
            self._save_rules()
            self._record_decision(permission_type, target, True, persist=True)
            return True

        elif response == PermissionResponse.NEVER:
            # Add to session deny
            if permission_type not in self.state.always_deny:
                self.state.always_deny[permission_type] = set()
            self.state.always_deny[permission_type].add(target)
            self._record_decision(permission_type, target, False)
            return False

        return False

    async def check_file_permission(
        self,
        operation: str,
        path: str,
        context: Optional[str] = None
    ) -> bool:
        """Convenience method for file operations"""
        op_map = {
            "read": PermissionType.READ,
            "write": PermissionType.WRITE,
            "edit": PermissionType.EDIT,
            "delete": PermissionType.DELETE,
            "create": PermissionType.WRITE,
        }

        permission_type = op_map.get(operation.lower(), PermissionType.WRITE)
        return await self.check_permission(permission_type, path, context)

    async def check_bash_permission(
        self,
        command: str,
        context: Optional[str] = None
    ) -> bool:
        """Check permission for bash command execution"""
        return await self.check_permission(
            PermissionType.EXECUTE,
            command,
            context
        )

    def allow_all(self, permission_type: PermissionType):
        """Allow all operations of this type for this session"""
        self.state.allow_all_type.add(permission_type)

    def deny_all(self, permission_type: PermissionType):
        """Deny all operations of this type for this session"""
        self.state.deny_all_type.add(permission_type)

    def reset_session(self):
        """Reset session-only rules"""
        self.state.always_deny.clear()
        self.state.allow_all_type.clear()
        self.state.deny_all_type.clear()
        self.state.history.clear()

    def _record_decision(
        self,
        permission_type: PermissionType,
        target: str,
        allowed: bool,
        persist: bool = False
    ):
        """Record a permission decision"""
        self.state.history.append({
            "type": permission_type.value,
            "target": target,
            "allowed": allowed,
            "persist": persist,
            "timestamp": datetime.now().isoformat()
        })

    def get_history(self) -> list:
        """Get permission decision history"""
        return self.state.history.copy()

    def show_status(self):
        """Show current permission status"""
        self.console.print("\n[bold cyan]Permission Status[/bold cyan]")
        self.console.print()

        # Always allow
        if self.state.always_allow:
            self.console.print("[green]Always Allow:[/green]")
            for ptype, patterns in self.state.always_allow.items():
                for p in patterns:
                    self.console.print(f"  [green]✓[/green] {ptype.value}: {p}")

        # Session deny
        if self.state.always_deny:
            self.console.print("\n[red]Session Deny:[/red]")
            for ptype, patterns in self.state.always_deny.items():
                for p in patterns:
                    self.console.print(f"  [red]✗[/red] {ptype.value}: {p}")

        # Type-level rules
        if self.state.allow_all_type:
            self.console.print("\n[green]Allow All (this session):[/green]")
            for ptype in self.state.allow_all_type:
                self.console.print(f"  [green]✓[/green] {ptype.value}")

        if self.state.deny_all_type:
            self.console.print("\n[red]Deny All (this session):[/red]")
            for ptype in self.state.deny_all_type:
                self.console.print(f"  [red]✗[/red] {ptype.value}")

        self.console.print()
