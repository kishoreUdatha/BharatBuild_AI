from fastapi import Depends, HTTPException, status, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Tuple
import uuid

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.models.project import Project

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""

    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Validate user_id is a valid UUID format
    try:
        uuid.UUID(user_id)  # Just validate, don't convert
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format"
        )

    # Get user from database - pass string directly, GUID type handles conversion
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current admin user"""
    if current_user.role != UserRole.ADMIN and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_current_faculty(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current faculty user"""
    if current_user.role not in [UserRole.FACULTY, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faculty access required"
        )
    return current_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """Get current user (optional)"""
    if not credentials:
        return None

    token = credentials.credentials
    payload = decode_token(token)
    return payload.get("sub")


# ==================== Project Ownership Dependencies ====================

async def get_user_project(
    project_id: str = Path(..., description="Project ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Project:
    """
    Get project with ownership verification.
    Raises 404 if project not found or not owned by user.

    Usage:
        @router.get("/{project_id}")
        async def get_project(project: Project = Depends(get_user_project)):
            return project
    """
    project_id_str = str(project_id)
    user_id_str = str(current_user.id)

    result = await db.execute(
        select(Project).where(
            Project.id == project_id_str,
            Project.user_id == user_id_str
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return project


async def get_user_project_with_db(
    project_id: str = Path(..., description="Project ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Tuple[Project, AsyncSession]:
    """
    Get project with ownership verification AND db session.
    Useful when you need both project and db for further operations.

    Usage:
        @router.post("/{project_id}/files")
        async def create_file(
            project_db: Tuple[Project, AsyncSession] = Depends(get_user_project_with_db)
        ):
            project, db = project_db
            # Use project and db
    """
    project = await get_user_project(project_id, current_user, db)
    return project, db
