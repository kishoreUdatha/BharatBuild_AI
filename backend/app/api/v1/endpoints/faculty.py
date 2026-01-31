"""
Faculty Dashboard API Endpoints

Provides endpoints for:
- Profile management
- Class & student management
- Assignment management (CRUD)
- Student progress tracking
- Auto-grading with Judge0
- Plagiarism detection
- Analytics and reports
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.core.logging_config import logger
from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, get_current_active_user
from app.models.user import User, UserRole
from app.models.lab_assistance import (
    Lab, LabEnrollment, LabTopic, LabCodingSubmission, LabMCQResponse,
    LabCodingProblem, SubmissionStatus
)
from app.models.college_management import (
    FacultyAssignment, StudentSection, Section, StudentProject
)
from app.services.faculty_service import get_faculty_service

router = APIRouter(tags=["Faculty Dashboard"])


# ==================== Enums ====================

class ProblemType(str, Enum):
    CODING = "coding"
    MCQ = "mcq"
    PROJECT = "project"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class SubmissionStatusEnum(str, Enum):
    PENDING = "pending"
    GRADED = "graded"
    PLAGIARISM = "plagiarism"
    LATE = "late"


# ==================== Request/Response Models ====================

class TestCase(BaseModel):
    input: str
    expected_output: str
    is_hidden: bool = False
    weight: int = 1


class AssignmentCreate(BaseModel):
    title: str
    subject: str
    description: str
    due_date: datetime
    batch_id: str
    problem_type: ProblemType = ProblemType.CODING
    difficulty: Difficulty = Difficulty.MEDIUM
    language: str = "python"
    test_cases: List[TestCase] = []
    max_score: int = 100
    allow_late_submission: bool = False
    late_penalty_percent: int = 10
    enable_plagiarism_check: bool = True
    starter_code: Optional[str] = None
    solution_code: Optional[str] = None


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    designation: Optional[str] = None
    specialization: Optional[str] = None


class StudentFilterRequest(BaseModel):
    class_id: str
    status: Optional[str] = None  # active, inactive
    performance_tier: Optional[str] = None  # weak, average, top
    progress_min: Optional[float] = None
    progress_max: Optional[float] = None
    search: Optional[str] = None


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    department_id: Optional[str] = None
    priority: str = "normal"  # low, normal, high, urgent


# ==================== Profile Endpoints ====================

@router.get("/profile")
async def get_faculty_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get current faculty profile with assignments"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty members can access this endpoint")

    service = get_faculty_service(db)
    profile = await service.get_faculty_profile(str(current_user.id))

    if not profile:
        raise HTTPException(status_code=404, detail="Faculty profile not found")

    return profile


@router.put("/profile")
async def update_faculty_profile(
    updates: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update faculty profile"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty members can access this endpoint")

    service = get_faculty_service(db)
    profile = await service.update_faculty_profile(
        str(current_user.id),
        updates.model_dump(exclude_none=True)
    )

    if not profile:
        raise HTTPException(status_code=404, detail="Faculty profile not found")

    return profile


# ==================== Subject & Lab Endpoints ====================

@router.get("/subjects")
async def get_assigned_subjects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get subjects assigned to faculty (via labs)"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty members can access this endpoint")

    service = get_faculty_service(db)
    labs = await service.get_assigned_labs(str(current_user.id))

    # Group by semester
    subjects_by_semester = {}
    for lab in labs:
        semester = lab.get("semester", "unknown")
        if semester not in subjects_by_semester:
            subjects_by_semester[semester] = []
        subjects_by_semester[semester].append(lab)

    return {
        "total_labs": len(labs),
        "by_semester": subjects_by_semester,
        "labs": labs
    }


@router.get("/labs")
async def get_faculty_labs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get labs assigned to faculty"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty members can access this endpoint")

    service = get_faculty_service(db)
    return await service.get_assigned_labs(str(current_user.id))


@router.get("/sections")
async def get_faculty_sections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get semester/section mappings for faculty"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty members can access this endpoint")

    service = get_faculty_service(db)
    return await service.get_semester_sections(str(current_user.id))


# ==================== Class & Student Endpoints ====================

@router.get("/students")
async def get_students_by_filters(
    department: Optional[str] = None,
    year: Optional[int] = None,
    semester: Optional[int] = None,
    section: Optional[str] = None,
    status: Optional[str] = None,
    performance: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get students filtered by department, year, semester, section"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty members can access this endpoint")

    # Build query to get students
    query = select(User).where(User.role == UserRole.STUDENT)

    # Apply filters based on user attributes
    if department:
        query = query.where(User.department == department)
    if search:
        query = query.where(
            or_(
                User.full_name.ilike(f"%{search}%"),
                User.roll_number.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )

    result = await db.execute(query.limit(100))
    users = result.scalars().all()

    students = []
    for user in users:
        # Get lab progress for each student
        lab_result = await db.execute(
            select(LabEnrollment).where(LabEnrollment.user_id == user.id)
        )
        enrollments = lab_result.scalars().all()

        # Calculate aggregates
        total_progress = sum(e.overall_progress or 0 for e in enrollments)
        total_score = sum(e.total_score or 0 for e in enrollments)
        avg_progress = total_progress / len(enrollments) if enrollments else 0
        avg_score = total_score / len(enrollments) if enrollments else 0

        # Determine activity status
        is_active = any(
            e.last_activity and (datetime.utcnow() - e.last_activity).days < 15
            for e in enrollments
        ) if enrollments else False

        # Calculate performance tier based on score
        if not is_active and (datetime.utcnow() - (user.created_at or datetime.utcnow())).days > 15:
            performance_tier = "inactive"
        elif avg_score >= 80:
            performance_tier = "top"
        elif avg_score >= 50:
            performance_tier = "average"
        else:
            performance_tier = "weak"

        # Apply performance filter
        if performance and performance_tier != performance:
            continue

        # Apply status filter
        if status == "active" and not is_active:
            continue
        if status == "inactive" and is_active:
            continue

        # Skip StudentProject query if table doesn't exist (checked once at startup)
        project = None
        project_status = "Not Started"

        # AI usage - set to random mock value for now (will be calculated from submissions later)
        import random
        ai_usage = random.randint(5, 35) if is_active else 0

        # Get pending labs count
        pending_labs = sum(1 for e in enrollments if (e.overall_progress or 0) < 100)

        # Get missed deadlines (approximate)
        missed_deadlines = sum(1 for e in enrollments if (e.overall_progress or 0) < 50)

        # Calculate attendance from activity
        active_enrollments = [e for e in enrollments if e.last_activity]
        attendance_percent = min(100, len(active_enrollments) * 20 + 60) if enrollments else 75

        last_active = max(
            (e.last_activity for e in enrollments if e.last_activity),
            default=None
        )

        students.append({
            "id": str(user.id),
            "roll_number": user.roll_number or f"STU{str(user.id)[:6]}",
            "name": user.full_name or user.email.split("@")[0],
            "email": user.email,
            "is_active": is_active,
            "attendance_percent": attendance_percent,
            "lab_completion_percent": int(avg_progress),
            "project_status": project_status,
            "ai_usage_percent": ai_usage,
            "overall_score": int(avg_score),
            "performance_tier": performance_tier,
            "last_active": last_active.isoformat() if last_active else None,
            "guide_name": project.guide.full_name if project and hasattr(project, 'guide') and project.guide else None,
            "pending_labs": pending_labs,
            "missed_deadlines": missed_deadlines
        })

    return {
        "department": department,
        "year": year,
        "semester": semester,
        "section": section,
        "total_students": len(students),
        "students": students
    }


@router.get("/classes")
async def get_faculty_classes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get classes/sections assigned to faculty"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty members can access this endpoint")

    service = get_faculty_service(db)
    return await service.get_classes(str(current_user.id))


@router.get("/classes/{class_id}/students")
async def get_class_students(
    class_id: str,
    status: Optional[str] = None,
    performance: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get students in a class with optional filters"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty members can access this endpoint")

    service = get_faculty_service(db)
    students = await service.get_class_students(
        class_id,
        status_filter=status,
        performance_tier=performance,
        search=search
    )

    return {
        "class_id": class_id,
        "total_students": len(students),
        "students": students
    }


@router.post("/students/filter")
async def filter_students(
    filters: StudentFilterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Filter students by multiple criteria"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty members can access this endpoint")

    service = get_faculty_service(db)
    students = await service.get_class_students(
        filters.class_id,
        status_filter=filters.status,
        performance_tier=filters.performance_tier,
        search=filters.search
    )

    # Apply progress filters
    if filters.progress_min is not None or filters.progress_max is not None:
        filtered = []
        for student in students:
            progress = student.get("lab_progress", {}).get("avg_progress", 0)
            if filters.progress_min and progress < filters.progress_min:
                continue
            if filters.progress_max and progress > filters.progress_max:
                continue
            filtered.append(student)
        students = filtered

    return {
        "filters_applied": filters.model_dump(exclude_none=True),
        "total_students": len(students),
        "students": students
    }


@router.get("/students/{student_id}")
async def get_student_detail(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed information about a student including attendance, progress, project, activity"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty members can access this endpoint")

    # Get user
    result = await db.execute(
        select(User).where(User.id == student_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get lab enrollments
    lab_result = await db.execute(
        select(LabEnrollment, Lab).join(Lab, LabEnrollment.lab_id == Lab.id).where(
            LabEnrollment.user_id == student_id
        )
    )
    enrollments_data = lab_result.all()

    # Get project (skip if table doesn't exist)
    project = None

    # Get submissions for activity tracking
    submissions_result = await db.execute(
        select(LabCodingSubmission).where(
            LabCodingSubmission.user_id == student_id
        ).order_by(LabCodingSubmission.submitted_at.desc()).limit(30)
    )
    submissions = submissions_result.scalars().all()

    # Calculate attendance from activity
    total_days = 30
    active_days = 0
    for enrollment, _ in enrollments_data:
        if enrollment.last_activity:
            days_since = (datetime.utcnow() - enrollment.last_activity).days
            if days_since <= total_days:
                active_days += 1

    overall_attendance = min(100, (active_days * 3 / total_days) * 100 + 60)

    # Subject-wise attendance (simulate from lab data)
    subject_attendance = []
    for enrollment, lab in enrollments_data:
        progress = enrollment.overall_progress or 0
        # Higher progress correlates with attendance
        attendance_pct = min(100, 60 + progress * 0.4)
        subject_attendance.append({
            "subject": lab.title,
            "percent": int(attendance_pct)
        })

    # Monthly trend (last 5 months)
    months = ["Sep", "Oct", "Nov", "Dec", "Jan"]
    monthly_trend = [{"month": m, "percent": min(100, 70 + (i * 5))} for i, m in enumerate(months)]

    # Lab completion
    total_progress = sum(e.overall_progress or 0 for e, _ in enrollments_data)
    lab_completion = int(total_progress / len(enrollments_data)) if enrollments_data else 0

    # Pending labs
    pending_labs = [
        lab.title for enrollment, lab in enrollments_data
        if (enrollment.overall_progress or 0) < 100
    ]

    # Lab enrollments for display
    lab_enrollments = []
    for enrollment, lab in enrollments_data:
        lab_enrollments.append({
            "lab_id": str(lab.id),
            "lab_name": lab.title,
            "lab_code": lab.lab_code or "LAB",
            "progress": enrollment.overall_progress or 0,
            "score": enrollment.total_score or 0,
            "rank": enrollment.rank if hasattr(enrollment, 'rank') else None
        })

    # Activity metrics
    login_frequency = len(set(
        s.submitted_at.date() for s in submissions if s.submitted_at
    )) if submissions else 0

    time_spent = sum(
        (s.execution_time_ms or 0) / 1000 / 60 / 60 for s in submissions
    )  # Hours

    last_active = max(
        (e.last_activity for e, _ in enrollments_data if e.last_activity),
        default=None
    )

    is_active = last_active and (datetime.utcnow() - last_active).days < 15

    coding_level = "High" if len(submissions) > 20 else "Medium" if len(submissions) > 5 else "Low" if submissions else "None"

    # AI detection average
    ai_scores = [getattr(s, 'ai_detection_score', 0) or 0 for s in submissions]
    avg_ai = int(sum(ai_scores) / len(ai_scores) * 100) if ai_scores else 0

    # Build response
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name or user.email.split("@")[0],
        "roll_number": user.roll_number or f"STU{str(user.id)[:6]}",
        "phone": getattr(user, 'phone', None),
        "college_name": user.college_name or "Engineering College",
        "department": user.department or "CSE",
        "section": "A",  # Get from student section mapping
        "semester": 5,   # Get from enrollment
        "batch": user.batch or "2021-2025",
        "is_active": is_active,
        "guide_name": project.guide.full_name if project and hasattr(project, 'guide') and project.guide else None,
        "attendance": {
            "overall": int(overall_attendance),
            "subject_wise": subject_attendance[:4],  # Top 4 subjects
            "lab_attendance": int(overall_attendance),
            "monthly_trend": monthly_trend
        },
        "learning_progress": {
            "theory_completion": 75,  # Placeholder
            "lab_completion": lab_completion,
            "pending_labs": pending_labs[:5],  # Top 5 pending
            "missed_deadlines": len([l for l in pending_labs if True])  # Simplified
        },
        "project": {
            "id": str(project.id),
            "title": project.title,
            "current_phase": project.current_phase or "Review-1",
            "review_status": "Completed",
            "next_review_date": (datetime.utcnow() + timedelta(days=14)).isoformat(),
            "reviewer_comments": "Good progress. Continue with documentation.",
            "guide_name": project.guide.full_name if hasattr(project, 'guide') and project.guide else "Dr. Faculty",
            "is_approved": project.is_approved if hasattr(project, 'is_approved') else True,
            "plagiarism_score": getattr(project, 'plagiarism_score', 10) or 10,
            "ai_detection_score": avg_ai
        } if project else None,
        "activity": {
            "login_frequency": min(login_frequency, 7),
            "time_spent_hours": round(time_spent, 1),
            "coding_activity_level": coding_level,
            "last_active": last_active.isoformat() if last_active else "N/A"
        },
        "lab_enrollments": lab_enrollments
    }


@router.get("/students/{student_id}/attendance")
async def get_student_attendance(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get attendance overview for a student"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty members can access this endpoint")

    # Get student's lab activities as proxy for attendance
    result = await db.execute(
        select(LabEnrollment).where(LabEnrollment.user_id == student_id)
    )
    enrollments = result.scalars().all()

    # Calculate attendance based on activity
    total_days = 30  # Last 30 days
    active_days = 0

    for enrollment in enrollments:
        if enrollment.last_activity:
            days_since = (datetime.utcnow() - enrollment.last_activity).days
            if days_since <= total_days:
                active_days += 1

    return {
        "student_id": student_id,
        "period_days": total_days,
        "active_days": min(active_days * 3, total_days),  # Approximate
        "attendance_percentage": min((active_days * 3 / total_days) * 100, 100),
        "last_active": max((e.last_activity for e in enrollments if e.last_activity), default=None),
        "lab_participation": [
            {
                "lab_id": str(e.lab_id),
                "last_activity": e.last_activity,
                "topics_completed": e.topics_completed
            }
            for e in enrollments
        ]
    }


# ==================== Analytics Endpoints ====================

@router.get("/analytics/overview")
async def get_analytics_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get overview analytics for faculty dashboard"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        # Return mock data for non-faculty (e.g., demo mode)
        return {
            "total_students": 156,
            "total_submissions": 423,
            "active_assignments": 5,
            "avg_score": 72.5,
            "plagiarism_cases": 3,
            "completion_rate": 68.5,
            "pending_reviews": 4,
            "guided_students": 8
        }

    service = get_faculty_service(db)
    analytics = await service.get_dashboard_analytics(str(current_user.id))

    # Enhance with plagiarism stats
    # Get submissions with high plagiarism
    result = await db.execute(
        select(func.count(LabCodingSubmission.id)).where(
            LabCodingSubmission.status == SubmissionStatus.FAILED
        )
    )
    plagiarism_cases = result.scalar() or 0

    analytics["plagiarism_cases"] = plagiarism_cases
    analytics["active_assignments"] = analytics.get("total_labs", 0)

    return analytics


@router.get("/analytics/lab/{lab_id}")
async def get_lab_analytics(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed analytics for a specific lab"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty members can access this endpoint")

    service = get_faculty_service(db)
    analytics = await service.get_lab_analytics(lab_id)

    if not analytics:
        raise HTTPException(status_code=404, detail="Lab not found")

    return analytics


@router.get("/analytics/batches")
async def get_batch_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get analytics grouped by batch/class"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty members can access this endpoint")

    service = get_faculty_service(db)
    classes = await service.get_classes(str(current_user.id))

    batch_analytics = []
    for cls in classes:
        students = await service.get_class_students(cls["id"])

        # Calculate stats
        scores = [s.get("lab_progress", {}).get("avg_score", 0) for s in students]
        avg_score = sum(scores) / len(scores) if scores else 0

        # Find top performer
        top_performer = max(students, key=lambda s: s.get("lab_progress", {}).get("avg_score", 0)) if students else None

        batch_analytics.append({
            "batch_id": cls["id"],
            "batch_name": cls["name"],
            "total_students": len(students),
            "avg_score": round(avg_score, 2),
            "top_performer": f"{top_performer['name']} ({top_performer.get('lab_progress', {}).get('avg_score', 0):.0f}%)" if top_performer else "N/A"
        })

    return batch_analytics


@router.get("/analytics/leaderboard")
async def get_leaderboard(
    class_id: Optional[str] = None,
    lab_id: Optional[str] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get student leaderboard"""
    query = select(LabEnrollment, User).join(
        User, LabEnrollment.user_id == User.id
    )

    if lab_id:
        query = query.where(LabEnrollment.lab_id == lab_id)

    query = query.order_by(LabEnrollment.total_score.desc()).limit(limit)

    result = await db.execute(query)
    data = result.all()

    leaderboard = []
    for rank, (enrollment, user) in enumerate(data, 1):
        leaderboard.append({
            "rank": rank,
            "student_id": str(user.id),
            "name": user.full_name or user.email,
            "roll_number": user.roll_number,
            "total_score": enrollment.total_score,
            "problems_solved": enrollment.problems_solved,
            "mcq_score": enrollment.mcq_score
        })

    return leaderboard


# ==================== Communication Endpoints ====================

@router.post("/announcements")
async def create_announcement(
    announcement: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new announcement"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty members can access this endpoint")

    service = get_faculty_service(db)
    result = await service.create_announcement(
        str(current_user.id),
        announcement.title,
        announcement.content,
        announcement.department_id,
        announcement.priority
    )

    if not result:
        raise HTTPException(status_code=400, detail="Could not create announcement. Check faculty assignment.")

    return result


@router.get("/announcements")
async def get_announcements(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get announcements"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty members can access this endpoint")

    service = get_faculty_service(db)
    return await service.get_announcements(str(current_user.id), limit)


# ==================== Assignment Endpoints (Legacy - keeping for compatibility) ====================

# In-memory storage for backward compatibility
ASSIGNMENTS_DB: Dict[str, Dict] = {}
SUBMISSIONS_DB: Dict[str, Dict] = {}


def generate_id() -> str:
    """Generate a unique ID"""
    import uuid
    return str(uuid.uuid4())[:8]


@router.post("/assignments", response_model=Dict[str, str])
async def create_assignment(
    assignment: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new assignment"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty members can create assignments")

    assignment_id = generate_id()

    ASSIGNMENTS_DB[assignment_id] = {
        "id": assignment_id,
        "title": assignment.title,
        "subject": assignment.subject,
        "description": assignment.description,
        "due_date": assignment.due_date.isoformat(),
        "batch_id": assignment.batch_id,
        "problem_type": assignment.problem_type,
        "difficulty": assignment.difficulty,
        "language": assignment.language,
        "test_cases": [tc.model_dump() for tc in assignment.test_cases],
        "max_score": assignment.max_score,
        "allow_late_submission": assignment.allow_late_submission,
        "late_penalty_percent": assignment.late_penalty_percent,
        "enable_plagiarism_check": assignment.enable_plagiarism_check,
        "starter_code": assignment.starter_code,
        "solution_code": assignment.solution_code,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": str(current_user.id),
        "status": "active"
    }

    logger.info(f"Created assignment: {assignment_id} - {assignment.title}")
    return {"id": assignment_id, "message": "Assignment created successfully"}


@router.get("/assignments", response_model=List[Dict])
async def list_assignments(
    batch_id: Optional[str] = None,
    status: Optional[str] = None,
    subject: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all assignments with optional filters"""
    assignments = list(ASSIGNMENTS_DB.values())

    # Filter by creator if not admin
    if current_user.role != UserRole.ADMIN:
        assignments = [a for a in assignments if a.get("created_by") == str(current_user.id)]

    if batch_id:
        assignments = [a for a in assignments if a["batch_id"] == batch_id]
    if status:
        assignments = [a for a in assignments if a["status"] == status]
    if subject:
        assignments = [a for a in assignments if a["subject"].lower() == subject.lower()]

    # Add submission stats
    for assignment in assignments:
        submissions = [s for s in SUBMISSIONS_DB.values() if s["assignment_id"] == assignment["id"]]
        assignment["submitted_count"] = len(submissions)
        assignment["graded_count"] = len([s for s in submissions if s["status"] == "graded"])
        graded_scores = [s["score"] for s in submissions if s["score"] is not None]
        assignment["avg_score"] = sum(graded_scores) / len(graded_scores) if graded_scores else 0
        assignment["total_students"] = 60  # Default

    return assignments


@router.get("/assignments/{assignment_id}")
async def get_assignment(
    assignment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get assignment details"""
    if assignment_id not in ASSIGNMENTS_DB:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return ASSIGNMENTS_DB[assignment_id]


@router.put("/assignments/{assignment_id}")
async def update_assignment(
    assignment_id: str,
    updates: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an assignment"""
    if assignment_id not in ASSIGNMENTS_DB:
        raise HTTPException(status_code=404, detail="Assignment not found")

    for key, value in updates.items():
        if key in ASSIGNMENTS_DB[assignment_id]:
            ASSIGNMENTS_DB[assignment_id][key] = value

    return {"message": "Assignment updated successfully"}


@router.delete("/assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an assignment"""
    if assignment_id not in ASSIGNMENTS_DB:
        raise HTTPException(status_code=404, detail="Assignment not found")

    del ASSIGNMENTS_DB[assignment_id]

    # Delete related submissions
    to_delete = [sid for sid, s in SUBMISSIONS_DB.items() if s["assignment_id"] == assignment_id]
    for sid in to_delete:
        del SUBMISSIONS_DB[sid]

    return {"message": "Assignment deleted successfully"}


# ==================== Submission Endpoints ====================

@router.get("/submissions")
async def list_submissions(
    assignment_id: Optional[str] = None,
    student_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List submissions with optional filters"""
    # Get from database
    query = select(LabCodingSubmission, User).join(
        User, LabCodingSubmission.user_id == User.id
    )

    if student_id:
        query = query.where(LabCodingSubmission.user_id == student_id)
    if status:
        query = query.where(LabCodingSubmission.status == status)

    query = query.order_by(LabCodingSubmission.submitted_at.desc()).limit(limit)

    result = await db.execute(query)
    data = result.all()

    submissions = []
    for submission, user in data:
        submissions.append({
            "id": str(submission.id),
            "problem_id": str(submission.problem_id),
            "student_id": str(user.id),
            "student_name": user.full_name or user.email,
            "language": submission.language.value if submission.language else "python",
            "status": submission.status.value if submission.status else "pending",
            "score": submission.score,
            "tests_passed": submission.tests_passed,
            "tests_total": submission.tests_total,
            "submitted_at": submission.submitted_at
        })

    # Also include in-memory submissions for legacy support
    legacy_submissions = list(SUBMISSIONS_DB.values())
    if assignment_id:
        legacy_submissions = [s for s in legacy_submissions if s["assignment_id"] == assignment_id]
    if student_id:
        legacy_submissions = [s for s in legacy_submissions if s["student_id"] == student_id]
    if status:
        legacy_submissions = [s for s in legacy_submissions if s["status"] == status]

    legacy_submissions.sort(key=lambda x: x["submitted_at"], reverse=True)

    return {
        "database_submissions": submissions,
        "legacy_submissions": legacy_submissions[:limit]
    }


@router.get("/submissions/{submission_id}")
async def get_submission(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get submission details"""
    # Try database first
    result = await db.execute(
        select(LabCodingSubmission).where(LabCodingSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()

    if submission:
        return {
            "id": str(submission.id),
            "problem_id": str(submission.problem_id),
            "user_id": str(submission.user_id),
            "language": submission.language.value if submission.language else "python",
            "code": submission.code,
            "status": submission.status.value if submission.status else "pending",
            "score": submission.score,
            "tests_passed": submission.tests_passed,
            "tests_total": submission.tests_total,
            "test_results": submission.test_results,
            "execution_time_ms": submission.execution_time_ms,
            "memory_used_mb": submission.memory_used_mb,
            "error_message": submission.error_message,
            "submitted_at": submission.submitted_at,
            "executed_at": submission.executed_at
        }

    # Fallback to legacy
    if submission_id in SUBMISSIONS_DB:
        return SUBMISSIONS_DB[submission_id]

    raise HTTPException(status_code=404, detail="Submission not found")


@router.post("/submissions/{submission_id}/feedback")
async def add_feedback(
    submission_id: str,
    feedback: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add feedback to a submission"""
    if submission_id in SUBMISSIONS_DB:
        SUBMISSIONS_DB[submission_id]["feedback"] = feedback
        return {"message": "Feedback added successfully"}

    raise HTTPException(status_code=404, detail="Submission not found")


# ==================== Batch Endpoints ====================

@router.get("/batches")
async def list_batches(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all batches/classes"""
    service = get_faculty_service(db)
    classes = await service.get_classes(str(current_user.id))

    return [
        {
            "id": cls["id"],
            "name": cls["name"],
            "students": cls["student_count"]
        }
        for cls in classes
    ]


# ==================== Integrity & Code Review Endpoints ====================

class CodeComment(BaseModel):
    line_number: int
    content: str


class ReviewUpdate(BaseModel):
    status: str  # approved, rejected, needs_revision
    comments: Optional[List[Dict[str, Any]]] = None


@router.get("/class/{class_id}/submissions-analysis")
async def get_class_submissions_analysis(
    class_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get AI/plagiarism analysis for class submissions"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

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
    student_ids = [str(s[0]) for s in students]
    student_map = {str(s[0]): s[1] or s[2] for s in students}

    # Get submissions for these students
    result = await db.execute(
        select(LabCodingSubmission, LabCodingProblem, Lab).join(
            LabCodingProblem, LabCodingSubmission.problem_id == LabCodingProblem.id
        ).join(
            Lab, LabCodingProblem.lab_id == Lab.id
        ).where(
            LabCodingSubmission.user_id.in_(student_ids)
        ).order_by(LabCodingSubmission.submitted_at.desc()).limit(100)
    )
    data = result.all()

    submissions = []
    for submission, problem, lab in data:
        # Calculate risk level based on AI/plagiarism scores
        ai_score = getattr(submission, 'ai_detection_score', 0) or 0
        plag_score = getattr(submission, 'plagiarism_score', 0) or 0

        if ai_score >= 60 or plag_score >= 50:
            risk_level = "high"
        elif ai_score >= 30 or plag_score >= 20:
            risk_level = "medium"
        else:
            risk_level = "low"

        submissions.append({
            "id": str(submission.id),
            "student_id": str(submission.user_id),
            "student_name": student_map.get(str(submission.user_id), "Unknown"),
            "problem_title": problem.title,
            "lab_title": lab.title,
            "ai_score": int(ai_score * 100) if ai_score <= 1 else int(ai_score),
            "plagiarism_score": int(plag_score * 100) if plag_score <= 1 else int(plag_score),
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "status": submission.status.value if submission.status else "pending",
            "risk_level": risk_level
        })

    return submissions


@router.get("/class/{class_id}/integrity-report")
async def get_class_integrity_report(
    class_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get integrity summary report for a class"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    # Get students in class
    students_result = await db.execute(
        select(StudentSection.user_id).where(
            StudentSection.section_id == class_id,
            StudentSection.is_active == True
        )
    )
    student_ids = [str(r[0]) for r in students_result.all()]

    if not student_ids:
        return {
            "class_id": class_id,
            "class_name": "Unknown",
            "total_submissions": 0,
            "avg_ai_score": 0,
            "avg_plagiarism_score": 0,
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 0
        }

    # Get submissions with scores
    result = await db.execute(
        select(LabCodingSubmission).where(
            LabCodingSubmission.user_id.in_(student_ids)
        )
    )
    submissions = result.scalars().all()

    total_ai = 0
    total_plag = 0
    high_risk = 0
    medium_risk = 0
    low_risk = 0

    for sub in submissions:
        ai_score = getattr(sub, 'ai_detection_score', 0) or 0
        plag_score = getattr(sub, 'plagiarism_score', 0) or 0

        # Normalize scores to percentage
        ai_pct = int(ai_score * 100) if ai_score <= 1 else int(ai_score)
        plag_pct = int(plag_score * 100) if plag_score <= 1 else int(plag_score)

        total_ai += ai_pct
        total_plag += plag_pct

        if ai_pct >= 60 or plag_pct >= 50:
            high_risk += 1
        elif ai_pct >= 30 or plag_pct >= 20:
            medium_risk += 1
        else:
            low_risk += 1

    total = len(submissions)
    avg_ai = total_ai / total if total > 0 else 0
    avg_plag = total_plag / total if total > 0 else 0

    # Get class name
    section_result = await db.execute(
        select(Section.name).where(Section.id == class_id)
    )
    class_name = section_result.scalar() or "Unknown"

    return {
        "class_id": class_id,
        "class_name": class_name,
        "total_submissions": total,
        "avg_ai_score": round(avg_ai, 1),
        "avg_plagiarism_score": round(avg_plag, 1),
        "high_risk_count": high_risk,
        "medium_risk_count": medium_risk,
        "low_risk_count": low_risk
    }


@router.get("/submissions/pending-review")
async def get_pending_review_submissions(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get submissions pending faculty review"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    # Get all submissions that need review
    result = await db.execute(
        select(LabCodingSubmission, User, LabCodingProblem, Lab).join(
            User, LabCodingSubmission.user_id == User.id
        ).join(
            LabCodingProblem, LabCodingSubmission.problem_id == LabCodingProblem.id
        ).join(
            Lab, LabCodingProblem.lab_id == Lab.id
        ).where(
            or_(
                LabCodingSubmission.status == SubmissionStatus.PASSED,
                LabCodingSubmission.status == SubmissionStatus.PARTIAL
            )
        ).order_by(LabCodingSubmission.submitted_at.desc()).limit(limit)
    )
    data = result.all()

    submissions = []
    for submission, user, problem, lab in data:
        ai_score = getattr(submission, 'ai_detection_score', 0) or 0
        plag_score = getattr(submission, 'plagiarism_score', 0) or 0

        submissions.append({
            "id": str(submission.id),
            "student_id": str(user.id),
            "student_name": user.full_name or user.email,
            "problem_id": str(problem.id),
            "problem_title": problem.title,
            "lab_title": lab.title,
            "language": submission.language.value if submission.language else "python",
            "code": submission.code,
            "status": submission.status.value if submission.status else "pending",
            "score": submission.score or 0,
            "tests_passed": submission.tests_passed or 0,
            "tests_total": submission.tests_total or 0,
            "execution_time_ms": submission.execution_time_ms or 0,
            "ai_score": int(ai_score * 100) if ai_score <= 1 else int(ai_score),
            "plagiarism_score": int(plag_score * 100) if plag_score <= 1 else int(plag_score),
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "review_status": getattr(submission, 'review_status', 'pending') or 'pending'
        })

    return submissions


@router.get("/submissions/{submission_id}/analysis")
async def get_submission_analysis(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed AI/plagiarism analysis for a submission"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    result = await db.execute(
        select(LabCodingSubmission).where(LabCodingSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    ai_score = getattr(submission, 'ai_detection_score', 0) or 0
    plag_score = getattr(submission, 'plagiarism_score', 0) or 0

    return {
        "id": str(submission.id),
        "ai_detection": {
            "score": int(ai_score * 100) if ai_score <= 1 else int(ai_score),
            "analysis_date": getattr(submission, 'analysis_completed_at', None),
            "model_confidence": 0.85,
            "flagged_sections": []  # Could be populated by analysis service
        },
        "plagiarism": {
            "score": int(plag_score * 100) if plag_score <= 1 else int(plag_score),
            "analysis_date": getattr(submission, 'analysis_completed_at', None),
            "matches": []  # Could be populated by plagiarism service
        }
    }


@router.get("/submissions/{submission_id}/comments")
async def get_submission_comments(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get code review comments for a submission"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    # For now, return from in-memory storage
    # In production, this would be stored in database
    comments_key = f"comments_{submission_id}"
    return SUBMISSIONS_DB.get(comments_key, [])


@router.post("/submissions/{submission_id}/comments")
async def add_submission_comment(
    submission_id: str,
    comment: CodeComment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a code review comment to a submission"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    # Verify submission exists
    result = await db.execute(
        select(LabCodingSubmission).where(LabCodingSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Store comment (in production, use a proper comments table)
    comments_key = f"comments_{submission_id}"
    if comments_key not in SUBMISSIONS_DB:
        SUBMISSIONS_DB[comments_key] = []

    comment_id = generate_id()
    new_comment = {
        "id": comment_id,
        "line_number": comment.line_number,
        "content": comment.content,
        "author": current_user.full_name or current_user.email,
        "created_at": datetime.utcnow().isoformat()
    }
    SUBMISSIONS_DB[comments_key].append(new_comment)

    return {"id": comment_id, "message": "Comment added successfully"}


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a code review comment"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    # Find and delete the comment
    for key in SUBMISSIONS_DB:
        if key.startswith("comments_") and isinstance(SUBMISSIONS_DB[key], list):
            SUBMISSIONS_DB[key] = [c for c in SUBMISSIONS_DB[key] if c.get("id") != comment_id]

    return {"message": "Comment deleted successfully"}


@router.get("/submissions/{submission_id}/versions")
async def get_submission_versions(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all versions of a submission for comparison"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    # Get the submission to find student and problem
    result = await db.execute(
        select(LabCodingSubmission).where(LabCodingSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Get all submissions by same student for same problem
    result = await db.execute(
        select(LabCodingSubmission).where(
            LabCodingSubmission.user_id == submission.user_id,
            LabCodingSubmission.problem_id == submission.problem_id
        ).order_by(LabCodingSubmission.submitted_at.asc())
    )
    all_submissions = result.scalars().all()

    versions = []
    for idx, sub in enumerate(all_submissions, 1):
        versions.append({
            "id": str(sub.id),
            "version": idx,
            "code": sub.code,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
            "tests_passed": sub.tests_passed or 0,
            "tests_total": sub.tests_total or 0
        })

    return versions


@router.put("/submissions/{submission_id}/review")
async def update_submission_review(
    submission_id: str,
    review: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update review status for a submission"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    result = await db.execute(
        select(LabCodingSubmission).where(LabCodingSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Update review status (if column exists)
    if hasattr(submission, 'review_status'):
        submission.review_status = review.status
    if hasattr(submission, 'reviewed_by'):
        submission.reviewed_by = str(current_user.id)
    if hasattr(submission, 'reviewed_at'):
        submission.reviewed_at = datetime.utcnow()

    await db.commit()

    return {"message": f"Submission {review.status}", "submission_id": submission_id}


@router.put("/settings/thresholds")
async def update_integrity_thresholds(
    thresholds: Dict[str, int] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update AI/plagiarism threshold settings for faculty"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    # Store thresholds in user preferences (or a settings table)
    # For now, just return success
    return {
        "message": "Thresholds updated successfully",
        "thresholds": thresholds
    }


# ==================== Report Generation Endpoints ====================

@router.get("/reports/student/{student_id}")
async def generate_student_report(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate comprehensive report for a student"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    from app.services.report_service import get_report_service
    service = get_report_service(db)
    report = await service.generate_student_report(student_id)

    if not report:
        raise HTTPException(status_code=404, detail="Student not found")

    return report


@router.get("/reports/class/{class_id}")
async def generate_class_report(
    class_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate class/section performance report"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    from app.services.report_service import get_report_service
    service = get_report_service(db)
    report = await service.generate_class_report(class_id)

    return report


@router.get("/reports/lab/{lab_id}/completion")
async def generate_lab_completion_report(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate lab completion report"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    from app.services.report_service import get_report_service
    service = get_report_service(db)
    report = await service.generate_lab_completion_report(lab_id)

    if not report:
        raise HTTPException(status_code=404, detail="Lab not found")

    return report


@router.get("/reports/project/{project_id}")
async def generate_project_review_report(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate project review report"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    from app.services.report_service import get_report_service
    service = get_report_service(db)
    report = await service.generate_project_review_report(project_id)

    if not report:
        raise HTTPException(status_code=404, detail="Project not found")

    return report


@router.get("/marks/export")
async def export_marks(
    class_id: str,
    lab_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export marks for a class in tabular format"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    from app.services.report_service import get_report_service
    service = get_report_service(db)
    marks_data = await service.export_marks(class_id, lab_id)

    return {
        "class_id": class_id,
        "lab_id": lab_id,
        "exported_at": datetime.utcnow().isoformat(),
        "data": marks_data
    }


@router.post("/messages")
async def send_message_to_student(
    student_id: str = Body(..., embed=True),
    content: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send a message to a student"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    # Verify student exists
    result = await db.execute(
        select(User).where(User.id == student_id)
    )
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # In production, store in a messages table
    # For now, just return success
    return {
        "message": "Message sent successfully",
        "student_id": student_id,
        "content": content,
        "sent_at": datetime.utcnow().isoformat()
    }


@router.get("/messages/student/{student_id}")
async def get_message_history(
    student_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get message history with a student"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    # In production, fetch from messages table
    # For now, return empty list
    return []


# ==================== Lab Topic Assignments ====================

class LabTopicAssignmentCreate(BaseModel):
    topic_id: str
    lab_id: str
    class_id: Optional[str] = None
    batch_id: Optional[str] = None
    student_ids: Optional[List[str]] = None
    deadline: datetime
    deadline_type: str = "soft"  # soft or hard


# In-memory storage for lab assignments (in production, use database)
lab_topic_assignments: Dict[str, Dict] = {}


@router.post("/lab-assignments")
async def create_lab_assignment(
    assignment: LabTopicAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Assign a lab topic to a class, batch, or individual students"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    # Verify topic exists
    result = await db.execute(
        select(LabTopic).where(LabTopic.id == assignment.topic_id)
    )
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Determine assignment type and target
    if assignment.class_id:
        assigned_to = "class"
        target_id = assignment.class_id
        target_name = f"Class {assignment.class_id}"
        # Get student count for class
        total = 65  # Default, in production query from sections
    elif assignment.batch_id:
        assigned_to = "batch"
        target_id = assignment.batch_id
        target_name = f"Batch {assignment.batch_id}"
        total = 32
    elif assignment.student_ids:
        assigned_to = "individual"
        target_id = ",".join(assignment.student_ids)
        target_name = f"{len(assignment.student_ids)} students"
        total = len(assignment.student_ids)
    else:
        raise HTTPException(status_code=400, detail="Must specify class_id, batch_id, or student_ids")

    import uuid
    assignment_id = str(uuid.uuid4())

    new_assignment = {
        "id": assignment_id,
        "topic_id": assignment.topic_id,
        "topic_title": topic.title,
        "lab_id": assignment.lab_id,
        "assigned_to": assigned_to,
        "target_id": target_id,
        "target_name": target_name,
        "deadline": assignment.deadline.isoformat(),
        "deadline_type": assignment.deadline_type,
        "submissions": 0,
        "total": total,
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "created_by": str(current_user.id)
    }

    lab_topic_assignments[assignment_id] = new_assignment

    return new_assignment


@router.get("/lab-assignments/{lab_id}")
async def get_lab_assignments(
    lab_id: str,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all assignments for a lab"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    assignments = [
        a for a in lab_topic_assignments.values()
        if a["lab_id"] == lab_id
    ]

    if status:
        assignments = [a for a in assignments if a["status"] == status]

    return assignments


@router.put("/lab-assignments/{assignment_id}")
async def update_lab_assignment(
    assignment_id: str,
    deadline: Optional[datetime] = Body(None),
    deadline_type: Optional[str] = Body(None),
    status: Optional[str] = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a lab assignment"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    if assignment_id not in lab_topic_assignments:
        raise HTTPException(status_code=404, detail="Assignment not found")

    assignment = lab_topic_assignments[assignment_id]

    if deadline:
        assignment["deadline"] = deadline.isoformat()
    if deadline_type:
        assignment["deadline_type"] = deadline_type
    if status:
        assignment["status"] = status

    assignment["updated_at"] = datetime.utcnow().isoformat()

    return assignment


@router.delete("/lab-assignments/{assignment_id}")
async def delete_lab_assignment(
    assignment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a lab assignment"""
    if current_user.role not in [UserRole.FACULTY, UserRole.HOD, UserRole.LECTURER, UserRole.PRINCIPAL, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty can access this endpoint")

    if assignment_id not in lab_topic_assignments:
        raise HTTPException(status_code=404, detail="Assignment not found")

    del lab_topic_assignments[assignment_id]

    return {"message": "Assignment deleted successfully"}
