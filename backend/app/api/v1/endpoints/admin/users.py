"""
Admin User Management endpoints.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import Optional, List
import math

from app.core.database import get_db
from app.models import User, UserRole, Project, Subscription, AuditLog
from app.models.billing import Plan, SubscriptionStatus
from app.modules.auth.dependencies import get_current_admin
from app.schemas.admin import (
    AdminUserResponse, AdminUserUpdate, AdminUsersResponse,
    BulkUserAction, BulkActionType
)

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


@router.get("", response_model=AdminUsersResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    sort_by: str = Query("created_at", regex="^(created_at|email|full_name|role|last_login)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List all users with filtering, sorting, and pagination"""

    # Build base query
    query = select(User)

    # Apply filters
    conditions = []
    if search:
        search_term = f"%{search}%"
        conditions.append(or_(
            User.email.ilike(search_term),
            User.full_name.ilike(search_term),
            User.organization.ilike(search_term),
            User.username.ilike(search_term)
        ))

    if role:
        try:
            role_enum = UserRole(role)
            conditions.append(User.role == role_enum)
        except ValueError:
            pass

    if is_active is not None:
        conditions.append(User.is_active == is_active)

    if is_verified is not None:
        conditions.append(User.is_verified == is_verified)

    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply sorting
    sort_column = getattr(User, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()

    # Build response with usage stats
    items = []
    for user in users:
        # Get projects count
        projects_count = await db.scalar(
            select(func.count(Project.id)).where(Project.user_id == user.id)
        )

        # Get subscription plan name
        subscription_plan_name = None
        subscription_result = await db.execute(
            select(Subscription, Plan)
            .join(Plan, Subscription.plan_id == Plan.id, isouter=True)
            .where(and_(
                Subscription.user_id == user.id,
                Subscription.status == SubscriptionStatus.ACTIVE
            ))
        )
        subscription_row = subscription_result.first()
        if subscription_row:
            subscription, plan = subscription_row
            subscription_plan_name = plan.name if plan else "Free"

        items.append(AdminUserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            username=user.username,
            role=user.role.value if user.role else "student",
            organization=user.organization,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            oauth_provider=user.oauth_provider,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
            last_login=user.last_login,
            projects_count=projects_count or 0,
            tokens_used=0,  # TODO: Calculate from TokenBalance
            subscription_plan=subscription_plan_name
        ))

    return AdminUsersResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1
    )


@router.get("/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get a specific user by ID"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    projects_count = await db.scalar(
        select(func.count(Project.id)).where(Project.user_id == user.id)
    )

    return AdminUserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        username=user.username,
        role=user.role.value if user.role else "student",
        organization=user.organization,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
        oauth_provider=user.oauth_provider,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
        last_login=user.last_login,
        projects_count=projects_count or 0,
        tokens_used=0,
        subscription_plan=None
    )


@router.patch("/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: str,
    update_data: AdminUserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Update a user's details (admin only)"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Track changes for audit log
    changes = {}

    if update_data.full_name is not None and update_data.full_name != user.full_name:
        changes["full_name"] = {"old": user.full_name, "new": update_data.full_name}
        user.full_name = update_data.full_name

    if update_data.role is not None:
        try:
            new_role = UserRole(update_data.role)
            if new_role != user.role:
                changes["role"] = {"old": user.role.value if user.role else None, "new": update_data.role}
                user.role = new_role
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {update_data.role}")

    if update_data.organization is not None and update_data.organization != user.organization:
        changes["organization"] = {"old": user.organization, "new": update_data.organization}
        user.organization = update_data.organization

    if update_data.is_active is not None and update_data.is_active != user.is_active:
        changes["is_active"] = {"old": user.is_active, "new": update_data.is_active}
        user.is_active = update_data.is_active

    if update_data.is_verified is not None and update_data.is_verified != user.is_verified:
        changes["is_verified"] = {"old": user.is_verified, "new": update_data.is_verified}
        user.is_verified = update_data.is_verified

    if update_data.is_superuser is not None and update_data.is_superuser != user.is_superuser:
        changes["is_superuser"] = {"old": user.is_superuser, "new": update_data.is_superuser}
        user.is_superuser = update_data.is_superuser

    if changes:
        user.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(user)

        # Log the action
        await log_admin_action(
            db=db,
            admin_id=str(current_admin.id),
            action="user_updated",
            target_type="user",
            target_id=user_id,
            details={"changes": changes},
            request=request
        )

    projects_count = await db.scalar(
        select(func.count(Project.id)).where(Project.user_id == user.id)
    )

    return AdminUserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        username=user.username,
        role=user.role.value if user.role else "student",
        organization=user.organization,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
        oauth_provider=user.oauth_provider,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
        last_login=user.last_login,
        projects_count=projects_count or 0,
        tokens_used=0,
        subscription_plan=None
    )


@router.post("/{user_id}/suspend")
async def suspend_user(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Suspend a user account"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if str(user.id) == str(current_admin.id):
        raise HTTPException(status_code=400, detail="Cannot suspend yourself")

    user.is_active = False
    user.updated_at = datetime.utcnow()
    await db.commit()

    await log_admin_action(
        db=db,
        admin_id=str(current_admin.id),
        action="user_suspended",
        target_type="user",
        target_id=user_id,
        details={"email": user.email},
        request=request
    )

    return {"message": f"User {user.email} has been suspended"}


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Activate a suspended user account"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    user.updated_at = datetime.utcnow()
    await db.commit()

    await log_admin_action(
        db=db,
        admin_id=str(current_admin.id),
        action="user_activated",
        target_type="user",
        target_id=user_id,
        details={"email": user.email},
        request=request
    )

    return {"message": f"User {user.email} has been activated"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Delete a user (soft delete - sets is_active=False)"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if str(user.id) == str(current_admin.id):
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    # Soft delete
    user.is_active = False
    user.updated_at = datetime.utcnow()
    await db.commit()

    await log_admin_action(
        db=db,
        admin_id=str(current_admin.id),
        action="user_deleted",
        target_type="user",
        target_id=user_id,
        details={"email": user.email},
        request=request
    )

    return {"message": f"User {user.email} has been deleted"}


@router.post("/bulk")
async def bulk_action(
    action_data: BulkUserAction,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Perform bulk actions on users"""
    results = {"success": 0, "failed": 0, "errors": []}

    for user_id in action_data.user_ids:
        try:
            user = await db.get(User, user_id)
            if not user:
                results["errors"].append(f"User {user_id} not found")
                results["failed"] += 1
                continue

            if str(user.id) == str(current_admin.id):
                results["errors"].append("Cannot modify yourself")
                results["failed"] += 1
                continue

            if action_data.action == BulkActionType.SUSPEND:
                user.is_active = False
            elif action_data.action == BulkActionType.ACTIVATE:
                user.is_active = True
            elif action_data.action == BulkActionType.DELETE:
                user.is_active = False
            elif action_data.action == BulkActionType.CHANGE_ROLE:
                if not action_data.role:
                    results["errors"].append("Role is required for CHANGE_ROLE action")
                    results["failed"] += 1
                    continue
                try:
                    user.role = UserRole(action_data.role)
                except ValueError:
                    results["errors"].append(f"Invalid role: {action_data.role}")
                    results["failed"] += 1
                    continue

            user.updated_at = datetime.utcnow()
            results["success"] += 1

        except Exception as e:
            results["errors"].append(str(e))
            results["failed"] += 1

    await db.commit()

    # Log bulk action
    await log_admin_action(
        db=db,
        admin_id=str(current_admin.id),
        action=f"bulk_{action_data.action.value}",
        target_type="user",
        target_id=None,
        details={
            "user_ids": action_data.user_ids,
            "success": results["success"],
            "failed": results["failed"]
        },
        request=request
    )

    return results


@router.get("/export/csv")
async def export_users_csv(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Export all users to CSV format"""
    from fastapi.responses import StreamingResponse
    import csv
    import io

    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "ID", "Email", "Full Name", "Username", "Role",
        "Organization", "Is Active", "Is Verified", "OAuth Provider",
        "Created At", "Last Login"
    ])

    # Write data
    for user in users:
        writer.writerow([
            str(user.id),
            user.email,
            user.full_name or "",
            user.username or "",
            user.role.value if user.role else "student",
            user.organization or "",
            user.is_active,
            user.is_verified,
            user.oauth_provider or "",
            user.created_at.isoformat() if user.created_at else "",
            user.last_login.isoformat() if user.last_login else ""
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users_export.csv"}
    )
