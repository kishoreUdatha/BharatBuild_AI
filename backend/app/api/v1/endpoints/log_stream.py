"""
WebSocket Log Stream - Real-time log collection (Bolt.new style)

Receives logs from:
1. Browser (iframe preview) via WebSocket
2. Network errors (fetch/XHR)
3. Build server (Vite/Next)
4. Backend server (Node/Python)
5. Docker containers

All logs flow to LogBus for Fixer Agent consumption.
Auto-fix is triggered automatically when errors are detected!
"""

import json
import asyncio
import re
from typing import Dict, Set, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from datetime import datetime

from app.core.logging_config import logger
from app.services.log_bus import get_log_bus, LogBusManager
from app.services.auto_fixer import get_auto_fixer, AutoFixConfig

router = APIRouter()


# ============= BUILD ERROR DETECTION (Bolt.new style) =============
# Patterns that indicate a build error across ALL technologies
BUILD_ERROR_PATTERNS = [
    # ============= VITE/WEBPACK/ESBUILD =============
    "Failed to resolve import",
    "Could not resolve",
    "[plugin:vite:",
    "[vite]",
    "Pre-transform error",
    "Transform failed",
    "Module not found",
    "Can't resolve",
    "Cannot find module",
    "esbuild:",

    # ============= TYPESCRIPT/JAVASCRIPT =============
    "TS2",  # TypeScript error codes (TS2304, TS2339, etc.)
    "TSError",
    "error TS",
    "SyntaxError:",
    "ReferenceError:",
    "TypeError:",
    "Unexpected token",
    "is not defined",
    "is not a function",
    "Property '",
    "Argument of type",

    # ============= PYTHON =============
    "ModuleNotFoundError",
    "ImportError",
    "NameError:",
    "AttributeError:",
    "IndentationError",
    "TabError",
    "SyntaxError: invalid syntax",
    "No module named",
    "cannot import name",
    "Traceback (most recent call last)",
    "File \"",  # Python stack trace

    # ============= PYTHON FRAMEWORKS =============
    "django.core.exceptions",
    "flask.exceptions",
    "FastAPI",
    "pydantic.error_wrappers",
    "ValidationError",

    # ============= GO =============
    "undefined:",
    "cannot find package",
    "imported and not used",
    "declared and not used",
    "no required module provides",
    "go: module",
    "panic:",

    # ============= RUST =============
    "error[E",  # Rust error codes (E0433, E0599, etc.)
    "cannot find",
    "unresolved import",
    "no method named",
    "mismatched types",
    "borrow of moved value",
    "cargo build",

    # ============= JAVA/KOTLIN =============
    "java.lang.Error",
    "java.lang.Exception",
    "ClassNotFoundException",
    "NoClassDefFoundError",
    "NullPointerException",
    "cannot find symbol",
    "package does not exist",
    "error: ",  # Java compiler
    "FAILURE: Build failed",  # Gradle
    "BUILD FAILURE",  # Maven

    # ============= C/C++ =============
    "undefined reference",
    "fatal error:",
    "error: expected",
    "linker error",
    "#include",
    "no such file or directory",

    # ============= .NET/C# =============
    "CS0",  # C# error codes
    "error CS",
    "System.Exception",
    "NullReferenceException",
    "Build FAILED",

    # ============= RUBY/RAILS =============
    "LoadError",
    "NameError:",
    "NoMethodError",
    "uninitialized constant",
    "Gem::LoadError",
    "ActiveRecord::",
    "ActionController::",

    # ============= PHP =============
    "Fatal error:",
    "Parse error:",
    "PHP Fatal error",
    "Class '",
    "Call to undefined",

    # ============= CSS/SASS/LESS =============
    "Sass Error",
    "Less Error",
    "PostCSS",
    "CssSyntaxError",
    "Unknown word",
    "Unclosed block",

    # ============= DATABASE =============
    "sqlite3.OperationalError",
    "psycopg2.Error",
    "pymysql.err",
    "OperationalError",
    "IntegrityError",
    "ProgrammingError",
    "relation \"",
    "column \"",
    "table \"",

    # ============= DOCKER/CONTAINER =============
    "docker:",
    "Dockerfile",
    "COPY failed",
    "RUN failed",
    "exited with code",

    # ============= GENERAL BUILD =============
    "Build failed",
    "Compilation failed",
    "compile error",
    "build error",
    "FAILED",
    "ERROR",
]


def is_build_error(message: str) -> bool:
    """
    Check if a message is a build error across ALL technologies.

    This helps correctly categorize errors that may come from
    docker/backend sources but are actually build errors.
    """
    if not message:
        return False

    message_lower = message.lower()

    # Check for build error patterns
    for pattern in BUILD_ERROR_PATTERNS:
        if pattern.lower() in message_lower:
            return True

    # Check for file path references with line numbers (common in build errors)
    # Supports: JS/TS, Python, Go, Rust, Java, C/C++, Ruby, PHP, C#
    file_extensions = r'\.(tsx?|jsx?|vue|svelte|py|go|rs|java|kt|c|cpp|h|hpp|rb|php|cs|swift|scala|ex|exs|erl|hs|ml|fs)'
    if re.search(rf'[/\\][\w/\\]+{file_extensions}[:(\d]', message):
        if 'error' in message_lower or 'failed' in message_lower or 'exception' in message_lower:
            return True

    # Check for Python-style stack traces
    if re.search(r'File "[^"]+\.py", line \d+', message):
        return True

    # Check for Go-style errors
    if re.search(r'\.go:\d+:\d+:', message):
        return True

    # Check for Rust-style errors
    if re.search(r'--> [^:]+\.rs:\d+:\d+', message):
        return True

    # Check for Java-style stack traces
    if re.search(r'at [\w.$]+\([^:]+\.java:\d+\)', message):
        return True

    return False


class LogStreamManager:
    """
    Manages WebSocket connections for log streaming.

    Each project can have multiple connected clients (browser previews).
    Logs are broadcast to LogBus and can be forwarded to monitoring clients.
    Auto-fix is triggered automatically when errors are detected!
    """

    def __init__(self):
        # project_id -> set of connected WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Monitoring connections (receive all logs)
        self.monitors: Set[WebSocket] = set()
        # Fix callback (set by application)
        self._fix_callback: Optional[callable] = None
        # Track pending auto-fix tasks
        self._pending_fixes: Dict[str, asyncio.Task] = {}

    def set_fix_callback(self, callback: callable):
        """Set the callback function for auto-fix"""
        self._fix_callback = callback
        logger.info("[LogStream] Auto-fix callback registered")

    async def connect(self, websocket: WebSocket, project_id: str):
        """Accept a new WebSocket connection for a project"""
        await websocket.accept()

        if project_id not in self.active_connections:
            self.active_connections[project_id] = set()

        self.active_connections[project_id].add(websocket)
        logger.info(f"[LogStream] Client connected for project {project_id}")

    async def connect_monitor(self, websocket: WebSocket):
        """Connect a monitoring client (receives all logs)"""
        await websocket.accept()
        self.monitors.add(websocket)
        logger.info("[LogStream] Monitor client connected")

    def disconnect(self, websocket: WebSocket, project_id: str = None):
        """Remove a WebSocket connection"""
        if project_id and project_id in self.active_connections:
            self.active_connections[project_id].discard(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]

        self.monitors.discard(websocket)
        logger.debug(f"[LogStream] Client disconnected")

    async def broadcast_to_monitors(self, message: dict):
        """Broadcast log to all monitoring clients"""
        dead_monitors = set()

        for monitor in self.monitors:
            try:
                await monitor.send_json(message)
            except Exception:
                dead_monitors.add(monitor)

        # Cleanup dead connections
        self.monitors -= dead_monitors

    async def broadcast_to_project(self, project_id: str, message: dict):
        """Broadcast message to all clients connected to a project"""
        if project_id not in self.active_connections:
            return

        dead_connections = set()
        for ws in self.active_connections[project_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.add(ws)

        # Cleanup dead connections
        self.active_connections[project_id] -= dead_connections

    async def trigger_auto_fix(self, project_id: str, is_error: bool = False):
        """
        Trigger auto-fix for a project if errors detected.

        This is the MAGIC that makes it feel automatic!
        Called after every error log is received.
        """
        if not is_error:
            logger.debug(f"[LogStream] trigger_auto_fix called for {project_id} but is_error=False")
            return

        if not self._fix_callback:
            logger.warning(f"[LogStream] Auto-fix callback not registered! Cannot auto-fix for {project_id}")
            return

        logger.info(f"[LogStream] Auto-fix triggered for project {project_id}")

        # Get auto-fixer for this project
        auto_fixer = get_auto_fixer(project_id)

        # Set up callbacks for fix events
        async def on_fix_started(pid: str, reason: str):
            await self.broadcast_to_project(pid, {
                "type": "fix_started",
                "reason": reason,
                "timestamp": datetime.utcnow().timestamp() * 1000
            })
            await self.broadcast_to_monitors({
                "type": "fix_started",
                "project_id": pid,
                "reason": reason,
                "timestamp": datetime.utcnow().timestamp() * 1000
            })

        async def on_fix_completed(pid: str, result: dict):
            await self.broadcast_to_project(pid, {
                "type": "fix_completed",
                "patches_applied": result.get("patches_applied", 0),
                "files_modified": result.get("files_modified", []),
                "timestamp": datetime.utcnow().timestamp() * 1000
            })
            await self.broadcast_to_monitors({
                "type": "fix_completed",
                "project_id": pid,
                "patches_applied": result.get("patches_applied", 0),
                "timestamp": datetime.utcnow().timestamp() * 1000
            })

        async def on_fix_failed(pid: str, error: str):
            await self.broadcast_to_project(pid, {
                "type": "fix_failed",
                "error": error,
                "timestamp": datetime.utcnow().timestamp() * 1000
            })

        auto_fixer.set_callbacks(
            on_started=on_fix_started,
            on_completed=on_fix_completed,
            on_failed=on_fix_failed
        )

        # Check and trigger fix (debounced)
        try:
            await auto_fixer.check_and_trigger(self._fix_callback)
        except Exception as e:
            logger.error(f"[LogStream] Auto-fix trigger failed: {e}")


# Global manager instance
log_stream_manager = LogStreamManager()


@router.websocket("/stream/{project_id}")
async def log_stream(websocket: WebSocket, project_id: str):
    """
    WebSocket endpoint for log streaming.

    Browser preview connects here and sends logs:
    {
        "source": "browser",
        "type": "runtime_error" | "console_error" | "fetch_error" | ...,
        "data": { ... },
        "timestamp": 1234567890
    }

    Logs are stored in LogBus for Fixer Agent.
    """
    await log_stream_manager.connect(websocket, project_id)
    log_bus = get_log_bus(project_id)

    try:
        while True:
            # Receive log message
            data = await websocket.receive_text()

            try:
                log_entry = json.loads(data)

                source = log_entry.get("source", "browser")
                log_type = log_entry.get("type", "unknown")
                log_data = log_entry.get("data", {})
                timestamp = log_entry.get("timestamp", datetime.utcnow().timestamp() * 1000)

                # Log received message for debugging
                message_preview = str(log_data.get("message", log_data))[:100]
                logger.info(f"[LogStream] 📥 RECEIVED from {project_id}: source={source}, type={log_type}, message={message_preview}")

                # Route to appropriate LogBus method
                if source == "browser":
                    if log_type == "runtime_error":
                        logger.info(f"[LogStream] 🔴 BROWSER RUNTIME ERROR for {project_id}: {log_data.get('message', '')[:150]}")
                        log_bus.add_browser_error(
                            message=log_data.get("message", "Unknown error"),
                            file=log_data.get("file"),
                            line=log_data.get("line"),
                            column=log_data.get("column"),
                            stack=log_data.get("stack")
                        )
                    elif log_type == "console_error":
                        args = log_data.get("args", [])
                        message = " ".join(str(a) for a in args)
                        log_bus.add_browser_error(message=message)
                    elif log_type == "promise_rejection":
                        log_bus.add_browser_error(
                            message=log_data.get("message", "Unhandled promise rejection"),
                            stack=log_data.get("stack")
                        )
                    elif log_type in ("fetch_error", "fetch_exception"):
                        log_bus.add_network_error(
                            message=log_data.get("error", f"HTTP {log_data.get('status', '?')}"),
                            url=log_data.get("url", ""),
                            status=log_data.get("status"),
                            method="GET"
                        )
                    elif log_type == "xhr_error":
                        log_bus.add_network_error(
                            message="XHR request failed",
                            url=log_data.get("url", ""),
                            method=log_data.get("method", "GET")
                        )
                    else:
                        # Generic browser log
                        log_bus.add_log(
                            source="browser",
                            level="error" if "error" in log_type else "info",
                            message=str(log_data)
                        )

                elif source == "network":
                    logger.info(f"[LogStream] 🌐 NETWORK ERROR for {project_id}: {log_data.get('message', '')[:100]} URL={log_data.get('url', '')}")
                    log_bus.add_network_error(
                        message=log_data.get("message", "Network error"),
                        url=log_data.get("url", ""),
                        status=log_data.get("status"),
                        method=log_data.get("method", "GET")
                    )

                elif source == "build":
                    message_str = str(log_data.get("data", log_data))
                    if log_type == "stderr" or is_build_error(message_str):
                        log_bus.add_build_error(message=message_str)
                    else:
                        log_bus.add_build_log(message_str)

                elif source == "backend":
                    message_str = str(log_data.get("data", log_data))
                    # Check if this is actually a build error (Vite/Webpack from container)
                    if is_build_error(message_str):
                        log_bus.add_build_error(message=message_str)
                    elif log_type == "stderr" or "error" in message_str.lower():
                        log_bus.add_backend_error(message=message_str)
                    else:
                        log_bus.add_backend_log(message_str)

                elif source == "docker":
                    message_str = str(log_data.get("data", log_data))
                    # Check if this is actually a build error (Vite/Webpack from container)
                    if is_build_error(message_str):
                        log_bus.add_build_error(message=message_str)
                    elif log_type == "stderr" or "error" in message_str.lower():
                        log_bus.add_docker_error(message_str)
                    else:
                        log_bus.add_docker_log(message_str)

                # Broadcast to monitors
                await log_stream_manager.broadcast_to_monitors({
                    "project_id": project_id,
                    "source": source,
                    "type": log_type,
                    "data": log_data,
                    "timestamp": timestamp
                })

                # ======= AUTO-FIX TRIGGER (Bolt.new Magic!) =======
                # Check if this was an error and trigger auto-fix
                message_for_check = str(log_data.get("data", log_data.get("message", "")))
                is_error_type = (
                    "error" in log_type.lower() or
                    log_type in ("runtime_error", "promise_rejection", "console_error", "stderr")
                )
                is_error = is_error_type or is_build_error(message_for_check)

                if is_error:
                    logger.info(f"[LogStream] 🔧 ERROR DETECTED - triggering auto-fix for {project_id}")
                    logger.info(f"[LogStream]    type={log_type}, is_error_type={is_error_type}, is_build_error={is_build_error(message_for_check)}")
                    # Trigger auto-fix in background (debounced)
                    asyncio.create_task(
                        log_stream_manager.trigger_auto_fix(project_id, is_error=True)
                    )
                else:
                    logger.debug(f"[LogStream] Non-error log from {project_id}: {log_type}")

            except json.JSONDecodeError:
                logger.warning(f"[LogStream] Invalid JSON received: {data[:100]}")
            except Exception as e:
                logger.error(f"[LogStream] Error processing log: {e}")

    except WebSocketDisconnect:
        log_stream_manager.disconnect(websocket, project_id)
    except Exception as e:
        logger.error(f"[LogStream] Connection error: {e}")
        log_stream_manager.disconnect(websocket, project_id)


@router.websocket("/monitor")
async def log_monitor(websocket: WebSocket):
    """
    WebSocket endpoint for monitoring all logs.

    DevTools/admin can connect here to see all project logs in real-time.
    """
    await log_stream_manager.connect_monitor(websocket)

    try:
        while True:
            # Keep connection alive, receive any commands
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_text("pong")
            elif data == "get_stats":
                stats = {
                    "active_projects": len(log_stream_manager.active_connections),
                    "total_connections": sum(
                        len(conns) for conns in log_stream_manager.active_connections.values()
                    ),
                    "monitors": len(log_stream_manager.monitors)
                }
                await websocket.send_json(stats)

    except WebSocketDisconnect:
        log_stream_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"[LogStream] Monitor error: {e}")
        log_stream_manager.disconnect(websocket)


@router.get("/status")
async def log_stream_status():
    """Get status of log streaming connections"""
    return {
        "active_projects": list(log_stream_manager.active_connections.keys()),
        "connection_counts": {
            pid: len(conns)
            for pid, conns in log_stream_manager.active_connections.items()
        },
        "monitor_count": len(log_stream_manager.monitors),
        "auto_fix_enabled": log_stream_manager._fix_callback is not None
    }


@router.get("/auto-fix/{project_id}/status")
async def get_auto_fix_status(project_id: str):
    """
    Get auto-fix status for a project.

    Returns current status, configuration, and tracked errors.
    """
    auto_fixer = get_auto_fixer(project_id)
    return {
        "project_id": project_id,
        "status": auto_fixer.get_status()
    }


@router.post("/auto-fix/{project_id}/configure")
async def configure_auto_fix(
    project_id: str,
    enabled: bool = True,
    debounce_seconds: float = 2.0,
    cooldown_seconds: float = 10.0,
    max_attempts: int = 3
):
    """
    Configure auto-fix for a project.

    Args:
        enabled: Enable/disable auto-fix
        debounce_seconds: Wait time before triggering fix (lets errors accumulate)
        cooldown_seconds: Minimum time between fix attempts
        max_attempts: Max fix attempts per error before giving up
    """
    auto_fixer = get_auto_fixer(project_id)
    auto_fixer.config.enabled = enabled
    auto_fixer.config.debounce_seconds = debounce_seconds
    auto_fixer.config.cooldown_seconds = cooldown_seconds
    auto_fixer.config.max_attempts_per_error = max_attempts

    logger.info(f"[AutoFix:{project_id}] Configured: enabled={enabled}, debounce={debounce_seconds}s, cooldown={cooldown_seconds}s")

    return {
        "project_id": project_id,
        "config": {
            "enabled": enabled,
            "debounce_seconds": debounce_seconds,
            "cooldown_seconds": cooldown_seconds,
            "max_attempts": max_attempts
        }
    }


@router.post("/auto-fix/{project_id}/reset")
async def reset_auto_fix(project_id: str):
    """
    Reset auto-fix attempts for a project.

    Use this after making manual changes to allow auto-fix to retry.
    """
    auto_fixer = get_auto_fixer(project_id)
    auto_fixer.reset_attempts()

    logger.info(f"[AutoFix:{project_id}] Reset fix attempts")

    return {
        "project_id": project_id,
        "message": "Auto-fix attempts reset"
    }


class ForwardLogRequest(BaseModel):
    """Request to forward a log entry to LogBus"""
    source: str  # browser, build, backend, docker, network
    type: str  # runtime_error, console_error, fetch_error, etc.
    data: dict  # Error data
    timestamp: Optional[int] = None


@router.post("/forward/{project_id}")
async def forward_log_entry(project_id: str, request: ForwardLogRequest):
    """
    Forward a log entry from frontend to LogBus.

    This is a fallback for when WebSocket connection is not available.
    Used by static preview (srcdoc) which cannot connect to WebSocket.

    After adding the log, triggers auto-fix if it's an error.
    """
    log_bus = get_log_bus(project_id)

    source = request.source
    log_type = request.type
    log_data = request.data

    # Route to appropriate LogBus method based on source
    is_error = False

    if source == "browser":
        if log_type in ("runtime_error", "console_error", "promise_rejection"):
            log_bus.add_browser_error(
                message=log_data.get("message", "Unknown error"),
                file=log_data.get("file"),
                line=log_data.get("line"),
                column=log_data.get("column"),
                stack=log_data.get("stack")
            )
            is_error = True
        else:
            log_bus.add_log(source="browser", level="info", message=str(log_data))

    elif source == "build":
        message_str = str(log_data.get("message", log_data))
        if log_type == "stderr" or is_build_error(message_str):
            log_bus.add_build_error(message=message_str)
            is_error = True
        else:
            log_bus.add_build_log(message_str)

    elif source == "network":
        log_bus.add_network_error(
            message=log_data.get("message", "Network error"),
            url=log_data.get("url", ""),
            status=log_data.get("status"),
            method=log_data.get("method", "GET")
        )
        is_error = True

    elif source == "backend":
        message_str = str(log_data.get("message", log_data))
        if is_build_error(message_str):
            log_bus.add_build_error(message=message_str)
            is_error = True
        elif "error" in message_str.lower():
            log_bus.add_backend_error(message=message_str)
            is_error = True
        else:
            log_bus.add_backend_log(message_str)

    elif source == "docker":
        message_str = str(log_data.get("message", log_data))
        if is_build_error(message_str):
            log_bus.add_build_error(message=message_str)
            is_error = True
        elif "error" in message_str.lower():
            log_bus.add_docker_error(message_str)
            is_error = True
        else:
            log_bus.add_docker_log(message_str)

    logger.info(f"[LogStream] Forwarded log from REST: {source}/{log_type}, is_error={is_error}")

    # Trigger auto-fix if it was an error
    if is_error:
        asyncio.create_task(
            log_stream_manager.trigger_auto_fix(project_id, is_error=True)
        )

    return {
        "success": True,
        "project_id": project_id,
        "source": source,
        "type": log_type,
        "auto_fix_triggered": is_error
    }


@router.post("/auto-fix/{project_id}/trigger")
async def trigger_auto_fix_manually(project_id: str):
    """
    Manually trigger auto-fix for a project.

    This is useful for testing or when auto-fix didn't trigger automatically.
    """
    if not log_stream_manager._fix_callback:
        return {
            "success": False,
            "error": "Auto-fix callback not registered"
        }

    auto_fixer = get_auto_fixer(project_id)

    # Force check and trigger
    triggered = await auto_fixer.check_and_trigger(log_stream_manager._fix_callback)

    return {
        "project_id": project_id,
        "triggered": triggered,
        "message": "Auto-fix triggered" if triggered else "No fixable errors detected"
    }
