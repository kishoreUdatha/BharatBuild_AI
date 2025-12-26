"""
Project Execution API - Run and execute generated projects in Docker containers

This module provides Docker-based project execution with:
1. Auto-generated Dockerfile if missing
2. Automatic port detection from container logs
3. Live preview URL for iframe embedding
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse, Response
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
import asyncio
import json
import zipfile
import io

from app.core.database import get_db
from app.core.logging_config import logger
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.modules.auth.dependencies import get_current_user, get_optional_user
from app.modules.auth.feature_flags import require_feature
from app.modules.orchestrator.dynamic_orchestrator import dynamic_orchestrator, ExecutionContext, OrchestratorEvent
from app.modules.automation.file_manager import FileManager
from app.modules.agents.production_fixer_agent import production_fixer_agent
from app.modules.agents.base_agent import AgentContext
from app.modules.execution.docker_executor import docker_executor, docker_compose_executor, FrameworkType, DEFAULT_PORTS
from app.services.unified_storage import unified_storage
from app.services.sandbox_cleanup import touch_project
from app.services.log_bus import get_log_bus

# Store running processes by project_id for stop functionality
_running_processes: dict[str, asyncio.subprocess.Process] = {}

# File manager instance for fallback
_file_manager = FileManager()


import os as _os

async def get_project_path_async(project_id: str, user_id: str = None):
    """
    Async version: Get project path - checks sandbox (local or EC2),
    restores from DB/S3 if needed, then falls back to permanent storage.

    When SANDBOX_DOCKER_HOST is set, files are on EC2, not local ECS.
    This function will:
    1. Check if files exist on EC2 sandbox
    2. If not, restore from DB/S3 to EC2
    3. Return the sandbox path for Docker to use

    Args:
        project_id: Project UUID string
        user_id: User UUID string (required for correct sandbox path)
    """
    from pathlib import Path

    sandbox_path = unified_storage.get_sandbox_path(project_id, user_id)
    sandbox_docker_host = _os.environ.get("SANDBOX_DOCKER_HOST")

    # Check if using remote EC2 sandbox
    if sandbox_docker_host:
        # Check if sandbox exists on EC2
        exists_on_ec2 = await unified_storage.sandbox_exists(project_id, user_id)

        if not exists_on_ec2:
            # Try to restore from DB/S3 to EC2
            logger.info(f"[Execution] Sandbox not on EC2, restoring from DB/S3: {project_id}")
            try:
                restored_files = await unified_storage.restore_project_from_database(project_id, user_id)
                if restored_files:
                    logger.info(f"[Execution] Restored {len(restored_files)} files to EC2 for {project_id}")
                    return sandbox_path
                else:
                    logger.warning(f"[Execution] No files restored for {project_id}")
            except Exception as e:
                logger.error(f"[Execution] Restore failed for {project_id}: {e}")

        else:
            logger.info(f"[Execution] Sandbox exists on EC2: {project_id}")
            return sandbox_path
    else:
        # Local sandbox (ECS or development)
        if sandbox_path.exists():
            return sandbox_path

        # Try legacy path without user_id
        if user_id:
            legacy_sandbox_path = unified_storage.get_sandbox_path(project_id)
            if legacy_sandbox_path.exists():
                logger.warning(f"[Execution] Using legacy sandbox path for {project_id}")
                return legacy_sandbox_path

    # Fallback to permanent storage
    permanent_path = _file_manager.get_project_path(project_id)
    if permanent_path.exists():
        logger.info(f"[Execution] Using permanent storage for {project_id}")
        return permanent_path

    # Return sandbox path (will be checked for existence by caller)
    return sandbox_path


def get_project_path(project_id: str, user_id: str = None):
    """
    Sync wrapper for get_project_path_async.
    For backwards compatibility with non-async callers.

    NOTE: This only works for LOCAL sandbox checks.
    For EC2 sandbox, use get_project_path_async() instead.
    """
    from pathlib import Path

    # Try sandbox first with user_id (primary for execution)
    sandbox_path = unified_storage.get_sandbox_path(project_id, user_id)
    if sandbox_path.exists():
        return sandbox_path

    # If user_id provided but path doesn't exist, try without user_id for backward compat
    if user_id:
        legacy_sandbox_path = unified_storage.get_sandbox_path(project_id)
        if legacy_sandbox_path.exists():
            logger.warning(f"[Execution] Using legacy sandbox path for {project_id} (missing user_id prefix)")
            return legacy_sandbox_path

    # Fallback to permanent storage
    permanent_path = _file_manager.get_project_path(project_id)
    if permanent_path.exists():
        logger.info(f"[Execution] Using permanent storage for {project_id}")
        return permanent_path

    # Return sandbox path (will be checked for existence by caller)
    return sandbox_path


async def verify_project_ownership(project_id: str, current_user: User, db: AsyncSession) -> bool:
    """Helper function to verify project ownership"""
    try:
        # GUID columns are String(36), so compare as strings (not UUID)
        result = await db.execute(
            text("SELECT id FROM projects WHERE id = :project_id AND user_id = :user_id"),
            {"project_id": str(project_id), "user_id": str(current_user.id)}
        )
        return result.scalar_one_or_none() is not None
    except Exception as e:
        logger.warning(f"[Execution] verify_project_ownership error: {e}")
        return False

router = APIRouter()


class RunProjectRequest(BaseModel):
    project_id: str
    commands: Optional[List[str]] = None  # Optional: custom commands to run


class FixErrorRequest(BaseModel):
    """Request model for auto-fixing runtime errors (Bolt.new style)"""
    error_message: str
    stack_trace: Optional[str] = None
    error_type: Optional[str] = None  # syntax, runtime, import, type, logic
    affected_files: Optional[List[str]] = None  # Files mentioned in error
    command: Optional[str] = None  # Command that failed (npm run dev, etc.)
    error_logs: Optional[List[str]] = None  # Additional error logs from terminal


@router.post("/run/{project_id}")
async def run_project(
    project_id: str,
    request: Optional[RunProjectRequest] = None,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_feature("code_execution"))
):
    """
    Run/execute a generated project in Docker container

    This endpoint streams progress for:
    1. Checking project status
    2. Creating/preparing container
    3. Restoring project files (if needed)
    4. Installing dependencies
    5. Starting dev server
    6. Returns preview URL when ready

    If project has no generated files, returns error without running commands.
    """
    # Validate project_id format (UUID)
    import re
    uuid_pattern = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', re.IGNORECASE)
    if not uuid_pattern.match(project_id):
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_project_id", "message": "Invalid project ID format"}
        )

    # Verify project ownership (skip if no auth in dev mode)
    if current_user and not await verify_project_ownership(project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get user_id for the streaming function
    user_id = str(current_user.id) if current_user else None

    try:
        # Check if project has been generated (has files in database)
        from app.models.project_file import ProjectFile
        files_result = await db.execute(
            select(ProjectFile).where(ProjectFile.project_id == project_id).limit(1)
        )
        has_files = files_result.scalar_one_or_none() is not None
    except Exception as db_err:
        logger.error(f"[Execution] Database error checking files: {db_err}")
        raise HTTPException(
            status_code=500,
            detail={"error": "database_error", "message": "Failed to check project files"}
        )

    if not has_files:
        try:
            # Check if project exists
            project_result = await db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = project_result.scalar_one_or_none()
        except Exception as db_err:
            logger.error(f"[Execution] Database error checking project: {db_err}")
            raise HTTPException(
                status_code=500,
                detail={"error": "database_error", "message": "Failed to check project status"}
            )

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if project.status in [ProjectStatus.DRAFT, ProjectStatus.PROCESSING]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "project_not_ready",
                    "message": "Project has not been generated yet. Please generate the project first.",
                    "status": project.status.value
                }
            )

    try:
        # Touch the project to keep it alive during execution (non-fatal if fails)
        try:
            touch_project(project_id)
        except Exception as touch_err:
            logger.warning(f"[Execution] touch_project failed in endpoint: {touch_err}")

        # Stream Docker execution with progress using sse-starlette
        # EventSourceResponse handles keepalive pings automatically
        return EventSourceResponse(
            _execute_docker_stream_with_progress(project_id, user_id, db),
            ping=1,  # Send ping every 1 second to keep connection alive
            ping_message_factory=lambda: {"comment": "keepalive"},
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop/{project_id}")
async def stop_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Stop a running project execution (Docker container).

    This endpoint stops the Docker container for the specified project.
    """
    # Verify project ownership (skip if no auth in dev mode)
    if current_user and not await verify_project_ownership(project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    try:
        # Use smart stop_project which handles both Docker and direct execution
        stopped = await docker_executor.stop_project(project_id)

        if stopped:
            logger.info(f"Stopped project: {project_id}")
            return {"status": "stopped", "message": "Project stopped successfully"}
        else:
            return {"status": "not_running", "message": "No running project found"}

    except Exception as e:
        logger.error(f"Error stopping project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix/{project_id}")
async def fix_runtime_error(
    project_id: str,
    request: FixErrorRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Auto-fix runtime errors using the AI Fixer Agent.

    This endpoint:
    1. Analyzes the error message and stack trace
    2. Identifies affected files
    3. Uses AI to generate fixes
    4. Returns fixed file contents to apply

    Returns:
    - success: bool
    - fixed_files: List of {path, content} objects
    - instructions: Optional shell commands to run (e.g., npm install)
    - analysis: Error analysis details
    """
    # Verify project ownership (skip if no auth in dev mode)
    if current_user and not await verify_project_ownership(project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    try:
        # Touch the project to keep it alive during fixing
        touch_project(project_id)

        # Get project path (sandbox first, then permanent storage)
        user_id = str(current_user.id) if current_user else None
        project_path = get_project_path(project_id, user_id)

        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        logger.info(f"[Fixer] Auto-fixing error for project: {project_id}")
        logger.info(f"[Fixer] Error: {request.error_message[:200]}...")
        logger.info(f"[Fixer] Command: {request.command}")

        # ============= BOLT.NEW STYLE: Use LogBus for context =============
        log_bus = get_log_bus(project_id)

        # Add error to LogBus (for tracking)
        log_bus.add_build_error(
            message=request.error_message,
            file=request.affected_files[0] if request.affected_files else None
        )

        # Add additional error logs if provided
        if request.error_logs:
            for error_log in request.error_logs:
                log_bus.add_build_log(error_log, level="error")

        # Get Bolt.new-style fixer payload with file context
        fixer_payload = log_bus.get_bolt_fixer_payload(
            project_path=str(project_path),
            command=request.command or "unknown",
            error_message=request.error_message
        )

        # Get all project files for context
        project_files = []
        file_contents = {}

        # Skip patterns - check BEFORE calling is_file() to avoid Windows file lock errors
        skip_patterns = ['node_modules', '__pycache__', '.git', '.env', 'dist', 'build', '.bin']

        for file_path in project_path.rglob("*"):
            try:
                # Get relative path first to check skip patterns
                rel_path = str(file_path.relative_to(project_path)).replace("\\", "/")

                # Skip certain directories and files BEFORE checking is_file()
                if any(pattern in rel_path for pattern in skip_patterns):
                    continue

                # Now safely check if it's a file (can fail with WinError 1920 on locked files)
                if not file_path.is_file():
                    continue

                project_files.append(rel_path)

                # Read file content if it might be affected
                # Only read source files to limit context size
                if any(ext in rel_path for ext in ['.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.html', '.css', '.yml', '.yaml']):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # Limit file size for context
                            if len(content) < 50000:
                                file_contents[rel_path] = content
                    except Exception as e:
                        logger.warning(f"Could not read file {rel_path}: {e}")

            except OSError as e:
                # Handle WinError 1920 and other OS errors for locked files
                # This is common on Windows when node_modules/.bin files are in use
                continue

        # Merge file contents from LogBus payload
        file_contents.update(fixer_payload.get("fileContext", {}))

        # Prepare context for fixer agent (Bolt.new style)
        context = AgentContext(
            project_id=project_id,
            user_request=f"Fix this error: {request.error_message}",
            metadata={
                "error_message": request.error_message,
                "stack_trace": request.stack_trace or "",
                "error_type": request.error_type,
                "affected_files": request.affected_files or fixer_payload.get("errorFiles", []),
                "project_files": project_files,
                "file_contents": file_contents,
                "project_path": str(project_path),
                # Bolt.new style additions
                "command": request.command or "unknown",
                "environment": fixer_payload.get("environment", {}),
                "error_logs": fixer_payload.get("errorLogs", {}),
                "package_json": fixer_payload.get("fileContext", {}).get("package.json"),
                "dockerfile": fixer_payload.get("fileContext", {}).get("Dockerfile"),
            }
        )

        # Call the fixer agent
        result = await production_fixer_agent.process(context)

        if not result.get("success"):
            logger.warning(f"Fixer agent failed: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error", "Failed to generate fix"),
                "suggestion": result.get("suggestion", "Manual intervention may be required")
            }

        # Process fixed files - save them to disk
        fixed_files = result.get("fixed_files", [])
        saved_files = []

        for file_info in fixed_files:
            file_path_str = file_info.get("path")
            content = file_info.get("content")

            if file_path_str and content:
                # Sanitize path: strip quotes and whitespace (defensive fix for quoted filenames)
                file_path_str = file_path_str.strip().strip('"').strip("'")
                # Ensure file path is within project
                full_path = project_path / file_path_str

                # Safety check: path must be within project
                try:
                    full_path.resolve().relative_to(project_path.resolve())
                except ValueError:
                    logger.error(f"Security: Attempted to write outside project: {file_path_str}")
                    continue

                # Create directory if needed
                full_path.parent.mkdir(parents=True, exist_ok=True)

                # Write the fixed content
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                saved_files.append({
                    "path": file_path_str,
                    "content": content,
                    "saved": True
                })
                logger.info(f"✅ Fixed and saved: {file_path_str}")

        # Build response
        response = {
            "success": True,
            "fixed_files": saved_files,
            "files_count": len(saved_files),
            "instructions": result.get("instructions"),
            "analysis": {
                "error_type": result.get("analysis", {}).error_type if hasattr(result.get("analysis"), "error_type") else None,
                "root_cause": result.get("analysis", {}).root_cause if hasattr(result.get("analysis"), "root_cause") else None,
                "confidence": result.get("analysis", {}).confidence if hasattr(result.get("analysis"), "confidence") else None
            } if result.get("analysis") else None
        }

        logger.info(f"🎉 Successfully fixed {len(saved_files)} files for project {project_id}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fixing project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _get_available_port(start_port: int = 3001) -> int:
    """Find an available port starting from start_port"""
    import socket
    port = start_port
    while port < 65535:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            port += 1
    return start_port


async def _execute_docker_stream_with_progress(project_id: str, user_id: str, db):
    """
    Execute project with step-by-step progress streaming.

    Uses sse-starlette EventSourceResponse for proper SSE handling.
    Yields dictionaries that get converted to SSE events automatically.

    Flow:
    1. Check project status
    2. Prepare/create container
    3. Restore project files (if needed)
    4. Install dependencies
    5. Start dev server
    6. Return preview URL

    All steps are streamed to the frontend for terminal display.
    """
    from pathlib import Path
    import re

    def emit(event_type: str, message: str = None, data: dict = None):
        """Helper to create SSE event dict for sse-starlette"""
        event = {"type": event_type}
        if message:
            event["message"] = message
            event["content"] = message
        if data:
            event["data"] = data
        # Return dict with 'data' key for EventSourceResponse
        return {"data": json.dumps(event)}

    def safe_parse_port(url: str, default: int = 3000) -> int:
        """Safely extract port from URL, with fallback"""
        try:
            if not url:
                return default
            port_match = re.search(r':(\d+)', url)
            if port_match:
                port = int(port_match.group(1))
                if 1 <= port <= 65535:
                    return port
            return default
        except (ValueError, AttributeError):
            return default

    try:
        # Send initial events immediately
        yield emit("output", "🖥️ Running directly on server...")
        yield emit("output", f"📂 Project ID: {project_id}")

        # Small delay to ensure events are flushed
        await asyncio.sleep(0.01)

        # Validate inputs
        if not project_id:
            yield emit("error", "Invalid project ID")
            return

        # Handle user_id being None (anonymous/dev mode)
        effective_user_id = user_id or "anonymous"

        logger.info(f"[SSE] Starting execution stream for {project_id}")

        # ==================== STEP 1: Check Project Status ====================
        yield emit("step", "Checking project status...", {"step": 1, "total": 5, "phase": "checking"})
        yield emit("output", "[1/5] Checking project status...")
        # keepalive handled by EventSourceResponse ping

        sandbox_docker_host = _os.environ.get("SANDBOX_DOCKER_HOST")
        project_path = None
        needs_restore = False
        restored_count = 0

        # Check if sandbox exists
        if sandbox_docker_host:
            # Remote EC2 sandbox
            try:
                exists_on_ec2 = await unified_storage.sandbox_exists(project_id, effective_user_id)
            except asyncio.TimeoutError:
                logger.warning(f"[Execution] sandbox_exists timed out for {project_id}")
                yield emit("output", "  Warning: Sandbox check timed out, will attempt restore")
                exists_on_ec2 = False
            except Exception as sandbox_err:
                logger.warning(f"[Execution] sandbox_exists check failed: {sandbox_err}")
                yield emit("output", "  Warning: Could not check sandbox, will attempt restore")
                exists_on_ec2 = False

            if exists_on_ec2:
                yield emit("output", "  Project files found in sandbox")
                project_path = unified_storage.get_sandbox_path(project_id, effective_user_id)
            else:
                yield emit("output", "  Project files not in sandbox, will restore from database")
                needs_restore = True
        else:
            # Local sandbox
            try:
                project_path = unified_storage.get_sandbox_path(project_id, effective_user_id)
                if project_path and project_path.exists():
                    has_package = (project_path / "package.json").exists()
                    has_requirements = (project_path / "requirements.txt").exists()
                    has_src = (project_path / "src").exists()
                    has_index = (project_path / "index.html").exists()
                    has_any_file = has_package or has_requirements or has_src or has_index

                    if has_any_file:
                        yield emit("output", "  Project files found in sandbox")
                    else:
                        yield emit("output", "  Sandbox empty, will restore from database")
                        needs_restore = True
                else:
                    yield emit("output", "  Sandbox not found, will restore from database")
                    needs_restore = True
            except Exception as path_err:
                logger.warning(f"[Execution] Error checking local sandbox: {path_err}")
                yield emit("output", "  Warning: Could not check sandbox, will attempt restore")
                needs_restore = True

        yield emit("step_complete", "Project status checked", {"step": 1})
        # keepalive handled by EventSourceResponse ping

        # ==================== STEP 2: Create/Prepare Container ====================
        yield emit("step", "Preparing container environment...", {"step": 2, "total": 5, "phase": "container"})
        yield emit("output", "\n[2/5] Preparing container environment...")

        try:
            touch_project(project_id)
        except Exception as touch_err:
            logger.warning(f"[Execution] touch_project failed: {touch_err}")

        yield emit("output", "  Container environment ready")
        yield emit("step_complete", "Container prepared", {"step": 2})
        # keepalive handled by EventSourceResponse ping

        # ==================== STEP 3: Restore Project Files (if needed) ====================
        if needs_restore:
            yield emit("step", "Restoring project files...", {"step": 3, "total": 5, "phase": "restore"})
            yield emit("output", "\n[3/5] Restoring project files from database...")
            # keepalive handled by EventSourceResponse ping

            try:
                from app.models.project_file import ProjectFile
                from app.core.database import async_session

                total_files = 0
                try:
                    async with async_session() as restore_db:
                        from sqlalchemy import select, func
                        count_result = await restore_db.execute(
                            select(func.count(ProjectFile.id)).where(ProjectFile.project_id == project_id)
                        )
                        total_files = count_result.scalar() or 0
                except Exception as count_err:
                    logger.warning(f"[Execution] Could not get file count: {count_err}")
                    total_files = 0

                if total_files > 0:
                    yield emit("output", f"  Found {total_files} files in database")
                else:
                    yield emit("output", "  Checking database for files...")

                # Restore files - EventSourceResponse handles keepalive automatically
                restored_files = await unified_storage.restore_project_from_database(project_id, effective_user_id)

                if restored_files:
                    restored_count = len(restored_files)
                    yield emit("output", f"  Restored {restored_count}/{total_files or restored_count} files to sandbox")
                    project_path = unified_storage.get_sandbox_path(project_id, effective_user_id)
                    yield emit("step_complete", f"Restored {restored_count} files", {"step": 3, "files_restored": restored_count})
                else:
                    yield emit("error", "No files found in database. Please regenerate the project.")
                    yield emit("output", "  ERROR: No files to restore")
                    return

            except asyncio.TimeoutError:
                yield emit("error", "Project restore timed out. Please try again.")
                return
            except Exception as restore_err:
                logger.error(f"[Execution] Restore failed: {restore_err}", exc_info=True)
                yield emit("error", f"Failed to restore project files: {str(restore_err)}")
                return
        else:
            yield emit("step", "Project files ready", {"step": 3, "total": 5, "phase": "restore"})
            yield emit("output", "\n[3/5] Project files already in sandbox")
            yield emit("step_complete", "Files ready", {"step": 3, "files_restored": 0})

        # keepalive handled by EventSourceResponse ping

        # ==================== STEP 4 & 5: Install & Run ====================
        yield emit("step", "Installing dependencies and starting server...", {"step": 4, "total": 5, "phase": "install"})
        yield emit("output", "\n[4/5] Installing dependencies...")
        # keepalive handled by EventSourceResponse ping

        if project_path is None:
            logger.error(f"[Execution] project_path is None for project {project_id}")
            yield emit("error", "Internal error: Project path not set. Please try again.")
            return

        try:
            if isinstance(project_path, str):
                project_path = Path(project_path)
        except Exception as path_err:
            logger.error(f"[Execution] Invalid project_path: {path_err}")
            yield emit("error", "Internal error: Invalid project path.")
            return

        # Execute Docker and stream output
        server_started = False
        preview_url = None
        docker_error = None
        output_count = 0
        max_outputs = 10000

        try:
            async for output in docker_executor.run_project(project_id, project_path, effective_user_id):
                output_count += 1
                if output_count > max_outputs:
                    logger.warning(f"[Execution] Max output count reached for {project_id}")
                    break

                if output is None:
                    continue
                if not isinstance(output, str):
                    try:
                        output = str(output)
                    except Exception:
                        continue

                # Check for server started markers
                if output.startswith("__SERVER_STARTED__:") or output.startswith("_PREVIEW_URL_:"):
                    try:
                        if output.startswith("__SERVER_STARTED__:"):
                            preview_url = output.split(":", 1)[1].strip()
                        else:
                            preview_url = output.split("_PREVIEW_URL_:", 1)[1].strip()
                        server_started = True

                        port = safe_parse_port(preview_url, 3000)

                        yield emit("step", "Starting dev server...", {"step": 5, "total": 5, "phase": "server"})
                        yield emit("output", "\n[5/5] Starting dev server...")
                        yield emit("output", f"  Server started on port {port}")
                        yield emit("server_started", None, {"port": port, "preview_url": preview_url})
                        yield emit("step_complete", "Server running", {"step": 5})
                    except Exception as parse_err:
                        logger.warning(f"[Execution] Error parsing server started marker: {parse_err}")

                elif "_PREVIEW_URL_:" in output:
                    try:
                        url_match = re.search(r'_PREVIEW_URL_:(.+?)(?:\n|$)', output)
                        if url_match:
                            preview_url = url_match.group(1).strip()
                            server_started = True
                            port = safe_parse_port(preview_url, 3000)
                            yield emit("server_started", None, {"port": port, "preview_url": preview_url})

                        clean_output = re.sub(r'_PREVIEW_URL_:.+?(?:\n|$)', '', output).strip()
                        if clean_output:
                            yield emit("output", clean_output)
                    except Exception as parse_err:
                        logger.warning(f"[Execution] Error parsing preview URL: {parse_err}")
                        yield emit("output", output.strip())
                else:
                    try:
                        stripped = output.strip()
                        if stripped:
                            yield emit("output", stripped)
                    except Exception:
                        pass

        except asyncio.CancelledError:
            logger.info(f"[Execution] Docker execution cancelled for {project_id}")
            yield emit("error", "Execution was cancelled.")
            return
        except Exception as docker_err:
            logger.error(f"[Execution] Docker executor error for {project_id}: {docker_err}", exc_info=True)
            docker_error = str(docker_err)
            yield emit("output", f"  Error: {docker_error}")

        # Send completion event
        if docker_error:
            yield emit("error", f"Execution failed: {docker_error}")
        elif server_started and preview_url:
            yield emit("complete", "Server running", {"preview_url": preview_url, "success": True})
        else:
            yield emit("step_complete", "Build completed", {"step": 4})
            yield emit("complete", "Execution completed", {"success": True})

        logger.info(f"[SSE] Execution stream completed for {project_id}")

    except asyncio.CancelledError:
        logger.info(f"[SSE] Stream cancelled for {project_id}")
        yield emit("error", "Execution was cancelled.")
    except Exception as e:
        logger.error(f"[SSE] Stream error for {project_id}: {e}", exc_info=True)
        yield emit("error", str(e))


async def _execute_docker_stream(project_id: str, project_path):
    """
    Execute project with smart Docker/Direct fallback and stream output.

    Flow:
    1. Detect framework type
    2. Auto-generate Dockerfile if missing
    3. Try Docker execution first
    4. If Docker fails, fall back to direct execution
    5. Stream logs and detect server start
    6. Return preview URL when server is ready
    """
    from pathlib import Path
    project_path = Path(project_path)

    try:
        # Send start event
        yield f"data: {json.dumps({'type': 'start', 'data': {'project_id': project_id}})}\n\n"

        yield f"data: {json.dumps({'type': 'output', 'content': 'Checking project structure...'})}\n\n"

        server_started = False
        preview_url = None

        # Use smart run_project which handles Docker + fallback
        async for output in docker_executor.run_project(project_id, project_path):
            # Check for special server started markers (both legacy and new format)
            # Legacy: __SERVER_STARTED__:URL
            # New:    _PREVIEW_URL_:URL
            if output.startswith("__SERVER_STARTED__:") or output.startswith("_PREVIEW_URL_:"):
                # Extract URL from either marker format
                if output.startswith("__SERVER_STARTED__:"):
                    preview_url = output.split(":", 1)[1].strip()
                else:
                    preview_url = output.split("_PREVIEW_URL_:", 1)[1].strip()
                server_started = True

                # Extract port from URL
                import re
                port_match = re.search(r':(\d+)', preview_url)
                port = int(port_match.group(1)) if port_match else 3000

                # Send server_started event for frontend
                yield f"data: {json.dumps({'type': 'server_started', 'port': port, 'preview_url': preview_url})}\n\n"
            elif "_PREVIEW_URL_:" in output:
                # Handle case where _PREVIEW_URL_ is embedded in output (e.g., after banner)
                import re
                url_match = re.search(r'_PREVIEW_URL_:(.+?)(?:\n|$)', output)
                if url_match:
                    preview_url = url_match.group(1).strip()
                    server_started = True
                    port_match = re.search(r':(\d+)', preview_url)
                    port = int(port_match.group(1)) if port_match else 3000
                    yield f"data: {json.dumps({'type': 'server_started', 'port': port, 'preview_url': preview_url})}\n\n"
                # Also send the output (without the marker) for display
                clean_output = re.sub(r'_PREVIEW_URL_:.+?(?:\n|$)', '', output).strip()
                if clean_output:
                    yield f"data: {json.dumps({'type': 'output', 'content': clean_output})}\n\n"
            else:
                # Regular output
                yield f"data: {json.dumps({'type': 'output', 'content': output.strip()})}\n\n"

        # Send completion event
        if server_started and preview_url:
            yield f"data: {json.dumps({'type': 'complete', 'data': {'message': 'Server running', 'preview_url': preview_url}})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'complete', 'data': {'message': 'Execution completed'}})}\n\n"

    except Exception as e:
        logger.error(f"Execution error for {project_id}: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


def _detect_project_type(project_path) -> dict:
    """Detect project type and return info"""
    project_info = {
        "type": "unknown",
        "frontend": False,
        "backend": False,
        "has_docker": False,
        "framework": None
    }

    # Check for Docker
    if (project_path / "docker-compose.yml").exists() or (project_path / "Dockerfile").exists():
        project_info["has_docker"] = True

    # Check for Node.js/Frontend
    package_json_path = None
    if (project_path / "package.json").exists():
        package_json_path = project_path / "package.json"
    elif (project_path / "frontend/package.json").exists():
        package_json_path = project_path / "frontend/package.json"

    if package_json_path:
        project_info["frontend"] = True
        try:
            import json
            with open(package_json_path) as f:
                pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "next" in deps:
                    project_info["framework"] = "nextjs"
                elif "vite" in deps:
                    project_info["framework"] = "vite"
                elif "react" in deps:
                    project_info["framework"] = "react"
                elif "vue" in deps:
                    project_info["framework"] = "vue"
                else:
                    project_info["framework"] = "nodejs"
        except (json.JSONDecodeError, IOError, OSError) as e:
            logger.debug(f"Could not parse package.json: {e}")
            project_info["framework"] = "nodejs"

    # Check for Python/Backend
    if (project_path / "requirements.txt").exists() or (project_path / "backend/requirements.txt").exists():
        project_info["backend"] = True
        req_path = project_path / "requirements.txt"
        if (project_path / "backend/requirements.txt").exists():
            req_path = project_path / "backend/requirements.txt"
        try:
            with open(req_path) as f:
                reqs = f.read().lower()
                if "fastapi" in reqs:
                    project_info["framework"] = "fastapi"
                elif "flask" in reqs:
                    project_info["framework"] = "flask"
                elif "django" in reqs:
                    project_info["framework"] = "django"
        except (IOError, OSError) as e:
            logger.debug(f"Could not read requirements.txt: {e}")

    # Check for simple HTML
    if (project_path / "index.html").exists():
        project_info["frontend"] = True
        if not project_info["framework"]:
            project_info["framework"] = "static"

    # Determine type
    if project_info["frontend"] and project_info["backend"]:
        project_info["type"] = "fullstack"
    elif project_info["frontend"]:
        project_info["type"] = "frontend"
    elif project_info["backend"]:
        project_info["type"] = "backend"

    return project_info


def _validate_project_files(project_path, project_info: dict) -> dict:
    """Validate project has all required files before execution"""
    validation = {
        "valid": True,
        "missing_files": [],
        "warnings": []
    }

    # Check for required files based on project type
    if project_info["frontend"]:
        if project_info["framework"] in ["nextjs", "vite", "react", "vue", "nodejs"]:
            # Need package.json
            pkg_path = project_path / "package.json"
            frontend_pkg = project_path / "frontend" / "package.json"
            if not pkg_path.exists() and not frontend_pkg.exists():
                validation["missing_files"].append("package.json")
                validation["valid"] = False
            else:
                # Validate package.json has scripts
                try:
                    import json
                    pkg_file = pkg_path if pkg_path.exists() else frontend_pkg
                    with open(pkg_file) as f:
                        pkg = json.load(f)
                        if "scripts" not in pkg or "dev" not in pkg.get("scripts", {}):
                            validation["warnings"].append("package.json missing 'dev' script")
                except Exception as e:
                    validation["warnings"].append(f"Could not validate package.json: {e}")

        elif project_info["framework"] == "static":
            # Need index.html
            if not (project_path / "index.html").exists():
                validation["missing_files"].append("index.html")
                validation["valid"] = False

    if project_info["backend"]:
        # Need requirements.txt or main entry point
        has_reqs = (project_path / "requirements.txt").exists() or (project_path / "backend" / "requirements.txt").exists()
        has_main = (project_path / "main.py").exists() or (project_path / "app.py").exists()

        if not has_reqs and not has_main:
            validation["warnings"].append("No requirements.txt or main.py found")

    return validation


async def _auto_detect_commands(project_id: str, user_id: str = None) -> List[str]:
    """Auto-detect commands based on project files"""
    commands = []
    project_path = get_project_path(project_id, user_id)
    project_info = _detect_project_type(project_path)

    logger.info(f"Detected project type: {project_info}")

    # Validate project files first
    validation = _validate_project_files(project_path, project_info)
    if not validation["valid"]:
        logger.error(f"Project validation failed: {validation['missing_files']}")
        return []  # Return empty - let the caller handle the error

    for warning in validation.get("warnings", []):
        logger.warning(f"Project validation warning: {warning}")

    # Get available port for frontend
    frontend_port = _get_available_port(3001)
    backend_port = _get_available_port(8001)

    # Handle Docker projects first
    if project_info["has_docker"] and (project_path / "docker-compose.yml").exists():
        commands.append("docker-compose up -d")
        return commands

    # Handle frontend
    if project_info["frontend"]:
        frontend_dir = "frontend" if (project_path / "frontend").exists() else ""

        if project_info["framework"] == "static":
            # Simple HTML - use Python HTTP server
            commands.append(f"python -m http.server {frontend_port}")
        elif project_info["framework"] in ["nextjs", "vite", "react", "vue", "nodejs"]:
            install_cmd = f"cd {frontend_dir} && npm install" if frontend_dir else "npm install"

            # Check if package.json has scripts
            pkg_path = project_path / frontend_dir / "package.json" if frontend_dir else project_path / "package.json"
            run_cmd = f"cd {frontend_dir} && npm run dev -- --port {frontend_port}" if frontend_dir else f"npm run dev -- --port {frontend_port}"

            # Framework-specific adjustments
            if project_info["framework"] == "vite":
                run_cmd = f"cd {frontend_dir} && npm run dev -- --port {frontend_port} --host" if frontend_dir else f"npm run dev -- --port {frontend_port} --host"
            elif project_info["framework"] == "nextjs":
                run_cmd = f"cd {frontend_dir} && npm run dev -- -p {frontend_port}" if frontend_dir else f"npm run dev -- -p {frontend_port}"

            commands.extend([install_cmd, run_cmd])

    # Handle backend
    if project_info["backend"]:
        backend_dir = "backend" if (project_path / "backend").exists() else ""

        install_cmd = f"cd {backend_dir} && pip install -r requirements.txt" if backend_dir else "pip install -r requirements.txt"

        # Framework-specific run commands
        if project_info["framework"] == "fastapi":
            run_cmd = f"cd {backend_dir} && uvicorn main:app --reload --host 0.0.0.0 --port {backend_port}" if backend_dir else f"uvicorn main:app --reload --host 0.0.0.0 --port {backend_port}"
        elif project_info["framework"] == "flask":
            run_cmd = f"cd {backend_dir} && flask run --host 0.0.0.0 --port {backend_port}" if backend_dir else f"flask run --host 0.0.0.0 --port {backend_port}"
        elif project_info["framework"] == "django":
            run_cmd = f"cd {backend_dir} && python manage.py runserver 0.0.0.0:{backend_port}" if backend_dir else f"python manage.py runserver 0.0.0.0:{backend_port}"
        else:
            # Generic Python
            main_file = "main.py" if (project_path / "main.py").exists() else "app.py"
            run_cmd = f"cd {backend_dir} && python {main_file}" if backend_dir else f"python {main_file}"

        commands.extend([install_cmd, run_cmd])

    return commands


async def _execute_commands_stream(project_id: str, commands: List[str], user_id: str = None):
    """Execute commands and stream output"""
    global _running_processes
    # Get project path (sandbox first, then permanent storage)
    project_path = get_project_path(project_id, user_id)

    # Send start event
    yield f"data: {json.dumps({'type': 'start', 'data': {'project_id': project_id, 'commands': commands}})}\n\n"

    for idx, command in enumerate(commands):
        try:
            # Send command start event
            yield f"data: {json.dumps({'type': 'command_start', 'data': {'command': command, 'index': idx}})}\n\n"

            # Execute command
            logger.info(f"Executing: {command} in {project_path}")

            # Use subprocess for actual execution
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(project_path)
            )

            # Store process for stop functionality
            _running_processes[project_id] = process

            # Stream stdout
            async for line in process.stdout:
                output = line.decode().strip()
                if output:
                    yield f"data: {json.dumps({'type': 'output', 'data': {'output': output, 'stream': 'stdout'}})}\n\n"
                    await asyncio.sleep(0.01)  # Small delay for streaming

            # Wait for completion
            await process.wait()

            # Get stderr if any
            stderr = await process.stderr.read()
            if stderr:
                error_output = stderr.decode().strip()
                yield f"data: {json.dumps({'type': 'output', 'data': {'output': error_output, 'stream': 'stderr'}})}\n\n"

            # Send command complete event
            success = process.returncode == 0
            yield f"data: {json.dumps({'type': 'command_complete', 'data': {'command': command, 'success': success, 'exit_code': process.returncode}})}\n\n"

            if not success:
                logger.warning(f"Command failed with exit code {process.returncode}: {command}")
                # Continue to next command even if this one failed

        except asyncio.CancelledError:
            logger.info(f"Execution cancelled for project {project_id}")
            yield f"data: {json.dumps({'type': 'cancelled', 'data': {'message': 'Execution cancelled'}})}\n\n"
            break
        except Exception as e:
            logger.error(f"Error executing command '{command}': {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': {'command': command, 'error': str(e)}})}\n\n"

    # Clean up
    if project_id in _running_processes:
        del _running_processes[project_id]

    # Send completion event
    yield f"data: {json.dumps({'type': 'complete', 'data': {'message': 'All commands executed'}})}\n\n"


@router.get("/validate/{project_id}")
async def validate_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate if a project is ready to run.
    Returns validation status, detected type, and suggested commands.
    """
    # Verify project ownership (skip if no auth in dev mode)
    if current_user and not await verify_project_ownership(project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    try:
        # Get project path (sandbox first, then permanent storage)
        user_id = str(current_user.id) if current_user else None
        project_path = get_project_path(project_id, user_id)

        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        # Detect project type
        project_info = _detect_project_type(project_path)

        # Validate files
        validation = _validate_project_files(project_path, project_info)

        # Get suggested commands
        commands = await _auto_detect_commands(project_id, user_id)

        return {
            "project_id": project_id,
            "valid": validation["valid"],
            "missing_files": validation["missing_files"],
            "warnings": validation["warnings"],
            "project_info": project_info,
            "suggested_commands": commands,
            "ready_to_run": validation["valid"] and len(commands) > 0
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{project_id}")
async def get_project_status(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current status of a project"""
    # Verify project ownership (skip if no auth in dev mode)
    if current_user and not await verify_project_ownership(project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    try:
        # Get project path (sandbox first, then permanent storage)
        user_id = str(current_user.id) if current_user else None
        project_path = get_project_path(project_id, user_id)

        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        # Check what's in the project
        files = []
        # Skip patterns to avoid Windows file lock errors (WinError 1920)
        skip_patterns = ['node_modules', '__pycache__', '.git', '.env', 'dist', 'build', '.bin']
        for file_path in project_path.rglob("*"):
            try:
                rel_path_str = str(file_path.relative_to(project_path)).replace("\\", "/")
                # Skip system/locked directories before calling is_file()
                if any(pattern in rel_path_str for pattern in skip_patterns):
                    continue
                if file_path.is_file() and not rel_path_str.startswith('.'):
                    files.append(rel_path_str)
            except OSError:
                # Handle WinError 1920 and other OS errors for locked files
                continue

        # Detect project type
        project_info = _detect_project_type(project_path)

        # Validate
        validation = _validate_project_files(project_path, project_info)

        return {
            "project_id": project_id,
            "path": str(project_path),
            "type": project_info.get("framework", "unknown"),
            "project_info": project_info,
            "files_count": len(files),
            "files": files[:20],  # Return first 20 files
            "valid": validation["valid"],
            "warnings": validation["warnings"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{project_id}")
async def export_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_feature("download_files"))
):
    """Export entire project as ZIP file"""
    # Verify project ownership (skip if no auth in dev mode)
    if current_user and not await verify_project_ownership(project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    try:
        # Touch the project to keep it alive during export
        touch_project(project_id)

        # Get project path (sandbox first, then permanent storage)
        user_id = str(current_user.id) if current_user else None
        project_path = get_project_path(project_id, user_id)

        logger.info(f"[Export] Attempting to export project: {project_id}")
        logger.info(f"[Export] Project path: {project_path}")
        logger.info(f"[Export] Path exists: {project_path.exists()}")

        if not project_path.exists():
            logger.error(f"[Export] Project directory not found: {project_path}")
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        files_added = 0

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Skip certain files/folders - check BEFORE is_file() to avoid WinError 1920
            skip_patterns = [
                '.project_metadata.json',
                '__pycache__',
                'node_modules',
                '.git',
                '.DS_Store',
                'Thumbs.db',
                '.bin'
            ]

            # Walk through all files in project
            for file_path in project_path.rglob("*"):
                try:
                    # Get relative path and check skip patterns FIRST (before is_file())
                    rel_path = file_path.relative_to(project_path)
                    rel_path_str = str(rel_path)

                    # Check if should skip - do this BEFORE is_file() to avoid Windows file lock errors
                    should_skip = any(
                        pattern in rel_path_str
                        for pattern in skip_patterns
                    )

                    if should_skip:
                        continue

                    # Now safe to check is_file() after skip patterns
                    if file_path.is_file():
                        # Add file to ZIP
                        zip_file.write(file_path, rel_path)
                        files_added += 1
                        logger.debug(f"[Export] Added to ZIP: {rel_path}")
                except OSError as e:
                    # Handle WinError 1920 and other OS errors for locked files
                    logger.warning(f"[Export] Skipping locked file: {file_path} - {e}")
                    continue

        # Get ZIP data
        zip_buffer.seek(0)
        zip_data = zip_buffer.getvalue()

        logger.info(f"[Export] Successfully exported project {project_id}: {files_added} files, {len(zip_data)} bytes")

        if files_added == 0:
            logger.warning(f"[Export] ZIP is empty - no files found in project {project_id}")

        # Return ZIP file
        return Response(
            content=zip_data,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={project_id}.zip"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Export] Error exporting project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
