"""
Faculty Portal API - dashboard aggregate and drill-down lists.

All routes require the faculty (or admin) role via `get_current_faculty`.
"""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.institution_time import humanise, local_today, to_local
from app.core.logging_config import logger
from app.models.faculty import (
    AttendanceRecord,
    AttendanceStatus,
    BasePaperStatus,
    ProjectBatch,
    ProjectReview,
    ReviewStatus,
    StudentEnrollment,
)
from app.models.faculty_import import ImportRun
from app.models.user import User, UserRole, COLLEGE_STAFF_ROLES
from app.modules.auth.dependencies import get_current_faculty
from app.schemas.faculty import FacultyDashboardResponse, FilterOptions
from app.services.faculty_dashboard import ATTENDANCE_FLOOR, FacultyDashboardService
from app.services.tenancy import tenant_of
from app.services.blocker_actions import BlockerActions
from app.services.milestone_actions import MilestoneActions
from app.services.milestone_board import MilestoneBoard
from app.services.task_board import TaskBoard
from app.services.project_tracker import ProjectTracker
from app.services.project_tracker_actions import TrackerActions, TrackerError
from app.services.project_schedule import (
    days_remaining,
    describe,
    expected_progress,
    is_behind,
    schedule_state,
)
from app.services.faculty_registrations import (
    FacultyRegistrationsService,
    RegistrationFilters,
)
from app.services.faculty_students import FacultyStudentsService, StudentFilters
from app.services.faculty_workflow import FacultyWorkflowService, WorkflowFilters
from app.models.faculty_import import ImportType
from app.services.faculty_imports import TEMPLATE_COLUMNS, FacultyImportService
from app.models.batch_detail import BatchDocument, DocumentStatus
from app.services.batch_detail import BatchDetailService
from app.models.academics import AcademicDepartment, AcademicSection
from app.services.academics import AcademicsService
from app.services.faculty_authority import FacultyAuthority
from app.services.batch_creation import BatchCreationError, BatchCreationService
from app.services import (
    attendance as attendance_service,
    batch_files,
    file_store,
    project_details,
    review_scheduling,
    submissions,
)
from app.services.batch_actions import (
    ActionError,
    decide_base_paper,
    cancel_review,
    complete_review,
    decide_document as decide_document_action,
    reschedule_review,
)

router = APIRouter(prefix="/faculty", tags=["Faculty Portal"])


def _default_academic_year(today: Optional[datetime] = None) -> str:
    """
    Current Indian academic year, e.g. "2026-27".

    The academic year rolls over in June, so January-May still belongs to the
    year that started the previous June.
    """
    now = today or datetime.utcnow()
    start = now.year if now.month >= 6 else now.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


@router.get("/dashboard", response_model=FacultyDashboardResponse)
async def get_faculty_dashboard(
    academic_year: Optional[str] = Query(None, description='e.g. "2026-27"; defaults to the current one'),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None, description='Section letter, or "All Sections"'),
    year: Optional[str] = Query(None, description='e.g. "4th Year"'),
    semester: Optional[str] = Query(None, description='"I" or "II"'),
    project_type: Optional[str] = Query(None),
    guide_id: Optional[str] = Query(None, description="Limit to one guide's batches"),
    mine_only: bool = Query(False, description="Shorthand for guide_id = the caller"),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Everything the faculty dashboard screen renders, in one response.

    Filters are AND-ed; omitting one (or passing an "All ..." value) widens the
    scope rather than narrowing it.
    """
    resolved_year = academic_year or _default_academic_year()
    resolved_guide = str(current_user.id) if mine_only else guide_id

    service = FacultyDashboardService(db, tenant_of(current_user))
    try:
        return await service.build_dashboard(
            current_user=current_user,
            academic_year=resolved_year,
            department=department,
            section=section,
            year=year,
            semester=semester,
            project_type=project_type,
            guide_id=resolved_guide,
        )
    except Exception as exc:
        logger.error(f"[Faculty] Dashboard build failed for {current_user.email}: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build faculty dashboard",
        )


@router.get("/filters", response_model=FilterOptions)
async def get_filter_options(
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Dropdown values, derived from the batches that actually exist."""
    service = FacultyDashboardService(db, tenant_of(current_user))
    return await service.build_filter_options(academic_year or _default_academic_year())


@router.get("/batches")
async def list_batches(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    needs_attention: bool = Query(False, description="Only batches behind their own schedule, overdue, or missing a base paper"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Batch list behind the dashboard's "Open Batch" and "View" links."""
    resolved_year = academic_year or _default_academic_year()

    stmt = (
        select(ProjectBatch)
        .options(
            selectinload(ProjectBatch.members),
            selectinload(ProjectBatch.base_paper),
            selectinload(ProjectBatch.reviews),
            selectinload(ProjectBatch.guide),
        )
        .where(ProjectBatch.college_id == tenant_of(current_user))
        .where(ProjectBatch.college_id == tenant_of(current_user))
        .where(ProjectBatch.academic_year == resolved_year)
        .where(ProjectBatch.is_active.is_(True))
    )
    if department:
        stmt = stmt.where(ProjectBatch.department == department)
    if section:
        stmt = stmt.where(ProjectBatch.section == section)

    batches = list((await db.execute(stmt.offset(offset).limit(limit))).scalars().unique().all())
    now = datetime.utcnow()

    items = []
    for batch in batches:
        bp = batch.base_paper
        overdue = sum(
            1 for r in batch.reviews
            if r.status == ReviewStatus.SCHEDULED and r.scheduled_at < now
        )
        inactive = sum(1 for m in batch.members if not m.is_active)
        expected = expected_progress(batch.start_date, batch.target_completion)
        behind = is_behind(batch.overall_progress, expected)
        flagged = (
            behind
            or overdue > 0
            or inactive > 0
            or bp is None
            or bp.status == BasePaperStatus.MISSING
        )
        if needs_attention and not flagged:
            continue

        items.append({
            "id": str(batch.id),
            "batch_code": batch.batch_code,
            "title": batch.title,
            "department": batch.department,
            "section": batch.section,
            "project_type": batch.project_type,
            "progress": int(round(batch.overall_progress or 0)),
            "expected_progress": None if expected is None else int(round(expected)),
            "schedule_state": schedule_state(batch.overall_progress, expected),
            "schedule_note": describe(batch.overall_progress, expected),
            "days_remaining": days_remaining(batch.target_completion),
            "guide_name": batch.guide.full_name if batch.guide else None,
            "member_count": len(batch.members),
            "inactive_members": inactive,
            "overdue_reviews": overdue,
            "base_paper_status": (bp.status.value if bp else BasePaperStatus.MISSING.value),
            "needs_attention": flagged,
        })

    return {"items": items, "count": len(items), "academic_year": resolved_year}


@router.get("/reviews")
async def list_reviews(
    academic_year: Optional[str] = Query(None),
    upcoming_only: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Scheduled reviews, newest first, behind "Open Schedule"/"View Calendar"."""
    resolved_year = academic_year or _default_academic_year()

    stmt = (
        select(ProjectReview, ProjectBatch)
        .join(ProjectBatch, ProjectReview.batch_id == ProjectBatch.id)
        .where(ProjectBatch.college_id == tenant_of(current_user))
        .where(ProjectBatch.academic_year == resolved_year)
    )
    if upcoming_only:
        stmt = stmt.where(ProjectReview.status == ReviewStatus.SCHEDULED)
        stmt = stmt.where(ProjectReview.scheduled_at >= datetime.utcnow())

    rows = (await db.execute(stmt.order_by(ProjectReview.scheduled_at).limit(limit))).all()

    return {
        "items": [
            {
                "id": str(review.id),
                "batch_code": batch.batch_code,
                "review_type": review.review_type,
                "scheduled_at": review.scheduled_at,
                # Formatted here, in the institution's timezone. The stored
                # value is naive UTC, and a browser parsing it without a zone
                # reads it as local - which showed every 10:00 review as 04:30.
                "scheduled_label": humanise(review.scheduled_at),
                "scheduled_day": to_local(review.scheduled_at).strftime("%A, %d %b %Y"),
                "scheduled_time": to_local(review.scheduled_at).strftime("%I:%M %p").lstrip("0"),
                "status": review.status.value,
            }
            for review, batch in rows
        ]
    }


@router.get("/students")
async def list_students(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    unassigned_only: bool = Query(False, description="Students not mapped to any section"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Enrolled students, behind the Registrations screen and the section drill-downs."""
    resolved_year = academic_year or _default_academic_year()

    stmt = (
        select(StudentEnrollment, User)
        .join(User, StudentEnrollment.student_id == User.id)
        .where(StudentEnrollment.college_id == tenant_of(current_user))
        .where(StudentEnrollment.academic_year == resolved_year)
        .where(StudentEnrollment.is_active.is_(True))
    )
    if department:
        stmt = stmt.where(StudentEnrollment.department == department)
    if section:
        stmt = stmt.where(StudentEnrollment.section == section)
    if unassigned_only:
        stmt = stmt.where(StudentEnrollment.section.is_(None))

    rows = (await db.execute(stmt.limit(limit))).all()

    return {
        "items": [
            {
                "id": str(enrollment.id),
                "student_id": str(user.id),
                "full_name": user.full_name,
                "email": user.email,
                "roll_number": user.roll_number,
                "department": enrollment.department,
                "section": enrollment.section,
                "year": enrollment.year,
                "semester": enrollment.semester,
                "is_registered": enrollment.is_registered,
            }
            for enrollment, user in rows
        ]
    }


@router.get("/attendance")
async def list_attendance(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    below_floor_only: bool = Query(False, description=f"Only students under {int(ATTENDANCE_FLOOR)}%"),
    limit: int = Query(200, ge=1, le=500),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Per-student attendance for the year, plus today's roll-up.

    Rate counts LATE as attended - the student was there, just not on time -
    so only ABSENT lowers it. Matches the dashboard's definition.
    """
    resolved_year = academic_year or _default_academic_year()

    enr_stmt = (
        select(StudentEnrollment, User)
        .join(User, StudentEnrollment.student_id == User.id)
        .where(StudentEnrollment.college_id == tenant_of(current_user))
        .where(StudentEnrollment.academic_year == resolved_year)
        .where(StudentEnrollment.is_active.is_(True))
    )
    if department:
        enr_stmt = enr_stmt.where(StudentEnrollment.department == department)
    if section:
        enr_stmt = enr_stmt.where(StudentEnrollment.section == section)

    rows = (await db.execute(enr_stmt)).all()
    student_ids = [e.student_id for e, _ in rows]

    rates: dict = {}
    if student_ids:
        rate_stmt = (
            select(
                AttendanceRecord.student_id,
                func.count().label("total"),
                func.sum(case((AttendanceRecord.status == AttendanceStatus.ABSENT, 1), else_=0)).label("absent"),
            )
            .where(AttendanceRecord.student_id.in_(student_ids))
            .where(AttendanceRecord.academic_year == resolved_year)
            .group_by(AttendanceRecord.student_id)
        )
        for student_id, total, absent in (await db.execute(rate_stmt)).all():
            if total:
                rates[str(student_id)] = round((total - (absent or 0)) / total * 100, 1)

    items = []
    for enrollment, user in rows:
        rate = rates.get(str(enrollment.student_id))
        if below_floor_only and (rate is None or rate >= ATTENDANCE_FLOOR):
            continue
        items.append({
            "student_id": str(user.id),
            "full_name": user.full_name,
            "roll_number": user.roll_number,
            "department": enrollment.department,
            "section": enrollment.section,
            "attendance_rate": rate,
            "below_floor": rate is not None and rate < ATTENDANCE_FLOOR,
        })

    items.sort(key=lambda i: (i["attendance_rate"] is None, i["attendance_rate"] or 0))

    today_counts = {"present": 0, "absent": 0, "late": 0}
    if student_ids:
        today_stmt = (
            select(AttendanceRecord.status, func.count())
            .where(AttendanceRecord.student_id.in_(student_ids))
            # The institution's today, not the server's - a UTC container
            # would report yesterday's roll-up all Indian evening.
            .where(AttendanceRecord.attendance_date == local_today())
            .group_by(AttendanceRecord.status)
        )
        for status_value, count in (await db.execute(today_stmt)).all():
            today_counts[status_value.value] = count

    return {
        "items": items[:limit],
        "count": len(items),
        "today": today_counts,
        "floor": ATTENDANCE_FLOOR,
        "academic_year": resolved_year,
    }


@router.get("/guides")
async def list_guides(
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Every faculty member and the batches they guide.

    An inner join here would list only the people who already hold batches -
    which is the opposite of what the screen is for. Deciding who to assign a
    batch to means seeing who is free, so someone carrying none is the most
    interesting row on the page, not one to hide.
    """
    resolved_year = academic_year or _default_academic_year()

    stmt = (
        select(
            User.id,
            User.full_name,
            User.email,
            User.department,
            func.count(ProjectBatch.id).label("batches"),
            func.avg(ProjectBatch.overall_progress).label("avg_progress"),
        )
        .outerjoin(
            ProjectBatch,
            (ProjectBatch.guide_id == User.id)
            & (ProjectBatch.academic_year == resolved_year)
            & (ProjectBatch.is_active.is_(True)),
        )
        .where(User.role.in_(COLLEGE_STAFF_ROLES))
        .group_by(User.id, User.full_name, User.email, User.department)
        .order_by(func.count(ProjectBatch.id).desc(), User.full_name)
    )
    rows = (await db.execute(stmt)).all()

    return {
        "items": [
            {
                "id": str(guide_id),
                "full_name": name,
                "email": email,
                "department": dept,
                "batches": batches,
                "avg_progress": int(round(avg or 0)),
            }
            for guide_id, name, email, dept, batches, avg in rows
        ]
    }


# ============================================
# Student & Batch Registrations
# ============================================


class AssignGuideRequest(BaseModel):
    batch_ids: List[str] = Field(..., min_length=1)
    guide_id: str


class ApproveRequest(BaseModel):
    batch_ids: List[str] = Field(..., min_length=1)


def _registration_filters(
    academic_year: Optional[str],
    department: Optional[str],
    section: Optional[str],
    year: Optional[str],
    semester: Optional[str],
    project_type: Optional[str],
    reg_status: Optional[str],
    search: Optional[str],
) -> RegistrationFilters:
    return RegistrationFilters(
        academic_year=academic_year or _default_academic_year(),
        department=department,
        section=section,
        year=year,
        semester=semester,
        project_type=project_type,
        status=reg_status,
        search=search,
    )


@router.get("/registrations")
async def get_registrations(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    project_type: Optional[str] = Query(None),
    reg_status: Optional[str] = Query(None, description="draft | incomplete | submitted | pending_approval | changes_requested | approved"),
    search: Optional[str] = Query(None, description="Batch code, project title, student name or roll number"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=5, le=100),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Everything the Student & Batch Registrations screen renders."""
    filters = _registration_filters(
        academic_year, department, section, year, semester, project_type, reg_status, search
    )
    service = FacultyRegistrationsService(db, tenant_of(current_user))
    try:
        return await service.build(filters, page=page, per_page=per_page)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error(f"[Faculty] Registrations build failed for {current_user.email}: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build registrations view",
        )


@router.post("/registrations/assign-guide")
async def assign_guide(
    payload: AssignGuideRequest,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Assign one guide to the selected batches."""
    service = FacultyRegistrationsService(db, tenant_of(current_user))
    try:
        updated = await service.assign_guide(payload.batch_ids, payload.guide_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    logger.info(f"[Faculty] {current_user.email} assigned a guide to {updated} batch(es)")
    return {"updated": updated}


@router.post("/registrations/approve")
async def approve_registrations(
    payload: ApproveRequest,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Approve the selected batches.

    A batch short of members, without a base paper, or without a guide is
    skipped and reported back rather than silently approved.
    """
    service = FacultyRegistrationsService(db, tenant_of(current_user))
    result = await service.approve(payload.batch_ids)
    logger.info(
        f"[Faculty] {current_user.email} approved {len(result['approved'])} batch(es), "
        f"skipped {len(result['skipped'])}"
    )
    return result


@router.get("/registrations/export")
async def export_registrations(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    project_type: Optional[str] = Query(None),
    reg_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """The current filtered view as CSV, all rows rather than one page."""
    import csv
    import io as _io

    filters = _registration_filters(
        academic_year, department, section, year, semester, project_type, reg_status, search
    )
    service = FacultyRegistrationsService(db, tenant_of(current_user))
    # per_page large enough to take the whole filtered set in one page.
    data = await service.build(filters, page=1, per_page=100)
    if data["total"] > 100:
        data = await service.build(filters, page=1, per_page=data["total"])

    buffer = _io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Batch Code", "Project Title", "Section", "Members", "Team Size",
        "Batch Leader", "Base Paper", "Guide", "Registration Status", "Last Updated",
    ])
    for row in data["rows"]:
        writer.writerow([
            row["batch_code"], row["title"] or "", row["section"] or "",
            row["members"], row["team_size"], row["batch_leader"] or "",
            row["base_paper"], row["guide"] or "Not Assigned", row["status"],
            row["last_updated"].strftime("%Y-%m-%d") if row["last_updated"] else "",
        ])
    buffer.seek(0)

    filename = f"registrations-{filters.academic_year}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============================================
# Student Registrations tab
# ============================================


class VerifyStudentsRequest(BaseModel):
    enrollment_ids: List[str] = Field(..., min_length=1)


class AssignToBatchRequest(BaseModel):
    enrollment_ids: List[str] = Field(..., min_length=1)
    batch_id: str


def _student_filters(
    academic_year: Optional[str],
    department: Optional[str],
    section: Optional[str],
    year: Optional[str],
    semester: Optional[str],
    batch_status: Optional[str],
    profile_status: Optional[str],
    search: Optional[str],
) -> StudentFilters:
    return StudentFilters(
        academic_year=academic_year or _default_academic_year(),
        department=department,
        section=section,
        year=year,
        semester=semester,
        batch_status=batch_status,
        profile_status=profile_status,
        search=search,
    )


@router.get("/registrations/students")
async def get_student_registrations(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    batch_status: Optional[str] = Query(None, description="in_batch | not_in_batch"),
    profile_status: Optional[str] = Query(None, description="verified | verification_pending | profile_incomplete"),
    search: Optional[str] = Query(None, description="Name, roll number, email, mobile or batch code"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=5, le=100),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Everything the Student Registrations tab renders."""
    filters = _student_filters(
        academic_year, department, section, year, semester, batch_status, profile_status, search
    )
    service = FacultyStudentsService(db, tenant_of(current_user))
    try:
        return await service.build(filters, page=page, per_page=per_page)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error(f"[Faculty] Student registrations failed for {current_user.email}: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build student registrations view",
        )


@router.post("/registrations/students/verify")
async def verify_students(
    payload: VerifyStudentsRequest,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark the selected profiles verified.

    A student with no mobile or email is skipped and reported - verifying them
    would empty the "missing mobile/email" queue without fixing anything.
    """
    service = FacultyStudentsService(db, tenant_of(current_user))
    result = await service.verify(payload.enrollment_ids)
    logger.info(
        f"[Faculty] {current_user.email} verified {len(result['verified'])} profile(s), "
        f"skipped {len(result['skipped'])}"
    )
    return result


@router.post("/registrations/students/assign-batch")
async def assign_students_to_batch(
    payload: AssignToBatchRequest,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Add the selected students to a batch as members."""
    service = FacultyStudentsService(db, tenant_of(current_user))
    try:
        result = await service.assign_to_batch(payload.enrollment_ids, payload.batch_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    logger.info(f"[Faculty] {current_user.email} added {result['added']} student(s) to {result['batch_code']}")
    return result


@router.get("/registrations/students/export")
async def export_student_registrations(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    batch_status: Optional[str] = Query(None),
    profile_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """The current filtered student list as CSV."""
    import csv
    import io as _io

    filters = _student_filters(
        academic_year, department, section, year, semester, batch_status, profile_status, search
    )
    service = FacultyStudentsService(db, tenant_of(current_user))
    first = await service.build(filters, page=1, per_page=100)
    data = first if first["total"] <= 100 else await service.build(filters, page=1, per_page=first["total"])

    buffer = _io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Roll Number", "Student", "Department", "Section", "Mobile", "Email",
        "Batch Code", "Role", "Profile Status",
    ])
    for row in data["rows"]:
        writer.writerow([
            row["roll_number"] or "", row["full_name"] or "", row["department"],
            row["section"] or "", row["mobile"] or "", row["email"],
            row["batch_code"] or "Not Joined", row["role"] or "-", row["profile_status"],
        ])
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="students-{filters.academic_year}.csv"'},
    )


# ============================================
# Incomplete Registrations + Approval Queue
# ============================================


class DecisionRequest(BaseModel):
    batch_ids: List[str] = Field(..., min_length=1)
    decision: str = Field(..., description="approve | reject | request_changes")
    note: Optional[str] = None


class AssignReviewerRequest(BaseModel):
    batch_ids: List[str] = Field(..., min_length=1)
    reviewer_id: str


class ReminderRequest(BaseModel):
    record_ids: List[str] = Field(..., min_length=1)
    kind: str = Field("student", description="student | batch")


def _workflow_filters(**kwargs) -> WorkflowFilters:
    academic_year = kwargs.pop("academic_year", None) or _default_academic_year()
    return WorkflowFilters(academic_year=academic_year, **kwargs)


@router.get("/registrations/incomplete")
async def get_incomplete_registrations(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    issue_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None, description="Critical | High | Medium"),
    scope: Optional[str] = Query(None, description="all | student | batch"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=5, le=100),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Records with at least one registration gap, derived rather than stored."""
    filters = _workflow_filters(
        academic_year=academic_year, department=department, section=section,
        year=year, semester=semester, issue_type=issue_type, priority=priority,
        scope=scope, search=search,
    )
    service = FacultyWorkflowService(db, tenant_of(current_user))
    try:
        return await service.build_incomplete(filters, page=page, per_page=per_page)
    except Exception as exc:
        logger.error(f"[Faculty] Incomplete view failed for {current_user.email}: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to build incomplete registrations view")


@router.get("/registrations/queue")
async def get_approval_queue(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    review_status: Optional[str] = Query("pending", description="pending | changes | approved | rejected"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=5, le=100),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """The approval queue, its KPIs, and the first row's full detail panel."""
    filters = _workflow_filters(
        academic_year=academic_year, department=department, section=section,
        year=year, semester=semester, review_status=review_status, search=search,
    )
    service = FacultyWorkflowService(db, tenant_of(current_user))
    try:
        return await service.build_queue(filters, page=page, per_page=per_page)
    except Exception as exc:
        logger.error(f"[Faculty] Approval queue failed for {current_user.email}: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to build approval queue")


@router.get("/registrations/queue/{batch_id}")
async def get_queue_detail(
    batch_id: str,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """One registration's detail panel and approval checklist."""
    detail = await FacultyWorkflowService(db, tenant_of(current_user)).detail(batch_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    return detail


@router.post("/registrations/queue/decide")
async def decide_registrations(
    payload: DecisionRequest,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Approve, reject, or send a registration back for changes.

    Approval runs the same seven-point checklist the screen renders, so a batch
    that fails any mandatory check is skipped with the reasons listed.
    """
    service = FacultyWorkflowService(db, tenant_of(current_user))
    try:
        result = await service.decide(payload.batch_ids, payload.decision, payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    logger.info(
        f"[Faculty] {current_user.email} {payload.decision}: {len(result['applied'])} applied, "
        f"{len(result['skipped'])} skipped"
    )
    return result


@router.post("/registrations/queue/assign-reviewer")
async def assign_reviewer(
    payload: AssignReviewerRequest,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Assign a reviewer to the selected registrations."""
    try:
        updated = await FacultyWorkflowService(db, tenant_of(current_user)).assign_reviewer(payload.batch_ids, payload.reviewer_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return {"updated": updated}


@router.post("/registrations/reminders")
async def record_reminders(
    payload: ReminderRequest,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Record that these records were chased.

    This stamps last_reminder_at only - no email is sent, because no dispatch
    pipeline is wired up. The response says so explicitly.
    """
    count = await FacultyWorkflowService(db, tenant_of(current_user)).send_reminders(payload.record_ids, payload.kind)
    return {
        "stamped": count,
        "emails_sent": 0,
        "detail": "Reminder timestamps recorded. No email was sent - the dispatch pipeline is not configured.",
    }


# ============================================
# Roster imports
# ============================================


class ArchiveImportsRequest(BaseModel):
    run_ids: List[str] = Field(..., min_length=1)


@router.get("/imports")
async def list_imports(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    import_type: Optional[str] = Query(None),
    import_status: Optional[str] = Query(None, description="processing | successful | partially_imported | failed"),
    imported_by: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=5, le=100),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Import history with its KPIs and the first run's detail panel."""
    service = FacultyImportService(db, tenant_of(current_user))
    try:
        return await service.build(
            academic_year=academic_year or _default_academic_year(),
            department=department,
            import_type=import_type,
            status=import_status,
            imported_by=imported_by,
            search=search,
            page=page,
            per_page=per_page,
        )
    except Exception as exc:
        logger.error(f"[Faculty] Import history failed for {current_user.email}: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to load import history")


@router.post("/imports", status_code=status.HTTP_201_CREATED)
async def create_import(
    file: UploadFile = File(..., description="CSV or XLSX roster"),
    import_type: str = Form(...),
    academic_year: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload and apply a roster.

    The file is parsed, every row validated, and valid rows written one at a
    time - a bad row is recorded against the run rather than failing the upload.
    """
    try:
        kind = ImportType(import_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown import type. Expected one of: {', '.join(t.value for t in ImportType)}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty.")

    service = FacultyImportService(db, tenant_of(current_user))
    try:
        run = await service.run_import(
            filename=file.filename or "upload.csv",
            content=content,
            import_type=kind,
            academic_year=academic_year or _default_academic_year(),
            department=department,
            actor=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error(f"[Faculty] Import failed for {current_user.email}: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="The import could not be processed")

    logger.info(
        f"[Faculty] {current_user.email} imported {run.import_code}: "
        f"{run.rows_imported} in, {run.rows_failed} failed, {run.rows_duplicate} duplicate"
    )
    return await service.detail(str(run.id))


@router.get("/imports/template")
async def download_import_template(
    import_type: str = Query("student_list"),
    current_user: User = Depends(get_current_faculty),
):
    """A header-only CSV with the columns this import type expects."""
    import csv as _csv
    import io as _io

    try:
        kind = ImportType(import_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown import type")

    buffer = _io.StringIO()
    writer = _csv.writer(buffer)
    writer.writerow(TEMPLATE_COLUMNS[kind])
    if kind is ImportType.STUDENT_LIST:
        writer.writerow(["23CS101", "Aadhya Reddy", "aadhya@sgit.ac.in", "9876543210", "CSE", "A", "4th Year", "I"])
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{kind.value}-template.csv"'},
    )


@router.get("/imports/{run_id}")
async def get_import(
    run_id: str,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """One run: summary, timeline and validation issues."""
    detail = await FacultyImportService(db, tenant_of(current_user)).detail(run_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found")
    return detail


@router.get("/imports/{run_id}/original")
async def download_original_file(
    run_id: str,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """The exact bytes that were uploaded."""
    run = (await db.execute(select(ImportRun).where(ImportRun.id == run_id))).scalar_one_or_none()
    if run is None or run.file_content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original file not available")
    return StreamingResponse(
        iter([run.file_content]),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{run.file_name}"'},
    )


@router.get("/imports/{run_id}/errors")
async def download_error_file(
    run_id: str,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Every rejected or skipped row, as a CSV that can be corrected and re-uploaded."""
    result = await FacultyImportService(db, tenant_of(current_user)).error_csv(run_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found")
    filename, body = result
    return StreamingResponse(
        iter([body]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/imports/archive")
async def archive_imports(
    payload: ArchiveImportsRequest,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Hide runs from the history without deleting their audit trail."""
    archived = await FacultyImportService(db, tenant_of(current_user)).archive(payload.run_ids)
    return {"archived": archived}


# ============================================
# Batch Registration Details
# ============================================


class InternalNoteRequest(BaseModel):
    note: str = Field("", max_length=4000)


class ChangeLeaderRequest(BaseModel):
    member_id: str


class MemberRolesRequest(BaseModel):
    roles: dict = Field(..., description="member_id -> responsibility")


class RemoveMemberRequest(BaseModel):
    member_id: str
    reason: str = Field(..., min_length=4, max_length=255)


class DocumentDecisionRequest(BaseModel):
    document_id: str
    decision: str = Field(..., description="verify | request_changes")
    note: Optional[str] = None


async def _require_batch(
    db: AsyncSession,
    identifier: str,
    user: User,
    *,
    manage: bool = False,
    action: str = "act",
):
    """
    Load a batch and check this user is entitled to it.

    Every batch route funnels through here, so the check cannot be forgotten on
    a new endpoint. `manage=True` is for anything that writes; reads only need
    a place in the department.
    """
    service = BatchDetailService(db)
    batch = await service.load(identifier)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    authority = FacultyAuthority(db)
    can_manage = await authority.can_manage(user, batch)
    allowed = can_manage if manage else await authority.can_view(user, batch)
    if not allowed:
        logger.warning(
            f"[Faculty] {user.email} denied {'write' if manage else 'read'} "
            f"access to {batch.batch_code}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=FacultyAuthority.denial(action) if manage
            else "This batch belongs to a department you are not attached to.",
        )
    # Carried on the batch so every tab payload can tell the UI whether to offer
    # its actions, rather than letting a viewer press a button that will 403.
    batch._can_manage = can_manage
    return service, batch


def _detail_route(name: str, builder: str, description: str):
    """Registers one tab endpoint; every tab shares the same load/error shape."""
    async def endpoint(
        identifier: str,
        current_user: User = Depends(get_current_faculty),
        db: AsyncSession = Depends(get_db),
    ):
        service, batch = await _require_batch(db, identifier, current_user)
        try:
            payload = await getattr(service, builder)(batch)
            payload["can_manage"] = getattr(batch, "_can_manage", False)
            return payload
        except Exception as exc:
            logger.error(f"[Faculty] Batch {name} failed for {identifier}: {type(exc).__name__}: {exc}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Failed to build the {name} tab")

    endpoint.__name__ = f"get_batch_{name}"
    endpoint.__doc__ = description
    router.get(f"/batches/{{identifier}}/{name}")(endpoint)


for _name, _builder, _doc in [
    ("overview", "overview", "Overview tab: team, project information, base paper, checklist, timeline."),
    ("team", "team", "Team Members tab: member cards, validation, roles, formation timeline."),
    ("project", "project", "Project Details tab: objectives, methodology, scope, stack, validation."),
    ("papers", "papers", "Base Papers tab: primary paper, improvement, supporting papers, quality."),
    ("documents", "documents", "Documents tab: versioned documents, checklist, queue, storage."),
    ("approvals", "approvals", "Approval History tab: journey, cycles, participants, decisions."),
]:
    _detail_route(_name, _builder, _doc)


@router.get("/batches/{identifier}/activity")
async def get_batch_activity(
    identifier: str,
    module: Optional[str] = Query(None),
    severity: Optional[str] = Query(None, description="info | success | warning | critical"),
    actor: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD, inclusive"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD, inclusive"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=5, le=100),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Activity Log tab. Records are append-only; there is no mutation route."""
    service, batch = await _require_batch(db, identifier, current_user)
    payload = await service.activity(
        batch, module=module, severity=severity, actor=actor, search=search,
        date_from=date_from, date_to=date_to, page=page, per_page=per_page,
    )
    payload["can_manage"] = getattr(batch, "_can_manage", False)
    return payload


@router.get("/batches/{identifier}/activity-log.csv")
async def export_batch_activity(
    identifier: str,
    module: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Export Log. Exports what the filters currently select, not the whole table -
    a filtered view that exports everything is a reliable way to mislead.
    """
    import csv as _csv
    import io as _io

    service, batch = await _require_batch(db, identifier, current_user)
    data = await service.activity(
        batch, module=module, severity=severity, actor=actor, search=search,
        date_from=date_from, date_to=date_to, page=1, per_page=100,
    )

    buffer = _io.StringIO()
    writer = _csv.writer(buffer)
    writer.writerow(["Event ID", "Time", "Actor", "Role", "Activity", "Module",
                     "Details", "Status", "Severity", "Source", "IP Address"])
    for r in data["rows"]:
        writer.writerow([
            r["event_code"],
            r["occurred_at"].strftime("%Y-%m-%d %H:%M:%S") if r.get("occurred_at") else "",
            r["actor"] or "", r["actor_role"] or "", r["activity"], r["module"],
            r["details"] or "", r["status_label"] or "", r["severity"],
            r.get("source") or "", r.get("ip_address") or "",
        ])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{batch.batch_code}-activity-log.csv"'},
    )


@router.patch("/batches/{identifier}/internal-note")
async def update_internal_note(
    identifier: str,
    payload: InternalNoteRequest,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Faculty-only note. Students never see this field."""
    _, batch = await _require_batch(db, identifier, current_user, manage=True, action="write an internal note")
    batch.internal_note = payload.note.strip() or None
    await db.commit()
    return {"internal_note": batch.internal_note}


@router.post("/batches/{identifier}/leader")
async def change_batch_leader(
    identifier: str,
    payload: ChangeLeaderRequest,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Move the leader flag to another active member."""
    _, batch = await _require_batch(db, identifier, current_user, manage=True, action="change the batch leader")
    target = next((m for m in batch.members if str(m.id) == payload.member_id), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in this batch")
    if not target.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="An inactive member cannot lead the batch")

    for member in batch.members:
        member.is_lead = member.id == target.id
    await db.commit()
    logger.info(f"[Faculty] {current_user.email} made {payload.member_id} leader of {batch.batch_code}")
    return {"batch_code": batch.batch_code, "leader_id": str(target.id)}


@router.patch("/batches/{identifier}/roles")
async def update_member_roles(
    identifier: str,
    payload: MemberRolesRequest,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Set each member's responsibility label."""
    _, batch = await _require_batch(db, identifier, current_user, manage=True, action="change member roles")
    by_id = {str(m.id): m for m in batch.members}
    updated = 0
    for member_id, responsibility in payload.roles.items():
        member = by_id.get(member_id)
        if member is None:
            continue
        member.responsibility = (responsibility or "").strip() or None
        updated += 1
    await db.commit()
    return {"updated": updated}


@router.post("/batches/{identifier}/remove-member")
async def remove_member(
    identifier: str,
    payload: RemoveMemberRequest,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate a member.

    The row is kept rather than deleted so the team history and audit trail stay
    intact, and the leader cannot be removed without handing the role over first.
    """
    _, batch = await _require_batch(db, identifier, current_user, manage=True,
                                    action="remove a member")
    target = next((m for m in batch.members if str(m.id) == payload.member_id), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in this batch")
    if target.is_lead:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Change the batch leader before removing this member",
        )
    target.is_active = False
    await db.commit()
    logger.info(
        f"[Faculty] {current_user.email} removed member {payload.member_id} "
        f"from {batch.batch_code}: {payload.reason}"
    )
    return {"removed": payload.member_id, "reason": payload.reason}


@router.post("/batches/{identifier}/documents/decide")
async def decide_document(
    identifier: str,
    payload: DocumentDecisionRequest,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a document or send it back.

    A verified document is locked - correcting it means uploading a new version,
    which is why re-verifying one is refused rather than silently re-stamped.
    """
    _, batch = await _require_batch(db, identifier, current_user, manage=True,
                                    action="decide on documents")
    # The rules live in batch_actions so the trainer portal, which writes the
    # same rows, cannot drift from this behaviour.
    try:
        return await decide_document_action(
            db, batch, payload.document_id, payload.decision, current_user, note=payload.note,
        )
    except ActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/batches/{identifier}/team-list")
async def download_team_list(
    identifier: str,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """The team as CSV, behind Download Team List."""
    import csv as _csv
    import io as _io

    service, batch = await _require_batch(db, identifier, current_user)
    data = await service.team(batch)

    buffer = _io.StringIO()
    writer = _csv.writer(buffer)
    writer.writerow(["Roll Number", "Name", "Role", "Responsibility", "Mobile", "Email",
                     "Department", "Section", "Joined", "Active"])
    for m in data["members"]:
        writer.writerow([
            m["roll_number"] or "", m["name"] or "", m["role"], m["responsibility"] or "",
            m["mobile"] or "", m["email"] or "", m["department"] or "", m["section"] or "",
            m["joined_at"].strftime("%Y-%m-%d %H:%M") if m.get("joined_at") else "",
            "Yes" if m["is_active"] else "No",
        ])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{batch.batch_code}-team.csv"'},
    )


# ============================================
# Departments & Sections
# ============================================


class SectionUpdateRequestBody(BaseModel):
    department: str = Field(..., description="Department code, e.g. CSE")
    section_id: Optional[str] = Field(None, description="Omit for a department-wide request")
    kind: str = Field(..., max_length=60, description="Capacity | Room | Timetable | Coordinator | Allocation | Other")
    note: str = Field(..., min_length=8, max_length=2000)
    academic_year: Optional[str] = None


async def _require_section(db: AsyncSession, section_id: str) -> tuple:
    service = AcademicsService(db, tenant_of(current_user))
    section = await service.load_section(section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    return service, section


@router.get("/academics/structure")
async def get_academic_structure(
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """The academic tree: school -> department -> year -> semester -> sections."""
    return await AcademicsService(db, tenant_of(current_user)).structure(academic_year or _default_academic_year())


@router.get("/academics/overview")
async def get_academic_overview(
    department: str = Query(..., description="Department code, e.g. CSE"),
    year: str = Query(..., description='e.g. "4th Year"'),
    semester: str = Query(..., description='"I" or "II"'),
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Section cards, allocation matrix and notices for one department cohort."""
    data = await AcademicsService(db, tenant_of(current_user)).overview(
        academic_year or _default_academic_year(), department, year, semester
    )
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No department {department} in this academic year")
    return data


def _section_route(name: str, builder: str, description: str):
    """Registers one section tab; every tab shares the same load/error shape."""
    async def endpoint(
        section_id: str,
        current_user: User = Depends(get_current_faculty),
        db: AsyncSession = Depends(get_db),
    ):
        service, section = await _require_section(db, section_id)
        try:
            return await getattr(service, builder)(section)
        except Exception as exc:
            logger.error(f"[Faculty] Section {name} failed for {section_id}: {type(exc).__name__}: {exc}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Failed to build the section {name} tab")

    endpoint.__name__ = f"get_section_{name}"
    endpoint.__doc__ = description
    suffix = "" if name == "overview" else f"/{name}"
    router.get(f"/academics/sections/{{section_id}}{suffix}")(endpoint)


for _name, _builder, _doc in [
    ("overview", "section_overview", "Section overview: KPIs, faculty, project mix, attention."),
    ("faculty", "section_faculty", "Faculty attached to the section and what each covers."),
    ("subjects", "section_subjects", "Subjects taught to the section."),
    ("projects", "section_projects", "Project batches registered in the section."),
]:
    _section_route(_name, _builder, _doc)


@router.get("/academics/my-access")
async def get_my_access(
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """What the signed-in faculty member can open, derived from their assignments."""
    return await AcademicsService(db, tenant_of(current_user)).my_access(
        current_user, academic_year or _default_academic_year()
    )


@router.get("/academics/structure.csv")
async def export_academic_structure(
    department: Optional[str] = Query(None, description="Limit to one department code"),
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Export Structure. One row per section with its live allocation figures, so
    the export says the same thing the screen does.
    """
    import csv as _csv
    import io as _io

    resolved = academic_year or _default_academic_year()
    service = AcademicsService(db, tenant_of(current_user))
    tree = await service.structure(resolved)

    buffer = _io.StringIO()
    writer = _csv.writer(buffer)
    writer.writerow(["School", "Department", "Department Code", "Year", "Semester", "Section",
                     "Capacity", "Assigned", "Unassigned Seats", "Project Batches",
                     "Faculty Guides", "Student-Guide Ratio", "Coordinator", "Room",
                     "Timetable", "Status"])

    for school in tree["schools"]:
        for dept in school["departments"]:
            if department and dept["code"] != department:
                continue
            for year in dept["years"]:
                for sem in year["semesters"]:
                    data = await service.overview(resolved, dept["code"], year["year"], sem["semester"])
                    for row in (data or {}).get("matrix", []):
                        writer.writerow([
                            school["school"], dept["name"], dept["code"],
                            year["year"], sem["semester"], row["section"],
                            row["capacity"], row["assigned"], row["unassigned"],
                            row["batches"], row["guides"], row["ratio"],
                            row["coordinator"] or "", row["room"] or "",
                            row["timetable"], row["status"],
                        ])

    buffer.seek(0)
    label = department or "all-departments"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{label}-structure-{resolved}.csv"'},
    )


@router.get("/academics/update-requests")
async def list_update_requests(
    department: str = Query(...),
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Open and past structure-change requests for a department."""
    resolved = academic_year or _default_academic_year()
    dept = (await db.execute(
        select(AcademicDepartment)
        .where(AcademicDepartment.code == department)
        .where(AcademicDepartment.academic_year == resolved)
    )).scalar_one_or_none()
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return {"rows": await AcademicsService(db, tenant_of(current_user)).update_requests(str(dept.id))}


@router.post("/academics/update-requests", status_code=status.HTTP_201_CREATED)
async def create_update_request(
    payload: SectionUpdateRequestBody,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Request Section Update.

    Faculty cannot edit the structure directly - the HOD and coordinator own
    it - so the ask is recorded here for them to action.
    """
    resolved = payload.academic_year or _default_academic_year()
    dept = (await db.execute(
        select(AcademicDepartment)
        .where(AcademicDepartment.code == payload.department)
        .where(AcademicDepartment.academic_year == resolved)
    )).scalar_one_or_none()
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    # A request is a claim about a department you work in.
    if not await FacultyAuthority(db).can_act_for_department(current_user, payload.department, resolved):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not attached to {payload.department}, so you cannot raise requests for it.",
        )

    section = None
    if payload.section_id:
        section = (await db.execute(
            select(AcademicSection).where(AcademicSection.id == payload.section_id)
        )).scalar_one_or_none()
        if section is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
        if section.department_id != dept.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="That section is not in this department")

    request = await AcademicsService(db, tenant_of(current_user)).create_update_request(
        user=current_user, department=dept, section=section,
        kind=payload.kind, note=payload.note,
    )
    logger.info(f"[Faculty] {current_user.email} requested a {payload.kind} update on {payload.department}")
    return {
        "id": str(request.id),
        "kind": request.kind,
        "status": request.status.value,
        "section": section.name if section else None,
        "created_at": request.created_at,
    }


# ============================================
# Forming a batch
# ============================================


class CreateBatchBody(BaseModel):
    department: str
    year: str
    semester: str
    section: str
    project_type: str = "Major Project"
    guide_id: Optional[str] = None
    team_size: int = Field(4, ge=2, le=8)
    project_fee: int = Field(15000, ge=0, le=1000000)
    count: int = Field(1, ge=1, le=20)
    academic_year: Optional[str] = None


@router.get("/registrations/batch-options")
async def batch_form_options(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    What the new-batch form may offer, plus how many students still need a seat
    in the chosen cohort - so the intake can be sized rather than guessed.
    """
    resolved = academic_year or _default_academic_year()
    service = BatchCreationService(db)
    payload = await service.options(current_user, resolved)
    if department and year and section:
        payload["unassigned_students"] = await service.unassigned_students(
            department, year, section, resolved
        )
    return payload


@router.post("/registrations/batches", status_code=status.HTTP_201_CREATED)
async def create_batches(
    payload: CreateBatchBody,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Form one or more empty batches for a section.

    Each gets a faculty-facing code and the join code students type. Creation is
    limited to a department the caller actually works in - the same rule that
    governs section-change requests.
    """
    resolved = payload.academic_year or _default_academic_year()
    if not await FacultyAuthority(db).can_act_for_department(
        current_user, payload.department, resolved
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not attached to {payload.department}, so you cannot form batches in it.",
        )
    try:
        return await BatchCreationService(db).create(
            current_user,
            academic_year=resolved,
            department=payload.department,
            year=payload.year,
            semester=payload.semester,
            section=payload.section,
            project_type=payload.project_type,
            guide_id=payload.guide_id,
            team_size=payload.team_size,
            project_fee=payload.project_fee,
            count=payload.count,
        )
    except BatchCreationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ============================================
# Project details entry
# ============================================


class ProjectObjectiveBody(BaseModel):
    text: str
    status: Optional[str] = None


class ProjectStepBody(BaseModel):
    title: str
    description: Optional[str] = None


class ProjectTechnologyBody(BaseModel):
    layer: Optional[str] = None
    name: str


class ProjectDetailsBody(BaseModel):
    """
    The whole Project Details form.

    Every list is optional so a screen may save one card without having to
    resend the others; a list that IS sent replaces what was there.
    """
    title: Optional[str] = None
    domain: Optional[str] = None
    project_type: Optional[str] = None
    keywords: Optional[List[str]] = None
    problem_statement: Optional[str] = None
    abstract: Optional[str] = None
    objectives: Optional[List[ProjectObjectiveBody]] = None
    methodology: Optional[List[ProjectStepBody]] = None
    outcomes: Optional[List[str]] = None
    in_scope: Optional[List[str]] = None
    out_of_scope: Optional[List[str]] = None
    deliverables: Optional[List[str]] = None
    technologies: Optional[List[ProjectTechnologyBody]] = None
    start_date: Optional[str] = None
    target_completion: Optional[str] = None
    weekly_effort_hours: Optional[int] = None


@router.get("/batches/{identifier}/project/form")
async def get_project_form(
    identifier: str,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """The Project Details tab's values, shaped for editing rather than display."""
    _, batch = await _require_batch(db, identifier, current_user)
    payload = project_details.form(batch)
    payload["can_manage"] = getattr(batch, "_can_manage", False)
    # Submitting is the team's act - a guide reviews what was submitted rather
    # than submitting on their behalf - so this form never offers the button.
    payload["can_submit"] = False
    return payload


@router.put("/batches/{identifier}/project")
async def save_project_details(
    identifier: str,
    body: ProjectDetailsBody,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Correct a batch's project details.

    A guide editing on the team's behalf writes through the same service the
    students use, so the two paths cannot validate differently.
    """
    _, batch = await _require_batch(db, identifier, current_user,
                                    manage=True, action="edit project details")
    try:
        result = await project_details.save(
            db, batch, body.model_dump(exclude_unset=True), current_user,
            actor_role="Faculty", source="Faculty Portal",
        )
    except project_details.ProjectDetailsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    logger.info(f"[Faculty] {current_user.email} edited project details on "
                f"{batch.batch_code}: {result.get('changed_fields')}")
    return result


# ============================================
# Files: documents and the base paper PDF
# ============================================


@router.get("/batches/{identifier}/files/options")
async def file_upload_options(
    identifier: str,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Categories and size limits, so the picker can refuse before uploading."""
    _, batch = await _require_batch(db, identifier, current_user)
    payload = batch_files.options()
    payload["can_manage"] = getattr(batch, "_can_manage", False)
    return payload


@router.post("/batches/{identifier}/documents", status_code=status.HTTP_201_CREATED)
async def upload_batch_document(
    identifier: str,
    file: UploadFile = File(...),
    category: str = Form("Project Document"),
    name: Optional[str] = Form(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Upload a registration document, or a new version of one."""
    _, batch = await _require_batch(db, identifier, current_user,
                                    manage=True, action="upload documents")
    try:
        return await batch_files.upload_document(
            db, batch, file, current_user, name=name, category=category,
            actor_role="Faculty", source="Faculty Portal",
        )
    except batch_files.BatchFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/batches/{identifier}/documents/{document_id}/download")
async def download_batch_document(
    identifier: str,
    document_id: str,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a document's bytes.

    Reading is enough - a guide who may see the batch may read what it holds -
    but the document must belong to this batch, which `_require_batch` plus the
    batch-scoped lookup together guarantee.
    """
    _, batch = await _require_batch(db, identifier, current_user)
    try:
        document, content = await batch_files.document_for_download(db, batch, document_id)
    except batch_files.BatchFileError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return StreamingResponse(
        iter([content]),
        media_type=document.file.mime_type,
        headers=file_store.download_headers(document.file, document.name),
    )


@router.delete("/batches/{identifier}/documents/{document_id}")
async def remove_batch_document(
    identifier: str,
    document_id: str,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Remove an unverified document. Verified ones are superseded, not deleted."""
    _, batch = await _require_batch(db, identifier, current_user,
                                    manage=True, action="remove documents")
    try:
        return await batch_files.delete_document(
            db, batch, document_id, current_user,
            actor_role="Faculty", source="Faculty Portal")
    except batch_files.BatchFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/batches/{identifier}/base-paper", status_code=status.HTTP_201_CREATED)
async def upload_batch_base_paper(
    identifier: str,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Attach the primary paper's PDF. Replacing it resets verification."""
    _, batch = await _require_batch(db, identifier, current_user,
                                    manage=True, action="upload a base paper")
    try:
        return await batch_files.upload_base_paper(
            db, batch, file, current_user, title=title,
            actor_role="Faculty", source="Faculty Portal")
    except batch_files.BatchFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/batches/{identifier}/base-paper/download")
async def download_batch_base_paper(
    identifier: str,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Send the base paper PDF."""
    _, batch = await _require_batch(db, identifier, current_user)
    try:
        paper, content = await batch_files.base_paper_for_download(db, batch)
    except batch_files.BatchFileError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return StreamingResponse(
        iter([content]),
        media_type=paper.file.mime_type,
        headers=file_store.download_headers(paper.file, paper.file_name),
    )


# ============================================
# Stage deliverables
# ============================================


class SubmissionDecisionBody(BaseModel):
    decision: str = Field(..., description="verify | reject")
    note: Optional[str] = Field(None, max_length=2000)


@router.get("/batches/{identifier}/submissions")
async def list_submissions(
    identifier: str,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """What the batch has handed in, and what is still expected of them."""
    _, batch = await _require_batch(db, identifier, current_user)
    rows = await submissions.load(db, batch.id)
    can_manage = getattr(batch, "_can_manage", False)
    return {
        "batch_code": batch.batch_code,
        "rows": [submissions.row(s, can_manage=can_manage) for s in rows],
        "pending": sum(1 for s in rows
                       if s.status.value == "pending" and s.superseded_by_id is None),
        "overall_progress": int(round(batch.overall_progress or 0)),
        "can_manage": can_manage,
        **submissions.options(rows),
    }


@router.post("/batches/{identifier}/submissions/{submission_id}/decide")
async def decide_submission(
    identifier: str,
    submission_id: str,
    body: SubmissionDecisionBody,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a deliverable or send it back with a reason.

    Accepting completes the stage it belongs to, which is what moves the
    batch's tracked progress.
    """
    _, batch = await _require_batch(db, identifier, current_user,
                                    manage=True, action="review submissions")
    try:
        return await submissions.decide(
            db, batch, submission_id, body.decision, current_user,
            note=body.note, actor_role="Faculty", source="Faculty Portal")
    except submissions.SubmissionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/batches/{identifier}/submissions", status_code=status.HTTP_201_CREATED)
async def submit_for_batch(
    identifier: str,
    document_type: str = Form(...),
    file: Optional[UploadFile] = File(None),
    link: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Hand something in on a team's behalf - a guide filing work collected offline."""
    _, batch = await _require_batch(db, identifier, current_user,
                                    manage=True, action="submit work")
    try:
        return await submissions.submit(
            db, batch, current_user, document_type=document_type, upload=file,
            link=link, title=title, actor_role="Faculty", source="Faculty Portal")
    except submissions.SubmissionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/batches/{identifier}/submissions/{submission_id}/download")
async def download_submission(
    identifier: str,
    submission_id: str,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Send a submitted file."""
    _, batch = await _require_batch(db, identifier, current_user)
    try:
        submission, content = await submissions.for_download(db, batch, submission_id)
    except submissions.SubmissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return StreamingResponse(
        iter([content]),
        media_type=submission.file.mime_type,
        headers=file_store.download_headers(submission.file),
    )


# ============================================
# Taking attendance
# ============================================


class AttendanceMarkBody(BaseModel):
    department: str
    section: Optional[str] = None
    year: Optional[str] = None
    date: Optional[str] = None
    # Absent means the session the clock is nearest, which is what a trainer
    # marking at the time of the class actually wants.
    session: Optional[str] = None
    academic_year: Optional[str] = None
    marks: List[dict] = Field(..., min_length=1, max_length=400)


@router.get("/attendance/roster")
async def attendance_roster(
    department: str = Query(..., description="Department code, e.g. CSE"),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    date: Optional[str] = Query(None, description="YYYY-MM-DD, default today"),
    session: Optional[str] = Query(None, description="forenoon | afternoon"),
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    The register for one section in one session.

    Same rule as taking it: attendance is a departmental record, and the
    people entitled to read a section's register are the ones entitled to
    correct it. A separate read rule would resolve to the same set today and
    quietly become a lie the first time either changed.
    """
    resolved = academic_year or _default_academic_year()
    if not await FacultyAuthority(db).can_act_for_department(
        current_user, department, resolved
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not attached to {department}.",
        )
    try:
        day = attendance_service.parse_day(date)
        return await attendance_service.AttendanceService(db).roster(
            department=department, year=year, section=section,
            academic_year=resolved, on=day,
            session=attendance_service.parse_session(session),
        )
    except attendance_service.AttendanceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/attendance/mark")
async def attendance_mark(
    body: AttendanceMarkBody,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Record the register for a day. Saving the same day again corrects it."""
    resolved = body.academic_year or _default_academic_year()
    if not await FacultyAuthority(db).can_act_for_department(
        current_user, body.department, resolved
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not attached to {body.department}, so you cannot take "
                   "attendance for it.",
        )
    try:
        day = attendance_service.parse_day(body.date)
        return await attendance_service.AttendanceService(db).mark(
            current_user, department=body.department, year=body.year,
            section=body.section, academic_year=resolved, on=day, marks=body.marks,
            session=attendance_service.parse_session(body.session),
        )
    except attendance_service.AttendanceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/attendance/student/{student_id}")
async def attendance_for_student(
    student_id: str,
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """One student's register, for the conversation about why a rate is low."""
    resolved = academic_year or _default_academic_year()
    student = (await db.execute(
        select(User).where(User.id == student_id).where(User.role == UserRole.STUDENT)
    )).scalar_one_or_none()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    enrollment = (await db.execute(
        select(StudentEnrollment)
        .where(StudentEnrollment.college_id == tenant_of(current_user))
        .where(StudentEnrollment.student_id == student.id)
        .where(StudentEnrollment.academic_year == resolved)
    )).scalar_one_or_none()
    department = enrollment.department if enrollment else None
    if department and not await FacultyAuthority(db).can_act_for_department(
        current_user, department, resolved
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="That student is in a department you are not attached to.",
        )

    payload = await attendance_service.AttendanceService(db).for_student(student, resolved)
    payload["student"] = {
        "id": str(student.id),
        "full_name": student.full_name,
        "roll_number": student.roll_number,
        "department": department,
        "section": enrollment.section if enrollment else None,
    }
    return payload


# ============================================
# Scheduling reviews
# ============================================


class ScheduleReviewBody(BaseModel):
    review_type: str
    date: str
    time: str
    reviewer_id: Optional[str] = None
    slot_minutes: int = Field(review_scheduling.DEFAULT_SLOT_MINUTES, ge=5, le=240)


class ScheduleRoundBody(BaseModel):
    department: str
    year: Optional[str] = None
    section: Optional[str] = None
    academic_year: Optional[str] = None
    review_type: str
    date: str
    start_time: str
    slot_minutes: int = Field(review_scheduling.DEFAULT_SLOT_MINUTES, ge=5, le=240)
    reviewer_id: Optional[str] = None
    # Given when a coordinator wants some of the cohort rather than all of it.
    batch_codes: Optional[List[str]] = None


class ReviewOutcomeBody(BaseModel):
    score: Optional[float] = None
    remarks: Optional[str] = Field(None, max_length=2000)


class RescheduleBody(BaseModel):
    date: str
    time: str


class CancelReviewBody(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)


@router.get("/reviews/options")
async def review_options(
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Review types, who can take one, and the defaults a booking starts from."""
    resolved = academic_year or _default_academic_year()
    return await review_scheduling.ReviewScheduler(db, tenant_of(current_user)).options(resolved)


@router.get("/reviews/schedule")
async def review_schedule(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    reviewer_id: Optional[str] = Query(None),
    date: Optional[str] = Query(None, description="One local day, YYYY-MM-DD"),
    include_past: bool = Query(False),
    limit: int = Query(200, ge=1, le=500),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """The review calendar, with what has already slipped."""
    resolved = academic_year or _default_academic_year()
    try:
        return await review_scheduling.ReviewScheduler(db, tenant_of(current_user)).agenda(
            academic_year=resolved, department=department, section=section,
            reviewer_id=reviewer_id, day=date, include_past=include_past, limit=limit,
        )
    except review_scheduling.SchedulingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/reviews/cohort-preview")
async def review_cohort_preview(
    department: str = Query(...),
    review_type: str = Query(...),
    year: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Which batches a round would cover, and which are already booked."""
    resolved = academic_year or _default_academic_year()
    if not await FacultyAuthority(db).can_act_for_department(
        current_user, department, resolved
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"You are not attached to {department}.")
    try:
        return await review_scheduling.ReviewScheduler(db, tenant_of(current_user)).cohort_preview(
            department=department, year=year, section=section,
            academic_year=resolved, review_type=review_type,
        )
    except review_scheduling.SchedulingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/reviews/round", status_code=status.HTTP_201_CREATED)
async def schedule_review_round(
    body: ScheduleRoundBody,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Book a review for every batch in a cohort, back to back.

    The primary way reviews get scheduled: a coordinator books a section, not a
    batch. Times are local wall clock and are stored as UTC.
    """
    resolved = body.academic_year or _default_academic_year()
    if not await FacultyAuthority(db).can_act_for_department(
        current_user, body.department, resolved
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not attached to {body.department}, so you cannot "
                   "schedule reviews in it.",
        )
    try:
        return await review_scheduling.ReviewScheduler(db, tenant_of(current_user)).schedule_round(
            current_user, department=body.department, year=body.year,
            section=body.section, academic_year=resolved,
            review_type=body.review_type, day=body.date, start_time=body.start_time,
            slot_minutes=body.slot_minutes, reviewer_id=body.reviewer_id,
            batch_codes=body.batch_codes,
        )
    except review_scheduling.SchedulingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/batches/{identifier}/reviews", status_code=status.HTTP_201_CREATED)
async def schedule_batch_review(
    identifier: str,
    body: ScheduleReviewBody,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Book one review for one batch."""
    _, batch = await _require_batch(db, identifier, current_user,
                                    manage=True, action="schedule reviews")
    try:
        return await review_scheduling.ReviewScheduler(db, tenant_of(current_user)).schedule(
            current_user, batch, review_type=body.review_type, day=body.date,
            at=body.time, reviewer_id=body.reviewer_id, slot_minutes=body.slot_minutes,
        )
    except review_scheduling.SchedulingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/batches/{identifier}/reviews")
async def batch_reviews(
    identifier: str,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Every review this batch has had or has coming."""
    _, batch = await _require_batch(db, identifier, current_user)
    scheduler = review_scheduling.ReviewScheduler(db, tenant_of(current_user))
    reviewers = {
        str(r.id): r for r in (await db.execute(
            select(User).where(User.role.in_(COLLEGE_STAFF_ROLES))
        )).scalars().all()
    }
    rows = sorted(batch.reviews, key=lambda r: r.scheduled_at, reverse=True)
    return {
        "batch_code": batch.batch_code,
        "items": [
            scheduler.row(r, batch.batch_code, reviewers.get(str(r.reviewer_id)))
            for r in rows
        ],
        "can_manage": getattr(batch, "_can_manage", False),
        "review_types": review_scheduling.REVIEW_TYPES,
    }


@router.post("/batches/{identifier}/reviews/{review_id}/complete")
async def faculty_complete_review(
    identifier: str,
    review_id: str,
    body: ReviewOutcomeBody,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Record that a review happened, with its score and remarks."""
    _, batch = await _require_batch(db, identifier, current_user,
                                    manage=True, action="complete reviews")
    try:
        return await complete_review(db, batch, review_id, current_user,
                                     score=body.score, remarks=body.remarks)
    except ActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/batches/{identifier}/reviews/{review_id}/reschedule")
async def faculty_reschedule_review(
    identifier: str,
    review_id: str,
    body: RescheduleBody,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Move a scheduled review to another local date and time."""
    _, batch = await _require_batch(db, identifier, current_user,
                                    manage=True, action="reschedule reviews")
    try:
        when = review_scheduling.parse_when(body.date, body.time)
        return await reschedule_review(db, batch, review_id, when)
    except review_scheduling.SchedulingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/batches/{identifier}/reviews/{review_id}/cancel")
async def faculty_cancel_review(
    identifier: str,
    review_id: str,
    body: CancelReviewBody,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a scheduled review. A reason is required."""
    _, batch = await _require_batch(db, identifier, current_user,
                                    manage=True, action="cancel reviews")
    try:
        return await cancel_review(db, batch, review_id, body.reason)
    except ActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


class BasePaperDecisionBody(BaseModel):
    decision: str = Field(..., description="verify | request_changes")
    note: Optional[str] = Field(None, max_length=2000)


@router.post("/batches/{identifier}/base-paper/decide")
async def decide_batch_base_paper(
    identifier: str,
    body: BasePaperDecisionBody,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify the base paper, or send it back.

    The approval checklist will not pass without this, so until it existed no
    batch registered through the app could be approved at all.
    """
    _, batch = await _require_batch(db, identifier, current_user,
                                    manage=True, action="verify a base paper")
    try:
        return await decide_base_paper(db, batch, body.decision, current_user, note=body.note)
    except ActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ==========================================================================
# Project Tracking
#
# One screen at three zoom levels - the cohort, the filtered table, and one
# project in full - so the reads share a single service and therefore a single
# definition of phase and health. The writes live in TrackerActions, which goes
# through FacultyAuthority like the rest of the portal.
# ==========================================================================

class TaskIn(BaseModel):
    title: str
    detail: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[str] = None


class TaskPatch(BaseModel):
    title: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None
    blocked_reason: Optional[str] = None


class DeliverablePatch(BaseModel):
    progress: Optional[int] = None
    status: Optional[str] = None
    evidence_url: Optional[str] = None


class IntegrationIn(BaseModel):
    kind: str
    state: str
    detail: Optional[str] = None
    url: Optional[str] = None


class MilestoneIn(BaseModel):
    stage: str
    planned_date: Optional[str] = None
    percent: Optional[float] = None


def _tracker(db: AsyncSession, current_user: User) -> ProjectTracker:
    return ProjectTracker(db, tenant_of(current_user))


def _tracker_actions(db: AsyncSession, current_user: User) -> TrackerActions:
    return TrackerActions(db, tenant_of(current_user))


@router.get("/tracking")
async def tracking_overview(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    guide_id: Optional[str] = Query(None),
    phase: Optional[str] = Query(None),
    health: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    mine: bool = Query(False, description="Only batches this person guides"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Counters and the project table, filtered."""
    resolved = academic_year or _default_academic_year()
    if mine:
        guide_id = str(current_user.id)
    return await _tracker(db, current_user).overview(
        resolved, department=department, section=section, year=year,
        semester=semester, guide_id=guide_id, phase=phase, health=health,
        search=search,
        page=page, per_page=per_page,
    )


@router.get("/tracking/alerts")
async def tracking_alerts(
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """The alert counters and what is coming up across the cohort."""
    resolved = academic_year or _default_academic_year()
    return await _tracker(db, current_user).alerts(resolved)


@router.get("/tracking/{identifier}")
async def tracking_detail(
    identifier: str,
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """One project: team, integrations, milestones, tasks, deliverables, activity."""
    resolved = academic_year or _default_academic_year()
    detail = await _tracker(db, current_user).detail(identifier, resolved)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No batch found with the code {identifier}.")
    return detail


@router.post("/tracking/{identifier}/tasks", status_code=status.HTTP_201_CREATED)
async def tracking_add_task(
    identifier: str,
    body: TaskIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _tracker_actions(db, current_user).add_task(
            current_user, identifier, body.model_dump())
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/tracking/tasks/{task_id}")
async def tracking_update_task(
    task_id: str,
    body: TaskPatch,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    # Only the fields actually sent are touched, so a status change cannot
    # silently clear a due date the caller never mentioned.
    payload = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    try:
        return await _tracker_actions(db, current_user).update_task(
            current_user, task_id, payload)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/tracking/deliverables/{deliverable_id}")
async def tracking_set_deliverable(
    deliverable_id: str,
    body: DeliverablePatch,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    payload = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    try:
        return await _tracker_actions(db, current_user).set_deliverable(
            current_user, deliverable_id, payload)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/tracking/{identifier}/integrations")
async def tracking_set_integration(
    identifier: str,
    body: IntegrationIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _tracker_actions(db, current_user).set_integration(
            current_user, identifier, body.model_dump())
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/tracking/{identifier}/milestones")
async def tracking_set_milestone(
    identifier: str,
    body: MilestoneIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    payload = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    try:
        return await _tracker_actions(db, current_user).set_milestone(
            current_user, identifier, payload)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


class BulkUpdateIn(BaseModel):
    batch_codes: List[str]
    note: Optional[str] = ""


class BulkMilestoneIn(BaseModel):
    batch_codes: List[str]
    stage: str
    planned_date: str


def _tracking_filters(department, section, year, semester, guide_id):
    return {k: v for k, v in {
        "department": department, "section": section, "year": year,
        "semester": semester, "guide_id": guide_id,
    }.items() if v}


@router.get("/tracking-views/milestones")
async def tracking_milestones(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    guide_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Every unfinished milestone in the cohort, overdue first."""
    return await _tracker(db, current_user).milestones(
        academic_year or _default_academic_year(),
        **_tracking_filters(department, section, year, semester, guide_id))


@router.get("/tracking-views/tasks")
async def tracking_tasks(
    academic_year: Optional[str] = Query(None),
    only_open: bool = Query(True),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    guide_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Every task, blocked first, then overdue."""
    return await _tracker(db, current_user).tasks(
        academic_year or _default_academic_year(), only_open=only_open,
        **_tracking_filters(department, section, year, semester, guide_id))


@router.get("/tracking-views/deliverables")
async def tracking_deliverables(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    guide_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Every deliverable, least finished first."""
    return await _tracker(db, current_user).deliverables(
        academic_year or _default_academic_year(),
        **_tracking_filters(department, section, year, semester, guide_id))


@router.get("/tracking-views/activity")
async def tracking_activity(
    academic_year: Optional[str] = Query(None),
    limit: int = Query(60, ge=1, le=200),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    guide_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """The cohort's activity feed."""
    return await _tracker(db, current_user).activity(
        academic_year or _default_academic_year(), limit=limit,
        **_tracking_filters(department, section, year, semester, guide_id))


@router.get("/tracking-views/insight")
async def tracking_insight(
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """The summary line, derived from the data rather than generated."""
    return await _tracker(db, current_user).insight(
        academic_year or _default_academic_year())


@router.get("/tracking-views/export.csv")
async def tracking_export(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    guide_id: Optional[str] = Query(None),
    phase: Optional[str] = Query(None),
    health: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """
    The tracker as a spreadsheet.

    Exports what the filters currently show, not everything - a coordinator
    who has narrowed to one section expects that section, and silently handing
    back the whole cohort is how the wrong list gets forwarded.
    """
    import csv
    import io as _io

    resolved = academic_year or _default_academic_year()
    data = await _tracker(db, current_user).overview(
        resolved, department=department, section=section, year=year,
        semester=semester, guide_id=guide_id, phase=phase, health=health,
        search=search, page=1, per_page=1000,
    )

    buffer = _io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Batch Code", "Project", "Guide", "Section", "Members", "Phase",
        "Progress %", "Expected %", "Schedule", "Milestones Done", "Tasks Done",
        "Overdue Tasks", "Blocked Tasks", "Deliverables Verified",
        "Next Due", "Last Activity", "Health", "Reasons",
    ])
    for r in data["rows"]:
        writer.writerow([
            r["batch_code"], r["title"] or "", r["guide_name"] or "Not assigned",
            r["section"] or "", f"{r['active_members']}/{r['member_count']}",
            r["current_phase"], r["progress"],
            "" if r["expected_progress"] is None else r["expected_progress"],
            r["schedule_state"],
            f"{r['milestones_done']}/{r['milestones_total']}",
            f"{r['tasks_done']}/{r['tasks_total']}",
            r["overdue_tasks"], r["blocked_tasks"],
            f"{r['deliverables_done']}/{r['deliverables_total']}",
            (r["next_due"] or {}).get("display", ""),
            r["last_activity"] or "", r["health"], "; ".join(r["reasons"]),
        ])
    buffer.seek(0)
    filename = f"project-tracker-{resolved}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/tracking/request-update")
async def tracking_request_update(
    body: BulkUpdateIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Ask the selected teams for a progress update."""
    try:
        return await _tracker_actions(db, current_user).request_update(
            current_user, body.batch_codes, body.note or "")
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/tracking/bulk-milestone")
async def tracking_bulk_milestone(
    body: BulkMilestoneIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Give one stage the same planned date across the selected projects."""
    try:
        return await _tracker_actions(db, current_user).add_milestone_date(
            current_user, body.batch_codes, body.stage, body.planned_date)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ==========================================================================
# Tasks & Blockers
#
# A different unit from the tracker: there the row is a project, here it is a
# task or a blocker, and the person working this screen is chasing people
# rather than reviewing progress.
# ==========================================================================

class BlockerIn(BaseModel):
    title: str
    root_cause: str
    category: str = "technical"
    severity: str = "medium"
    impact: Optional[str] = None
    task_id: Optional[str] = None
    resolution_owner_id: Optional[str] = None
    target_resolution: Optional[str] = None


class BlockerAssignIn(BaseModel):
    owner_id: str
    target_resolution: Optional[str] = None


class BlockerNoteIn(BaseModel):
    note: str = ""


class BulkTaskEditIn(BaseModel):
    task_ids: List[str]
    assignee_id: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None


class CommentIn(BaseModel):
    body: str


class DependencyIn(BaseModel):
    depends_on_id: str


def _board(db: AsyncSession, current_user: User) -> TaskBoard:
    return TaskBoard(db, tenant_of(current_user))


def _blocker_actions(db: AsyncSession, current_user: User) -> BlockerActions:
    return BlockerActions(db, tenant_of(current_user))


def _board_filters(**kwargs):
    return {k: v for k, v in kwargs.items() if v not in (None, "", False)}


@router.get("/tasks/board")
async def tasks_board(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    batch_code: Optional[str] = Query(None),
    guide_id: Optional[str] = Query(None),
    assignee_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    task_status: Optional[str] = Query(None, alias="status"),
    due: Optional[str] = Query(None, description="overdue, today or week"),
    unassigned: bool = Query(False),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Counters, the four board columns, and the register."""
    return await _board(db, current_user).board(
        academic_year or _default_academic_year(),
        **_board_filters(
            department=department, section=section, year=year, semester=semester,
            batch_code=batch_code, guide_id=guide_id, assignee_id=assignee_id,
            priority=priority, status=task_status, due=due,
            unassigned=unassigned, search=search))


@router.get("/tasks/blockers")
async def tasks_blockers(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    batch_code: Optional[str] = Query(None),
    guide_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """The resolution queue, category analysis and SLA figures."""
    return await _board(db, current_user).blockers(
        academic_year or _default_academic_year(),
        **_board_filters(department=department, section=section,
                         batch_code=batch_code, guide_id=guide_id))


@router.get("/tasks/workload")
async def tasks_workload(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    guide_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Per-student load, and which batches carry the overdue work."""
    return await _board(db, current_user).workload(
        academic_year or _default_academic_year(),
        **_board_filters(department=department, section=section, guide_id=guide_id))


@router.get("/tasks/insight")
async def tasks_insight(
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """What the open blockers are actually holding up."""
    return await _board(db, current_user).insight(
        academic_year or _default_academic_year())


@router.post("/tasks/{identifier}/blockers", status_code=status.HTTP_201_CREATED)
async def report_blocker(
    identifier: str,
    body: BlockerIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _blocker_actions(db, current_user).report(
            current_user, identifier, body.model_dump())
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/tasks/blockers/{blocker_id}/assign")
async def assign_blocker(
    blocker_id: str,
    body: BlockerAssignIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _blocker_actions(db, current_user).assign(
            current_user, blocker_id, body.owner_id, body.target_resolution)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/tasks/blockers/{blocker_id}/escalate")
async def escalate_blocker(
    blocker_id: str,
    body: BlockerNoteIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _blocker_actions(db, current_user).escalate(
            current_user, blocker_id, body.note)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/tasks/blockers/{blocker_id}/resolve")
async def resolve_blocker(
    blocker_id: str,
    body: BlockerNoteIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _blocker_actions(db, current_user).resolve(
            current_user, blocker_id, body.note)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/tasks/bulk-edit")
async def bulk_task_edit(
    body: BulkTaskEditIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Assign, re-prioritise, re-date or complete several tasks at once."""
    payload = body.model_dump(exclude_unset=True)
    payload.pop("task_ids", None)
    try:
        return await _blocker_actions(db, current_user).bulk_task_edit(
            current_user, body.task_ids, payload)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/tasks/{task_id}/comments", status_code=status.HTTP_201_CREATED)
async def comment_on_task(
    task_id: str,
    body: CommentIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _blocker_actions(db, current_user).comment(
            current_user, task_id, body.body)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/tasks/{task_id}/dependencies", status_code=status.HTTP_201_CREATED)
async def add_task_dependency(
    task_id: str,
    body: DependencyIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _blocker_actions(db, current_user).add_dependency(
            current_user, task_id, body.depends_on_id)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ==========================================================================
# Milestones
#
# A third unit again: the tracker's row is a project, the task board's is a
# task, and here it is a milestone. This screen answers "what will slip" and
# "what is waiting on my signature".
# ==========================================================================

class MilestoneIn(BaseModel):
    name: str
    detail: Optional[str] = None
    stage: Optional[str] = None
    priority: str = "medium"
    owner_id: Optional[str] = None
    reviewer_id: Optional[str] = None
    planned_start: Optional[str] = None
    planned_date: Optional[str] = None
    forecast_date: Optional[str] = None
    checklist: Optional[List[str]] = None


class MilestonePatch(BaseModel):
    progress: Optional[int] = None
    planned_date: Optional[str] = None
    forecast_date: Optional[str] = None
    priority: Optional[str] = None
    owner_id: Optional[str] = None
    blocked: Optional[bool] = None


class ReviewNoteIn(BaseModel):
    note: str = ""


class EvidenceRequestIn(BaseModel):
    milestone_ids: List[str]
    label: str = "Evidence"


class EvidenceVerifyIn(BaseModel):
    accept: bool = True


class ChecklistIn(BaseModel):
    done: bool


class MilestoneDependencyIn(BaseModel):
    depends_on_id: str


def _milestones(db: AsyncSession, current_user: User) -> MilestoneBoard:
    return MilestoneBoard(db, tenant_of(current_user))


def _milestone_actions(db: AsyncSession, current_user: User) -> MilestoneActions:
    return MilestoneActions(db, tenant_of(current_user))


@router.get("/milestones/board")
async def milestones_board(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    batch_code: Optional[str] = Query(None),
    guide_id: Optional[str] = Query(None),
    milestone: Optional[str] = Query(None),
    milestone_status: Optional[str] = Query(None, alias="status"),
    approval: Optional[str] = Query(None),
    due_from: Optional[str] = Query(None),
    due_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Counters, the tracker grouped by batch, and the details table."""
    return await _milestones(db, current_user).board(
        academic_year or _default_academic_year(),
        page=page, per_page=per_page,
        **_board_filters(
            department=department, section=section, year=year, semester=semester,
            batch_code=batch_code, guide_id=guide_id, milestone=milestone,
            status=milestone_status, approval=approval,
            due_from=due_from, due_to=due_to))


@router.get("/milestones/queue")
async def milestones_queue(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    batch_code: Optional[str] = Query(None),
    guide_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Approval queue, upcoming deadlines, health split and dependency alerts."""
    return await _milestones(db, current_user).queue(
        academic_year or _default_academic_year(),
        **_board_filters(department=department, section=section,
                         batch_code=batch_code, guide_id=guide_id))


@router.get("/milestones/insight")
async def milestones_insight(
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Which milestones are likely to miss, and what to clear first."""
    return await _milestones(db, current_user).insight(
        academic_year or _default_academic_year())


@router.get("/milestones/recovery-plan")
async def milestone_recovery_plan(
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    batch_code: Optional[str] = Query(None),
    guide_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """The order to clear the slipping milestones in, derived from the graph."""
    return await _milestones(db, current_user).recovery_plan(
        academic_year or _default_academic_year(),
        **_board_filters(department=department, section=section,
                         batch_code=batch_code, guide_id=guide_id))


@router.get("/milestones/{milestone_id}")
async def milestone_detail(
    milestone_id: str,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """One milestone: checklist, evidence, dependencies and activity."""
    found = await _milestones(db, current_user).detail(milestone_id)
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="That milestone no longer exists.")
    return found


@router.post("/milestones/{identifier}", status_code=status.HTTP_201_CREATED)
async def add_milestone(
    identifier: str,
    body: MilestoneIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _milestone_actions(db, current_user).add(
            current_user, identifier, body.model_dump())
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/milestones/{milestone_id}")
async def update_milestone(
    milestone_id: str,
    body: MilestonePatch,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _milestone_actions(db, current_user).update(
            current_user, milestone_id, body.model_dump(exclude_unset=True))
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/milestones/{milestone_id}/submit")
async def submit_milestone(
    milestone_id: str,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _milestone_actions(db, current_user).submit_for_review(
            current_user, milestone_id)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/milestones/{milestone_id}/approve")
async def approve_milestone(
    milestone_id: str,
    body: ReviewNoteIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _milestone_actions(db, current_user).approve(
            current_user, milestone_id, body.note)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/milestones/{milestone_id}/request-changes")
async def request_milestone_changes(
    milestone_id: str,
    body: ReviewNoteIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _milestone_actions(db, current_user).request_changes(
            current_user, milestone_id, body.note)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


class MilestoneBulkIn(BaseModel):
    milestone_ids: List[str]
    action: str
    value: Optional[str] = None


@router.post("/milestones/bulk")
async def bulk_milestones(
    body: MilestoneBulkIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Approve, re-date or chase the selected milestones."""
    try:
        return await _milestone_actions(db, current_user).bulk(
            current_user, body.milestone_ids, body.action, body.value)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/milestones/request-evidence")
async def request_milestone_evidence(
    body: EvidenceRequestIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Ask the selected milestones for a named piece of evidence."""
    try:
        return await _milestone_actions(db, current_user).request_evidence(
            current_user, body.milestone_ids, body.label)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/milestones/evidence/{evidence_id}/verify")
async def verify_milestone_evidence(
    evidence_id: str,
    body: EvidenceVerifyIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _milestone_actions(db, current_user).verify_evidence(
            current_user, evidence_id, body.accept)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/milestones/checklist/{item_id}")
async def toggle_milestone_checklist(
    item_id: str,
    body: ChecklistIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _milestone_actions(db, current_user).toggle_checklist(
            current_user, item_id, body.done)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/milestones/{milestone_id}/dependencies",
             status_code=status.HTTP_201_CREATED)
async def add_milestone_dependency(
    milestone_id: str,
    body: MilestoneDependencyIn,
    current_user: User = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _milestone_actions(db, current_user).add_dependency(
            current_user, milestone_id, body.depends_on_id)
    except TrackerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
