"""
BharatBuild CLI Checkpointing & Rewind System

Save and restore conversation and code states:
  /checkpoint         Create checkpoint
  /rewind             Rewind to previous state
  /checkpoints        List all checkpoints
"""

import os
import json
import shutil
import hashlib
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm


class RewindMode(str, Enum):
    """Rewind modes"""
    CONVERSATION_ONLY = "conversation"  # Rewind conversation only
    CODE_ONLY = "code"                  # Rewind code only
    BOTH = "both"                       # Rewind both


@dataclass
class FileSnapshot:
    """Snapshot of a file state"""
    path: str
    content_hash: str
    exists: bool
    content: Optional[str] = None  # Only stored if file is small


@dataclass
class CodeState:
    """State of code/files at a checkpoint"""
    files: Dict[str, FileSnapshot] = field(default_factory=dict)
    git_commit: str = ""  # Git commit hash if available
    git_branch: str = ""
    git_dirty: bool = False
    timestamp: str = ""


@dataclass
class ConversationState:
    """State of conversation at a checkpoint"""
    messages: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0


@dataclass
class Checkpoint:
    """A complete checkpoint"""
    id: str
    name: str
    description: str
    timestamp: str
    conversation: ConversationState
    code: CodeState
    metadata: Dict[str, Any] = field(default_factory=dict)


class CheckpointManager:
    """
    Manages checkpoints for conversation and code state.

    Features:
    - Automatic checkpoints on each user prompt
    - Manual checkpoint creation
    - Rewind to any checkpoint
    - Granular rewind (conversation only, code only, or both)
    - 30-day retention
    - Git integration

    Usage:
        manager = CheckpointManager(console, project_dir, config_dir)

        # Create checkpoint
        manager.create_checkpoint("Before refactoring")

        # Rewind
        manager.rewind(checkpoint_id, RewindMode.BOTH)

        # List checkpoints
        manager.list_checkpoints()
    """

    MAX_FILE_SIZE = 100 * 1024  # 100KB max for inline storage
    RETENTION_DAYS = 30
    MAX_CHECKPOINTS = 100

    def __init__(
        self,
        console: Console,
        project_dir: Path = None,
        config_dir: Path = None
    ):
        self.console = console
        self.project_dir = project_dir or Path.cwd()
        self.config_dir = config_dir or Path.home() / ".bharatbuild"
        self.checkpoints_dir = self.config_dir / "checkpoints" / self._get_project_id()

        # Ensure directories exist
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

        # Current conversation state
        self._current_messages: List[Dict[str, Any]] = []
        self._current_context: Dict[str, Any] = {}

        # Load checkpoint index
        self._checkpoints: List[Checkpoint] = []
        self._load_index()

    def _get_project_id(self) -> str:
        """Get unique project identifier"""
        return hashlib.md5(str(self.project_dir).encode()).hexdigest()[:12]

    def _load_index(self):
        """Load checkpoint index"""
        index_file = self.checkpoints_dir / "index.json"

        if index_file.exists():
            try:
                with open(index_file) as f:
                    data = json.load(f)

                for cp_data in data.get("checkpoints", []):
                    checkpoint = self._deserialize_checkpoint(cp_data)
                    if checkpoint:
                        self._checkpoints.append(checkpoint)

                # Clean old checkpoints
                self._cleanup_old_checkpoints()

            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load checkpoints: {e}[/yellow]")

    def _save_index(self):
        """Save checkpoint index"""
        index_file = self.checkpoints_dir / "index.json"

        data = {
            "project_dir": str(self.project_dir),
            "checkpoints": [self._serialize_checkpoint(cp) for cp in self._checkpoints]
        }

        with open(index_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _serialize_checkpoint(self, checkpoint: Checkpoint) -> Dict:
        """Serialize checkpoint for storage"""
        return {
            "id": checkpoint.id,
            "name": checkpoint.name,
            "description": checkpoint.description,
            "timestamp": checkpoint.timestamp,
            "conversation": {
                "messages": checkpoint.conversation.messages,
                "context": checkpoint.conversation.context,
                "token_count": checkpoint.conversation.token_count
            },
            "code": {
                "files": {path: asdict(snap) for path, snap in checkpoint.code.files.items()},
                "git_commit": checkpoint.code.git_commit,
                "git_branch": checkpoint.code.git_branch,
                "git_dirty": checkpoint.code.git_dirty,
                "timestamp": checkpoint.code.timestamp
            },
            "metadata": checkpoint.metadata
        }

    def _deserialize_checkpoint(self, data: Dict) -> Optional[Checkpoint]:
        """Deserialize checkpoint from storage"""
        try:
            files = {}
            for path, snap_data in data.get("code", {}).get("files", {}).items():
                files[path] = FileSnapshot(**snap_data)

            code = CodeState(
                files=files,
                git_commit=data.get("code", {}).get("git_commit", ""),
                git_branch=data.get("code", {}).get("git_branch", ""),
                git_dirty=data.get("code", {}).get("git_dirty", False),
                timestamp=data.get("code", {}).get("timestamp", "")
            )

            conv_data = data.get("conversation", {})
            conversation = ConversationState(
                messages=conv_data.get("messages", []),
                context=conv_data.get("context", {}),
                token_count=conv_data.get("token_count", 0)
            )

            return Checkpoint(
                id=data["id"],
                name=data.get("name", ""),
                description=data.get("description", ""),
                timestamp=data["timestamp"],
                conversation=conversation,
                code=code,
                metadata=data.get("metadata", {})
            )
        except Exception:
            return None

    def _cleanup_old_checkpoints(self):
        """Remove checkpoints older than retention period"""
        cutoff = datetime.now().timestamp() - (self.RETENTION_DAYS * 24 * 60 * 60)

        new_checkpoints = []
        for cp in self._checkpoints:
            try:
                cp_time = datetime.fromisoformat(cp.timestamp).timestamp()
                if cp_time > cutoff:
                    new_checkpoints.append(cp)
                else:
                    # Delete checkpoint files
                    self._delete_checkpoint_files(cp.id)
            except Exception:
                new_checkpoints.append(cp)

        # Also enforce max checkpoints
        if len(new_checkpoints) > self.MAX_CHECKPOINTS:
            for cp in new_checkpoints[:-self.MAX_CHECKPOINTS]:
                self._delete_checkpoint_files(cp.id)
            new_checkpoints = new_checkpoints[-self.MAX_CHECKPOINTS:]

        self._checkpoints = new_checkpoints

    def _delete_checkpoint_files(self, checkpoint_id: str):
        """Delete files associated with a checkpoint"""
        cp_dir = self.checkpoints_dir / checkpoint_id
        if cp_dir.exists():
            shutil.rmtree(cp_dir)

    # ==================== Conversation State ====================

    def update_conversation(self, messages: List[Dict[str, Any]], context: Dict[str, Any] = None):
        """Update current conversation state"""
        self._current_messages = messages.copy()
        self._current_context = context or {}

    def add_message(self, message: Dict[str, Any]):
        """Add a message to current conversation"""
        self._current_messages.append(message)

    # ==================== Checkpoint Creation ====================

    def create_checkpoint(
        self,
        name: str = "",
        description: str = "",
        auto: bool = False
    ) -> Checkpoint:
        """Create a new checkpoint"""
        checkpoint_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]

        # Capture code state
        code_state = self._capture_code_state()

        # Capture conversation state
        conv_state = ConversationState(
            messages=self._current_messages.copy(),
            context=self._current_context.copy(),
            token_count=sum(len(str(m.get("content", ""))) // 4 for m in self._current_messages)
        )

        # Create checkpoint
        checkpoint = Checkpoint(
            id=checkpoint_id,
            name=name or f"Checkpoint {len(self._checkpoints) + 1}",
            description=description,
            timestamp=datetime.now().isoformat(),
            conversation=conv_state,
            code=code_state,
            metadata={"auto": auto}
        )

        # Save file snapshots
        self._save_file_snapshots(checkpoint)

        # Add to list
        self._checkpoints.append(checkpoint)
        self._save_index()

        if not auto:
            self.console.print(f"[green]✓ Checkpoint created: {checkpoint.name}[/green]")

        return checkpoint

    def create_auto_checkpoint(self):
        """Create automatic checkpoint (called on each user prompt)"""
        return self.create_checkpoint(
            name=f"Auto {datetime.now().strftime('%H:%M:%S')}",
            description="Automatic checkpoint",
            auto=True
        )

    def _capture_code_state(self) -> CodeState:
        """Capture current code/file state"""
        code_state = CodeState(timestamp=datetime.now().isoformat())

        # Get git info
        code_state.git_commit = self._get_git_commit()
        code_state.git_branch = self._get_git_branch()
        code_state.git_dirty = self._is_git_dirty()

        # Capture tracked files
        tracked_files = self._get_tracked_files()

        for file_path in tracked_files:
            full_path = self.project_dir / file_path

            if full_path.exists() and full_path.is_file():
                try:
                    content = full_path.read_bytes()
                    content_hash = hashlib.sha256(content).hexdigest()

                    snapshot = FileSnapshot(
                        path=file_path,
                        content_hash=content_hash,
                        exists=True,
                        content=content.decode('utf-8') if len(content) < self.MAX_FILE_SIZE else None
                    )

                    code_state.files[file_path] = snapshot

                except Exception:
                    pass

        return code_state

    def _save_file_snapshots(self, checkpoint: Checkpoint):
        """Save large file snapshots to disk"""
        cp_dir = self.checkpoints_dir / checkpoint.id
        cp_dir.mkdir(exist_ok=True)

        for path, snapshot in checkpoint.code.files.items():
            if snapshot.content is None and snapshot.exists:
                # Save large file
                full_path = self.project_dir / path
                if full_path.exists():
                    try:
                        dest_path = cp_dir / path.replace("/", "_").replace("\\", "_")
                        shutil.copy2(full_path, dest_path)
                    except Exception:
                        pass

    def _get_tracked_files(self) -> List[str]:
        """Get list of files to track"""
        files = []

        # If git repo, use git tracked files
        if self._is_git_repo():
            try:
                result = subprocess.run(
                    ["git", "ls-files"],
                    cwd=str(self.project_dir),
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
            except Exception:
                pass

        # If no git or no files, scan directory
        if not files:
            ignore_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build'}
            ignore_exts = {'.pyc', '.pyo', '.exe', '.dll', '.so', '.dylib'}

            for root, dirs, filenames in os.walk(self.project_dir):
                # Filter directories
                dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]

                for filename in filenames:
                    if any(filename.endswith(ext) for ext in ignore_exts):
                        continue

                    rel_path = os.path.relpath(os.path.join(root, filename), self.project_dir)
                    files.append(rel_path)

                    if len(files) >= 500:  # Limit
                        break

        return files[:500]

    # ==================== Git Helpers ====================

    def _is_git_repo(self) -> bool:
        """Check if project is a git repo"""
        return (self.project_dir / ".git").exists()

    def _get_git_commit(self) -> str:
        """Get current git commit hash"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()[:8] if result.returncode == 0 else ""
        except Exception:
            return ""

    def _get_git_branch(self) -> str:
        """Get current git branch"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""

    def _is_git_dirty(self) -> bool:
        """Check if git working directory is dirty"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=5
            )
            return bool(result.stdout.strip()) if result.returncode == 0 else False
        except Exception:
            return False

    # ==================== Rewind ====================

    def rewind(
        self,
        checkpoint_id: str = None,
        mode: RewindMode = RewindMode.BOTH,
        confirm: bool = True
    ) -> bool:
        """Rewind to a checkpoint"""
        # Find checkpoint
        if checkpoint_id:
            checkpoint = self._find_checkpoint(checkpoint_id)
        else:
            # Use previous checkpoint
            if len(self._checkpoints) < 2:
                self.console.print("[yellow]No previous checkpoint available[/yellow]")
                return False
            checkpoint = self._checkpoints[-2]

        if not checkpoint:
            self.console.print(f"[red]Checkpoint not found: {checkpoint_id}[/red]")
            return False

        # Confirm
        if confirm:
            self.console.print(f"\n[bold]Rewind to: {checkpoint.name}[/bold]")
            self.console.print(f"[dim]Created: {checkpoint.timestamp}[/dim]")
            self.console.print(f"[dim]Mode: {mode.value}[/dim]\n")

            if mode in (RewindMode.CODE_ONLY, RewindMode.BOTH):
                self.console.print("[yellow]Warning: This will modify files in your project[/yellow]")

            if not Confirm.ask("Proceed with rewind?"):
                return False

        # Perform rewind
        success = True

        if mode in (RewindMode.CONVERSATION_ONLY, RewindMode.BOTH):
            self._rewind_conversation(checkpoint)
            self.console.print("[green]✓ Conversation rewound[/green]")

        if mode in (RewindMode.CODE_ONLY, RewindMode.BOTH):
            if self._rewind_code(checkpoint):
                self.console.print("[green]✓ Code rewound[/green]")
            else:
                self.console.print("[red]✗ Failed to rewind code[/red]")
                success = False

        return success

    def _find_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Find checkpoint by ID or partial ID"""
        for cp in self._checkpoints:
            if cp.id == checkpoint_id or cp.id.startswith(checkpoint_id):
                return cp
        return None

    def _rewind_conversation(self, checkpoint: Checkpoint):
        """Rewind conversation state"""
        self._current_messages = checkpoint.conversation.messages.copy()
        self._current_context = checkpoint.conversation.context.copy()

    def _rewind_code(self, checkpoint: Checkpoint) -> bool:
        """Rewind code/file state"""
        try:
            # If we have a git commit, try to use git
            if checkpoint.code.git_commit and self._is_git_repo():
                # Create a backup branch first
                backup_branch = f"bharatbuild-backup-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                subprocess.run(
                    ["git", "branch", backup_branch],
                    cwd=str(self.project_dir),
                    capture_output=True,
                    timeout=10
                )

            # Restore files
            cp_dir = self.checkpoints_dir / checkpoint.id

            for path, snapshot in checkpoint.code.files.items():
                full_path = self.project_dir / path

                if not snapshot.exists:
                    # File should not exist
                    if full_path.exists():
                        full_path.unlink()
                    continue

                # Restore file
                if snapshot.content:
                    # Content stored inline
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(snapshot.content)
                else:
                    # Content stored in checkpoint directory
                    stored_path = cp_dir / path.replace("/", "_").replace("\\", "_")
                    if stored_path.exists():
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(stored_path, full_path)

            return True

        except Exception as e:
            self.console.print(f"[red]Error rewinding code: {e}[/red]")
            return False

    def rewind_last(self, mode: RewindMode = RewindMode.BOTH) -> bool:
        """Rewind to the last checkpoint"""
        return self.rewind(mode=mode)

    # ==================== Display ====================

    def list_checkpoints(self, limit: int = 20):
        """List all checkpoints"""
        if not self._checkpoints:
            self.console.print("[dim]No checkpoints available[/dim]")
            return

        table = Table(title="Checkpoints", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim", width=12)
        table.add_column("Name")
        table.add_column("Time")
        table.add_column("Messages", justify="right")
        table.add_column("Files", justify="right")
        table.add_column("Git")

        for cp in reversed(self._checkpoints[-limit:]):
            # Format time
            try:
                dt = datetime.fromisoformat(cp.timestamp)
                time_str = dt.strftime("%m/%d %H:%M")
            except Exception:
                time_str = cp.timestamp[:16]

            # Git info
            git_info = ""
            if cp.code.git_commit:
                git_info = f"{cp.code.git_branch}@{cp.code.git_commit}"
                if cp.code.git_dirty:
                    git_info += "*"

            # Auto indicator
            name = cp.name
            if cp.metadata.get("auto"):
                name = f"[dim]{name}[/dim]"

            table.add_row(
                cp.id[:10],
                name,
                time_str,
                str(len(cp.conversation.messages)),
                str(len(cp.code.files)),
                git_info or "[dim]-[/dim]"
            )

        self.console.print(table)
        self.console.print(f"\n[dim]Total: {len(self._checkpoints)} checkpoints[/dim]")

    def show_checkpoint(self, checkpoint_id: str):
        """Show checkpoint details"""
        checkpoint = self._find_checkpoint(checkpoint_id)

        if not checkpoint:
            self.console.print(f"[red]Checkpoint not found: {checkpoint_id}[/red]")
            return

        content_lines = []
        content_lines.append(f"[bold]ID:[/bold] {checkpoint.id}")
        content_lines.append(f"[bold]Name:[/bold] {checkpoint.name}")
        content_lines.append(f"[bold]Description:[/bold] {checkpoint.description or 'None'}")
        content_lines.append(f"[bold]Created:[/bold] {checkpoint.timestamp}")
        content_lines.append("")

        content_lines.append("[bold]Conversation:[/bold]")
        content_lines.append(f"  Messages: {len(checkpoint.conversation.messages)}")
        content_lines.append(f"  Tokens: ~{checkpoint.conversation.token_count}")
        content_lines.append("")

        content_lines.append("[bold]Code State:[/bold]")
        content_lines.append(f"  Files tracked: {len(checkpoint.code.files)}")

        if checkpoint.code.git_commit:
            content_lines.append(f"  Git commit: {checkpoint.code.git_commit}")
            content_lines.append(f"  Git branch: {checkpoint.code.git_branch}")
            content_lines.append(f"  Dirty: {'Yes' if checkpoint.code.git_dirty else 'No'}")

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title=f"[bold cyan]Checkpoint: {checkpoint.name}[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

    def show_diff(self, checkpoint_id: str):
        """Show diff between checkpoint and current state"""
        checkpoint = self._find_checkpoint(checkpoint_id)

        if not checkpoint:
            self.console.print(f"[red]Checkpoint not found: {checkpoint_id}[/red]")
            return

        self.console.print(f"\n[bold]Changes since checkpoint: {checkpoint.name}[/bold]\n")

        changes = 0

        for path, snapshot in checkpoint.code.files.items():
            full_path = self.project_dir / path

            if not full_path.exists():
                if snapshot.exists:
                    self.console.print(f"[red]- Deleted: {path}[/red]")
                    changes += 1
                continue

            if not snapshot.exists:
                self.console.print(f"[green]+ Added: {path}[/green]")
                changes += 1
                continue

            # Compare hash
            try:
                current_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
                if current_hash != snapshot.content_hash:
                    self.console.print(f"[yellow]~ Modified: {path}[/yellow]")
                    changes += 1
            except Exception:
                pass

        if changes == 0:
            self.console.print("[dim]No changes since checkpoint[/dim]")
        else:
            self.console.print(f"\n[dim]{changes} file(s) changed[/dim]")

    def show_help(self):
        """Show checkpoint help"""
        help_text = """
[bold cyan]Checkpoint Commands[/bold cyan]

Save and restore conversation and code states.

[bold]Commands:[/bold]
  [green]/checkpoint[/green]          Create new checkpoint
  [green]/checkpoints[/green]         List all checkpoints
  [green]/checkpoint show <id>[/green] Show checkpoint details
  [green]/rewind[/green]              Rewind to last checkpoint
  [green]/rewind <id>[/green]         Rewind to specific checkpoint
  [green]/rewind --code[/green]       Rewind code only
  [green]/rewind --conv[/green]       Rewind conversation only
  [green]/diff <id>[/green]           Show changes since checkpoint

[bold]Keyboard:[/bold]
  Esc Esc             Quick rewind menu

[bold]Auto-Checkpoints:[/bold]
  Checkpoints are created automatically on each prompt.
  Retained for 30 days, max 100 checkpoints.

[bold]Rewind Modes:[/bold]
  • conversation - Rewind conversation only
  • code         - Rewind files only
  • both         - Rewind both (default)

[bold]Examples:[/bold]
  /checkpoint "Before refactoring"
  /rewind 20240101_12
  /rewind --code
  /diff 20240101_12
"""
        self.console.print(help_text)

    def get_conversation_state(self) -> Tuple[List[Dict], Dict]:
        """Get current conversation state"""
        return self._current_messages.copy(), self._current_context.copy()
