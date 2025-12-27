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
import os
import tempfile
import shutil
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
from app.models.user import User
from app.services.log_bus import LogBus, get_log_bus
from app.services.auto_fixer import get_auto_fixer
from app.core.config import settings
from app.core.logging_config import logger
from pathlib import Path

# Check if we're in remote Docker mode
IS_REMOTE_SANDBOX = bool(os.environ.get("SANDBOX_DOCKER_HOST"))

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

            # IMPORTANT: Include actual docker/build errors from LogBus for better context
            docker_errors = log_bus.get_errors(source="docker")
            build_errors = log_bus.get_errors(source="build")
            if docker_errors or build_errors:
                all_error_entries = docker_errors + build_errors
                # Extract messages from error dicts, get last 20 for context
                error_messages = [e.get("message", "") for e in all_error_entries if e.get("level") == "error"]
                if error_messages:
                    error_logs = "\n".join(error_messages[-20:])
                    if error_logs and error_logs not in error_context:
                        error_context = f"{error_context}\n\nActual error output:\n{error_logs}"
                        logger.info(f"[ErrorHandler:{project_id}] Added {len(error_messages)} error logs to context")

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
    temp_dir = None
    try:
        # Find project path - handle remote sandbox mode
        project_path = None

        if IS_REMOTE_SANDBOX:
            # Remote sandbox mode: files are on EC2, need to restore from database
            logger.info(f"[ErrorHandler:{project_id}] Remote sandbox mode - restoring files from database")

            try:
                from app.services.unified_storage import UnifiedStorageService
                from app.core.database import AsyncSessionLocal

                # Create temp directory for fixer to work with
                temp_dir = tempfile.mkdtemp(prefix=f"fixer_{project_id[:8]}_")
                project_path = Path(temp_dir)

                # Restore files from database to temp directory
                async with AsyncSessionLocal() as db_session:
                    unified_storage = UnifiedStorageService()
                    restored_count = await unified_storage.restore_project_to_local(
                        db=db_session,
                        project_id=project_id,
                        target_path=project_path,
                        user_id=user_id
                    )
                    logger.info(f"[ErrorHandler:{project_id}] Restored {restored_count} files to temp directory")

            except Exception as restore_err:
                logger.error(f"[ErrorHandler:{project_id}] Failed to restore files: {restore_err}")
                import traceback
                logger.error(traceback.format_exc())
                # Try to get files directly from database as fallback
                project_path = None
        else:
            # Local mode: files are on the same machine
            project_path = Path(settings.USER_PROJECTS_PATH) / project_id

            if not project_path.exists():
                # Try sandbox path
                sandbox_base = Path(settings.SANDBOX_PATH) if hasattr(settings, 'SANDBOX_PATH') else Path("/tmp/sandbox/workspace")
                try:
                    for user_dir in sandbox_base.iterdir():
                        if user_dir.is_dir():
                            potential_path = user_dir / project_id
                            if potential_path.exists():
                                project_path = potential_path
                                break
                except FileNotFoundError:
                    logger.warning(f"[ErrorHandler:{project_id}] Sandbox path not found: {sandbox_base}")

        if project_path is None or not project_path.exists():
            logger.error(f"[ErrorHandler:{project_id}] Project path not found")
            await notify_fix_failed(project_id, "Could not find project files for auto-fix")
            return

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

            # Sync modified files: FIRST to running container, THEN to S3/DB
            try:
                from app.services.unified_storage import UnifiedStorageService
                unified_storage = UnifiedStorageService()

                for file_path in result.files_modified:
                    try:
                        full_path = project_path / file_path
                        if full_path.exists():
                            content = full_path.read_text(encoding='utf-8', errors='ignore')

                            # STEP 1: Sync to RUNNING CONTAINER first (for immediate HMR effect)
                            if IS_REMOTE_SANDBOX and user_id:
                                try:
                                    container_synced = await unified_storage._write_to_remote_sandbox(
                                        project_id=project_id,
                                        file_path=file_path,
                                        content=content,
                                        user_id=user_id
                                    )
                                    if container_synced:
                                        logger.info(f"[ErrorHandler:{project_id}] ✓ Synced to CONTAINER: {file_path}")
                                    else:
                                        logger.warning(f"[ErrorHandler:{project_id}] Container sync failed: {file_path}")
                                except Exception as container_err:
                                    logger.warning(f"[ErrorHandler:{project_id}] Container sync error for {file_path}: {container_err}")

                            # STEP 2: Save to database (Layer 3) for persistence
                            db_saved = await unified_storage.save_to_database(project_id, file_path, content)
                            if db_saved:
                                logger.info(f"[ErrorHandler:{project_id}] Synced to DB: {file_path}")

                            # STEP 3: Save to S3 (Layer 2) for persistence
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

                logger.info(f"[ErrorHandler:{project_id}] Synced {len(result.files_modified)} fixed files to Container + DB + S3")

                # STEP 4: If package.json was modified, run npm install in container
                package_json_modified = any(
                    'package.json' in f and 'package-lock.json' not in f
                    for f in result.files_modified
                )
                if package_json_modified and IS_REMOTE_SANDBOX and user_id:
                    try:
                        from app.services.container_executor import container_executor

                        # Find the working directory (frontend/ or root)
                        pkg_file = next((f for f in result.files_modified if 'package.json' in f), None)
                        work_dir = "/app"
                        if pkg_file and '/' in pkg_file:
                            # e.g., frontend/package.json -> /app/frontend
                            work_dir = f"/app/{pkg_file.rsplit('/', 1)[0]}"

                        logger.info(f"[ErrorHandler:{project_id}] Running npm install in container (workdir={work_dir})")

                        # Find the container for this project
                        container = await container_executor._get_existing_container(project_id)
                        if container:
                            # Run npm install in the container
                            exit_code, output = container.exec_run(
                                f"sh -c 'cd {work_dir} && npm install --legacy-peer-deps 2>&1'",
                                workdir="/app",
                                demux=True
                            )
                            stdout = output[0].decode('utf-8') if output[0] else ""
                            stderr = output[1].decode('utf-8') if output[1] else ""
                            full_output = stdout + stderr

                            if exit_code == 0:
                                logger.info(f"[ErrorHandler:{project_id}] ✓ npm install completed successfully")
                            else:
                                logger.warning(f"[ErrorHandler:{project_id}] npm install exit code: {exit_code}")
                                logger.warning(f"[ErrorHandler:{project_id}] npm install output: {full_output[:500]}")
                        else:
                            logger.warning(f"[ErrorHandler:{project_id}] Container not found for npm install")
                    except Exception as npm_err:
                        logger.warning(f"[ErrorHandler:{project_id}] Failed to run npm install: {npm_err}")

            except Exception as storage_err:
                logger.warning(f"[ErrorHandler:{project_id}] Storage sync error: {storage_err}")


            # STEP 5: Auto-rebuild after fixes - trigger container to rebuild
            if result.files_modified and IS_REMOTE_SANDBOX and user_id:
                try:
                    from app.services.container_executor import container_executor

                    logger.info(f"[ErrorHandler:{project_id}] Triggering auto-rebuild after fix...")

                    # Notify frontend that rebuild is starting
                    await notify_rebuild_started(project_id)

                    # Ensure docker client is initialized for container lookup
                    if not container_executor.docker_client:
                        logger.info(f"[ErrorHandler:{project_id}] Initializing docker client for auto-rebuild...")
                        await container_executor.initialize()

                    # Find the container by project_id label
                    container = await container_executor._get_existing_container(project_id)
                    if container:
                        # Kill any existing dev server and restart it
                        has_frontend = any('frontend/' in f for f in result.files_modified)
                        work_dir = "/app/frontend" if has_frontend else "/app"

                        # Kill existing node processes and restart dev server
                        logger.info(f"[ErrorHandler:{project_id}] Restarting dev server in {work_dir}")

                        # Kill existing processes (wait for completion)
                        container.exec_run("pkill -f 'node.*vite' || true", detach=False)
                        container.exec_run("pkill -f 'npm.*dev' || true", detach=False)

                        await asyncio.sleep(2)

                        # Start the dev server in the background with proper host binding
                        start_cmd = f"sh -c 'cd {work_dir} && nohup npm run dev -- --host 0.0.0.0 > /tmp/dev.log 2>&1 &'"
                        container.exec_run(start_cmd, workdir="/app", detach=True)

                        logger.info(f"[ErrorHandler:{project_id}] Dev server restart triggered, waiting for ready...")

                        # Wait for dev server to be ready (check logs for "ready" message)
                        max_wait = 15  # Max 15 seconds
                        ready = False
                        for i in range(max_wait):
                            await asyncio.sleep(1)
                            try:
                                # Check if Vite has started (look for "ready" or "Local:" in logs)
                                exit_code, output = container.exec_run(
                                    "cat /tmp/dev.log 2>/dev/null | tail -20",
                                    demux=True
                                )
                                log_output = ""
                                if output[0]:
                                    log_output = output[0].decode('utf-8', errors='ignore')

                                if 'ready in' in log_output.lower() or 'local:' in log_output.lower():
                                    logger.info(f"[ErrorHandler:{project_id}] Dev server ready after {i+1}s")
                                    ready = True
                                    break
                                elif 'error' in log_output.lower() and 'esbuild' not in log_output.lower():
                                    logger.warning(f"[ErrorHandler:{project_id}] Dev server error detected")
                                    break
                            except Exception as check_err:
                                logger.debug(f"[ErrorHandler:{project_id}] Log check error: {check_err}")

                        if not ready:
                            logger.warning(f"[ErrorHandler:{project_id}] Dev server may not be ready after {max_wait}s")

                        # Notify frontend that rebuild is complete
                        await notify_rebuild_completed(project_id, result.files_modified)
                    else:
                        logger.warning(f"[ErrorHandler:{project_id}] Container not found for auto-rebuild (project_id={project_id})")
                except Exception as rebuild_err:
                    logger.warning(f"[ErrorHandler:{project_id}] Auto-rebuild error: {rebuild_err}")
                    import traceback
                    logger.warning(traceback.format_exc())

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
    finally:
        # Clean up temp directory if we created one
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"[ErrorHandler:{project_id}] Cleaned up temp directory")
            except Exception as cleanup_err:
                logger.warning(f"[ErrorHandler:{project_id}] Failed to cleanup temp dir: {cleanup_err}")


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




async def notify_rebuild_started(project_id: str):
    """Notify WebSocket clients that auto-rebuild is starting"""
    await broadcast_to_project(project_id, {
        "type": "rebuild_started",
        "message": "Rebuilding project after fix...",
        "timestamp": datetime.now().isoformat()
    })


async def notify_rebuild_completed(project_id: str, files_modified: List[str]):
    """Notify WebSocket clients that auto-rebuild is complete"""
    await broadcast_to_project(project_id, {
        "type": "rebuild_completed",
        "files_modified": files_modified,
        "message": "Project rebuilt successfully. Preview is ready.",
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
        sandbox_base = Path(settings.SANDBOX_PATH) if hasattr(settings, 'SANDBOX_PATH') else Path("/tmp/sandbox/workspace")
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
