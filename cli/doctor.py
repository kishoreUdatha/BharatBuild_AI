"""
BharatBuild CLI — Doctor
===========================
Runs a series of diagnostic checks and prints a pass/fail report.

    await run_doctor(config)

Checks
------
  ✓ Python version         ≥ 3.10
  ✓ Required packages      httpx, rich, prompt_toolkit
  ✓ Config directory       ~/.bharatbuild exists & writeable
  ✓ Credentials file       exists & valid JSON
  ✓ Backend reachable      GET /health → {"status":"healthy"}
  ✓ Authentication         GET /users/me → 200
  ✓ Token balance          GET /tokens/balance
  ✓ Docker available       `docker info` exits 0
  ✓ Git available          `git --version`
"""

from __future__ import annotations

import asyncio
import importlib
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cli.config import CLIConfig

console = Console()

# ── result model ─────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    name:    str
    ok:      bool
    detail:  str = ""
    warning: bool = False   # True → yellow instead of green


@dataclass
class DoctorReport:
    results: List[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        self.results.append(result)

    @property
    def all_ok(self) -> bool:
        return all(r.ok or r.warning for r in self.results)

    @property
    def failures(self) -> List[CheckResult]:
        return [r for r in self.results if not r.ok and not r.warning]


# ── individual checks ─────────────────────────────────────────────────────────

async def _check_python(config: CLIConfig) -> CheckResult:
    major, minor = sys.version_info[:2]
    ok = (major, minor) >= (3, 10)
    return CheckResult(
        name   = "Python version",
        ok     = ok,
        detail = f"{major}.{minor}  (need ≥ 3.10)" if not ok else f"{major}.{minor}",
    )


async def _check_packages(config: CLIConfig) -> CheckResult:
    required = ["httpx", "rich", "prompt_toolkit", "aiofiles"]
    missing  = []
    for pkg in required:
        try:
            importlib.import_module(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        return CheckResult(
            name   = "Required packages",
            ok     = False,
            detail = f"Missing: {', '.join(missing)}  →  pip install {' '.join(missing)}",
        )
    return CheckResult(name="Required packages", ok=True, detail="all present")


async def _check_config_dir(config: CLIConfig) -> CheckResult:
    d = Path(config.config_dir)
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".write_test"
        probe.write_text("ok")
        probe.unlink()
        return CheckResult(name="Config directory", ok=True, detail=str(d))
    except Exception as exc:
        return CheckResult(name="Config directory", ok=False, detail=str(exc))


async def _check_credentials(config: CLIConfig) -> CheckResult:
    from cli.auth import AuthManager
    creds = AuthManager.load()
    if creds is None:
        return CheckResult(
            name    = "Credentials",
            ok      = False,
            warning = True,
            detail  = "Not logged in — run [cyan]bharatbuild login[/cyan]",
        )
    return CheckResult(
        name   = "Credentials",
        ok     = True,
        detail = f"{creds.email}  (tier: {creds.tier})",
    )


async def _check_backend(config: CLIConfig) -> CheckResult:
    from cli.client import BharatBuildClient

    try:
        async with BharatBuildClient(config) as client:
            healthy = await client.health()
        if healthy:
            return CheckResult(name="Backend reachable", ok=True, detail=config.api_base_url)
        return CheckResult(
            name   = "Backend reachable",
            ok     = False,
            detail = f"Unhealthy response from {config.api_base_url}",
        )
    except Exception as exc:
        return CheckResult(
            name   = "Backend reachable",
            ok     = False,
            detail = f"{exc}  (is the server running?)",
        )


async def _check_auth_api(config: CLIConfig) -> CheckResult:
    from cli.client import BharatBuildClient, APIError, AuthError
    from cli.auth  import AuthManager

    creds = AuthManager.load()
    if not creds:
        return CheckResult(
            name    = "API authentication",
            ok      = False,
            warning = True,
            detail  = "Skipped — not logged in",
        )

    try:
        async with BharatBuildClient(config) as client:
            me = await client.me()
        return CheckResult(
            name   = "API authentication",
            ok     = True,
            detail = f"Token valid for {me.get('email', '?')}",
        )
    except AuthError:
        return CheckResult(
            name   = "API authentication",
            ok     = False,
            detail = "Token rejected — run [cyan]bharatbuild login[/cyan] again",
        )
    except APIError as exc:
        return CheckResult(
            name   = "API authentication",
            ok     = False,
            detail = str(exc),
        )


async def _check_token_balance(config: CLIConfig) -> CheckResult:
    from cli.client import BharatBuildClient, APIError
    from cli.auth  import AuthManager

    creds = AuthManager.load()
    if not creds:
        return CheckResult(
            name    = "Token balance",
            ok      = True,
            warning = True,
            detail  = "Skipped — not logged in",
        )

    try:
        async with BharatBuildClient(config) as client:
            data = await client.token_balance()
        balance = data.get("balance", data.get("tokens_remaining", "?"))
        return CheckResult(name="Token balance", ok=True, detail=str(balance))
    except Exception as exc:
        return CheckResult(
            name    = "Token balance",
            ok      = True,
            warning = True,
            detail  = f"Could not fetch: {exc}",
        )


async def _check_docker(config: CLIConfig) -> CheckResult:
    if not shutil.which("docker"):
        return CheckResult(
            name    = "Docker",
            ok      = True,
            warning = True,
            detail  = "Not installed — required for sandbox execution",
        )
    try:
        proc = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=8
        )
        if proc.returncode == 0:
            return CheckResult(name="Docker", ok=True, detail="daemon running")
        return CheckResult(
            name    = "Docker",
            ok      = True,
            warning = True,
            detail  = "Installed but daemon not running",
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name    = "Docker",
            ok      = True,
            warning = True,
            detail  = "Timeout querying daemon",
        )
    except Exception as exc:
        return CheckResult(name="Docker", ok=True, warning=True, detail=str(exc))


async def _check_git(config: CLIConfig) -> CheckResult:
    if shutil.which("git"):
        try:
            result = subprocess.run(
                ["git", "--version"], capture_output=True, text=True, timeout=5
            )
            return CheckResult(
                name   = "Git",
                ok     = True,
                detail = result.stdout.strip(),
            )
        except Exception:
            pass
    return CheckResult(
        name    = "Git",
        ok      = True,
        warning = True,
        detail  = "Not found — some features may not work",
    )


# ── runner ────────────────────────────────────────────────────────────────────

_ALL_CHECKS: List[Callable[[CLIConfig], Awaitable[CheckResult]]] = [
    _check_python,
    _check_packages,
    _check_config_dir,
    _check_credentials,
    _check_backend,
    _check_auth_api,
    _check_token_balance,
    _check_docker,
    _check_git,
]


async def run_doctor(config: CLIConfig) -> DoctorReport:
    """Run all checks and print a formatted report. Returns the DoctorReport."""
    report = DoctorReport()

    console.print()
    console.print(Panel(
        "[bold]Running diagnostics…[/bold]\n"
        "[dim]This checks your environment, connectivity, and configuration.[/dim]",
        title="[cyan]BharatBuild Doctor[/cyan]",
        border_style="cyan",
    ))
    console.print()

    t = Table(show_header=True, header_style="bold cyan",
              border_style="dim", show_lines=False)
    t.add_column("Check",   style="white", min_width=24)
    t.add_column("",        width=3,  justify="center")
    t.add_column("Detail",  style="dim")

    for check_fn in _ALL_CHECKS:
        with console.status(f"[dim]Checking {check_fn.__name__[7:].replace('_',' ')}…[/dim]",
                            spinner="dots"):
            result = await check_fn(config)

        report.add(result)

        if result.ok and not result.warning:
            icon  = Text("✓", style="bold green")
        elif result.warning:
            icon  = Text("⚠", style="bold yellow")
        else:
            icon  = Text("✗", style="bold red")

        t.add_row(result.name, icon, result.detail)

    console.print(t)
    console.print()

    if report.all_ok:
        console.print(Panel(
            "[bold green]✓ All checks passed.[/bold green]\n"
            "[dim]Your environment is ready to use BharatBuild CLI.[/dim]",
            border_style="green",
        ))
    else:
        failures = report.failures
        items = "\n".join(f"  • [red]{r.name}[/red]: {r.detail}" for r in failures)
        console.print(Panel(
            f"[bold red]{len(failures)} check(s) failed:[/bold red]\n{items}\n\n"
            "[dim]Fix the issues above and run [cyan]bharatbuild doctor[/cyan] again.[/dim]",
            border_style="red",
        ))

    console.print()
    return report
