from fastapi import Depends, Header, HTTPException, status, Path
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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user.

    Credentials are collected with auto_error off so that a *missing*
    Authorization header answers 401 rather than the 403 HTTPBearer raises
    by default. The difference is not cosmetic: 401 means "sign in", 403
    means "signed in, but not yours", and clients branch on exactly that.
    While the two were conflated, every signed-out visitor to the student
    registration page was told the area belonged to someone else and was
    bounced to the builder instead of to the login screen.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
    if (current_user.role not in (UserRole.ADMIN, UserRole.MANAGER)
            and not current_user.is_superuser):
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


async def get_current_trainer(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    x_college_id: Optional[str] = Header(None, alias="X-College-Id"),
    x_trainer_id: Optional[str] = Header(None, alias="X-Trainer-Id"),
) -> User:
    """
    Get current trainer.

    Trainer is its own role rather than a capacity of a faculty account: the
    trainer portal is a separate surface with its own screens, so a faculty
    login is not admitted here. Admins keep access for support.

    Their colleges are resolved here, once, and cached on the request. A
    trainer is platform staff with no college of their own, so without this
    every scoped query would have nothing to compare against - and doing it
    here means no endpoint can forget.
    """
    if current_user.role not in [UserRole.TRAINER, UserRole.ADMIN,
                                 UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trainer access required"
        )
    from app.services.tenancy import load_trainer_tenants
    assigned = await load_trainer_tenants(db, current_user)

    # The college they are currently working in. Narrowing here, once, is what
    # makes every screen show one institution at a time - two colleges both
    # have a "CSE section A", and a merged view is how a register gets marked
    # against the wrong students.
    if x_college_id:
        # Compared as text. The id arrives as a string and the assigned set
        # holds whatever the column type hands back, so comparing the two
        # directly matched nothing and quietly left the trainer seeing every
        # college they teach - the exact opposite of what choosing one means.
        wanted = str(x_college_id).strip().lower()
        match = next((c for c in assigned if str(c).lower() == wanted), None)
        # An unrecognised choice is ignored rather than obeyed: falling back to
        # everything they are assigned is safe, while trusting a header would
        # let a client name any college at all.
        if match is not None:
            current_user._tenant_ids = {match}

    # And which trainer they are looking at. Only a manager may ask: a trainer
    # narrowed to another trainer would be reading a colleague's batches, which
    # is the manager's job and not theirs.
    if x_trainer_id and current_user.role == UserRole.MANAGER:
        from app.services.tenancy import tenants_of
        from app.models.trainer_assignment import TrainerAssignment
        # Accepted only if that trainer actually works in a college the manager
        # is currently looking at. Otherwise the filter is dropped rather than
        # obeyed - narrowing to somebody with no assignment here would show an
        # empty portal and read as "this trainer does nothing".
        allowed = (await db.execute(
            select(TrainerAssignment.trainer_id)
            .where(TrainerAssignment.is_active.is_(True))
            .where(TrainerAssignment.college_id.in_(tenants_of(current_user)))
        )).scalars().all()
        wanted = str(x_trainer_id).strip().lower()
        match = next((t for t in allowed if str(t).lower() == wanted), None)
        if match is not None:
            current_user._focus_trainer_id = match
    return current_user


async def get_platform_staff(
    current_user: User = Depends(get_current_admin)
) -> User:
    """
    Somebody who runs the platform's operations, across every college.

    The operator and their managers. Wider than `get_platform_admin` and
    narrower than `get_current_admin`: a college's own administrator is kept
    out - onboarding colleges and moving trainers between them is not a
    customer's business - while a manager is let in, because running those is
    the whole of their job.
    """
    if current_user.is_superuser or current_user.role == UserRole.MANAGER:
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This area belongs to the platform operator, not to a college.",
    )


async def get_platform_admin(
    current_user: User = Depends(get_current_admin)
) -> User:
    """
    An administrator of the platform, not of a college.

    Once the product is sold to more than one institution, "admin" stops being
    one thing. A college needs an administrator for its own staff and students;
    the vendor needs one for revenue, plans, API keys and every tenant at once.
    Both carry UserRole.ADMIN today, so `is_superuser` is what separates them -
    it already existed and already means exactly this.

    Guarding the platform routers with it keeps a customer's administrator out
    of the business's revenue figures and cross-tenant analytics.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This area belongs to the platform operator, not to a college.",
        )
    return current_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security)
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

async def _may_open(db: AsyncSession, user: User, project: Project) -> bool:
    """Whether this account may open that project. See `get_user_project`."""
    if project.user_id and str(project.user_id) == str(user.id):
        return True

    batch_id = getattr(project, "batch_id", None)
    if not batch_id:
        # A personal project with no owner left. Nobody inherits it.
        return False

    from app.models.faculty import ProjectBatch, ProjectBatchMember

    # On the team.
    member = (await db.execute(
        select(ProjectBatchMember.id)
        .where(ProjectBatchMember.batch_id == batch_id)
        .where(ProjectBatchMember.student_id == user.id)
        .limit(1)
    )).scalars().first()
    if member is not None:
        return True

    # Or responsible for the batch: its guide or reviewer, the trainer
    # assigned to it, a manager, or an administrator. Decided by the same
    # authority service every other faculty action goes through, so a project
    # cannot be reachable by somebody who could not already open the batch.
    if user.role in (UserRole.STUDENT,):
        return False

    batch = (await db.execute(
        select(ProjectBatch).where(ProjectBatch.id == batch_id)
    )).scalar_one_or_none()
    if batch is None:
        return False

    from app.services.faculty_authority import FacultyAuthority
    from app.services.tenancy import load_trainer_tenants

    if user.role in (UserRole.TRAINER, UserRole.MANAGER):
        # Their colleges have to be resolved before authority can be asked;
        # outside a request nothing has done it yet.
        if getattr(user, "_tenant_ids", None) is None:
            await load_trainer_tenants(db, user)
    try:
        return await FacultyAuthority(db).can_view(user, batch)
    except Exception as exc:
        logger.warning(f"Project access check failed for {user.email}: "
                       f"{type(exc).__name__}: {exc}")
        return False


async def get_user_project(
    project_id: str = Path(..., description="Project ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Project:
    """
    Get a project the caller is entitled to open, or 404.

    Two kinds of project, one rule each:

    A personal project belongs to the account that made it, and nobody else
    sees it. That was the only case this handled.

    A batch project belongs to a team. Four students share it the way four
    developers share a repository, so the rule is membership: you may open it
    if you are on that batch. That is also what keeps batches apart - a
    student on CSE-A-002 is not a member of CSE-A-001 and gets the same 404 a
    stranger would, in their own college or any other. Their trainer and the
    batch's guide are admitted too, because reviewing the work is their job.

    404 rather than 403 throughout: telling somebody a project exists but is
    not theirs is itself worth something, and this endpoint is reachable by
    guessing ids.
    """
    project_id_str = str(project_id)
    user_id_str = str(current_user.id)

    project = (await db.execute(
        select(Project).where(Project.id == project_id_str)
    )).scalar_one_or_none()

    if project is not None and not await _may_open(db, current_user, project):
        project = None

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
