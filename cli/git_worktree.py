"""
BharatBuild CLI Git Worktree Support

Manage multiple git worktrees for parallel development.

Usage:
  /worktree list        List worktrees
  /worktree add <name>  Create worktree
  /worktree switch <n>  Switch to worktree
  /worktree remove <n>  Remove worktree
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel


@dataclass
class Worktree:
    """Git worktree information"""
    path: Path
    branch: str
    commit: str
    is_main: bool = False
    is_current: bool = False
    is_bare: bool = False
    is_detached: bool = False
    is_locked: bool = False
    lock_reason: str = ""


class GitWorktreeManager:
    """
    Manages git worktrees for parallel development.

    Usage:
        manager = GitWorktreeManager(project_root, console)

        # List worktrees
        worktrees = manager.list_worktrees()

        # Create new worktree
        manager.create_worktree("feature-branch")

        # Switch to worktree
        manager.switch_worktree("feature-branch")
    """

    def __init__(self, project_root: Path, console: Console):
        self.project_root = project_root
        self.console = console
        self._git_root: Optional[Path] = None

    def _run_git(self, *args, cwd: Path = None) -> tuple:
        """Run git command and return (stdout, stderr, returncode)"""
        try:
            result = subprocess.run(
                ['git', *args],
                cwd=str(cwd or self.project_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode

        except subprocess.TimeoutExpired:
            return "", "Command timed out", 1
        except FileNotFoundError:
            return "", "Git not found", 1
        except Exception as e:
            return "", str(e), 1

    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository"""
        stdout, stderr, code = self._run_git('rev-parse', '--git-dir')
        return code == 0

    def get_git_root(self) -> Optional[Path]:
        """Get the root of the git repository"""
        if self._git_root:
            return self._git_root

        stdout, stderr, code = self._run_git('rev-parse', '--show-toplevel')
        if code == 0:
            self._git_root = Path(stdout)
            return self._git_root
        return None

    def get_current_branch(self) -> str:
        """Get current branch name"""
        stdout, stderr, code = self._run_git('branch', '--show-current')
        if code == 0 and stdout:
            return stdout
        return "HEAD"

    # ==================== Worktree Operations ====================

    def list_worktrees(self) -> List[Worktree]:
        """List all worktrees"""
        stdout, stderr, code = self._run_git('worktree', 'list', '--porcelain')

        if code != 0:
            return []

        worktrees = []
        current_wt = {}

        for line in stdout.split('\n'):
            line = line.strip()

            if not line:
                # End of current worktree entry
                if current_wt and 'path' in current_wt:
                    wt = Worktree(
                        path=Path(current_wt['path']),
                        branch=current_wt.get('branch', ''),
                        commit=current_wt.get('commit', ''),
                        is_main=len(worktrees) == 0,  # First is main
                        is_bare=current_wt.get('bare', False),
                        is_detached=current_wt.get('detached', False),
                        is_locked=current_wt.get('locked', False),
                        lock_reason=current_wt.get('lock_reason', '')
                    )

                    # Check if current
                    wt.is_current = wt.path == self.project_root

                    worktrees.append(wt)

                current_wt = {}
                continue

            if line.startswith('worktree '):
                current_wt['path'] = line[9:]
            elif line.startswith('HEAD '):
                current_wt['commit'] = line[5:][:8]  # Short hash
            elif line.startswith('branch '):
                # Format: refs/heads/branch-name
                branch = line[7:]
                if branch.startswith('refs/heads/'):
                    branch = branch[11:]
                current_wt['branch'] = branch
            elif line == 'bare':
                current_wt['bare'] = True
            elif line == 'detached':
                current_wt['detached'] = True
            elif line == 'locked':
                current_wt['locked'] = True
            elif line.startswith('locked '):
                current_wt['locked'] = True
                current_wt['lock_reason'] = line[7:]

        # Handle last entry
        if current_wt and 'path' in current_wt:
            wt = Worktree(
                path=Path(current_wt['path']),
                branch=current_wt.get('branch', ''),
                commit=current_wt.get('commit', ''),
                is_main=len(worktrees) == 0,
                is_bare=current_wt.get('bare', False),
                is_detached=current_wt.get('detached', False),
                is_locked=current_wt.get('locked', False),
                lock_reason=current_wt.get('lock_reason', '')
            )
            wt.is_current = wt.path == self.project_root
            worktrees.append(wt)

        return worktrees

    def create_worktree(
        self,
        branch: str,
        path: Optional[Path] = None,
        base_branch: str = "main",
        create_branch: bool = True
    ) -> bool:
        """
        Create a new worktree.

        Args:
            branch: Branch name for the worktree
            path: Path for worktree (default: ../{repo_name}_{branch})
            base_branch: Base branch to create from
            create_branch: Create new branch if doesn't exist
        """
        # Determine path
        if not path:
            repo_name = self.project_root.name
            path = self.project_root.parent / f"{repo_name}_{branch}"

        # Check if path exists
        if path.exists():
            self.console.print(f"[red]Path already exists: {path}[/red]")
            return False

        # Check if branch exists
        stdout, stderr, code = self._run_git('branch', '--list', branch)
        branch_exists = bool(stdout.strip())

        # Build command
        args = ['worktree', 'add']

        if create_branch and not branch_exists:
            args.extend(['-b', branch])
            args.append(str(path))
            args.append(base_branch)
        else:
            args.append(str(path))
            args.append(branch)

        stdout, stderr, code = self._run_git(*args)

        if code == 0:
            self.console.print(f"[green]✓ Created worktree: {path}[/green]")
            self.console.print(f"[dim]Branch: {branch}[/dim]")
            return True
        else:
            self.console.print(f"[red]Error creating worktree: {stderr}[/red]")
            return False

    def remove_worktree(self, path_or_branch: str, force: bool = False) -> bool:
        """Remove a worktree"""
        # Find worktree by path or branch
        worktrees = self.list_worktrees()
        target = None

        for wt in worktrees:
            if str(wt.path) == path_or_branch or wt.branch == path_or_branch:
                target = wt
                break

        if not target:
            self.console.print(f"[red]Worktree not found: {path_or_branch}[/red]")
            return False

        if target.is_main:
            self.console.print("[red]Cannot remove main worktree[/red]")
            return False

        if target.is_current:
            self.console.print("[red]Cannot remove current worktree[/red]")
            return False

        # Remove
        args = ['worktree', 'remove']
        if force:
            args.append('--force')
        args.append(str(target.path))

        stdout, stderr, code = self._run_git(*args)

        if code == 0:
            self.console.print(f"[green]✓ Removed worktree: {target.path}[/green]")
            return True
        else:
            self.console.print(f"[red]Error removing worktree: {stderr}[/red]")
            if "not clean" in stderr.lower():
                self.console.print("[dim]Use --force to remove with uncommitted changes[/dim]")
            return False

    def switch_worktree(self, path_or_branch: str) -> Optional[Path]:
        """
        Get path to switch to a worktree.

        Note: This returns the path - actual directory change must be done by caller.
        """
        worktrees = self.list_worktrees()

        for wt in worktrees:
            if str(wt.path) == path_or_branch or wt.branch == path_or_branch:
                return wt.path

        self.console.print(f"[red]Worktree not found: {path_or_branch}[/red]")
        return None

    def lock_worktree(self, path_or_branch: str, reason: str = "") -> bool:
        """Lock a worktree to prevent pruning"""
        worktrees = self.list_worktrees()
        target = None

        for wt in worktrees:
            if str(wt.path) == path_or_branch or wt.branch == path_or_branch:
                target = wt
                break

        if not target:
            self.console.print(f"[red]Worktree not found: {path_or_branch}[/red]")
            return False

        args = ['worktree', 'lock']
        if reason:
            args.extend(['--reason', reason])
        args.append(str(target.path))

        stdout, stderr, code = self._run_git(*args)

        if code == 0:
            self.console.print(f"[green]✓ Locked worktree: {target.path}[/green]")
            return True
        else:
            self.console.print(f"[red]Error locking worktree: {stderr}[/red]")
            return False

    def unlock_worktree(self, path_or_branch: str) -> bool:
        """Unlock a worktree"""
        worktrees = self.list_worktrees()
        target = None

        for wt in worktrees:
            if str(wt.path) == path_or_branch or wt.branch == path_or_branch:
                target = wt
                break

        if not target:
            self.console.print(f"[red]Worktree not found: {path_or_branch}[/red]")
            return False

        stdout, stderr, code = self._run_git('worktree', 'unlock', str(target.path))

        if code == 0:
            self.console.print(f"[green]✓ Unlocked worktree: {target.path}[/green]")
            return True
        else:
            self.console.print(f"[red]Error unlocking worktree: {stderr}[/red]")
            return False

    def prune_worktrees(self) -> bool:
        """Prune stale worktree entries"""
        stdout, stderr, code = self._run_git('worktree', 'prune')

        if code == 0:
            self.console.print("[green]✓ Pruned stale worktree entries[/green]")
            return True
        else:
            self.console.print(f"[red]Error pruning worktrees: {stderr}[/red]")
            return False

    # ==================== Display ====================

    def show_worktrees(self):
        """Display worktrees in a table"""
        worktrees = self.list_worktrees()

        if not worktrees:
            self.console.print("[dim]No worktrees found[/dim]")
            return

        table = Table(title="Git Worktrees", show_header=True, header_style="bold cyan")
        table.add_column("", width=3)  # Status
        table.add_column("Branch")
        table.add_column("Path")
        table.add_column("Commit")
        table.add_column("Status")

        for wt in worktrees:
            # Status indicator
            if wt.is_current:
                indicator = "[green]►[/green]"
            elif wt.is_main:
                indicator = "[cyan]●[/cyan]"
            else:
                indicator = " "

            # Branch name
            if wt.is_detached:
                branch = f"[yellow](detached)[/yellow]"
            else:
                branch = f"[green]{wt.branch}[/green]" if wt.branch else "[dim]unknown[/dim]"

            # Path (truncate if long)
            path_str = str(wt.path)
            if len(path_str) > 40:
                path_str = "..." + path_str[-37:]

            # Status
            status_parts = []
            if wt.is_main:
                status_parts.append("[cyan]main[/cyan]")
            if wt.is_locked:
                lock_info = f"[yellow]locked[/yellow]"
                if wt.lock_reason:
                    lock_info += f" ({wt.lock_reason})"
                status_parts.append(lock_info)
            if wt.is_bare:
                status_parts.append("[dim]bare[/dim]")

            status = ", ".join(status_parts) if status_parts else ""

            table.add_row(
                indicator,
                branch,
                path_str,
                wt.commit or "",
                status
            )

        self.console.print(table)

        # Show help
        self.console.print("\n[dim]Commands: /worktree add <branch> | /worktree remove <branch> | /worktree switch <branch>[/dim]")

    def show_current(self):
        """Show current worktree info"""
        worktrees = self.list_worktrees()

        for wt in worktrees:
            if wt.is_current:
                content = []
                content.append(f"[bold]Path:[/bold] {wt.path}")
                content.append(f"[bold]Branch:[/bold] {wt.branch or '(detached)'}")
                content.append(f"[bold]Commit:[/bold] {wt.commit}")
                if wt.is_main:
                    content.append("[bold]Type:[/bold] Main worktree")
                if wt.is_locked:
                    content.append(f"[bold]Locked:[/bold] {wt.lock_reason or 'Yes'}")

                panel = Panel(
                    "\n".join(content),
                    title="[bold cyan]Current Worktree[/bold cyan]",
                    border_style="cyan"
                )
                self.console.print(panel)
                return

        self.console.print("[dim]Not in a git worktree[/dim]")

    def show_help(self):
        """Show worktree help"""
        help_text = """
[bold cyan]Git Worktree Commands[/bold cyan]

Manage multiple working directories for parallel development.

[bold]Commands:[/bold]
  [green]/worktree[/green]              List all worktrees
  [green]/worktree list[/green]         List all worktrees
  [green]/worktree add <branch>[/green] Create new worktree
  [green]/worktree remove <b>[/green]   Remove worktree
  [green]/worktree switch <b>[/green]   Switch to worktree
  [green]/worktree lock <b>[/green]     Lock worktree
  [green]/worktree unlock <b>[/green]   Unlock worktree
  [green]/worktree prune[/green]        Prune stale entries

[bold]Examples:[/bold]
  /worktree add feature-x     Create worktree for feature-x
  /worktree switch feature-x  Switch to feature-x worktree
  /worktree remove feature-x  Remove feature-x worktree

[bold]Notes:[/bold]
  • Worktrees allow parallel work on different branches
  • Each worktree has its own working directory
  • Changes in one worktree don't affect others
  • Useful for comparing implementations or quick fixes
"""
        self.console.print(help_text)


class WorktreeContext:
    """
    Context manager for temporarily switching worktrees.

    Usage:
        with WorktreeContext(manager, "feature-branch") as path:
            # Work in feature-branch worktree
            ...
        # Back to original directory
    """

    def __init__(self, manager: GitWorktreeManager, branch: str):
        self.manager = manager
        self.branch = branch
        self.original_dir: Optional[Path] = None
        self.worktree_path: Optional[Path] = None

    def __enter__(self) -> Optional[Path]:
        self.original_dir = Path.cwd()
        self.worktree_path = self.manager.switch_worktree(self.branch)

        if self.worktree_path:
            os.chdir(self.worktree_path)
            return self.worktree_path

        return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.original_dir:
            os.chdir(self.original_dir)
        return False
