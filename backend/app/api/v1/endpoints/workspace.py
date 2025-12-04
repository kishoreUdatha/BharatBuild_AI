"""
Workspace Management API - Bolt.new Style Restoration

Endpoints for managing project workspaces:
- Check workspace status
- Restore workspace from storage
- Regenerate workspace from plan
- CRUD operations for Workspace model
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import json
import asyncio

from app.core.database import get_db
from app.core.logging_config import logger
from app.models.user import User
from app.models.project import Project
from app.models.workspace import Workspace
from app.modules.auth.dependencies import get_current_user
from app.services.workspace_restore import workspace_restore
from app.services.sandbox_cleanup import touch_project


router = APIRouter()


# ==================== WORKSPACE MODEL SCHEMAS ====================

class WorkspaceCreate(BaseModel):
    """Schema for creating a new workspace"""
    name: str = "My Workspace"
    description: Optional[str] = None


class WorkspaceUpdate(BaseModel):
    """Schema for updating a workspace"""
    name: Optional[str] = None
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    """Schema for workspace response"""
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    is_default: bool
    storage_path: Optional[str] = None
    s3_prefix: Optional[str] = None
    project_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectInWorkspace(BaseModel):
    """Schema for project summary in workspace"""
    id: str
    title: str
    status: str
    created_at: datetime


class WorkspaceWithProjects(WorkspaceResponse):
    """Workspace with list of projects"""
    projects: List[ProjectInWorkspace] = []


# ==================== WORKSPACE CRUD ENDPOINTS ====================

@router.get("/", response_model=List[WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all workspaces for the current user.

    Returns list of workspaces with project counts.
    """
    result = await db.execute(
        select(Workspace).where(Workspace.user_id == current_user.id)
    )
    workspaces = result.scalars().all()

    return [
        WorkspaceResponse(
            id=str(ws.id),
            user_id=str(ws.user_id),
            name=ws.name,
            description=ws.description,
            is_default=ws.is_default,
            storage_path=ws.storage_path,
            s3_prefix=ws.s3_prefix,
            project_count=ws.project_count,
            created_at=ws.created_at,
            updated_at=ws.updated_at
        )
        for ws in workspaces
    ]


@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new workspace for the current user.

    Note: Each user has one default workspace created automatically.
    """
    # Check if user already has a default workspace
    existing = await db.execute(
        select(Workspace).where(
            Workspace.user_id == current_user.id,
            Workspace.is_default == True
        )
    )
    has_default = existing.scalar_one_or_none() is not None

    # Create new workspace
    workspace = Workspace(
        user_id=current_user.id,
        name=workspace_data.name,
        description=workspace_data.description,
        is_default=not has_default,  # First workspace is default
        storage_path=f"workspaces/{current_user.id}",
        s3_prefix=f"workspaces/{current_user.id}"
    )

    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)

    logger.info(f"Created workspace {workspace.id} for user {current_user.id}")

    return WorkspaceResponse(
        id=str(workspace.id),
        user_id=str(workspace.user_id),
        name=workspace.name,
        description=workspace.description,
        is_default=workspace.is_default,
        storage_path=workspace.storage_path,
        s3_prefix=workspace.s3_prefix,
        project_count=0,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at
    )


@router.get("/default", response_model=WorkspaceWithProjects)
async def get_default_workspace(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the default workspace for the current user.

    Creates one if it doesn't exist.
    """
    result = await db.execute(
        select(Workspace).where(
            Workspace.user_id == current_user.id,
            Workspace.is_default == True
        )
    )
    workspace = result.scalar_one_or_none()

    # Create default workspace if none exists
    if not workspace:
        workspace = Workspace(
            user_id=current_user.id,
            name="My Workspace",
            is_default=True,
            storage_path=f"workspaces/{current_user.id}",
            s3_prefix=f"workspaces/{current_user.id}"
        )
        db.add(workspace)
        await db.commit()
        await db.refresh(workspace)
        logger.info(f"Created default workspace for user {current_user.id}")

    # Get projects in workspace
    projects_result = await db.execute(
        select(Project).where(Project.workspace_id == workspace.id)
    )
    projects = projects_result.scalars().all()

    return WorkspaceWithProjects(
        id=str(workspace.id),
        user_id=str(workspace.user_id),
        name=workspace.name,
        description=workspace.description,
        is_default=workspace.is_default,
        storage_path=workspace.storage_path,
        s3_prefix=workspace.s3_prefix,
        project_count=len(projects),
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        projects=[
            ProjectInWorkspace(
                id=str(p.id),
                title=p.title,
                status=p.status.value if p.status else "unknown",
                created_at=p.created_at
            )
            for p in projects
        ]
    )


@router.get("/{workspace_id}", response_model=WorkspaceWithProjects)
async def get_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific workspace with its projects."""
    try:
        result = await db.execute(
            select(Workspace).where(
                Workspace.id == UUID(workspace_id),
                Workspace.user_id == current_user.id
            )
        )
        workspace = result.scalar_one_or_none()

        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID"
        )

    # Get projects in workspace
    projects_result = await db.execute(
        select(Project).where(Project.workspace_id == workspace.id)
    )
    projects = projects_result.scalars().all()

    return WorkspaceWithProjects(
        id=str(workspace.id),
        user_id=str(workspace.user_id),
        name=workspace.name,
        description=workspace.description,
        is_default=workspace.is_default,
        storage_path=workspace.storage_path,
        s3_prefix=workspace.s3_prefix,
        project_count=len(projects),
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        projects=[
            ProjectInWorkspace(
                id=str(p.id),
                title=p.title,
                status=p.status.value if p.status else "unknown",
                created_at=p.created_at
            )
            for p in projects
        ]
    )


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    workspace_data: WorkspaceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a workspace."""
    try:
        result = await db.execute(
            select(Workspace).where(
                Workspace.id == UUID(workspace_id),
                Workspace.user_id == current_user.id
            )
        )
        workspace = result.scalar_one_or_none()

        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID"
        )

    # Update fields
    if workspace_data.name is not None:
        workspace.name = workspace_data.name
    if workspace_data.description is not None:
        workspace.description = workspace_data.description

    await db.commit()
    await db.refresh(workspace)

    return WorkspaceResponse(
        id=str(workspace.id),
        user_id=str(workspace.user_id),
        name=workspace.name,
        description=workspace.description,
        is_default=workspace.is_default,
        storage_path=workspace.storage_path,
        s3_prefix=workspace.s3_prefix,
        project_count=workspace.project_count,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at
    )


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a workspace and all its projects.

    Cannot delete the default workspace.
    """
    try:
        result = await db.execute(
            select(Workspace).where(
                Workspace.id == UUID(workspace_id),
                Workspace.user_id == current_user.id
            )
        )
        workspace = result.scalar_one_or_none()

        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )

        if workspace.is_default:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete default workspace"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID"
        )

    await db.delete(workspace)
    await db.commit()

    logger.info(f"Deleted workspace {workspace_id}")

    return {"success": True, "message": "Workspace deleted"}


# ==================== WORKSPACE RESTORATION ENDPOINTS ====================


class RestoreRequest(BaseModel):
    """Request model for workspace restoration"""
    prefer_regenerate: bool = False  # If True, prefer regeneration over restoration


@router.get("/status/{project_id}")
async def get_workspace_status(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check workspace status for a project.

    Returns:
    - workspace_exists: Whether files exist in sandbox
    - can_restore: Whether files can be restored from storage
    - can_regenerate: Whether workspace can be regenerated from plan
    - file_count: Number of files available in storage
    """
    # Verify ownership
    try:
        result = await db.execute(
            select(Project).where(
                Project.id == UUID(project_id),
                Project.user_id == current_user.id
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID"
        )

    status_info = await workspace_restore.check_workspace_status(project_id, db)

    return {
        **status_info,
        "project_title": project.title,
        "project_status": project.status.value if project.status else None
    }


@router.post("/restore/{project_id}")
async def restore_workspace(
    project_id: str,
    request: Optional[RestoreRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Restore a project workspace after sandbox cleanup.

    Two modes:
    1. RESTORE from storage (default) - Fast, uses stored files
    2. REGENERATE from plan - Re-runs writer agent (Bolt.new style)

    Set prefer_regenerate=true to use regeneration mode.
    """
    # Verify ownership
    try:
        result = await db.execute(
            select(Project).where(
                Project.id == UUID(project_id),
                Project.user_id == current_user.id
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID"
        )

    prefer_regenerate = request.prefer_regenerate if request else False

    # Restore workspace
    result = await workspace_restore.auto_restore(
        project_id=project_id,
        db=db,
        prefer_regenerate=prefer_regenerate
    )

    # Touch project to keep it alive
    if result.get("success"):
        touch_project(project_id)

    return result


@router.post("/restore/{project_id}/stream")
async def restore_workspace_stream(
    project_id: str,
    request: Optional[RestoreRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Restore workspace with SSE streaming progress.

    Streams events as files are restored:
    - file_restored: Each file as it's restored
    - complete: When restoration is complete
    - error: If an error occurs
    """
    # Verify ownership
    try:
        result = await db.execute(
            select(Project).where(
                Project.id == UUID(project_id),
                Project.user_id == current_user.id
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID"
        )

    async def stream_restore():
        """Stream restoration progress"""
        try:
            # Check status first
            status_info = await workspace_restore.check_workspace_status(project_id, db)

            yield f"data: {json.dumps({'type': 'status', 'data': status_info})}\n\n"

            if status_info["workspace_exists"]:
                yield f"data: {json.dumps({'type': 'complete', 'data': {'message': 'Workspace already exists'}})}\n\n"
                return

            if not status_info["can_restore"] and not status_info["can_regenerate"]:
                yield f"data: {json.dumps({'type': 'error', 'data': {'error': 'No restoration method available'}})}\n\n"
                return

            # Progress callback
            async def progress_callback(event):
                pass  # We'll yield directly in the loop

            # Restore from storage
            if status_info["can_restore"]:
                yield f"data: {json.dumps({'type': 'start', 'data': {'method': 'restore', 'file_count': status_info['file_count']}})}\n\n"

                result = await workspace_restore.restore_from_storage(
                    project_id=project_id,
                    db=db
                )

                if result["success"]:
                    touch_project(project_id)

                yield f"data: {json.dumps({'type': 'complete', 'data': result})}\n\n"

            elif status_info["can_regenerate"]:
                yield f"data: {json.dumps({'type': 'start', 'data': {'method': 'regenerate'}})}\n\n"
                yield f"data: {json.dumps({'type': 'info', 'data': {'message': 'Regeneration requires re-running the orchestrator'}})}\n\n"

        except Exception as e:
            logger.error(f"[Workspace] Error streaming restore: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e)}})}\n\n"

    return StreamingResponse(
        stream_restore(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/regenerate/{project_id}")
async def regenerate_workspace(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate workspace from plan (Bolt.new style).

    This will:
    1. Create empty workspace
    2. Re-run the writer agent using stored plan_json
    3. Generate fresh files

    Note: This takes longer than restore but creates fresh files.
    """
    # Verify ownership
    try:
        result = await db.execute(
            select(Project).where(
                Project.id == UUID(project_id),
                Project.user_id == current_user.id
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        if not project.plan_json:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No plan found for this project"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID"
        )

    # Return regeneration info - actual regeneration happens via orchestrator
    return {
        "success": True,
        "method": "regenerate",
        "project_id": project_id,
        "plan_available": True,
        "message": "Call /orchestrator/execute with existing plan to regenerate workspace",
        "plan_summary": {
            "file_count": len(project.plan_json.get("files", [])) if isinstance(project.plan_json, dict) else 0,
            "has_tasks": "tasks" in project.plan_json if isinstance(project.plan_json, dict) else False
        }
    }
