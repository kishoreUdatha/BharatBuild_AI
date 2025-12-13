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
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.simple_fixer import simple_fixer
from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user_optional
from app.modules.auth.usage_limits import get_user_limits
from app.models import User
from app.services.log_bus import LogBus, get_log_bus
from app.services.auto_fixer import get_auto_fixer
from app.core.config import settings
from app.core.logging_config import logger
from pathlib import Path

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
async def report_errors(
    project_id: str,
    request: ErrorReportRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    UNIFIED ERROR ENDPOINT - Single entry point for all errors

    This endpoint:
    1. Receives errors from all sources (browser, build, Docker, network)
    2. Logs them to the LogBus for tracking
    3. Triggers the auto-fixer automatically (if user has bug_fixing feature)
    4. Returns fix status

    NOTE: Bug fixing requires Premium plan. Free users can see errors but cannot auto-fix.
    """
    # Check if user has bug_fixing feature enabled
    can_auto_fix = True
    if current_user:
        try:
            limits = await get_user_limits(current_user, db)
            feature_flags = limits.feature_flags or {}
            can_auto_fix = feature_flags.get("bug_fixing", False) or feature_flags.get("all", False)
        except Exception as e:
            logger.warning(f"[ErrorHandler:{project_id}] Could not check feature flags: {e}")
            can_auto_fix = False
    else:
        # No user = anonymous, block auto-fix
        can_auto_fix = False

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

    # Trigger auto-fix if we have fixable errors AND user has permission
    fix_triggered = False
    fix_status = None

    if has_fixable_error and primary_error:
        # Check if user can auto-fix
        if not can_auto_fix:
            logger.info(f"[ErrorHandler:{project_id}] Bug fixing blocked - upgrade required")
            return ErrorReportResponse(
                success=True,
                project_id=project_id,
                errors_received=len(request.errors),
                fix_triggered=False,
                fix_status="upgrade_required",
                message="Bug fixing requires Premium plan. Upgrade to automatically fix errors."
            )

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
            # Convert errors to dict format for SimpleFixer
            errors_for_fixer = [
                {
                    "source": str(e.source.value) if hasattr(e.source, 'value') else str(e.source),
                    "type": e.type,
                    "message": e.message,
                    "file": e.file,
                    "line": e.line,
                    "column": e.column,
                    "stack": e.stack,
                    "severity": str(e.severity.value) if hasattr(e.severity, 'value') else str(e.severity)
                }
                for e in request.errors
            ]

            # Get user_id for token tracking
            fix_user_id = str(current_user.id) if current_user else None

            async def run_fix_with_logging():
                try:
                    logger.info(f"[ErrorHandler:{project_id}] Starting SimpleFixer background task...")
                    await execute_fix_with_notification(
                        project_id=project_id,
                        errors=errors_for_fixer,
                        context=error_context,
                        command=request.command,
                        file_tree=request.file_tree,
                        recently_modified=request.recently_modified,
                        user_id=fix_user_id
                    )
                    logger.info(f"[ErrorHandler:{project_id}] SimpleFixer background task completed")
                except Exception as e:
                    logger.error(f"[ErrorHandler:{project_id}] SimpleFixer background task FAILED: {e}")
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
    errors: List[Dict],
    context: str = "",
    command: Optional[str] = None,
    file_tree: Optional[List[str]] = None,
    recently_modified: Optional[List[RecentlyModifiedEntry]] = None,
    user_id: Optional[str] = None
):
    """Execute fix using SimpleFixer and send WebSocket notifications"""
    try:
        # Find project path
        project_path = Path(settings.USER_PROJECTS_PATH) / project_id

        if not project_path.exists():
            # Try sandbox path
            sandbox_base = Path(settings.SANDBOX_PATH) if hasattr(settings, 'SANDBOX_PATH') else Path("C:/tmp/sandbox/workspace")
            for user_dir in sandbox_base.iterdir():
                if user_dir.is_dir():
                    potential_path = user_dir / project_id
                    if potential_path.exists():
                        project_path = potential_path
                        break

        logger.info(f"[ErrorHandler:{project_id}] Using SimpleFixer (Bolt.new style)")
        logger.info(f"[ErrorHandler:{project_id}] Project path: {project_path}")

        # Convert recently_modified to dict format
        recently_mod_dicts = [
            {"path": f.path, "action": f.action, "timestamp": f.timestamp}
            for f in (recently_modified or [])
        ] if recently_modified else None

        # Reset token tracking before fix
        simple_fixer.reset_token_tracking()

        # Use SimpleFixer for ALL errors
        result = await simple_fixer.fix_from_frontend(
            project_id=project_id,
            project_path=project_path,
            errors=errors,
            context=context,
            command=command,
            file_tree=file_tree,
            recently_modified=recently_mod_dicts
        )

        # Save token transaction after fix
        token_usage = simple_fixer.get_token_usage()
        if token_usage.get("total_tokens", 0) > 0 and user_id:
            try:
                from app.services.token_tracker import token_tracker
                from app.models.usage import AgentType, OperationType

                await token_tracker.log_transaction_simple(
                    user_id=user_id,
                    project_id=project_id,
                    agent_type=AgentType.FIXER,
                    operation=OperationType.AUTO_FIX,
                    model=token_usage.get("model", "haiku"),
                    input_tokens=token_usage.get("input_tokens", 0),
                    output_tokens=token_usage.get("output_tokens", 0),
                    metadata={
                        "call_count": token_usage.get("call_count", 0),
                        "source": "simple_fixer",
                        "files_modified": result.files_modified if result.success else []
                    }
                )
                logger.info(f"[ErrorHandler:{project_id}] Token usage saved: {token_usage.get('total_tokens', 0)} tokens")
            except Exception as token_err:
                logger.warning(f"[ErrorHandler:{project_id}] Failed to save token usage: {token_err}")

        if result.success and result.files_modified:
            logger.info(f"[ErrorHandler:{project_id}] SimpleFixer completed: {len(result.files_modified)} files")

            # Sync modified files to database and S3
            try:
                from app.services.unified_storage import UnifiedStorageService
                unified_storage = UnifiedStorageService()

                for file_path in result.files_modified:
                    try:
                        full_path = project_path / file_path
                        if full_path.exists():
                            content = full_path.read_text(encoding='utf-8', errors='ignore')

                            # Save to database (Layer 3)
                            db_saved = await unified_storage.save_to_database(project_id, file_path, content)
                            if db_saved:
                                logger.info(f"[ErrorHandler:{project_id}] Synced to DB: {file_path}")
                            else:
                                logger.warning(f"[ErrorHandler:{project_id}] DB sync failed: {file_path}")

                            # Save to S3 (Layer 2) if user_id is available
                            if user_id:
                                try:
                                    s3_result = await unified_storage.upload_to_s3(
                                        user_id=user_id,
                                        project_id=project_id,
                                        file_path=file_path,
                                        content=content
                                    )
                                    if s3_result.get('success'):
                                        logger.info(f"[ErrorHandler:{project_id}] Synced to S3: {file_path}")
                                except Exception as s3_err:
                                    logger.warning(f"[ErrorHandler:{project_id}] S3 sync failed for {file_path}: {s3_err}")

                    except Exception as sync_err:
                        logger.warning(f"[ErrorHandler:{project_id}] Failed to sync {file_path}: {sync_err}")

                logger.info(f"[ErrorHandler:{project_id}] Synced {len(result.files_modified)} fixed files to DB and S3")

            except Exception as storage_err:
                logger.warning(f"[ErrorHandler:{project_id}] Storage sync error: {storage_err}")

            await notify_fix_completed(project_id, result.patches_applied, result.files_modified)
        elif result.success:
            logger.info(f"[ErrorHandler:{project_id}] SimpleFixer: {result.message}")
            # No fix needed - don't notify as failed
        else:
            logger.warning(f"[ErrorHandler:{project_id}] SimpleFixer failed: {result.message}")
            await notify_fix_failed(project_id, result.message)

    except Exception as e:
        logger.error(f"[ErrorHandler:{project_id}] Fix execution error: {e}")
        import traceback
        logger.error(traceback.format_exc())
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


# ==================== COST OPTIMIZATION: User Confirmation Endpoints ====================

@router.get("/pending-fix/{project_id}")
async def get_pending_fix(project_id: str):
    """
    Get pending fix details for user confirmation.

    Returns fix details including:
    - Error summary
    - Complexity classification (simple/moderate/complex)
    - Estimated API cost
    - Command that triggered the error
    """
    pending = simple_fixer.get_pending_fix(project_id)
    if not pending:
        return {
            "has_pending_fix": False,
            "project_id": project_id
        }

    return {
        "has_pending_fix": True,
        "project_id": project_id,
        **pending
    }


@router.post("/approve-fix/{project_id}")
async def approve_fix(
    project_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Approve and execute a pending fix.

    User clicked "Fix" button after seeing the estimated cost.
    Executes the fix and returns results.
    """
    # Find project path
    project_path = Path(settings.USER_PROJECTS_PATH) / project_id

    if not project_path.exists():
        sandbox_base = Path(settings.SANDBOX_PATH) if hasattr(settings, 'SANDBOX_PATH') else Path("C:/tmp/sandbox/workspace")
        for user_dir in sandbox_base.iterdir():
            if user_dir.is_dir():
                potential_path = user_dir / project_id
                if potential_path.exists():
                    project_path = potential_path
                    break

    user_id = str(current_user.id) if current_user else None
    logger.info(f"[ErrorHandler:{project_id}] User approved fix, executing...")

    # Notify WebSocket clients
    await notify_fix_started(project_id, "User approved fix")

    try:
        # Reset token tracking before fix
        simple_fixer.reset_token_tracking()

        result = await simple_fixer.approve_and_execute_fix(project_id, project_path)

        if result.success and result.files_modified:
            # Sync modified files to database and S3
            try:
                from app.services.unified_storage import UnifiedStorageService
                unified_storage = UnifiedStorageService()

                for file_path in result.files_modified:
                    try:
                        full_path = project_path / file_path
                        if full_path.exists():
                            content = full_path.read_text(encoding='utf-8', errors='ignore')

                            # Save to database (Layer 3)
                            db_saved = await unified_storage.save_to_database(project_id, file_path, content)
                            if db_saved:
                                logger.info(f"[ErrorHandler:{project_id}] Synced to DB: {file_path}")

                            # Save to S3 (Layer 2) if user_id is available
                            if user_id:
                                try:
                                    s3_result = await unified_storage.upload_to_s3(
                                        user_id=user_id,
                                        project_id=project_id,
                                        file_path=file_path,
                                        content=content
                                    )
                                    if s3_result.get('success'):
                                        logger.info(f"[ErrorHandler:{project_id}] Synced to S3: {file_path}")
                                except Exception as s3_err:
                                    logger.warning(f"[ErrorHandler:{project_id}] S3 sync failed for {file_path}: {s3_err}")

                    except Exception as sync_err:
                        logger.warning(f"[ErrorHandler:{project_id}] Failed to sync {file_path}: {sync_err}")

                logger.info(f"[ErrorHandler:{project_id}] Synced {len(result.files_modified)} fixed files to DB and S3")
            except Exception as storage_err:
                logger.warning(f"[ErrorHandler:{project_id}] Storage sync error: {storage_err}")

            # Save token transaction
            token_usage = simple_fixer.get_token_usage()
            if token_usage.get("total_tokens", 0) > 0 and user_id:
                try:
                    from app.services.token_tracker import token_tracker
                    from app.models.usage import AgentType, OperationType

                    await token_tracker.log_transaction_simple(
                        user_id=user_id,
                        project_id=project_id,
                        agent_type=AgentType.FIXER,
                        operation=OperationType.AUTO_FIX,
                        model=token_usage.get("model", "haiku"),
                        input_tokens=token_usage.get("input_tokens", 0),
                        output_tokens=token_usage.get("output_tokens", 0),
                        metadata={
                            "call_count": token_usage.get("call_count", 0),
                            "source": "simple_fixer_approved",
                            "files_modified": result.files_modified
                        }
                    )
                    logger.info(f"[ErrorHandler:{project_id}] Token usage saved: {token_usage.get('total_tokens', 0)} tokens")
                except Exception as token_err:
                    logger.warning(f"[ErrorHandler:{project_id}] Failed to save token usage: {token_err}")

            await notify_fix_completed(project_id, result.patches_applied, result.files_modified)
        elif result.success:
            await notify_fix_completed(project_id, result.patches_applied, result.files_modified)
        else:
            await notify_fix_failed(project_id, result.message)

        return {
            "success": result.success,
            "project_id": project_id,
            "files_modified": result.files_modified,
            "patches_applied": result.patches_applied,
            "message": result.message
        }

    except Exception as e:
        logger.error(f"[ErrorHandler:{project_id}] Approved fix failed: {e}")
        await notify_fix_failed(project_id, str(e))
        return {
            "success": False,
            "project_id": project_id,
            "message": str(e)
        }


@router.post("/cancel-fix/{project_id}")
async def cancel_fix(project_id: str):
    """
    Cancel a pending fix.

    User decided not to proceed with the fix (to save API costs).
    """
    cancelled = simple_fixer.cancel_pending_fix(project_id)

    return {
        "success": cancelled,
        "project_id": project_id,
        "message": "Fix cancelled" if cancelled else "No pending fix found"
    }


@router.post("/set-auto-fix-mode")
async def set_auto_fix_mode(enabled: bool):
    """
    Toggle auto-fix mode.

    - enabled=True: Fix errors immediately (current behavior)
    - enabled=False: Queue fixes for user confirmation (Bolt.new style - saves costs)
    """
    simple_fixer.auto_fix_enabled = enabled
    logger.info(f"[ErrorHandler] Auto-fix mode set to: {enabled}")

    return {
        "success": True,
        "auto_fix_enabled": enabled,
        "message": f"Auto-fix {'enabled' if enabled else 'disabled (fixes will require confirmation)'}"
    }


@router.get("/auto-fix-mode")
async def get_auto_fix_mode():
    """Get current auto-fix mode setting"""
    return {
        "auto_fix_enabled": simple_fixer.auto_fix_enabled,
        "message": "Auto-fix is " + ("enabled" if simple_fixer.auto_fix_enabled else "disabled (requires confirmation)")
    }
