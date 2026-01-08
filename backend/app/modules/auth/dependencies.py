from fastapi import Depends, HTTPException, status, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Tuple
import uuid

from app.core.database import get_db
from app.core.security import decode_token
from app.core.logging_config import logger, set_user_id, set_project_id
from app.models.user import User, UserRole
from app.models.project import Project

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if token provided, None otherwise (for dev/optional auth)"""
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = decode_token(token)

        if payload.get("type") != "access":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        try:
            uuid.UUID(user_id)
        except ValueError:
            return None

        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        return user if user and user.is_active else None
    except (HTTPException, ValueError) as e:
        logger.debug(f"Optional auth validation error: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error in get_optional_user: {type(e).__name__}: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""

    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
        logger.warning("Invalid token type in get_current_user", extra={"event_type": "auth_validation_failed"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    user_id = payload.get("sub")
    if not user_id:
        logger.warning("Missing user_id in token payload", extra={"event_type": "auth_validation_failed"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Validate user_id is a valid UUID format
    try:
        uuid.UUID(user_id)  # Just validate, don't convert
    except ValueError:
        logger.warning(f"Invalid user_id format: {user_id}", extra={"event_type": "auth_validation_failed"})
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
        logger.warning(f"User not found for id: {user_id}", extra={"event_type": "auth_validation_failed"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {user.email}", extra={"event_type": "auth_validation_failed"})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Set user context for downstream logging
    set_user_id(str(user.id))

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


# Alias for require_admin (used in some endpoints)
require_admin = get_current_admin


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
    """Get current user ID (optional)"""
    if not credentials:
        return None

    token = credentials.credentials
    payload = decode_token(token)
    return payload.get("sub")


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current authenticated user (optional - returns None if not authenticated)"""
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = decode_token(token)

        if payload.get("type") != "access":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        # Validate user_id is a valid UUID format
        try:
            uuid.UUID(user_id)
        except ValueError:
            return None

        # Get user from database
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            return None

        return user
    except (HTTPException, ValueError) as e:
        logger.debug(f"Optional user auth error: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error in get_current_user_optional: {type(e).__name__}: {e}")
        return None


async def get_current_user_from_token(
    token: str,
    db: AsyncSession
) -> User:
    """
    Get current user from a raw token string.
    Useful for WebSocket authentication where you can't use Depends.
    """
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

    try:
        uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format"
        )

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
        logger.warning(
            f"Project not found or access denied: {project_id_str}",
            extra={"event_type": "project_access_denied", "project_id": project_id_str}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Set project context for downstream logging
    set_project_id(project_id_str)

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
