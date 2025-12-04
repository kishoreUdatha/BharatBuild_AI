"""
BharatBuild CLI Undo/Redo System

Provides file-level undo/redo operations:
  > /undo          # Revert last file change
  > /redo          # Redo reverted change
  > /history       # Show change history
"""

import os
import json
import shutil
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class OperationType(str, Enum):
    """Types of file operations"""
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    RENAME = "rename"
    MOVE = "move"


@dataclass
class FileSnapshot:
    """Snapshot of a file's content"""
    path: str
    content: Optional[str]
    exists: bool
    hash: Optional[str] = None
    size: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def compute_hash(self) -> str:
        """Compute hash of content"""
        if self.content:
            return hashlib.md5(self.content.encode()).hexdigest()[:8]
        return ""


@dataclass
class FileOperation:
    """A file operation that can be undone/redone"""
    operation_type: OperationType
    path: str
    before: Optional[FileSnapshot]
    after: Optional[FileSnapshot]
    description: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    id: str = field(default_factory=lambda: hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8])

    # For rename/move operations
    old_path: Optional[str] = None
    new_path: Optional[str] = None


@dataclass
class UndoRedoState:
    """State of the undo/redo system"""
    history: List[FileOperation] = field(default_factory=list)
    undo_stack: List[str] = field(default_factory=list)  # Operation IDs
    redo_stack: List[str] = field(default_factory=list)  # Operation IDs
    max_history: int = 100


class UndoRedoManager:
    """
    Manages undo/redo operations for file changes.

    Usage:
        manager = UndoRedoManager(working_dir, console)

        # Record a change
        manager.record_change(path, old_content, new_content, "Modified config")

        # Undo last change
        manager.undo()

        # Redo undone change
        manager.redo()

        # Show history
        manager.show_history()
    """

    def __init__(
        self,
        working_dir: Path,
        console: Console,
        state_dir: Optional[Path] = None,
        max_history: int = 100
    ):
        self.working_dir = working_dir
        self.console = console
        self.state_dir = state_dir or (Path.home() / ".bharatbuild" / "undo")
        self.max_history = max_history

        # Ensure state directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Load state
        self.state = self._load_state()

    def _load_state(self) -> UndoRedoState:
        """Load state from disk"""
        state_file = self.state_dir / f"{self._get_project_id()}.json"

        if state_file.exists():
            try:
                with open(state_file) as f:
                    data = json.load(f)

                state = UndoRedoState(max_history=self.max_history)
                state.undo_stack = data.get("undo_stack", [])
                state.redo_stack = data.get("redo_stack", [])

                # Reconstruct history
                for op_data in data.get("history", []):
                    before = None
                    after = None

                    if op_data.get("before"):
                        before = FileSnapshot(**op_data["before"])
                    if op_data.get("after"):
                        after = FileSnapshot(**op_data["after"])

                    op = FileOperation(
                        operation_type=OperationType(op_data["operation_type"]),
                        path=op_data["path"],
                        before=before,
                        after=after,
                        description=op_data["description"],
                        timestamp=op_data["timestamp"],
                        id=op_data["id"],
                        old_path=op_data.get("old_path"),
                        new_path=op_data.get("new_path")
                    )
                    state.history.append(op)

                return state

            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load undo history: {e}[/yellow]")

        return UndoRedoState(max_history=self.max_history)

    def _save_state(self):
        """Save state to disk"""
        state_file = self.state_dir / f"{self._get_project_id()}.json"

        try:
            history_data = []
            for op in self.state.history:
                op_data = {
                    "operation_type": op.operation_type.value,
                    "path": op.path,
                    "before": asdict(op.before) if op.before else None,
                    "after": asdict(op.after) if op.after else None,
                    "description": op.description,
                    "timestamp": op.timestamp,
                    "id": op.id,
                    "old_path": op.old_path,
                    "new_path": op.new_path
                }
                history_data.append(op_data)

            data = {
                "history": history_data,
                "undo_stack": self.state.undo_stack,
                "redo_stack": self.state.redo_stack
            }

            with open(state_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not save undo history: {e}[/yellow]")

    def _get_project_id(self) -> str:
        """Get unique project identifier"""
        return hashlib.md5(str(self.working_dir).encode()).hexdigest()[:12]

    def _create_snapshot(self, path: str) -> FileSnapshot:
        """Create a snapshot of a file"""
        full_path = self.working_dir / path

        if full_path.exists() and full_path.is_file():
            try:
                content = full_path.read_text(errors='replace')
                snapshot = FileSnapshot(
                    path=path,
                    content=content,
                    exists=True,
                    size=len(content)
                )
                snapshot.hash = snapshot.compute_hash()
                return snapshot
            except Exception:
                pass

        return FileSnapshot(
            path=path,
            content=None,
            exists=False
        )

    def _restore_snapshot(self, snapshot: FileSnapshot) -> bool:
        """Restore a file from a snapshot"""
        full_path = self.working_dir / snapshot.path

        try:
            if snapshot.exists and snapshot.content is not None:
                # Restore file content
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(snapshot.content)
                return True
            elif not snapshot.exists:
                # Delete file if it shouldn't exist
                if full_path.exists():
                    full_path.unlink()
                return True

        except Exception as e:
            self.console.print(f"[red]Error restoring {snapshot.path}: {e}[/red]")

        return False

    def record_create(self, path: str, content: str, description: str = ""):
        """Record file creation"""
        after = FileSnapshot(
            path=path,
            content=content,
            exists=True,
            size=len(content)
        )
        after.hash = after.compute_hash()

        before = FileSnapshot(
            path=path,
            content=None,
            exists=False
        )

        op = FileOperation(
            operation_type=OperationType.CREATE,
            path=path,
            before=before,
            after=after,
            description=description or f"Created {path}"
        )

        self._add_operation(op)

    def record_modify(
        self,
        path: str,
        old_content: str,
        new_content: str,
        description: str = ""
    ):
        """Record file modification"""
        before = FileSnapshot(
            path=path,
            content=old_content,
            exists=True,
            size=len(old_content)
        )
        before.hash = before.compute_hash()

        after = FileSnapshot(
            path=path,
            content=new_content,
            exists=True,
            size=len(new_content)
        )
        after.hash = after.compute_hash()

        op = FileOperation(
            operation_type=OperationType.MODIFY,
            path=path,
            before=before,
            after=after,
            description=description or f"Modified {path}"
        )

        self._add_operation(op)

    def record_delete(self, path: str, content: str, description: str = ""):
        """Record file deletion"""
        before = FileSnapshot(
            path=path,
            content=content,
            exists=True,
            size=len(content)
        )
        before.hash = before.compute_hash()

        after = FileSnapshot(
            path=path,
            content=None,
            exists=False
        )

        op = FileOperation(
            operation_type=OperationType.DELETE,
            path=path,
            before=before,
            after=after,
            description=description or f"Deleted {path}"
        )

        self._add_operation(op)

    def record_rename(
        self,
        old_path: str,
        new_path: str,
        content: str,
        description: str = ""
    ):
        """Record file rename/move"""
        before = FileSnapshot(
            path=old_path,
            content=content,
            exists=True,
            size=len(content)
        )
        before.hash = before.compute_hash()

        after = FileSnapshot(
            path=new_path,
            content=content,
            exists=True,
            size=len(content)
        )
        after.hash = after.compute_hash()

        op = FileOperation(
            operation_type=OperationType.RENAME,
            path=new_path,
            before=before,
            after=after,
            description=description or f"Renamed {old_path} to {new_path}",
            old_path=old_path,
            new_path=new_path
        )

        self._add_operation(op)

    def record_change(
        self,
        path: str,
        old_content: Optional[str],
        new_content: Optional[str],
        description: str = ""
    ):
        """Record a generic change (auto-detects type)"""
        if old_content is None and new_content is not None:
            self.record_create(path, new_content, description)
        elif old_content is not None and new_content is None:
            self.record_delete(path, old_content, description)
        elif old_content is not None and new_content is not None:
            self.record_modify(path, old_content, new_content, description)

    def _add_operation(self, op: FileOperation):
        """Add operation to history"""
        self.state.history.append(op)
        self.state.undo_stack.append(op.id)
        self.state.redo_stack.clear()  # Clear redo stack on new operation

        # Trim history if needed
        while len(self.state.history) > self.max_history:
            oldest = self.state.history.pop(0)
            if oldest.id in self.state.undo_stack:
                self.state.undo_stack.remove(oldest.id)

        self._save_state()

    def _get_operation_by_id(self, op_id: str) -> Optional[FileOperation]:
        """Get operation by ID"""
        for op in self.state.history:
            if op.id == op_id:
                return op
        return None

    def can_undo(self) -> bool:
        """Check if undo is available"""
        return len(self.state.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available"""
        return len(self.state.redo_stack) > 0

    def undo(self) -> Optional[FileOperation]:
        """
        Undo the last operation.

        Returns the undone operation, or None if nothing to undo.
        """
        if not self.can_undo():
            self.console.print("[yellow]Nothing to undo[/yellow]")
            return None

        op_id = self.state.undo_stack.pop()
        op = self._get_operation_by_id(op_id)

        if not op:
            self.console.print("[red]Error: Operation not found in history[/red]")
            return None

        # Restore the "before" state
        if op.operation_type == OperationType.RENAME:
            # For rename, restore old path and delete new path
            if op.before:
                self._restore_snapshot(op.before)
            # Delete new path
            new_path = self.working_dir / op.new_path
            if new_path.exists():
                new_path.unlink()
        elif op.before:
            self._restore_snapshot(op.before)

        # Add to redo stack
        self.state.redo_stack.append(op_id)
        self._save_state()

        self.console.print(f"[green]✓ Undone:[/green] {op.description}")
        return op

    def redo(self) -> Optional[FileOperation]:
        """
        Redo the last undone operation.

        Returns the redone operation, or None if nothing to redo.
        """
        if not self.can_redo():
            self.console.print("[yellow]Nothing to redo[/yellow]")
            return None

        op_id = self.state.redo_stack.pop()
        op = self._get_operation_by_id(op_id)

        if not op:
            self.console.print("[red]Error: Operation not found in history[/red]")
            return None

        # Restore the "after" state
        if op.operation_type == OperationType.RENAME:
            # For rename, delete old path and restore new path
            old_path = self.working_dir / op.old_path
            if old_path.exists():
                old_path.unlink()
            if op.after:
                self._restore_snapshot(op.after)
        elif op.after:
            self._restore_snapshot(op.after)

        # Add back to undo stack
        self.state.undo_stack.append(op_id)
        self._save_state()

        self.console.print(f"[green]✓ Redone:[/green] {op.description}")
        return op

    def show_history(self, limit: int = 20):
        """Show operation history"""
        if not self.state.history:
            self.console.print("[dim]No operations in history[/dim]")
            return

        table = Table(title="Operation History", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Type", width=8)
        table.add_column("Path", style="cyan")
        table.add_column("Description")
        table.add_column("Status", width=8)

        # Show most recent first
        history = list(reversed(self.state.history[-limit:]))

        for i, op in enumerate(history, 1):
            # Type with color
            type_colors = {
                OperationType.CREATE: "green",
                OperationType.MODIFY: "yellow",
                OperationType.DELETE: "red",
                OperationType.RENAME: "blue",
            }
            type_color = type_colors.get(op.operation_type, "white")
            type_text = f"[{type_color}]{op.operation_type.value}[/{type_color}]"

            # Status
            if op.id in self.state.undo_stack:
                status = "[green]active[/green]"
            elif op.id in self.state.redo_stack:
                status = "[yellow]undone[/yellow]"
            else:
                status = "[dim]---[/dim]"

            table.add_row(
                str(i),
                type_text,
                op.path[:40],
                op.description[:30],
                status
            )

        self.console.print(table)

        # Show undo/redo status
        self.console.print()
        self.console.print(f"[dim]Undo available: {len(self.state.undo_stack)} | Redo available: {len(self.state.redo_stack)}[/dim]")

    def show_diff(self, op_id: Optional[str] = None):
        """Show diff for an operation"""
        if op_id:
            op = self._get_operation_by_id(op_id)
        elif self.state.undo_stack:
            op = self._get_operation_by_id(self.state.undo_stack[-1])
        else:
            self.console.print("[yellow]No operation to show diff for[/yellow]")
            return

        if not op:
            self.console.print("[red]Operation not found[/red]")
            return

        self.console.print(f"\n[bold]Diff for: {op.description}[/bold]")
        self.console.print(f"[dim]Path: {op.path}[/dim]")
        self.console.print()

        if op.before and op.after and op.before.content and op.after.content:
            import difflib

            diff = difflib.unified_diff(
                op.before.content.splitlines(keepends=True),
                op.after.content.splitlines(keepends=True),
                fromfile=f"a/{op.path}",
                tofile=f"b/{op.path}"
            )

            for line in diff:
                if line.startswith('+') and not line.startswith('+++'):
                    self.console.print(f"[green]{line.rstrip()}[/green]")
                elif line.startswith('-') and not line.startswith('---'):
                    self.console.print(f"[red]{line.rstrip()}[/red]")
                elif line.startswith('@@'):
                    self.console.print(f"[cyan]{line.rstrip()}[/cyan]")
                else:
                    self.console.print(line.rstrip())
        else:
            if op.operation_type == OperationType.CREATE:
                self.console.print("[green]+ (new file created)[/green]")
            elif op.operation_type == OperationType.DELETE:
                self.console.print("[red]- (file deleted)[/red]")

    def clear_history(self):
        """Clear all history"""
        self.state = UndoRedoState(max_history=self.max_history)
        self._save_state()
        self.console.print("[green]✓ History cleared[/green]")

    def get_pending_undo_count(self) -> int:
        """Get number of undoable operations"""
        return len(self.state.undo_stack)

    def get_pending_redo_count(self) -> int:
        """Get number of redoable operations"""
        return len(self.state.redo_stack)
