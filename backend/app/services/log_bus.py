"""
LogBus - Central Log Collection System (Bolt.new Style)

Collects logs from 5 sources:
1. Browser Console (runtime errors, console.error, promise rejections)
2. Build Logs (Vite/Next/Webpack compile errors)
3. Backend Runtime (Node/Python/FastAPI server logs)
4. Network Errors (fetch/XHR failures, CORS)
5. Docker/Dev Server (container logs, startup errors)

BOLT.NEW STYLE AUTO-HEALING:
- Collects file context (Dockerfile, docker-compose.yml, package.json)
- Tracks last changed files
- Builds structured fixer_payload.json for Claude
- Enables self-healing loop

All logs feed into the Fixer Agent when user requests a fix.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
import threading
import re
import json
import os

from app.core.logging_config import logger
from app.services.log_rebuilder import log_rebuilder, DetectedError


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

        # Sanitize message for Windows console logging (cp1252 encoding)
        safe_msg = message[:100].encode('ascii', 'replace').decode('ascii')
        logger.debug(f"[LogBus:{self.project_id}] Added {source}/{level}: {safe_msg}...")

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

    # ============= BOLT.NEW STYLE FILE CONTEXT COLLECTION =============

    def collect_file_context(self, project_path: str) -> Dict[str, Any]:
        """
        Collect file context for Fixer Agent (Bolt.new style).

        Collects:
        1. Dockerfile
        2. docker-compose.yml
        3. package.json
        4. Main scripts
        5. Config files
        6. Last changed files
        """
        project_path = Path(project_path)
        context = {
            "dockerfile": None,
            "docker_compose": None,
            "package_json": None,
            "requirements_txt": None,
            "tsconfig_json": None,
            "vite_config": None,
            "main_files": {},
            "config_files": {},
            "source_files": {},
        }

        # Collect specific config files
        config_files = [
            ("Dockerfile", "dockerfile"),
            ("docker-compose.yml", "docker_compose"),
            ("docker-compose.yaml", "docker_compose"),
            ("package.json", "package_json"),
            ("requirements.txt", "requirements_txt"),
            ("tsconfig.json", "tsconfig_json"),
            ("vite.config.ts", "vite_config"),
            ("vite.config.js", "vite_config"),
        ]

        for filename, key in config_files:
            file_path = project_path / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    context[key] = content[:10000]  # Limit size
                except Exception as e:
                    logger.warning(f"Could not read {filename}: {e}")

        # Collect main entry files
        main_files = [
            "src/main.tsx", "src/main.ts", "src/main.jsx", "src/main.js",
            "src/index.tsx", "src/index.ts", "src/index.jsx", "src/index.js",
            "src/App.tsx", "src/App.ts", "src/App.jsx", "src/App.js",
            "main.py", "app.py", "server.py",
            "index.html",
        ]

        for main_file in main_files:
            file_path = project_path / main_file
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    context["main_files"][main_file] = content[:5000]
                except Exception as e:
                    logger.warning(f"Could not read {main_file}: {e}")

        # Collect files mentioned in errors
        for error_file in self._error_files:
            file_path = project_path / error_file
            if file_path.exists() and error_file not in context["source_files"]:
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    context["source_files"][error_file] = content[:5000]
                except Exception as e:
                    logger.warning(f"Could not read error file {error_file}: {e}")

        return context

    def detect_environment(self, project_path: str) -> Dict[str, Any]:
        """Detect project environment info"""
        project_path = Path(project_path)
        env = {
            "node_version": None,
            "python_version": None,
            "framework": None,
            "ports": [],
            "has_docker": False,
            "project_type": "unknown"
        }

        # Check for Docker
        if (project_path / "Dockerfile").exists() or (project_path / "docker-compose.yml").exists():
            env["has_docker"] = True

        # Check package.json for Node info
        pkg_path = project_path / "package.json"
        if pkg_path.exists():
            try:
                pkg = json.loads(pkg_path.read_text(encoding='utf-8'))
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                if "vite" in deps:
                    env["framework"] = "vite"
                    env["ports"].append(5173)
                elif "next" in deps:
                    env["framework"] = "nextjs"
                    env["ports"].append(3000)
                elif "react" in deps:
                    env["framework"] = "react"
                    env["ports"].append(3000)

                env["project_type"] = "node"
            except Exception as e:
                logger.warning(f"Could not parse package.json: {e}")

        # Check requirements.txt for Python info
        req_path = project_path / "requirements.txt"
        if req_path.exists():
            try:
                reqs = req_path.read_text(encoding='utf-8').lower()
                if "fastapi" in reqs:
                    env["framework"] = "fastapi"
                    env["ports"].append(8000)
                elif "flask" in reqs:
                    env["framework"] = "flask"
                    env["ports"].append(5000)
                elif "django" in reqs:
                    env["framework"] = "django"
                    env["ports"].append(8000)

                env["project_type"] = "python"
            except Exception as e:
                logger.warning(f"Could not parse requirements.txt: {e}")

        return env

    def _rebuild_error_logs(self, errors: List[LogEntry], context: Optional[Dict] = None) -> List[Dict]:
        """
        Rebuild error logs using Log Rebuilder for complete context.

        Even if sandbox sends truncated logs, this ensures Claude gets
        full stack traces and error context.
        """
        rebuilt_errors = []
        for error in errors:
            # Handle both LogEntry objects and dicts
            if isinstance(error, LogEntry):
                message = error.message
            elif isinstance(error, dict):
                message = error.get("message", "")
            else:
                message = str(error)

            if not message:
                continue

            try:
                # Use Log Rebuilder to complete truncated logs
                detected = log_rebuilder.rebuild(message, context)

                rebuilt_errors.append({
                    "original": message,
                    "rebuilt": detected.rebuilt_log,
                    "error_type": detected.error_type.value,
                    "file": detected.file,
                    "line": detected.line,
                    "module": detected.module,
                    "confidence": detected.confidence,
                })
            except Exception as e:
                logger.warning(f"[LogBus] Failed to rebuild error log: {e}")
                # Fallback to original message
                rebuilt_errors.append({
                    "original": message,
                    "rebuilt": message,
                    "error_type": "unknown",
                    "confidence": 0.0,
                })

        return rebuilt_errors

    def get_bolt_fixer_payload(self, project_path: str, command: str = None, error_message: str = None) -> Dict[str, Any]:
        """
        Get complete Bolt.new-style fixer payload for Claude.

        This is the exact format that enables Claude to fix accurately:
        - exact logs (rebuilt with full stack traces)
        - exact file code
        - environment details

        The Log Rebuilder ensures even truncated logs are completed
        with template-based stack traces, giving Claude full context.

        Returns structured fixer_payload.json
        """
        # Collect file context
        file_context = self.collect_file_context(project_path)

        # Detect environment
        environment = self.detect_environment(project_path)

        # Get all errors
        all_errors = self.get_errors()

        # Context for log rebuilding (helps with file path inference)
        rebuild_context = {
            "project_path": project_path,
            "framework": environment.get("framework"),
            "project_type": environment.get("project_type"),
            "error_files": list(self._error_files),
        }

        # Rebuild error logs with full context using Log Rebuilder
        browser_errors = self._rebuild_error_logs(
            [e for e in self._logs["browser"] if e.level == "error"],
            rebuild_context
        )[-10:]

        build_errors = self._rebuild_error_logs(
            [e for e in self._logs["build"] if e.level == "error"],
            rebuild_context
        )[-10:]

        docker_errors = self._rebuild_error_logs(
            [e for e in self._logs["docker"] if e.level == "error"],
            rebuild_context
        )[-10:]

        backend_errors = self._rebuild_error_logs(
            [e for e in self._logs["backend"] if e.level == "error"],
            rebuild_context
        )[-10:]

        # Use rebuilt primary error message
        primary_error = error_message
        if not primary_error and all_errors:
            # Get the rebuilt version of the primary error
            primary_rebuilt = self._rebuild_error_logs([all_errors[0]], rebuild_context)
            if primary_rebuilt:
                primary_error = primary_rebuilt[0].get("rebuilt", all_errors[0]["message"])
            else:
                primary_error = all_errors[0]["message"]
        primary_error = primary_error or "Unknown error"

        # Build the payload with rebuilt logs
        payload = {
            "error": primary_error,
            "command": command or "unknown",
            "fileContext": {
                "package.json": file_context.get("package_json"),
                "Dockerfile": file_context.get("dockerfile"),
                "docker-compose.yml": file_context.get("docker_compose"),
                "requirements.txt": file_context.get("requirements_txt"),
                "vite.config": file_context.get("vite_config"),
                "tsconfig.json": file_context.get("tsconfig_json"),
                **file_context.get("main_files", {}),
                **file_context.get("source_files", {}),
            },
            "environment": environment,
            # Rebuilt error logs with full context
            "errorLogs": {
                "browser": browser_errors,
                "build": build_errors,
                "docker": docker_errors,
                "backend": backend_errors,
            },
            # Also include simple message arrays for backward compatibility
            "errorMessages": {
                "browser": [e.get("rebuilt", e.get("original", "")) for e in browser_errors],
                "build": [e.get("rebuilt", e.get("original", "")) for e in build_errors],
                "docker": [e.get("rebuilt", e.get("original", "")) for e in docker_errors],
                "backend": [e.get("rebuilt", e.get("original", "")) for e in backend_errors],
            },
            "stackTraces": self._stack_traces[-5:],
            "errorFiles": list(self._error_files),
            "timestamp": datetime.utcnow().isoformat(),
            # Log Rebuilder metadata
            "logRebuilderUsed": True,
        }

        # Remove None values from fileContext
        payload["fileContext"] = {k: v for k, v in payload["fileContext"].items() if v is not None}

        logger.info(f"[LogBus:{self.project_id}] Built fixer payload with {len(build_errors)} rebuilt build errors")

        return payload

    def set_last_command(self, command: str) -> None:
        """Track the last executed command"""
        with self._lock:
            self._last_command = command

    def get_last_command(self) -> Optional[str]:
        """Get the last executed command"""
        with self._lock:
            return getattr(self, '_last_command', None)


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
