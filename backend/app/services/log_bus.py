"""
LogBus - Central Log Collection System (Bolt.new Style)

Collects logs from 5 sources:
1. Browser Console (runtime errors, console.error, promise rejections)
2. Build Logs (Vite/Next/Webpack compile errors)
3. Backend Runtime (Node/Python/FastAPI server logs)
4. Network Errors (fetch/XHR failures, CORS)
5. Docker/Dev Server (container logs, startup errors)

All logs feed into the Fixer Agent when user requests a fix.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import threading
import re

from app.core.logging_config import logger


@dataclass
class LogEntry:
    """Single log entry"""
    source: str  # browser, build, backend, network, docker
    level: str   # error, warning, info, debug
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    stack: Optional[str] = None
    # Network-specific
    url: Optional[str] = None
    status: Optional[int] = None
    method: Optional[str] = None
    # Extra metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "stack": self.stack,
            "url": self.url,
            "status": self.status,
            "method": self.method,
            "metadata": self.metadata
        }


class LogBus:
    """
    Central log aggregator for a project.

    Stores logs in memory with automatic cleanup of old entries.
    Provides structured log payload for Fixer Agent.
    """

    # Log retention (keep last N entries per source)
    MAX_LOGS_PER_SOURCE = 50
    # Time-based retention (logs older than this are cleaned)
    LOG_RETENTION_MINUTES = 30

    def __init__(self, project_id: str):
        self.project_id = project_id
        self._lock = threading.Lock()

        # Logs organized by source
        self._logs: Dict[str, List[LogEntry]] = {
            "browser": [],
            "build": [],
            "backend": [],
            "network": [],
            "docker": []
        }

        # Stack traces extracted from logs
        self._stack_traces: List[Dict[str, Any]] = []

        # Files mentioned in errors (for context engine)
        self._error_files: set = set()

    def add_log(
        self,
        source: str,
        level: str,
        message: str,
        **kwargs
    ) -> None:
        """Add a log entry to the bus"""
        if source not in self._logs:
            source = "backend"  # Default unknown sources to backend

        entry = LogEntry(
            source=source,
            level=level,
            message=message,
            **kwargs
        )

        with self._lock:
            # Add to appropriate source list
            self._logs[source].append(entry)

            # Trim if over limit
            if len(self._logs[source]) > self.MAX_LOGS_PER_SOURCE:
                self._logs[source] = self._logs[source][-self.MAX_LOGS_PER_SOURCE:]

            # Extract file references
            self._extract_file_references(entry)

            # Extract stack traces
            if entry.stack:
                self._extract_stack_trace(entry)

        logger.debug(f"[LogBus:{self.project_id}] Added {source}/{level}: {message[:100]}...")

    def add_browser_error(
        self,
        message: str,
        file: Optional[str] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
        stack: Optional[str] = None
    ) -> None:
        """Add browser console/runtime error"""
        self.add_log(
            source="browser",
            level="error",
            message=message,
            file=file,
            line=line,
            column=column,
            stack=stack
        )

    def add_build_error(
        self,
        message: str,
        file: Optional[str] = None,
        line: Optional[int] = None
    ) -> None:
        """Add build/compile error (Vite/Webpack/tsc)"""
        self.add_log(
            source="build",
            level="error",
            message=message,
            file=file,
            line=line
        )

    def add_build_log(self, message: str, level: str = "info") -> None:
        """Add general build log"""
        self.add_log(source="build", level=level, message=message)

    def add_backend_error(
        self,
        message: str,
        stack: Optional[str] = None
    ) -> None:
        """Add backend runtime error"""
        self.add_log(
            source="backend",
            level="error",
            message=message,
            stack=stack
        )

    def add_backend_log(self, message: str, level: str = "info") -> None:
        """Add general backend log"""
        self.add_log(source="backend", level=level, message=message)

    def add_network_error(
        self,
        message: str,
        url: str,
        status: Optional[int] = None,
        method: str = "GET"
    ) -> None:
        """Add network/fetch error"""
        self.add_log(
            source="network",
            level="error",
            message=message,
            url=url,
            status=status,
            method=method
        )

    def add_docker_error(self, message: str) -> None:
        """Add Docker container error"""
        self.add_log(source="docker", level="error", message=message)

    def add_docker_log(self, message: str, level: str = "info") -> None:
        """Add general Docker log"""
        self.add_log(source="docker", level=level, message=message)

    def _extract_file_references(self, entry: LogEntry) -> None:
        """Extract file paths mentioned in error"""
        # Direct file reference
        if entry.file:
            self._error_files.add(entry.file)

        # Extract from message using patterns
        patterns = [
            # React/JS: "at Component (src/App.jsx:10:5)"
            r'at\s+\w+\s+\(([^:)]+\.[jt]sx?):\d+',
            # Direct: "src/App.jsx:10:5"
            r'([^\s:(]+\.[jt]sx?):\d+',
            # Python: 'File "app/main.py", line 10'
            r'File\s+"([^"]+\.py)"',
            # Webpack: "in ./src/App.jsx"
            r'in\s+\.?/?([^\s]+\.[jt]sx?)',
            # Vite: "src/App.jsx:10:5"
            r'^([^\s:]+\.[jt]sx?):\d+:\d+',
        ]

        text = entry.message + (entry.stack or "")
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Clean up path
                clean_path = match.replace("./", "").strip()
                if clean_path and not clean_path.startswith("node_modules"):
                    self._error_files.add(clean_path)

    def _extract_stack_trace(self, entry: LogEntry) -> None:
        """Parse and store structured stack trace"""
        if not entry.stack:
            return

        frames = []
        # Parse stack trace frames
        frame_pattern = r'at\s+([^\s]+)\s+\(([^:]+):(\d+):(\d+)\)'
        matches = re.findall(frame_pattern, entry.stack)

        for func, file, line, col in matches[:10]:  # Keep top 10 frames
            if "node_modules" not in file:
                frames.append({
                    "function": func,
                    "file": file.replace("./", ""),
                    "line": int(line),
                    "column": int(col)
                })

        if frames:
            self._stack_traces.append({
                "source": entry.source,
                "message": entry.message[:200],
                "frames": frames
            })
            # Keep only recent stack traces
            self._stack_traces = self._stack_traces[-20:]

    def get_errors(self, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get error logs, optionally filtered by source"""
        with self._lock:
            if source:
                return [
                    e.to_dict() for e in self._logs.get(source, [])
                    if e.level == "error"
                ]

            # All errors
            errors = []
            for src_logs in self._logs.values():
                errors.extend([e.to_dict() for e in src_logs if e.level == "error"])
            return errors

    def get_all_logs(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all logs organized by source"""
        with self._lock:
            return {
                source: [e.to_dict() for e in entries]
                for source, entries in self._logs.items()
            }

    def get_error_files(self) -> List[str]:
        """Get list of files mentioned in errors"""
        with self._lock:
            return list(self._error_files)

    def get_stack_traces(self) -> List[Dict[str, Any]]:
        """Get parsed stack traces"""
        with self._lock:
            return self._stack_traces.copy()

    def get_fixer_payload(self) -> Dict[str, Any]:
        """
        Get complete log payload for Fixer Agent.

        This is what gets sent to Claude when fixing errors.
        """
        with self._lock:
            # Collect errors by source
            browser_errors = [e.to_dict() for e in self._logs["browser"] if e.level == "error"]
            build_errors = [e.to_dict() for e in self._logs["build"] if e.level == "error"]
            backend_errors = [e.to_dict() for e in self._logs["backend"] if e.level == "error"]
            network_errors = [e.to_dict() for e in self._logs["network"] if e.level == "error"]
            docker_errors = [e.to_dict() for e in self._logs["docker"] if e.level == "error"]

            # Recent logs (for context)
            recent_build_logs = [e.to_dict() for e in self._logs["build"][-20:]]
            recent_backend_logs = [e.to_dict() for e in self._logs["backend"][-20:]]
            recent_docker_logs = [e.to_dict() for e in self._logs["docker"][-20:]]

            return {
                "browser_errors": browser_errors,
                "build_errors": build_errors,
                "backend_errors": backend_errors,
                "network_errors": network_errors,
                "docker_errors": docker_errors,
                "stack_traces": self._stack_traces,
                "error_files": list(self._error_files),
                "recent_logs": {
                    "build": recent_build_logs,
                    "backend": recent_backend_logs,
                    "docker": recent_docker_logs
                }
            }

    def clear(self) -> None:
        """Clear all logs"""
        with self._lock:
            for source in self._logs:
                self._logs[source] = []
            self._stack_traces = []
            self._error_files = set()

    def cleanup_old_logs(self) -> None:
        """Remove logs older than retention period"""
        cutoff = datetime.utcnow() - timedelta(minutes=self.LOG_RETENTION_MINUTES)

        with self._lock:
            for source in self._logs:
                self._logs[source] = [
                    e for e in self._logs[source]
                    if e.timestamp > cutoff
                ]


class LogBusManager:
    """
    Manages LogBus instances for all projects.

    Singleton pattern - one manager for the entire application.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._buses: Dict[str, LogBus] = {}
                    cls._instance._bus_lock = threading.Lock()
        return cls._instance

    def get_bus(self, project_id: str) -> LogBus:
        """Get or create LogBus for a project"""
        with self._bus_lock:
            if project_id not in self._buses:
                self._buses[project_id] = LogBus(project_id)
                logger.info(f"[LogBusManager] Created LogBus for project {project_id}")
            return self._buses[project_id]

    def remove_bus(self, project_id: str) -> None:
        """Remove LogBus for a project (cleanup)"""
        with self._bus_lock:
            if project_id in self._buses:
                del self._buses[project_id]
                logger.info(f"[LogBusManager] Removed LogBus for project {project_id}")

    def cleanup_all(self) -> None:
        """Cleanup old logs in all buses"""
        with self._bus_lock:
            for bus in self._buses.values():
                bus.cleanup_old_logs()


# Global singleton instance
log_bus_manager = LogBusManager()


def get_log_bus(project_id: str) -> LogBus:
    """Convenience function to get LogBus for a project"""
    return log_bus_manager.get_bus(project_id)
