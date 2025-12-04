"""
BharatBuild CLI Session Manager

Resume and manage conversation sessions:
  bharatbuild -c      Continue recent conversation
  bharatbuild -r      Resume specific session
  /sessions           List recent sessions
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt


class SessionState(str, Enum):
    """Session state"""
    ACTIVE = "active"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    ARCHIVED = "archived"


@dataclass
class SessionMetadata:
    """Session metadata"""
    id: str
    created_at: str
    updated_at: str
    state: SessionState = SessionState.ACTIVE
    project_dir: str = ""
    project_name: str = ""
    summary: str = ""
    message_count: int = 0
    token_count: int = 0


@dataclass
class Session:
    """A conversation session"""
    metadata: SessionMetadata
    messages: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """
    Manages conversation sessions for resume functionality.

    Features:
    - Auto-save sessions
    - Continue recent session (-c)
    - Resume specific session (-r)
    - Session history
    - Session archiving

    Usage:
        manager = SessionManager(console, config_dir)

        # Start new session
        session = manager.create_session()

        # Save session state
        manager.save_session(session)

        # Resume session
        session = manager.resume_session(session_id)

        # Continue most recent
        session = manager.continue_recent()
    """

    MAX_SESSIONS = 50
    AUTO_SAVE_INTERVAL = 5  # Save every N messages

    def __init__(
        self,
        console: Console,
        config_dir: Path = None,
        project_dir: Path = None
    ):
        self.console = console
        self.config_dir = config_dir or Path.home() / ".bharatbuild"
        self.project_dir = project_dir or Path.cwd()
        self.sessions_dir = self.config_dir / "sessions"

        # Ensure directories exist
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Current session
        self._current_session: Optional[Session] = None

        # Session index
        self._sessions: List[SessionMetadata] = []
        self._load_index()

    def _load_index(self):
        """Load session index"""
        index_file = self.sessions_dir / "index.json"

        if index_file.exists():
            try:
                with open(index_file) as f:
                    data = json.load(f)

                for session_data in data.get("sessions", []):
                    metadata = SessionMetadata(
                        id=session_data["id"],
                        created_at=session_data["created_at"],
                        updated_at=session_data.get("updated_at", session_data["created_at"]),
                        state=SessionState(session_data.get("state", "completed")),
                        project_dir=session_data.get("project_dir", ""),
                        project_name=session_data.get("project_name", ""),
                        summary=session_data.get("summary", ""),
                        message_count=session_data.get("message_count", 0),
                        token_count=session_data.get("token_count", 0)
                    )
                    self._sessions.append(metadata)

            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load session index: {e}[/yellow]")

    def _save_index(self):
        """Save session index"""
        index_file = self.sessions_dir / "index.json"

        data = {
            "sessions": [
                {
                    "id": s.id,
                    "created_at": s.created_at,
                    "updated_at": s.updated_at,
                    "state": s.state.value,
                    "project_dir": s.project_dir,
                    "project_name": s.project_name,
                    "summary": s.summary,
                    "message_count": s.message_count,
                    "token_count": s.token_count
                }
                for s in self._sessions[-self.MAX_SESSIONS:]
            ]
        }

        with open(index_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _get_session_file(self, session_id: str) -> Path:
        """Get session file path"""
        return self.sessions_dir / f"{session_id}.json"

    # ==================== Session Operations ====================

    def create_session(self) -> Session:
        """Create a new session"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        metadata = SessionMetadata(
            id=session_id,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            state=SessionState.ACTIVE,
            project_dir=str(self.project_dir),
            project_name=self.project_dir.name
        )

        session = Session(metadata=metadata)

        # Add to index
        self._sessions.append(metadata)
        self._current_session = session

        # Save
        self._save_session_file(session)
        self._save_index()

        return session

    def get_current_session(self) -> Optional[Session]:
        """Get current active session"""
        return self._current_session

    def save_session(self, session: Session = None):
        """Save session to disk"""
        session = session or self._current_session
        if not session:
            return

        # Update metadata
        session.metadata.updated_at = datetime.now().isoformat()
        session.metadata.message_count = len(session.messages)

        # Estimate tokens
        session.metadata.token_count = sum(
            len(str(m.get("content", ""))) // 4
            for m in session.messages
        )

        # Generate summary from first user message
        if not session.metadata.summary and session.messages:
            for msg in session.messages:
                if msg.get("role") == "user":
                    content = str(msg.get("content", ""))
                    session.metadata.summary = content[:100]
                    if len(content) > 100:
                        session.metadata.summary += "..."
                    break

        # Save
        self._save_session_file(session)

        # Update index
        for i, s in enumerate(self._sessions):
            if s.id == session.metadata.id:
                self._sessions[i] = session.metadata
                break

        self._save_index()

    def _save_session_file(self, session: Session):
        """Save session to file"""
        session_file = self._get_session_file(session.metadata.id)

        data = {
            "metadata": {
                "id": session.metadata.id,
                "created_at": session.metadata.created_at,
                "updated_at": session.metadata.updated_at,
                "state": session.metadata.state.value,
                "project_dir": session.metadata.project_dir,
                "project_name": session.metadata.project_name,
                "summary": session.metadata.summary,
                "message_count": session.metadata.message_count,
                "token_count": session.metadata.token_count
            },
            "messages": session.messages,
            "context": session.context
        }

        with open(session_file, 'w') as f:
            json.dump(data, f, indent=2)

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load session from disk"""
        session_file = self._get_session_file(session_id)

        if not session_file.exists():
            return None

        try:
            with open(session_file) as f:
                data = json.load(f)

            metadata = SessionMetadata(
                id=data["metadata"]["id"],
                created_at=data["metadata"]["created_at"],
                updated_at=data["metadata"].get("updated_at", data["metadata"]["created_at"]),
                state=SessionState(data["metadata"].get("state", "completed")),
                project_dir=data["metadata"].get("project_dir", ""),
                project_name=data["metadata"].get("project_name", ""),
                summary=data["metadata"].get("summary", ""),
                message_count=data["metadata"].get("message_count", 0),
                token_count=data["metadata"].get("token_count", 0)
            )

            return Session(
                metadata=metadata,
                messages=data.get("messages", []),
                context=data.get("context", {})
            )

        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not load session {session_id}: {e}[/yellow]")
            return None

    def resume_session(self, session_id: str) -> Optional[Session]:
        """Resume a specific session"""
        session = self.load_session(session_id)

        if not session:
            self.console.print(f"[red]Session not found: {session_id}[/red]")
            return None

        # Update state
        session.metadata.state = SessionState.ACTIVE
        self._current_session = session

        self.console.print(f"[green]✓ Resumed session: {session.metadata.id}[/green]")
        self.console.print(f"[dim]{session.metadata.summary}[/dim]")
        self.console.print(f"[dim]{session.metadata.message_count} messages[/dim]")

        return session

    def continue_recent(self) -> Optional[Session]:
        """Continue the most recent session"""
        # Find most recent session for current project
        project_sessions = [
            s for s in reversed(self._sessions)
            if s.project_dir == str(self.project_dir)
        ]

        if not project_sessions:
            # Fall back to any recent session
            if self._sessions:
                return self.resume_session(self._sessions[-1].id)
            else:
                self.console.print("[yellow]No recent sessions to continue[/yellow]")
                return None

        return self.resume_session(project_sessions[0].id)

    def end_session(self, session: Session = None):
        """End and save session"""
        session = session or self._current_session
        if not session:
            return

        session.metadata.state = SessionState.COMPLETED
        self.save_session(session)

        if session == self._current_session:
            self._current_session = None

    def add_message(self, message: Dict[str, Any]):
        """Add message to current session"""
        if not self._current_session:
            return

        self._current_session.messages.append(message)

        # Auto-save periodically
        if len(self._current_session.messages) % self.AUTO_SAVE_INTERVAL == 0:
            self.save_session()

    def update_context(self, context: Dict[str, Any]):
        """Update session context"""
        if not self._current_session:
            return

        self._current_session.context.update(context)

    # ==================== Session Management ====================

    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        session_file = self._get_session_file(session_id)

        if session_file.exists():
            session_file.unlink()

        # Remove from index
        self._sessions = [s for s in self._sessions if s.id != session_id]
        self._save_index()

        self.console.print(f"[green]✓ Deleted session: {session_id}[/green]")
        return True

    def archive_session(self, session_id: str) -> bool:
        """Archive a session"""
        for session in self._sessions:
            if session.id == session_id:
                session.state = SessionState.ARCHIVED
                self._save_index()
                self.console.print(f"[green]✓ Archived session: {session_id}[/green]")
                return True

        return False

    def clear_old_sessions(self, days: int = 30):
        """Clear sessions older than N days"""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        to_delete = []

        for session in self._sessions:
            try:
                created = datetime.fromisoformat(session.created_at).timestamp()
                if created < cutoff:
                    to_delete.append(session.id)
            except Exception:
                pass

        for session_id in to_delete:
            self.delete_session(session_id)

        self.console.print(f"[green]✓ Cleared {len(to_delete)} old sessions[/green]")

    # ==================== Display ====================

    def list_sessions(self, limit: int = 20, project_only: bool = False):
        """List recent sessions"""
        sessions = self._sessions

        if project_only:
            sessions = [s for s in sessions if s.project_dir == str(self.project_dir)]

        if not sessions:
            self.console.print("[dim]No sessions found[/dim]")
            return

        table = Table(title="Recent Sessions", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim", width=15)
        table.add_column("Project")
        table.add_column("Summary")
        table.add_column("Messages", justify="right")
        table.add_column("Status")
        table.add_column("Updated")

        for session in reversed(sessions[-limit:]):
            # Format time
            try:
                dt = datetime.fromisoformat(session.updated_at)
                time_str = dt.strftime("%m/%d %H:%M")
            except Exception:
                time_str = session.updated_at[:16]

            # Status
            status_map = {
                SessionState.ACTIVE: "[green]Active[/green]",
                SessionState.COMPLETED: "[dim]Completed[/dim]",
                SessionState.INTERRUPTED: "[yellow]Interrupted[/yellow]",
                SessionState.ARCHIVED: "[dim]Archived[/dim]"
            }
            status = status_map.get(session.state, session.state.value)

            # Summary
            summary = session.summary[:30]
            if len(session.summary) > 30:
                summary += "..."

            table.add_row(
                session.id,
                session.project_name or "[dim]-[/dim]",
                summary or "[dim]No summary[/dim]",
                str(session.message_count),
                status,
                time_str
            )

        self.console.print(table)
        self.console.print(f"\n[dim]Use 'bharatbuild -r <id>' to resume a session[/dim]")

    def show_session(self, session_id: str):
        """Show session details"""
        session = self.load_session(session_id)

        if not session:
            self.console.print(f"[red]Session not found: {session_id}[/red]")
            return

        content_lines = []
        content_lines.append(f"[bold]ID:[/bold] {session.metadata.id}")
        content_lines.append(f"[bold]Project:[/bold] {session.metadata.project_name}")
        content_lines.append(f"[bold]Directory:[/bold] {session.metadata.project_dir}")
        content_lines.append(f"[bold]Created:[/bold] {session.metadata.created_at}")
        content_lines.append(f"[bold]Updated:[/bold] {session.metadata.updated_at}")
        content_lines.append(f"[bold]State:[/bold] {session.metadata.state.value}")
        content_lines.append("")
        content_lines.append(f"[bold]Messages:[/bold] {session.metadata.message_count}")
        content_lines.append(f"[bold]Tokens:[/bold] ~{session.metadata.token_count}")
        content_lines.append("")
        content_lines.append(f"[bold]Summary:[/bold]")
        content_lines.append(f"  {session.metadata.summary or 'No summary'}")

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title="[bold cyan]Session Details[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

    def show_help(self):
        """Show session help"""
        help_text = """
[bold cyan]Session Commands[/bold cyan]

Manage and resume conversation sessions.

[bold]CLI Arguments:[/bold]
  bharatbuild -c       Continue most recent session
  bharatbuild -r <id>  Resume specific session

[bold]Commands:[/bold]
  [green]/sessions[/green]           List recent sessions
  [green]/session show <id>[/green]  Show session details
  [green]/session resume <id>[/green] Resume session
  [green]/session delete <id>[/green] Delete session
  [green]/session archive <id>[/green] Archive session
  [green]/session clear[/green]      Clear old sessions

[bold]Auto-Save:[/bold]
  Sessions are automatically saved every 5 messages.
  Interrupted sessions can be resumed later.

[bold]Examples:[/bold]
  bharatbuild -c
  bharatbuild -r 20240101_123456
  /sessions --project
"""
        self.console.print(help_text)
