"""
Admin Feedback Management endpoints.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
from typing import Optional
import math

from app.core.database import get_db
from app.models import User, AuditLog
from app.modules.auth.dependencies import get_current_admin
from app.schemas.admin import (
    AdminFeedbackResponse, AdminFeedbacksResponse,
    FeedbackStatusUpdate, FeedbackResponseCreate
)

router = APIRouter()


# Since there's no Feedback model in the codebase, we'll create a simple in-memory store
# In production, this should be a proper database table
# For now, we'll query the existing feedback table if it exists, or return empty

@router.get("", response_model=AdminFeedbacksResponse)
async def list_feedback(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    type: Optional[str] = None,
    user_id: Optional[str] = None,
    rating_min: Optional[int] = Query(None, ge=1, le=5),
    rating_max: Optional[int] = Query(None, ge=1, le=5),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List all user feedback with filtering and pagination"""
    # Check if feedback table exists
    try:
        from app.models import Feedback
        has_feedback_model = True
    except ImportError:
        has_feedback_model = False

    if not has_feedback_model:
        # Return empty response if no feedback model exists
        return AdminFeedbacksResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            total_pages=1
        )

    # If feedback model exists, query it
    query = select(Feedback, User).join(User, Feedback.user_id == User.id)

    conditions = []
    if status:
        conditions.append(Feedback.status == status)
    if type:
        conditions.append(Feedback.type == type)
    if user_id:
        conditions.append(Feedback.user_id == user_id)
    if rating_min:
        conditions.append(Feedback.rating >= rating_min)
    if rating_max:
        conditions.append(Feedback.rating <= rating_max)

    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(
        select(Feedback).where(and_(*conditions) if conditions else True).subquery()
    )
    total = await db.scalar(count_query)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Feedback.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for feedback, user in rows:
        items.append(AdminFeedbackResponse(
            id=str(feedback.id),
            user_id=str(feedback.user_id),
            user_email=user.email,
            user_name=user.full_name,
            type=feedback.type,
            rating=feedback.rating,
            message=feedback.message,
            status=feedback.status,
            admin_response=feedback.admin_response,
            responded_at=feedback.responded_at,
            created_at=feedback.created_at
        ))

    return AdminFeedbacksResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
        total_pages=math.ceil((total or 0) / page_size) if total and total > 0 else 1
    )


@router.get("/stats")
async def get_feedback_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get feedback statistics"""
    try:
        from app.models import Feedback
        has_feedback_model = True
    except ImportError:
        has_feedback_model = False

    if not has_feedback_model:
        return {
            "total_feedback": 0,
            "feedback_in_period": 0,
            "by_status": {},
            "by_type": {},
            "average_rating": 0,
            "pending_count": 0
        }

    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    total = await db.scalar(select(func.count(Feedback.id)))
    in_period = await db.scalar(
        select(func.count(Feedback.id)).where(Feedback.created_at >= start_date)
    )

    # By status
    status_query = (
        select(Feedback.status, func.count(Feedback.id))
        .group_by(Feedback.status)
    )
    result = await db.execute(status_query)
    by_status = {row[0]: row[1] for row in result}

    # By type
    type_query = (
        select(Feedback.type, func.count(Feedback.id))
        .group_by(Feedback.type)
    )
    result = await db.execute(type_query)
    by_type = {row[0]: row[1] for row in result}

    # Average rating
    avg_rating = await db.scalar(select(func.avg(Feedback.rating)))

    # Pending count
    pending = await db.scalar(
        select(func.count(Feedback.id)).where(Feedback.status == "pending")
    )

    return {
        "total_feedback": total or 0,
        "feedback_in_period": in_period or 0,
        "period_days": days,
        "by_status": by_status,
        "by_type": by_type,
        "average_rating": round(avg_rating, 2) if avg_rating else 0,
        "pending_count": pending or 0
    }


@router.patch("/{feedback_id}/status")
async def update_feedback_status(
    feedback_id: str,
    status_data: FeedbackStatusUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Update feedback status"""
    try:
        from app.models import Feedback
    except ImportError:
        raise HTTPException(status_code=501, detail="Feedback system not implemented")

    feedback = await db.get(Feedback, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    old_status = feedback.status
    feedback.status = status_data.status
    feedback.updated_at = datetime.utcnow()

    await db.commit()

    # Log action
    log = AuditLog(
        admin_id=str(current_admin.id),
        action="feedback_status_updated",
        target_type="feedback",
        target_id=feedback_id,
        details={"old_status": old_status, "new_status": status_data.status},
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(log)
    await db.commit()

    return {"message": f"Feedback status updated to {status_data.status}"}


@router.post("/{feedback_id}/respond")
async def respond_to_feedback(
    feedback_id: str,
    response_data: FeedbackResponseCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Respond to user feedback"""
    try:
        from app.models import Feedback
    except ImportError:
        raise HTTPException(status_code=501, detail="Feedback system not implemented")

    feedback = await db.get(Feedback, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    feedback.admin_response = response_data.response
    feedback.responded_at = datetime.utcnow()
    feedback.responded_by = current_admin.id
    feedback.status = "reviewed"
    feedback.updated_at = datetime.utcnow()

    await db.commit()

    # Log action
    log = AuditLog(
        admin_id=str(current_admin.id),
        action="feedback_responded",
        target_type="feedback",
        target_id=feedback_id,
        details={"response_length": len(response_data.response)},
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(log)
    await db.commit()

    return {"message": "Response submitted successfully"}


@router.get("/{feedback_id}")
async def get_feedback(
    feedback_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get a specific feedback item"""
    try:
        from app.models import Feedback
    except ImportError:
        raise HTTPException(status_code=501, detail="Feedback system not implemented")

    result = await db.execute(
        select(Feedback, User)
        .join(User, Feedback.user_id == User.id)
        .where(Feedback.id == feedback_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Feedback not found")

    feedback, user = row

    return AdminFeedbackResponse(
        id=str(feedback.id),
        user_id=str(feedback.user_id),
        user_email=user.email,
        user_name=user.full_name,
        type=feedback.type,
        rating=feedback.rating,
        message=feedback.message,
        status=feedback.status,
        admin_response=feedback.admin_response,
        responded_at=feedback.responded_at,
        created_at=feedback.created_at
    )
