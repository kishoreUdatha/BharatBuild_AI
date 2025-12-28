"""
Execution Context - Backend-First Error Capture

This module provides the ExecutionContext class that captures COMPLETE
command execution state for auto-fixing. This is the SINGLE SOURCE OF TRUTH
for error context - NO FRONTEND INVOLVEMENT.

Architecture:
    Container → ExecutionContext (buffer) → Auto-Fixer
                      ↓
              SSE/WebSocket (read-only UI)

Key Principles:
1. Terminal logs captured DIRECTLY from backend runtime
2. UI is READ-ONLY - only displays logs, never sends errors
3. Complete stderr/stdout buffered before sending to fixer
4. Retry loop managed entirely in backend
"""

import time
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from app.core.logging_config import logger


class ExecutionState(str, Enum):
    """Execution lifecycle states"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    FIXING = "fixing"
    FIXED = "fixed"
    EXHAUSTED = "exhausted"  # Max fix attempts reached


class RuntimeType(str, Enum):
    """Detected runtime/technology"""
    NODE = "node"
    PYTHON = "python"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    DOTNET = "dotnet"
    RUBY = "ruby"
    PHP = "php"
    UNKNOWN = "unknown"


@dataclass
class ExecutionContext:
    """
    Captures COMPLETE command execution state for auto-fixing.

    This is the SINGLE SOURCE OF TRUTH for error context.
    Backend buffers ALL output here - UI never sends errors.

    Usage:
        ctx = ExecutionContext(
            project_id="proj-123",
            command="npm run dev",
            runtime=RuntimeType.NODE
        )

        # During streaming
        ctx.add_stdout("Starting server...")
        ctx.add_stderr("Error: Module not found")

        # On completion
        ctx.complete(exit_code=1)

        # Get payload for fixer
        if ctx.should_attempt_fix():
            payload = ctx.get_fixer_payload()
    """

    # Required fields
    project_id: str
    user_id: str
    command: str
    runtime: RuntimeType = RuntimeType.UNKNOWN
    working_dir: str = "/app"

    # Buffers (accumulated during streaming)
    stdout_buffer: List[str] = field(default_factory=list)
    stderr_buffer: List[str] = field(default_factory=list)
    combined_buffer: List[str] = field(default_factory=list)  # Interleaved for context

    # Execution state
    state: ExecutionState = ExecutionState.PENDING
    exit_code: Optional[int] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    # Container info
    container_id: Optional[str] = None
    container_name: Optional[str] = None

    # Fix tracking
    fix_attempt: int = 0
    max_fix_attempts: int = 3
    fixes_applied: List[Dict[str, Any]] = field(default_factory=list)

    # Server detection
    server_started: bool = False
    server_url: Optional[str] = None

    # Error classification (detected from stderr)
    primary_error_type: Optional[str] = None
    error_file: Optional[str] = None
    error_line: Optional[int] = None

    # Limits
    max_buffer_lines: int = 500
    max_stderr_lines: int = 200

    def start(self):
        """Mark execution as started"""
        self.state = ExecutionState.RUNNING
        self.started_at = time.time()
        logger.info(f"[ExecutionContext:{self.project_id}] Started: {self.command[:50]}...")

    def add_stdout(self, line: str):
        """Add stdout line to buffer"""
        if not line:
            return

        self.stdout_buffer.append(line)
        self.combined_buffer.append(f"[OUT] {line}")

        # Trim if too large
        if len(self.stdout_buffer) > self.max_buffer_lines:
            self.stdout_buffer = self.stdout_buffer[-self.max_buffer_lines:]
        if len(self.combined_buffer) > self.max_buffer_lines * 2:
            self.combined_buffer = self.combined_buffer[-(self.max_buffer_lines * 2):]

        # Detect server started
        self._check_server_started(line)

    def add_stderr(self, line: str):
        """Add stderr line to buffer"""
        if not line:
            return

        self.stderr_buffer.append(line)
        self.combined_buffer.append(f"[ERR] {line}")

        # Trim if too large
        if len(self.stderr_buffer) > self.max_stderr_lines:
            self.stderr_buffer = self.stderr_buffer[-self.max_stderr_lines:]
        if len(self.combined_buffer) > self.max_buffer_lines * 2:
            self.combined_buffer = self.combined_buffer[-(self.max_buffer_lines * 2):]

        # Classify error
        self._classify_error(line)

    def add_output(self, line: str, is_stderr: bool = False):
        """Add output line (auto-detect stderr vs stdout)"""
        if is_stderr:
            self.add_stderr(line)
        else:
            self.add_stdout(line)

    def complete(self, exit_code: int):
        """Mark execution as completed"""
        self.exit_code = exit_code
        self.completed_at = time.time()

        if exit_code == 0 or self.server_started:
            self.state = ExecutionState.SUCCESS
        else:
            self.state = ExecutionState.FAILED

        duration = self.completed_at - self.started_at
        logger.info(
            f"[ExecutionContext:{self.project_id}] Completed: "
            f"exit_code={exit_code}, state={self.state.value}, "
            f"duration={duration:.2f}s, stderr_lines={len(self.stderr_buffer)}"
        )

    def mark_fixing(self):
        """Mark that fix attempt is in progress"""
        self.state = ExecutionState.FIXING
        self.fix_attempt += 1
        logger.info(f"[ExecutionContext:{self.project_id}] Fix attempt {self.fix_attempt}/{self.max_fix_attempts}")

    def mark_fixed(self, files_modified: List[str]):
        """Mark that fix was applied successfully"""
        self.state = ExecutionState.FIXED
        self.fixes_applied.append({
            "attempt": self.fix_attempt,
            "files": files_modified,
            "timestamp": time.time()
        })
        logger.info(f"[ExecutionContext:{self.project_id}] Fixed: {files_modified}")

    def mark_exhausted(self):
        """Mark that all fix attempts are exhausted"""
        self.state = ExecutionState.EXHAUSTED
        logger.warning(f"[ExecutionContext:{self.project_id}] Exhausted after {self.fix_attempt} attempts")

    def reset_for_retry(self):
        """Reset buffers for retry after fix"""
        self.stdout_buffer.clear()
        self.stderr_buffer.clear()
        self.combined_buffer.clear()
        self.exit_code = None
        self.completed_at = None
        self.server_started = False
        self.server_url = None
        self.primary_error_type = None
        self.error_file = None
        self.error_line = None
        self.state = ExecutionState.RUNNING
        self.started_at = time.time()
        logger.info(f"[ExecutionContext:{self.project_id}] Reset for retry attempt {self.fix_attempt + 1}")

    def should_attempt_fix(self) -> bool:
        """Check if we should try auto-fix"""
        # Don't fix if already succeeded or server started
        if self.server_started:
            return False
        if self.state == ExecutionState.SUCCESS:
            return False

        # Don't fix if exhausted
        if self.fix_attempt >= self.max_fix_attempts:
            return False

        # Need a failure with stderr
        if self.exit_code is None:
            return False
        if self.exit_code == 0:
            return False
        if len(self.stderr_buffer) == 0 and len(self.stdout_buffer) == 0:
            return False

        return True

    def get_fixer_payload(self) -> Dict[str, Any]:
        """
        Get COMPLETE payload for auto-fixer.

        This is the SINGLE SOURCE OF TRUTH - contains everything
        the fixer needs to understand and fix the error.
        NO FRONTEND DATA INVOLVED.
        """
        duration_ms = None
        if self.completed_at and self.started_at:
            duration_ms = (self.completed_at - self.started_at) * 1000

        return {
            # Identification
            "project_id": self.project_id,
            "user_id": self.user_id,
            "container_id": self.container_id,

            # Command context
            "command": self.command,
            "runtime": self.runtime.value,
            "working_dir": self.working_dir,

            # Execution result
            "exit_code": self.exit_code,
            "duration_ms": duration_ms,

            # Complete output buffers
            "stderr": "\n".join(self.stderr_buffer),
            "stdout": "\n".join(self.stdout_buffer[-100:]),  # Last 100 lines
            "combined_output": "\n".join(self.combined_buffer[-200:]),  # Last 200 interleaved

            # Error classification
            "primary_error_type": self.primary_error_type,
            "error_file": self.error_file,
            "error_line": self.error_line,

            # Fix tracking
            "fix_attempt": self.fix_attempt,
            "max_fix_attempts": self.max_fix_attempts,
            "previous_fixes": self.fixes_applied,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current status for UI display"""
        return {
            "project_id": self.project_id,
            "state": self.state.value,
            "exit_code": self.exit_code,
            "fix_attempt": self.fix_attempt,
            "max_fix_attempts": self.max_fix_attempts,
            "server_started": self.server_started,
            "server_url": self.server_url,
            "stderr_lines": len(self.stderr_buffer),
            "stdout_lines": len(self.stdout_buffer),
        }

    def _check_server_started(self, line: str):
        """Detect if server has started successfully"""
        line_lower = line.lower()

        # Node.js / Vite / Next.js patterns
        start_patterns = [
            r"ready in \d+",
            r"compiled successfully",
            r"compiled client and server",
            r"listening on port",
            r"server running at",
            r"local:\s*https?://",
            r"started server on",
            r"application started",
            r"server started on port",
        ]

        for pattern in start_patterns:
            if re.search(pattern, line_lower):
                self.server_started = True
                self.state = ExecutionState.SUCCESS

                # Try to extract URL
                url_match = re.search(r'https?://[^\s]+', line)
                if url_match:
                    self.server_url = url_match.group(0)

                logger.info(f"[ExecutionContext:{self.project_id}] Server started: {self.server_url or 'detected'}")
                return

    def _classify_error(self, line: str):
        """Classify error type from stderr line"""
        line_lower = line.lower()

        # Already classified?
        if self.primary_error_type:
            return

        # Error type patterns
        error_patterns = {
            "syntax_error": [r"syntaxerror", r"syntax error", r"unexpected token"],
            "module_not_found": [r"cannot find module", r"module not found", r"no module named"],
            "type_error": [r"typeerror", r"type error", r"ts\d{4}:"],
            "reference_error": [r"referenceerror", r"is not defined"],
            "import_error": [r"importerror", r"failed to resolve import"],
            "dependency_error": [r"npm err", r"enoent", r"eresolve", r"peer dep"],
            "port_in_use": [r"eaddrinuse", r"address already in use"],
            "permission_error": [r"permission denied", r"eacces", r"eperm"],
            "build_error": [r"failed to compile", r"build failed", r"\[error\]"],
            "runtime_error": [r"exception", r"traceback", r"panic:"],
        }

        for error_type, patterns in error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, line_lower):
                    self.primary_error_type = error_type
                    logger.debug(f"[ExecutionContext:{self.project_id}] Classified error: {error_type}")
                    break
            if self.primary_error_type:
                break

        # Try to extract file and line number
        file_line_patterns = [
            r'([a-zA-Z0-9_\-./]+\.(tsx?|jsx?|py|java|go|rs)):(\d+)',  # file.ts:123
            r'File "([^"]+)", line (\d+)',  # Python traceback
            r'at ([^\s]+):(\d+):(\d+)',  # Node.js stack trace
        ]

        for pattern in file_line_patterns:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()
                self.error_file = groups[0]
                try:
                    # Line number is in different positions for different patterns
                    line_idx = 2 if len(groups) > 2 and groups[2] and groups[2].isdigit() else 1
                    if len(groups) > 1 and groups[line_idx - 1]:
                        potential_line = groups[line_idx] if len(groups) > line_idx else groups[1]
                        if potential_line and potential_line.isdigit():
                            self.error_line = int(potential_line)
                except (ValueError, IndexError):
                    pass
                break


# Active execution contexts (per project)
_active_contexts: Dict[str, ExecutionContext] = {}


def get_execution_context(project_id: str) -> Optional[ExecutionContext]:
    """Get active execution context for a project"""
    return _active_contexts.get(project_id)


def create_execution_context(
    project_id: str,
    user_id: str,
    command: str,
    runtime: RuntimeType = RuntimeType.UNKNOWN,
    working_dir: str = "/app",
    container_id: Optional[str] = None,
) -> ExecutionContext:
    """Create and register a new execution context"""
    ctx = ExecutionContext(
        project_id=project_id,
        user_id=user_id,
        command=command,
        runtime=runtime,
        working_dir=working_dir,
        container_id=container_id,
    )
    _active_contexts[project_id] = ctx
    logger.info(f"[ExecutionContext] Created context for {project_id}")
    return ctx


def remove_execution_context(project_id: str):
    """Remove execution context for a project"""
    if project_id in _active_contexts:
        del _active_contexts[project_id]
        logger.info(f"[ExecutionContext] Removed context for {project_id}")


def get_all_contexts() -> Dict[str, ExecutionContext]:
    """Get all active execution contexts"""
    return _active_contexts.copy()
