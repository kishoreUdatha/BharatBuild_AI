"""
Admin Analytics endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, asc
from datetime import datetime, timedelta
from typing import Optional, List

from app.core.database import get_db
from app.models import User, Project, Transaction
from app.models.usage import TokenUsageLog
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
    """Get token usage analytics from TokenUsageLog (actual Claude API usage)"""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # Total tokens used (from TokenUsageLog - actual project generation)
    total_tokens = await db.scalar(
        select(func.coalesce(func.sum(TokenUsageLog.total_tokens), 0))
    )

    # Tokens by model (from TokenUsageLog)
    tokens_by_model = {}
    for model in ["haiku", "sonnet", "opus"]:
        # Match model names that contain the model type
        model_tokens = await db.scalar(
            select(func.coalesce(func.sum(TokenUsageLog.total_tokens), 0)).where(
                TokenUsageLog.model.ilike(f"%{model}%")
            )
        )
        tokens_by_model[model] = model_tokens or 0

    # Daily usage (from TokenUsageLog)
    daily_usage = []
    for i in range(days):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        day_tokens = await db.scalar(
            select(func.coalesce(func.sum(TokenUsageLog.total_tokens), 0)).where(
                and_(
                    TokenUsageLog.created_at >= day_start,
                    TokenUsageLog.created_at < day_end
                )
            )
        )

        daily_usage.append(TimeSeriesDataPoint(
            date=day_start.strftime("%Y-%m-%d"),
            value=float(day_tokens or 0)
        ))

    daily_usage.reverse()

    # Top users by token usage (from TokenUsageLog)
    top_users_query = (
        select(User.email, User.full_name, func.sum(TokenUsageLog.total_tokens).label("total_tokens"))
        .join(TokenUsageLog, User.id == TokenUsageLog.user_id)
        .where(TokenUsageLog.created_at >= start_date)
        .group_by(User.id)
        .order_by(func.sum(TokenUsageLog.total_tokens).desc())
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
    """Get API call analytics from TokenUsageLog (actual Claude API calls)"""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # Total API calls (from TokenUsageLog)
    total_calls = await db.scalar(select(func.count(TokenUsageLog.id)))

    # Average tokens per call (no response time in TokenUsageLog, use tokens instead)
    avg_tokens_per_call = await db.scalar(
        select(func.avg(TokenUsageLog.total_tokens))
    )

    # Calls by agent type (equivalent to endpoint for AI calls)
    agent_query = (
        select(TokenUsageLog.agent_type, func.count(TokenUsageLog.id).label("count"))
        .where(TokenUsageLog.created_at >= start_date)
        .group_by(TokenUsageLog.agent_type)
        .order_by(func.count(TokenUsageLog.id).desc())
        .limit(10)
    )
    result = await db.execute(agent_query)
    calls_by_endpoint = {
        (row.agent_type.value if row.agent_type else "unknown"): row.count
        for row in result
    }

    # Daily calls
    daily_calls = []
    for i in range(days):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        day_count = await db.scalar(
            select(func.count(TokenUsageLog.id)).where(
                and_(
                    TokenUsageLog.created_at >= day_start,
                    TokenUsageLog.created_at < day_end
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
        average_response_time=float(avg_tokens_per_call or 0)  # Use avg tokens as proxy
    )


@router.get("/model-usage")
async def get_model_usage(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get Claude model usage breakdown from TokenUsageLog (actual API calls)"""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    models = ["haiku", "sonnet", "opus"]
    usage = {}

    for model in models:
        # Call count (model name contains the model type, e.g. "claude-3-haiku-20240307")
        call_count = await db.scalar(
            select(func.count(TokenUsageLog.id)).where(
                and_(
                    TokenUsageLog.model.ilike(f"%{model}%"),
                    TokenUsageLog.created_at >= start_date
                )
            )
        )

        # Token count
        token_count = await db.scalar(
            select(func.coalesce(func.sum(TokenUsageLog.total_tokens), 0)).where(
                and_(
                    TokenUsageLog.model.ilike(f"%{model}%"),
                    TokenUsageLog.created_at >= start_date
                )
            )
        )

        # Cost in paise
        cost_paise = await db.scalar(
            select(func.coalesce(func.sum(TokenUsageLog.cost_paise), 0)).where(
                and_(
                    TokenUsageLog.model.ilike(f"%{model}%"),
                    TokenUsageLog.created_at >= start_date
                )
            )
        )

        usage[model] = {
            "calls": call_count or 0,
            "tokens": token_count or 0,
            "cost_inr": round((cost_paise or 0) / 100, 2),
            "cost_usd": round((cost_paise or 0) / 100 / 83, 4)
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
    """Get a quick analytics overview using TokenUsageLog for AI metrics"""
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

    # API metrics (from TokenUsageLog - actual Claude API calls)
    api_calls_today = await db.scalar(
        select(func.count(TokenUsageLog.id)).where(TokenUsageLog.created_at >= today_start)
    )
    tokens_today = await db.scalar(
        select(func.coalesce(func.sum(TokenUsageLog.total_tokens), 0)).where(
            TokenUsageLog.created_at >= today_start
        )
    )
    cost_today_paise = await db.scalar(
        select(func.coalesce(func.sum(TokenUsageLog.cost_paise), 0)).where(
            TokenUsageLog.created_at >= today_start
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
            "tokens_today": tokens_today or 0,
            "cost_today_inr": round((cost_today_paise or 0) / 100, 2),
            "cost_today_usd": round((cost_today_paise or 0) / 100 / 83, 4)
        },
        "revenue": {
            "today": float(revenue_today or 0) / 100,
            "this_month": float(revenue_this_month or 0) / 100,
            "currency": "INR"
        }
    }


@router.get("/project-costs")
async def get_project_costs(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search_user: Optional[str] = Query(None, description="Search by user email"),
    search_project: Optional[str] = Query(None, description="Search by project name"),
    start_date_filter: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date_filter: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    sort_by: str = Query("cost", description="Sort by: cost, tokens, date, name, user"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Get cost (in dollars) consumed for each project generation.

    Returns:
    - List of projects with their token usage and cost
    - Cost breakdown by agent type (planner, writer, fixer, etc.)
    - Total cost in USD and INR

    Supports:
    - Search by user email or project name
    - Date range filtering
    - Sorting by cost, tokens, date, name, or user
    """
    now = datetime.utcnow()

    # Handle date filtering
    if start_date_filter:
        try:
            start_date = datetime.strptime(start_date_filter, "%Y-%m-%d")
        except ValueError:
            start_date = now - timedelta(days=days)
    else:
        start_date = now - timedelta(days=days)

    if end_date_filter:
        try:
            end_date = datetime.strptime(end_date_filter, "%Y-%m-%d") + timedelta(days=1)  # Include full end day
        except ValueError:
            end_date = now
    else:
        end_date = now

    # Get project costs aggregated from TokenUsageLog
    project_costs_query = (
        select(
            TokenUsageLog.project_id,
            Project.name.label("project_name"),
            Project.created_at.label("project_created_at"),
            User.email.label("user_email"),
            User.full_name.label("user_name"),
            func.sum(TokenUsageLog.input_tokens).label("input_tokens"),
            func.sum(TokenUsageLog.output_tokens).label("output_tokens"),
            func.sum(TokenUsageLog.total_tokens).label("total_tokens"),
            func.sum(TokenUsageLog.cost_paise).label("total_cost_paise"),
            func.count(TokenUsageLog.id).label("api_calls"),
            func.min(TokenUsageLog.created_at).label("first_call"),
            func.max(TokenUsageLog.created_at).label("last_call")
        )
        .join(Project, TokenUsageLog.project_id == Project.id)
        .join(User, TokenUsageLog.user_id == User.id)
        .where(TokenUsageLog.created_at >= start_date)
        .where(TokenUsageLog.created_at <= end_date)
    )

    # Apply search filters
    if search_user:
        project_costs_query = project_costs_query.where(
            User.email.ilike(f"%{search_user}%")
        )

    if search_project:
        project_costs_query = project_costs_query.where(
            Project.name.ilike(f"%{search_project}%")
        )

    # Group by
    project_costs_query = project_costs_query.group_by(
        TokenUsageLog.project_id, Project.name, Project.created_at, User.email, User.full_name
    )

    # Dynamic sorting
    sort_column_map = {
        "cost": func.sum(TokenUsageLog.cost_paise),
        "tokens": func.sum(TokenUsageLog.total_tokens),
        "date": Project.created_at,
        "name": Project.name,
        "user": User.email,
        "calls": func.count(TokenUsageLog.id)
    }
    sort_column = sort_column_map.get(sort_by, func.sum(TokenUsageLog.cost_paise))

    if sort_order.lower() == "asc":
        project_costs_query = project_costs_query.order_by(asc(sort_column))
    else:
        project_costs_query = project_costs_query.order_by(desc(sort_column))

    # Apply offset and limit
    project_costs_query = project_costs_query.offset(offset).limit(limit)

    # Get total count for pagination (without limit/offset)
    count_query = (
        select(func.count(func.distinct(TokenUsageLog.project_id)))
        .join(Project, TokenUsageLog.project_id == Project.id)
        .join(User, TokenUsageLog.user_id == User.id)
        .where(TokenUsageLog.created_at >= start_date)
        .where(TokenUsageLog.created_at <= end_date)
    )
    if search_user:
        count_query = count_query.where(User.email.ilike(f"%{search_user}%"))
    if search_project:
        count_query = count_query.where(Project.name.ilike(f"%{search_project}%"))

    total_count_result = await db.execute(count_query)
    total_count = total_count_result.scalar() or 0

    result = await db.execute(project_costs_query)
    projects = []
    total_cost_paise = 0
    total_tokens = 0

    for row in result:
        cost_paise = row.total_cost_paise or 0
        cost_inr = cost_paise / 100  # Convert paise to rupees
        cost_usd = cost_inr / 83  # Approximate USD conversion

        total_cost_paise += cost_paise
        total_tokens += row.total_tokens or 0

        projects.append({
            "project_id": str(row.project_id),
            "project_name": row.project_name or "Unnamed Project",
            "user_email": row.user_email,
            "user_name": row.user_name,
            "input_tokens": row.input_tokens or 0,
            "output_tokens": row.output_tokens or 0,
            "total_tokens": row.total_tokens or 0,
            "api_calls": row.api_calls or 0,
            "cost_inr": round(cost_inr, 2),
            "cost_usd": round(cost_usd, 4),
            "created_at": row.project_created_at.isoformat() if row.project_created_at else None,
            "first_generation": row.first_call.isoformat() if row.first_call else None,
            "last_activity": row.last_call.isoformat() if row.last_call else None
        })

    # Get agent-wise breakdown
    agent_breakdown_query = (
        select(
            TokenUsageLog.agent_type,
            func.sum(TokenUsageLog.total_tokens).label("tokens"),
            func.sum(TokenUsageLog.cost_paise).label("cost_paise"),
            func.count(TokenUsageLog.id).label("calls")
        )
        .where(TokenUsageLog.created_at >= start_date)
        .group_by(TokenUsageLog.agent_type)
    )

    agent_result = await db.execute(agent_breakdown_query)
    agent_breakdown = {}
    for row in agent_result:
        agent_name = row.agent_type.value if row.agent_type else "unknown"
        cost_paise = row.cost_paise or 0
        agent_breakdown[agent_name] = {
            "tokens": row.tokens or 0,
            "cost_inr": round(cost_paise / 100, 2),
            "cost_usd": round(cost_paise / 100 / 83, 4),
            "api_calls": row.calls or 0
        }

    # Get model-wise breakdown
    model_breakdown_query = (
        select(
            TokenUsageLog.model,
            func.sum(TokenUsageLog.total_tokens).label("tokens"),
            func.sum(TokenUsageLog.cost_paise).label("cost_paise"),
            func.count(TokenUsageLog.id).label("calls")
        )
        .where(TokenUsageLog.created_at >= start_date)
        .group_by(TokenUsageLog.model)
    )

    model_result = await db.execute(model_breakdown_query)
    model_breakdown = {}
    for row in model_result:
        model_name = row.model or "unknown"
        cost_paise = row.cost_paise or 0
        model_breakdown[model_name] = {
            "tokens": row.tokens or 0,
            "cost_inr": round(cost_paise / 100, 2),
            "cost_usd": round(cost_paise / 100 / 83, 4),
            "api_calls": row.calls or 0
        }

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "filters": {
            "search_user": search_user,
            "search_project": search_project,
            "sort_by": sort_by,
            "sort_order": sort_order
        },
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(projects) < total_count
        },
        "summary": {
            "total_projects": total_count,
            "total_projects_in_page": len(projects),
            "total_tokens": total_tokens,
            "total_cost_inr": round(total_cost_paise / 100, 2),
            "total_cost_usd": round(total_cost_paise / 100 / 83, 4),
            "avg_cost_per_project": round((total_cost_paise / 100 / 83) / max(len(projects), 1), 4),
            "currency_rate": "1 USD = 83 INR (approximate)"
        },
        "projects": projects,
        "agent_breakdown": agent_breakdown,
        "model_breakdown": model_breakdown
    }


@router.get("/project-costs/{project_id}")
async def get_project_cost_details(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Get detailed cost breakdown for a specific project.

    Returns:
    - Token usage by agent type
    - Token usage by operation
    - Timeline of API calls
    - Total cost in USD and INR
    """
    from uuid import UUID

    try:
        project_uuid = UUID(project_id)
    except ValueError:
        return {"error": "Invalid project ID"}

    # Get project info
    project = await db.get(Project, project_uuid)
    if not project:
        return {"error": "Project not found"}

    # Get user info
    user = await db.get(User, project.user_id)

    # Get all token usage logs for this project
    logs_query = (
        select(TokenUsageLog)
        .where(TokenUsageLog.project_id == project_uuid)
        .order_by(TokenUsageLog.created_at)
    )

    result = await db.execute(logs_query)
    logs = result.scalars().all()

    # Aggregate by agent
    agent_usage = {}
    operation_usage = {}
    timeline = []
    total_input = 0
    total_output = 0
    total_cost_paise = 0

    for log in logs:
        agent = log.agent_type.value if log.agent_type else "unknown"
        operation = log.operation.value if log.operation else "unknown"

        # Agent aggregation
        if agent not in agent_usage:
            agent_usage[agent] = {"tokens": 0, "cost_paise": 0, "calls": 0}
        agent_usage[agent]["tokens"] += log.total_tokens or 0
        agent_usage[agent]["cost_paise"] += log.cost_paise or 0
        agent_usage[agent]["calls"] += 1

        # Operation aggregation
        if operation not in operation_usage:
            operation_usage[operation] = {"tokens": 0, "cost_paise": 0, "calls": 0}
        operation_usage[operation]["tokens"] += log.total_tokens or 0
        operation_usage[operation]["cost_paise"] += log.cost_paise or 0
        operation_usage[operation]["calls"] += 1

        # Timeline
        timeline.append({
            "timestamp": log.created_at.isoformat(),
            "agent": agent,
            "operation": operation,
            "model": log.model,
            "input_tokens": log.input_tokens,
            "output_tokens": log.output_tokens,
            "cost_inr": round((log.cost_paise or 0) / 100, 4),
            "file_path": log.file_path
        })

        total_input += log.input_tokens or 0
        total_output += log.output_tokens or 0
        total_cost_paise += log.cost_paise or 0

    # Convert agent_usage costs to INR/USD
    for agent in agent_usage:
        cost_paise = agent_usage[agent]["cost_paise"]
        agent_usage[agent]["cost_inr"] = round(cost_paise / 100, 2)
        agent_usage[agent]["cost_usd"] = round(cost_paise / 100 / 83, 4)
        del agent_usage[agent]["cost_paise"]

    # Convert operation_usage costs to INR/USD
    for op in operation_usage:
        cost_paise = operation_usage[op]["cost_paise"]
        operation_usage[op]["cost_inr"] = round(cost_paise / 100, 2)
        operation_usage[op]["cost_usd"] = round(cost_paise / 100 / 83, 4)
        del operation_usage[op]["cost_paise"]

    return {
        "project": {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "created_at": project.created_at.isoformat() if project.created_at else None
        },
        "user": {
            "email": user.email if user else None,
            "name": user.full_name if user else None
        },
        "summary": {
            "total_api_calls": len(logs),
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "cost_inr": round(total_cost_paise / 100, 2),
            "cost_usd": round(total_cost_paise / 100 / 83, 4)
        },
        "by_agent": agent_usage,
        "by_operation": operation_usage,
        "timeline": timeline
    }


@router.get("/project-costs/trends")
async def get_cost_trends(
    days: int = Query(30, ge=1, le=365),
    granularity: str = Query("daily", description="Granularity: daily, weekly, monthly"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Get cost trends over time for visualization.

    Returns daily/weekly/monthly cost aggregations for trend analysis.
    """
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # Get daily cost aggregations
    daily_query = (
        select(
            func.date(TokenUsageLog.created_at).label("date"),
            func.sum(TokenUsageLog.cost_paise).label("cost_paise"),
            func.sum(TokenUsageLog.total_tokens).label("tokens"),
            func.count(TokenUsageLog.id).label("api_calls"),
            func.count(func.distinct(TokenUsageLog.project_id)).label("projects")
        )
        .where(TokenUsageLog.created_at >= start_date)
        .group_by(func.date(TokenUsageLog.created_at))
        .order_by(func.date(TokenUsageLog.created_at))
    )

    result = await db.execute(daily_query)
    daily_data = []

    for row in result:
        cost_paise = row.cost_paise or 0
        daily_data.append({
            "date": row.date.isoformat() if row.date else None,
            "cost_usd": round(cost_paise / 100 / 83, 4),
            "cost_inr": round(cost_paise / 100, 2),
            "tokens": row.tokens or 0,
            "api_calls": row.api_calls or 0,
            "projects": row.projects or 0
        })

    # Calculate moving averages and trends
    costs = [d["cost_usd"] for d in daily_data]

    # 7-day moving average
    moving_avg_7 = []
    for i in range(len(costs)):
        start_idx = max(0, i - 6)
        window = costs[start_idx:i + 1]
        moving_avg_7.append(round(sum(window) / len(window), 4) if window else 0)

    # Add moving average to data
    for i, data in enumerate(daily_data):
        data["moving_avg_7d"] = moving_avg_7[i]

    # Calculate period-over-period comparison
    mid_point = len(daily_data) // 2
    first_half_cost = sum(d["cost_usd"] for d in daily_data[:mid_point]) if mid_point > 0 else 0
    second_half_cost = sum(d["cost_usd"] for d in daily_data[mid_point:]) if mid_point > 0 else 0

    growth_rate = 0
    if first_half_cost > 0:
        growth_rate = round(((second_half_cost - first_half_cost) / first_half_cost) * 100, 2)

    return {
        "period_days": days,
        "granularity": granularity,
        "start_date": start_date.isoformat(),
        "end_date": now.isoformat(),
        "trends": {
            "total_cost_usd": round(sum(costs), 4),
            "avg_daily_cost_usd": round(sum(costs) / max(len(costs), 1), 4),
            "max_daily_cost_usd": round(max(costs), 4) if costs else 0,
            "min_daily_cost_usd": round(min(costs), 4) if costs else 0,
            "growth_rate_percent": growth_rate,
            "first_half_cost_usd": round(first_half_cost, 4),
            "second_half_cost_usd": round(second_half_cost, 4)
        },
        "daily_data": daily_data
    }


@router.get("/project-costs/by-user")
async def get_costs_by_user(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Get aggregated costs by user for identifying top spenders.
    """
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    user_costs_query = (
        select(
            User.id.label("user_id"),
            User.email.label("user_email"),
            User.full_name.label("user_name"),
            func.count(func.distinct(TokenUsageLog.project_id)).label("project_count"),
            func.sum(TokenUsageLog.total_tokens).label("total_tokens"),
            func.sum(TokenUsageLog.cost_paise).label("total_cost_paise"),
            func.count(TokenUsageLog.id).label("api_calls"),
            func.min(TokenUsageLog.created_at).label("first_activity"),
            func.max(TokenUsageLog.created_at).label("last_activity")
        )
        .join(User, TokenUsageLog.user_id == User.id)
        .where(TokenUsageLog.created_at >= start_date)
        .group_by(User.id, User.email, User.full_name)
        .order_by(desc(func.sum(TokenUsageLog.cost_paise)))
        .limit(limit)
    )

    result = await db.execute(user_costs_query)
    users = []
    total_cost_paise = 0

    for row in result:
        cost_paise = row.total_cost_paise or 0
        total_cost_paise += cost_paise
        users.append({
            "user_id": str(row.user_id),
            "email": row.user_email,
            "name": row.user_name,
            "project_count": row.project_count or 0,
            "total_tokens": row.total_tokens or 0,
            "api_calls": row.api_calls or 0,
            "cost_inr": round(cost_paise / 100, 2),
            "cost_usd": round(cost_paise / 100 / 83, 4),
            "avg_cost_per_project": round((cost_paise / 100 / 83) / max(row.project_count, 1), 4),
            "first_activity": row.first_activity.isoformat() if row.first_activity else None,
            "last_activity": row.last_activity.isoformat() if row.last_activity else None
        })

    return {
        "period_days": days,
        "summary": {
            "total_users": len(users),
            "total_cost_usd": round(total_cost_paise / 100 / 83, 4),
            "avg_cost_per_user": round((total_cost_paise / 100 / 83) / max(len(users), 1), 4)
        },
        "users": users
    }


@router.get("/project-costs/statistics")
async def get_cost_statistics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Get advanced cost statistics including percentiles, median, and distributions.
    """
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # Get all project costs
    project_costs_query = (
        select(
            TokenUsageLog.project_id,
            func.sum(TokenUsageLog.cost_paise).label("cost_paise"),
            func.sum(TokenUsageLog.total_tokens).label("tokens")
        )
        .where(TokenUsageLog.created_at >= start_date)
        .group_by(TokenUsageLog.project_id)
    )

    result = await db.execute(project_costs_query)
    costs = []
    tokens = []

    for row in result:
        cost_usd = (row.cost_paise or 0) / 100 / 83
        costs.append(cost_usd)
        tokens.append(row.tokens or 0)

    if not costs:
        return {
            "period_days": days,
            "message": "No data available for this period"
        }

    # Sort for percentile calculations
    costs_sorted = sorted(costs)
    tokens_sorted = sorted(tokens)

    def percentile(data, p):
        if not data:
            return 0
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f
        return data[f] + (k - f) * (data[c] - data[f]) if c != f else data[f]

    # Cost distribution buckets
    cost_buckets = {
        "under_0.01": 0,
        "0.01_to_0.05": 0,
        "0.05_to_0.10": 0,
        "0.10_to_0.50": 0,
        "0.50_to_1.00": 0,
        "over_1.00": 0
    }

    for cost in costs:
        if cost < 0.01:
            cost_buckets["under_0.01"] += 1
        elif cost < 0.05:
            cost_buckets["0.01_to_0.05"] += 1
        elif cost < 0.10:
            cost_buckets["0.05_to_0.10"] += 1
        elif cost < 0.50:
            cost_buckets["0.10_to_0.50"] += 1
        elif cost < 1.00:
            cost_buckets["0.50_to_1.00"] += 1
        else:
            cost_buckets["over_1.00"] += 1

    # Calculate standard deviation
    mean_cost = sum(costs) / len(costs)
    variance = sum((x - mean_cost) ** 2 for x in costs) / len(costs)
    std_dev = variance ** 0.5

    # Identify outliers (beyond 2 standard deviations)
    outlier_threshold = mean_cost + (2 * std_dev)
    outliers_count = sum(1 for c in costs if c > outlier_threshold)

    return {
        "period_days": days,
        "project_count": len(costs),
        "cost_statistics": {
            "total_usd": round(sum(costs), 4),
            "mean_usd": round(mean_cost, 4),
            "median_usd": round(percentile(costs_sorted, 50), 4),
            "std_dev_usd": round(std_dev, 4),
            "min_usd": round(min(costs), 4),
            "max_usd": round(max(costs), 4),
            "percentile_25": round(percentile(costs_sorted, 25), 4),
            "percentile_75": round(percentile(costs_sorted, 75), 4),
            "percentile_90": round(percentile(costs_sorted, 90), 4),
            "percentile_95": round(percentile(costs_sorted, 95), 4),
            "percentile_99": round(percentile(costs_sorted, 99), 4)
        },
        "token_statistics": {
            "total": sum(tokens),
            "mean": round(sum(tokens) / len(tokens), 0),
            "median": round(percentile(tokens_sorted, 50), 0),
            "min": min(tokens),
            "max": max(tokens)
        },
        "cost_distribution": cost_buckets,
        "outliers": {
            "threshold_usd": round(outlier_threshold, 4),
            "count": outliers_count,
            "percentage": round((outliers_count / len(costs)) * 100, 2)
        },
        "cost_alerts": {
            "high_cost_threshold_usd": round(percentile(costs_sorted, 90), 4),
            "projects_above_threshold": sum(1 for c in costs if c > percentile(costs_sorted, 90))
        }
    }


@router.get("/project-costs/export")
async def export_project_costs(
    days: int = Query(30, ge=1, le=365),
    format: str = Query("csv", description="Export format: csv, json"),
    search_user: Optional[str] = Query(None),
    search_project: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Export project costs data for reporting.
    Returns data in CSV or JSON format for download.
    """
    from fastapi.responses import Response
    import csv
    import io

    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # Get all project costs
    query = (
        select(
            TokenUsageLog.project_id,
            Project.name.label("project_name"),
            Project.created_at.label("project_created_at"),
            User.email.label("user_email"),
            User.full_name.label("user_name"),
            func.sum(TokenUsageLog.input_tokens).label("input_tokens"),
            func.sum(TokenUsageLog.output_tokens).label("output_tokens"),
            func.sum(TokenUsageLog.total_tokens).label("total_tokens"),
            func.sum(TokenUsageLog.cost_paise).label("total_cost_paise"),
            func.count(TokenUsageLog.id).label("api_calls")
        )
        .join(Project, TokenUsageLog.project_id == Project.id)
        .join(User, TokenUsageLog.user_id == User.id)
        .where(TokenUsageLog.created_at >= start_date)
    )

    if search_user:
        query = query.where(User.email.ilike(f"%{search_user}%"))
    if search_project:
        query = query.where(Project.name.ilike(f"%{search_project}%"))

    query = query.group_by(
        TokenUsageLog.project_id, Project.name, Project.created_at, User.email, User.full_name
    ).order_by(desc(func.sum(TokenUsageLog.cost_paise)))

    result = await db.execute(query)

    rows = []
    for row in result:
        cost_paise = row.total_cost_paise or 0
        rows.append({
            "project_id": str(row.project_id),
            "project_name": row.project_name or "Unnamed",
            "user_email": row.user_email,
            "user_name": row.user_name or "",
            "created_at": row.project_created_at.isoformat() if row.project_created_at else "",
            "input_tokens": row.input_tokens or 0,
            "output_tokens": row.output_tokens or 0,
            "total_tokens": row.total_tokens or 0,
            "api_calls": row.api_calls or 0,
            "cost_inr": round(cost_paise / 100, 2),
            "cost_usd": round(cost_paise / 100 / 83, 4)
        })

    if format == "csv":
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=project_costs_{now.strftime('%Y%m%d')}.csv"
            }
        )
    else:
        return {
            "export_date": now.isoformat(),
            "period_days": days,
            "total_projects": len(rows),
            "data": rows
        }


@router.get("/project-costs/by-model")
async def get_costs_by_model(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Get cost breakdown by AI model to understand which models are most expensive.
    """
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    model_costs_query = (
        select(
            TokenUsageLog.model,
            func.sum(TokenUsageLog.input_tokens).label("input_tokens"),
            func.sum(TokenUsageLog.output_tokens).label("output_tokens"),
            func.sum(TokenUsageLog.total_tokens).label("total_tokens"),
            func.sum(TokenUsageLog.cost_paise).label("total_cost_paise"),
            func.count(TokenUsageLog.id).label("api_calls"),
            func.count(func.distinct(TokenUsageLog.project_id)).label("projects")
        )
        .where(TokenUsageLog.created_at >= start_date)
        .group_by(TokenUsageLog.model)
        .order_by(desc(func.sum(TokenUsageLog.cost_paise)))
    )

    result = await db.execute(model_costs_query)
    models = []
    total_cost_paise = 0
    total_tokens = 0

    for row in result:
        cost_paise = row.total_cost_paise or 0
        tokens = row.total_tokens or 0
        total_cost_paise += cost_paise
        total_tokens += tokens

        models.append({
            "model": row.model or "unknown",
            "input_tokens": row.input_tokens or 0,
            "output_tokens": row.output_tokens or 0,
            "total_tokens": tokens,
            "api_calls": row.api_calls or 0,
            "projects": row.projects or 0,
            "cost_inr": round(cost_paise / 100, 2),
            "cost_usd": round(cost_paise / 100 / 83, 4),
            "avg_tokens_per_call": round(tokens / max(row.api_calls, 1), 0),
            "avg_cost_per_call_usd": round((cost_paise / 100 / 83) / max(row.api_calls, 1), 6)
        })

    # Add percentage to each model
    for model in models:
        model["percentage_of_total_cost"] = round(
            (model["cost_usd"] / (total_cost_paise / 100 / 83)) * 100, 2
        ) if total_cost_paise > 0 else 0
        model["percentage_of_total_tokens"] = round(
            (model["total_tokens"] / total_tokens) * 100, 2
        ) if total_tokens > 0 else 0

    return {
        "period_days": days,
        "summary": {
            "total_cost_usd": round(total_cost_paise / 100 / 83, 4),
            "total_tokens": total_tokens,
            "model_count": len(models)
        },
        "models": models
    }


@router.get("/project-costs/alerts")
async def get_cost_alerts(
    days: int = Query(7, ge=1, le=30),
    cost_threshold_usd: float = Query(0.50, ge=0, description="Alert threshold in USD"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Get projects that exceed cost thresholds for monitoring.
    """
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # Convert USD threshold to paise
    threshold_paise = cost_threshold_usd * 83 * 100

    # Get high-cost projects
    high_cost_query = (
        select(
            TokenUsageLog.project_id,
            Project.name.label("project_name"),
            User.email.label("user_email"),
            func.sum(TokenUsageLog.total_tokens).label("total_tokens"),
            func.sum(TokenUsageLog.cost_paise).label("total_cost_paise"),
            func.count(TokenUsageLog.id).label("api_calls"),
            func.max(TokenUsageLog.created_at).label("last_activity")
        )
        .join(Project, TokenUsageLog.project_id == Project.id)
        .join(User, TokenUsageLog.user_id == User.id)
        .where(TokenUsageLog.created_at >= start_date)
        .group_by(TokenUsageLog.project_id, Project.name, User.email)
        .having(func.sum(TokenUsageLog.cost_paise) > threshold_paise)
        .order_by(desc(func.sum(TokenUsageLog.cost_paise)))
    )

    result = await db.execute(high_cost_query)
    alerts = []

    for row in result:
        cost_paise = row.total_cost_paise or 0
        cost_usd = cost_paise / 100 / 83

        # Determine severity
        if cost_usd >= cost_threshold_usd * 5:
            severity = "critical"
        elif cost_usd >= cost_threshold_usd * 2:
            severity = "high"
        else:
            severity = "warning"

        alerts.append({
            "project_id": str(row.project_id),
            "project_name": row.project_name or "Unnamed",
            "user_email": row.user_email,
            "total_tokens": row.total_tokens or 0,
            "api_calls": row.api_calls or 0,
            "cost_usd": round(cost_usd, 4),
            "cost_inr": round(cost_paise / 100, 2),
            "threshold_exceeded_by": round(cost_usd - cost_threshold_usd, 4),
            "severity": severity,
            "last_activity": row.last_activity.isoformat() if row.last_activity else None
        })

    # Group by severity
    severity_counts = {"critical": 0, "high": 0, "warning": 0}
    for alert in alerts:
        severity_counts[alert["severity"]] += 1

    return {
        "period_days": days,
        "threshold_usd": cost_threshold_usd,
        "summary": {
            "total_alerts": len(alerts),
            "critical": severity_counts["critical"],
            "high": severity_counts["high"],
            "warning": severity_counts["warning"]
        },
        "alerts": alerts
    }
