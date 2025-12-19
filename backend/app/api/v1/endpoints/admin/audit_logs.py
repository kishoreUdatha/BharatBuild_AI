"""
Admin Audit Logs endpoints.
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
from typing import Optional
import math
import csv
import io

from app.core.database import get_db
from app.models import User, AuditLog
from app.modules.auth.dependencies import get_current_admin
from app.schemas.admin import AuditLogResponse, AuditLogsResponse

router = APIRouter()


@router.get("", response_model=AuditLogsResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    admin_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List audit logs with filtering and pagination"""
    query = select(AuditLog, User).join(User, AuditLog.admin_id == User.id)

    conditions = []
    if action:
        conditions.append(AuditLog.action == action)
    if target_type:
        conditions.append(AuditLog.target_type == target_type)
    if admin_id:
        conditions.append(AuditLog.admin_id == admin_id)
    if start_date:
        conditions.append(AuditLog.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        conditions.append(AuditLog.created_at <= datetime.fromisoformat(end_date))
    if search:
        search_term = f"%{search}%"
        conditions.append(or_(
            AuditLog.action.ilike(search_term),
            AuditLog.target_type.ilike(search_term)
        ))

    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(
        select(AuditLog).where(and_(*conditions) if conditions else True).subquery()
    )
    total = await db.scalar(count_query)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for log, admin in rows:
        items.append(AuditLogResponse(
            id=str(log.id),
            admin_id=str(log.admin_id),
            admin_email=admin.email,
            admin_name=admin.full_name,
            action=log.action,
            target_type=log.target_type,
            target_id=str(log.target_id) if log.target_id else None,
            details=log.details,
            ip_address=log.ip_address,
            created_at=log.created_at
        ))

    return AuditLogsResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
        total_pages=math.ceil((total or 0) / page_size) if total and total > 0 else 1
    )


@router.get("/actions")
async def get_available_actions(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get list of distinct action types for filtering"""
    result = await db.execute(
        select(AuditLog.action).distinct().order_by(AuditLog.action)
    )
    actions = [row[0] for row in result.all() if row[0]]

    return {"actions": actions}


@router.get("/target-types")
async def get_target_types(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get list of distinct target types for filtering"""
    result = await db.execute(
        select(AuditLog.target_type).distinct().order_by(AuditLog.target_type)
    )
    types = [row[0] for row in result.all() if row[0]]

    return {"target_types": types}


@router.get("/stats")
async def get_audit_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get audit log statistics"""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # Total logs
    total_logs = await db.scalar(select(func.count(AuditLog.id)))

    # Logs in period
    logs_in_period = await db.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.created_at >= start_date)
    )

    # Logs by action
    action_query = (
        select(AuditLog.action, func.count(AuditLog.id).label("count"))
        .where(AuditLog.created_at >= start_date)
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
    )
    result = await db.execute(action_query)
    logs_by_action = {row.action: row.count for row in result}

    # Logs by admin
    admin_query = (
        select(User.email, func.count(AuditLog.id).label("count"))
        .join(AuditLog, User.id == AuditLog.admin_id)
        .where(AuditLog.created_at >= start_date)
        .group_by(User.id)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
    )
    result = await db.execute(admin_query)
    logs_by_admin = {row.email: row.count for row in result}

    # Daily activity
    daily_activity = []
    for i in range(min(days, 30)):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        count = await db.scalar(
            select(func.count(AuditLog.id)).where(
                and_(
                    AuditLog.created_at >= day_start,
                    AuditLog.created_at < day_end
                )
            )
        )
        daily_activity.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": count or 0
        })

    daily_activity.reverse()

    return {
        "total_logs": total_logs or 0,
        "logs_in_period": logs_in_period or 0,
        "period_days": days,
        "logs_by_action": logs_by_action,
        "logs_by_admin": logs_by_admin,
        "daily_activity": daily_activity
    }


@router.get("/export")
async def export_audit_logs(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Export audit logs to CSV"""
    query = select(AuditLog, User).join(User, AuditLog.admin_id == User.id)

    conditions = []
    if start_date:
        conditions.append(AuditLog.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        conditions.append(AuditLog.created_at <= datetime.fromisoformat(end_date))
    if action:
        conditions.append(AuditLog.action == action)
    if target_type:
        conditions.append(AuditLog.target_type == target_type)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(AuditLog.created_at.desc()).limit(10000)

    result = await db.execute(query)
    rows = result.all()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "ID", "Admin Email", "Admin Name", "Action", "Target Type",
        "Target ID", "IP Address", "Created At", "Details"
    ])

    # Data
    for log, admin in rows:
        writer.writerow([
            str(log.id),
            admin.email,
            admin.full_name or "",
            log.action,
            log.target_type,
            str(log.target_id) if log.target_id else "",
            log.ip_address or "",
            log.created_at.isoformat() if log.created_at else "",
            str(log.details) if log.details else ""
        ])

    output.seek(0)

    filename = f"audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
