from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse
)
from app.modules.auth.dependencies import get_current_user
from app.modules.orchestrator.multi_agent_orchestrator import orchestrator
from app.core.logging_config import logger

router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new project"""

    # Create project
    project = Project(
        user_id=current_user.id,
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
        status=ProjectStatus.DRAFT
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    logger.info(f"Project created: {project.id}")

    return project


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's projects"""

    # Count total
    count_query = select(func.count(Project.id)).where(Project.user_id == current_user.id)
    total = await db.scalar(count_query)

    # Get projects
    offset = (page - 1) * page_size
    query = (
        select(Project)
        .where(Project.user_id == current_user.id)
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


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project details"""

    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return project


@router.post("/{project_id}/execute")
async def execute_project(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute project generation"""

    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

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
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete project"""

    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    await db.delete(project)
    await db.commit()

    logger.info(f"Project deleted: {project_id}")

    return None
