"""
BharatBuild CLI — Authentication
==================================
Handles login, logout, registration, token persistence, and whoami.

Token storage: ~/.bharatbuild/credentials.json  (600 permissions on POSIX)

Public API
----------
    AuthManager.login(email, password)   -> UserCredentials
    AuthManager.logout()
    AuthManager.load()                   -> UserCredentials | None
    AuthManager.require()                -> UserCredentials  (raises if not logged in)
    print_whoami(creds)                  -> pretty table

Interactive helpers
-------------------
    interactive_login(config)            -> UserCredentials | None
    interactive_register(config)         -> UserCredentials | None
"""

from __future__ import annotations

import json
import os
import stat
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from cli.config import CLIConfig

console = Console()

_CREDS_FILE = Path.home() / ".bharatbuild" / "credentials.json"


# ── data model ───────────────────────────────────────────────────────────────

@dataclass
class UserCredentials:
    user_id:       str
    email:         str
    name:          str
    access_token:  str
    refresh_token: Optional[str]  = None
    token_expiry:  Optional[str]  = None
    tier:          str            = "free"
    college_name:  Optional[str]  = None
    department:    Optional[str]  = None
    avatar_url:    str            = ""
    saved_at:      str            = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── persistence ──────────────────────────────────────────────────────────────

def _save_credentials(creds: UserCredentials) -> None:
    _CREDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CREDS_FILE.write_text(json.dumps(asdict(creds), indent=2))
    # restrict permissions on POSIX so only owner can read
    try:
        os.chmod(_CREDS_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except AttributeError:
        pass  # Windows — skip


def _load_credentials() -> Optional[UserCredentials]:
    if not _CREDS_FILE.exists():
        return None
    try:
        data = json.loads(_CREDS_FILE.read_text())
        return UserCredentials(**{k: v for k, v in data.items() if k in UserCredentials.__dataclass_fields__})
    except Exception:
        return None


def _delete_credentials() -> None:
    if _CREDS_FILE.exists():
        _CREDS_FILE.unlink()


# ── AuthManager ──────────────────────────────────────────────────────────────

class AuthManager:
    """
    Central auth façade used by the rest of the CLI.

    Every method is synchronous because credential file I/O is trivial;
    network calls are delegated to the caller (main, commands, etc.) which
    already owns an async context.
    """

    # ── read ────────────────────────────────────────────────────────────────

    @staticmethod
    def load() -> Optional[UserCredentials]:
        """Return stored credentials or None."""
        return _load_credentials()

    @staticmethod
    def require() -> UserCredentials:
        """Return credentials or print error + exit."""
        creds = _load_credentials()
        if not creds:
            console.print(
                Panel(
                    "[bold red]Not logged in.[/bold red]\n\n"
                    "Run [bold cyan]bharatbuild login[/bold cyan] to authenticate.",
                    title="Auth Required",
                    border_style="red",
                )
            )
            sys.exit(1)
        return creds

    # ── write ───────────────────────────────────────────────────────────────

    @staticmethod
    def save_from_response(response: dict) -> UserCredentials:
        """
        Parse a /auth/login or /auth/register response dict and persist.
        The backend returns either a flat LoginResponse or a nested structure
        — we handle both shapes.
        """
        # extract token
        token = (
            response.get("access_token")
            or response.get("token", {}).get("access_token", "")
        )
        refresh = (
            response.get("refresh_token")
            or response.get("token", {}).get("refresh_token")
        )
        # extract user
        user = response.get("user", response)

        creds = UserCredentials(
            user_id       = str(user.get("id", user.get("user_id", ""))),
            email         = user.get("email", ""),
            name          = user.get("name", user.get("full_name", "")),
            access_token  = token,
            refresh_token = refresh,
            token_expiry  = user.get("token_expiry"),
            tier          = user.get("tier", user.get("account_tier", "free")),
            college_name  = user.get("college_name"),
            department    = user.get("department"),
            avatar_url    = user.get("avatar_url", ""),
        )
        _save_credentials(creds)
        return creds

    @staticmethod
    def logout() -> None:
        _delete_credentials()

    @staticmethod
    def inject_into_config(config: CLIConfig, creds: UserCredentials) -> None:
        """Push credentials into the live config object."""
        config.auth_token  = creds.access_token
        config.user_id     = creds.user_id
        config.user_email  = creds.email
        config.user_name   = creds.name


# ── display helpers ───────────────────────────────────────────────────────────

def print_whoami(creds: UserCredentials) -> None:
    """Print a pretty account summary table."""
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="dim", justify="right")
    t.add_column(style="bold white")

    tier_color = {
        "free":       "white",
        "student":    "cyan",
        "pro":        "green",
        "team":       "yellow",
        "enterprise": "magenta",
    }.get(creds.tier.lower(), "white")

    t.add_row("Name",    creds.name)
    t.add_row("Email",   creds.email)
    t.add_row("User ID", creds.user_id)
    t.add_row("Plan",    Text(creds.tier.upper(), style=f"bold {tier_color}"))
    if creds.college_name:
        t.add_row("College", creds.college_name)
    if creds.department:
        t.add_row("Dept",    creds.department)
    if creds.saved_at:
        try:
            dt = datetime.fromisoformat(creds.saved_at).strftime("%d %b %Y %H:%M")
            t.add_row("Logged in", dt)
        except ValueError:
            pass

    console.print(
        Panel(t, title="[bold cyan]● Logged In[/bold cyan]", border_style="cyan")
    )


# ── interactive flows ─────────────────────────────────────────────────────────

async def interactive_login(config: CLIConfig) -> Optional[UserCredentials]:
    """
    Prompt for email + password, POST to /auth/login, store credentials.
    Returns UserCredentials on success, None on failure.
    """
    from cli.client import BharatBuildClient, APIError, AuthError

    console.print()
    console.print(Panel(
        "[bold]Welcome back![/bold]\nEnter your BharatBuild credentials.",
        title="[cyan]Login[/cyan]",
        border_style="cyan",
    ))

    email    = Prompt.ask("  [cyan]Email[/cyan]")
    password = Prompt.ask("  [cyan]Password[/cyan]", password=True)

    with console.status("[cyan]Authenticating…[/cyan]", spinner="dots"):
        try:
            async with BharatBuildClient(config) as client:
                resp = await client.login(email, password)
        except AuthError:
            console.print("[red]✗ Invalid email or password.[/red]")
            return None
        except APIError as exc:
            console.print(f"[red]✗ Login failed: {exc.detail}[/red]")
            return None

    creds = AuthManager.save_from_response(resp)
    AuthManager.inject_into_config(config, creds)
    console.print(f"\n[bold green]✓ Logged in as {creds.name} ({creds.email})[/bold green]")
    return creds


async def interactive_register(config: CLIConfig) -> Optional[UserCredentials]:
    """
    Prompt for name/email/password, POST to /auth/register, store credentials.
    Returns UserCredentials on success, None on failure.
    """
    from cli.client import BharatBuildClient, APIError

    console.print()
    console.print(Panel(
        "[bold]Create your BharatBuild account.[/bold]",
        title="[cyan]Register[/cyan]",
        border_style="cyan",
    ))

    name     = Prompt.ask("  [cyan]Full Name[/cyan]")
    email    = Prompt.ask("  [cyan]Email[/cyan]")
    password = Prompt.ask("  [cyan]Password[/cyan]", password=True)
    confirm  = Prompt.ask("  [cyan]Confirm Password[/cyan]", password=True)

    if password != confirm:
        console.print("[red]✗ Passwords do not match.[/red]")
        return None

    with console.status("[cyan]Creating account…[/cyan]", spinner="dots"):
        try:
            async with BharatBuildClient(config) as client:
                resp = await client.register(email, password, name)
        except APIError as exc:
            console.print(f"[red]✗ Registration failed: {exc.detail}[/red]")
            return None

    # Some backends return the user object directly on register without a token
    # In that case, prompt them to login
    if not resp.get("access_token") and not resp.get("token"):
        console.print(
            "[green]✓ Account created![/green] "
            "Please check your email to verify, then run [cyan]bharatbuild login[/cyan]."
        )
        return None

    creds = AuthManager.save_from_response(resp)
    AuthManager.inject_into_config(config, creds)
    console.print(f"\n[bold green]✓ Account created and logged in as {creds.name}[/bold green]")
    return creds


async def login_with_token(config: CLIConfig, token: str) -> Optional[UserCredentials]:
    """
    Login using a pre-generated CLI token (copied from the web portal).
    Fetches /users/me to resolve user info.
    """
    from cli.client import BharatBuildClient, APIError, AuthError

    config.auth_token = token
    with console.status("[cyan]Validating token…[/cyan]", spinner="dots"):
        try:
            async with BharatBuildClient(config) as client:
                user = await client.me()
        except (APIError, AuthError) as exc:
            console.print(f"[red]✗ Invalid token: {exc.detail}[/red]")
            config.auth_token = None
            return None

    creds = UserCredentials(
        user_id      = str(user.get("id", "")),
        email        = user.get("email", ""),
        name         = user.get("name", user.get("full_name", "")),
        access_token = token,
        tier         = user.get("tier", "free"),
    )
    _save_credentials(creds)
    AuthManager.inject_into_config(config, creds)
    console.print(f"[bold green]✓ Logged in as {creds.name} ({creds.email})[/bold green]")
    return creds
