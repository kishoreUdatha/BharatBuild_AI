"""
Workspace Management API - Bolt.new Style

BOLT.NEW ARCHITECTURE:
=====================
Stage 1: GET /workspace/project/{projectId} → Returns tree + metadata (NO content)
Stage 5: GET /workspace/project/{projectId}/file?path=... → Lazy load single file
Stage 6: PATCH /workspace/project/{projectId}/file → Update file content

Key principles:
1. NO full content in workspace fetch (lazy loading)
2. File tree is hierarchical
3. Content loaded on-demand
4. Super fast initial load

Also includes:
- Workspace CRUD operations
- Restoration endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, String
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import json
import asyncio

from app.core.database import get_db
from app.core.logging_config import logger
from app.models.user import User
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.workspace import Workspace
from app.modules.auth.dependencies import get_current_user
from app.services.workspace_restore import workspace_restore
from app.services.unified_storage import unified_storage
from app.services.sandbox_cleanup import touch_project
from app.utils.pagination import paginate, create_paginated_response


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


class PaginatedProjectsInWorkspace(BaseModel):
    """Paginated projects response for workspace"""
    items: List[ProjectInWorkspace]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class WorkspaceWithPaginatedProjects(WorkspaceResponse):
    """Workspace with paginated projects"""
    projects: PaginatedProjectsInWorkspace


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


@router.get("/{workspace_id}", response_model=WorkspaceWithPaginatedProjects)
async def get_workspace(
    workspace_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific workspace with paginated projects."""
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

    # Get total count of projects
    count_result = await db.execute(
        select(func.count(Project.id)).where(Project.workspace_id == workspace.id)
    )
    total = count_result.scalar() or 0

    # Get paginated projects
    offset = (page - 1) * page_size
    projects_result = await db.execute(
        select(Project)
        .where(Project.workspace_id == workspace.id)
        .order_by(Project.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    projects = projects_result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return WorkspaceWithPaginatedProjects(
        id=str(workspace.id),
        user_id=str(workspace.user_id),
        name=workspace.name,
        description=workspace.description,
        is_default=workspace.is_default,
        storage_path=workspace.storage_path,
        s3_prefix=workspace.s3_prefix,
        project_count=total,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        projects=PaginatedProjectsInWorkspace(
            items=[
                ProjectInWorkspace(
                    id=str(p.id),
                    title=p.title,
                    status=p.status.value if p.status else "unknown",
                    created_at=p.created_at
                )
                for p in projects
            ],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )
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


# ==================== BOLT.NEW STYLE ENDPOINTS ====================
# These endpoints match Bolt.new's architecture for lazy loading

class FileNode(BaseModel):
    """File tree node (no content - lazy loaded)"""
    name: str
    path: str
    type: str  # "file" or "folder"
    size: Optional[int] = None
    language: Optional[str] = None
    children: Optional[List['FileNode']] = None

    class Config:
        from_attributes = True


class BoltWorkspaceResponse(BaseModel):
    """Full workspace response (Bolt.new style) - NO file content!"""
    projectId: str
    root: str = "/"
    tree: List[FileNode]
    openTabs: List[str] = []
    plan: Optional[Dict[str, Any]] = None
    techStack: List[str] = []
    messages: List[Dict[str, Any]] = []
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class FileContentResponse(BaseModel):
    """Single file content response (lazy loaded)"""
    path: str
    content: str
    language: str
    size: int
    checksum: Optional[str] = None


class FileUpdateRequest(BaseModel):
    """File update request"""
    path: str
    content: Optional[str] = None
    contentDiff: Optional[str] = None  # For incremental updates


# Update forward reference for recursive model
FileNode.model_rebuild()


def _build_bolt_tree(files: List[ProjectFile]) -> List[FileNode]:
    """
    Build hierarchical file tree from flat file list.
    Returns Bolt.new style tree (NO content):
    [
        { "name": "src", "type": "folder", "children": [...] },
        { "name": "index.html", "type": "file", "size": 210 }
    ]
    """
    root: Dict[str, Any] = {"children": {}}

    for file in files:
        parts = file.path.split('/')
        current = root

        # Build path
        for i, part in enumerate(parts):
            if part not in current["children"]:
                is_file = (i == len(parts) - 1) and not file.is_folder
                current["children"][part] = {
                    "name": part,
                    "path": '/'.join(parts[:i+1]),
                    "type": "file" if is_file else "folder",
                    "size": file.size_bytes if is_file else None,
                    "language": file.language if is_file else None,
                    "children": {} if not is_file else None
                }
            current = current["children"][part]

    # Convert to list format
    def to_list(node: Dict) -> List[FileNode]:
        result = []
        for name, data in sorted(node.get("children", {}).items()):
            children = None
            if data.get("type") == "folder" and data.get("children"):
                children = to_list(data)

            result.append(FileNode(
                name=data["name"],
                path=data["path"],
                type=data["type"],
                size=data.get("size"),
                language=data.get("language"),
                children=children if children else None
            ))
        return result

    return to_list(root)


@router.get("/project/{project_id}", response_model=BoltWorkspaceResponse)
async def get_bolt_workspace(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Stage 1-4: Get workspace metadata + tree (NO file content).

    This is SUPER FAST because we only return:
    - File tree structure (hierarchical)
    - Project metadata
    - Plan JSON
    - Claude messages

    File content is lazy-loaded via GET /workspace/project/{id}/file?path=...
    """
    try:
        user_id = str(current_user.id)

        # Stage 2: Fetch project metadata
        # Cast column to String(36) to handle UUID/VARCHAR mismatch
        result = await db.execute(
            select(Project).where(cast(Project.id, String(36)) == str(project_id))
        )
        project = result.scalar_one_or_none()

        # Stage 2: Fetch file tree (metadata only, NO content!)
        # Cast column to String(36) to handle UUID/VARCHAR mismatch
        files_result = await db.execute(
            select(ProjectFile)
            .where(cast(ProjectFile.project_id, String(36)) == str(project_id))
            .order_by(ProjectFile.path)
        )
        files = files_result.scalars().all()

        # Stage 3: Build hierarchical tree (Bolt.new style)
        tree = _build_bolt_tree(files)

        # Extract tech stack
        tech_stack = []
        if project and project.tech_stack:
            if isinstance(project.tech_stack, list):
                tech_stack = project.tech_stack
            elif isinstance(project.tech_stack, str):
                tech_stack = [t.strip() for t in project.tech_stack.split(',')]

        logger.info(f"[Bolt] Workspace fetch: {project_id} - {len(files)} files in tree (NO content)")

        # Touch project to keep sandbox alive
        touch_project(project_id)

        # Stage 4: Return workspace (NO file content!)
        return BoltWorkspaceResponse(
            projectId=project_id,
            root="/",
            tree=tree,
            openTabs=[],
            plan=project.plan_json if project else None,
            techStack=tech_stack,
            messages=project.history if project and project.history else [],
            createdAt=project.created_at.isoformat() if project and project.created_at else None,
            updatedAt=project.updated_at.isoformat() if project and project.updated_at else None
        )

    except Exception as e:
        logger.error(f"[Bolt] Error fetching workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}/file", response_model=FileContentResponse)
async def get_file_content(
    project_id: str,
    path: str = Query(..., description="File path to load"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Stage 5: Lazy load single file content.

    Called when:
    - User clicks file in tree
    - User opens tab
    - File needed for preview (entrypoints)

    This keeps initial workspace load SUPER FAST!
    """
    try:
        user_id = str(current_user.id)

        # Try to get from database first (Layer 3)
        # Cast column to String(36) to handle UUID/VARCHAR mismatch
        file_result = await db.execute(
            select(ProjectFile)
            .where(cast(ProjectFile.project_id, String(36)) == str(project_id))
            .where(ProjectFile.path == path)
        )
        file_record = file_result.scalar_one_or_none()

        if file_record:
            # Get content - prioritize S3, fallback to inline for legacy data
            content = ""
            if file_record.s3_key:
                # Fetch from S3
                content = await unified_storage.download_from_s3(file_record.s3_key) or ""
            elif file_record.content_inline:
                # Legacy fallback for old inline content
                content = file_record.content_inline

            logger.info(f"[Bolt] Lazy load: {path} ({len(content)} bytes)")

            return FileContentResponse(
                path=path,
                content=content,
                language=file_record.language or "plaintext",
                size=file_record.size_bytes or len(content),
                checksum=file_record.content_hash
            )

        # Fallback: Try sandbox (Layer 1)
        content = await unified_storage.read_from_sandbox(project_id, path, user_id)
        if content:
            # Detect language from extension
            ext = path.rsplit('.', 1)[-1] if '.' in path else ''
            lang_map = {
                'ts': 'typescript', 'tsx': 'typescript',
                'js': 'javascript', 'jsx': 'javascript',
                'py': 'python', 'json': 'json',
                'html': 'html', 'css': 'css',
                'md': 'markdown', 'yaml': 'yaml', 'yml': 'yaml'
            }
            language = lang_map.get(ext, 'plaintext')

            logger.info(f"[Bolt] Lazy load (sandbox): {path} ({len(content)} bytes)")

            return FileContentResponse(
                path=path,
                content=content,
                language=language,
                size=len(content),
                checksum=None
            )

        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Bolt] Error fetching file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/project/{project_id}/file")
async def update_file_content(
    project_id: str,
    request: FileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Stage 6: Update file content (sync live changes).

    Called when user types in editor.
    Stores:
    - Updated content in database
    - Also syncs to sandbox for preview

    This maintains workspace state even if you reload browser.
    """
    try:
        user_id = str(current_user.id)

        content = request.content
        if not content and request.contentDiff:
            # TODO: Apply diff to existing content
            raise HTTPException(status_code=400, detail="contentDiff not yet supported, send full content")

        if not content:
            raise HTTPException(status_code=400, detail="content is required")

        # Save to database (Layer 3 - persistent)
        db_saved = await unified_storage.save_to_database(project_id, request.path, content)

        # Save to sandbox (Layer 1 - for preview)
        await unified_storage.write_to_sandbox(project_id, request.path, content, user_id)

        logger.info(f"[Bolt] File updated: {request.path} ({len(content)} bytes)")

        return {
            "success": db_saved,
            "path": request.path,
            "size": len(content),
            "updatedAt": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Bolt] Error updating file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
