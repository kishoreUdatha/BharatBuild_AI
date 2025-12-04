"""
Tool Executor - Handles file operations and bash commands

Similar to Claude Code's tool execution system.
"""

import asyncio
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

from cli.config import CLIConfig


@dataclass
class CommandResult:
    """Result of a command execution"""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float


@dataclass
class FileOperation:
    """Represents a file operation"""
    operation: str  # read, write, edit, delete
    path: str
    content: Optional[str] = None
    old_content: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


class ToolExecutor:
    """Executes tools (file operations, bash commands, etc.)"""

    def __init__(self, config: CLIConfig, console: Console):
        self.config = config
        self.console = console
        self.working_dir = Path(config.working_directory).resolve()
        self.file_history: List[FileOperation] = []
        self.command_history: List[CommandResult] = []

    def _resolve_path(self, path: str) -> Path:
        """Resolve path relative to working directory"""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.working_dir / p

    # ==================== File Operations ====================

    async def read_file(self, path: str) -> Optional[str]:
        """Read a file's contents"""
        try:
            file_path = self._resolve_path(path)

            if not file_path.exists():
                return None

            if not file_path.is_file():
                raise ValueError(f"{path} is not a file")

            # Check file size (limit to 1MB for safety)
            if file_path.stat().st_size > 1024 * 1024:
                raise ValueError(f"File {path} is too large (>1MB)")

            content = file_path.read_text(encoding='utf-8')

            self.file_history.append(FileOperation(
                operation="read",
                path=str(file_path),
                content=content
            ))

            return content

        except Exception as e:
            self.file_history.append(FileOperation(
                operation="read",
                path=path,
                success=False,
                error=str(e)
            ))
            raise

    async def write_file(self, path: str, content: str) -> bool:
        """Write content to a file"""
        try:
            file_path = self._resolve_path(path)

            # Store old content for undo
            old_content = None
            if file_path.exists():
                old_content = file_path.read_text(encoding='utf-8')

            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            file_path.write_text(content, encoding='utf-8')

            self.file_history.append(FileOperation(
                operation="write",
                path=str(file_path),
                content=content,
                old_content=old_content
            ))

            return True

        except Exception as e:
            self.file_history.append(FileOperation(
                operation="write",
                path=path,
                content=content,
                success=False,
                error=str(e)
            ))
            raise

    async def edit_file(self, path: str, old_string: str, new_string: str) -> bool:
        """Edit a file by replacing old_string with new_string"""
        try:
            file_path = self._resolve_path(path)

            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            content = file_path.read_text(encoding='utf-8')
            old_content = content

            if old_string not in content:
                raise ValueError(f"String not found in file: {old_string[:50]}...")

            # Replace string
            new_content = content.replace(old_string, new_string, 1)

            # Write back
            file_path.write_text(new_content, encoding='utf-8')

            self.file_history.append(FileOperation(
                operation="edit",
                path=str(file_path),
                content=new_content,
                old_content=old_content
            ))

            return True

        except Exception as e:
            self.file_history.append(FileOperation(
                operation="edit",
                path=path,
                success=False,
                error=str(e)
            ))
            raise

    async def delete_file(self, path: str) -> bool:
        """Delete a file"""
        try:
            file_path = self._resolve_path(path)

            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            old_content = None
            if file_path.is_file():
                old_content = file_path.read_text(encoding='utf-8')
                file_path.unlink()
            elif file_path.is_dir():
                shutil.rmtree(file_path)

            self.file_history.append(FileOperation(
                operation="delete",
                path=str(file_path),
                old_content=old_content
            ))

            return True

        except Exception as e:
            self.file_history.append(FileOperation(
                operation="delete",
                path=path,
                success=False,
                error=str(e)
            ))
            raise

    async def list_files(self, path: str = ".", pattern: str = "*") -> List[str]:
        """List files in a directory"""
        dir_path = self._resolve_path(path)

        if not dir_path.exists():
            return []

        if not dir_path.is_dir():
            return [str(dir_path)]

        files = []
        for item in dir_path.glob(pattern):
            rel_path = item.relative_to(self.working_dir)
            files.append(str(rel_path))

        return sorted(files)

    async def glob_files(self, pattern: str) -> List[str]:
        """Find files matching a glob pattern"""
        files = []
        for item in self.working_dir.glob(pattern):
            rel_path = item.relative_to(self.working_dir)
            files.append(str(rel_path))
        return sorted(files)

    async def grep_files(
        self,
        pattern: str,
        path: str = ".",
        file_pattern: str = "*"
    ) -> List[Dict[str, Any]]:
        """Search for pattern in files"""
        import re

        dir_path = self._resolve_path(path)
        results = []

        try:
            regex = re.compile(pattern)
        except re.error:
            # Treat as literal string if not valid regex
            regex = re.compile(re.escape(pattern))

        for file_path in dir_path.rglob(file_pattern):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text(encoding='utf-8')
                for i, line in enumerate(content.split('\n'), 1):
                    if regex.search(line):
                        results.append({
                            "file": str(file_path.relative_to(self.working_dir)),
                            "line": i,
                            "content": line.strip()
                        })
            except (UnicodeDecodeError, PermissionError):
                continue

        return results

    # ==================== Bash Commands ====================

    async def execute_bash(
        self,
        command: str,
        timeout: int = 120,
        capture_output: bool = True
    ) -> CommandResult:
        """Execute a bash command"""
        import time

        start_time = time.time()

        try:
            # Determine shell based on platform
            if os.name == 'nt':  # Windows
                shell_cmd = ["cmd", "/c", command]
            else:  # Unix
                shell_cmd = ["/bin/bash", "-c", command]

            process = await asyncio.create_subprocess_exec(
                *shell_cmd,
                stdout=asyncio.subprocess.PIPE if capture_output else None,
                stderr=asyncio.subprocess.PIPE if capture_output else None,
                cwd=str(self.working_dir)
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                raise TimeoutError(f"Command timed out after {timeout}s")

            duration = time.time() - start_time

            result = CommandResult(
                command=command,
                exit_code=process.returncode,
                stdout=stdout.decode('utf-8', errors='replace') if stdout else "",
                stderr=stderr.decode('utf-8', errors='replace') if stderr else "",
                duration=duration
            )

            self.command_history.append(result)
            return result

        except Exception as e:
            duration = time.time() - start_time
            result = CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration=duration
            )
            self.command_history.append(result)
            return result

    async def execute_bash_streaming(
        self,
        command: str,
        timeout: int = 120
    ):
        """Execute bash command with streaming output"""
        if os.name == 'nt':
            shell_cmd = ["cmd", "/c", command]
        else:
            shell_cmd = ["/bin/bash", "-c", command]

        process = await asyncio.create_subprocess_exec(
            *shell_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(self.working_dir)
        )

        try:
            while True:
                line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=timeout
                )
                if not line:
                    break
                yield line.decode('utf-8', errors='replace')

        except asyncio.TimeoutError:
            process.kill()
            yield f"\n[Timeout after {timeout}s]\n"

        await process.wait()

    # ==================== Undo Operations ====================

    def undo_last_file_operation(self) -> Optional[FileOperation]:
        """Undo the last file operation"""
        if not self.file_history:
            return None

        last_op = self.file_history.pop()

        if last_op.operation == "write" and last_op.old_content is not None:
            # Restore old content
            file_path = Path(last_op.path)
            file_path.write_text(last_op.old_content, encoding='utf-8')
            return last_op

        elif last_op.operation == "write" and last_op.old_content is None:
            # File was created, delete it
            file_path = Path(last_op.path)
            if file_path.exists():
                file_path.unlink()
            return last_op

        elif last_op.operation == "edit":
            # Restore old content
            file_path = Path(last_op.path)
            if last_op.old_content:
                file_path.write_text(last_op.old_content, encoding='utf-8')
            return last_op

        elif last_op.operation == "delete":
            # Restore deleted file
            file_path = Path(last_op.path)
            if last_op.old_content:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(last_op.old_content, encoding='utf-8')
            return last_op

        return None

    # ==================== Git Operations ====================

    async def git_status(self) -> str:
        """Get git status"""
        result = await self.execute_bash("git status --porcelain")
        return result.stdout

    async def git_diff(self, staged: bool = False) -> str:
        """Get git diff"""
        cmd = "git diff --staged" if staged else "git diff"
        result = await self.execute_bash(cmd)
        return result.stdout

    async def is_git_repo(self) -> bool:
        """Check if current directory is a git repo"""
        result = await self.execute_bash("git rev-parse --git-dir")
        return result.exit_code == 0
