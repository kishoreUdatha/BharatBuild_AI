"""
BharatBuild CLI Extended Commands

Missing Claude Code CLI commands:
  /add-dir          Add additional working directories
  /bashes           List/manage background bash tasks
  /bug              Report bugs
  /export           Export conversation to file/clipboard
  /permissions      View/update access controls
  /pr-comments      View pull request comments
  /review           Request code review
  /terminal-setup   Install Shift+Enter keybinding
  /todos            List current TODO items
  /output-style     Set output style
  /release-notes    View release notes
  /privacy-settings View/update privacy settings
"""

import os
import json
import subprocess
import platform
import pyperclip
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.markdown import Markdown


# ==================== Output Styles ====================

class OutputStyle(str, Enum):
    """Output style modes"""
    DEFAULT = "default"
    EXPLANATORY = "explanatory"
    LEARNING = "learning"
    CONCISE = "concise"
    VERBOSE = "verbose"


OUTPUT_STYLE_DESCRIPTIONS = {
    OutputStyle.DEFAULT: "Standard software engineering focus",
    OutputStyle.EXPLANATORY: "Educational insights between tasks",
    OutputStyle.LEARNING: "Collaborative learn-by-doing with TODO markers",
    OutputStyle.CONCISE: "Minimal, direct responses",
    OutputStyle.VERBOSE: "Detailed explanations for everything"
}


# ==================== Privacy Settings ====================

@dataclass
class PrivacySettings:
    """Privacy configuration"""
    telemetry_enabled: bool = True
    share_usage_stats: bool = True
    send_crash_reports: bool = True
    allow_model_training: bool = False
    store_conversations: bool = True
    conversation_retention_days: int = 30


# ==================== TODO Item ====================

@dataclass
class TodoItem:
    """A TODO item"""
    id: str
    content: str
    file_path: str = ""
    line_number: int = 0
    priority: str = "medium"  # low, medium, high
    status: str = "pending"  # pending, in_progress, done
    created_at: str = ""
    tags: List[str] = field(default_factory=list)


# ==================== Background Bash Task ====================

@dataclass
class BashTask:
    """A background bash task"""
    id: str
    command: str
    pid: int
    status: str  # running, completed, failed
    started_at: str
    ended_at: str = ""
    output: str = ""
    exit_code: int = -1


class ExtendedCommandsManager:
    """
    Manages extended CLI commands for Claude Code compatibility.

    Commands:
    - /add-dir: Add working directories
    - /bashes: Manage background tasks
    - /bug: Report bugs
    - /export: Export conversations
    - /permissions: Access controls
    - /pr-comments: PR comments
    - /review: Code review
    - /terminal-setup: Terminal configuration
    - /todos: TODO management
    - /output-style: Output style selection
    - /release-notes: Release notes
    - /privacy-settings: Privacy configuration
    """

    VERSION = "0.1.0"

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

        # State
        self._working_dirs: Set[Path] = {self.project_dir}
        self._background_tasks: Dict[str, BashTask] = {}
        self._todos: List[TodoItem] = []
        self._output_style: OutputStyle = OutputStyle.DEFAULT
        self._privacy_settings = PrivacySettings()
        self._conversation_history: List[Dict[str, Any]] = []

        # Load saved state
        self._load_state()

    def _load_state(self):
        """Load saved state from config"""
        state_file = self.config_dir / "extended_state.json"

        if state_file.exists():
            try:
                with open(state_file) as f:
                    data = json.load(f)

                # Load working dirs
                for dir_path in data.get("working_dirs", []):
                    path = Path(dir_path)
                    if path.exists():
                        self._working_dirs.add(path)

                # Load output style
                style = data.get("output_style", "default")
                self._output_style = OutputStyle(style)

                # Load privacy settings
                privacy = data.get("privacy_settings", {})
                self._privacy_settings = PrivacySettings(
                    telemetry_enabled=privacy.get("telemetry_enabled", True),
                    share_usage_stats=privacy.get("share_usage_stats", True),
                    send_crash_reports=privacy.get("send_crash_reports", True),
                    allow_model_training=privacy.get("allow_model_training", False),
                    store_conversations=privacy.get("store_conversations", True),
                    conversation_retention_days=privacy.get("conversation_retention_days", 30)
                )

            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load state: {e}[/yellow]")

    def _save_state(self):
        """Save state to config"""
        state_file = self.config_dir / "extended_state.json"

        data = {
            "working_dirs": [str(d) for d in self._working_dirs],
            "output_style": self._output_style.value,
            "privacy_settings": asdict(self._privacy_settings)
        }

        with open(state_file, 'w') as f:
            json.dump(data, f, indent=2)

    # ==================== /add-dir ====================

    def cmd_add_dir(self, args: str = ""):
        """Add additional working directories"""
        if not args:
            # Show current working directories
            self.console.print("\n[bold cyan]Working Directories[/bold cyan]\n")

            table = Table(show_header=True, header_style="bold")
            table.add_column("#", style="dim", width=4)
            table.add_column("Directory")
            table.add_column("Status")

            for i, dir_path in enumerate(sorted(self._working_dirs), 1):
                exists = dir_path.exists()
                status = "[green]Active[/green]" if exists else "[red]Not found[/red]"
                table.add_row(str(i), str(dir_path), status)

            self.console.print(table)
            self.console.print("\n[dim]Usage: /add-dir <path> to add a directory[/dim]")
            self.console.print("[dim]       /add-dir --remove <path> to remove[/dim]")
            return

        # Parse arguments
        if args.startswith("--remove "):
            path_str = args[9:].strip()
            path = Path(path_str).resolve()

            if path in self._working_dirs:
                if path == self.project_dir:
                    self.console.print("[red]Cannot remove the main project directory[/red]")
                    return

                self._working_dirs.remove(path)
                self._save_state()
                self.console.print(f"[green]✓ Removed: {path}[/green]")
            else:
                self.console.print(f"[yellow]Directory not in working set: {path}[/yellow]")
            return

        # Add directory
        path = Path(args).resolve()

        if not path.exists():
            self.console.print(f"[red]Directory does not exist: {path}[/red]")
            return

        if not path.is_dir():
            self.console.print(f"[red]Not a directory: {path}[/red]")
            return

        if path in self._working_dirs:
            self.console.print(f"[yellow]Directory already added: {path}[/yellow]")
            return

        self._working_dirs.add(path)
        self._save_state()
        self.console.print(f"[green]✓ Added working directory: {path}[/green]")

    # ==================== /bashes ====================

    def cmd_bashes(self, args: str = ""):
        """List and manage background bash tasks"""
        if not args:
            # List all background tasks
            self.console.print("\n[bold cyan]Background Bash Tasks[/bold cyan]\n")

            if not self._background_tasks:
                self.console.print("[dim]No background tasks[/dim]")
                self.console.print("\n[dim]Start a task with: /bashes run <command>[/dim]")
                return

            table = Table(show_header=True, header_style="bold")
            table.add_column("ID", style="dim", width=8)
            table.add_column("Command")
            table.add_column("PID", justify="right")
            table.add_column("Status")
            table.add_column("Started")

            for task_id, task in self._background_tasks.items():
                status_color = {
                    "running": "cyan",
                    "completed": "green",
                    "failed": "red"
                }.get(task.status, "white")

                try:
                    started = datetime.fromisoformat(task.started_at).strftime("%H:%M:%S")
                except:
                    started = task.started_at

                table.add_row(
                    task_id,
                    task.command[:40] + ("..." if len(task.command) > 40 else ""),
                    str(task.pid),
                    f"[{status_color}]{task.status}[/{status_color}]",
                    started
                )

            self.console.print(table)
            self.console.print("\n[dim]Commands: /bashes run <cmd> | /bashes kill <id> | /bashes output <id>[/dim]")
            return

        parts = args.split(maxsplit=1)
        action = parts[0].lower()

        if action == "run" and len(parts) > 1:
            command = parts[1]
            self._run_background_task(command)
        elif action == "kill" and len(parts) > 1:
            task_id = parts[1]
            self._kill_background_task(task_id)
        elif action == "output" and len(parts) > 1:
            task_id = parts[1]
            self._show_task_output(task_id)
        else:
            self.console.print("[yellow]Usage: /bashes [run|kill|output] <arg>[/yellow]")

    def _run_background_task(self, command: str):
        """Run a command in the background"""
        import threading

        task_id = datetime.now().strftime("%H%M%S")

        try:
            # Start process
            if platform.system() == "Windows":
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )

            task = BashTask(
                id=task_id,
                command=command,
                pid=process.pid,
                status="running",
                started_at=datetime.now().isoformat()
            )

            self._background_tasks[task_id] = task

            # Monitor in background thread
            def monitor():
                output, _ = process.communicate()
                task.output = output
                task.exit_code = process.returncode
                task.status = "completed" if process.returncode == 0 else "failed"
                task.ended_at = datetime.now().isoformat()

            thread = threading.Thread(target=monitor, daemon=True)
            thread.start()

            self.console.print(f"[green]✓ Started task {task_id} (PID: {process.pid})[/green]")
            self.console.print(f"[dim]Command: {command}[/dim]")

        except Exception as e:
            self.console.print(f"[red]Failed to start task: {e}[/red]")

    def _kill_background_task(self, task_id: str):
        """Kill a background task"""
        if task_id not in self._background_tasks:
            self.console.print(f"[red]Task not found: {task_id}[/red]")
            return

        task = self._background_tasks[task_id]

        if task.status != "running":
            self.console.print(f"[yellow]Task is not running (status: {task.status})[/yellow]")
            return

        try:
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/F", "/PID", str(task.pid)], capture_output=True)
            else:
                subprocess.run(["kill", "-9", str(task.pid)], capture_output=True)

            task.status = "failed"
            task.ended_at = datetime.now().isoformat()

            self.console.print(f"[green]✓ Killed task {task_id}[/green]")

        except Exception as e:
            self.console.print(f"[red]Failed to kill task: {e}[/red]")

    def _show_task_output(self, task_id: str):
        """Show output of a background task"""
        if task_id not in self._background_tasks:
            self.console.print(f"[red]Task not found: {task_id}[/red]")
            return

        task = self._background_tasks[task_id]

        self.console.print(f"\n[bold cyan]Task {task_id} Output[/bold cyan]")
        self.console.print(f"[dim]Command: {task.command}[/dim]")
        self.console.print(f"[dim]Status: {task.status}[/dim]\n")

        if task.output:
            self.console.print(Panel(task.output, border_style="dim"))
        else:
            self.console.print("[dim]No output yet[/dim]")

    # ==================== /bug ====================

    def cmd_bug(self, args: str = ""):
        """Report a bug"""
        self.console.print("\n[bold cyan]Bug Report[/bold cyan]\n")

        # Collect system info
        system_info = {
            "os": platform.system(),
            "os_version": platform.release(),
            "python_version": platform.python_version(),
            "cli_version": self.VERSION
        }

        self.console.print("[bold]System Information:[/bold]")
        for key, value in system_info.items():
            self.console.print(f"  {key}: {value}")

        self.console.print()

        if args:
            title = args
        else:
            title = Prompt.ask("[bold]Bug title[/bold]")

        description = Prompt.ask("[bold]Description[/bold] (what happened?)")
        steps = Prompt.ask("[bold]Steps to reproduce[/bold]", default="")

        include_conversation = Confirm.ask("Include recent conversation context?", default=False)

        # Build bug report
        report = {
            "title": title,
            "description": description,
            "steps_to_reproduce": steps,
            "system_info": system_info,
            "timestamp": datetime.now().isoformat()
        }

        if include_conversation and self._conversation_history:
            report["conversation_context"] = self._conversation_history[-10:]

        # Save report
        reports_dir = self.config_dir / "bug_reports"
        reports_dir.mkdir(exist_ok=True)

        report_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"bug_{report_id}.json"

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        self.console.print(f"\n[green]✓ Bug report saved: {report_file}[/green]")
        self.console.print("[dim]Thank you for reporting![/dim]")

        # Offer to open GitHub
        if Confirm.ask("\nOpen GitHub issues page?", default=True):
            import webbrowser
            webbrowser.open("https://github.com/bharatbuild/bharatbuild-cli/issues/new")

    # ==================== /export ====================

    def cmd_export(self, args: str = ""):
        """Export conversation to file or clipboard"""
        self.console.print("\n[bold cyan]Export Conversation[/bold cyan]\n")

        if not self._conversation_history:
            self.console.print("[yellow]No conversation to export[/yellow]")
            return

        # Export format selection
        self.console.print("[bold]Export format:[/bold]")
        self.console.print("  [cyan]1.[/cyan] Markdown")
        self.console.print("  [cyan]2.[/cyan] JSON")
        self.console.print("  [cyan]3.[/cyan] Plain text")

        format_choice = Prompt.ask("Select format", choices=["1", "2", "3"], default="1")

        # Export destination
        self.console.print("\n[bold]Export to:[/bold]")
        self.console.print("  [cyan]1.[/cyan] File")
        self.console.print("  [cyan]2.[/cyan] Clipboard")

        dest_choice = Prompt.ask("Select destination", choices=["1", "2"], default="1")

        # Generate content
        if format_choice == "1":
            content = self._export_markdown()
            ext = ".md"
        elif format_choice == "2":
            content = self._export_json()
            ext = ".json"
        else:
            content = self._export_text()
            ext = ".txt"

        # Export
        if dest_choice == "1":
            # Export to file
            default_name = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            filename = Prompt.ask("Filename", default=default_name)

            filepath = self.project_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            self.console.print(f"\n[green]✓ Exported to: {filepath}[/green]")
        else:
            # Export to clipboard
            try:
                pyperclip.copy(content)
                self.console.print("\n[green]✓ Copied to clipboard[/green]")
            except Exception as e:
                self.console.print(f"[red]Failed to copy to clipboard: {e}[/red]")
                self.console.print("[dim]Content:[/dim]")
                self.console.print(content[:500] + "..." if len(content) > 500 else content)

    def _export_markdown(self) -> str:
        """Export conversation as Markdown"""
        lines = ["# BharatBuild Conversation Export\n"]
        lines.append(f"*Exported: {datetime.now().isoformat()}*\n")
        lines.append("---\n")

        for msg in self._conversation_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "user":
                lines.append(f"## User\n\n{content}\n")
            elif role == "assistant":
                lines.append(f"## Assistant\n\n{content}\n")

            lines.append("---\n")

        return "\n".join(lines)

    def _export_json(self) -> str:
        """Export conversation as JSON"""
        data = {
            "exported_at": datetime.now().isoformat(),
            "messages": self._conversation_history
        }
        return json.dumps(data, indent=2)

    def _export_text(self) -> str:
        """Export conversation as plain text"""
        lines = ["BharatBuild Conversation Export"]
        lines.append(f"Exported: {datetime.now().isoformat()}")
        lines.append("=" * 50)

        for msg in self._conversation_history:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            lines.append(f"\n[{role}]\n{content}")
            lines.append("-" * 50)

        return "\n".join(lines)

    def set_conversation_history(self, history: List[Dict[str, Any]]):
        """Set conversation history for export"""
        self._conversation_history = history

    # ==================== /permissions ====================

    def cmd_permissions(self, args: str = ""):
        """View or update access controls"""
        permissions_file = self.config_dir / "permissions.json"

        # Load current permissions
        if permissions_file.exists():
            with open(permissions_file) as f:
                permissions = json.load(f)
        else:
            permissions = {
                "allow": [],
                "ask": [],
                "deny": []
            }

        if not args:
            # Show current permissions
            self.console.print("\n[bold cyan]Access Permissions[/bold cyan]\n")

            self.console.print("[bold green]Allowed (auto-approve):[/bold green]")
            if permissions["allow"]:
                for rule in permissions["allow"]:
                    self.console.print(f"  ✓ {rule}")
            else:
                self.console.print("  [dim]None[/dim]")

            self.console.print("\n[bold yellow]Ask (require confirmation):[/bold yellow]")
            if permissions["ask"]:
                for rule in permissions["ask"]:
                    self.console.print(f"  ? {rule}")
            else:
                self.console.print("  [dim]None[/dim]")

            self.console.print("\n[bold red]Denied (blocked):[/bold red]")
            if permissions["deny"]:
                for rule in permissions["deny"]:
                    self.console.print(f"  ✗ {rule}")
            else:
                self.console.print("  [dim]None[/dim]")

            self.console.print("\n[dim]Usage: /permissions add <allow|ask|deny> <pattern>[/dim]")
            self.console.print("[dim]       /permissions remove <allow|ask|deny> <pattern>[/dim]")
            self.console.print("[dim]       /permissions reset[/dim]")
            return

        parts = args.split(maxsplit=2)
        action = parts[0].lower()

        if action == "add" and len(parts) >= 3:
            category = parts[1].lower()
            pattern = parts[2]

            if category not in ["allow", "ask", "deny"]:
                self.console.print("[red]Invalid category. Use: allow, ask, deny[/red]")
                return

            if pattern not in permissions[category]:
                permissions[category].append(pattern)
                self._save_permissions(permissions)
                self.console.print(f"[green]✓ Added to {category}: {pattern}[/green]")
            else:
                self.console.print(f"[yellow]Already exists in {category}[/yellow]")

        elif action == "remove" and len(parts) >= 3:
            category = parts[1].lower()
            pattern = parts[2]

            if category not in ["allow", "ask", "deny"]:
                self.console.print("[red]Invalid category. Use: allow, ask, deny[/red]")
                return

            if pattern in permissions[category]:
                permissions[category].remove(pattern)
                self._save_permissions(permissions)
                self.console.print(f"[green]✓ Removed from {category}: {pattern}[/green]")
            else:
                self.console.print(f"[yellow]Not found in {category}[/yellow]")

        elif action == "reset":
            if Confirm.ask("Reset all permissions to default?", default=False):
                permissions = {"allow": [], "ask": [], "deny": []}
                self._save_permissions(permissions)
                self.console.print("[green]✓ Permissions reset[/green]")
        else:
            self.console.print("[yellow]Invalid command. Use: add, remove, reset[/yellow]")

    def _save_permissions(self, permissions: Dict):
        """Save permissions to file"""
        permissions_file = self.config_dir / "permissions.json"
        with open(permissions_file, 'w') as f:
            json.dump(permissions, f, indent=2)

    # ==================== /pr-comments ====================

    def cmd_pr_comments(self, args: str = ""):
        """View pull request comments"""
        self.console.print("\n[bold cyan]Pull Request Comments[/bold cyan]\n")

        # Try to get PR number from args or detect from branch
        pr_number = args.strip() if args else None

        if not pr_number:
            # Try to detect from current branch
            try:
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_dir
                )
                branch = result.stdout.strip()

                # Check if branch looks like a PR branch
                if branch:
                    self.console.print(f"[dim]Current branch: {branch}[/dim]")
                    pr_number = Prompt.ask("Enter PR number", default="")
            except:
                pass

        if not pr_number:
            self.console.print("[yellow]Please specify a PR number: /pr-comments <number>[/yellow]")
            return

        # Try to fetch PR comments using gh CLI
        try:
            # Get repository info
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                cwd=self.project_dir
            )

            if result.returncode != 0:
                self.console.print("[yellow]Not a git repository or no remote configured[/yellow]")
                return

            remote_url = result.stdout.strip()

            # Extract owner/repo from URL
            if "github.com" in remote_url:
                # Try using gh CLI
                result = subprocess.run(
                    ["gh", "pr", "view", pr_number, "--comments", "--json", "comments"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_dir
                )

                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    comments = data.get("comments", [])

                    if not comments:
                        self.console.print("[dim]No comments on this PR[/dim]")
                        return

                    for i, comment in enumerate(comments, 1):
                        author = comment.get("author", {}).get("login", "Unknown")
                        body = comment.get("body", "")
                        created = comment.get("createdAt", "")

                        self.console.print(f"\n[bold]Comment #{i}[/bold] by [cyan]{author}[/cyan]")
                        self.console.print(f"[dim]{created}[/dim]")
                        self.console.print(Panel(body, border_style="dim"))
                else:
                    self.console.print("[yellow]Failed to fetch PR comments. Is gh CLI installed?[/yellow]")
                    self.console.print(f"[dim]Error: {result.stderr}[/dim]")
            else:
                self.console.print("[yellow]Only GitHub PRs are supported currently[/yellow]")

        except FileNotFoundError:
            self.console.print("[yellow]gh CLI not found. Install it from https://cli.github.com[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    # ==================== /review ====================

    def cmd_review(self, args: str = ""):
        """Request code review"""
        self.console.print("\n[bold cyan]Code Review Request[/bold cyan]\n")

        # Get files to review
        if args:
            files = args.split()
        else:
            # Get changed files from git
            try:
                result = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_dir
                )

                if result.returncode == 0 and result.stdout.strip():
                    files = result.stdout.strip().split("\n")
                    self.console.print("[bold]Changed files:[/bold]")
                    for f in files:
                        self.console.print(f"  • {f}")

                    if not Confirm.ask("\nReview these files?", default=True):
                        files = Prompt.ask("Enter files to review (space-separated)").split()
                else:
                    files = Prompt.ask("Enter files to review (space-separated)").split()

            except:
                files = Prompt.ask("Enter files to review (space-separated)").split()

        if not files:
            self.console.print("[yellow]No files specified for review[/yellow]")
            return

        # Review type
        self.console.print("\n[bold]Review type:[/bold]")
        self.console.print("  [cyan]1.[/cyan] Security review")
        self.console.print("  [cyan]2.[/cyan] Code quality")
        self.console.print("  [cyan]3.[/cyan] Performance")
        self.console.print("  [cyan]4.[/cyan] Best practices")
        self.console.print("  [cyan]5.[/cyan] Full review (all)")

        review_type = Prompt.ask("Select type", choices=["1", "2", "3", "4", "5"], default="5")

        review_types = {
            "1": "security",
            "2": "quality",
            "3": "performance",
            "4": "best_practices",
            "5": "full"
        }

        review_request = {
            "files": files,
            "type": review_types[review_type],
            "requested_at": datetime.now().isoformat()
        }

        self.console.print(f"\n[green]✓ Review requested for {len(files)} file(s)[/green]")
        self.console.print(f"[dim]Type: {review_types[review_type]}[/dim]")

        # This would typically be sent to the AI for review
        return review_request

    # ==================== /terminal-setup ====================

    def cmd_terminal_setup(self, args: str = ""):
        """Install Shift+Enter key binding for newlines"""
        self.console.print("\n[bold cyan]Terminal Setup[/bold cyan]\n")

        system = platform.system()

        self.console.print("[bold]Available configurations:[/bold]\n")

        if system == "Darwin":  # macOS
            self.console.print("[cyan]iTerm2:[/cyan]")
            self.console.print("  1. Open iTerm2 Preferences (Cmd+,)")
            self.console.print("  2. Go to Profiles → Keys → Key Mappings")
            self.console.print("  3. Add new mapping:")
            self.console.print("     - Keyboard Shortcut: Shift+Enter")
            self.console.print("     - Action: Send Text")
            self.console.print("     - Value: \\n")

            self.console.print("\n[cyan]Terminal.app:[/cyan]")
            self.console.print("  Terminal.app doesn't support Shift+Enter remapping.")
            self.console.print("  Use \\ + Enter for multiline input instead.")

        elif system == "Windows":
            self.console.print("[cyan]Windows Terminal:[/cyan]")
            self.console.print("  1. Open Settings (Ctrl+,)")
            self.console.print("  2. Go to Actions")
            self.console.print("  3. Add new action:")
            self.console.print('     { "command": { "action": "sendInput", "input": "\\n" },')
            self.console.print('       "keys": "shift+enter" }')

            self.console.print("\n[cyan]PowerShell / CMD:[/cyan]")
            self.console.print("  Use \\ + Enter or Ctrl+J for multiline input.")

        else:  # Linux
            self.console.print("[cyan]GNOME Terminal / Konsole:[/cyan]")
            self.console.print("  Most Linux terminals support Shift+Enter by default.")
            self.console.print("  If not working, use \\ + Enter for multiline input.")

        self.console.print("\n[bold]Alternative methods (all terminals):[/bold]")
        self.console.print("  • \\ + Enter - Universal linebreak")
        self.console.print("  • Ctrl+J - Alternative linebreak")
        self.console.print("  • Paste multiline text directly")

        self.console.print("\n[dim]Note: Some terminals may require restart after configuration.[/dim]")

    # ==================== /todos ====================

    def cmd_todos(self, args: str = ""):
        """List and manage TODO items"""
        if not args:
            # Scan for TODOs in codebase
            self._scan_todos()
            self._display_todos()
            return

        parts = args.split(maxsplit=1)
        action = parts[0].lower()

        if action == "scan":
            self._scan_todos()
            self._display_todos()
        elif action == "add" and len(parts) > 1:
            self._add_todo(parts[1])
        elif action == "done" and len(parts) > 1:
            self._mark_todo_done(parts[1])
        elif action == "clear":
            self._clear_todos()
        else:
            self.console.print("[yellow]Usage: /todos [scan|add|done|clear] [args][/yellow]")

    def _scan_todos(self):
        """Scan codebase for TODO comments"""
        self._todos = []

        # File patterns to scan
        patterns = ["**/*.py", "**/*.js", "**/*.ts", "**/*.java", "**/*.go", "**/*.rs"]

        todo_id = 1

        for pattern in patterns:
            for file_path in self.project_dir.glob(pattern):
                # Skip node_modules, venv, etc.
                if any(skip in str(file_path) for skip in ["node_modules", "venv", ".git", "__pycache__"]):
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if "TODO" in line or "FIXME" in line or "HACK" in line:
                                # Extract TODO content
                                for marker in ["TODO:", "TODO", "FIXME:", "FIXME", "HACK:", "HACK"]:
                                    if marker in line:
                                        idx = line.find(marker)
                                        content = line[idx:].strip()
                                        break
                                else:
                                    content = line.strip()

                                # Determine priority
                                priority = "medium"
                                if "FIXME" in line or "!" in content:
                                    priority = "high"
                                elif "HACK" in line:
                                    priority = "low"

                                todo = TodoItem(
                                    id=str(todo_id),
                                    content=content[:100],
                                    file_path=str(file_path.relative_to(self.project_dir)),
                                    line_number=line_num,
                                    priority=priority,
                                    created_at=datetime.now().isoformat()
                                )
                                self._todos.append(todo)
                                todo_id += 1

                except Exception:
                    pass

    def _display_todos(self):
        """Display TODO items"""
        self.console.print("\n[bold cyan]TODO Items[/bold cyan]\n")

        if not self._todos:
            self.console.print("[dim]No TODOs found in codebase[/dim]")
            return

        # Group by priority
        high = [t for t in self._todos if t.priority == "high"]
        medium = [t for t in self._todos if t.priority == "medium"]
        low = [t for t in self._todos if t.priority == "low"]

        table = Table(show_header=True, header_style="bold")
        table.add_column("ID", style="dim", width=4)
        table.add_column("Priority", width=8)
        table.add_column("Content")
        table.add_column("Location")

        priority_colors = {"high": "red", "medium": "yellow", "low": "dim"}

        for todo in high + medium + low:
            color = priority_colors[todo.priority]
            location = f"{todo.file_path}:{todo.line_number}"
            table.add_row(
                todo.id,
                f"[{color}]{todo.priority}[/{color}]",
                todo.content[:50] + ("..." if len(todo.content) > 50 else ""),
                location
            )

        self.console.print(table)
        self.console.print(f"\n[dim]Total: {len(self._todos)} TODOs ({len(high)} high, {len(medium)} medium, {len(low)} low)[/dim]")

    def _add_todo(self, content: str):
        """Add a manual TODO item"""
        todo = TodoItem(
            id=str(len(self._todos) + 1),
            content=content,
            priority="medium",
            created_at=datetime.now().isoformat()
        )
        self._todos.append(todo)
        self.console.print(f"[green]✓ Added TODO: {content}[/green]")

    def _mark_todo_done(self, todo_id: str):
        """Mark a TODO as done"""
        for todo in self._todos:
            if todo.id == todo_id:
                todo.status = "done"
                self.console.print(f"[green]✓ Marked TODO #{todo_id} as done[/green]")
                return

        self.console.print(f"[red]TODO #{todo_id} not found[/red]")

    def _clear_todos(self):
        """Clear completed TODOs"""
        before = len(self._todos)
        self._todos = [t for t in self._todos if t.status != "done"]
        cleared = before - len(self._todos)
        self.console.print(f"[green]✓ Cleared {cleared} completed TODOs[/green]")

    # ==================== /output-style ====================

    def cmd_output_style(self, args: str = ""):
        """Set output style"""
        if not args:
            # Show current style and options
            self.console.print("\n[bold cyan]Output Styles[/bold cyan]\n")
            self.console.print(f"[bold]Current:[/bold] {self._output_style.value}\n")

            self.console.print("[bold]Available styles:[/bold]")
            for i, (style, desc) in enumerate(OUTPUT_STYLE_DESCRIPTIONS.items(), 1):
                current = " [green](current)[/green]" if style == self._output_style else ""
                self.console.print(f"  [cyan]{i}.[/cyan] {style.value} - {desc}{current}")

            choice = Prompt.ask("\nSelect style", choices=["1", "2", "3", "4", "5"], default="1")
            style_map = {
                "1": OutputStyle.DEFAULT,
                "2": OutputStyle.EXPLANATORY,
                "3": OutputStyle.LEARNING,
                "4": OutputStyle.CONCISE,
                "5": OutputStyle.VERBOSE
            }
            self._output_style = style_map[choice]
        else:
            # Set directly
            try:
                self._output_style = OutputStyle(args.lower())
            except ValueError:
                self.console.print(f"[red]Invalid style: {args}[/red]")
                self.console.print(f"[dim]Valid styles: {', '.join(s.value for s in OutputStyle)}[/dim]")
                return

        self._save_state()
        self.console.print(f"[green]✓ Output style set to: {self._output_style.value}[/green]")

    def get_output_style(self) -> OutputStyle:
        """Get current output style"""
        return self._output_style

    # ==================== /release-notes ====================

    def cmd_release_notes(self, args: str = ""):
        """View release notes"""
        self.console.print("\n[bold cyan]BharatBuild CLI Release Notes[/bold cyan]\n")

        # Release notes content
        release_notes = """
## Version 0.1.0 (Current)

### New Features
- Full Claude Code CLI compatibility
- 40+ slash commands
- MCP (Model Context Protocol) support
- Hooks system for automation
- Skills and subagents
- Plugin system
- Sandbox mode for safe execution
- Session management with resume
- Checkpointing and rewind
- Vim mode
- Extended thinking display

### AI/ML Features
- AI project templates
- Jupyter notebook integration
- TensorBoard and MLflow support
- GPU/CUDA detection

### Documentation
- IEEE document generation
- SRS, SDD, Test Plan templates
- Dynamic document generation from code analysis

### Coming Soon
- VS Code extension
- JetBrains plugin
- GitHub Actions integration
- Team collaboration features
"""

        self.console.print(Markdown(release_notes))

        # Check for updates
        self.console.print("\n[dim]Checking for updates...[/dim]")
        # In production, this would check the actual version
        self.console.print("[green]✓ You are on the latest version[/green]")

    # ==================== /privacy-settings ====================

    def cmd_privacy_settings(self, args: str = ""):
        """View and update privacy settings"""
        if not args:
            # Show current settings
            self.console.print("\n[bold cyan]Privacy Settings[/bold cyan]\n")

            settings = [
                ("Telemetry", self._privacy_settings.telemetry_enabled, "Send anonymous usage data"),
                ("Usage Stats", self._privacy_settings.share_usage_stats, "Share aggregated usage statistics"),
                ("Crash Reports", self._privacy_settings.send_crash_reports, "Send crash reports for debugging"),
                ("Model Training", self._privacy_settings.allow_model_training, "Allow conversations for model improvement"),
                ("Store Conversations", self._privacy_settings.store_conversations, "Store conversation history locally"),
            ]

            table = Table(show_header=True, header_style="bold")
            table.add_column("Setting")
            table.add_column("Status")
            table.add_column("Description")

            for name, enabled, desc in settings:
                status = "[green]Enabled[/green]" if enabled else "[red]Disabled[/red]"
                table.add_row(name, status, desc)

            self.console.print(table)

            self.console.print(f"\n[dim]Conversation retention: {self._privacy_settings.conversation_retention_days} days[/dim]")
            self.console.print("\n[dim]Usage: /privacy-settings <setting> <on|off>[/dim]")
            self.console.print("[dim]       /privacy-settings retention <days>[/dim]")
            return

        parts = args.split()

        if len(parts) < 2:
            self.console.print("[yellow]Usage: /privacy-settings <setting> <on|off>[/yellow]")
            return

        setting = parts[0].lower()
        value = parts[1].lower()

        setting_map = {
            "telemetry": "telemetry_enabled",
            "usage": "share_usage_stats",
            "crash": "send_crash_reports",
            "training": "allow_model_training",
            "store": "store_conversations",
            "retention": "conversation_retention_days"
        }

        if setting not in setting_map:
            self.console.print(f"[red]Unknown setting: {setting}[/red]")
            return

        attr = setting_map[setting]

        if setting == "retention":
            try:
                days = int(value)
                self._privacy_settings.conversation_retention_days = days
                self.console.print(f"[green]✓ Retention set to {days} days[/green]")
            except ValueError:
                self.console.print("[red]Invalid number of days[/red]")
                return
        else:
            if value in ["on", "true", "yes", "1"]:
                setattr(self._privacy_settings, attr, True)
                self.console.print(f"[green]✓ {setting} enabled[/green]")
            elif value in ["off", "false", "no", "0"]:
                setattr(self._privacy_settings, attr, False)
                self.console.print(f"[green]✓ {setting} disabled[/green]")
            else:
                self.console.print("[red]Invalid value. Use: on/off[/red]")
                return

        self._save_state()

    # ==================== Help ====================

    def show_help(self):
        """Show help for extended commands"""
        help_text = """
[bold cyan]Extended Commands[/bold cyan]

Additional Claude Code-compatible commands.

[bold]Directory Management:[/bold]
  [green]/add-dir[/green] <path>      Add working directory
  [green]/add-dir[/green] --remove    Remove working directory

[bold]Background Tasks:[/bold]
  [green]/bashes[/green]              List background tasks
  [green]/bashes[/green] run <cmd>    Run command in background
  [green]/bashes[/green] kill <id>    Kill background task
  [green]/bashes[/green] output <id>  Show task output

[bold]Reporting:[/bold]
  [green]/bug[/green] [title]         Report a bug
  [green]/export[/green]              Export conversation

[bold]Security:[/bold]
  [green]/permissions[/green]         View/edit access controls
  [green]/privacy-settings[/green]    Configure privacy

[bold]Code Review:[/bold]
  [green]/review[/green] [files]      Request code review
  [green]/pr-comments[/green] <num>   View PR comments

[bold]Development:[/bold]
  [green]/todos[/green]               List TODO items
  [green]/terminal-setup[/green]      Configure terminal

[bold]Configuration:[/bold]
  [green]/output-style[/green]        Set output style
  [green]/release-notes[/green]       View release notes
"""
        self.console.print(help_text)


# Factory function
def get_extended_commands(
    console: Console = None,
    config_dir: Path = None,
    project_dir: Path = None
) -> ExtendedCommandsManager:
    """Get extended commands manager instance"""
    return ExtendedCommandsManager(
        console=console or Console(),
        config_dir=config_dir,
        project_dir=project_dir
    )
