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
from app.services.container_executor import container_executor

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


class FixTerminalErrorRequest(BaseModel):
    """Request model for terminal/build error auto-fixing (Bolt.new style)"""
    error_output: str  # Full stderr/stdout from failed command
    exit_code: int = 1  # Exit code from failed command
    command: Optional[str] = None  # The command that failed


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
    logger.info(f"[Execution] POST /run/{project_id} called, user={current_user.id if current_user else 'anonymous'}")

    # Validate project_id format (UUID)
    import re
    uuid_pattern = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', re.IGNORECASE)
    if not uuid_pattern.match(project_id):
        logger.warning(f"[Execution] Invalid project ID format: {project_id}")
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_project_id", "message": "Invalid project ID format"}
        )

    # Verify project ownership (skip if no auth in dev mode)
    if current_user and not await verify_project_ownership(project_id, current_user, db):
        logger.warning(f"[Execution] Project ownership verification failed for {project_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    logger.info(f"[Execution] Ownership check passed for {project_id}")

    # Get user_id for the streaming function
    user_id = str(current_user.id) if current_user else None

    try:
        # Check if project has been generated (has files in database)
        from app.models.project_file import ProjectFile
        files_result = await db.execute(
            select(ProjectFile).where(ProjectFile.project_id == project_id).limit(1)
        )
        has_files = files_result.scalar_one_or_none() is not None
        logger.info(f"[Execution] Project {project_id} has_files={has_files}")
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

        # Stream Docker execution with progress
        # Use StreamingResponse with manual SSE formatting
        async def sse_generator():
            """Wrapper that formats events as SSE and adds keepalive"""
            event_count = 0
            try:
                logger.info(f"[SSE] Starting SSE stream for project {project_id}")
                async for event in _execute_docker_stream_with_progress(project_id, user_id, db):
                    event_count += 1
                    if isinstance(event, dict) and "data" in event:
                        sse_line = f"data: {event['data']}\n\n"
                        if event_count <= 5:  # Log first 5 events
                            logger.info(f"[SSE] Event #{event_count}: {sse_line[:100]}...")
                        yield sse_line
                    elif isinstance(event, str):
                        if event_count <= 5:
                            logger.info(f"[SSE] Raw event #{event_count}: {event[:100]}...")
                        yield event
                    # Yield immediately to flush
                    await asyncio.sleep(0)
                logger.info(f"[SSE] Stream completed for {project_id}, total events: {event_count}")
            except Exception as e:
                logger.error(f"[SSE] Generator error: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Transfer-Encoding": "chunked",
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

        # In remote sandbox mode, files are on EC2 not local ECS
        # Skip local path check in remote mode
        sandbox_docker_host = _os.environ.get("SANDBOX_DOCKER_HOST")
        is_remote_mode = bool(sandbox_docker_host)

        if not is_remote_mode and not project_path.exists():
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

                # PROTECTION: Block full docker-compose.yml replacement
                # AI has been known to corrupt docker-compose.yml by deleting services
                if "docker-compose" in file_path_str.lower():
                    logger.warning(
                        f"[Execution] BLOCKING docker-compose.yml modification - "
                        "AI must use patches, not full file replacement"
                    )
                    continue

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

                # Sync to S3 for persistence (fixes survive container restarts)
                try:
                    from app.services.storage_service import storage_service
                    await storage_service.upload_file(
                        project_id=project_id,
                        file_path=file_path_str,
                        content=content.encode('utf-8'),
                        content_type="text/plain"
                    )
                    logger.info(f"✅ Fixed and synced to S3: {file_path_str}")
                except Exception as s3_err:
                    logger.warning(f"⚠️ S3 sync failed for {file_path_str}: {s3_err}")

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


@router.post("/fix-terminal/{project_id}")
async def fix_terminal_error(
    project_id: str,
    request: FixTerminalErrorRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Auto-fix terminal/build errors using rule-based fixes first, then AI.

    This implements Bolt.new-style terminal error fixing:
    1. Classify error into known categories (dependency, port, command, etc.)
    2. Apply rule-based fix if available (NO AI - fast & cheap)
    3. Escalate to AI only if rules fail
    4. Return fix details for frontend to apply

    Returns:
    - fixed: bool - whether a fix was applied
    - fix_type: "rule" | "ai" | null
    - fix: Object with fix details
    - needs_ai: bool - if AI intervention is needed
    - errors: List of classified errors
    - retry_allowed: bool - if more retries are allowed
    """
    from app.services.terminal_error_fixer import get_terminal_fixer

    # Verify project ownership
    if current_user and not await verify_project_ownership(project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    try:
        # Touch the project to keep it alive
        touch_project(project_id)

        # Get project path
        user_id = str(current_user.id) if current_user else None
        project_path = await get_project_path_async(project_id, user_id)

        if not project_path:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        # Get or create terminal fixer for this project
        fixer = get_terminal_fixer(project_id, project_path, user_id)

        # Analyze and attempt fix
        result = await fixer.analyze_and_fix(
            error_output=request.error_output,
            exit_code=request.exit_code,
            command=request.command
        )

        logger.info(f"[TerminalFixer] Result for {project_id}: fixed={result['fixed']}, fix_type={result['fix_type']}, needs_ai={result['needs_ai']}")

        # If rule-based fix applied and we're using EC2, run the fix command
        if result['fixed'] and result['fix'] and result['fix'].get('command'):
            sandbox_docker_host = _os.environ.get("SANDBOX_DOCKER_HOST")
            if sandbox_docker_host:
                # TODO: Execute fix command in container on EC2
                # For now, return the command for frontend to trigger re-run
                result['requires_rerun'] = True

        # If AI is needed, call the existing fix endpoint logic
        if result['needs_ai'] and result['errors']:
            primary_error = result['errors'][0] if result['errors'] else {}
            result['ai_context'] = {
                'error_category': primary_error.get('category'),
                'root_cause': primary_error.get('root_cause'),
                'affected_file': primary_error.get('affected_file'),
                'missing_module': primary_error.get('missing_module'),
            }

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fixing terminal error for {project_id}: {e}", exc_info=True)
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
    Logs are also stored in LogBus for auto-fixer context.
    """
    from pathlib import Path
    import re

    # Get LogBus for this project to store logs for auto-fixer
    log_bus = get_log_bus(project_id)

    # Error detection patterns for LogBus classification
    error_patterns = [
        r"npm ERR!",
        r"Error:",
        r"ERROR:",
        r"error:",
        r"\[ERROR\]",           # esbuild [ERROR] format
        r"No matching export",  # esbuild export mismatch
        r"Failed to resolve",   # Vite resolve errors
        r"does not provide an export named",  # ESM export errors
        r"SyntaxError:",
        r"ReferenceError:",
        r"TypeError:",
        r"Module not found",
        r"Cannot find module",
        r"ENOENT:",
        r"EADDRINUSE",
        r"Permission denied",
        r"Traceback \(most recent call last\)",
        r"ImportError:",
        r"ModuleNotFoundError:",
        r"failed",
        r"FAILED",
    ]

    def emit(event_type: str, message: str = None, data: dict = None):
        """Helper to create SSE event dict for sse-starlette"""
        event = {"type": event_type}
        if message:
            event["message"] = message
            event["content"] = message
        if data:
            # Spread data fields directly onto event (frontend expects data.port, not data.data.port)
            event.update(data)
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
        # Send connection confirmation immediately
        logger.info(f"[Execution] Starting stream for {project_id}")
        yield emit("output", "📡 Connected to execution server")
        await asyncio.sleep(0)  # Flush immediately

        # Send initial events
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
        yield emit("output", "[1/5] Checking project status...")
        # keepalive handled by EventSourceResponse ping

        sandbox_docker_host = _os.environ.get("SANDBOX_DOCKER_HOST")
        project_path = None
        needs_restore = False
        restored_count = 0
        container_already_running = False

        # CRITICAL: Check if container EXISTS (running OR stopped) FIRST
        # If exists, files are already in the container volume - skip restoration
        # This prevents Vite restart loops caused by file modifications
        if sandbox_docker_host:
            try:
                from app.services.container_executor import ContainerExecutor
                executor = ContainerExecutor()
                container_already_running = executor.is_container_running(project_id, effective_user_id)
                if container_already_running:
                    yield emit("output", "  ♻️ Container exists - skipping file restoration (prevents restart loop)")
                    logger.info(f"[Execution] Container exists for {project_id}, skipping restore to prevent restart loop")
            except Exception as check_err:
                logger.warning(f"[Execution] Error checking container status: {check_err}")

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
                # DEBUG: Log actual path for troubleshooting
                logger.info(f"[Execution] DEBUG: project_path (cached) = {project_path}, effective_user_id = {effective_user_id}")
                yield emit("output", f"  📁 Path: {project_path}")
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

        # ==================== STEP 2: Create/Prepare Container ====================
        yield emit("output", "\n[2/5] Preparing container environment...")

        try:
            touch_project(project_id)
        except Exception as touch_err:
            logger.warning(f"[Execution] touch_project failed: {touch_err}")

        yield emit("output", "  Container environment ready")

        # ==================== STEP 3: Restore Project Files (if needed) ====================
        # CRITICAL: Skip restoration if container is already running to prevent Vite restart loops
        if needs_restore and not container_already_running:
            yield emit("output", "\n[3/5] Restoring project files from database...")
            await asyncio.sleep(0)  # Flush immediately

            try:
                from app.models.project_file import ProjectFile
                from app.core.database import async_session

                total_files = 0
                try:
                    async with async_session() as restore_db:
                        from sqlalchemy import select, func
                        count_result = await restore_db.execute(
                            select(func.count(ProjectFile.id))
                            .where(ProjectFile.project_id == project_id)
                            .where(ProjectFile.is_folder == False)  # Only count actual files, not folders
                        )
                        total_files = count_result.scalar() or 0
                except Exception as count_err:
                    logger.warning(f"[Execution] Could not get file count: {count_err}")
                    total_files = 0

                if total_files > 0:
                    yield emit("output", f"  Found {total_files} files in database")
                else:
                    yield emit("output", "  Checking database for files...")
                await asyncio.sleep(0)  # Flush

                # ============ CONCURRENT RESTORE WITH KEEPALIVE ============
                # Run restore in background task while yielding keepalives
                # This prevents CloudFront/ALB timeout during long restores
                restore_task = asyncio.create_task(
                    unified_storage.restore_project_from_database(project_id, effective_user_id)
                )

                restored_files = None
                restore_error = None
                keepalive_count = 0

                while not restore_task.done():
                    # Wait up to 5 seconds for restore to complete
                    try:
                        restored_files = await asyncio.wait_for(
                            asyncio.shield(restore_task),
                            timeout=5.0
                        )
                        break  # Restore completed
                    except asyncio.TimeoutError:
                        # Restore still running, send keepalive
                        keepalive_count += 1
                        yield emit("output", f"  Restoring files... ({keepalive_count * 5}s)")
                        await asyncio.sleep(0)  # Flush immediately
                        continue
                    except asyncio.CancelledError:
                        restore_task.cancel()
                        raise
                    except Exception as e:
                        restore_error = e
                        break

                # Check for errors from the task itself
                if restore_error is None and restore_task.done():
                    try:
                        restored_files = restore_task.result()
                    except Exception as e:
                        restore_error = e

                if restore_error:
                    raise restore_error

                if restored_files:
                    restored_count = len(restored_files)
                    yield emit("output", f"  ✅ Restored {restored_count}/{total_files or restored_count} files to sandbox")
                    project_path = unified_storage.get_sandbox_path(project_id, effective_user_id)
                    # DEBUG: Log actual path for troubleshooting
                    logger.info(f"[Execution] DEBUG: project_path after restore = {project_path}, effective_user_id = {effective_user_id}")
                    yield emit("output", f"  📁 Path: {project_path}")
                else:
                    # FALLBACK: Check if files already exist on sandbox (may not be in S3)
                    project_path = unified_storage.get_sandbox_path(project_id, effective_user_id)
                    sandbox_has_files = await unified_storage.sandbox_exists(project_id, effective_user_id)

                    if sandbox_has_files:
                        yield emit("output", "  ⚠️ S3 restore failed, but sandbox has files - using existing files")
                        yield emit("output", f"  📁 Path: {project_path}")
                        logger.info(f"[Execution] Fallback: Using existing sandbox files at {project_path}")

                        # SYNC: Upload sandbox files to S3 in background for future restores
                        yield emit("output", "  ☁️ Syncing sandbox files to S3...")
                        try:
                            synced_count = await unified_storage.sync_sandbox_to_s3(project_id, effective_user_id)
                            if synced_count > 0:
                                yield emit("output", f"  ✅ Synced {synced_count} files to S3")
                                logger.info(f"[Execution] Synced {synced_count} files from sandbox to S3")
                        except Exception as sync_err:
                            logger.warning(f"[Execution] Sandbox to S3 sync failed: {sync_err}")
                            yield emit("output", f"  ⚠️ S3 sync skipped: {sync_err}")
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
        elif container_already_running:
            # Container exists - files are already in the volume, just get the path
            yield emit("output", "\n[3/5] Using existing files (container has files) ✅")
            project_path = unified_storage.get_sandbox_path(project_id, effective_user_id)
            logger.info(f"[Execution] Container exists, using existing path: {project_path}")
        else:
            yield emit("output", "\n[3/5] Project files already in sandbox ✅")

        # ==================== STEP 4 & 5: Install & Run ====================
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

        # CRITICAL #1: Adaptive stream timeout based on phase
        # - npm install phase: 10 minutes (large projects need time)
        # - dev server phase: 3 minutes (should start quickly after install)
        MAX_INSTALL_DURATION_SECONDS = 600  # 10 minutes for npm install
        MAX_DEV_SERVER_DURATION_SECONDS = 600  # 10 minutes for dev server (increased for Java --no-cache rebuild)
        stream_start_time = asyncio.get_event_loop().time()
        install_complete = False  # Track when install finishes

        # Gap #5: Per-phase timeout tracking
        phase_start_time = stream_start_time
        current_phase = "install"  # Start in install phase

        try:
            last_keepalive = stream_start_time  # HIGH #6: Track keepalive timing

            async for output in docker_executor.run_project(project_id, project_path, effective_user_id):
                # CRITICAL #1: Adaptive stream watchdog based on phase
                elapsed = asyncio.get_event_loop().time() - stream_start_time
                max_duration = MAX_DEV_SERVER_DURATION_SECONDS if install_complete else MAX_INSTALL_DURATION_SECONDS

                if elapsed > max_duration:
                    phase_name = "dev server" if install_complete else "install"
                    logger.warning(f"[Execution] Stream watchdog triggered after {elapsed:.0f}s ({phase_name} phase) for {project_id}")
                    yield emit("error", f"Stream timeout: {phase_name} phase exceeded {max_duration}s")
                    break

                # HIGH #6: Send keepalive every 30s to prevent CloudFront/ALB timeout
                now = asyncio.get_event_loop().time()
                if now - last_keepalive > 30:
                    yield emit("keepalive", "...")
                    last_keepalive = now
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

                # Check for error marker from container_executor
                if output.startswith("__ERROR__:"):
                    error_msg = output.split("__ERROR__:", 1)[1].strip()
                    docker_error = error_msg
                    log_bus.add_docker_error(error_msg)
                    logger.error(f"[Execution] Container error: {error_msg}")
                    continue

                # CRITICAL #1: Detect install completion to switch to dev server phase
                # Extended patterns to catch all npm/yarn/pnpm/pip output formats
                install_complete_patterns = [
                    # npm patterns (various versions)
                    r"added \d+ packages?",
                    r"up to date",
                    r"audited \d+ packages?",
                    r"packages are looking for funding",
                    r"npm WARN",  # Warnings after install
                    r"found \d+ vulnerabilities",
                    r"removed \d+ packages?",  # npm uninstall completion
                    r"changed \d+ packages?",
                    # yarn patterns
                    r"Done in \d+",
                    r"success Saved lockfile",
                    r"YN0000.*Done",
                    # pnpm patterns
                    r"Progress: resolved \d+",
                    r"dependencies:",
                    r"devDependencies:",
                    # pip patterns
                    r"Successfully installed",
                    r"Installing collected packages",
                    r"Requirement already satisfied",
                    # Maven patterns
                    r"BUILD SUCCESS",
                    r"\[INFO\] BUILD",
                    # Gradle patterns
                    r"Dependencies resolved",
                    r"BUILD SUCCESSFUL",
                    # Generic completion markers
                    r"npm run dev",  # Command transition indicates install done
                    r"npm start",
                    r"yarn dev",
                    r"yarn start",
                ]

                # CRITICAL #1: Also detect dev server start commands as install completion
                dev_server_start_patterns = [
                    r"vite",
                    r"next dev",
                    r"react-scripts start",
                    r"webpack serve",
                    r"ng serve",
                    r"nuxt dev",
                ]

                if not install_complete:
                    is_install_done = any(re.search(p, output, re.IGNORECASE) for p in install_complete_patterns)
                    is_dev_starting = any(re.search(p, output, re.IGNORECASE) for p in dev_server_start_patterns)

                    if is_install_done or is_dev_starting:
                        install_complete = True
                        phase_start_time = asyncio.get_event_loop().time()  # Reset phase timer
                        current_phase = "dev_server"
                        logger.info(f"[Execution] Install phase complete, switching to dev_server phase")

                # Check for server started markers
                if output.startswith("__SERVER_STARTED__:") or output.startswith("_PREVIEW_URL_:"):
                    try:
                        if output.startswith("__SERVER_STARTED__:"):
                            preview_url = output.split(":", 1)[1].strip()
                        else:
                            preview_url = output.split("_PREVIEW_URL_:", 1)[1].strip()
                        server_started = True

                        port = safe_parse_port(preview_url, 3000)

                        yield emit("output", "\n[5/5] Starting dev server...")
                        yield emit("output", f"  ✅ Server started on port {port}")
                        yield emit("server_started", None, {"port": port, "preview_url": preview_url})
                        # Store success in LogBus
                        log_bus.add_docker_log(f"Server started successfully on port {port}")
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
                            log_bus.add_docker_log(f"Server ready at {preview_url}")

                        clean_output = re.sub(r'_PREVIEW_URL_:.+?(?:\n|$)', '', output).strip()
                        if clean_output:
                            yield emit("output", clean_output)
                            # Store log in LogBus
                            is_error = any(re.search(pattern, clean_output, re.IGNORECASE) for pattern in error_patterns)
                            if is_error:
                                log_bus.add_docker_error(clean_output)
                            else:
                                log_bus.add_docker_log(clean_output)
                    except Exception as parse_err:
                        logger.warning(f"[Execution] Error parsing preview URL: {parse_err}")
                        yield emit("output", output.strip())
                else:
                    try:
                        stripped = output.strip()
                        if stripped:
                            yield emit("output", stripped)
                            # Store log in LogBus for auto-fixer context
                            is_error = any(re.search(pattern, stripped, re.IGNORECASE) for pattern in error_patterns)
                            if is_error:
                                log_bus.add_docker_error(stripped)
                            else:
                                log_bus.add_docker_log(stripped)
                    except Exception:
                        pass

        except asyncio.CancelledError:
            logger.info(f"[Execution] Docker execution cancelled for {project_id}")
            log_bus.add_docker_error("Execution was cancelled")
            yield emit("error", "Execution was cancelled.")
            return
        except Exception as docker_err:
            logger.error(f"[Execution] Docker executor error for {project_id}: {docker_err}", exc_info=True)
            docker_error = str(docker_err)
            log_bus.add_docker_error(f"Docker execution error: {docker_error}")
            yield emit("output", f"  Error: {docker_error}")

        # Send completion event
        if docker_error:
            yield emit("error", f"Execution failed: {docker_error}")
        elif server_started and preview_url:
            yield emit("output", "✅ Server running successfully!")
        else:
            yield emit("output", "✅ Build completed")

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


@router.post("/heartbeat/{project_id}")
async def project_heartbeat(
    project_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Heartbeat endpoint to keep container alive.
    Call this periodically (e.g., every 5 min) while user is viewing the preview.
    This updates last_activity to prevent 30-min idle cleanup.
    """
    # Update activity timestamp
    container_executor.update_activity(project_id)

    # Also touch the project in sandbox cleanup tracker
    touch_project(project_id)

    return {"status": "ok", "project_id": project_id, "message": "Activity updated"}


@router.get("/export/{project_id}")
async def export_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_feature("download_files"))
):
    """Export entire project as ZIP file"""
    import tempfile
    import shutil
    from pathlib import Path

    # Verify project ownership (skip if no auth in dev mode)
    if current_user and not await verify_project_ownership(project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    temp_restore_path = None

    try:
        # Touch the project to keep it alive during export
        touch_project(project_id)

        user_id = str(current_user.id) if current_user else None

        # Check if using remote sandbox - files may not be available locally
        sandbox_docker_host = _os.environ.get("SANDBOX_DOCKER_HOST")
        project_path = None
        local_file_count = 0

        # Try local sandbox first (only if not using remote sandbox)
        if not sandbox_docker_host:
            project_path = get_project_path(project_id, user_id)
            logger.info(f"[Export] Checking local path: {project_path}")

            if project_path.exists():
                # Count files to check if we have enough
                local_file_count = sum(1 for _ in project_path.rglob("*") if _.is_file())
                logger.info(f"[Export] Local path has {local_file_count} files")

        # If no local path, remote sandbox, or very few local files, restore from database
        should_restore_from_db = (
            sandbox_docker_host or  # Using remote EC2 sandbox
            not project_path or  # No path found
            not project_path.exists() or  # Path doesn't exist
            local_file_count < 3  # Very few files locally (likely incomplete)
        )

        if should_restore_from_db:
            logger.info(f"[Export] Restoring from database (remote_sandbox={bool(sandbox_docker_host)}, local_files={local_file_count})")
            temp_dir = tempfile.mkdtemp(prefix=f"export_{project_id[:8]}_")
            temp_restore_path = Path(temp_dir)

            # Restore files from database/S3 to temp directory
            restored_count = await unified_storage.restore_project_to_local(db, project_id, temp_restore_path, user_id)
            logger.info(f"[Export] Restored {restored_count} files from database to {temp_restore_path}")

            if restored_count > 0:
                project_path = temp_restore_path
            elif project_path and project_path.exists() and local_file_count > 0:
                # Fallback to local path if database restore returned nothing
                logger.warning(f"[Export] Database restore empty, using local path with {local_file_count} files")
            else:
                raise HTTPException(status_code=404, detail=f"Project {project_id} not found or has no files")

        logger.info(f"[Export] Attempting to export project: {project_id}")
        logger.info(f"[Export] Project path: {project_path}")
        logger.info(f"[Export] Path exists: {project_path.exists()}")

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
    finally:
        # Clean up temp directory if created
        if temp_restore_path and temp_restore_path.exists():
            try:
                shutil.rmtree(temp_restore_path, ignore_errors=True)
                logger.debug(f"[Export] Cleaned up temp directory: {temp_restore_path}")
            except Exception as cleanup_err:
                logger.warning(f"[Export] Failed to clean up temp directory: {cleanup_err}")
