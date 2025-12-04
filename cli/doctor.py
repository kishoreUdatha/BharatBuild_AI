"""
BharatBuild CLI Doctor Command

Diagnose and fix common issues:
  /doctor           Run all checks
  /doctor fix       Attempt to fix issues
  /doctor --verbose Show detailed output
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn


class CheckStatus(str, Enum):
    """Status of a diagnostic check"""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class CheckResult:
    """Result of a diagnostic check"""
    name: str
    status: CheckStatus
    message: str
    details: str = ""
    fix_available: bool = False
    fix_command: str = ""


class DoctorCommand:
    """
    Diagnostic tool for BharatBuild CLI.

    Checks:
    - Python version
    - Required packages
    - API key configuration
    - Git installation
    - Network connectivity
    - Disk space
    - Configuration files
    - Permissions

    Usage:
        doctor = DoctorCommand(console, config_dir)

        # Run all checks
        doctor.run_checks()

        # Run specific check
        result = doctor.check_python()

        # Fix issues
        doctor.fix_issues()
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
        self._results: List[CheckResult] = []

    def run_checks(self, verbose: bool = False) -> List[CheckResult]:
        """Run all diagnostic checks"""
        self._results = []

        checks = [
            ("Python Version", self.check_python),
            ("Required Packages", self.check_packages),
            ("API Key", self.check_api_key),
            ("Git Installation", self.check_git),
            ("Node.js (optional)", self.check_node),
            ("Network Connectivity", self.check_network),
            ("Disk Space", self.check_disk_space),
            ("Configuration", self.check_config),
            ("Permissions", self.check_permissions),
            ("Project Structure", self.check_project),
        ]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task("Running diagnostics...", total=len(checks))

            for name, check_func in checks:
                progress.update(task, description=f"Checking {name}...")
                try:
                    result = check_func()
                    self._results.append(result)
                except Exception as e:
                    self._results.append(CheckResult(
                        name=name,
                        status=CheckStatus.FAIL,
                        message=f"Check failed with error",
                        details=str(e)
                    ))
                progress.advance(task)

        self._display_results(verbose)
        return self._results

    def _display_results(self, verbose: bool = False):
        """Display check results"""
        # Summary counts
        passed = sum(1 for r in self._results if r.status == CheckStatus.PASS)
        warnings = sum(1 for r in self._results if r.status == CheckStatus.WARN)
        failed = sum(1 for r in self._results if r.status == CheckStatus.FAIL)

        # Results table
        table = Table(show_header=True, header_style="bold cyan", title="Diagnostic Results")
        table.add_column("Check", style="bold")
        table.add_column("Status", width=8)
        table.add_column("Message")

        for result in self._results:
            if result.status == CheckStatus.PASS:
                status = "[green]✓ Pass[/green]"
            elif result.status == CheckStatus.WARN:
                status = "[yellow]⚠ Warn[/yellow]"
            elif result.status == CheckStatus.FAIL:
                status = "[red]✗ Fail[/red]"
            else:
                status = "[dim]○ Skip[/dim]"

            message = result.message
            if verbose and result.details:
                message += f"\n[dim]{result.details}[/dim]"

            table.add_row(result.name, status, message)

        self.console.print(table)

        # Summary
        summary_parts = []
        if passed > 0:
            summary_parts.append(f"[green]{passed} passed[/green]")
        if warnings > 0:
            summary_parts.append(f"[yellow]{warnings} warnings[/yellow]")
        if failed > 0:
            summary_parts.append(f"[red]{failed} failed[/red]")

        self.console.print(f"\n{' · '.join(summary_parts)}")

        # Suggestions
        if failed > 0:
            self.console.print("\n[yellow]Run '/doctor fix' to attempt automatic fixes[/yellow]")

    # ==================== Individual Checks ====================

    def check_python(self) -> CheckResult:
        """Check Python version"""
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"

        if version.major < 3 or (version.major == 3 and version.minor < 8):
            return CheckResult(
                name="Python Version",
                status=CheckStatus.FAIL,
                message=f"Python {version_str} - requires 3.8+",
                details="Please upgrade Python to version 3.8 or higher",
                fix_available=False
            )

        if version.minor < 10:
            return CheckResult(
                name="Python Version",
                status=CheckStatus.WARN,
                message=f"Python {version_str} - 3.10+ recommended",
                details="Some features work better with Python 3.10+"
            )

        return CheckResult(
            name="Python Version",
            status=CheckStatus.PASS,
            message=f"Python {version_str}"
        )

    def check_packages(self) -> CheckResult:
        """Check required packages"""
        required = [
            "rich",
            "prompt_toolkit",
            "httpx",
            "pydantic",
        ]

        optional = [
            "anthropic",
            "pygments",
            "watchdog",
        ]

        missing_required = []
        missing_optional = []

        for pkg in required:
            try:
                __import__(pkg)
            except ImportError:
                missing_required.append(pkg)

        for pkg in optional:
            try:
                __import__(pkg)
            except ImportError:
                missing_optional.append(pkg)

        if missing_required:
            return CheckResult(
                name="Required Packages",
                status=CheckStatus.FAIL,
                message=f"Missing: {', '.join(missing_required)}",
                details=f"pip install {' '.join(missing_required)}",
                fix_available=True,
                fix_command=f"pip install {' '.join(missing_required)}"
            )

        if missing_optional:
            return CheckResult(
                name="Required Packages",
                status=CheckStatus.WARN,
                message=f"Optional missing: {', '.join(missing_optional)}",
                details="Some features may not work without these packages"
            )

        return CheckResult(
            name="Required Packages",
            status=CheckStatus.PASS,
            message="All packages installed"
        )

    def check_api_key(self) -> CheckResult:
        """Check API key configuration"""
        # Check environment variable
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

        if not api_key:
            # Check config file
            config_file = self.config_dir / "config.json"
            if config_file.exists():
                try:
                    import json
                    with open(config_file) as f:
                        config = json.load(f)
                    api_key = config.get("api_key", "")
                except Exception:
                    pass

        if not api_key:
            return CheckResult(
                name="API Key",
                status=CheckStatus.FAIL,
                message="No API key configured",
                details="Set ANTHROPIC_API_KEY environment variable or run /config api-key",
                fix_available=False
            )

        # Validate format (basic check)
        if not api_key.startswith("sk-"):
            return CheckResult(
                name="API Key",
                status=CheckStatus.WARN,
                message="API key format may be incorrect",
                details="Anthropic API keys typically start with 'sk-'"
            )

        # Mask key for display
        masked = api_key[:7] + "..." + api_key[-4:]

        return CheckResult(
            name="API Key",
            status=CheckStatus.PASS,
            message=f"Configured ({masked})"
        )

    def check_git(self) -> CheckResult:
        """Check Git installation"""
        git_path = shutil.which("git")

        if not git_path:
            return CheckResult(
                name="Git Installation",
                status=CheckStatus.WARN,
                message="Git not found",
                details="Some features require Git. Install from https://git-scm.com"
            )

        # Get version
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            version = result.stdout.strip()

            return CheckResult(
                name="Git Installation",
                status=CheckStatus.PASS,
                message=version
            )
        except Exception as e:
            return CheckResult(
                name="Git Installation",
                status=CheckStatus.WARN,
                message="Git found but error getting version",
                details=str(e)
            )

    def check_node(self) -> CheckResult:
        """Check Node.js installation (optional)"""
        node_path = shutil.which("node")

        if not node_path:
            return CheckResult(
                name="Node.js (optional)",
                status=CheckStatus.SKIP,
                message="Not installed",
                details="Only needed for JavaScript/TypeScript projects"
            )

        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            version = result.stdout.strip()

            return CheckResult(
                name="Node.js (optional)",
                status=CheckStatus.PASS,
                message=f"Node.js {version}"
            )
        except Exception:
            return CheckResult(
                name="Node.js (optional)",
                status=CheckStatus.SKIP,
                message="Not available"
            )

    def check_network(self) -> CheckResult:
        """Check network connectivity"""
        import socket

        hosts = [
            ("api.anthropic.com", 443),
            ("github.com", 443),
        ]

        for host, port in hosts:
            try:
                socket.create_connection((host, port), timeout=5)
            except (socket.timeout, socket.error) as e:
                return CheckResult(
                    name="Network Connectivity",
                    status=CheckStatus.FAIL,
                    message=f"Cannot reach {host}",
                    details=str(e)
                )

        return CheckResult(
            name="Network Connectivity",
            status=CheckStatus.PASS,
            message="Connected"
        )

    def check_disk_space(self) -> CheckResult:
        """Check available disk space"""
        try:
            if platform.system() == "Windows":
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(str(self.project_dir)),
                    None, None, ctypes.pointer(free_bytes)
                )
                free_gb = free_bytes.value / (1024 ** 3)
            else:
                stat = os.statvfs(self.project_dir)
                free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)

            if free_gb < 1:
                return CheckResult(
                    name="Disk Space",
                    status=CheckStatus.FAIL,
                    message=f"Low disk space: {free_gb:.1f} GB",
                    details="At least 1 GB recommended"
                )

            if free_gb < 5:
                return CheckResult(
                    name="Disk Space",
                    status=CheckStatus.WARN,
                    message=f"Available: {free_gb:.1f} GB",
                    details="Consider freeing up space"
                )

            return CheckResult(
                name="Disk Space",
                status=CheckStatus.PASS,
                message=f"Available: {free_gb:.1f} GB"
            )

        except Exception as e:
            return CheckResult(
                name="Disk Space",
                status=CheckStatus.SKIP,
                message="Could not check",
                details=str(e)
            )

    def check_config(self) -> CheckResult:
        """Check configuration files"""
        issues = []

        # Check config directory
        if not self.config_dir.exists():
            issues.append("Config directory not found")

        # Check for config file
        config_file = self.config_dir / "config.json"
        if not config_file.exists():
            issues.append("No config.json file")

        if issues:
            return CheckResult(
                name="Configuration",
                status=CheckStatus.WARN,
                message="; ".join(issues),
                details=f"Config dir: {self.config_dir}",
                fix_available=True,
                fix_command="init"
            )

        return CheckResult(
            name="Configuration",
            status=CheckStatus.PASS,
            message=f"Config found at {self.config_dir}"
        )

    def check_permissions(self) -> CheckResult:
        """Check file permissions"""
        issues = []

        # Check config dir writable
        if self.config_dir.exists():
            if not os.access(self.config_dir, os.W_OK):
                issues.append("Config directory not writable")

        # Check project dir writable
        if not os.access(self.project_dir, os.W_OK):
            issues.append("Project directory not writable")

        if issues:
            return CheckResult(
                name="Permissions",
                status=CheckStatus.FAIL,
                message="; ".join(issues),
                details="Check directory permissions"
            )

        return CheckResult(
            name="Permissions",
            status=CheckStatus.PASS,
            message="Read/write access OK"
        )

    def check_project(self) -> CheckResult:
        """Check project structure"""
        # Look for common project indicators
        indicators = {
            "package.json": "Node.js",
            "requirements.txt": "Python",
            "pyproject.toml": "Python",
            "Cargo.toml": "Rust",
            "go.mod": "Go",
            "pom.xml": "Java/Maven",
            "build.gradle": "Java/Gradle",
        }

        found = []
        for file, lang in indicators.items():
            if (self.project_dir / file).exists():
                found.append(lang)

        # Check for BHARATBUILD.md
        has_instructions = (self.project_dir / "BHARATBUILD.md").exists()

        if not found:
            return CheckResult(
                name="Project Structure",
                status=CheckStatus.WARN,
                message="No recognized project type",
                details="Run '/init' to set up project"
            )

        message = f"Detected: {', '.join(set(found))}"
        if has_instructions:
            message += " + BHARATBUILD.md"

        return CheckResult(
            name="Project Structure",
            status=CheckStatus.PASS,
            message=message
        )

    # ==================== Fix Issues ====================

    def fix_issues(self) -> int:
        """Attempt to fix issues"""
        if not self._results:
            self.run_checks(verbose=False)

        fixed = 0
        failed_fixes = []

        for result in self._results:
            if result.status == CheckStatus.FAIL and result.fix_available:
                self.console.print(f"\n[cyan]Fixing: {result.name}[/cyan]")

                try:
                    if result.fix_command.startswith("pip install"):
                        # Run pip install
                        subprocess.run(
                            result.fix_command.split(),
                            check=True,
                            capture_output=True
                        )
                        self.console.print(f"[green]✓ Fixed: {result.name}[/green]")
                        fixed += 1

                    elif result.fix_command == "init":
                        # Create config directory
                        self.config_dir.mkdir(parents=True, exist_ok=True)
                        self.console.print(f"[green]✓ Created config directory[/green]")
                        fixed += 1

                except Exception as e:
                    failed_fixes.append((result.name, str(e)))
                    self.console.print(f"[red]✗ Failed to fix: {result.name}[/red]")

        if fixed > 0:
            self.console.print(f"\n[green]Fixed {fixed} issue(s)[/green]")

        if failed_fixes:
            self.console.print(f"\n[red]Failed to fix {len(failed_fixes)} issue(s):[/red]")
            for name, error in failed_fixes:
                self.console.print(f"  - {name}: {error}")

        return fixed

    def show_system_info(self):
        """Display system information"""
        info = {
            "Platform": platform.platform(),
            "Python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "Python Path": sys.executable,
            "Working Dir": str(self.project_dir),
            "Config Dir": str(self.config_dir),
            "OS": platform.system(),
            "Architecture": platform.machine(),
        }

        table = Table(title="System Information", show_header=False)
        table.add_column("Property", style="bold")
        table.add_column("Value")

        for key, value in info.items():
            table.add_row(key, value)

        self.console.print(table)
