"""
Admin Dashboard endpoints - KPIs and activity feed.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import get_db
from app.models import User, Project, Subscription, Transaction, UsageLog, AuditLog
from app.modules.auth.dependencies import get_current_admin
from app.schemas.admin import DashboardStats, ActivityFeedResponse, ActivityItem

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get dashboard KPI statistics"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start.replace(day=1)

    # User stats
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(select(func.count(User.id)).where(User.is_active == True))
    new_users_today = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )
    new_users_week = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= week_start)
    )
    new_users_month = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= month_start)
    )

    # Project stats
    total_projects = await db.scalar(select(func.count(Project.id)))
    active_projects = await db.scalar(
        select(func.count(Project.id)).where(
            Project.last_activity >= now - timedelta(days=7)
        )
    )

    # Revenue stats
    total_revenue_result = await db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.status == "success"
        )
    )
    total_revenue = float(total_revenue_result or 0) / 100  # Convert paise to INR

    revenue_month_result = await db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.status == "success",
                Transaction.created_at >= month_start
            )
        )
    )
    revenue_this_month = float(revenue_month_result or 0) / 100

    # Subscription stats
    total_subscriptions = await db.scalar(select(func.count(Subscription.id)))
    active_subscriptions = await db.scalar(
        select(func.count(Subscription.id)).where(Subscription.status == "active")
    )

    # Token/API stats
    total_tokens = await db.scalar(
        select(func.coalesce(func.sum(UsageLog.tokens_used), 0))
    )
    tokens_today = await db.scalar(
        select(func.coalesce(func.sum(UsageLog.tokens_used), 0)).where(
            UsageLog.created_at >= today_start
        )
    )

    total_api_calls = await db.scalar(select(func.count(UsageLog.id)))
    api_calls_today = await db.scalar(
        select(func.count(UsageLog.id)).where(UsageLog.created_at >= today_start)
    )

    # Calculate conversion rate (subscribers / users)
    conversion_rate = 0.0
    if total_users and total_users > 0:
        conversion_rate = round((active_subscriptions or 0) / total_users * 100, 2)

    # Calculate verified users percentage
    verified_users = await db.scalar(
        select(func.count(User.id)).where(User.is_verified == True)
    )
    verification_rate = 0.0
    if total_users and total_users > 0:
        verification_rate = round((verified_users or 0) / total_users * 100, 2)

    return DashboardStats(
        total_users=total_users or 0,
        active_users=active_users or 0,
        new_users_today=new_users_today or 0,
        new_users_this_week=new_users_week or 0,
        new_users_this_month=new_users_month or 0,
        total_projects=total_projects or 0,
        active_projects=active_projects or 0,
        total_revenue=total_revenue,
        revenue_this_month=revenue_this_month,
        total_subscriptions=total_subscriptions or 0,
        active_subscriptions=active_subscriptions or 0,
        total_tokens_used=total_tokens or 0,
        tokens_used_today=tokens_today or 0,
        total_api_calls=total_api_calls or 0,
        api_calls_today=api_calls_today or 0,
        conversion_rate=conversion_rate,
        verification_rate=verification_rate,
        avg_revenue_per_user=round(total_revenue / (total_users or 1), 2)
    )


@router.get("/activity", response_model=ActivityFeedResponse)
async def get_activity_feed(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get recent activity feed for admin dashboard"""
    activities = []

    # Get recent user signups
    recent_users = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .limit(10)
    )
    for user in recent_users.scalars():
        activities.append(ActivityItem(
            id=str(user.id),
            type="user_signup",
            title="New User Signup",
            description=f"{user.full_name or user.email} joined the platform",
            user_email=user.email,
            user_name=user.full_name,
            timestamp=user.created_at,
            metadata={"role": user.role.value if user.role else "student"}
        ))

    # Get recent projects
    recent_projects = await db.execute(
        select(Project, User)
        .join(User, Project.user_id == User.id)
        .order_by(Project.created_at.desc())
        .limit(10)
    )
    for project, user in recent_projects:
        activities.append(ActivityItem(
            id=str(project.id),
            type="project_created",
            title="New Project Created",
            description=f"Project '{project.title}' was created",
            user_email=user.email,
            user_name=user.full_name,
            timestamp=project.created_at,
            metadata={"status": project.status.value if project.status else "draft"}
        ))

    # Get recent transactions
    recent_transactions = await db.execute(
        select(Transaction, User)
        .join(User, Transaction.user_id == User.id)
        .where(Transaction.status == "success")
        .order_by(Transaction.created_at.desc())
        .limit(10)
    )
    for txn, user in recent_transactions:
        activities.append(ActivityItem(
            id=str(txn.id),
            type="payment",
            title="Payment Received",
            description=f"Payment of ₹{txn.amount / 100:.2f} received",
            user_email=user.email,
            user_name=user.full_name,
            timestamp=txn.created_at,
            metadata={"amount": txn.amount, "currency": txn.currency}
        ))

    # Sort all activities by timestamp
    activities.sort(key=lambda x: x.timestamp, reverse=True)

    # Apply pagination
    paginated = activities[offset:offset + limit]

    return ActivityFeedResponse(
        items=paginated,
        total=len(activities)
    )
