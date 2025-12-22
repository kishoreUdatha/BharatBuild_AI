"""
Admin Project Management endpoints.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Request, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from datetime import datetime, timedelta
from typing import Optional
import math
import zipfile
import io
import os
import tempfile

from app.core.database import get_db
from app.models import User, Project, ProjectStatus, ProjectFile, AuditLog
from app.modules.auth.dependencies import get_current_admin
from app.schemas.admin import AdminProjectResponse, AdminProjectsResponse, StorageStats
from app.services.storage_service import storage_service
from app.core.types import generate_uuid

router = APIRouter()


async def log_admin_action(
    db: AsyncSession,
    admin_id: str,
    action: str,
    target_type: str,
    target_id: str = None,
    details: dict = None,
    request: Request = None
):
    """Log an admin action to audit log"""
    log = AuditLog(
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(log)
    await db.commit()


@router.get("", response_model=AdminProjectsResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    sort_by: str = Query("created_at", regex="^(created_at|title|status|last_activity)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List all projects with filtering, sorting, and pagination"""

    # Build base query with user join
    query = select(Project, User).join(User, Project.user_id == User.id)

    # Apply filters
    conditions = []
    if search:
        search_term = f"%{search}%"
        conditions.append(or_(
            Project.title.ilike(search_term),
            Project.description.ilike(search_term),
            User.email.ilike(search_term)
        ))

    if status:
        try:
            status_enum = ProjectStatus(status)
            conditions.append(Project.status == status_enum)
        except ValueError:
            pass

    if user_id:
        conditions.append(Project.user_id == user_id)

    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(
        select(Project).join(User, Project.user_id == User.id)
        .where(and_(*conditions) if conditions else True)
        .subquery()
    )
    total = await db.scalar(count_query)

    # Apply sorting
    sort_column = getattr(Project, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    rows = result.all()

    # Build response
    items = []
    for project, user in rows:
        # Get files count
        files_count = await db.scalar(
            select(func.count(ProjectFile.id)).where(ProjectFile.project_id == project.id)
        )

        items.append(AdminProjectResponse(
            id=str(project.id),
            title=project.title,
            description=project.description,
            status=project.status.value if project.status else "draft",
            mode=project.mode.value if project.mode else "student",
            user_id=str(project.user_id),
            user_email=user.email,
            user_name=user.full_name,
            files_count=files_count or 0,
            storage_size_mb=0.0,  # TODO: Calculate from file sizes
            created_at=project.created_at,
            updated_at=project.updated_at,
            last_activity=project.last_activity
        ))

    return AdminProjectsResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
        total_pages=math.ceil((total or 0) / page_size) if total and total > 0 else 1
    )


@router.get("/stats")
async def get_project_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get project statistics"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start.replace(day=1)

    total_projects = await db.scalar(select(func.count(Project.id)))

    # Projects by status
    status_counts = {}
    for status in ProjectStatus:
        count = await db.scalar(
            select(func.count(Project.id)).where(Project.status == status)
        )
        status_counts[status.value] = count or 0

    # Projects created today/week/month
    projects_today = await db.scalar(
        select(func.count(Project.id)).where(Project.created_at >= today_start)
    )
    projects_this_week = await db.scalar(
        select(func.count(Project.id)).where(Project.created_at >= week_start)
    )
    projects_this_month = await db.scalar(
        select(func.count(Project.id)).where(Project.created_at >= month_start)
    )

    # Active projects (activity in last 7 days)
    active_projects = await db.scalar(
        select(func.count(Project.id)).where(
            Project.last_activity >= now - timedelta(days=7)
        )
    )

    # Total files
    total_files = await db.scalar(select(func.count(ProjectFile.id)))

    return {
        "total_projects": total_projects or 0,
        "active_projects": active_projects or 0,
        "projects_by_status": status_counts,
        "projects_today": projects_today or 0,
        "projects_this_week": projects_this_week or 0,
        "projects_this_month": projects_this_month or 0,
        "total_files": total_files or 0
    }


@router.get("/storage", response_model=StorageStats)
async def get_storage_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get storage usage statistics"""

    # This is a simplified version - in production, you'd calculate actual file sizes
    total_projects = await db.scalar(select(func.count(Project.id)))
    total_files = await db.scalar(select(func.count(ProjectFile.id)))

    # Estimate storage (simplified)
    estimated_storage_gb = (total_files or 0) * 0.01 / 1024  # Assume 10KB per file average

    # Get top users by project count
    top_users_query = (
        select(User.email, User.full_name, func.count(Project.id).label("project_count"))
        .join(Project, User.id == Project.user_id)
        .group_by(User.id)
        .order_by(func.count(Project.id).desc())
        .limit(10)
    )
    result = await db.execute(top_users_query)
    storage_by_user = [
        {"email": row.email, "name": row.full_name, "projects": row.project_count, "estimated_mb": row.project_count * 10}
        for row in result
    ]

    # Get top projects by file count
    top_projects_query = (
        select(Project.id, Project.title, func.count(ProjectFile.id).label("files_count"))
        .join(ProjectFile, Project.id == ProjectFile.project_id)
        .group_by(Project.id)
        .order_by(func.count(ProjectFile.id).desc())
        .limit(10)
    )
    result = await db.execute(top_projects_query)
    storage_by_project = [
        {"id": str(row.id), "title": row.title, "files": row.files_count, "estimated_mb": row.files_count * 0.01}
        for row in result
    ]

    return StorageStats(
        total_storage_gb=100.0,  # Placeholder - would be actual S3 bucket size
        used_storage_gb=estimated_storage_gb,
        storage_by_user=storage_by_user,
        storage_by_project=storage_by_project
    )


@router.get("/{project_id}", response_model=AdminProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get a specific project by ID"""
    result = await db.execute(
        select(Project, User)
        .join(User, Project.user_id == User.id)
        .where(Project.id == project_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    project, user = row

    files_count = await db.scalar(
        select(func.count(ProjectFile.id)).where(ProjectFile.project_id == project.id)
    )

    return AdminProjectResponse(
        id=str(project.id),
        title=project.title,
        description=project.description,
        status=project.status.value if project.status else "draft",
        mode=project.mode.value if project.mode else "student",
        user_id=str(project.user_id),
        user_email=user.email,
        user_name=user.full_name,
        files_count=files_count or 0,
        storage_size_mb=0.0,
        created_at=project.created_at,
        updated_at=project.updated_at,
        last_activity=project.last_activity
    )


@router.patch("/{project_id}/status")
async def update_project_status(
    project_id: str,
    status: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Update project status"""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        new_status = ProjectStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    old_status = project.status.value if project.status else None
    project.status = new_status
    project.updated_at = datetime.utcnow()
    await db.commit()

    await log_admin_action(
        db=db,
        admin_id=str(current_admin.id),
        action="project_status_updated",
        target_type="project",
        target_id=project_id,
        details={"old_status": old_status, "new_status": status},
        request=request
    )

    return {"message": f"Project status updated to {status}"}


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Delete a project (hard delete)"""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_title = project.title

    # Delete project and cascade to files
    await db.delete(project)
    await db.commit()

    await log_admin_action(
        db=db,
        admin_id=str(current_admin.id),
        action="project_deleted",
        target_type="project",
        target_id=project_id,
        details={"title": project_title},
        request=request
    )

    return {"message": f"Project '{project_title}' has been deleted"}


@router.get("/{project_id}/download")
async def download_project(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Download a project as ZIP file.
    Admin can download any user's project for backup or inspection.
    """
    # Get project with files
    result = await db.execute(
        select(Project, User)
        .join(User, Project.user_id == User.id)
        .where(Project.id == project_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    project, user = row

    # Get all project files from database
    files_result = await db.execute(
        select(ProjectFile).where(
            ProjectFile.project_id == project_id,
            ProjectFile.is_folder == False
        )
    )
    files = files_result.scalars().all()

    if not files:
        raise HTTPException(status_code=404, detail="No files found in project")

    # Create ZIP in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            content = None

            # Try to get content from S3
            if file.s3_key:
                try:
                    content_bytes = await storage_service.download_file(file.s3_key)
                    if content_bytes:
                        content = content_bytes
                except Exception as e:
                    pass

            # Fallback to inline content (legacy)
            if not content and file.content_inline:
                content = file.content_inline.encode('utf-8')

            if content:
                # Write file to ZIP
                zf.writestr(file.path, content)

    # Seek to beginning
    zip_buffer.seek(0)

    # Sanitize filename
    safe_title = "".join(c for c in project.title if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_title = safe_title or "project"
    filename = f"{safe_title}_{project_id[:8]}.zip"

    # Log admin action
    await log_admin_action(
        db=db,
        admin_id=str(current_admin.id),
        action="project_downloaded",
        target_type="project",
        target_id=project_id,
        details={"title": project.title, "owner": user.email, "files_count": len(files)},
        request=request
    )

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# File extensions to process (text-based files)
TEXT_EXTENSIONS = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h', '.hpp',
    '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.html',
    '.css', '.scss', '.less', '.json', '.xml', '.yaml', '.yml', '.md', '.txt',
    '.sql', '.sh', '.bat', '.ps1', '.env', '.gitignore', '.dockerignore',
    '.dockerfile', '.makefile', '.gradle', '.properties', '.ini', '.cfg',
    '.vue', '.svelte', '.astro', '.prisma', '.graphql', '.proto'
}

# Directories to skip
SKIP_DIRS = {
    'node_modules', '.git', '__pycache__', '.venv', 'venv', 'env',
    '.idea', '.vscode', 'dist', 'build', 'target', '.next', '.nuxt',
    'coverage', '.pytest_cache', '.mypy_cache', 'vendor', 'packages'
}

MAX_FILE_SIZE = 100 * 1024  # 100KB per file
MAX_TOTAL_SIZE = 50 * 1024 * 1024  # 50MB total for admin upload


def get_language_from_extension(ext: str) -> str:
    """Map file extension to language"""
    mapping = {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.tsx': 'typescriptreact', '.jsx': 'javascriptreact',
        '.java': 'java', '.cpp': 'cpp', '.c': 'c', '.h': 'c', '.hpp': 'cpp',
        '.cs': 'csharp', '.go': 'go', '.rs': 'rust', '.rb': 'ruby',
        '.php': 'php', '.swift': 'swift', '.kt': 'kotlin', '.scala': 'scala',
        '.html': 'html', '.css': 'css', '.scss': 'scss', '.less': 'less',
        '.json': 'json', '.xml': 'xml', '.yaml': 'yaml', '.yml': 'yaml',
        '.md': 'markdown', '.txt': 'plaintext', '.sql': 'sql',
        '.sh': 'bash', '.bat': 'batch', '.ps1': 'powershell',
        '.vue': 'vue', '.svelte': 'svelte', '.graphql': 'graphql', '.prisma': 'prisma',
    }
    return mapping.get(ext, 'plaintext')


@router.post("/upload")
async def upload_project_for_user(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Form(...),
    project_name: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Upload a project ZIP file for a specific user.
    Admin can upload projects to any user's account.
    """
    # Verify target user exists
    target_user = await db.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported")

    try:
        # Read ZIP file
        content = await file.read()
        if len(content) > MAX_TOTAL_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {MAX_TOTAL_SIZE // (1024*1024)}MB"
            )

        # Extract files from ZIP
        files_data = []
        total_size = 0

        with zipfile.ZipFile(io.BytesIO(content), 'r') as zip_ref:
            for zip_info in zip_ref.infolist():
                # Skip directories
                if zip_info.is_dir():
                    continue

                file_path = zip_info.filename

                # Skip hidden and excluded directories
                path_parts = file_path.split('/')
                if any(part in SKIP_DIRS or part.startswith('.') for part in path_parts[:-1]):
                    continue

                # Skip if file is too large
                if zip_info.file_size > MAX_FILE_SIZE:
                    continue

                # Get file extension
                _, ext = os.path.splitext(file_path.lower())

                # Only process text files
                if ext not in TEXT_EXTENSIONS and not file_path.endswith('Dockerfile'):
                    continue

                # Read file content
                try:
                    with zip_ref.open(zip_info) as f:
                        file_content = f.read().decode('utf-8', errors='ignore')
                        total_size += len(file_content)

                        if total_size > MAX_TOTAL_SIZE:
                            break

                        language = get_language_from_extension(ext)
                        files_data.append({
                            'path': file_path,
                            'content': file_content,
                            'language': language,
                            'size': len(file_content)
                        })
                except Exception:
                    continue

        if not files_data:
            raise HTTPException(status_code=400, detail="No valid source files found in ZIP")

        # Extract project name from ZIP filename if not provided
        if not project_name:
            project_name = os.path.splitext(file.filename)[0]

        # Create project in database
        project_id = str(generate_uuid())
        project = Project(
            id=project_id,
            title=project_name,
            description=f"Uploaded by admin: {current_admin.email}",
            user_id=user_id,
            status=ProjectStatus.COMPLETED
        )
        db.add(project)

        # Create project files and upload to S3
        for file_data in files_data:
            file_content_bytes = file_data['content'].encode('utf-8')

            # Upload to S3
            upload_result = await storage_service.upload_file(
                project_id=project_id,
                file_path=file_data['path'],
                content=file_content_bytes
            )

            # Create file record in database
            project_file = ProjectFile(
                id=str(generate_uuid()),
                project_id=project_id,
                path=file_data['path'],
                name=file_data['path'].split('/')[-1],
                language=file_data['language'],
                s3_key=upload_result.get('s3_key'),
                content_hash=upload_result.get('content_hash'),
                size_bytes=file_data['size'],
                is_folder=False,
                is_inline=False
            )
            db.add(project_file)

        await db.commit()

        # Log admin action
        await log_admin_action(
            db=db,
            admin_id=str(current_admin.id),
            action="project_uploaded",
            target_type="project",
            target_id=project_id,
            details={
                "project_name": project_name,
                "target_user": target_user.email,
                "files_count": len(files_data),
                "total_size": total_size
            },
            request=request
        )

        return {
            "success": True,
            "project_id": project_id,
            "project_name": project_name,
            "target_user": target_user.email,
            "total_files": len(files_data),
            "total_size": total_size,
            "message": f"Project '{project_name}' uploaded successfully for user {target_user.email}"
        }

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
