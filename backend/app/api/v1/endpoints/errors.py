"""
Unified Error Handler - Single Entry Point for All Errors

This module provides a centralized endpoint for receiving and processing
all types of errors from the frontend. It handles:
- Browser runtime errors
- Build/compile errors
- Docker container errors
- Network errors
- Backend errors

All errors are processed through the auto-fixer system automatically.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from app.services.fix_executor import FixExecutor
from app.services.log_bus import LogBus, get_log_bus
from app.services.auto_fixer import get_auto_fixer

logger = logging.getLogger(__name__)

router = APIRouter()


class ErrorSource(str, Enum):
    """Source of the error (Bolt.new-style comprehensive capture)"""
    BROWSER = "browser"      # JS runtime errors
    BUILD = "build"          # Build/compile errors
    DOCKER = "docker"        # Container errors
    NETWORK = "network"      # Fetch/XHR errors
    BACKEND = "backend"      # Backend API errors
    TERMINAL = "terminal"    # Terminal output errors
    # NEW: Bolt.new-style error sources
    REACT = "react"          # React component errors
    HMR = "hmr"              # Hot Module Replacement errors
    RESOURCE = "resource"    # Resource load errors (img/script/css)
    CSP = "csp"              # Content Security Policy violations
    MODULE = "module"        # Module loader errors


class ErrorSeverity(str, Enum):
    """Severity level of the error"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ErrorEntry(BaseModel):
    """Single error entry"""
    source: ErrorSource
    type: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    stack: Optional[str] = None
    severity: ErrorSeverity = ErrorSeverity.ERROR
    timestamp: Optional[int] = None


class RecentlyModifiedEntry(BaseModel):
    """Recently modified file entry"""
    path: str
    action: str  # 'created', 'updated', 'deleted'
    timestamp: int


class ErrorReportRequest(BaseModel):
    """Request body for error report"""
    errors: List[ErrorEntry]
    context: Optional[str] = None  # Full output context
    command: Optional[str] = None  # Command that was running
    timestamp: Optional[int] = None
    # Bolt.new-style fixer context
    file_tree: Optional[List[str]] = None  # All file paths in project
    recently_modified: Optional[List[RecentlyModifiedEntry]] = None  # Recently modified files


class ErrorReportResponse(BaseModel):
    """Response for error report"""
    success: bool
    project_id: str
    errors_received: int
    fix_triggered: bool
    fix_status: Optional[str] = None
    message: str


# WebSocket connections for real-time fix notifications
ws_connections: Dict[str, List[WebSocket]] = {}


@router.post("/report/{project_id}", response_model=ErrorReportResponse)
async def report_errors(project_id: str, request: ErrorReportRequest):
    """
    UNIFIED ERROR ENDPOINT - Single entry point for all errors

    This endpoint:
    1. Receives errors from all sources (browser, build, Docker, network)
    2. Logs them to the LogBus for tracking
    3. Triggers the auto-fixer automatically
    4. Returns fix status

    Usage:
    ```
    POST /api/v1/errors/report/{project_id}
    {
        "errors": [
            {
                "source": "build",
                "type": "compile_error",
                "message": "Module not found: Cannot find module 'react'",
                "file": "src/App.tsx",
                "line": 1,
                "severity": "error"
            }
        ],
        "context": "Full terminal output for context...",
        "command": "npm run dev"
    }
    ```
    """
    if not request.errors:
        return ErrorReportResponse(
            success=True,
            project_id=project_id,
            errors_received=0,
            fix_triggered=False,
            message="No errors to process"
        )

    logger.info(f"[ErrorHandler:{project_id}] Received {len(request.errors)} errors")

    # Get LogBus for this project
    log_bus = get_log_bus(project_id)

    # Process each error and add to LogBus
    has_fixable_error = False
    primary_error = None

    for error in request.errors:
        logger.info(f"[ErrorHandler:{project_id}] Processing error: {error.source}/{error.type} - {error.message[:100]}")

        # Add to appropriate LogBus method based on source
        if error.source == ErrorSource.BROWSER:
            log_bus.add_browser_error(
                message=error.message,
                file=error.file,
                line=error.line,
                column=error.column,
                stack=error.stack
            )
            has_fixable_error = True
            if not primary_error:
                primary_error = error

        elif error.source == ErrorSource.BUILD:
            log_bus.add_build_error(message=error.message)
            has_fixable_error = True
            if not primary_error:
                primary_error = error

        elif error.source == ErrorSource.DOCKER:
            log_bus.add_docker_error(message=error.message)
            has_fixable_error = True
            if not primary_error:
                primary_error = error

        elif error.source == ErrorSource.NETWORK:
            log_bus.add_network_error(
                message=error.message,
                url=error.file or "",  # file field may contain URL
                status=error.line,  # line field may contain status code
                method="GET"
            )
            # Network errors are usually not auto-fixable

        elif error.source == ErrorSource.BACKEND:
            log_bus.add_backend_error(message=error.message)
            has_fixable_error = True
            if not primary_error:
                primary_error = error

        # ===== NEW: Bolt.new-style error sources =====
        elif error.source == ErrorSource.REACT:
            # React component errors (render errors, hook errors)
            log_bus.add_browser_error(
                message=f"[React] {error.message}",
                file=error.file,
                line=error.line,
                column=error.column,
                stack=error.stack
            )
            has_fixable_error = True
            if not primary_error:
                primary_error = error

        elif error.source == ErrorSource.HMR:
            # Hot Module Replacement errors (Vite/Webpack/Next.js)
            log_bus.add_build_error(message=f"[HMR] {error.message}")
            has_fixable_error = True
            if not primary_error:
                primary_error = error

        elif error.source == ErrorSource.RESOURCE:
            # Resource load errors (images, scripts, CSS)
            log_bus.add_browser_error(
                message=f"[Resource] {error.message}",
                file=error.file
            )
            has_fixable_error = True
            if not primary_error:
                primary_error = error

        elif error.source == ErrorSource.CSP:
            # Content Security Policy violations
            log_bus.add_browser_error(
                message=f"[CSP] {error.message}",
                file=error.file,
                line=error.line
            )
            # CSP errors might not be auto-fixable but log them
            has_fixable_error = False

        elif error.source == ErrorSource.MODULE:
            # Module loader errors (dynamic imports, missing modules)
            log_bus.add_build_error(message=f"[Module] {error.message}")
            has_fixable_error = True
            if not primary_error:
                primary_error = error

        elif error.source == ErrorSource.TERMINAL:
            # Terminal output errors
            log_bus.add_build_error(message=error.message)
            has_fixable_error = True
            if not primary_error:
                primary_error = error

    # Trigger auto-fix if we have fixable errors
    fix_triggered = False
    fix_status = None

    if has_fixable_error and primary_error:
        try:
            # Get the auto-fixer
            auto_fixer = get_auto_fixer(project_id)

            # Prepare error context
            error_context = request.context or primary_error.message
            stack_trace = primary_error.stack or ""

            # If we have full context, use it as the error message
            if request.context and len(request.context) > len(primary_error.message):
                error_context = request.context

            logger.info(f"[ErrorHandler:{project_id}] Triggering auto-fix...")
            logger.info(f"[ErrorHandler:{project_id}] Error: {error_context[:200]}")
            logger.info(f"[ErrorHandler:{project_id}] Command: {request.command}")

            # Notify WebSocket clients that fix is starting
            await notify_fix_started(project_id, primary_error.message[:100])

            # Trigger the fix (runs in background)
            # Include Bolt.new-style fixer context
            async def run_fix_with_logging():
                try:
                    logger.info(f"[ErrorHandler:{project_id}] 🔧 Starting background fix task...")
                    await execute_fix_with_notification(
                        project_id=project_id,
                        error_message=error_context,
                        stack_trace=stack_trace,
                        command=request.command,
                        file_tree=request.file_tree,
                        recently_modified=request.recently_modified
                    )
                    logger.info(f"[ErrorHandler:{project_id}] ✅ Background fix task completed")
                except Exception as e:
                    logger.error(f"[ErrorHandler:{project_id}] ❌ Background fix task FAILED: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            asyncio.create_task(run_fix_with_logging())

            fix_triggered = True
            fix_status = "fix_queued"

        except Exception as e:
            logger.error(f"[ErrorHandler:{project_id}] Failed to trigger auto-fix: {e}")
            fix_status = f"fix_error: {str(e)}"

    return ErrorReportResponse(
        success=True,
        project_id=project_id,
        errors_received=len(request.errors),
        fix_triggered=fix_triggered,
        fix_status=fix_status,
        message=f"Processed {len(request.errors)} errors" + (", fix triggered" if fix_triggered else "")
    )


async def execute_fix_with_notification(
    project_id: str,
    error_message: str,
    stack_trace: str,
    command: Optional[str] = None,
    file_tree: Optional[List[str]] = None,
    recently_modified: Optional[List[RecentlyModifiedEntry]] = None
):
    """Execute fix and send WebSocket notifications"""
    try:
        # Get fix executor
        fix_executor = FixExecutor(project_id)

        # Build context with Bolt.new-style fixer data
        context = {
            "command": command,
            "file_tree": file_tree,
            "recently_modified": [
                {"path": f.path, "action": f.action, "timestamp": f.timestamp}
                for f in (recently_modified or [])
            ] if recently_modified else []
        }

        # Execute the fix with enhanced context
        result = await fix_executor.execute_fix(
            error_message=error_message,
            stack_trace=stack_trace,
            command=command,
            context=context
        )

        if result.get("success"):
            patches_applied = result.get("patches_applied", 0)
            files_modified = result.get("files_modified", [])

            logger.info(f"[ErrorHandler:{project_id}] Fix completed: {patches_applied} patches")

            await notify_fix_completed(project_id, patches_applied, files_modified)
        else:
            error = result.get("error", "Unknown error")
            logger.warning(f"[ErrorHandler:{project_id}] Fix failed: {error}")

            await notify_fix_failed(project_id, error)

    except Exception as e:
        logger.error(f"[ErrorHandler:{project_id}] Fix execution error: {e}")
        await notify_fix_failed(project_id, str(e))


@router.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """
    WebSocket endpoint for real-time fix notifications

    Connect to receive:
    - fix_started: When auto-fix begins
    - fix_completed: When fix is successful
    - fix_failed: When fix fails
    """
    await websocket.accept()

    # Add to connections
    if project_id not in ws_connections:
        ws_connections[project_id] = []
    ws_connections[project_id].append(websocket)

    logger.info(f"[ErrorHandler:{project_id}] WebSocket connected")

    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()
            # Client can send ping/pong or other messages
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info(f"[ErrorHandler:{project_id}] WebSocket disconnected")
    finally:
        if project_id in ws_connections:
            ws_connections[project_id].remove(websocket)
            if not ws_connections[project_id]:
                del ws_connections[project_id]


async def notify_fix_started(project_id: str, reason: str):
    """Notify WebSocket clients that fix has started"""
    await broadcast_to_project(project_id, {
        "type": "fix_started",
        "reason": reason,
        "timestamp": datetime.now().isoformat()
    })


async def notify_fix_completed(project_id: str, patches_applied: int, files_modified: List[str]):
    """Notify WebSocket clients that fix is complete"""
    await broadcast_to_project(project_id, {
        "type": "fix_completed",
        "patches_applied": patches_applied,
        "files_modified": files_modified,
        "timestamp": datetime.now().isoformat()
    })


async def notify_fix_failed(project_id: str, error: str):
    """Notify WebSocket clients that fix failed"""
    await broadcast_to_project(project_id, {
        "type": "fix_failed",
        "error": error,
        "timestamp": datetime.now().isoformat()
    })


async def broadcast_to_project(project_id: str, message: dict):
    """Broadcast message to all WebSocket connections for a project"""
    import json

    if project_id not in ws_connections:
        return

    message_str = json.dumps(message)
    dead_connections = []

    for ws in ws_connections[project_id]:
        try:
            await ws.send_text(message_str)
        except Exception:
            dead_connections.append(ws)

    # Clean up dead connections
    for ws in dead_connections:
        ws_connections[project_id].remove(ws)


@router.get("/status/{project_id}")
async def get_error_status(project_id: str):
    """
    Get current error status for a project
    """
    log_bus = get_log_bus(project_id)
    auto_fixer = get_auto_fixer(project_id)

    # Get recent errors
    recent_errors = log_bus.get_recent_errors(limit=10)

    return {
        "project_id": project_id,
        "error_count": len(recent_errors),
        "recent_errors": recent_errors,
        "fix_attempts": auto_fixer.fix_attempts if hasattr(auto_fixer, 'fix_attempts') else 0,
        "is_fixing": auto_fixer.is_fixing if hasattr(auto_fixer, 'is_fixing') else False,
        "websocket_connections": len(ws_connections.get(project_id, []))
    }


@router.post("/reset/{project_id}")
async def reset_error_state(project_id: str):
    """
    Reset error state for a project
    Clears error history and reset fix attempts
    """
    log_bus = get_log_bus(project_id)
    auto_fixer = get_auto_fixer(project_id)

    # Clear LogBus
    log_bus.clear()

    # Reset auto-fixer
    auto_fixer.reset_attempts()

    logger.info(f"[ErrorHandler:{project_id}] Reset error state")

    return {
        "success": True,
        "project_id": project_id,
        "message": "Error state reset successfully"
    }
