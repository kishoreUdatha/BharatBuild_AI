"""
Sandbox Management API Endpoints

Provides endpoints for:
- Docker container management for project sandboxes
- Viewing sandbox cleanup stats
- Extending project life
- Getting project expiry info
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.models.user import User
from app.services.docker_sandbox_service import DockerSandboxService, ContainerConfig
from app.services.sandbox_reconstruction_service import SandboxReconstructionService

# Import conditionally to handle missing module
try:
    from app.services.sandbox_cleanup import sandbox_cleanup, touch_project, get_project_expiry
    CLEANUP_AVAILABLE = True
except ImportError:
    CLEANUP_AVAILABLE = False

router = APIRouter()


# ========== Request/Response Models ==========

class CreateSandboxRequest(BaseModel):
    project_id: str
    cpu_limit: float = 0.5
    memory_limit: str = "512m"
    container_port: int = 3000

class ExecuteCommandRequest(BaseModel):
    command: str
    timeout: int = 60

class SandboxResponse(BaseModel):
    success: bool
    container_id: Optional[str] = None
    host_port: Optional[int] = None
    preview_url: Optional[str] = None
    error: Optional[str] = None


# ========== Docker Sandbox Endpoints ==========

@router.post("/docker/create", response_model=SandboxResponse)
async def create_docker_sandbox(
    request: CreateSandboxRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new Docker sandbox container for a project.

    This:
    1. Creates workspace with project files
    2. Starts Docker container
    3. Returns preview URL
    """
    try:
        project_id = UUID(request.project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    # First, reconstruct the workspace with files
    reconstruction_service = SandboxReconstructionService(db)
    reconstruction_result = await reconstruction_service.reconstruct_sandbox(project_id)

    if not reconstruction_result.success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reconstruct workspace: {reconstruction_result.error}"
        )

    # Now create Docker container
    docker_service = DockerSandboxService(db)
    config = ContainerConfig(
        cpu_limit=request.cpu_limit,
        memory_limit=request.memory_limit,
        container_port=request.container_port
    )

    result = await docker_service.create_sandbox(
        project_id=project_id,
        workspace_path=reconstruction_result.workspace_path,
        config=config
    )

    return SandboxResponse(
        success=result.success,
        container_id=result.container_id,
        host_port=result.host_port,
        preview_url=result.preview_url,
        error=result.error
    )


@router.post("/docker/{project_id}/start-dev")
async def start_dev_server(
    project_id: str,
    command: str = "npm run dev",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start the development server in a sandbox container.
    """
    docker_service = DockerSandboxService(db)

    # Get container ID from database
    from app.services.sandbox_db_service import SandboxDBService
    sandbox_service = SandboxDBService(db)
    sandbox = await sandbox_service.get_latest_sandbox(UUID(project_id))

    if not sandbox or not sandbox.docker_container_id:
        raise HTTPException(status_code=404, detail="Sandbox container not found")

    result = await docker_service.start_dev_server(
        container_id=sandbox.docker_container_id,
        command=command
    )

    return {
        "success": result.success,
        "error": result.error
    }


@router.post("/docker/{project_id}/install")
async def install_dependencies(
    project_id: str,
    project_type: str = "node",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Install project dependencies (npm install, pip install, etc.)
    """
    docker_service = DockerSandboxService(db)

    from app.services.sandbox_db_service import SandboxDBService
    sandbox_service = SandboxDBService(db)
    sandbox = await sandbox_service.get_latest_sandbox(UUID(project_id))

    if not sandbox or not sandbox.docker_container_id:
        raise HTTPException(status_code=404, detail="Sandbox container not found")

    result = await docker_service.install_dependencies(
        container_id=sandbox.docker_container_id,
        project_type=project_type
    )

    return result


@router.post("/docker/{project_id}/exec")
async def execute_command(
    project_id: str,
    request: ExecuteCommandRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a command in the sandbox container.
    """
    docker_service = DockerSandboxService(db)

    from app.services.sandbox_db_service import SandboxDBService
    sandbox_service = SandboxDBService(db)
    sandbox = await sandbox_service.get_latest_sandbox(UUID(project_id))

    if not sandbox or not sandbox.docker_container_id:
        raise HTTPException(status_code=404, detail="Sandbox container not found")

    result = await docker_service.execute_command(
        container_id=sandbox.docker_container_id,
        command=request.command,
        timeout=request.timeout
    )

    return result


@router.get("/docker/{project_id}/logs")
async def get_sandbox_logs(
    project_id: str,
    tail: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get logs from sandbox container.
    """
    docker_service = DockerSandboxService(db)

    from app.services.sandbox_db_service import SandboxDBService
    sandbox_service = SandboxDBService(db)
    sandbox = await sandbox_service.get_latest_sandbox(UUID(project_id))

    if not sandbox or not sandbox.docker_container_id:
        raise HTTPException(status_code=404, detail="Sandbox container not found")

    logs = await docker_service.get_container_logs(
        container_id=sandbox.docker_container_id,
        tail=tail
    )

    return {"logs": logs}


@router.get("/docker/{project_id}/status")
async def get_sandbox_status(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get status of sandbox container.
    """
    docker_service = DockerSandboxService(db)

    from app.services.sandbox_db_service import SandboxDBService
    sandbox_service = SandboxDBService(db)
    sandbox = await sandbox_service.get_latest_sandbox(UUID(project_id))

    if not sandbox or not sandbox.docker_container_id:
        return {
            "status": "not_found",
            "running": False,
            "container_exists": False
        }

    status = await docker_service.get_sandbox_status(sandbox.docker_container_id)
    return status


@router.delete("/docker/{project_id}")
async def stop_sandbox(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Stop and remove sandbox container.
    """
    docker_service = DockerSandboxService(db)

    success = await docker_service.stop_sandbox(UUID(project_id))

    return {
        "success": success,
        "project_id": project_id
    }


@router.get("/docker/list")
async def list_sandboxes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all active sandbox containers.
    """
    docker_service = DockerSandboxService(db)
    sandboxes = await docker_service.list_sandboxes()

    return {"sandboxes": sandboxes}


# ========== Legacy Cleanup Endpoints ==========


@router.get("/stats")
async def get_sandbox_stats():
    """
    Get sandbox cleanup statistics.
    """
    if not CLEANUP_AVAILABLE:
        return {
            "enabled": False,
            "message": "Sandbox cleanup module not available"
        }

    if not settings.SANDBOX_CLEANUP_ENABLED:
        return {
            "enabled": False,
            "message": "Sandbox cleanup is disabled"
        }

    stats = sandbox_cleanup.get_stats()
    return {
        "enabled": True,
        **stats
    }


@router.get("/projects/{project_id}/expiry")
async def get_project_expiry_info(project_id: str):
    """
    Get expiry information for a specific project.
    """
    if not CLEANUP_AVAILABLE:
        return {"enabled": False, "project_id": project_id}

    if not settings.SANDBOX_CLEANUP_ENABLED:
        return {
            "enabled": False,
            "message": "Sandbox cleanup is disabled",
            "project_id": project_id,
            "will_expire": False
        }

    expiry_info = get_project_expiry(project_id)

    if not expiry_info:
        raise HTTPException(status_code=404, detail="Project not found in sandbox")

    return expiry_info


@router.post("/projects/{project_id}/touch")
async def touch_project_endpoint(project_id: str):
    """
    Touch a project to reset its idle timer.
    """
    if not CLEANUP_AVAILABLE:
        return {"success": False, "message": "Cleanup module not available"}

    touch_project(project_id)

    return {
        "success": True,
        "project_id": project_id,
        "message": "Project activity updated"
    }


@router.post("/projects/{project_id}/extend")
async def extend_project_life(project_id: str):
    """
    Extend a project's life by resetting its idle timer.
    """
    if not CLEANUP_AVAILABLE:
        return {"success": False, "message": "Cleanup module not available"}

    success = sandbox_cleanup.extend_project_life(project_id)

    if not success:
        raise HTTPException(status_code=404, detail="Project not found in sandbox")

    expiry_info = get_project_expiry(project_id)

    return {
        "success": True,
        "project_id": project_id,
        "new_expiry": expiry_info
    }


@router.get("/config")
async def get_sandbox_config():
    """
    Get current sandbox configuration.
    """
    return {
        "enabled": settings.SANDBOX_CLEANUP_ENABLED,
        "sandbox_path": settings.SANDBOX_PATH,
        "idle_timeout_hours": settings.SANDBOX_IDLE_TIMEOUT_HOURS,
        "cleanup_interval_minutes": settings.SANDBOX_CLEANUP_INTERVAL_MINUTES,
        "min_age_minutes": settings.SANDBOX_MIN_AGE_MINUTES
    }
