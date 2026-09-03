"""
Faculty Dashboard Service - aggregates the faculty portal's dashboard payload.

One entry point, `build_dashboard`, so the screen costs a single round trip
instead of a dozen. Every figure is computed from the filtered set of batches
and enrollments; nothing is cached.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Sequence

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.faculty import (
    AttendanceRecord,
    AttendanceStatus,
    BasePaper,
    BasePaperStatus,
    BatchStageProgress,
    ProjectBatch,
    ProjectBatchMember,
    ProjectReview,
    ProjectSubmission,
    ReviewStatus,
    STAGE_LABELS,
    STAGE_ORDER,
    StudentEnrollment,
    SubmissionStatus,
)
from app.models.user import User
from app.core.institution_time import local_today
from app.schemas.faculty import (
    AttendanceToday,
    AttentionItem,
    BasePaperRow,
    BasePaperSummary,
    FacultyDashboardResponse,
    FacultyProfile,
    FilterOptions,
    GuideOption,
    Kpi,
    ProjectRow,
    SectionRow,
    StagePoint,
    StageSummary,
    SubmissionsSummary,
    UpcomingReview,
    WorkloadSummary,
)
from app.services.project_schedule import (
    SCHEDULE_GRACE,
    describe,
    expected_progress,
    is_behind,
)

# A student under this attendance rate is flagged to the guide.
ATTENDANCE_FLOOR = 75.0

# Section grading. Overall progress averages all eight stages, so a healthy
# batch mid-year sits around 60-70%, not 90% - these thresholds are calibrated
# to that, not to a naive "80% = good".
PROGRESS_EXCELLENT, ATTENDANCE_EXCELLENT = 65, 90
PROGRESS_ON_TRACK, ATTENDANCE_ON_TRACK = 55, 80

# Sentinel used by the filter dropdowns for "no filter".
ALL_PREFIXES = ("all", "")


def _is_all(value: Optional[str]) -> bool:
    """True when a filter value means 'do not filter'."""
    if value is None:
        return True
    return value.strip().lower().startswith(ALL_PREFIXES[0]) or not value.strip()


def _pct(part: float, whole: float) -> Optional[int]:
    """Rounded percentage, or None when there is nothing to divide by."""
    if not whole:
        return None
    return int(round(part / whole * 100))



async def attendance_rates(
    db, student_ids: Sequence[str], academic_year: str
) -> Dict[str, float]:
    """
    Attendance rate per student across the academic year.

    Late counts as attended - the student was present, just not on time - so
    only ABSENT reduces the rate. Module level because the Departments &
    Sections screen reports the same number; two definitions would eventually
    disagree.
    """
    if not student_ids:
        return {}

    stmt = (
        select(
            AttendanceRecord.student_id,
            func.count().label("total"),
            func.sum(
                case((AttendanceRecord.status == AttendanceStatus.ABSENT, 1), else_=0)
            ).label("absent"),
        )
        .where(AttendanceRecord.student_id.in_(list(student_ids)))
        .where(AttendanceRecord.academic_year == academic_year)
        .group_by(AttendanceRecord.student_id)
    )
    rows = (await db.execute(stmt)).all()

    rates: Dict[str, float] = {}
    for student_id, total, absent in rows:
        if not total:
            continue
        rates[str(student_id)] = (total - (absent or 0)) / total * 100
    return rates


class FacultyDashboardService:
    def __init__(self, db: AsyncSession, college_id=None):
        self.db = db
        # The caller's college. Every query this service builds is
        # confined to it - see app/services/tenancy.py.
        self.college_id = college_id

    # ------------------------------------------------------------ filtering

    def _batch_filters(
        self,
        stmt,
        academic_year: str,
        department: Optional[str],
        section: Optional[str],
        year: Optional[str],
        semester: Optional[str],
        project_type: Optional[str],
        guide_id: Optional[str],
    ):
        # Confine every batch query to the caller's college. Without this the
        # dashboard hands an outsider another institution's project rows,
        # reviews, attendance totals and base-paper counts.
        if self.college_id:
            stmt = stmt.where(ProjectBatch.college_id == self.college_id)
        stmt = stmt.where(ProjectBatch.academic_year == academic_year)
        stmt = stmt.where(ProjectBatch.is_active.is_(True))
        if not _is_all(department):
            stmt = stmt.where(ProjectBatch.department == department)
        if not _is_all(section):
            stmt = stmt.where(ProjectBatch.section == section)
        if not _is_all(year):
            stmt = stmt.where(ProjectBatch.year == year)
        if not _is_all(semester):
            stmt = stmt.where(ProjectBatch.semester == semester)
        if not _is_all(project_type):
            stmt = stmt.where(ProjectBatch.project_type == project_type)
        if guide_id:
            stmt = stmt.where(ProjectBatch.guide_id == guide_id)
        return stmt

    def _enrollment_filters(
        self,
        stmt,
        academic_year: str,
        department: Optional[str],
        section: Optional[str],
        year: Optional[str],
        semester: Optional[str],
    ):
        if self.college_id:
            stmt = stmt.where(StudentEnrollment.college_id == self.college_id)
        stmt = stmt.where(StudentEnrollment.academic_year == academic_year)
        stmt = stmt.where(StudentEnrollment.is_active.is_(True))
        if not _is_all(department):
            stmt = stmt.where(StudentEnrollment.department == department)
        if not _is_all(section):
            stmt = stmt.where(StudentEnrollment.section == section)
        if not _is_all(year):
            stmt = stmt.where(StudentEnrollment.year == year)
        if not _is_all(semester):
            stmt = stmt.where(StudentEnrollment.semester == semester)
        return stmt

    # ------------------------------------------------------------ attendance

    async def _attendance_rates(
        self, student_ids: Sequence[str], academic_year: str
    ) -> Dict[str, float]:
        return await attendance_rates(self.db, student_ids, academic_year)

    # ----------------------------------------------------------------- build

    async def build_dashboard(
        self,
        current_user: User,
        academic_year: str,
        department: Optional[str] = None,
        section: Optional[str] = None,
        year: Optional[str] = None,
        semester: Optional[str] = None,
        project_type: Optional[str] = None,
        guide_id: Optional[str] = None,
    ) -> FacultyDashboardResponse:
        # The institution's today. On a UTC container an Indian evening would
        # otherwise be counted against the previous day.
        today = local_today()

        # --- batches in scope, with everything the panels need eager-loaded
        batch_stmt = select(ProjectBatch).options(
            selectinload(ProjectBatch.members),
            selectinload(ProjectBatch.stage_progress),
            selectinload(ProjectBatch.base_paper),
            selectinload(ProjectBatch.reviews),
        )
        batch_stmt = self._batch_filters(
            batch_stmt, academic_year, department, section, year, semester, project_type, guide_id
        )
        batches: List[ProjectBatch] = list((await self.db.execute(batch_stmt)).scalars().unique().all())
        batch_ids = [b.id for b in batches]

        # --- enrollments in scope
        enr_stmt = self._enrollment_filters(
            select(StudentEnrollment), academic_year, department, section, year, semester
        )
        enrollments: List[StudentEnrollment] = list((await self.db.execute(enr_stmt)).scalars().all())

        student_ids = [e.student_id for e in enrollments]
        attendance_rates = await self._attendance_rates(student_ids, academic_year)

        # --- stage progress, overall and per section
        stage_totals: Dict[str, List[float]] = defaultdict(list)
        stage_by_section: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        for batch in batches:
            sec = batch.section or "Unassigned"
            for sp in batch.stage_progress:
                key = sp.stage.value if hasattr(sp.stage, "value") else str(sp.stage)
                stage_totals[key].append(sp.percent or 0.0)
                stage_by_section[sec][key].append(sp.percent or 0.0)

        stages: List[StageSummary] = []
        for stage in STAGE_ORDER:
            values = stage_totals.get(stage.value, [])
            stages.append(
                StageSummary(
                    key=stage.value,
                    label=STAGE_LABELS[stage],
                    percent=int(round(sum(values) / len(values))) if values else 0,
                )
            )

        series_names = sorted(
            {b.section for b in batches if b.section},
            key=str,
        )
        progress_series: List[StagePoint] = []
        for stage in STAGE_ORDER:
            values: Dict[str, int] = {}
            for sec in series_names:
                per = stage_by_section.get(sec, {}).get(stage.value, [])
                if per:
                    values[sec] = int(round(sum(per) / len(per)))
            progress_series.append(StagePoint(stage=STAGE_LABELS[stage], values=values))

        # --- reviews
        pending_reviews = 0
        overdue_reviews = 0
        upcoming: List[ProjectReview] = []
        now = datetime.utcnow()
        for batch in batches:
            for review in batch.reviews:
                if review.status != ReviewStatus.SCHEDULED:
                    continue
                pending_reviews += 1
                if review.scheduled_at < now:
                    overdue_reviews += 1
                else:
                    upcoming.append(review)

        batch_by_id = {b.id: b for b in batches}
        upcoming.sort(key=lambda r: r.scheduled_at)
        upcoming_reviews = [
            UpcomingReview(
                id=str(r.id),
                date=r.scheduled_at.strftime("%d %b %Y"),
                time=r.scheduled_at.strftime("%I:%M %p").lstrip("0"),
                batch_code=batch_by_id[r.batch_id].batch_code if r.batch_id in batch_by_id else "",
                review_type=r.review_type,
                scheduled_at=r.scheduled_at,
            )
            for r in upcoming[:5]
        ]

        # --- base papers and inactive members
        missing_base_papers = 0
        base_paper_counts = {BasePaperStatus.VERIFIED: 0, BasePaperStatus.PENDING: 0, BasePaperStatus.MISSING: 0}
        inactive_member_batches = 0
        for batch in batches:
            bp = batch.base_paper
            status = bp.status if bp else BasePaperStatus.MISSING
            base_paper_counts[status] = base_paper_counts.get(status, 0) + 1
            if status == BasePaperStatus.MISSING:
                missing_base_papers += 1
            if any(not m.is_active for m in batch.members):
                inactive_member_batches += 1

        low_attendance_students = sum(1 for rate in attendance_rates.values() if rate < ATTENDANCE_FLOOR)

        # --- KPIs
        avg_progress_values = [b.overall_progress or 0.0 for b in batches]
        avg_progress = int(round(sum(avg_progress_values) / len(avg_progress_values))) if avg_progress_values else 0
        avg_attendance = (
            int(round(sum(attendance_rates.values()) / len(attendance_rates))) if attendance_rates else 0
        )

        # A batch "needs attention" if it is behind, overdue, missing its base
        # paper, or has dropped a member - the same rule the table below uses.
        project_rows = self._build_project_rows(batches, now)

        kpis = [
            Kpi(id="students", value=str(len(enrollments)), label="Registered Students"),
            Kpi(id="batches", value=str(len(batches)), label="Project Batches"),
            Kpi(id="progress", value=f"{avg_progress}%", label="Average Progress"),
            Kpi(id="attendance", value=f"{avg_attendance}%", label="Average Attendance"),
            Kpi(id="reviews", value=str(pending_reviews), label="Reviews Pending"),
            Kpi(id="attention", value=str(len(project_rows)), label="Need Attention"),
        ]

        attention_items = [
            AttentionItem(id="attendance", label=f"Students below {int(ATTENDANCE_FLOOR)}% attendance", count=low_attendance_students),
            AttentionItem(id="base-papers", label="Batches missing base papers", count=missing_base_papers),
            AttentionItem(id="overdue", label="Reviews overdue", count=overdue_reviews),
            AttentionItem(id="inactive", label="Batches with inactive members", count=inactive_member_batches),
        ]

        section_rows = self._build_section_rows(enrollments, batches, attendance_rates, now)

        # --- today's attendance across the filtered students
        attendance_today = AttendanceToday()
        if student_ids:
            today_stmt = (
                select(AttendanceRecord.status, func.count())
                .where(AttendanceRecord.student_id.in_(student_ids))
                .where(AttendanceRecord.attendance_date == today)
                .group_by(AttendanceRecord.status)
            )
            for status, count in (await self.db.execute(today_stmt)).all():
                if status == AttendanceStatus.PRESENT:
                    attendance_today.present = count
                elif status == AttendanceStatus.ABSENT:
                    attendance_today.absent = count
                elif status == AttendanceStatus.LATE:
                    attendance_today.late = count

        # --- submissions awaiting verification
        pending_submissions = 0
        if batch_ids:
            sub_stmt = (
                select(func.count())
                .select_from(ProjectSubmission)
                .where(ProjectSubmission.batch_id.in_(batch_ids))
                .where(ProjectSubmission.status == SubmissionStatus.PENDING)
            )
            pending_submissions = (await self.db.execute(sub_stmt)).scalar() or 0

        # --- this faculty member's own workload, independent of the filters
        workload = await self._build_workload(current_user, academic_year, now)

        return FacultyDashboardResponse(
            faculty=FacultyProfile(
                name=current_user.full_name or current_user.email.split("@")[0],
                department=current_user.department,
                sections=self._describe_sections(series_names),
                academic_year=academic_year,
            ),
            filters_applied={
                "department": department,
                "section": section,
                "year": year,
                "semester": semester,
                "project_type": project_type,
                "academic_year": academic_year,
            },
            kpis=kpis,
            stages=stages,
            progress_series=progress_series,
            series_names=list(series_names),
            attention_items=attention_items,
            upcoming_reviews=upcoming_reviews,
            section_rows=section_rows,
            project_rows=project_rows,
            attendance_today=attendance_today,
            recent_submissions=SubmissionsSummary(count=pending_submissions),
            faculty_workload=workload,
            base_paper_status=BasePaperSummary(
                rows=[
                    BasePaperRow(count=base_paper_counts.get(BasePaperStatus.VERIFIED, 0), label="Verified"),
                    BasePaperRow(count=base_paper_counts.get(BasePaperStatus.PENDING, 0), label="Pending"),
                    BasePaperRow(count=base_paper_counts.get(BasePaperStatus.MISSING, 0), label="Missing"),
                ]
            ),
            ai_insight=self._build_insight(section_rows),
        )

    # ------------------------------------------------------------- fragments

    @staticmethod
    def _describe_sections(sections: Sequence[str]) -> Optional[str]:
        """"Sections A–C" for a contiguous run, otherwise a plain list."""
        if not sections:
            return None
        if len(sections) == 1:
            return f"Section {sections[0]}"
        return f"Sections {sections[0]}–{sections[-1]}"

    def _build_project_rows(self, batches: List[ProjectBatch], now: datetime) -> List[ProjectRow]:
        """Batches with at least one problem, worst progress first."""
        rows: List[ProjectRow] = []
        for batch in batches:
            issues: List[str] = []

            inactive = sum(1 for m in batch.members if not m.is_active)
            if inactive:
                issues.append("Missing member" if inactive == 1 else f"{inactive} missing members")

            bp = batch.base_paper
            if bp is None or bp.status == BasePaperStatus.MISSING:
                issues.append("base paper")

            overdue = [
                r for r in batch.reviews
                if r.status == ReviewStatus.SCHEDULED and r.scheduled_at < now
            ]
            if overdue:
                issues.append("Review overdue" if len(overdue) == 1 else f"{len(overdue)} reviews overdue")

            progress = int(round(batch.overall_progress or 0.0))
            # Judged against this batch's own timeline - see project_schedule.
            expected = expected_progress(batch.start_date, batch.target_completion)
            behind = is_behind(batch.overall_progress, expected)
            if not issues and not behind:
                continue

            if issues:
                # "Missing member & base paper" reads better than a comma list.
                issue_text = " & ".join(issues) if len(issues) <= 2 else ", ".join(issues)
            else:
                issue_text = describe(batch.overall_progress, expected)

            # Far enough under the line to be more than ordinary drift.
            far_behind = (
                expected is not None
                and (batch.overall_progress or 0.0) < expected - (SCHEDULE_GRACE * 2)
            )
            at_risk = far_behind or len(issues) >= 2
            rows.append(
                ProjectRow(
                    batch_id=str(batch.id),
                    batch_code=batch.batch_code,
                    title=batch.title or "Untitled project",
                    issue=issue_text,
                    progress=progress,
                    risk="At Risk" if at_risk else "Need Attention",
                )
            )

        rows.sort(key=lambda r: r.progress)
        return rows

    def _build_section_rows(
        self,
        enrollments: List[StudentEnrollment],
        batches: List[ProjectBatch],
        attendance_rates: Dict[str, float],
        now: datetime,
    ) -> List[SectionRow]:
        by_section: Dict[Optional[str], List[StudentEnrollment]] = defaultdict(list)
        for e in enrollments:
            by_section[e.section].append(e)

        batches_by_section: Dict[Optional[str], List[ProjectBatch]] = defaultdict(list)
        for b in batches:
            batches_by_section[b.section].append(b)

        # Named sections first in order, unassigned students last.
        keys = sorted([k for k in by_section if k], key=str) + ([None] if None in by_section else [])

        rows: List[SectionRow] = []
        for key in keys:
            section_enrollments = by_section[key]
            section_batches = batches_by_section.get(key, [])

            pending = sum(
                1
                for b in section_batches
                for r in b.reviews
                if r.status == ReviewStatus.SCHEDULED
            )

            if key is None:
                rows.append(
                    SectionRow(
                        section="Unassigned",
                        students=len(section_enrollments),
                        batches=None,
                        registration=None,
                        attendance=None,
                        progress=None,
                        pending_reviews=pending,
                        status="Not Assigned",
                    )
                )
                continue

            registered = sum(1 for e in section_enrollments if e.is_registered)
            registration = _pct(registered, len(section_enrollments))

            rates = [
                attendance_rates[str(e.student_id)]
                for e in section_enrollments
                if str(e.student_id) in attendance_rates
            ]
            attendance = int(round(sum(rates) / len(rates))) if rates else None

            progresses = [b.overall_progress or 0.0 for b in section_batches]
            progress = int(round(sum(progresses) / len(progresses))) if progresses else None

            rows.append(
                SectionRow(
                    section=f"Section {key}",
                    students=len(section_enrollments),
                    batches=len(section_batches),
                    registration=registration,
                    attendance=attendance,
                    progress=progress,
                    pending_reviews=pending,
                    status=self._section_status(progress, attendance),
                )
            )
        return rows

    @staticmethod
    def _section_status(progress: Optional[int], attendance: Optional[int]) -> str:
        if progress is None or attendance is None:
            return "Not Assigned"
        if progress >= PROGRESS_EXCELLENT and attendance >= ATTENDANCE_EXCELLENT:
            return "Excellent"
        if progress >= PROGRESS_ON_TRACK and attendance >= ATTENDANCE_ON_TRACK:
            return "On Track"
        return "Need Attention"

    async def _build_workload(self, user: User, academic_year: str, now: datetime) -> WorkloadSummary:
        assigned_stmt = (
            select(func.count())
            .select_from(ProjectBatch)
            .where(ProjectBatch.guide_id == user.id)
            .where(ProjectBatch.academic_year == academic_year)
            .where(ProjectBatch.is_active.is_(True))
        )
        assigned = (await self.db.execute(assigned_stmt)).scalar() or 0

        week_end = now + timedelta(days=7)
        reviews_stmt = (
            select(func.count())
            .select_from(ProjectReview)
            .join(ProjectBatch, ProjectReview.batch_id == ProjectBatch.id)
            .where(ProjectBatch.guide_id == user.id)
            .where(ProjectReview.status == ReviewStatus.SCHEDULED)
            .where(ProjectReview.scheduled_at >= now)
            .where(ProjectReview.scheduled_at <= week_end)
        )
        reviews = (await self.db.execute(reviews_stmt)).scalar() or 0

        return WorkloadSummary(assigned_batches=assigned, reviews_this_week=reviews)

    @staticmethod
    def _build_insight(section_rows: List[SectionRow]) -> Optional[str]:
        """Call out the widest attendance gap between sections, if any."""
        rated = [r for r in section_rows if r.attendance is not None]
        if len(rated) < 2:
            return None

        best = max(rated, key=lambda r: r.attendance or 0)
        worst = min(rated, key=lambda r: r.attendance or 0)
        gap = (best.attendance or 0) - (worst.attendance or 0)
        if gap < 10:
            return None

        return (
            f"{worst.section} attendance is {gap} percentage points below "
            f"{best.section} and is affecting project progress."
        )

    # ---------------------------------------------------------- filter lists

    async def build_filter_options(self, academic_year: Optional[str] = None) -> FilterOptions:
        """Distinct values actually present in the data, for the dropdowns."""

        async def distinct(column, *, where=None) -> List[str]:
            stmt = select(column).distinct().where(column.isnot(None))
            if where is not None:
                stmt = stmt.where(where)
            rows = (await self.db.execute(stmt)).scalars().all()
            return sorted({str(r) for r in rows if r})

        scope = ProjectBatch.academic_year == academic_year if academic_year else None

        guides_stmt = (
            select(User.id, User.full_name)
            .join(ProjectBatch, ProjectBatch.guide_id == User.id)
            .distinct()
        )
        if academic_year:
            guides_stmt = guides_stmt.where(ProjectBatch.academic_year == academic_year)
        guides = [
            GuideOption(id=str(guide_id), name=name)
            for guide_id, name in (await self.db.execute(guides_stmt)).all()
            if name
        ]

        return FilterOptions(
            departments=await distinct(ProjectBatch.department, where=scope),
            years=await distinct(ProjectBatch.year, where=scope),
            semesters=await distinct(ProjectBatch.semester, where=scope),
            sections=await distinct(ProjectBatch.section, where=scope),
            project_types=await distinct(ProjectBatch.project_type, where=scope),
            guides=sorted(guides, key=lambda g: g.name),
            academic_years=await distinct(ProjectBatch.academic_year),
        )
