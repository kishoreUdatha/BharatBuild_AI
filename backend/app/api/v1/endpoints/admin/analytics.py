"""
Admin Analytics endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import get_db
from app.models import User, Project, UsageLog, Transaction
from app.modules.auth.dependencies import get_current_admin
from app.schemas.admin import (
    UserGrowthResponse, TokenUsageResponse, ApiCallsResponse, TimeSeriesDataPoint
)

router = APIRouter()


@router.get("/user-growth", response_model=UserGrowthResponse)
async def get_user_growth(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get user growth analytics over time"""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # Get total users
    total_users = await db.scalar(select(func.count(User.id)))

    # Get users at start of period
    users_at_start = await db.scalar(
        select(func.count(User.id)).where(User.created_at < start_date)
    )

    # Calculate growth rate
    new_users = (total_users or 0) - (users_at_start or 0)
    if users_at_start and users_at_start > 0:
        growth_rate = (new_users / users_at_start) * 100
    else:
        growth_rate = 100.0 if new_users > 0 else 0.0

    # Daily data
    data = []
    for i in range(days):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        new_users_day = await db.scalar(
            select(func.count(User.id)).where(
                and_(
                    User.created_at >= day_start,
                    User.created_at < day_end
                )
            )
        )

        # Cumulative users up to this day
        cumulative = await db.scalar(
            select(func.count(User.id)).where(User.created_at < day_end)
        )

        data.append(TimeSeriesDataPoint(
            date=day_start.strftime("%Y-%m-%d"),
            value=float(cumulative or 0),
            label=f"+{new_users_day or 0}"
        ))

    data.reverse()

    return UserGrowthResponse(
        data=data,
        total_users=total_users or 0,
        growth_rate=round(growth_rate, 2)
    )


@router.get("/token-usage", response_model=TokenUsageResponse)
async def get_token_usage(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get token usage analytics"""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # Total tokens used
    total_tokens = await db.scalar(
        select(func.coalesce(func.sum(UsageLog.tokens_used), 0))
    )

    # Tokens by model
    tokens_by_model = {}
    for model in ["haiku", "sonnet", "opus"]:
        model_tokens = await db.scalar(
            select(func.coalesce(func.sum(UsageLog.tokens_used), 0)).where(
                UsageLog.model_used == model
            )
        )
        tokens_by_model[model] = model_tokens or 0

    # Daily usage
    daily_usage = []
    for i in range(days):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        day_tokens = await db.scalar(
            select(func.coalesce(func.sum(UsageLog.tokens_used), 0)).where(
                and_(
                    UsageLog.created_at >= day_start,
                    UsageLog.created_at < day_end
                )
            )
        )

        daily_usage.append(TimeSeriesDataPoint(
            date=day_start.strftime("%Y-%m-%d"),
            value=float(day_tokens or 0)
        ))

    daily_usage.reverse()

    # Top users by token usage
    top_users_query = (
        select(User.email, User.full_name, func.sum(UsageLog.tokens_used).label("total_tokens"))
        .join(UsageLog, User.id == UsageLog.user_id)
        .where(UsageLog.created_at >= start_date)
        .group_by(User.id)
        .order_by(func.sum(UsageLog.tokens_used).desc())
        .limit(10)
    )
    result = await db.execute(top_users_query)
    top_users = [
        {"email": row.email, "name": row.full_name, "tokens": int(row.total_tokens or 0)}
        for row in result
    ]

    return TokenUsageResponse(
        total_tokens=total_tokens or 0,
        tokens_by_model=tokens_by_model,
        daily_usage=daily_usage,
        top_users=top_users
    )


@router.get("/api-calls", response_model=ApiCallsResponse)
async def get_api_calls(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get API call analytics"""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # Total API calls
    total_calls = await db.scalar(select(func.count(UsageLog.id)))

    # Average response time
    avg_response_time = await db.scalar(
        select(func.avg(UsageLog.response_time))
    )

    # Calls by endpoint (top 10)
    endpoint_query = (
        select(UsageLog.endpoint, func.count(UsageLog.id).label("count"))
        .where(UsageLog.created_at >= start_date)
        .group_by(UsageLog.endpoint)
        .order_by(func.count(UsageLog.id).desc())
        .limit(10)
    )
    result = await db.execute(endpoint_query)
    calls_by_endpoint = {row.endpoint or "unknown": row.count for row in result}

    # Daily calls
    daily_calls = []
    for i in range(days):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        day_count = await db.scalar(
            select(func.count(UsageLog.id)).where(
                and_(
                    UsageLog.created_at >= day_start,
                    UsageLog.created_at < day_end
                )
            )
        )

        daily_calls.append(TimeSeriesDataPoint(
            date=day_start.strftime("%Y-%m-%d"),
            value=float(day_count or 0)
        ))

    daily_calls.reverse()

    return ApiCallsResponse(
        total_calls=total_calls or 0,
        calls_by_endpoint=calls_by_endpoint,
        daily_calls=daily_calls,
        average_response_time=float(avg_response_time or 0)
    )


@router.get("/model-usage")
async def get_model_usage(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get Claude model usage breakdown"""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    models = ["haiku", "sonnet", "opus"]
    usage = {}

    for model in models:
        # Call count
        call_count = await db.scalar(
            select(func.count(UsageLog.id)).where(
                and_(
                    UsageLog.model_used == model,
                    UsageLog.created_at >= start_date
                )
            )
        )

        # Token count
        token_count = await db.scalar(
            select(func.coalesce(func.sum(UsageLog.tokens_used), 0)).where(
                and_(
                    UsageLog.model_used == model,
                    UsageLog.created_at >= start_date
                )
            )
        )

        usage[model] = {
            "calls": call_count or 0,
            "tokens": token_count or 0
        }

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": now.isoformat(),
        "models": usage
    }


@router.get("/overview")
async def get_analytics_overview(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get a quick analytics overview"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start.replace(day=1)

    # User metrics
    total_users = await db.scalar(select(func.count(User.id)))
    new_users_today = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )
    new_users_this_week = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= week_start)
    )

    # Project metrics
    total_projects = await db.scalar(select(func.count(Project.id)))
    active_projects = await db.scalar(
        select(func.count(Project.id)).where(
            Project.last_activity >= now - timedelta(days=7)
        )
    )

    # API metrics
    api_calls_today = await db.scalar(
        select(func.count(UsageLog.id)).where(UsageLog.created_at >= today_start)
    )
    tokens_today = await db.scalar(
        select(func.coalesce(func.sum(UsageLog.tokens_used), 0)).where(
            UsageLog.created_at >= today_start
        )
    )

    # Revenue metrics
    revenue_today = await db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.status == "success",
                Transaction.created_at >= today_start
            )
        )
    )
    revenue_this_month = await db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.status == "success",
                Transaction.created_at >= month_start
            )
        )
    )

    return {
        "users": {
            "total": total_users or 0,
            "new_today": new_users_today or 0,
            "new_this_week": new_users_this_week or 0
        },
        "projects": {
            "total": total_projects or 0,
            "active": active_projects or 0
        },
        "api": {
            "calls_today": api_calls_today or 0,
            "tokens_today": tokens_today or 0
        },
        "revenue": {
            "today": float(revenue_today or 0) / 100,
            "this_month": float(revenue_this_month or 0) / 100,
            "currency": "INR"
        }
    }
