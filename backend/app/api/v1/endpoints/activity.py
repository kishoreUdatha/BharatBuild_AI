"""
Activity Tracking API Endpoints
Provides endpoints for tracking and monitoring student activity
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_active_user
from app.models.user import User, UserRole
from app.models.activity_tracking import StudentActivity, EngagementAlert, ActivitySummary, ActivityType, ResourceType
from app.models.lab_assistance import LabEnrollment, LabCodingSubmission, Lab
from app.models.college_management import StudentSection, Section

router = APIRouter(tags=["Activity Tracking"])


# ==================== Request/Response Models ====================

class ActivityCreate(BaseModel):
    activity_type: str
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    duration_seconds: Optional[int] = None
    metadata: Optional[dict] = None


class ActivityResponse(BaseModel):
    id: str
    student_id: str
    activity_type: str
    resource_id: Optional[str]
    resource_type: Optional[str]
    duration_seconds: Optional[int]
    metadata: Optional[dict]
    created_at: datetime


class AlertResponse(BaseModel):
    id: str
    student_id: str
    student_name: Optional[str]
    alert_type: str
    severity: str
    message: str
    is_read: bool
    is_resolved: bool
    created_at: datetime


# ==================== Activity Tracking Endpoints ====================

@router.post("/track")
async def track_activity(
    activity: ActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Track a student activity"""
    from app.core.types import generate_uuid

    new_activity = StudentActivity(
        id=generate_uuid(),
        student_id=str(current_user.id),
        activity_type=ActivityType(activity.activity_type) if activity.activity_type in [e.value for e in ActivityType] else ActivityType.LAB_VIEW,
        resource_id=activity.resource_id,
        resource_type=ResourceType(activity.resource_type) if activity.resource_type in [e.value for e in ResourceType] else None,
        duration_seconds=activity.duration_seconds,
        activity_data=activity.metadata
    )

    db.add(new_activity)
    await db.commit()

    return {"status": "tracked", "activity_id": str(new_activity.id)}


@router.get("/student/{student_id}")
async def get_student_activity(
    student_id: str,
    days: int = 30,
    activity_type: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get activity log for a student (Faculty only)"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.ADMIN]:
        # Students can only see their own activity
        if str(current_user.id) != student_id:
            raise HTTPException(status_code=403, detail="Not authorized")

    start_date = datetime.utcnow() - timedelta(days=days)

    query = select(StudentActivity).where(
        StudentActivity.student_id == student_id,
        StudentActivity.created_at >= start_date
    )

    if activity_type:
        query = query.where(StudentActivity.activity_type == activity_type)

    query = query.order_by(StudentActivity.created_at.desc()).limit(limit)

    result = await db.execute(query)
    activities = result.scalars().all()

    return [
        {
            "id": str(a.id),
            "activity_type": a.activity_type.value if a.activity_type else "unknown",
            "resource_id": str(a.resource_id) if a.resource_id else None,
            "resource_type": a.resource_type.value if a.resource_type else None,
            "duration_seconds": a.duration_seconds,
            "metadata": a.activity_data,
            "created_at": a.created_at
        }
        for a in activities
    ]


@router.get("/student/{student_id}/summary")
async def get_student_activity_summary(
    student_id: str,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get activity summary for a student"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.ADMIN]:
        if str(current_user.id) != student_id:
            raise HTTPException(status_code=403, detail="Not authorized")

    start_date = datetime.utcnow() - timedelta(days=days)

    # Get activity counts by type
    result = await db.execute(
        select(
            StudentActivity.activity_type,
            func.count(StudentActivity.id).label('count'),
            func.sum(StudentActivity.duration_seconds).label('total_duration')
        ).where(
            StudentActivity.student_id == student_id,
            StudentActivity.created_at >= start_date
        ).group_by(StudentActivity.activity_type)
    )
    activity_stats = result.all()

    # Get daily activity for the period
    daily_result = await db.execute(
        select(
            func.date(StudentActivity.created_at).label('date'),
            func.count(StudentActivity.id).label('count')
        ).where(
            StudentActivity.student_id == student_id,
            StudentActivity.created_at >= start_date
        ).group_by(func.date(StudentActivity.created_at))
    )
    daily_activity = daily_result.all()

    # Get login count
    login_count = next((s.count for s in activity_stats if s.activity_type == ActivityType.LOGIN), 0)

    # Get submission count
    submissions_result = await db.execute(
        select(func.count(LabCodingSubmission.id)).where(
            LabCodingSubmission.user_id == student_id,
            LabCodingSubmission.submitted_at >= start_date
        )
    )
    submission_count = submissions_result.scalar() or 0

    # Calculate total time
    total_time = sum(s.total_duration or 0 for s in activity_stats)

    return {
        "student_id": student_id,
        "period_days": days,
        "total_activities": sum(s.count for s in activity_stats),
        "total_time_minutes": total_time // 60 if total_time else 0,
        "login_count": login_count,
        "submission_count": submission_count,
        "activity_by_type": {
            s.activity_type.value if s.activity_type else "unknown": {
                "count": s.count,
                "duration_minutes": (s.total_duration or 0) // 60
            }
            for s in activity_stats
        },
        "daily_activity": [
            {"date": str(d.date), "count": d.count}
            for d in daily_activity
        ],
        "avg_daily_activities": sum(d.count for d in daily_activity) / len(daily_activity) if daily_activity else 0
    }


@router.get("/student/{student_id}/code-history")
async def get_code_edit_history(
    student_id: str,
    problem_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get code edit history for a student"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.ADMIN]:
        if str(current_user.id) != student_id:
            raise HTTPException(status_code=403, detail="Not authorized")

    query = select(LabCodingSubmission).where(
        LabCodingSubmission.user_id == student_id
    )

    if problem_id:
        query = query.where(LabCodingSubmission.problem_id == problem_id)

    query = query.order_by(LabCodingSubmission.submitted_at.desc()).limit(limit)

    result = await db.execute(query)
    submissions = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "problem_id": str(s.problem_id),
            "language": s.language.value if s.language else "python",
            "status": s.status.value if s.status else "pending",
            "score": s.score,
            "tests_passed": s.tests_passed,
            "tests_total": s.tests_total,
            "execution_time_ms": s.execution_time_ms,
            "submitted_at": s.submitted_at
        }
        for s in submissions
    ]


@router.get("/class/{class_id}/engagement")
async def get_class_engagement(
    class_id: str,
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get engagement metrics for a class (Faculty only)"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can view class engagement")

    start_date = datetime.utcnow() - timedelta(days=days)

    # Get students in class
    students_result = await db.execute(
        select(StudentSection.user_id, User.full_name, User.email).join(
            User, StudentSection.user_id == User.id
        ).where(
            StudentSection.section_id == class_id,
            StudentSection.is_active == True
        )
    )
    students = students_result.all()

    engagement_data = []
    for student_id, name, email in students:
        # Get activity count
        activity_result = await db.execute(
            select(func.count(StudentActivity.id)).where(
                StudentActivity.student_id == str(student_id),
                StudentActivity.created_at >= start_date
            )
        )
        activity_count = activity_result.scalar() or 0

        # Get submission count
        submission_result = await db.execute(
            select(func.count(LabCodingSubmission.id)).where(
                LabCodingSubmission.user_id == str(student_id),
                LabCodingSubmission.submitted_at >= start_date
            )
        )
        submission_count = submission_result.scalar() or 0

        # Calculate engagement level
        if activity_count > 20:
            engagement_level = "high"
        elif activity_count > 5:
            engagement_level = "medium"
        else:
            engagement_level = "low"

        engagement_data.append({
            "student_id": str(student_id),
            "name": name or email,
            "activity_count": activity_count,
            "submission_count": submission_count,
            "engagement_level": engagement_level
        })

    # Calculate class averages
    total_activities = sum(s["activity_count"] for s in engagement_data)
    avg_activities = total_activities / len(engagement_data) if engagement_data else 0

    # Count engagement levels
    high_engagement = len([s for s in engagement_data if s["engagement_level"] == "high"])
    medium_engagement = len([s for s in engagement_data if s["engagement_level"] == "medium"])
    low_engagement = len([s for s in engagement_data if s["engagement_level"] == "low"])

    return {
        "class_id": class_id,
        "period_days": days,
        "total_students": len(engagement_data),
        "avg_activities_per_student": round(avg_activities, 1),
        "engagement_distribution": {
            "high": high_engagement,
            "medium": medium_engagement,
            "low": low_engagement
        },
        "students": sorted(engagement_data, key=lambda x: x["activity_count"], reverse=True)
    }


@router.get("/alerts")
async def get_engagement_alerts(
    is_resolved: bool = False,
    severity: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get engagement alerts for faculty"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can view alerts")

    query = select(EngagementAlert, User).join(
        User, EngagementAlert.student_id == User.id
    ).where(
        or_(
            EngagementAlert.faculty_id == str(current_user.id),
            EngagementAlert.faculty_id == None
        )
    )

    if not is_resolved:
        query = query.where(EngagementAlert.is_resolved == "false")
    if severity:
        query = query.where(EngagementAlert.severity == severity)

    query = query.order_by(EngagementAlert.created_at.desc()).limit(limit)

    result = await db.execute(query)
    alerts = result.all()

    return [
        {
            "id": str(alert.id),
            "student_id": str(alert.student_id),
            "student_name": user.full_name or user.email,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message,
            "is_read": alert.is_read == "true",
            "is_resolved": alert.is_resolved == "true",
            "created_at": alert.created_at
        }
        for alert, user in alerts
    ]


@router.put("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    resolution_notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Resolve an engagement alert"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can resolve alerts")

    result = await db.execute(
        select(EngagementAlert).where(EngagementAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_resolved = "true"
    alert.resolved_by = str(current_user.id)
    alert.resolved_at = datetime.utcnow()
    alert.resolution_notes = resolution_notes

    await db.commit()

    return {"status": "resolved", "alert_id": alert_id}


@router.get("/heatmap/{student_id}")
async def get_activity_heatmap(
    student_id: str,
    weeks: int = 12,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get activity heatmap data for a student (like GitHub contribution graph)"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.ADMIN]:
        if str(current_user.id) != student_id:
            raise HTTPException(status_code=403, detail="Not authorized")

    start_date = datetime.utcnow() - timedelta(weeks=weeks)

    # Get daily activity counts
    result = await db.execute(
        select(
            func.date(StudentActivity.created_at).label('date'),
            func.count(StudentActivity.id).label('count')
        ).where(
            StudentActivity.student_id == student_id,
            StudentActivity.created_at >= start_date
        ).group_by(func.date(StudentActivity.created_at))
    )
    daily_data = result.all()

    # Convert to dict for easy lookup
    activity_map = {str(d.date): d.count for d in daily_data}

    # Generate full date range
    heatmap = []
    current_date = start_date.date()
    end_date = datetime.utcnow().date()

    while current_date <= end_date:
        date_str = str(current_date)
        count = activity_map.get(date_str, 0)

        # Determine intensity level (0-4)
        if count == 0:
            level = 0
        elif count <= 3:
            level = 1
        elif count <= 6:
            level = 2
        elif count <= 10:
            level = 3
        else:
            level = 4

        heatmap.append({
            "date": date_str,
            "count": count,
            "level": level,
            "weekday": current_date.weekday()
        })

        current_date += timedelta(days=1)

    return {
        "student_id": student_id,
        "weeks": weeks,
        "total_activities": sum(d["count"] for d in heatmap),
        "active_days": len([d for d in heatmap if d["count"] > 0]),
        "heatmap": heatmap
    }
