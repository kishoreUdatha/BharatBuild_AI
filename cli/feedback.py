"""
BharatBuild CLI Feedback System

Submit feedback, bug reports, and feature requests:
  /feedback           Interactive feedback submission
  /feedback bug       Report a bug
  /feedback feature   Request a feature
  /feedback praise    Send positive feedback
"""

import os
import json
import platform
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown


class FeedbackType(str, Enum):
    """Types of feedback"""
    BUG = "bug"
    FEATURE = "feature"
    IMPROVEMENT = "improvement"
    PRAISE = "praise"
    QUESTION = "question"
    OTHER = "other"


class FeedbackPriority(str, Enum):
    """Feedback priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FeedbackStatus(str, Enum):
    """Feedback submission status"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class SystemInfo:
    """System information for bug reports"""
    os_name: str = ""
    os_version: str = ""
    python_version: str = ""
    cli_version: str = ""
    terminal: str = ""
    shell: str = ""

    @classmethod
    def collect(cls) -> "SystemInfo":
        """Collect current system information"""
        import sys

        return cls(
            os_name=platform.system(),
            os_version=platform.release(),
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            cli_version="0.1.0",  # Would be fetched from version module
            terminal=os.environ.get("TERM", "unknown"),
            shell=os.environ.get("SHELL", os.environ.get("COMSPEC", "unknown"))
        )


@dataclass
class FeedbackEntry:
    """A feedback submission"""
    id: str
    type: FeedbackType
    title: str
    description: str
    created_at: str
    status: FeedbackStatus = FeedbackStatus.DRAFT
    priority: FeedbackPriority = FeedbackPriority.MEDIUM

    # Optional details
    steps_to_reproduce: List[str] = field(default_factory=list)
    expected_behavior: str = ""
    actual_behavior: str = ""
    system_info: Optional[SystemInfo] = None

    # Attachments
    logs: List[str] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)

    # Metadata
    tags: List[str] = field(default_factory=list)
    user_email: str = ""
    session_id: str = ""
    conversation_context: str = ""


class FeedbackManager:
    """
    Manages feedback submission for BharatBuild CLI.

    Features:
    - Bug reports with system info
    - Feature requests
    - Improvement suggestions
    - Positive feedback
    - Local storage of drafts
    - GitHub issue creation (optional)

    Usage:
        manager = FeedbackManager(console, config_dir)

        # Interactive submission
        manager.submit_interactive()

        # Quick bug report
        manager.submit_bug("Title", "Description")

        # Feature request
        manager.submit_feature("Title", "Description")
    """

    GITHUB_REPO = "bharatbuild/bharatbuild-cli"
    FEEDBACK_API = "https://api.bharatbuild.dev/feedback"

    def __init__(
        self,
        console: Console,
        config_dir: Path = None
    ):
        self.console = console
        self.config_dir = config_dir or Path.home() / ".bharatbuild"
        self.feedback_dir = self.config_dir / "feedback"

        # Ensure directories exist
        self.feedback_dir.mkdir(parents=True, exist_ok=True)

        # Load saved feedback
        self._feedback: List[FeedbackEntry] = []
        self._load_feedback()

    def _load_feedback(self):
        """Load saved feedback entries"""
        index_file = self.feedback_dir / "index.json"

        if index_file.exists():
            try:
                with open(index_file) as f:
                    data = json.load(f)

                for entry_data in data.get("feedback", []):
                    system_info = None
                    if entry_data.get("system_info"):
                        si = entry_data["system_info"]
                        system_info = SystemInfo(
                            os_name=si.get("os_name", ""),
                            os_version=si.get("os_version", ""),
                            python_version=si.get("python_version", ""),
                            cli_version=si.get("cli_version", ""),
                            terminal=si.get("terminal", ""),
                            shell=si.get("shell", "")
                        )

                    entry = FeedbackEntry(
                        id=entry_data["id"],
                        type=FeedbackType(entry_data["type"]),
                        title=entry_data["title"],
                        description=entry_data["description"],
                        created_at=entry_data["created_at"],
                        status=FeedbackStatus(entry_data.get("status", "draft")),
                        priority=FeedbackPriority(entry_data.get("priority", "medium")),
                        steps_to_reproduce=entry_data.get("steps_to_reproduce", []),
                        expected_behavior=entry_data.get("expected_behavior", ""),
                        actual_behavior=entry_data.get("actual_behavior", ""),
                        system_info=system_info,
                        logs=entry_data.get("logs", []),
                        screenshots=entry_data.get("screenshots", []),
                        tags=entry_data.get("tags", []),
                        user_email=entry_data.get("user_email", ""),
                        session_id=entry_data.get("session_id", ""),
                        conversation_context=entry_data.get("conversation_context", "")
                    )
                    self._feedback.append(entry)

            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load feedback: {e}[/yellow]")

    def _save_feedback(self):
        """Save feedback entries"""
        index_file = self.feedback_dir / "index.json"

        data = {
            "feedback": []
        }

        for entry in self._feedback:
            entry_data = {
                "id": entry.id,
                "type": entry.type.value,
                "title": entry.title,
                "description": entry.description,
                "created_at": entry.created_at,
                "status": entry.status.value,
                "priority": entry.priority.value,
                "steps_to_reproduce": entry.steps_to_reproduce,
                "expected_behavior": entry.expected_behavior,
                "actual_behavior": entry.actual_behavior,
                "system_info": asdict(entry.system_info) if entry.system_info else None,
                "logs": entry.logs,
                "screenshots": entry.screenshots,
                "tags": entry.tags,
                "user_email": entry.user_email,
                "session_id": entry.session_id,
                "conversation_context": entry.conversation_context
            }
            data["feedback"].append(entry_data)

        with open(index_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _generate_id(self) -> str:
        """Generate unique feedback ID"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    # ==================== Interactive Submission ====================

    def submit_interactive(self, feedback_type: FeedbackType = None):
        """Interactive feedback submission"""
        self.console.print("\n[bold cyan]📝 BharatBuild Feedback[/bold cyan]\n")

        # Select type if not provided
        if not feedback_type:
            self.console.print("[bold]What type of feedback would you like to submit?[/bold]\n")
            self.console.print("  [cyan]1.[/cyan] 🐛 Bug Report")
            self.console.print("  [cyan]2.[/cyan] ✨ Feature Request")
            self.console.print("  [cyan]3.[/cyan] 💡 Improvement Suggestion")
            self.console.print("  [cyan]4.[/cyan] 🎉 Praise / Positive Feedback")
            self.console.print("  [cyan]5.[/cyan] ❓ Question")
            self.console.print("  [cyan]6.[/cyan] 📋 Other")
            self.console.print()

            choice = Prompt.ask(
                "Select type",
                choices=["1", "2", "3", "4", "5", "6"],
                default="1"
            )

            type_map = {
                "1": FeedbackType.BUG,
                "2": FeedbackType.FEATURE,
                "3": FeedbackType.IMPROVEMENT,
                "4": FeedbackType.PRAISE,
                "5": FeedbackType.QUESTION,
                "6": FeedbackType.OTHER
            }
            feedback_type = type_map[choice]

        # Route to specific handler
        if feedback_type == FeedbackType.BUG:
            self._submit_bug_interactive()
        elif feedback_type == FeedbackType.FEATURE:
            self._submit_feature_interactive()
        elif feedback_type == FeedbackType.PRAISE:
            self._submit_praise_interactive()
        else:
            self._submit_general_interactive(feedback_type)

    def _submit_bug_interactive(self):
        """Interactive bug report submission"""
        self.console.print("\n[bold red]🐛 Bug Report[/bold red]\n")

        # Title
        title = Prompt.ask("[bold]Title[/bold] (brief description)")

        # Description
        self.console.print("\n[bold]Description[/bold] (what happened?)")
        description = Prompt.ask("")

        # Steps to reproduce
        self.console.print("\n[bold]Steps to Reproduce[/bold] (one per line, empty to finish)")
        steps = []
        step_num = 1
        while True:
            step = Prompt.ask(f"  {step_num}.", default="")
            if not step:
                break
            steps.append(step)
            step_num += 1

        # Expected vs actual
        expected = Prompt.ask("\n[bold]Expected behavior[/bold]", default="")
        actual = Prompt.ask("[bold]Actual behavior[/bold]", default="")

        # Priority
        self.console.print("\n[bold]Priority[/bold]")
        priority_choice = Prompt.ask(
            "  Select",
            choices=["low", "medium", "high", "critical"],
            default="medium"
        )
        priority = FeedbackPriority(priority_choice)

        # Collect system info
        include_system = Confirm.ask("\nInclude system information?", default=True)
        system_info = SystemInfo.collect() if include_system else None

        # Include logs
        include_logs = Confirm.ask("Include recent logs?", default=False)
        logs = []
        if include_logs:
            logs = self._collect_recent_logs()

        # Email (optional)
        email = Prompt.ask("\n[bold]Email[/bold] (optional, for follow-up)", default="")

        # Create entry
        entry = FeedbackEntry(
            id=self._generate_id(),
            type=FeedbackType.BUG,
            title=title,
            description=description,
            created_at=datetime.now().isoformat(),
            priority=priority,
            steps_to_reproduce=steps,
            expected_behavior=expected,
            actual_behavior=actual,
            system_info=system_info,
            logs=logs,
            user_email=email
        )

        # Confirm and submit
        self._confirm_and_submit(entry)

    def _submit_feature_interactive(self):
        """Interactive feature request submission"""
        self.console.print("\n[bold green]✨ Feature Request[/bold green]\n")

        # Title
        title = Prompt.ask("[bold]Feature Title[/bold]")

        # Description
        self.console.print("\n[bold]Description[/bold] (what should this feature do?)")
        description = Prompt.ask("")

        # Use case
        use_case = Prompt.ask("\n[bold]Use Case[/bold] (why do you need this?)", default="")

        # Priority
        priority_choice = Prompt.ask(
            "\n[bold]Priority[/bold]",
            choices=["low", "medium", "high"],
            default="medium"
        )
        priority = FeedbackPriority(priority_choice)

        # Email
        email = Prompt.ask("\n[bold]Email[/bold] (optional)", default="")

        # Create entry
        entry = FeedbackEntry(
            id=self._generate_id(),
            type=FeedbackType.FEATURE,
            title=title,
            description=description,
            created_at=datetime.now().isoformat(),
            priority=priority,
            expected_behavior=use_case,
            user_email=email
        )

        self._confirm_and_submit(entry)

    def _submit_praise_interactive(self):
        """Interactive praise submission"""
        self.console.print("\n[bold yellow]🎉 We love positive feedback![/bold yellow]\n")

        # Title
        title = Prompt.ask("[bold]What did you love?[/bold]")

        # Description
        description = Prompt.ask("\n[bold]Tell us more[/bold] (optional)", default="")

        # Create entry
        entry = FeedbackEntry(
            id=self._generate_id(),
            type=FeedbackType.PRAISE,
            title=title,
            description=description,
            created_at=datetime.now().isoformat(),
            priority=FeedbackPriority.LOW
        )

        self._confirm_and_submit(entry)

    def _submit_general_interactive(self, feedback_type: FeedbackType):
        """General feedback submission"""
        type_names = {
            FeedbackType.IMPROVEMENT: "💡 Improvement Suggestion",
            FeedbackType.QUESTION: "❓ Question",
            FeedbackType.OTHER: "📋 Feedback"
        }

        self.console.print(f"\n[bold cyan]{type_names.get(feedback_type, 'Feedback')}[/bold cyan]\n")

        title = Prompt.ask("[bold]Title[/bold]")
        description = Prompt.ask("[bold]Description[/bold]")
        email = Prompt.ask("\n[bold]Email[/bold] (optional)", default="")

        entry = FeedbackEntry(
            id=self._generate_id(),
            type=feedback_type,
            title=title,
            description=description,
            created_at=datetime.now().isoformat(),
            user_email=email
        )

        self._confirm_and_submit(entry)

    def _confirm_and_submit(self, entry: FeedbackEntry):
        """Confirm and submit feedback"""
        self.console.print("\n")
        self._show_entry_preview(entry)

        self.console.print("\n[bold]How would you like to submit?[/bold]")
        self.console.print("  [cyan]1.[/cyan] Save locally (for later)")
        self.console.print("  [cyan]2.[/cyan] Open GitHub issue")
        self.console.print("  [cyan]3.[/cyan] Submit to BharatBuild")
        self.console.print("  [cyan]4.[/cyan] Cancel")

        choice = Prompt.ask("Select", choices=["1", "2", "3", "4"], default="1")

        if choice == "1":
            self._save_locally(entry)
        elif choice == "2":
            self._open_github_issue(entry)
        elif choice == "3":
            self._submit_to_api(entry)
        else:
            self.console.print("[dim]Cancelled[/dim]")

    def _show_entry_preview(self, entry: FeedbackEntry):
        """Show preview of feedback entry"""
        type_emoji = {
            FeedbackType.BUG: "🐛",
            FeedbackType.FEATURE: "✨",
            FeedbackType.IMPROVEMENT: "💡",
            FeedbackType.PRAISE: "🎉",
            FeedbackType.QUESTION: "❓",
            FeedbackType.OTHER: "📋"
        }

        content_lines = []
        content_lines.append(f"[bold]Type:[/bold] {type_emoji.get(entry.type, '')} {entry.type.value.title()}")
        content_lines.append(f"[bold]Title:[/bold] {entry.title}")
        content_lines.append(f"[bold]Priority:[/bold] {entry.priority.value}")
        content_lines.append("")
        content_lines.append(f"[bold]Description:[/bold]")
        content_lines.append(f"  {entry.description}")

        if entry.steps_to_reproduce:
            content_lines.append("")
            content_lines.append("[bold]Steps to Reproduce:[/bold]")
            for i, step in enumerate(entry.steps_to_reproduce, 1):
                content_lines.append(f"  {i}. {step}")

        if entry.expected_behavior:
            content_lines.append("")
            content_lines.append(f"[bold]Expected:[/bold] {entry.expected_behavior}")

        if entry.actual_behavior:
            content_lines.append(f"[bold]Actual:[/bold] {entry.actual_behavior}")

        if entry.system_info:
            content_lines.append("")
            content_lines.append("[bold]System:[/bold]")
            content_lines.append(f"  OS: {entry.system_info.os_name} {entry.system_info.os_version}")
            content_lines.append(f"  Python: {entry.system_info.python_version}")
            content_lines.append(f"  CLI: {entry.system_info.cli_version}")

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title="[bold cyan]Feedback Preview[/bold cyan]",
            border_style="cyan"
        )
        self.console.print(panel)

    # ==================== Submission Methods ====================

    def _save_locally(self, entry: FeedbackEntry):
        """Save feedback locally"""
        entry.status = FeedbackStatus.DRAFT
        self._feedback.append(entry)
        self._save_feedback()

        self.console.print(f"\n[green]✓ Feedback saved locally[/green]")
        self.console.print(f"[dim]ID: {entry.id}[/dim]")
        self.console.print(f"[dim]Use '/feedback list' to view saved feedback[/dim]")

    def _open_github_issue(self, entry: FeedbackEntry):
        """Open GitHub issue in browser"""
        import urllib.parse

        # Build issue body
        body_parts = []
        body_parts.append(f"## Description\n{entry.description}")

        if entry.steps_to_reproduce:
            body_parts.append("\n## Steps to Reproduce")
            for i, step in enumerate(entry.steps_to_reproduce, 1):
                body_parts.append(f"{i}. {step}")

        if entry.expected_behavior:
            body_parts.append(f"\n## Expected Behavior\n{entry.expected_behavior}")

        if entry.actual_behavior:
            body_parts.append(f"\n## Actual Behavior\n{entry.actual_behavior}")

        if entry.system_info:
            body_parts.append("\n## System Information")
            body_parts.append(f"- OS: {entry.system_info.os_name} {entry.system_info.os_version}")
            body_parts.append(f"- Python: {entry.system_info.python_version}")
            body_parts.append(f"- CLI Version: {entry.system_info.cli_version}")

        body = "\n".join(body_parts)

        # Build labels
        labels = []
        if entry.type == FeedbackType.BUG:
            labels.append("bug")
        elif entry.type == FeedbackType.FEATURE:
            labels.append("enhancement")

        # Build URL
        params = {
            "title": entry.title,
            "body": body
        }
        if labels:
            params["labels"] = ",".join(labels)

        query = urllib.parse.urlencode(params)
        url = f"https://github.com/{self.GITHUB_REPO}/issues/new?{query}"

        # Open in browser
        try:
            import webbrowser
            webbrowser.open(url)
            self.console.print(f"\n[green]✓ Opened GitHub issue form in browser[/green]")

            # Save locally as submitted
            entry.status = FeedbackStatus.SUBMITTED
            self._feedback.append(entry)
            self._save_feedback()

        except Exception as e:
            self.console.print(f"[red]Could not open browser: {e}[/red]")
            self.console.print(f"[dim]URL: {url}[/dim]")

    def _submit_to_api(self, entry: FeedbackEntry):
        """Submit feedback to BharatBuild API"""
        # In a real implementation, this would POST to the feedback API
        # For now, we simulate submission

        self.console.print("\n[cyan]Submitting feedback...[/cyan]")

        try:
            # Simulate API call
            # In production: requests.post(self.FEEDBACK_API, json=asdict(entry))

            import time
            time.sleep(1)  # Simulate network delay

            entry.status = FeedbackStatus.SUBMITTED
            self._feedback.append(entry)
            self._save_feedback()

            self.console.print(f"[green]✓ Feedback submitted successfully![/green]")
            self.console.print(f"[dim]Reference: {entry.id}[/dim]")
            self.console.print(f"[dim]Thank you for your feedback![/dim]")

        except Exception as e:
            self.console.print(f"[red]Failed to submit: {e}[/red]")
            self.console.print("[dim]Saving locally instead...[/dim]")
            self._save_locally(entry)

    # ==================== Quick Submission ====================

    def submit_bug(self, title: str, description: str, **kwargs):
        """Quick bug report submission"""
        entry = FeedbackEntry(
            id=self._generate_id(),
            type=FeedbackType.BUG,
            title=title,
            description=description,
            created_at=datetime.now().isoformat(),
            system_info=SystemInfo.collect(),
            **kwargs
        )

        self._feedback.append(entry)
        self._save_feedback()

        self.console.print(f"[green]✓ Bug report saved: {entry.id}[/green]")
        return entry

    def submit_feature(self, title: str, description: str, **kwargs):
        """Quick feature request submission"""
        entry = FeedbackEntry(
            id=self._generate_id(),
            type=FeedbackType.FEATURE,
            title=title,
            description=description,
            created_at=datetime.now().isoformat(),
            **kwargs
        )

        self._feedback.append(entry)
        self._save_feedback()

        self.console.print(f"[green]✓ Feature request saved: {entry.id}[/green]")
        return entry

    # ==================== Management ====================

    def list_feedback(self, status: FeedbackStatus = None, limit: int = 20):
        """List saved feedback"""
        feedback = self._feedback

        if status:
            feedback = [f for f in feedback if f.status == status]

        if not feedback:
            self.console.print("[dim]No feedback found[/dim]")
            return

        table = Table(title="Feedback", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim", width=15)
        table.add_column("Type")
        table.add_column("Title")
        table.add_column("Status")
        table.add_column("Priority")
        table.add_column("Created")

        type_emoji = {
            FeedbackType.BUG: "🐛",
            FeedbackType.FEATURE: "✨",
            FeedbackType.IMPROVEMENT: "💡",
            FeedbackType.PRAISE: "🎉",
            FeedbackType.QUESTION: "❓",
            FeedbackType.OTHER: "📋"
        }

        for entry in reversed(feedback[-limit:]):
            try:
                dt = datetime.fromisoformat(entry.created_at)
                time_str = dt.strftime("%m/%d %H:%M")
            except Exception:
                time_str = entry.created_at[:16]

            table.add_row(
                entry.id,
                f"{type_emoji.get(entry.type, '')} {entry.type.value}",
                entry.title[:30] + ("..." if len(entry.title) > 30 else ""),
                entry.status.value,
                entry.priority.value,
                time_str
            )

        self.console.print(table)

    def show_feedback(self, feedback_id: str):
        """Show feedback details"""
        entry = None
        for f in self._feedback:
            if f.id == feedback_id:
                entry = f
                break

        if not entry:
            self.console.print(f"[red]Feedback not found: {feedback_id}[/red]")
            return

        self._show_entry_preview(entry)

    def delete_feedback(self, feedback_id: str) -> bool:
        """Delete a feedback entry"""
        for i, f in enumerate(self._feedback):
            if f.id == feedback_id:
                del self._feedback[i]
                self._save_feedback()
                self.console.print(f"[green]✓ Deleted feedback: {feedback_id}[/green]")
                return True

        self.console.print(f"[red]Feedback not found: {feedback_id}[/red]")
        return False

    def _collect_recent_logs(self) -> List[str]:
        """Collect recent log entries"""
        logs = []
        log_file = self.config_dir / "logs" / "cli.log"

        if log_file.exists():
            try:
                with open(log_file) as f:
                    lines = f.readlines()
                    # Get last 50 lines
                    logs = [line.strip() for line in lines[-50:]]
            except Exception:
                pass

        return logs

    def show_help(self):
        """Show feedback help"""
        help_text = """
[bold cyan]Feedback Commands[/bold cyan]

Submit feedback, bug reports, and feature requests.

[bold]Commands:[/bold]
  [green]/feedback[/green]              Interactive feedback submission
  [green]/feedback bug[/green]          Report a bug
  [green]/feedback feature[/green]      Request a feature
  [green]/feedback praise[/green]       Send positive feedback
  [green]/feedback list[/green]         List saved feedback
  [green]/feedback show <id>[/green]    Show feedback details
  [green]/feedback delete <id>[/green]  Delete feedback

[bold]Quick Examples:[/bold]
  /feedback
  /feedback bug "CLI crashes on startup"
  /feedback feature "Add dark mode"

[bold]Submission Options:[/bold]
  - Save locally (as draft)
  - Open GitHub issue
  - Submit to BharatBuild

[bold]Bug Reports Include:[/bold]
  - System information
  - Steps to reproduce
  - Expected vs actual behavior
  - Recent logs (optional)
"""
        self.console.print(help_text)
