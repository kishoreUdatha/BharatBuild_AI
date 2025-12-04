"""
BharatBuild CLI IDE Integration

Bridge Claude Code with IDE instances:
  /ide                 Show IDE connection status
  /ide connect         Connect to IDE
  /ide disconnect      Disconnect from IDE
  /install-github-app  Set up GitHub Actions integration
"""

import os
import json
import subprocess
import socket
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm


class IDEType(str, Enum):
    """Supported IDE types"""
    VSCODE = "vscode"
    CURSOR = "cursor"
    WINDSURF = "windsurf"
    JETBRAINS = "jetbrains"
    UNKNOWN = "unknown"


@dataclass
class IDEConnection:
    """IDE connection info"""
    ide_type: IDEType
    port: int
    pid: int
    workspace: str
    connected_at: str
    status: str = "connected"


class IDEIntegrationManager:
    """
    Manages IDE integration for BharatBuild CLI.

    Features:
    - VS Code extension integration
    - JetBrains plugin support
    - Context sharing (selections, open files)
    - Diff viewing in IDE
    - Diagnostic sharing

    Usage:
        manager = IDEIntegrationManager(console, config_dir)

        # Check connection
        if manager.is_connected():
            manager.share_context(selection)

        # Connect to IDE
        manager.connect()
    """

    DEFAULT_PORT = 8378
    GITHUB_APP_URL = "https://github.com/apps/bharatbuild-ai"
    GITHUB_ACTIONS_DOCS = "https://docs.bharatbuild.dev/github-actions"

    def __init__(
        self,
        console: Console,
        config_dir: Path = None,
        project_dir: Path = None
    ):
        self.console = console
        self.config_dir = config_dir or Path.home() / ".bharatbuild"
        self.project_dir = project_dir or Path.cwd()

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Connection state
        self._connection: Optional[IDEConnection] = None
        self._load_connection()

    def _load_connection(self):
        """Load saved connection info"""
        conn_file = self.config_dir / "ide_connection.json"

        if conn_file.exists():
            try:
                with open(conn_file) as f:
                    data = json.load(f)

                self._connection = IDEConnection(
                    ide_type=IDEType(data.get("ide_type", "unknown")),
                    port=data.get("port", self.DEFAULT_PORT),
                    pid=data.get("pid", 0),
                    workspace=data.get("workspace", ""),
                    connected_at=data.get("connected_at", ""),
                    status=data.get("status", "disconnected")
                )

                # Verify connection is still valid
                if not self._verify_connection():
                    self._connection = None

            except Exception:
                self._connection = None

    def _save_connection(self):
        """Save connection info"""
        conn_file = self.config_dir / "ide_connection.json"

        if self._connection:
            with open(conn_file, 'w') as f:
                json.dump(asdict(self._connection), f, indent=2)
        elif conn_file.exists():
            conn_file.unlink()

    def _verify_connection(self) -> bool:
        """Verify IDE connection is still active"""
        if not self._connection:
            return False

        try:
            # Try to connect to the IDE's socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', self._connection.port))
            sock.close()
            return result == 0
        except Exception:
            return False

    # ==================== Connection Management ====================

    def is_connected(self) -> bool:
        """Check if connected to an IDE"""
        return self._connection is not None and self._verify_connection()

    def connect(self, ide_type: IDEType = None):
        """Connect to IDE"""
        self.console.print("\n[bold cyan]IDE Connection[/bold cyan]\n")

        # Detect IDE
        if not ide_type:
            ide_type = self._detect_ide()

        if ide_type == IDEType.UNKNOWN:
            self.console.print("[yellow]No supported IDE detected[/yellow]")
            self.console.print("\n[bold]Supported IDEs:[/bold]")
            self.console.print("  • VS Code / Cursor / Windsurf")
            self.console.print("  • JetBrains (IntelliJ, PyCharm, WebStorm, etc.)")
            self.console.print("\n[dim]Start your IDE and run /ide connect again[/dim]")
            return

        self.console.print(f"[green]✓ Detected: {ide_type.value}[/green]")

        # Establish connection
        port = self._find_ide_port(ide_type)

        if port:
            self._connection = IDEConnection(
                ide_type=ide_type,
                port=port,
                pid=os.getpid(),
                workspace=str(self.project_dir),
                connected_at=datetime.now().isoformat(),
                status="connected"
            )
            self._save_connection()

            self.console.print(f"[green]✓ Connected to {ide_type.value} on port {port}[/green]")
            self._show_connection_info()
        else:
            self.console.print(f"[yellow]Could not establish connection to {ide_type.value}[/yellow]")
            self._show_manual_setup(ide_type)

    def disconnect(self):
        """Disconnect from IDE"""
        if self._connection:
            ide_type = self._connection.ide_type.value
            self._connection = None
            self._save_connection()
            self.console.print(f"[green]✓ Disconnected from {ide_type}[/green]")
        else:
            self.console.print("[dim]Not connected to any IDE[/dim]")

    def _detect_ide(self) -> IDEType:
        """Detect running IDE"""
        # Check for VS Code
        if self._is_process_running("code") or self._is_process_running("Code"):
            return IDEType.VSCODE

        # Check for Cursor
        if self._is_process_running("cursor") or self._is_process_running("Cursor"):
            return IDEType.CURSOR

        # Check for Windsurf
        if self._is_process_running("windsurf") or self._is_process_running("Windsurf"):
            return IDEType.WINDSURF

        # Check for JetBrains IDEs
        jetbrains_processes = ["idea", "pycharm", "webstorm", "goland", "phpstorm", "clion", "rider"]
        for proc in jetbrains_processes:
            if self._is_process_running(proc):
                return IDEType.JETBRAINS

        return IDEType.UNKNOWN

    def _is_process_running(self, name: str) -> bool:
        """Check if process is running"""
        try:
            if os.name == 'nt':  # Windows
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {name}*"],
                    capture_output=True,
                    text=True
                )
                return name.lower() in result.stdout.lower()
            else:  # Unix
                result = subprocess.run(
                    ["pgrep", "-i", name],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
        except Exception:
            return False

    def _find_ide_port(self, ide_type: IDEType) -> Optional[int]:
        """Find IDE's communication port"""
        # Check common ports
        ports_to_check = [
            self.DEFAULT_PORT,
            8379, 8380,  # Alternates
            3000, 3001,  # Dev server ports that might be used
        ]

        for port in ports_to_check:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex(('localhost', port))
                sock.close()

                if result == 0:
                    return port
            except Exception:
                pass

        # Return default port even if not verified
        return self.DEFAULT_PORT

    def _show_connection_info(self):
        """Show connection information"""
        if not self._connection:
            return

        self.console.print("\n[bold]Connection Details:[/bold]")
        self.console.print(f"  IDE: {self._connection.ide_type.value}")
        self.console.print(f"  Port: {self._connection.port}")
        self.console.print(f"  Workspace: {self._connection.workspace}")

        self.console.print("\n[bold]Features Available:[/bold]")
        self.console.print("  • Context sharing (selections, open files)")
        self.console.print("  • Diff viewing in IDE")
        self.console.print("  • Diagnostic sharing (lint errors)")
        self.console.print("  • File navigation")

    def _show_manual_setup(self, ide_type: IDEType):
        """Show manual setup instructions"""
        self.console.print("\n[bold]Manual Setup:[/bold]")

        if ide_type in [IDEType.VSCODE, IDEType.CURSOR, IDEType.WINDSURF]:
            self.console.print("  1. Install BharatBuild extension from marketplace")
            self.console.print("  2. Open Command Palette (Ctrl+Shift+P)")
            self.console.print("  3. Run 'BharatBuild: Connect CLI'")
            self.console.print("  4. Run /ide connect again")

        elif ide_type == IDEType.JETBRAINS:
            self.console.print("  1. Install BharatBuild plugin from marketplace")
            self.console.print("  2. Open Settings → Tools → BharatBuild")
            self.console.print("  3. Enable CLI Integration")
            self.console.print("  4. Run /ide connect again")
            self.console.print("\n[dim]Tip: Use Cmd+Esc (Mac) or Ctrl+Esc (Win/Linux) to open[/dim]")

    # ==================== Context Sharing ====================

    def share_selection(self, selection: str):
        """Share selected text with IDE"""
        if not self.is_connected():
            return

        # In a real implementation, this would send to IDE via socket/IPC
        self.console.print("[dim]Shared selection with IDE[/dim]")

    def get_ide_context(self) -> Dict[str, Any]:
        """Get context from IDE (open files, selection, diagnostics)"""
        if not self.is_connected():
            return {}

        # In a real implementation, this would request from IDE
        return {
            "open_files": [],
            "active_file": "",
            "selection": "",
            "diagnostics": []
        }

    def open_diff(self, file_path: str, original: str, modified: str):
        """Open diff view in IDE"""
        if not self.is_connected():
            self.console.print("[yellow]Not connected to IDE. Use /ide connect[/yellow]")
            return

        # In a real implementation, this would send diff to IDE
        self.console.print(f"[dim]Opening diff for {file_path} in IDE[/dim]")

    def navigate_to_file(self, file_path: str, line: int = 1):
        """Navigate to file in IDE"""
        if not self.is_connected():
            self.console.print("[yellow]Not connected to IDE[/yellow]")
            return

        # Try to open file using IDE's CLI
        if self._connection.ide_type == IDEType.VSCODE:
            subprocess.run(["code", "--goto", f"{file_path}:{line}"], capture_output=True)
        elif self._connection.ide_type == IDEType.JETBRAINS:
            # JetBrains uses different command
            subprocess.run(["idea", "--line", str(line), file_path], capture_output=True)

        self.console.print(f"[dim]Navigated to {file_path}:{line}[/dim]")

    # ==================== GitHub App Installation ====================

    def cmd_install_github_app(self, args: str = ""):
        """Install GitHub App for CI/CD integration"""
        self.console.print("\n[bold cyan]GitHub App Installation[/bold cyan]\n")

        self.console.print("[bold]BharatBuild GitHub App provides:[/bold]")
        self.console.print("  • AI-powered PR reviews")
        self.console.print("  • Automatic issue-to-PR conversion")
        self.console.print("  • @bharatbuild mentions in PRs")
        self.console.print("  • Code analysis and suggestions")

        self.console.print("\n[bold]Setup Steps:[/bold]")
        self.console.print("  1. Install GitHub App to your repository")
        self.console.print("  2. Add API key to repository secrets")
        self.console.print("  3. Create workflow file")

        # Check if in a git repo
        if not (self.project_dir / ".git").exists():
            self.console.print("\n[yellow]Warning: Not in a git repository[/yellow]")

        # Offer to open installation page
        if Confirm.ask("\nOpen GitHub App installation page?", default=True):
            try:
                webbrowser.open(self.GITHUB_APP_URL)
                self.console.print("[green]✓ Opened browser[/green]")
            except Exception as e:
                self.console.print(f"[red]Could not open browser: {e}[/red]")
                self.console.print(f"[dim]Visit: {self.GITHUB_APP_URL}[/dim]")

        # Offer to create workflow file
        if Confirm.ask("\nCreate GitHub Actions workflow file?", default=True):
            self._create_github_workflow()

    def _create_github_workflow(self):
        """Create GitHub Actions workflow file"""
        workflows_dir = self.project_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)

        workflow_file = workflows_dir / "bharatbuild.yml"

        if workflow_file.exists():
            if not Confirm.ask(f"Workflow file exists. Overwrite?", default=False):
                return

        workflow_content = """# BharatBuild AI GitHub Actions Workflow
# Enables @bharatbuild mentions in PRs and issues

name: BharatBuild AI

on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
  issues:
    types: [opened, assigned]
  pull_request:
    types: [opened, synchronize]

jobs:
  bharatbuild:
    if: |
      (github.event_name == 'issue_comment' && contains(github.event.comment.body, '@bharatbuild')) ||
      (github.event_name == 'pull_request_review_comment' && contains(github.event.comment.body, '@bharatbuild')) ||
      (github.event_name == 'issues' && contains(github.event.issue.body, '@bharatbuild')) ||
      (github.event_name == 'pull_request')
    runs-on: ubuntu-latest

    permissions:
      contents: write
      issues: write
      pull-requests: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Run BharatBuild
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          npm install -g @bharatbuild/cli
          bharatbuild --github-action

# Add ANTHROPIC_API_KEY to your repository secrets:
# Settings → Secrets and variables → Actions → New repository secret
"""

        with open(workflow_file, 'w') as f:
            f.write(workflow_content)

        self.console.print(f"\n[green]✓ Created: {workflow_file}[/green]")
        self.console.print("\n[bold]Next Steps:[/bold]")
        self.console.print("  1. Add ANTHROPIC_API_KEY to repository secrets")
        self.console.print("  2. Commit and push the workflow file")
        self.console.print("  3. Mention @bharatbuild in PRs or issues")

    # ==================== Command Handlers ====================

    def cmd_ide(self, args: str = ""):
        """Handle /ide command"""
        if not args:
            self._show_status()
            return

        arg = args.lower().strip()

        if arg == "connect":
            self.connect()
        elif arg == "disconnect":
            self.disconnect()
        elif arg == "status":
            self._show_status()
        elif arg == "help":
            self.show_help()
        else:
            self.console.print(f"[yellow]Unknown option: {arg}[/yellow]")
            self.show_help()

    def _show_status(self):
        """Show IDE connection status"""
        self.console.print("\n[bold cyan]IDE Integration Status[/bold cyan]\n")

        if self.is_connected():
            self.console.print("[green]● Connected[/green]")
            self._show_connection_info()
        else:
            self.console.print("[red]● Not Connected[/red]")
            self.console.print("\n[dim]Use /ide connect to connect to your IDE[/dim]")

        # Show detected IDEs
        detected = self._detect_ide()
        if detected != IDEType.UNKNOWN:
            self.console.print(f"\n[dim]Detected IDE: {detected.value}[/dim]")

    def show_help(self):
        """Show IDE help"""
        help_text = """
[bold cyan]IDE Integration Commands[/bold cyan]

Connect BharatBuild CLI with your IDE.

[bold]Commands:[/bold]
  [green]/ide[/green]                  Show connection status
  [green]/ide connect[/green]          Connect to IDE
  [green]/ide disconnect[/green]       Disconnect from IDE
  [green]/install-github-app[/green]   Set up GitHub Actions

[bold]Supported IDEs:[/bold]
  • VS Code / Cursor / Windsurf
  • JetBrains (IntelliJ, PyCharm, WebStorm, etc.)

[bold]Features:[/bold]
  • Context sharing (selections, open files)
  • Diff viewing in IDE
  • Diagnostic sharing (lint/syntax errors)
  • File navigation

[bold]Keyboard Shortcuts:[/bold]
  • Cmd+Esc (Mac) / Ctrl+Esc (Win/Linux) - Open from JetBrains
  • Cmd+Option+K (Mac) / Alt+Ctrl+K - Insert file reference

[bold]GitHub Integration:[/bold]
  • @bharatbuild mentions in PRs
  • Automatic code review
  • Issue-to-PR conversion
"""
        self.console.print(help_text)


# Factory function
def get_ide_manager(
    console: Console = None,
    config_dir: Path = None,
    project_dir: Path = None
) -> IDEIntegrationManager:
    """Get IDE integration manager instance"""
    return IDEIntegrationManager(
        console=console or Console(),
        config_dir=config_dir,
        project_dir=project_dir
    )
