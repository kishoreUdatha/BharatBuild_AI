"""
Registrations Service - the Student & Batch Registrations screen.

Everything that screen renders in one aggregate (KPIs, attention list,
progress bars, and the paged batch table), plus the two mutations its toolbar
performs: assigning a guide and approving a selection.
"""

from dataclasses import dataclass
from math import ceil
from typing import Dict, List, Optional, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.faculty import (
    BasePaperStatus,
    BatchRegistrationStatus,
    ProjectBatch,
    ProjectBatchMember,
    StudentEnrollment,
)
from app.models.user import User

# A full team. Batches under this are "incomplete" on the registration screen.
# The default when a batch does not state its own size. A batch formed through
# the app always does, so this is a floor for legacy rows, not a rule.
TEAM_SIZE = 4


def _size_of(batch) -> int:
    return getattr(batch, "team_size", None) or TEAM_SIZE

# Statuses grouped the way the KPI tiles count them.
COMPLETE_STATUSES = {BatchRegistrationStatus.SUBMITTED, BatchRegistrationStatus.APPROVED}
INCOMPLETE_STATUSES = {BatchRegistrationStatus.DRAFT, BatchRegistrationStatus.INCOMPLETE}
AWAITING_STATUSES = {BatchRegistrationStatus.PENDING_APPROVAL, BatchRegistrationStatus.CHANGES_REQUESTED}

STATUS_LABELS = {
    BatchRegistrationStatus.DRAFT: "Draft",
    BatchRegistrationStatus.INCOMPLETE: "Incomplete",
    BatchRegistrationStatus.SUBMITTED: "Submitted",
    BatchRegistrationStatus.PENDING_APPROVAL: "Pending Approval",
    BatchRegistrationStatus.CHANGES_REQUESTED: "Changes Requested",
    BatchRegistrationStatus.APPROVED: "Approved",
    BatchRegistrationStatus.REJECTED: "Rejected",
}

# Every enum member must have a label - the dropdown iterates the enum, so a
# missing entry is a 500, not a cosmetic gap.
assert set(STATUS_LABELS) == set(BatchRegistrationStatus), (
    f"STATUS_LABELS is missing: {set(BatchRegistrationStatus) - set(STATUS_LABELS)}"
)

# The registration screen calls an unverified upload "Uploaded"; the base-paper
# screen calls the same state "Pending". Same value, audience-specific wording.
BASE_PAPER_LABELS = {
    BasePaperStatus.VERIFIED: "Verified",
    BasePaperStatus.PENDING: "Uploaded",
    BasePaperStatus.MISSING: "Missing",
}


@dataclass
class RegistrationFilters:
    academic_year: str
    department: Optional[str] = None
    section: Optional[str] = None
    year: Optional[str] = None
    semester: Optional[str] = None
    project_type: Optional[str] = None
    status: Optional[str] = None
    search: Optional[str] = None


def _is_all(value: Optional[str]) -> bool:
    return value is None or not value.strip() or value.strip().lower().startswith("all")


class FacultyRegistrationsService:
    def __init__(self, db: AsyncSession, college_id=None):
        self.db = db
        # The caller's college. Every query this service builds is
        # confined to it - see app/services/tenancy.py.
        self.college_id = college_id

    def _mine(self, stmt):
        """Confine a batch query to the caller's college."""
        if self.college_id:
            return stmt.where(ProjectBatch.college_id == self.college_id)
        return stmt

    # ------------------------------------------------------------- selection

    def _apply_filters(self, stmt, f: RegistrationFilters):
        stmt = stmt.where(ProjectBatch.academic_year == f.academic_year)
        stmt = stmt.where(ProjectBatch.is_active.is_(True))
        if not _is_all(f.department):
            stmt = stmt.where(ProjectBatch.department == f.department)
        if not _is_all(f.section):
            stmt = stmt.where(ProjectBatch.section == f.section)
        if not _is_all(f.year):
            stmt = stmt.where(ProjectBatch.year == f.year)
        if not _is_all(f.semester):
            stmt = stmt.where(ProjectBatch.semester == f.semester)
        if not _is_all(f.project_type):
            stmt = stmt.where(ProjectBatch.project_type == f.project_type)
        if not _is_all(f.status):
            stmt = stmt.where(ProjectBatch.registration_status == BatchRegistrationStatus(f.status))
        return stmt

    async def _batches(self, f: RegistrationFilters) -> List[ProjectBatch]:
        stmt = self._mine(select(ProjectBatch)).options(
            selectinload(ProjectBatch.members).selectinload(ProjectBatchMember.student),
            selectinload(ProjectBatch.base_paper),
            selectinload(ProjectBatch.guide),
        )
        stmt = self._apply_filters(stmt, f)
        batches = list((await self.db.execute(stmt)).scalars().unique().all())

        # Search spans batch code, project title, and any member's name or roll
        # number - so a faculty member can paste a roll number and find the team.
        if f.search and f.search.strip():
            needle = f.search.strip().lower()

            def matches(batch: ProjectBatch) -> bool:
                haystack = [batch.batch_code or "", batch.title or ""]
                for member in batch.members:
                    student = member.student
                    if student:
                        haystack += [student.full_name or "", student.roll_number or ""]
                return any(needle in value.lower() for value in haystack)

            batches = [b for b in batches if matches(b)]

        batches.sort(key=lambda b: b.batch_code)
        return batches

    # ---------------------------------------------------------------- shapes

    @staticmethod
    def _row(batch: ProjectBatch) -> dict:
        active = [m for m in batch.members if m.is_active]
        lead = next((m for m in batch.members if m.is_lead), None)
        leader = lead.student if lead and lead.student else None
        bp_status = batch.base_paper.status if batch.base_paper else BasePaperStatus.MISSING

        return {
            "id": str(batch.id),
            "batch_code": batch.batch_code,
            "title": batch.title,
            "section": batch.section,
            "members": len(active),
            "team_size": _size_of(batch),
            "batch_leader": (leader.full_name if leader else None),
            "base_paper": BASE_PAPER_LABELS.get(bp_status, "Missing"),
            "base_paper_status": bp_status.value,
            "guide": (batch.guide.full_name if batch.guide else None),
            "guide_id": str(batch.guide_id) if batch.guide_id else None,
            "status": STATUS_LABELS.get(batch.registration_status, "Draft"),
            "status_key": batch.registration_status.value,
            "last_updated": (batch.updated_at or batch.created_at),
        }

    # --------------------------------------------------------------- summary

    async def build(self, f: RegistrationFilters, page: int, per_page: int) -> dict:
        batches = await self._batches(f)

        # Enrollments are the denominator for every student-level figure.
        enr_stmt = (
            select(StudentEnrollment, User)
            .join(User, StudentEnrollment.student_id == User.id)
            .where(StudentEnrollment.academic_year == f.academic_year)
            .where(StudentEnrollment.is_active.is_(True))
        )
        if not _is_all(f.department):
            enr_stmt = enr_stmt.where(StudentEnrollment.department == f.department)
        if not _is_all(f.section):
            enr_stmt = enr_stmt.where(StudentEnrollment.section == f.section)
        enrollments = (await self.db.execute(enr_stmt)).all()
        total_students = len(enrollments)

        # Which students sit in a batch this year (across all batches, not the
        # filtered page, so "not in any batch" stays truthful).
        # base_paper is eager-loaded because _progress reads it. Without this the
        # unfiltered case only worked by accident - the filtered query had already
        # populated those instances in the identity map - and any narrow filter
        # hit a lazy load outside the async context (MissingGreenlet).
        all_batches_stmt = self._mine(select(ProjectBatch)).options(
            selectinload(ProjectBatch.members),
            selectinload(ProjectBatch.base_paper),
        ).where(
            ProjectBatch.academic_year == f.academic_year, ProjectBatch.is_active.is_(True)
        )
        all_batches = list((await self.db.execute(all_batches_stmt)).scalars().unique().all())
        batched_ids = {
            str(m.student_id) for b in all_batches for m in b.members if m.is_active
        }

        students_not_in_batch = sum(
            1 for e, _ in enrollments if str(e.student_id) not in batched_ids
        )

        complete = sum(1 for b in batches if b.registration_status in COMPLETE_STATUSES)
        incomplete = sum(1 for b in batches if b.registration_status in INCOMPLETE_STATUSES)
        awaiting = sum(1 for b in batches if b.registration_status in AWAITING_STATUSES)

        short_teams = sum(1 for b in batches
                          if len([m for m in b.members if m.is_active]) < _size_of(b))
        missing_paper = sum(
            1 for b in batches
            if b.base_paper is None or b.base_paper.status == BasePaperStatus.MISSING
        )
        no_guide = sum(1 for b in batches if b.guide_id is None)

        kpis = [
            {"id": "students", "value": str(total_students), "label": "Total Students"},
            {"id": "expected", "value": str(ceil(total_students / TEAM_SIZE) if total_students else 0),
             "label": "Expected Batches"},
            {"id": "complete", "value": str(complete), "label": "Complete Batches"},
            {"id": "incomplete", "value": str(incomplete), "label": "Incomplete Batches"},
            {"id": "pending", "value": str(awaiting), "label": "Pending Approval"},
            {"id": "unbatched", "value": str(students_not_in_batch), "label": "Students Not in Batch"},
        ]

        attention = [
            {"id": "unbatched", "label": "Students not in any batch", "count": students_not_in_batch},
            # Batches no longer all hold four, so the label states the condition
            # rather than a number that would be wrong for half of them.
            {"id": "short-teams", "label": "Batches short of their team size", "count": short_teams},
            {"id": "missing-papers", "label": "Projects missing base papers", "count": missing_paper},
            {"id": "no-guide", "label": "Batches without faculty guide", "count": no_guide},
            {"id": "awaiting", "label": "Registrations awaiting approval", "count": awaiting},
        ]

        progress = self._progress(enrollments, all_batches, batched_ids, total_students)

        total_rows = len(batches)
        pages = max(1, ceil(total_rows / per_page)) if total_rows else 1
        current = min(max(page, 1), pages)
        start = (current - 1) * per_page
        window = batches[start:start + per_page]

        return {
            "kpis": kpis,
            "attention_items": attention,
            "progress": progress,
            "rows": [self._row(b) for b in window],
            "page": current,
            "pages": pages,
            "per_page": per_page,
            "total": total_rows,
            "showing_from": (start + 1) if total_rows else 0,
            "showing_to": min(start + per_page, total_rows),
            "statuses": [{"key": s.value, "label": STATUS_LABELS[s]} for s in BatchRegistrationStatus],
        }

    @staticmethod
    def _progress(enrollments, all_batches, batched_ids, total_students: int) -> List[dict]:
        """
        The five registration milestones, each counted in students so the bars
        share one denominator.
        """
        batch_of: Dict[str, ProjectBatch] = {}
        for batch in all_batches:
            for member in batch.members:
                if member.is_active:
                    batch_of[str(member.student_id)] = batch

        profiles = sum(1 for _, user in enrollments if user.roll_number and user.college_name)
        teamed = sum(1 for e, _ in enrollments if str(e.student_id) in batched_ids)

        details = papers = approved = 0
        for enrollment, _ in enrollments:
            batch = batch_of.get(str(enrollment.student_id))
            if not batch:
                continue
            if batch.title:
                details += 1
            bp = getattr(batch, "base_paper", None)
            if bp is not None and bp.status != BasePaperStatus.MISSING:
                papers += 1
            if batch.registration_status == BatchRegistrationStatus.APPROVED:
                approved += 1

        return [
            {"label": "Individual Profiles", "done": profiles, "total": total_students},
            {"label": "Team Formation", "done": teamed, "total": total_students},
            {"label": "Project Details", "done": details, "total": total_students},
            {"label": "Base Papers", "done": papers, "total": total_students},
            {"label": "Faculty Approval", "done": approved, "total": total_students},
        ]

    # ------------------------------------------------------------- mutations

    async def assign_guide(self, batch_ids: Sequence[str], guide_id: str) -> int:
        guide = (await self.db.execute(select(User).where(User.id == guide_id))).scalar_one_or_none()
        if guide is None:
            raise ValueError("Guide not found")

        stmt = self._mine(select(ProjectBatch)).where(ProjectBatch.id.in_(list(batch_ids)))
        batches = list((await self.db.execute(stmt)).scalars().all())
        for batch in batches:
            batch.guide_id = guide.id
            # A batch held up only by a missing guide can now move forward.
            if batch.registration_status == BatchRegistrationStatus.INCOMPLETE:
                batch.registration_status = BatchRegistrationStatus.PENDING_APPROVAL
        await self.db.commit()
        return len(batches)

    async def approve(self, batch_ids: Sequence[str]) -> dict:
        stmt = self._mine(select(ProjectBatch)).options(
            selectinload(ProjectBatch.members), selectinload(ProjectBatch.base_paper)
        ).where(ProjectBatch.id.in_(list(batch_ids)))
        batches = list((await self.db.execute(stmt)).scalars().unique().all())

        approved, skipped = [], []
        for batch in batches:
            active = len([m for m in batch.members if m.is_active])
            bp = batch.base_paper
            # Approving a team that is short-handed or has no verified paper
            # would defeat the purpose of the queue, so those are refused.
            size = _size_of(batch)
            if active < size:
                skipped.append({"batch_code": batch.batch_code,
                                "reason": f"only {active} of {size} seats taken"})
                continue
            if bp is None or bp.status == BasePaperStatus.MISSING:
                skipped.append({"batch_code": batch.batch_code, "reason": "no base paper"})
                continue
            if batch.guide_id is None:
                skipped.append({"batch_code": batch.batch_code, "reason": "no guide assigned"})
                continue
            batch.registration_status = BatchRegistrationStatus.APPROVED
            approved.append(batch.batch_code)

        await self.db.commit()
        return {"approved": approved, "skipped": skipped}
