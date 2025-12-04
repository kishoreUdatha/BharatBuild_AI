"""
BharatBuild CLI Conversation Branching

Enables branching conversation history:
  /branch create feature-exploration
  /branch list
  /branch switch main
  /branch merge feature-exploration
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.text import Text


@dataclass
class Message:
    """A conversation message"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Branch:
    """A conversation branch"""
    name: str
    parent: Optional[str]  # Parent branch name
    fork_point: int  # Message index where branch was created
    messages: List[Message] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    description: str = ""
    is_active: bool = True


@dataclass
class ConversationTree:
    """The full conversation tree with all branches"""
    branches: Dict[str, Branch] = field(default_factory=dict)
    current_branch: str = "main"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class BranchManager:
    """
    Manages conversation branching.

    Usage:
        manager = BranchManager(console, state_dir)

        # Create a branch
        manager.create_branch("experiment")

        # Switch branches
        manager.switch_branch("experiment")

        # Add message to current branch
        manager.add_message(Message(role="user", content="..."))

        # Merge branches
        manager.merge_branch("experiment", "main")
    """

    def __init__(
        self,
        console: Console,
        state_dir: Optional[Path] = None,
        project_id: Optional[str] = None
    ):
        self.console = console
        self.state_dir = state_dir or (Path.home() / ".bharatbuild" / "branches")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.project_id = project_id or "default"

        # Load or create tree
        self.tree = self._load_tree()

    def _get_state_file(self) -> Path:
        """Get state file path"""
        return self.state_dir / f"{self.project_id}.json"

    def _load_tree(self) -> ConversationTree:
        """Load conversation tree from disk"""
        state_file = self._get_state_file()

        if state_file.exists():
            try:
                with open(state_file) as f:
                    data = json.load(f)

                tree = ConversationTree(
                    current_branch=data.get("current_branch", "main"),
                    created_at=data.get("created_at", datetime.now().isoformat())
                )

                for name, branch_data in data.get("branches", {}).items():
                    messages = [
                        Message(
                            role=m["role"],
                            content=m["content"],
                            timestamp=m.get("timestamp", ""),
                            metadata=m.get("metadata", {})
                        )
                        for m in branch_data.get("messages", [])
                    ]

                    tree.branches[name] = Branch(
                        name=name,
                        parent=branch_data.get("parent"),
                        fork_point=branch_data.get("fork_point", 0),
                        messages=messages,
                        created_at=branch_data.get("created_at", ""),
                        description=branch_data.get("description", ""),
                        is_active=branch_data.get("is_active", True)
                    )

                return tree

            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load branch state: {e}[/yellow]")

        # Create default tree with main branch
        tree = ConversationTree()
        tree.branches["main"] = Branch(
            name="main",
            parent=None,
            fork_point=0,
            description="Main conversation"
        )
        return tree

    def _save_tree(self):
        """Save conversation tree to disk"""
        state_file = self._get_state_file()

        try:
            branches_data = {}
            for name, branch in self.tree.branches.items():
                branches_data[name] = {
                    "parent": branch.parent,
                    "fork_point": branch.fork_point,
                    "messages": [
                        {
                            "role": m.role,
                            "content": m.content,
                            "timestamp": m.timestamp,
                            "metadata": m.metadata
                        }
                        for m in branch.messages
                    ],
                    "created_at": branch.created_at,
                    "description": branch.description,
                    "is_active": branch.is_active
                }

            data = {
                "branches": branches_data,
                "current_branch": self.tree.current_branch,
                "created_at": self.tree.created_at
            }

            with open(state_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not save branch state: {e}[/yellow]")

    # ==================== Branch Operations ====================

    def create_branch(
        self,
        name: str,
        description: str = "",
        from_branch: Optional[str] = None
    ) -> bool:
        """
        Create a new branch from current or specified branch.

        The new branch inherits messages up to the current point.
        """
        if name in self.tree.branches:
            self.console.print(f"[red]Branch '{name}' already exists[/red]")
            return False

        # Validate name
        if not self._is_valid_branch_name(name):
            self.console.print("[red]Invalid branch name. Use alphanumeric, dashes, underscores.[/red]")
            return False

        parent_name = from_branch or self.tree.current_branch
        parent = self.tree.branches.get(parent_name)

        if not parent:
            self.console.print(f"[red]Parent branch '{parent_name}' not found[/red]")
            return False

        # Create branch with inherited messages
        new_branch = Branch(
            name=name,
            parent=parent_name,
            fork_point=len(parent.messages),
            messages=parent.messages.copy(),
            description=description or f"Branched from {parent_name}"
        )

        self.tree.branches[name] = new_branch
        self._save_tree()

        self.console.print(f"[green]✓ Created branch '{name}' from '{parent_name}'[/green]")
        return True

    def switch_branch(self, name: str) -> bool:
        """Switch to a different branch"""
        if name not in self.tree.branches:
            self.console.print(f"[red]Branch '{name}' not found[/red]")
            return False

        old_branch = self.tree.current_branch
        self.tree.current_branch = name
        self._save_tree()

        branch = self.tree.branches[name]
        self.console.print(f"[green]✓ Switched to branch '{name}'[/green]")
        self.console.print(f"[dim]  {len(branch.messages)} messages in history[/dim]")

        return True

    def delete_branch(self, name: str, force: bool = False) -> bool:
        """Delete a branch"""
        if name == "main":
            self.console.print("[red]Cannot delete main branch[/red]")
            return False

        if name not in self.tree.branches:
            self.console.print(f"[red]Branch '{name}' not found[/red]")
            return False

        if name == self.tree.current_branch:
            self.console.print("[red]Cannot delete current branch. Switch first.[/red]")
            return False

        # Check for child branches
        children = [b.name for b in self.tree.branches.values() if b.parent == name]
        if children and not force:
            self.console.print(f"[red]Branch has children: {', '.join(children)}[/red]")
            self.console.print("[dim]Use --force to delete anyway[/dim]")
            return False

        # Reparent children
        if children:
            parent = self.tree.branches[name].parent
            for child_name in children:
                self.tree.branches[child_name].parent = parent

        del self.tree.branches[name]
        self._save_tree()

        self.console.print(f"[green]✓ Deleted branch '{name}'[/green]")
        return True

    def merge_branch(
        self,
        source: str,
        target: Optional[str] = None,
        strategy: str = "append"
    ) -> bool:
        """
        Merge one branch into another.

        Strategies:
        - append: Add source messages after target messages
        - replace: Replace target messages from fork point
        """
        target = target or self.tree.current_branch

        if source not in self.tree.branches:
            self.console.print(f"[red]Source branch '{source}' not found[/red]")
            return False

        if target not in self.tree.branches:
            self.console.print(f"[red]Target branch '{target}' not found[/red]")
            return False

        source_branch = self.tree.branches[source]
        target_branch = self.tree.branches[target]

        if strategy == "append":
            # Find new messages in source (after fork point)
            new_messages = source_branch.messages[source_branch.fork_point:]
            target_branch.messages.extend(new_messages)
            self.console.print(f"[green]✓ Appended {len(new_messages)} messages from '{source}' to '{target}'[/green]")

        elif strategy == "replace":
            # Replace from fork point
            fork_point = source_branch.fork_point
            target_branch.messages = (
                target_branch.messages[:fork_point] +
                source_branch.messages[fork_point:]
            )
            self.console.print(f"[green]✓ Merged '{source}' into '{target}' (replace)[/green]")

        self._save_tree()
        return True

    def rename_branch(self, old_name: str, new_name: str) -> bool:
        """Rename a branch"""
        if old_name == "main":
            self.console.print("[red]Cannot rename main branch[/red]")
            return False

        if old_name not in self.tree.branches:
            self.console.print(f"[red]Branch '{old_name}' not found[/red]")
            return False

        if new_name in self.tree.branches:
            self.console.print(f"[red]Branch '{new_name}' already exists[/red]")
            return False

        if not self._is_valid_branch_name(new_name):
            self.console.print("[red]Invalid branch name[/red]")
            return False

        # Update branch
        branch = self.tree.branches.pop(old_name)
        branch.name = new_name
        self.tree.branches[new_name] = branch

        # Update children's parent references
        for b in self.tree.branches.values():
            if b.parent == old_name:
                b.parent = new_name

        # Update current if needed
        if self.tree.current_branch == old_name:
            self.tree.current_branch = new_name

        self._save_tree()
        self.console.print(f"[green]✓ Renamed '{old_name}' to '{new_name}'[/green]")
        return True

    # ==================== Message Operations ====================

    def add_message(self, message: Message):
        """Add a message to the current branch"""
        branch = self.tree.branches[self.tree.current_branch]
        branch.messages.append(message)
        self._save_tree()

    def get_messages(self, branch_name: Optional[str] = None) -> List[Message]:
        """Get messages from a branch"""
        name = branch_name or self.tree.current_branch
        if name in self.tree.branches:
            return self.tree.branches[name].messages
        return []

    def get_current_branch(self) -> Branch:
        """Get current branch"""
        return self.tree.branches[self.tree.current_branch]

    def rewind(self, count: int = 1) -> bool:
        """Remove last N messages from current branch"""
        branch = self.get_current_branch()

        if count >= len(branch.messages):
            self.console.print("[red]Cannot rewind beyond start of conversation[/red]")
            return False

        removed = branch.messages[-count:]
        branch.messages = branch.messages[:-count]
        self._save_tree()

        self.console.print(f"[green]✓ Removed {count} message(s)[/green]")
        return True

    # ==================== Display ====================

    def list_branches(self):
        """List all branches"""
        table = Table(title="Conversation Branches", show_header=True, header_style="bold cyan")
        table.add_column("Branch", style="cyan")
        table.add_column("Parent")
        table.add_column("Messages", justify="right")
        table.add_column("Created")
        table.add_column("Description")

        for name, branch in self.tree.branches.items():
            # Highlight current branch
            if name == self.tree.current_branch:
                name_display = f"[bold green]* {name}[/bold green]"
            else:
                name_display = f"  {name}"

            # Format date
            try:
                created = datetime.fromisoformat(branch.created_at)
                created_str = created.strftime("%Y-%m-%d %H:%M")
            except Exception:
                created_str = branch.created_at[:16]

            table.add_row(
                name_display,
                branch.parent or "-",
                str(len(branch.messages)),
                created_str,
                branch.description[:30] + "..." if len(branch.description) > 30 else branch.description
            )

        self.console.print(table)

    def show_tree(self):
        """Show branch tree visualization"""
        tree = Tree(f"[bold cyan]📂 Conversation Tree[/bold cyan]")

        def add_branch_to_tree(parent_tree, branch_name):
            branch = self.tree.branches[branch_name]

            # Build label
            if branch_name == self.tree.current_branch:
                label = f"[bold green]* {branch_name}[/bold green] ({len(branch.messages)} msgs)"
            else:
                label = f"{branch_name} ({len(branch.messages)} msgs)"

            if branch.description:
                label += f" [dim]- {branch.description[:20]}[/dim]"

            node = parent_tree.add(label)

            # Add children
            for name, b in self.tree.branches.items():
                if b.parent == branch_name:
                    add_branch_to_tree(node, name)

        # Start with main branch
        add_branch_to_tree(tree, "main")

        self.console.print(tree)

    def show_diff(self, branch1: str, branch2: str):
        """Show difference between two branches"""
        if branch1 not in self.tree.branches:
            self.console.print(f"[red]Branch '{branch1}' not found[/red]")
            return

        if branch2 not in self.tree.branches:
            self.console.print(f"[red]Branch '{branch2}' not found[/red]")
            return

        b1 = self.tree.branches[branch1]
        b2 = self.tree.branches[branch2]

        self.console.print(f"\n[bold]Comparing '{branch1}' vs '{branch2}'[/bold]")
        self.console.print(f"[dim]{len(b1.messages)} vs {len(b2.messages)} messages[/dim]\n")

        # Find common ancestor point
        common = min(len(b1.messages), len(b2.messages))
        for i in range(common):
            if b1.messages[i].content != b2.messages[i].content:
                common = i
                break

        self.console.print(f"[cyan]Common messages:[/cyan] {common}")
        self.console.print(f"[green]Only in {branch1}:[/green] {len(b1.messages) - common}")
        self.console.print(f"[yellow]Only in {branch2}:[/yellow] {len(b2.messages) - common}")

    # ==================== Utilities ====================

    def _is_valid_branch_name(self, name: str) -> bool:
        """Check if branch name is valid"""
        import re
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', name))

    def get_branch_count(self) -> int:
        """Get total number of branches"""
        return len(self.tree.branches)

    def get_total_messages(self) -> int:
        """Get total messages across all branches"""
        return sum(len(b.messages) for b in self.tree.branches.values())

    def export_branch(self, name: str, path: Path) -> bool:
        """Export a branch to a file"""
        if name not in self.tree.branches:
            self.console.print(f"[red]Branch '{name}' not found[/red]")
            return False

        branch = self.tree.branches[name]

        try:
            with open(path, 'w') as f:
                json.dump({
                    "branch": name,
                    "messages": [
                        {
                            "role": m.role,
                            "content": m.content,
                            "timestamp": m.timestamp
                        }
                        for m in branch.messages
                    ],
                    "exported_at": datetime.now().isoformat()
                }, f, indent=2)

            self.console.print(f"[green]✓ Exported '{name}' to {path}[/green]")
            return True

        except Exception as e:
            self.console.print(f"[red]Export failed: {e}[/red]")
            return False

    def import_branch(self, path: Path, name: Optional[str] = None) -> bool:
        """Import a branch from a file"""
        try:
            with open(path) as f:
                data = json.load(f)

            branch_name = name or data.get("branch", "imported")

            if branch_name in self.tree.branches:
                self.console.print(f"[red]Branch '{branch_name}' already exists[/red]")
                return False

            messages = [
                Message(
                    role=m["role"],
                    content=m["content"],
                    timestamp=m.get("timestamp", "")
                )
                for m in data.get("messages", [])
            ]

            self.tree.branches[branch_name] = Branch(
                name=branch_name,
                parent="main",
                fork_point=0,
                messages=messages,
                description=f"Imported from {path.name}"
            )

            self._save_tree()
            self.console.print(f"[green]✓ Imported {len(messages)} messages as '{branch_name}'[/green]")
            return True

        except Exception as e:
            self.console.print(f"[red]Import failed: {e}[/red]")
            return False
