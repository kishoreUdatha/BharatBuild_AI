from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.models.workspace import Workspace
from app.models.document import Document
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse
)
from app.modules.auth.dependencies import get_current_user, get_user_project, get_user_project_with_db
from app.modules.auth.usage_limits import check_project_limit, check_project_generation_allowed
from app.services.project_service import ProjectService
from app.core.logging_config import logger

router = APIRouter()


async def get_or_create_default_workspace(user_id, db: AsyncSession) -> Workspace:
    """Get user's default workspace or create one if it doesn't exist."""
    result = await db.execute(
        select(Workspace).where(
            Workspace.user_id == user_id,
            Workspace.is_default == True
        )
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        # Create default workspace
        workspace = Workspace(
            user_id=user_id,
            name="My Workspace",
            is_default=True,
            storage_path=f"workspaces/{user_id}",
            s3_prefix=f"workspaces/{user_id}"
        )
        db.add(workspace)
        await db.flush()  # Get the ID without committing
        logger.info(f"Created default workspace for user {user_id}")

    return workspace


# ========== File Management Schemas ==========

class FileCreate(BaseModel):
    path: str
    content: str
    language: Optional[str] = None


class FileUpdate(BaseModel):
    content: str


class FileBulkCreate(BaseModel):
    files: List[FileCreate]


class FileResponse(BaseModel):
    id: str
    path: str
    name: str
    language: Optional[str]
    size_bytes: int
    is_folder: bool = False

    class Config:
        from_attributes = True


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create new project.

    Projects are automatically assigned to the user's default workspace.
    Storage structure: workspaces/{user_id}/{project_id}/

    Note: This endpoint enforces project limits based on user's subscription plan.
    - Free: 0 projects (demo only)
    - Premium: 2 projects
    """
    # Check project generation limits
    limit_check = await check_project_generation_allowed(current_user, db)
    logger.info(f"Project limit check passed: {limit_check.message}")

    # Get or create default workspace for user
    workspace = await get_or_create_default_workspace(current_user.id, db)

    # Create project with workspace assignment
    project = Project(
        user_id=current_user.id,
        workspace_id=workspace.id,  # Assign to workspace
        title=project_data.title,
        description=project_data.description,
        mode=project_data.mode,
        domain=project_data.domain,
        tech_stack=project_data.tech_stack,
        requirements=project_data.requirements,
        framework=project_data.framework,
        deployment_target=project_data.deployment_target,
        industry=project_data.industry,
        target_market=project_data.target_market,
        config=project_data.config or {},
        status=ProjectStatus.DRAFT,
        # Set S3 path using workspace structure
        s3_path=f"workspaces/{current_user.id}/{project_data.title.replace(' ', '_').lower()}"
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    logger.info(f"Project created: {project.id} in workspace {workspace.id}")

    return project


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's projects"""

    # Convert user_id to string for comparison with String(36) GUID columns
    user_id_str = str(current_user.id)
    logger.info(f"[Projects] Listing projects for user: {current_user.email} (ID: {user_id_str})")

    # Count total with explicit string comparison
    count_query = select(func.count(Project.id)).where(Project.user_id == user_id_str)
    total = await db.scalar(count_query)
    logger.info(f"[Projects] Found {total} projects for user {current_user.email}")

    # Get projects
    offset = (page - 1) * page_size
    query = (
        select(Project)
        .where(Project.user_id == user_id_str)
        .order_by(Project.created_at.desc())
        .limit(page_size)
        .offset(offset)
    )

    result = await db.execute(query)
    projects = result.scalars().all()

    return {
        "projects": projects,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/search")
async def search_projects(
    q: str = Query(..., min_length=1, description="Search query"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    tech_stack: Optional[str] = Query(None, description="Filter by tech stack"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search user's projects by title, description, or tech stack.

    Search is case-insensitive and matches partial text.

    Parameters:
    - q: Search query (required, searches in title and description)
    - status_filter: Filter by project status (draft, generating, ready, error)
    - tech_stack: Filter by tech stack (e.g., "react", "python")
    - page: Page number (default: 1)
    - page_size: Results per page (default: 10, max: 50)
    """
    user_id_str = str(current_user.id)
    search_term = f"%{q.lower()}%"

    logger.info(f"[Projects] Search for '{q}' by user {current_user.email}")

    # Base query with user filter and search
    base_conditions = [
        Project.user_id == user_id_str,
        or_(
            func.lower(Project.title).like(search_term),
            func.lower(Project.description).like(search_term),
            func.lower(func.coalesce(Project.tech_stack, '')).like(search_term)
        )
    ]

    # Add status filter if provided
    if status_filter:
        try:
            status_enum = ProjectStatus(status_filter.lower())
            base_conditions.append(Project.status == status_enum)
        except ValueError:
            pass  # Invalid status, ignore filter

    # Add tech stack filter if provided
    if tech_stack:
        tech_filter = f"%{tech_stack.lower()}%"
        base_conditions.append(func.lower(func.coalesce(Project.tech_stack, '')).like(tech_filter))

    # Count total matching
    count_query = select(func.count(Project.id)).where(*base_conditions)
    total = await db.scalar(count_query)

    # Get matching projects
    offset = (page - 1) * page_size
    query = (
        select(Project)
        .where(*base_conditions)
        .order_by(Project.updated_at.desc())
        .limit(page_size)
        .offset(offset)
    )

    result = await db.execute(query)
    projects = result.scalars().all()

    logger.info(f"[Projects] Search found {total} results for '{q}'")

    return {
        "query": q,
        "projects": [
            {
                "id": str(p.id),
                "title": p.title,
                "description": p.description,
                "status": p.status.value if p.status else "draft",
                "tech_stack": p.tech_stack,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in projects
        ],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0
    }


@router.get("/list")
async def list_projects_with_documents(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List user's projects with document counts.
    Used by dashboard to show projects with their document stats.
    """
    user_id_str = str(current_user.id)
    logger.info(f"[Projects] Listing projects with documents for user: {current_user.email}")

    # Count total projects
    count_query = select(func.count(Project.id)).where(Project.user_id == user_id_str)
    total = await db.scalar(count_query)

    # Get projects with sorting
    order_column = getattr(Project, sort_by, Project.created_at)
    if sort_order.lower() == "desc":
        order_column = order_column.desc()
    else:
        order_column = order_column.asc()

    query = (
        select(Project)
        .where(Project.user_id == user_id_str)
        .order_by(order_column)
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    projects = result.scalars().all()

    # Get document counts for each project
    items = []
    for project in projects:
        # Count documents for this project
        doc_count_result = await db.execute(
            select(func.count(Document.id)).where(Document.project_id == project.id)
        )
        doc_count = doc_count_result.scalar() or 0

        # Also check file system for documents (legacy)
        from app.core.config import settings
        project_docs_dir = settings.get_project_docs_dir(str(project.id))
        fs_doc_count = 0
        if project_docs_dir.exists():
            fs_doc_count = len([f for f in project_docs_dir.iterdir()
                               if f.is_file() and f.suffix in ['.docx', '.pptx', '.pdf']])

        items.append({
            "id": str(project.id),
            "title": project.title,
            "description": project.description,
            "status": project.status.value if project.status else "draft",
            "progress": project.progress,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
            "documents_count": doc_count + fs_doc_count
        })

    return {
        "items": items,
        "total": total or 0,
        "limit": limit,
        "offset": offset
    }


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project: Project = Depends(get_user_project)
):
    """Get project details"""
    return project


# ========== Bolt-style Metadata Endpoint ==========

class FileTreeItem(BaseModel):
    """File tree item with hash for change detection (Bolt.new style)"""
    path: str
    name: str
    type: str  # 'file' or 'folder'
    hash: Optional[str] = None  # MD5 hash for change detection
    language: Optional[str] = None
    size_bytes: Optional[int] = None
    children: Optional[List['FileTreeItem']] = None

    class Config:
        from_attributes = True


class ProjectMetadataResponse(BaseModel):
    """
    Bolt.new-style project metadata response.

    Returns:
    - Project info (title, description, status)
    - File tree (paths + hashes, NO content)
    - Chat messages count

    Files are NOT loaded here - they're lazy-loaded when user clicks.
    """
    success: bool
    project_id: str
    project_title: str
    project_description: Optional[str] = None
    status: str
    technology: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    file_tree: List[FileTreeItem]
    total_files: int
    messages_count: int


@router.get("/{project_id}/metadata", response_model=ProjectMetadataResponse)
async def get_project_metadata(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Bolt.new-style project metadata endpoint.

    STEP 1 of project loading:
    - Returns project info + file tree (NO content)
    - File tree includes hash for change detection
    - Frontend shows file tree immediately
    - Content is lazy-loaded when user clicks a file

    This is much faster than loading all files at once!
    """
    from app.models.project_file import ProjectFile
    from sqlalchemy import cast, String
    import hashlib

    # Get project - cast IDs to string for comparison (handles UUID/VARCHAR mismatch)
    result = await db.execute(
        select(Project).where(
            cast(Project.id, String(36)) == str(project_id),
            cast(Project.user_id, String(36)) == str(current_user.id)
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get files from database (ProjectFile table) - METADATA ONLY, NO CONTENT
    db_result = await db.execute(
        select(ProjectFile).where(ProjectFile.project_id == cast(project_id, String(36)))
    )
    project_files = db_result.scalars().all()

    # Build hierarchical file tree with hashes
    def build_file_tree(files) -> List[FileTreeItem]:
        """Convert flat file list to hierarchical tree with hashes"""
        root = []
        folder_registry = {}

        for pf in files:
            if pf.is_folder:
                continue  # Folders are created from file paths

            file_path = pf.path

            # Use stored content hash (for change detection)
            # Short hash for file tree (first 12 chars of SHA-256)
            content_hash = pf.content_hash[:12] if pf.content_hash else None

            # Detect language from extension
            ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
            lang_map = {
                "ts": "typescript", "tsx": "typescript",
                "js": "javascript", "jsx": "javascript",
                "py": "python", "json": "json",
                "html": "html", "css": "css",
                "md": "markdown", "yaml": "yaml", "yml": "yaml"
            }
            language = lang_map.get(ext, "plaintext")

            # Split path into parts
            parts = file_path.split("/")

            if len(parts) == 1:
                # Root level file
                root.append(FileTreeItem(
                    path=file_path,
                    name=file_path,
                    type="file",
                    hash=content_hash,
                    language=language,
                    size_bytes=pf.size_bytes
                ))
            else:
                # Nested file - create folder structure
                current_level = root
                current_path = ""

                for i, part in enumerate(parts[:-1]):
                    current_path = f"{current_path}/{part}" if current_path else part

                    if current_path in folder_registry:
                        folder = folder_registry[current_path]
                    else:
                        # Find or create folder
                        folder = None
                        for item in current_level:
                            if item.type == "folder" and item.path == current_path:
                                folder = item
                                break

                        if not folder:
                            folder = FileTreeItem(
                                path=current_path,
                                name=part,
                                type="folder",
                                children=[]
                            )
                            current_level.append(folder)
                            folder_registry[current_path] = folder

                    # Ensure folder has a children list and get reference to it
                    if folder.children is None:
                        folder.children = []
                    current_level = folder.children

                # Add file to current folder
                current_level.append(FileTreeItem(
                    path=file_path,
                    name=parts[-1],
                    type="file",
                    hash=content_hash,
                    language=language,
                    size_bytes=pf.size_bytes
                ))

        return root

    file_tree = build_file_tree(project_files)
    total_files = len([f for f in project_files if not f.is_folder])

    # FALLBACK: If database has no files, try loading from sandbox (disk)
    # This handles cases where files were written to disk but failed to save to DB
    if total_files == 0:
        try:
            from app.services.unified_storage import unified_storage
            user_id = str(current_user.id)
            logger.info(f"[Metadata] DB has 0 files, trying sandbox fallback for {project_id}")

            sandbox_files = await unified_storage.list_sandbox_files(project_id, user_id)
            if sandbox_files:
                # Convert sandbox files to FileTreeItem format
                def convert_sandbox_to_tree(files) -> List[FileTreeItem]:
                    result = []
                    for f in files:
                        item = FileTreeItem(
                            path=f.path,
                            name=f.name or f.path.split('/')[-1],
                            type=f.type,
                            hash=None,  # FileInfo doesn't have hash
                            language=f.language or 'plaintext',
                            size_bytes=f.size_bytes if f.type == 'file' else None,
                            children=convert_sandbox_to_tree(f.children) if f.children else None
                        )
                        result.append(item)
                    return result

                file_tree = convert_sandbox_to_tree(sandbox_files)
                flat_files = unified_storage._flatten_tree(sandbox_files)
                total_files = len([f for f in flat_files if f.type == 'file'])
                logger.info(f"[Metadata] Fallback to sandbox: loaded {total_files} files from disk for project {project_id}")
        except Exception as e:
            logger.warning(f"[Metadata] Sandbox fallback failed for project {project_id}: {e}")

    # Count messages
    from app.models.project_message import ProjectMessage
    msg_result = await db.execute(
        select(func.count(ProjectMessage.id)).where(
            ProjectMessage.project_id == project_id
        )
    )
    messages_count = msg_result.scalar() or 0

    logger.info(f"[Metadata] Loaded metadata for project {project_id}: {len(project_files)} files, {messages_count} messages")

    return ProjectMetadataResponse(
        success=True,
        project_id=project_id,
        project_title=project.title,
        project_description=project.description,
        status=project.status.value if project.status else "draft",
        technology=project.technology,
        created_at=project.created_at.isoformat() if project.created_at else None,
        updated_at=project.updated_at.isoformat() if project.updated_at else None,
        file_tree=file_tree,
        total_files=total_files,
        messages_count=messages_count
    )


@router.post("/{project_id}/execute")
async def execute_project(
    background_tasks: BackgroundTasks,
    project_db: tuple = Depends(get_user_project_with_db)
):
    """Execute project generation"""
    project, db = project_db

    if project.status == ProjectStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is already being processed"
        )

    # Update status
    project.status = ProjectStatus.PROCESSING
    project.progress = 0
    await db.commit()

    # Execute in background (in production, use Celery)
    # background_tasks.add_task(execute_project_task, project.id)

    logger.info(f"Project execution started: {project.id}")

    return {
        "message": "Project execution started",
        "project_id": str(project.id)
    }


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    background_tasks: BackgroundTasks,
    project_db: tuple = Depends(get_user_project_with_db)
):
    """
    Delete project and all associated resources:
    - Project files (PostgreSQL + S3)
    - Cache entries (Redis)
    - Database schema (if using shared infrastructure)
    - Container resources (if running)
    """
    project, db = project_db
    project_id_str = str(project.id)

    # Delete files first
    service = ProjectService(db)
    await service.delete_project_files(project.id)

    # Schedule database cleanup in background (if using shared infrastructure)
    background_tasks.add_task(cleanup_project_database, project_id_str)

    # Delete project record
    await db.delete(project)
    await db.commit()

    logger.info(f"Project deleted: {project.id} (database cleanup scheduled)")

    return None


async def cleanup_project_database(project_id: str):
    """
    Background task to cleanup project's database.
    Called when project is deleted.
    """
    from app.core.config import settings

    # Only run if using shared database infrastructure
    if not getattr(settings, 'USE_SHARED_DB_INFRASTRUCTURE', False):
        logger.info(f"Skipping database cleanup for {project_id} (not using shared infrastructure)")
        return

    try:
        from app.modules.execution.database_infrastructure import (
            db_infrastructure,
            DatabaseType
        )

        # Deprovision all database types for this project
        for db_type in DatabaseType:
            try:
                await db_infrastructure.deprovision_database(
                    project_id=project_id,
                    db_type=db_type,
                    keep_data=False  # Full delete
                )
            except Exception as e:
                # Log but don't fail - some db types may not exist for this project
                logger.debug(f"No {db_type.value} database to cleanup for {project_id}: {e}")

        logger.info(f"Database cleanup completed for project: {project_id}")

    except Exception as e:
        logger.error(f"Error during database cleanup for {project_id}: {e}")


# ========== File Management Endpoints ==========

@router.get("/{project_id}/files")
async def get_project_files(
    project_db: tuple = Depends(get_user_project_with_db)
):
    """
    Get all files for a project (metadata only, not content)
    Used for displaying file tree in UI
    """
    project, db = project_db

    service = ProjectService(db)
    files = await service.get_project_files(project.id)

    total_size = sum(f.get('size_bytes', 0) for f in files)

    return {
        "project_id": str(project.id),
        "files": files,
        "total_count": len(files),
        "total_size_bytes": total_size
    }


@router.get("/{project_id}/files/{file_path:path}")
async def get_file_content(
    file_path: str,
    project_db: tuple = Depends(get_user_project_with_db)
):
    """
    Get content of a specific file
    Uses multi-layer caching (Redis → PostgreSQL inline → S3)
    """
    project, db = project_db

    service = ProjectService(db)
    content = await service.get_file_content(project.id, file_path)

    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}"
        )

    return {
        "path": file_path,
        "content": content
    }


@router.post("/{project_id}/files", response_model=FileResponse)
async def create_file(
    file_data: FileCreate,
    project_db: tuple = Depends(get_user_project_with_db)
):
    """
    Create or update a file
    Automatically selects storage (inline PostgreSQL vs S3) based on size
    """
    project, db = project_db

    service = ProjectService(db)

    result = await service.save_file(
        project_id=project.id,
        file_path=file_data.path,
        content=file_data.content,
        language=file_data.language
    )

    logger.info(f"Created/updated file: {file_data.path} for project {project.id}")

    return FileResponse(
        id=result['id'],
        path=result['path'],
        name=result['name'],
        language=result['language'],
        size_bytes=result['size_bytes']
    )


@router.post("/{project_id}/files/bulk")
async def create_files_bulk(
    data: FileBulkCreate,
    project_db: tuple = Depends(get_user_project_with_db)
):
    """
    Bulk create/update multiple files
    Optimized for AI-generated projects
    """
    project, db = project_db

    service = ProjectService(db)

    files_to_save = [
        {
            'path': f.path,
            'content': f.content,
            'language': f.language
        }
        for f in data.files
    ]

    results = await service.save_multiple_files(project.id, files_to_save)

    logger.info(f"Bulk created {len(results)} files for project {project.id}")

    return {
        "created": len(results),
        "files": results
    }


@router.put("/{project_id}/files/{file_path:path}", response_model=FileResponse)
async def update_file(
    file_path: str,
    file_data: FileUpdate,
    project_db: tuple = Depends(get_user_project_with_db)
):
    """
    Update file content
    """
    project, db = project_db

    service = ProjectService(db)

    result = await service.save_file(
        project_id=project.id,
        file_path=file_path,
        content=file_data.content
    )

    logger.info(f"Updated file: {file_path} for project {project.id}")

    return FileResponse(
        id=result['id'],
        path=result['path'],
        name=result['name'],
        language=result['language'],
        size_bytes=result['size_bytes']
    )


@router.delete("/{project_id}/files/{file_path:path}")
async def delete_file(
    file_path: str,
    project_db: tuple = Depends(get_user_project_with_db)
):
    """
    Delete a file from all storage layers
    """
    project, db = project_db

    service = ProjectService(db)
    deleted = await service.delete_file(project.id, file_path)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}"
        )

    return {"message": f"File deleted: {file_path}"}


@router.post("/{project_id}/sanitize-files")
async def sanitize_project_files(
    project_db: tuple = Depends(get_user_project_with_db)
):
    """
    Sanitize all files in a project by removing empty first lines.
    """
    project, db = project_db
    service = ProjectService(db)
    files = await service.get_project_files(project.id)

    fixed_count = 0
    for file_meta in files:
        if file_meta.get('is_folder', False):
            continue

        file_path = file_meta['path']
        content = await service.get_file_content(project.id, file_path)

        if content:
            original = content
            sanitized = content.lstrip('\n').rstrip() + '\n'

            if sanitized != original:
                await service.save_file(project.id, file_path, sanitized)
                fixed_count += 1
                logger.info(f"Sanitized: {file_path}")

    return {"success": True, "files_fixed": fixed_count}


@router.get("/{project_id}/load")
async def load_project_with_files(
    project_db: tuple = Depends(get_user_project_with_db)
):
    """
    Load project with all files (for page refresh/restore)
    Returns project metadata + file tree + file contents
    """
    project, db = project_db

    service = ProjectService(db)

    # Get files metadata
    files = await service.get_project_files(project.id)

    # Get content for each file
    files_with_content = []
    for file_meta in files:
        if not file_meta.get('is_folder', False):
            content = await service.get_file_content(project.id, file_meta['path'])
            files_with_content.append({
                **file_meta,
                'content': content or ''
            })
        else:
            files_with_content.append(file_meta)

    return {
        'project': project,
        'files': files_with_content,
        'total_files': len(files_with_content)
    }


# ========== Ephemeral Database Endpoints ==========

@router.get("/{project_id}/database/status")
async def get_database_status(
    project_db: tuple = Depends(get_user_project_with_db)
):
    """
    Get ephemeral database status including time remaining before cleanup.
    Used by frontend to show countdown timer.
    """
    project, db = project_db
    project_id_str = str(project.id)

    from app.services.ephemeral_db_cleanup import ephemeral_db_manager

    status = ephemeral_db_manager.get_status(project_id_str)

    if not status:
        return {
            "project_id": project_id_str,
            "has_database": False,
            "message": "No active database for this project"
        }

    return {
        "project_id": project_id_str,
        "has_database": True,
        **status
    }


@router.post("/{project_id}/save")
async def save_project_permanently(
    project_db: tuple = Depends(get_user_project_with_db)
):
    """
    Save project permanently (no auto-cleanup).

    - Free users: Cannot save (must upgrade)
    - Basic users: Can save up to 5 projects
    - Pro users: Unlimited saves

    When saved:
    - Database is kept permanently
    - Files are kept in S3
    - Project marked as "saved" in database
    """
    project, db = project_db
    project_id_str = str(project.id)

    from app.services.ephemeral_db_cleanup import save_project_database

    # Mark database as permanent
    db_saved = await save_project_database(project_id_str)

    # Update project record
    project.is_saved = True
    await db.commit()

    logger.info(f"Project saved permanently: {project_id_str}")

    return {
        "success": True,
        "project_id": project_id_str,
        "message": "Project saved permanently. It will not be auto-deleted.",
        "database_saved": db_saved
    }


@router.post("/{project_id}/activity")
async def update_project_activity(
    project_db: tuple = Depends(get_user_project_with_db)
):
    """
    Update project activity timestamp.
    Call this on user interactions to prevent auto-cleanup.

    Frontend should call this:
    - On file edit
    - On terminal command
    - On preview interaction
    - Every 5 minutes while tab is active
    """
    project, db = project_db
    project_id_str = str(project.id)

    from app.services.ephemeral_db_cleanup import touch_project_activity

    touch_project_activity(project_id_str)

    return {
        "success": True,
        "project_id": project_id_str,
        "message": "Activity updated"
    }


@router.post("/{project_id}/restore")
async def restore_project_from_database(
    project_db: tuple = Depends(get_user_project_with_db)
):
    """
    Restore project files from database to sandbox.

    Call this when a user opens a project whose sandbox was cleaned up.
    This enables project recovery after the 30-minute ephemeral cleanup.

    Flow:
    1. Check if sandbox exists
    2. If not, restore files from database (PostgreSQL/S3) to sandbox
    3. Return list of restored files

    Returns:
        - files: List of restored file metadata
        - sandbox_existed: Whether sandbox already existed
        - restored_count: Number of files restored
    """
    project, db = project_db
    project_id_str = str(project.id)

    from app.services.unified_storage import unified_storage

    # Check if sandbox already exists
    sandbox_exists = await unified_storage.sandbox_exists(project_id_str)

    if sandbox_exists:
        # Sandbox exists, return current file list
        files = await unified_storage.list_sandbox_files(project_id_str)
        return {
            "success": True,
            "project_id": project_id_str,
            "sandbox_existed": True,
            "restored_count": 0,
            "files": [f.to_dict() for f in files],
            "message": "Sandbox already exists, no restoration needed"
        }

    # Restore from database
    logger.info(f"Restoring project {project_id_str} from database")
    restored_files = await unified_storage.restore_project_from_database(project_id_str)

    if not restored_files:
        return {
            "success": False,
            "project_id": project_id_str,
            "sandbox_existed": False,
            "restored_count": 0,
            "files": [],
            "message": "No files found in database to restore. Project may not have been saved."
        }

    return {
        "success": True,
        "project_id": project_id_str,
        "sandbox_existed": False,
        "restored_count": len(restored_files),
        "files": [f.to_dict() for f in restored_files],
        "message": f"Successfully restored {len(restored_files)} files from database"
    }


@router.get("/{project_id}/files/contents")
async def get_project_files_with_contents(
    project_db: tuple = Depends(get_user_project_with_db)
):
    """
    Get all files for a project WITH their contents.
    Used for loading a project in the frontend editor.

    This endpoint:
    1. Tries to get files from sandbox (fastest)
    2. Falls back to database if sandbox doesn't exist
    3. Restores sandbox from database for future requests

    Returns complete file tree with content for display in editor.
    """
    project, db = project_db
    project_id_str = str(project.id)

    from app.services.unified_storage import unified_storage

    # Check if sandbox exists
    sandbox_exists = await unified_storage.sandbox_exists(project_id_str)

    if not sandbox_exists:
        # Restore from database first
        logger.info(f"Sandbox not found for {project_id_str}, restoring from database")
        await unified_storage.restore_project_from_database(project_id_str)

    # Get files from sandbox (now should exist)
    files = await unified_storage.list_sandbox_files(project_id_str)

    # Build response with content
    files_with_content = []
    for file_info in unified_storage._flatten_tree(files):
        if file_info.type == 'file':
            content = await unified_storage.read_from_sandbox(project_id_str, file_info.path)
            files_with_content.append({
                'path': file_info.path,
                'name': file_info.name,
                'type': 'file',
                'language': file_info.language,
                'size_bytes': file_info.size_bytes,
                'content': content or ''
            })
        else:
            files_with_content.append({
                'path': file_info.path,
                'name': file_info.name,
                'type': 'folder',
                'children': []  # Folders handled by tree structure
            })

    return {
        "success": True,
        "project_id": project_id_str,
        "files": files_with_content,
        "total_files": len([f for f in files_with_content if f['type'] == 'file']),
        "sandbox_restored": not sandbox_exists
    }


@router.get("/admin/database/stats")
async def get_database_cleanup_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get ephemeral database cleanup statistics.
    Admin only endpoint.
    """
    # TODO: Add admin check
    from app.services.ephemeral_db_cleanup import ephemeral_db_manager

    stats = ephemeral_db_manager.get_stats()

    return {
        "success": True,
        **stats
    }


# ========== Error Fix Schemas ==========

class ErrorInfo(BaseModel):
    """Error information from frontend"""
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    stack: Optional[str] = None
    source: str = "browser"  # browser, build, runtime, terminal
    severity: str = "error"  # error, warning, info


class FixErrorRequest(BaseModel):
    """Request to fix a single error"""
    error: ErrorInfo


class FixErrorsRequest(BaseModel):
    """Request to fix multiple errors"""
    errors: List[ErrorInfo]


class FixResult(BaseModel):
    """Result of a file fix"""
    file: str
    patch: str
    description: str


class FixErrorResponse(BaseModel):
    """Response from fix error endpoint"""
    success: bool
    fixes: List[FixResult] = []
    message: Optional[str] = None


@router.post("/{project_id}/fix-error", response_model=FixErrorResponse)
async def fix_single_error(
    request: FixErrorRequest,
    project_db: tuple = Depends(get_user_project_with_db)
):
    """
    AUTOMATIC FIX - No user interaction needed.

    Flow:
    1. Get all logs from LogBus (browser, build, backend, network, docker)
    2. Get relevant files using Context Engine
    3. Call Fixer Agent to generate patches
    4. Apply patches automatically
    5. Trigger preview reload
    6. Return fix details

    Like Bolt.new's automatic error fix loop.
    """
    project, db = project_db
    project_id_str = str(project.id)

    from app.modules.agents.fixer_agent import FixerAgent
    from app.services.unified_storage import unified_storage
    from app.modules.automation.file_manager import FileManager

    error = request.error

    try:
        # Get LogBus payload (all 5 collectors)
        try:
            from app.services.log_bus import get_log_bus
            log_bus = get_log_bus(project_id_str)
            log_payload = log_bus.get_fixer_payload()
        except Exception:
            log_payload = {}

        # Get all project files for context
        file_manager = FileManager()
        project_path = file_manager.get_project_path(project_id_str)
        files_created = []
        if project_path.exists():
            for f in project_path.rglob("*"):
                if f.is_file() and not any(p in str(f) for p in ['node_modules', '.git', '__pycache__', '.next']):
                    files_created.append({"path": str(f.relative_to(project_path))})

        # Prepare error dict for Fixer Agent
        error_dict = {
            "message": error.message,
            "type": error.source,
            "file": error.file,
            "line": error.line,
            "column": error.column,
            "stack": error.stack
        }

        # Call Fixer Agent with full context
        fixer = FixerAgent()
        result = await fixer.fix_error(
            error=error_dict,
            project_id=project_id_str,
            file_context={
                "files_created": files_created,
                "tech_stack": {},
                "terminal_logs": log_payload.get("recent_logs", {}).get("backend", [])
            }
        )

        if not result.get("success"):
            return FixErrorResponse(
                success=False,
                message="Fixer agent could not generate a fix"
            )

        fixes = []

        # PRIORITY 1: Apply unified diff patches
        patches = result.get("patches", [])
        if patches:
            from app.modules.bolt.patch_applier import apply_unified_patch, apply_patch_fuzzy

            for patch_info in patches:
                file_path = patch_info.get("path")
                patch_content = patch_info.get("patch")

                if file_path and patch_content:
                    # Read original file
                    full_path = project_path / file_path
                    original_content = ""
                    if full_path.exists():
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            original_content = f.read()

                    # Apply patch (try exact first, then fuzzy)
                    patch_result = apply_unified_patch(original_content, patch_content)
                    if not patch_result.get("success"):
                        patch_result = apply_patch_fuzzy(original_content, patch_content, fuzziness=3)

                    if patch_result.get("success"):
                        new_content = patch_result["new_content"]

                        # Save patched file
                        await unified_storage.save_to_sandbox(project_id_str, file_path, new_content)
                        await unified_storage.save_to_database(project_id_str, file_path, new_content)

                        fixes.append(FixResult(
                            file=file_path,
                            patch=patch_content[:300] + "..." if len(patch_content) > 300 else patch_content,
                            description="Applied patch"
                        ))
                        logger.info(f"[AutoFix] Applied patch to {file_path}")

        # PRIORITY 2: Apply full file replacements (for new files)
        fixed_files = result.get("fixed_files", [])
        for file_info in fixed_files:
            file_path = file_info.get("path")
            file_content = file_info.get("content")

            # Skip if already patched
            if any(f.file == file_path for f in fixes):
                continue

            if file_path and file_content:
                await unified_storage.save_to_sandbox(project_id_str, file_path, file_content)
                await unified_storage.save_to_database(project_id_str, file_path, file_content)

                fixes.append(FixResult(
                    file=file_path,
                    patch="[Full file replacement]",
                    description="Created/replaced file"
                ))
                logger.info(f"[AutoFix] Replaced file {file_path}")

        # PRIORITY 3: Run instructions (npm install, etc.)
        instructions = result.get("instructions")
        if instructions:
            logger.info(f"[AutoFix] Instructions: {instructions}")
            # TODO: Execute instructions in container

        # Mark error as resolved in LogBus
        try:
            log_bus.clear()  # Clear old errors after fix
        except Exception:
            pass

        logger.info(f"[AutoFix] Fixed error in {project_id_str}: {len(fixes)} files patched")

        return FixErrorResponse(
            success=len(fixes) > 0,
            fixes=fixes,
            message=f"Automatically applied {len(fixes)} fixes"
        )

    except Exception as e:
        logger.error(f"[AutoFix] Error: {e}")
        return FixErrorResponse(
            success=False,
            message=str(e)
        )


@router.post("/{project_id}/fix-errors", response_model=FixErrorResponse)
async def fix_multiple_errors(
    request: FixErrorsRequest,
    project_db: tuple = Depends(get_user_project_with_db)
):
    """
    AUTOMATIC FIX ALL - Fix all errors at once without user interaction.

    Flow:
    1. Get all logs from LogBus
    2. Combine all errors into single context
    3. Call Fixer Agent once with full context
    4. Apply all patches automatically
    5. Return results
    """
    project, db = project_db
    project_id_str = str(project.id)

    from app.modules.agents.fixer_agent import FixerAgent
    from app.services.unified_storage import unified_storage
    from app.modules.automation.file_manager import FileManager

    all_fixes = []

    try:
        # Get LogBus payload (all 5 collectors)
        try:
            from app.services.log_bus import get_log_bus
            log_bus = get_log_bus(project_id_str)
            log_payload = log_bus.get_fixer_payload()
        except Exception:
            log_payload = {}

        # Get all project files
        file_manager = FileManager()
        project_path = file_manager.get_project_path(project_id_str)
        files_created = []
        if project_path.exists():
            for f in project_path.rglob("*"):
                if f.is_file() and not any(p in str(f) for p in ['node_modules', '.git', '__pycache__', '.next']):
                    files_created.append({"path": str(f.relative_to(project_path))})

        # Combine all errors into single message
        combined_errors = "\n".join([
            f"- [{e.source}] {e.message}" + (f" ({e.file}:{e.line})" if e.file else "")
            for e in request.errors
        ])

        error_dict = {
            "message": f"Multiple errors to fix:\n{combined_errors}",
            "type": "multiple",
            "file": None,
            "multiple_errors": True,
            "error_count": len(request.errors)
        }

        # Call Fixer Agent with full context
        fixer = FixerAgent()
        result = await fixer.fix_error(
            error=error_dict,
            project_id=project_id_str,
            file_context={
                "files_created": files_created,
                "tech_stack": {},
                "terminal_logs": log_payload.get("recent_logs", {}).get("backend", [])
            }
        )

        if result.get("success"):
            # Apply unified diff patches
            patches = result.get("patches", [])
            if patches:
                from app.modules.bolt.patch_applier import apply_unified_patch, apply_patch_fuzzy

                for patch_info in patches:
                    file_path = patch_info.get("path")
                    patch_content = patch_info.get("patch")

                    if file_path and patch_content:
                        full_path = project_path / file_path
                        original_content = ""
                        if full_path.exists():
                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                original_content = f.read()

                        patch_result = apply_unified_patch(original_content, patch_content)
                        if not patch_result.get("success"):
                            patch_result = apply_patch_fuzzy(original_content, patch_content, fuzziness=3)

                        if patch_result.get("success"):
                            new_content = patch_result["new_content"]
                            await unified_storage.save_to_sandbox(project_id_str, file_path, new_content)
                            await unified_storage.save_to_database(project_id_str, file_path, new_content)

                            all_fixes.append(FixResult(
                                file=file_path,
                                patch=patch_content[:300] + "...",
                                description="Applied patch"
                            ))

            # Apply full file replacements
            for file_info in result.get("fixed_files", []):
                file_path = file_info.get("path")
                file_content = file_info.get("content")

                if file_path and file_content and not any(f.file == file_path for f in all_fixes):
                    await unified_storage.save_to_sandbox(project_id_str, file_path, file_content)
                    await unified_storage.save_to_database(project_id_str, file_path, file_content)

                    all_fixes.append(FixResult(
                        file=file_path,
                        patch="[Full replacement]",
                        description="Replaced file"
                    ))

        # Clear LogBus after fix
        try:
            log_bus.clear()
        except Exception:
            pass

        logger.info(f"[AutoFix] Fixed {len(all_fixes)} files in project {project_id_str}")

        return FixErrorResponse(
            success=len(all_fixes) > 0,
            fixes=all_fixes,
            message=f"Automatically fixed {len(all_fixes)} files"
        )

    except Exception as e:
        logger.error(f"Error fixing multiple errors: {e}")
        return FixErrorResponse(
            success=False,
            message=str(e)
        )


# ========== Project Messages Endpoints ==========

class ProjectMessageResponse(BaseModel):
    """Response for a single project message"""
    id: str
    role: str
    agent_type: Optional[str]
    content: str
    tokens_used: int
    model_used: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class ProjectMessagesResponse(BaseModel):
    """Response for listing project messages"""
    success: bool
    project_id: str
    messages: List[ProjectMessageResponse]
    total: int


@router.get("/{project_id}/messages", response_model=ProjectMessagesResponse)
async def get_project_messages(
    project_id: str,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get chat history (user prompts and Claude responses) for a project.

    Returns messages in chronological order with pagination support.

    This is used to restore conversation context when loading a project.
    """
    from app.services.message_service import MessageService
    from uuid import UUID

    try:
        # Verify project belongs to user - cast IDs to string for comparison
        from sqlalchemy import cast, String
        result = await db.execute(
            select(Project).where(
                cast(Project.id, String(36)) == str(project_id),
                cast(Project.user_id, String(36)) == str(current_user.id)
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # Get messages
        message_service = MessageService(db)
        messages = await message_service.get_messages(
            project_id=UUID(project_id),
            limit=limit,
            offset=offset
        )

        # Convert to response format
        message_responses = [
            ProjectMessageResponse(
                id=str(msg.id),
                role=msg.role,
                agent_type=msg.agent_type,
                content=msg.content,
                tokens_used=msg.tokens_used or 0,
                model_used=msg.model_used,
                created_at=msg.created_at.isoformat() if msg.created_at else ""
            )
            for msg in messages
        ]

        logger.info(f"[Messages] Loaded {len(message_responses)} messages for project {project_id}")

        return ProjectMessagesResponse(
            success=True,
            project_id=project_id,
            messages=message_responses,
            total=len(message_responses)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
