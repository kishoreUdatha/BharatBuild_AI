"""
BharatBuild CLI Sandbox Mode

Isolated execution environment for bash commands:
  /sandbox on         Enable sandbox mode
  /sandbox off        Disable sandbox mode
  /sandbox status     Show sandbox status
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm


class SandboxType(str, Enum):
    """Types of sandbox isolation"""
    NONE = "none"           # No sandboxing
    BASIC = "basic"         # Basic restrictions
    DOCKER = "docker"       # Docker container
    FIREJAIL = "firejail"   # Firejail (Linux)
    BUBBLEWRAP = "bwrap"    # Bubblewrap (Linux)


@dataclass
class SandboxConfig:
    """Sandbox configuration"""
    enabled: bool = False
    type: SandboxType = SandboxType.BASIC

    # Filesystem restrictions
    read_only_paths: List[str] = field(default_factory=list)
    writable_paths: List[str] = field(default_factory=list)
    hidden_paths: List[str] = field(default_factory=list)  # Paths to hide

    # Network restrictions
    allow_network: bool = True
    allowed_hosts: List[str] = field(default_factory=list)

    # Process restrictions
    max_processes: int = 100
    max_memory_mb: int = 1024
    timeout_seconds: int = 60

    # Environment
    clear_env: bool = False
    allowed_env_vars: List[str] = field(default_factory=list)
    custom_env: Dict[str, str] = field(default_factory=dict)


@dataclass
class SandboxResult:
    """Result of sandboxed execution"""
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False
    memory_exceeded: bool = False
    error: str = ""


class SandboxManager:
    """
    Manages sandboxed execution of bash commands.

    Features:
    - Basic sandboxing (environment restrictions)
    - Docker-based isolation
    - Linux sandboxing (firejail, bubblewrap)
    - Network restrictions
    - Filesystem restrictions

    Usage:
        manager = SandboxManager(console, project_dir)

        # Enable sandbox
        manager.enable()

        # Execute command
        result = manager.execute("ls -la")

        # Check result
        if result.exit_code == 0:
            print(result.stdout)
    """

    # Dangerous commands to always block
    BLOCKED_COMMANDS = [
        "rm -rf /",
        "rm -rf /*",
        ": (){:|:&};:",  # Fork bomb
        "mkfs",
        "dd if=/dev/zero",
        "chmod -R 777 /",
        "> /dev/sda",
    ]

    # Commands that require confirmation
    SENSITIVE_COMMANDS = [
        "rm -rf",
        "sudo",
        "chmod",
        "chown",
        "kill",
        "pkill",
        "killall",
        "shutdown",
        "reboot",
        "systemctl",
        "apt",
        "yum",
        "dnf",
        "brew",
        "npm install -g",
        "pip install",
    ]

    def __init__(
        self,
        console: Console,
        project_dir: Path = None,
        config_dir: Path = None
    ):
        self.console = console
        self.project_dir = project_dir or Path.cwd()
        self.config_dir = config_dir or Path.home() / ".bharatbuild"

        # Configuration
        self.config = SandboxConfig(
            writable_paths=[str(self.project_dir)],
            allowed_env_vars=["PATH", "HOME", "USER", "LANG", "TERM", "SHELL"]
        )

        # Detect available sandbox types
        self._available_types = self._detect_sandbox_types()

    def _detect_sandbox_types(self) -> List[SandboxType]:
        """Detect available sandbox types"""
        available = [SandboxType.NONE, SandboxType.BASIC]

        # Check for Docker
        if shutil.which("docker"):
            try:
                result = subprocess.run(
                    ["docker", "info"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    available.append(SandboxType.DOCKER)
            except Exception:
                pass

        # Check for firejail (Linux)
        if sys.platform == "linux" and shutil.which("firejail"):
            available.append(SandboxType.FIREJAIL)

        # Check for bubblewrap (Linux)
        if sys.platform == "linux" and shutil.which("bwrap"):
            available.append(SandboxType.BUBBLEWRAP)

        return available

    # ==================== Configuration ====================

    def enable(self, sandbox_type: SandboxType = None):
        """Enable sandbox mode"""
        if sandbox_type and sandbox_type not in self._available_types:
            self.console.print(f"[red]Sandbox type not available: {sandbox_type.value}[/red]")
            self.console.print(f"[dim]Available: {', '.join(t.value for t in self._available_types)}[/dim]")
            return

        self.config.enabled = True
        if sandbox_type:
            self.config.type = sandbox_type

        self.console.print(f"[green]✓ Sandbox enabled ({self.config.type.value})[/green]")

    def disable(self):
        """Disable sandbox mode"""
        self.config.enabled = False
        self.console.print("[green]✓ Sandbox disabled[/green]")

    def toggle(self) -> bool:
        """Toggle sandbox mode"""
        self.config.enabled = not self.config.enabled
        status = "enabled" if self.config.enabled else "disabled"
        self.console.print(f"[green]✓ Sandbox {status}[/green]")
        return self.config.enabled

    def set_type(self, sandbox_type: SandboxType):
        """Set sandbox type"""
        if sandbox_type not in self._available_types:
            self.console.print(f"[red]Sandbox type not available: {sandbox_type.value}[/red]")
            return

        self.config.type = sandbox_type
        self.console.print(f"[green]✓ Sandbox type set to: {sandbox_type.value}[/green]")

    def add_writable_path(self, path: str):
        """Add a writable path"""
        if path not in self.config.writable_paths:
            self.config.writable_paths.append(path)
            self.console.print(f"[green]✓ Added writable path: {path}[/green]")

    def add_read_only_path(self, path: str):
        """Add a read-only path"""
        if path not in self.config.read_only_paths:
            self.config.read_only_paths.append(path)
            self.console.print(f"[green]✓ Added read-only path: {path}[/green]")

    def set_network(self, allow: bool):
        """Enable/disable network access"""
        self.config.allow_network = allow
        status = "enabled" if allow else "disabled"
        self.console.print(f"[green]✓ Network access {status}[/green]")

    # ==================== Command Validation ====================

    def is_command_blocked(self, command: str) -> bool:
        """Check if command is blocked"""
        command_lower = command.lower().strip()

        for blocked in self.BLOCKED_COMMANDS:
            if blocked in command_lower:
                return True

        return False

    def is_command_sensitive(self, command: str) -> Tuple[bool, str]:
        """Check if command is sensitive and requires confirmation"""
        command_lower = command.lower().strip()

        for sensitive in self.SENSITIVE_COMMANDS:
            if sensitive in command_lower:
                return True, sensitive

        return False, ""

    def validate_command(self, command: str) -> Tuple[bool, str]:
        """Validate command before execution"""
        # Check blocked commands
        if self.is_command_blocked(command):
            return False, "Command is blocked for security reasons"

        # Check sensitive commands
        is_sensitive, sensitive_part = self.is_command_sensitive(command)
        if is_sensitive and self.config.enabled:
            return False, f"Sensitive command '{sensitive_part}' blocked in sandbox mode"

        return True, ""

    # ==================== Execution ====================

    def execute(
        self,
        command: str,
        cwd: Path = None,
        env: Dict[str, str] = None,
        timeout: int = None,
        confirm_sensitive: bool = True
    ) -> SandboxResult:
        """Execute command with sandbox restrictions"""

        # Validate command
        is_valid, error = self.validate_command(command)
        if not is_valid:
            return SandboxResult(
                stdout="",
                stderr=error,
                exit_code=1,
                error=error
            )

        # Check sensitive commands
        if confirm_sensitive:
            is_sensitive, sensitive_part = self.is_command_sensitive(command)
            if is_sensitive:
                self.console.print(f"[yellow]Warning: Sensitive command detected ({sensitive_part})[/yellow]")
                if not Confirm.ask("Execute anyway?"):
                    return SandboxResult(
                        stdout="",
                        stderr="Cancelled by user",
                        exit_code=1,
                        error="Cancelled"
                    )

        # Execute based on sandbox type
        if not self.config.enabled:
            return self._execute_direct(command, cwd, env, timeout)

        if self.config.type == SandboxType.BASIC:
            return self._execute_basic(command, cwd, env, timeout)
        elif self.config.type == SandboxType.DOCKER:
            return self._execute_docker(command, cwd, env, timeout)
        elif self.config.type == SandboxType.FIREJAIL:
            return self._execute_firejail(command, cwd, env, timeout)
        elif self.config.type == SandboxType.BUBBLEWRAP:
            return self._execute_bubblewrap(command, cwd, env, timeout)
        else:
            return self._execute_direct(command, cwd, env, timeout)

    def _execute_direct(
        self,
        command: str,
        cwd: Path = None,
        env: Dict[str, str] = None,
        timeout: int = None
    ) -> SandboxResult:
        """Execute command directly without sandbox"""
        timeout = timeout or self.config.timeout_seconds

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(cwd or self.project_dir),
                env=env or os.environ.copy(),
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return SandboxResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode
            )

        except subprocess.TimeoutExpired:
            return SandboxResult(
                stdout="",
                stderr="Command timed out",
                exit_code=124,
                timed_out=True
            )
        except Exception as e:
            return SandboxResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
                error=str(e)
            )

    def _execute_basic(
        self,
        command: str,
        cwd: Path = None,
        env: Dict[str, str] = None,
        timeout: int = None
    ) -> SandboxResult:
        """Execute with basic restrictions"""
        timeout = timeout or self.config.timeout_seconds

        # Create restricted environment
        restricted_env = {}

        if self.config.clear_env:
            # Only allowed env vars
            for var in self.config.allowed_env_vars:
                if var in os.environ:
                    restricted_env[var] = os.environ[var]
        else:
            restricted_env = os.environ.copy()

        # Add custom env
        restricted_env.update(self.config.custom_env)

        # Override with provided env
        if env:
            restricted_env.update(env)

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(cwd or self.project_dir),
                env=restricted_env,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return SandboxResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode
            )

        except subprocess.TimeoutExpired:
            return SandboxResult(
                stdout="",
                stderr="Command timed out",
                exit_code=124,
                timed_out=True
            )
        except Exception as e:
            return SandboxResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
                error=str(e)
            )

    def _execute_docker(
        self,
        command: str,
        cwd: Path = None,
        env: Dict[str, str] = None,
        timeout: int = None
    ) -> SandboxResult:
        """Execute in Docker container"""
        timeout = timeout or self.config.timeout_seconds
        work_dir = cwd or self.project_dir

        # Build docker command
        docker_cmd = ["docker", "run", "--rm"]

        # Mount project directory
        docker_cmd.extend(["-v", f"{work_dir}:/workspace"])
        docker_cmd.extend(["-w", "/workspace"])

        # Network
        if not self.config.allow_network:
            docker_cmd.append("--network=none")

        # Memory limit
        docker_cmd.extend(["--memory", f"{self.config.max_memory_mb}m"])

        # Environment variables
        if env:
            for key, value in env.items():
                docker_cmd.extend(["-e", f"{key}={value}"])

        # Use a basic image
        docker_cmd.append("alpine:latest")

        # Command
        docker_cmd.extend(["sh", "-c", command])

        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return SandboxResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode
            )

        except subprocess.TimeoutExpired:
            return SandboxResult(
                stdout="",
                stderr="Command timed out",
                exit_code=124,
                timed_out=True
            )
        except Exception as e:
            return SandboxResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
                error=str(e)
            )

    def _execute_firejail(
        self,
        command: str,
        cwd: Path = None,
        env: Dict[str, str] = None,
        timeout: int = None
    ) -> SandboxResult:
        """Execute with firejail (Linux)"""
        timeout = timeout or self.config.timeout_seconds
        work_dir = cwd or self.project_dir

        # Build firejail command
        firejail_cmd = ["firejail", "--quiet"]

        # Whitelist writable paths
        for path in self.config.writable_paths:
            firejail_cmd.extend(["--whitelist", path])

        # Read-only paths
        for path in self.config.read_only_paths:
            firejail_cmd.extend(["--read-only", path])

        # Network
        if not self.config.allow_network:
            firejail_cmd.append("--net=none")

        # Working directory
        firejail_cmd.extend(["--private-cwd", str(work_dir)])

        # Command
        firejail_cmd.extend(["bash", "-c", command])

        try:
            result = subprocess.run(
                firejail_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env or os.environ.copy()
            )

            return SandboxResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode
            )

        except subprocess.TimeoutExpired:
            return SandboxResult(
                stdout="",
                stderr="Command timed out",
                exit_code=124,
                timed_out=True
            )
        except Exception as e:
            return SandboxResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
                error=str(e)
            )

    def _execute_bubblewrap(
        self,
        command: str,
        cwd: Path = None,
        env: Dict[str, str] = None,
        timeout: int = None
    ) -> SandboxResult:
        """Execute with bubblewrap (Linux)"""
        timeout = timeout or self.config.timeout_seconds
        work_dir = cwd or self.project_dir

        # Build bwrap command
        bwrap_cmd = ["bwrap"]

        # Basic filesystem
        bwrap_cmd.extend(["--ro-bind", "/usr", "/usr"])
        bwrap_cmd.extend(["--ro-bind", "/lib", "/lib"])
        bwrap_cmd.extend(["--ro-bind", "/lib64", "/lib64"])
        bwrap_cmd.extend(["--ro-bind", "/bin", "/bin"])
        bwrap_cmd.extend(["--proc", "/proc"])
        bwrap_cmd.extend(["--dev", "/dev"])

        # Writable paths
        for path in self.config.writable_paths:
            if Path(path).exists():
                bwrap_cmd.extend(["--bind", path, path])

        # Working directory
        bwrap_cmd.extend(["--chdir", str(work_dir)])

        # Network (unshare network namespace if disabled)
        if not self.config.allow_network:
            bwrap_cmd.append("--unshare-net")

        # Command
        bwrap_cmd.extend(["bash", "-c", command])

        try:
            result = subprocess.run(
                bwrap_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env or os.environ.copy()
            )

            return SandboxResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode
            )

        except subprocess.TimeoutExpired:
            return SandboxResult(
                stdout="",
                stderr="Command timed out",
                exit_code=124,
                timed_out=True
            )
        except Exception as e:
            return SandboxResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
                error=str(e)
            )

    # ==================== Display ====================

    def show_status(self):
        """Show sandbox status"""
        content_lines = []

        status = "[green]Enabled[/green]" if self.config.enabled else "[dim]Disabled[/dim]"
        content_lines.append(f"[bold]Status:[/bold] {status}")
        content_lines.append(f"[bold]Type:[/bold] {self.config.type.value}")
        content_lines.append("")

        content_lines.append("[bold]Available Types:[/bold]")
        for stype in self._available_types:
            indicator = "[green]►[/green]" if stype == self.config.type else " "
            content_lines.append(f"  {indicator} {stype.value}")

        content_lines.append("")
        content_lines.append("[bold]Restrictions:[/bold]")
        content_lines.append(f"  Network: {'Allowed' if self.config.allow_network else 'Blocked'}")
        content_lines.append(f"  Timeout: {self.config.timeout_seconds}s")
        content_lines.append(f"  Max Memory: {self.config.max_memory_mb}MB")

        if self.config.writable_paths:
            content_lines.append("")
            content_lines.append("[bold]Writable Paths:[/bold]")
            for path in self.config.writable_paths[:5]:
                content_lines.append(f"  • {path}")

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title="[bold cyan]Sandbox Status[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

    def show_help(self):
        """Show sandbox help"""
        help_text = """
[bold cyan]Sandbox Commands[/bold cyan]

Isolated execution environment for safety.

[bold]Commands:[/bold]
  [green]/sandbox[/green]            Show sandbox status
  [green]/sandbox on[/green]         Enable sandbox
  [green]/sandbox off[/green]        Disable sandbox
  [green]/sandbox type <t>[/green]   Set sandbox type
  [green]/sandbox network on/off[/green] Toggle network

[bold]Sandbox Types:[/bold]
  • none     - No sandboxing
  • basic    - Environment restrictions
  • docker   - Docker container isolation
  • firejail - Firejail (Linux)
  • bwrap    - Bubblewrap (Linux)

[bold]Blocked Commands:[/bold]
  • rm -rf /
  • Fork bombs
  • Disk formatting
  • Other dangerous operations

[bold]Sensitive Commands:[/bold]
  Commands like sudo, rm -rf, chmod require
  confirmation or are blocked in sandbox mode.

[bold]Examples:[/bold]
  /sandbox on
  /sandbox type docker
  /sandbox network off
"""
        self.console.print(help_text)
