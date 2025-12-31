"""
Container Execution API - Bolt.new/Replit Style

This is the API that makes BharatBuild work like Bolt.new:
- Create isolated container per project
- Execute commands inside container
- Stream output in real-time via SSE
- Auto-cleanup after 24 hours

Frontend calls these endpoints to:
1. Create project → GET /containers/{project_id}/create
2. Run command → POST /containers/{project_id}/exec
3. Get preview → GET /containers/{project_id}/preview
4. Write files → POST /containers/{project_id}/files
"""

import asyncio
import json
import os
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession

# =============================================================================
# PREVIEW URL - Use centralized function
# =============================================================================
from app.core.preview_url import get_preview_url as _get_preview_url_centralized


def _get_preview_url(port: int, project_id: str = None) -> str:
    """Generate preview URL - delegates to centralized function."""
    return _get_preview_url_centralized(port, project_id or "")

from app.modules.execution import (
    get_container_manager,
    ContainerConfig,
    ContainerStatus,
)
from app.core.security import decode_token
from app.core.database import get_db
from app.core.logging_config import logger
from app.services.workspace_restore import workspace_restore
from app.modules.auth.feature_flags import require_code_execution

router = APIRouter(prefix="/containers", tags=["Container Execution"])


def safe_get_container_manager():
    """
    Safely get container manager, raising proper HTTP exception if Docker is unavailable.

    This allows frontend to detect Docker unavailability and fall back to direct execution.
    """
    try:
        return get_container_manager()
    except RuntimeError as e:
        error_msg = str(e)
        if "Docker" in error_msg or "docker" in error_msg:
            raise HTTPException(
                status_code=503,  # Service Unavailable
                detail=f"Docker not available: {error_msg}"
            )
        raise HTTPException(status_code=500, detail=str(e))


# Request/Response Models

class CreateContainerRequest(BaseModel):
    """Request to create a project container"""
    project_type: str = Field(default="node", description="Project type: node, python, java, go, rust")
    memory_limit: str = Field(default="512m", description="Memory limit (e.g., 512m, 1g)")
    cpu_limit: float = Field(default=0.5, description="CPU cores (0.5 = half core)")


class ExecuteCommandRequest(BaseModel):
    """Request to execute a command"""
    command: str = Field(..., description="Command to execute (e.g., 'npm install')")
    timeout: int = Field(default=300, description="Timeout in seconds")


class WriteFileRequest(BaseModel):
    """Request to write a file"""
    path: str = Field(..., description="Relative file path")
    content: str = Field(..., description="File content")


class ContainerInfo(BaseModel):
    """Container information response"""
    container_id: str
    project_id: str
    status: str
    ports: dict
    preview_urls: dict
    created_at: str
    memory_limit: str
    cpu_limit: float


class FileInfo(BaseModel):
    """File information"""
    name: str
    path: str
    type: str  # "file" or "directory"
    size: int


# Helper to get user_id from request
async def get_current_user_id(request: Request) -> str:
    """Extract user ID from request headers or auth token"""
    # Check header first
    user_id = request.headers.get("X-User-ID")
    if user_id:
        logger.info(f"[Auth] Got user_id from X-User-ID header: {user_id}")
        return user_id

    # Decode JWT token to get user_id
    auth_header = request.headers.get("Authorization")
    logger.info(f"[Auth] Authorization header present: {bool(auth_header)}")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header[7:]  # Remove "Bearer " prefix
            payload = decode_token(token)
            user_id = payload.get("sub")
            if user_id:
                logger.info(f"[Auth] Extracted user_id from JWT: {user_id}")
                return user_id
        except Exception as e:
            logger.warning(f"[Auth] Failed to decode JWT token: {e}")

    logger.info("[Auth] No valid auth found, returning 'anonymous'")
    return "anonymous"


# Endpoints

@router.post("/{project_id}/create", response_model=ContainerInfo)
async def create_container(
    project_id: str,
    request: CreateContainerRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_code_execution)
):
    """
    Create an isolated container for a project.

    This is called when:
    - User creates a new project
    - User opens an existing project

    Each project gets its own Docker container with:
    - Isolated filesystem
    - Resource limits (CPU, memory)
    - Port forwarding for preview
    - Auto-cleanup after 24 hours

    Before creating the container, workspace files are restored from
    database if the workspace directory doesn't exist (e.g., after sandbox cleanup).
    """
    manager = safe_get_container_manager()

    # Restore workspace from database if needed (Bolt.new style)
    try:
        # FIX: Keep user_id as "anonymous" instead of converting to None
        # This ensures path consistency with execution.py which uses "anonymous" for anonymous users
        # Path: /tmp/sandbox/workspace/anonymous/{project_id}
        restore_result = await workspace_restore.auto_restore(
            project_id=project_id,
            db=db,
            user_id=user_id,  # Keep as "anonymous" if that's what the caller used
            project_type=request.project_type  # Pass project type for essential file check
        )
        if restore_result.get("success"):
            method = restore_result.get('method', 'unknown')
            logger.info(f"[Container] Workspace restore for {project_id}: {method}")

            if restore_result.get("restored_files"):
                logger.info(f"[Container] Restored {restore_result['restored_files']} files from database")

            # Log warning if workspace is incomplete
            if method == "incomplete":
                missing = restore_result.get("missing_files", [])
                logger.warning(f"[Container] Workspace incomplete for {project_id}, missing: {missing}")
                logger.warning(f"[Container] Project files may need to be synced from frontend before running")

            # Use user_id from workspace path if we restored successfully
            workspace_path = restore_result.get("workspace_path", "")
            if workspace_path and "anonymous" not in workspace_path:
                # Extract user_id from path like: C:/tmp/sandbox/workspace/{user_id}/{project_id}
                import os
                path_parts = workspace_path.replace("\\", "/").split("/")
                if len(path_parts) >= 2:
                    potential_user_id = path_parts[-2]
                    if potential_user_id != project_id and potential_user_id != "workspace":
                        user_id = potential_user_id
                        logger.info(f"[Container] Using user_id from restore: {user_id}")
        else:
            # Not an error - might be a new project with no files
            logger.info(f"[Container] No workspace restore available for {project_id}: {restore_result.get('error', 'N/A')}")
    except Exception as e:
        logger.warning(f"[Container] Workspace restore failed for {project_id}: {e}")
        # Continue anyway - container can still be created

    config = ContainerConfig(
        memory_limit=request.memory_limit,
        cpu_limit=request.cpu_limit,
    )

    try:
        container = await manager.create_container(
            project_id=project_id,
            user_id=user_id,
            project_type=request.project_type,
            config=config,
        )

        # CRITICAL #4: Validate port mappings exist
        if not container.port_mappings:
            logger.warning(f"[Container] Container created but no port mappings for {project_id}")
            # Still continue - the reverse proxy might work

        # Build preview URLs - Direct port URLs work better on Windows Docker
        preview_urls = {}
        primary_url = None

        # Common dev server ports in priority order
        priority_ports = [3000, 5173, 5174, 4173, 8080, 8000, 5000]

        for container_port, host_port in container.port_mappings.items():
            # CRITICAL #4: Validate host_port is valid
            if host_port is None or host_port == 0:
                logger.warning(f"[Container] Invalid host_port for container_port {container_port}")
                continue

            direct_url = _get_preview_url(host_port)
            preview_urls[str(container_port)] = direct_url

            # Set primary URL from first matching priority port
            if primary_url is None and int(container_port) in priority_ports:
                primary_url = direct_url

        # Fallback to first available port if no priority port found
        if primary_url is None and container.port_mappings:
            valid_ports = [p for p in container.port_mappings.values() if p and p != 0]
            if valid_ports:
                first_host_port = valid_ports[0]
                primary_url = _get_preview_url(first_host_port)

        # Also include reverse proxy as fallback (may work in some setups)
        bolt_style_preview_url = f"/api/v1/preview/{project_id}/"

        return ContainerInfo(
            container_id=container.container_id[:12],
            project_id=project_id,
            status=container.status.value,
            ports=container.port_mappings,
            preview_urls={
                "primary": primary_url or bolt_style_preview_url,  # Direct URL as primary
                "reverse_proxy": bolt_style_preview_url,  # Reverse proxy as fallback
                **preview_urls  # All port URLs
            },
            created_at=container.created_at.isoformat(),
            memory_limit=config.memory_limit,
            cpu_limit=config.cpu_limit,
        )

    except Exception as e:
        logger.error(f"Failed to create container: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/exec")
async def execute_command(
    project_id: str,
    request: ExecuteCommandRequest,
    _: None = Depends(require_code_execution)
):
    """
    Execute a command inside project container with streaming output.

    This is the CORE API that runs user code:
    - npm install
    - npm run dev
    - python main.py
    - pip install -r requirements.txt
    - etc.

    Returns: Server-Sent Events stream with real-time output

    Response format (each event):
    {
        "type": "stdout|stderr|exit|error|done",
        "data": "raw message (unchanged for fixers)",
        "display": {
            "level": "info|success|warning|error",
            "category": "build|install|server|test|error|general",
            "icon": "emoji/symbol",
            "label": "SHORT_LABEL",
            "color": "#hexcolor"
        },
        "timestamp": "HH:MM:SS"
    }
    """
    from app.services.terminal_log_formatter import terminal_formatter

    manager = safe_get_container_manager()

    async def event_stream():
        """Generate SSE events from command execution with display hints"""
        try:
            # Send start event
            start_event = {
                "type": "system",
                "data": f"Running: {request.command}",
                "display": {
                    "level": "system",
                    "category": "general",
                    "icon": "▶",
                    "label": "START",
                    "color": "#90CAF9"
                }
            }
            yield f"data: {json.dumps(start_event)}\n\n"

            async for event in manager.execute_command(
                project_id=project_id,
                command=request.command,
                timeout=request.timeout,
            ):
                # Format for display (adds hints, keeps raw data)
                formatted = terminal_formatter.format_event(event)

                # Build response with raw data + display hints
                response = {
                    # Raw data - UNCHANGED for fixers
                    "type": event.get("type"),
                    "data": event.get("data"),
                    # Display hints - for UI
                    "display": {
                        "level": formatted.level.value,
                        "category": formatted.category.value,
                        "icon": formatted.icon,
                        "label": formatted.label,
                        "color": formatted.color,
                    },
                    "timestamp": formatted.timestamp,
                }

                # Include file/line if detected
                if formatted.file_path:
                    response["file"] = formatted.file_path
                if formatted.line_number:
                    response["line"] = formatted.line_number

                # Include exit-specific fields
                if event.get("type") == "exit":
                    response["success"] = event.get("success", False)

                yield f"data: {json.dumps(response)}\n\n"

        except Exception as e:
            error_event = {
                "type": "error",
                "data": str(e),
                "display": {
                    "level": "error",
                    "category": "error",
                    "icon": "✗",
                    "label": "ERROR",
                    "color": "#E57373"
                }
            }
            yield f"data: {json.dumps(error_event)}\n\n"

        # Send done event
        done_event = {
            "type": "done",
            "data": "",
            "display": {
                "level": "system",
                "category": "general",
                "icon": "■",
                "label": "DONE",
                "color": "#90CAF9"
            }
        }
        yield f"data: {json.dumps(done_event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.post("/{project_id}/files")
async def write_file(
    project_id: str,
    request: WriteFileRequest,
):
    """
    Write a file to the project container.

    Used when:
    - AI generates code
    - User saves file from editor
    - Creating new files
    """
    manager = safe_get_container_manager()

    try:
        success = await manager.write_file(
            project_id=project_id,
            file_path=request.path,
            content=request.content,
        )

        return {"success": success, "path": request.path}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to write file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/files")
async def list_files(
    project_id: str,
    path: str = Query(default=".", description="Directory path"),
) -> List[FileInfo]:
    """
    List files in project directory.

    Used by:
    - File explorer in UI
    - Getting project structure
    """
    manager = safe_get_container_manager()

    try:
        files = await manager.list_files(project_id, path)
        return [FileInfo(**f) for f in files]

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/files/{file_path:path}")
async def read_file(
    project_id: str,
    file_path: str,
):
    """
    Read a file from the project container.

    Used by:
    - Code editor to display file content
    - AI to read existing code
    """
    manager = safe_get_container_manager()

    try:
        content = await manager.read_file(project_id, file_path)

        if content is None:
            raise HTTPException(status_code=404, detail="File not found")

        return {"path": file_path, "content": content}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/preview")
async def get_preview_url(
    project_id: str,
    port: int = Query(default=3000, description="Container port"),
    request: Request = None,
):
    """
    Get the preview URL for a running project.

    Uses Bolt.new-style reverse proxy routing:
    - /api/v1/preview/{project_id}/ (path-based, infinite scaling)

    Falls back to direct port mapping for WebSocket HMR support.
    """
    manager = safe_get_container_manager()

    if project_id not in manager.containers:
        raise HTTPException(status_code=404, detail="Preview not available - container not found")

    container_info = manager.containers[project_id]
    active_port = container_info.active_port

    # Bolt.new-style: Use reverse proxy URL (no port collision, infinite scaling)
    # The preview_proxy endpoint will route to the container's internal IP
    reverse_proxy_url = f"/api/v1/preview/{project_id}/"

    # Also provide direct port URL for HMR WebSocket fallback
    direct_url = await manager.get_preview_url(project_id, port)

    return {
        "url": reverse_proxy_url,  # Primary: Bolt.new-style reverse proxy
        "direct_url": direct_url,  # Fallback: Direct port mapping (for HMR)
        "port": port,
        "active_port": active_port,
        "auto_detected": active_port is not None,
        "routing_method": "reverse_proxy",
        "note": "Use 'url' for iframe preview. Use 'direct_url' for WebSocket HMR."
    }


@router.get("/{project_id}/ports")
async def get_all_ports(project_id: str):
    """
    Get all available port mappings for a project.

    Returns all mapped ports so the frontend can try them.
    Useful when the dev server falls back to a different port.
    """
    manager = safe_get_container_manager()

    if project_id not in manager.containers:
        raise HTTPException(status_code=404, detail="Container not found")

    container = manager.containers[project_id]

    return {
        "project_id": project_id,
        "active_port": container.active_port,
        "port_mappings": container.port_mappings,  # container_port -> host_port
        "preview_urls": manager.get_all_preview_urls(project_id),
    }


@router.get("/{project_id}/stats")
async def get_container_stats(project_id: str):
    """
    Get resource usage stats for a container.

    Shows:
    - CPU usage %
    - Memory usage
    - Container status
    """
    manager = safe_get_container_manager()

    stats = await manager.get_container_stats(project_id)

    if not stats:
        raise HTTPException(status_code=404, detail="Container not found")

    return stats


@router.post("/{project_id}/stop")
async def stop_container(project_id: str):
    """
    Stop a project container.

    Container can be restarted later. Files are preserved.
    Gap #15: Verifies container is actually stopped after the request.
    Gap #16: Invalidates preview cache to ensure stale IPs aren't used.
    """
    # Gap #16: Invalidate preview cache immediately
    try:
        from app.api.v1.endpoints.preview_proxy import invalidate_preview_cache
        invalidate_preview_cache(project_id)
    except Exception as cache_err:
        logger.warning(f"[Container] Failed to invalidate preview cache: {cache_err}")

    manager = safe_get_container_manager()

    success = await manager.stop_container(project_id)

    if not success:
        raise HTTPException(status_code=404, detail="Container not found")

    # Gap #15: Verify container is actually stopped
    verification_attempts = 0
    max_verification_attempts = 3
    container_stopped = False

    while verification_attempts < max_verification_attempts:
        await asyncio.sleep(0.5)  # Wait for container state to update
        verification_attempts += 1

        try:
            status = await manager.get_container_status(project_id)
            if status is None or status.get("status") in ["stopped", "exited", None]:
                container_stopped = True
                break
            logger.warning(f"[Container] Stop verification attempt {verification_attempts}: container still {status.get('status')}")
        except Exception as e:
            # Container not found means it's stopped
            container_stopped = True
            break

    if not container_stopped:
        logger.warning(f"[Container] Failed to verify container stop for {project_id} after {max_verification_attempts} attempts")
        return {
            "success": True,
            "message": "Container stop requested but verification failed",
            "verified": False
        }

    return {"success": True, "message": "Container stopped", "verified": True}


@router.delete("/{project_id}")
async def delete_container(
    project_id: str,
    delete_files: bool = Query(default=False, description="Also delete project files"),
):
    """
    Delete a project container.

    If delete_files=True, also removes all project files (irreversible).
    """
    manager = safe_get_container_manager()

    success = await manager.delete_container(project_id, delete_files)

    if not success:
        raise HTTPException(status_code=404, detail="Container not found")

    return {
        "success": True,
        "message": "Container deleted",
        "files_deleted": delete_files
    }


@router.get("/{project_id}/status")
async def get_container_status(project_id: str):
    """
    Get container status and info.
    """
    manager = safe_get_container_manager()

    if project_id not in manager.containers:
        raise HTTPException(status_code=404, detail="Container not found")

    container = manager.containers[project_id]

    return {
        "project_id": project_id,
        "container_id": container.container_id[:12],
        "status": container.status.value,
        "created_at": container.created_at.isoformat(),
        "last_activity": container.last_activity.isoformat(),
        "ports": container.port_mappings,
        "is_expired": container.is_expired(),
    }


# Batch operations for efficiency

class BatchWriteRequest(BaseModel):
    """Write multiple files at once"""
    files: List[WriteFileRequest]


@router.post("/{project_id}/files/batch")
async def batch_write_files(
    project_id: str,
    request: BatchWriteRequest,
):
    """
    Write multiple files at once.

    More efficient than calling write_file multiple times.
    Used when AI generates multiple files.
    """
    manager = safe_get_container_manager()

    results = []
    for file in request.files:
        try:
            await manager.write_file(project_id, file.path, file.content)
            results.append({"path": file.path, "success": True})
        except Exception as e:
            results.append({"path": file.path, "success": False, "error": str(e)})

    return {
        "total": len(request.files),
        "success": sum(1 for r in results if r["success"]),
        "results": results
    }


class FileVerifyRequest(BaseModel):
    """Verify files exist in container"""
    paths: List[str]


@router.post("/{project_id}/files/verify")
async def verify_files(
    project_id: str,
    request: FileVerifyRequest,
):
    """
    HIGH #2: Verify that specified files exist in the container.
    Used to confirm file sync completed before running commands.
    """
    manager = safe_get_container_manager()

    existing = []
    missing = []

    for path in request.paths:
        try:
            content = await manager.read_file(project_id, path)
            if content is not None:
                existing.append(path)
            else:
                missing.append(path)
        except Exception:
            missing.append(path)

    return {
        "all_exist": len(missing) == 0,
        "existing": existing,
        "missing": missing,
        "total": len(request.paths)
    }


class BatchCommandRequest(BaseModel):
    """Execute multiple commands in sequence"""
    commands: List[str]
    stop_on_error: bool = True


@router.post("/{project_id}/exec/batch")
async def batch_execute_commands(
    project_id: str,
    request: BatchCommandRequest,
):
    """
    Execute multiple commands in sequence with streaming output.

    Common use case: npm install && npm run build && npm run dev
    """
    from app.services.terminal_log_formatter import terminal_formatter

    manager = safe_get_container_manager()

    async def event_stream():
        for i, command in enumerate(request.commands):
            # Command start event with display hints
            start_event = {
                "type": "command_start",
                "index": i,
                "command": command,
                "data": f"[{i+1}/{len(request.commands)}] {command}",
                "display": {
                    "level": "system",
                    "category": "general",
                    "icon": "▶",
                    "label": f"CMD {i+1}",
                    "color": "#90CAF9"
                }
            }
            yield f"data: {json.dumps(start_event)}\n\n"

            error_occurred = False
            async for event in manager.execute_command(project_id, command):
                # Format for display
                formatted = terminal_formatter.format_event(event)

                response = {
                    "type": event.get("type"),
                    "data": event.get("data"),
                    "display": {
                        "level": formatted.level.value,
                        "category": formatted.category.value,
                        "icon": formatted.icon,
                        "label": formatted.label,
                        "color": formatted.color,
                    },
                    "timestamp": formatted.timestamp,
                }

                if formatted.file_path:
                    response["file"] = formatted.file_path
                if formatted.line_number:
                    response["line"] = formatted.line_number
                if event.get("type") == "exit":
                    response["success"] = event.get("success", False)

                yield f"data: {json.dumps(response)}\n\n"

                if event.get("type") == "error":
                    error_occurred = True
                if event.get("type") == "exit" and not event.get("success"):
                    error_occurred = True

            if error_occurred and request.stop_on_error:
                stop_event = {
                    "type": "batch_stopped",
                    "reason": "error",
                    "data": f"Batch stopped at command {i+1} due to error",
                    "display": {
                        "level": "error",
                        "category": "error",
                        "icon": "⏹",
                        "label": "STOPPED",
                        "color": "#E57373"
                    }
                }
                yield f"data: {json.dumps(stop_event)}\n\n"
                break

        done_event = {
            "type": "done",
            "data": "",
            "display": {
                "level": "system",
                "category": "general",
                "icon": "■",
                "label": "DONE",
                "color": "#90CAF9"
            }
        }
        yield f"data: {json.dumps(done_event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# =============================================================================
# ERROR RECOVERY ENDPOINTS
# =============================================================================

class RecoveryRequest(BaseModel):
    """Request to recover from an error"""
    error_type: str = Field(..., description="Type of error: missing_files, s3_failure, container_crash, fix_exhausted")
    context: dict = Field(default_factory=dict, description="Additional context for recovery")


class RecoveryResponse(BaseModel):
    """Response from recovery attempt"""
    success: bool
    action_taken: str
    message: str
    details: Optional[dict] = None
    next_steps: List[str] = []


@router.post("/{project_id}/recover", response_model=RecoveryResponse)
async def recover_from_error(
    project_id: str,
    request: RecoveryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Attempt to recover from a run-time error.

    Error types:
    - missing_files: Critical files missing from workspace
    - s3_failure: S3 download failed
    - container_crash: Container crashed or unhealthy
    - fix_exhausted: Auto-fix exhausted all attempts

    Returns recovery result with next steps if manual action needed.
    """
    from app.services.error_recovery import error_recovery, RecoveryType

    # Map string to enum
    error_type_map = {
        "missing_files": RecoveryType.MISSING_FILES,
        "s3_failure": RecoveryType.S3_FAILURE,
        "container_crash": RecoveryType.CONTAINER_CRASH,
        "fix_exhausted": RecoveryType.FIX_EXHAUSTED,
        "validation_failed": RecoveryType.VALIDATION_FAILED,
    }

    recovery_type = error_type_map.get(request.error_type.lower())
    if not recovery_type:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid error type: {request.error_type}. Valid types: {list(error_type_map.keys())}"
        )

    # Add project_id to context
    context = request.context.copy()
    context["project_id"] = project_id

    # Attempt recovery
    result = await error_recovery.recover(
        error_type=recovery_type,
        context=context,
        db=db
    )

    return RecoveryResponse(
        success=result.success,
        action_taken=result.action_taken.value,
        message=result.message,
        details=result.details,
        next_steps=result.next_steps
    )


@router.post("/{project_id}/restart")
async def restart_container(project_id: str):
    """
    Restart a container (stop and start).

    Use this when container is in an unhealthy state.
    """
    from app.services.error_recovery import error_recovery, RecoveryType
    from app.services.container_executor import container_executor

    # Get container ID
    container_info = container_executor.active_containers.get(project_id)
    if not container_info:
        raise HTTPException(status_code=404, detail="Container not found")

    # Attempt recovery via restart
    result = await error_recovery.recover(
        error_type=RecoveryType.CONTAINER_CRASH,
        context={
            "project_id": project_id,
            "container_id": container_info["container_id"],
        }
    )

    return {
        "success": result.success,
        "message": result.message,
        "next_steps": result.next_steps
    }


@router.post("/{project_id}/regenerate")
async def regenerate_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Regenerate project files from saved plan.

    Use this when files are corrupted or missing and need to be recreated from scratch.
    """
    try:
        # Check if regeneration is available
        status = await workspace_restore.check_workspace_status(project_id, db)

        if not status.get("can_regenerate"):
            return {
                "success": False,
                "message": "No saved plan available for regeneration",
                "can_restore": status.get("can_restore", False)
            }

        # Trigger regeneration
        result = await workspace_restore.regenerate_from_plan(project_id, db)

        return {
            "success": result.get("success", False),
            "message": result.get("message", "Regeneration context prepared"),
            "regeneration_context": result.get("regeneration_context"),
            "instructions": result.get("instructions")
        }
    except Exception as e:
        logger.error(f"[Containers] Regeneration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
