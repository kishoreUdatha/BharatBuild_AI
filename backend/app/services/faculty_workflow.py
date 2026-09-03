"""
Registration Workflow Service - the Incomplete Registrations and Approval
Queue tabs.

Neither screen stores an "issue" or a "queue entry": both are derived from the
same batch/enrollment records the rest of the portal uses, so a record leaves a
queue the moment the underlying gap is filled.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil
from typing import Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.faculty import (
    BasePaperStatus,
    BatchRegistrationStatus,
    ProjectBatch,
    ProjectBatchMember,
    StudentEnrollment,
    StudentProfileStatus,
)
from app.models.user import User
from app.services.faculty_registrations import TEAM_SIZE


def _size_of(batch) -> int:
    """
    How many students this batch is meant to hold.

    A coordinator picks the size when forming the batch, so nothing here may
    assume four: a team of two would otherwise read "1/4" forever and never
    clear the membership gate.
    """
    return getattr(batch, "team_size", None) or TEAM_SIZE

# How long a submitted registration may sit before the queue calls it overdue.
REVIEW_SLA_HOURS = 48

# A record older than this that is still incomplete counts as overdue.
OVERDUE_AFTER_DAYS = 14

# The seven gates a batch must clear before it can be approved. Order matters:
# it is the order the checklist renders in.
CHECKLIST = [
    ("team", "All students verified"),
    ("cohort", "Same department/year/section"),
    ("details", "Project title and abstract"),
    ("base_paper", "Primary base paper"),
    ("improvement", "Improvement over base paper"),
    ("guide", "Faculty guide assigned"),
    ("declaration", "Student declaration"),
]


def _is_all(value: Optional[str]) -> bool:
    return value is None or not value.strip() or value.strip().lower().startswith("all")


def _page(items: list, page: int, per_page: int) -> dict:
    total = len(items)
    pages = max(1, ceil(total / per_page)) if total else 1
    current = min(max(page, 1), pages)
    start = (current - 1) * per_page
    return {
        "window": items[start:start + per_page],
        "page": current,
        "pages": pages,
        "per_page": per_page,
        "total": total,
        "showing_from": (start + 1) if total else 0,
        "showing_to": min(start + per_page, total),
    }


@dataclass
class WorkflowFilters:
    academic_year: str
    department: Optional[str] = None
    section: Optional[str] = None
    year: Optional[str] = None
    semester: Optional[str] = None
    issue_type: Optional[str] = None
    priority: Optional[str] = None
    scope: Optional[str] = None        # all | student | batch
    review_status: Optional[str] = None
    search: Optional[str] = None


class FacultyWorkflowService:
    def __init__(self, db: AsyncSession, college_id=None):
        self.db = db
        # The approval queue lists batches awaiting a decision. Without this
        # it listed every college's.
        self.college_id = college_id

    def _mine(self, stmt):
        """Confine a batch query to the caller's college."""
        if self.college_id:
            return stmt.where(ProjectBatch.college_id == self.college_id)
        return stmt

    # ------------------------------------------------------------ loading

    async def _batches(self, f: WorkflowFilters) -> List[ProjectBatch]:
        stmt = (
            self._mine(select(ProjectBatch))
            .options(
                selectinload(ProjectBatch.members).selectinload(ProjectBatchMember.student),
                selectinload(ProjectBatch.base_paper),
                selectinload(ProjectBatch.guide),
                selectinload(ProjectBatch.reviewer),
            )
            .where(ProjectBatch.academic_year == f.academic_year)
            .where(ProjectBatch.is_active.is_(True))
        )
        if not _is_all(f.department):
            stmt = stmt.where(ProjectBatch.department == f.department)
        if not _is_all(f.section):
            stmt = stmt.where(ProjectBatch.section == f.section)
        if not _is_all(f.year):
            stmt = stmt.where(ProjectBatch.year == f.year)
        if not _is_all(f.semester):
            stmt = stmt.where(ProjectBatch.semester == f.semester)
        return list((await self.db.execute(stmt)).scalars().unique().all())

    async def _enrollments(self, f: WorkflowFilters):
        stmt = (
            select(StudentEnrollment, User)
            .join(User, StudentEnrollment.student_id == User.id)
            .where(StudentEnrollment.academic_year == f.academic_year)
            .where(StudentEnrollment.is_active.is_(True))
        )
        if not _is_all(f.department):
            stmt = stmt.where(StudentEnrollment.department == f.department)
        if not _is_all(f.section):
            stmt = stmt.where(StudentEnrollment.section == f.section)
        return (await self.db.execute(stmt)).all()

    # -------------------------------------------------- incomplete records

    @staticmethod
    def _batch_issues(batch: ProjectBatch) -> tuple:
        """(issue keys, human summary, completion %) for one batch."""
        active = [m for m in batch.members if m.is_active]
        size = _size_of(batch)
        keys, parts, passed = [], [], 0
        total_checks = 4

        if len(active) < size:
            missing = size - len(active)
            keys.append("incomplete_membership")
            parts.append("One teammate" if missing == 1 else f"{missing} teammates")
        else:
            passed += 1

        bp = batch.base_paper
        if bp is None or bp.status == BasePaperStatus.MISSING:
            keys.append("base_paper")
            parts.append("base paper")
        else:
            passed += 1

        if batch.guide_id is None:
            keys.append("guide")
            parts.append("faculty guide")
        else:
            passed += 1

        if not batch.title or not batch.abstract:
            keys.append("project_details")
            parts.append("project abstract" if batch.title else "project title, abstract")
        else:
            passed += 1

        return keys, ", ".join(parts), int(round(passed / total_checks * 100))

    @staticmethod
    def _student_issues(enrollment: StudentEnrollment, user: User, in_batch: bool) -> tuple:
        keys, parts, passed = [], [], 0
        total_checks = 4

        if enrollment.profile_status == StudentProfileStatus.PROFILE_INCOMPLETE:
            keys.append("profile_details")
            parts.append("profile details")
        else:
            passed += 1

        if not enrollment.contact_verified or not user.phone:
            keys.append("profile_details")
            parts.append("Mobile verification")
        else:
            passed += 1

        if not in_batch:
            keys.append("not_in_batch")
            parts.append("Batch membership")
        elif not enrollment.invitation_accepted:
            keys.append("invitation")
            parts.append("Batch invitation acceptance")
        else:
            passed += 1

        if not enrollment.declaration_signed:
            keys.append("profile_details")
            parts.append("declaration")
        else:
            passed += 1

        return list(dict.fromkeys(keys)), ", ".join(parts), int(round(passed / total_checks * 100))

    @staticmethod
    def _priority(issue_count: int, completion: int) -> str:
        if issue_count >= 3 or completion <= 50:
            return "Critical"
        if issue_count == 2 or completion <= 75:
            return "High"
        return "Medium"

    async def build_incomplete(self, f: WorkflowFilters, page: int, per_page: int) -> dict:
        batches = await self._batches(f)
        enrollments = await self._enrollments(f)

        in_batch: Dict[str, ProjectBatch] = {}
        for batch in batches:
            for member in batch.members:
                if member.is_active:
                    in_batch[str(member.student_id)] = batch

        records: List[dict] = []

        for enrollment, user in enrollments:
            batch = in_batch.get(str(enrollment.student_id))
            keys, summary, completion = self._student_issues(enrollment, user, batch is not None)
            if not keys:
                continue
            records.append({
                "id": str(enrollment.id),
                "kind": "student",
                "label": f"{user.full_name or user.email} • {user.roll_number or '-'}",
                "type": "Student",
                "department": enrollment.department,
                "section": enrollment.section,
                "batch": (
                    batch.batch_code if batch
                    else ("Invitation Pending" if enrollment.invitation_accepted is False and batch else "Not Joined")
                ),
                "missing": summary,
                "completion": completion,
                "issues": keys,
                "priority": self._priority(len(keys), completion),
                "last_reminder": enrollment.last_reminder_at,
                "action": "Assign Batch" if batch is None else "Complete Profile",
            })

        for batch in batches:
            keys, summary, completion = self._batch_issues(batch)
            if not keys:
                continue
            active = len([m for m in batch.members if m.is_active])
            records.append({
                "id": str(batch.id),
                "kind": "batch",
                "label": f"{batch.batch_code} • {batch.title or 'Untitled'}",
                "type": "Batch",
                "department": batch.department,
                "section": batch.section,
                "batch": f"{active}/{_size_of(batch)} Members",
                "missing": summary,
                "completion": completion,
                "issues": keys,
                "priority": self._priority(len(keys), completion),
                "last_reminder": batch.last_reminder_at,
                "action": "Resolve",
            })

        # --- filters that only make sense once issues are known
        if f.scope == "student":
            records = [r for r in records if r["kind"] == "student"]
        elif f.scope == "batch":
            records = [r for r in records if r["kind"] == "batch"]
        if not _is_all(f.issue_type):
            records = [r for r in records if f.issue_type in r["issues"]]
        if not _is_all(f.priority):
            records = [r for r in records if r["priority"].lower() == f.priority.lower()]
        if f.search and f.search.strip():
            needle = f.search.strip().lower()
            records = [
                r for r in records
                if needle in r["label"].lower() or needle in r["missing"].lower()
            ]

        order = {"Critical": 0, "High": 1, "Medium": 2}
        records.sort(key=lambda r: (order.get(r["priority"], 3), r["completion"]))

        breakdown_labels = {
            "incomplete_membership": "Incomplete team membership",
            "not_in_batch": "Students not in batch",
            "profile_details": "Profiles missing details",
            "base_paper": "Base papers missing",
            "guide": "Guides not assigned",
            "project_details": "Project details incomplete",
        }
        breakdown = [
            {"id": key, "label": label, "count": sum(1 for r in records if key in r["issues"])}
            for key, label in breakdown_labels.items()
        ]

        kpis = [
            {"id": "records", "value": str(len(records)), "label": "Incomplete Records"},
            {"id": "batches", "value": str(sum(1 for r in records if r["kind"] == "batch")), "label": "Incomplete Batches"},
            {"id": "unbatched", "value": str(sum(1 for r in records if "not_in_batch" in r["issues"])), "label": "Students Not in Batch"},
            {"id": "profiles", "value": str(sum(1 for r in records if "profile_details" in r["issues"])), "label": "Profiles Incomplete"},
            {"id": "papers", "value": str(sum(1 for r in records if "base_paper" in r["issues"])), "label": "Base Papers Missing"},
            {"id": "guides", "value": str(sum(1 for r in records if "guide" in r["issues"])), "label": "Guides Not Assigned"},
        ]

        progress = self._resolution_progress(batches, enrollments, len(records))
        paged = _page(records, page, per_page)

        return {
            "kpis": kpis,
            "breakdown": breakdown,
            "resolution": progress,
            "recommendations": self._recommendations(records),
            "rows": paged.pop("window"),
            **paged,
            "issue_types": [{"key": k, "label": v} for k, v in breakdown_labels.items()],
            "priorities": ["Critical", "High", "Medium"],
        }

    @staticmethod
    def _resolution_progress(batches, enrollments, pending: int) -> dict:
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)

        # Batches only. Counting every verified enrollment inflated this to the
        # whole cohort, because a bulk verify stamps updated_at on all of them -
        # that measures the last write, not a resolution.
        resolved_week = sum(
            1 for b in batches
            if b.resolved_at and b.resolved_at >= week_ago
        )

        overdue = sum(
            1 for b in batches
            if b.registration_status in {BatchRegistrationStatus.DRAFT, BatchRegistrationStatus.INCOMPLETE}
            and b.created_at and (now - b.created_at).days >= OVERDUE_AFTER_DAYS
        )

        # Measured submission -> resolution. Negatives are dropped rather than
        # averaged in: they mean the two timestamps are inconsistent, and a
        # negative "average resolution time" is worse than no figure.
        durations = [
            d for d in (
                (b.resolved_at - b.submitted_at).total_seconds() / 86400
                for b in batches if b.resolved_at and b.submitted_at
            )
            if d >= 0
        ]
        avg_days = round(sum(durations) / len(durations), 1) if durations else 0.0

        total = resolved_week + pending
        return {
            "resolved_this_week": resolved_week,
            "pending": pending,
            "overdue": overdue,
            "average_days": avg_days,
            "percent_resolved": int(round(resolved_week / total * 100)) if total else 0,
        }

    @staticmethod
    def _recommendations(records: List[dict]) -> List[str]:
        out = []
        unbatched = sum(1 for r in records if "not_in_batch" in r["issues"])
        critical = sum(1 for r in records if r["priority"] == "Critical")
        invites = sum(1 for r in records if "invitation" in r["issues"])
        if unbatched:
            out.append(f"Assign the {unbatched} ungrouped students to batches in their own department, year and section.")
        if critical:
            out.append(f"Complete {critical} critical record(s) before faculty approval.")
        if invites:
            out.append(f"Send reminders to {invites} students with pending invitations.")
        return out or ["Nothing outstanding - every record in scope is complete."]

    # ----------------------------------------------------- approval queue

    def _checklist(self, batch: ProjectBatch) -> List[dict]:
        active = [m for m in batch.members if m.is_active]
        bp = batch.base_paper
        sections = {m.student.section for m in active if m.student and m.student.section}

        size = _size_of(batch)
        results = {
            "team": (len(active) >= size, "Complete" if len(active) >= size else f"{len(active)}/{size}"),
            "cohort": (len(sections) <= 1, "Complete" if len(sections) <= 1 else "Mixed sections"),
            "details": (bool(batch.title and batch.abstract), "Complete" if batch.title and batch.abstract else "Missing"),
            # An uploaded-but-unverified paper is a warning, not a pass: the
            # guide still has to open it.
            "base_paper": (
                bp is not None and bp.status == BasePaperStatus.VERIFIED,
                "Complete" if bp and bp.status == BasePaperStatus.VERIFIED
                else "Uploaded, verify" if bp and bp.status == BasePaperStatus.PENDING else "Missing",
            ),
            "improvement": (bool(batch.abstract), "Complete" if batch.abstract else "Missing"),
            "guide": (batch.guide_id is not None, "Complete" if batch.guide_id else "Not assigned"),
            "declaration": (True, "Complete"),
        }
        return [
            {"key": key, "label": label, "passed": results[key][0], "detail": results[key][1]}
            for key, label in CHECKLIST
        ]

    def _queue_row(self, batch: ProjectBatch, now: datetime) -> dict:
        active = [m for m in batch.members if m.is_active]
        bp = batch.base_paper
        due = batch.review_due_at
        if due:
            delta = due - now
            hours = int(delta.total_seconds() // 3600)
            sla = f"{hours}h left" if hours >= 0 else f"Overdue {abs(delta.days) or 1}d"
        else:
            sla = "—"

        paper = (
            "Verified" if bp and bp.status == BasePaperStatus.VERIFIED
            else "Pending Verification" if bp and bp.status == BasePaperStatus.PENDING
            else "Missing"
        )
        checks = self._checklist(batch)
        passed = sum(1 for c in checks if c["passed"])

        return {
            "id": str(batch.id),
            "batch_code": batch.batch_code,
            "title": batch.title,
            "section": batch.section,
            "team": f"{len(active)}/{_size_of(batch)} Complete",
            "team_complete": len(active) >= _size_of(batch),
            "project_details": "Complete" if batch.title and batch.abstract else "Incomplete",
            "base_paper": paper,
            "guide": batch.guide.full_name if batch.guide else None,
            "reviewer": batch.reviewer.full_name if batch.reviewer else None,
            "submitted_at": batch.submitted_at,
            "sla": sla,
            "overdue": bool(due and due < now),
            "status_key": batch.registration_status.value,
            "checks_passed": passed,
            "checks_total": len(checks),
            "action": (
                "Verify Paper" if paper == "Pending Verification"
                else "Re-review" if batch.registration_status == BatchRegistrationStatus.CHANGES_REQUESTED
                else "Review"
            ),
        }

    async def build_queue(self, f: WorkflowFilters, page: int, per_page: int) -> dict:
        batches = await self._batches(f)
        now = datetime.utcnow()

        tab_map = {
            "pending": {BatchRegistrationStatus.SUBMITTED, BatchRegistrationStatus.PENDING_APPROVAL},
            "changes": {BatchRegistrationStatus.CHANGES_REQUESTED},
            "approved": {BatchRegistrationStatus.APPROVED},
            "rejected": {BatchRegistrationStatus.REJECTED},
        }
        wanted = tab_map.get(f.review_status or "pending", tab_map["pending"])
        in_scope = [b for b in batches if b.registration_status in wanted]

        if f.search and f.search.strip():
            needle = f.search.strip().lower()
            in_scope = [
                b for b in in_scope
                if needle in (b.batch_code or "").lower()
                or needle in (b.title or "").lower()
                or needle in ((b.guide.full_name if b.guide else "") or "").lower()
            ]

        in_scope.sort(key=lambda b: (b.submitted_at or now))
        rows = [self._queue_row(b, now) for b in in_scope]

        awaiting = [b for b in batches if b.registration_status in tab_map["pending"]]
        due_today = sum(
            1 for b in awaiting
            if b.review_due_at and b.review_due_at.date() == now.date()
        )
        overdue = sum(1 for b in awaiting if b.review_due_at and b.review_due_at < now)
        week_ago = now - timedelta(days=7)
        approved_week = sum(
            1 for b in batches
            if b.registration_status == BatchRegistrationStatus.APPROVED
            and b.resolved_at and b.resolved_at >= week_ago
        )
        papers_pending = sum(
            1 for b in awaiting
            if b.base_paper and b.base_paper.status == BasePaperStatus.PENDING
        )

        kpis = [
            {"id": "awaiting", "value": str(len(awaiting)), "label": "Awaiting Review"},
            {"id": "due", "value": str(due_today), "label": "Due Today"},
            {"id": "changes", "value": str(sum(1 for b in batches if b.registration_status == BatchRegistrationStatus.CHANGES_REQUESTED)), "label": "Changes Requested"},
            {"id": "approved", "value": str(approved_week), "label": "Approved This Week"},
            {"id": "papers", "value": str(papers_pending), "label": "Base Papers Pending Verification"},
            {"id": "overdue", "value": str(overdue), "label": "Overdue Review"},
        ]

        by_section: Dict[str, int] = {}
        for b in awaiting:
            key = b.section or "Unassigned"
            by_section[key] = by_section.get(key, 0) + 1

        oldest = min((b.submitted_at for b in awaiting if b.submitted_at), default=None)
        review_hours = [
            (b.resolved_at - b.submitted_at).total_seconds() / 3600
            for b in batches if b.resolved_at and b.submitted_at
        ]

        paged = _page(rows, page, per_page)
        selected = in_scope[0] if in_scope else None

        return {
            "kpis": kpis,
            "rows": paged.pop("window"),
            **paged,
            "summary": {
                "by_section": [{"section": k, "pending": v} for k, v in sorted(by_section.items())],
                "oldest_days": (now - oldest).days if oldest else 0,
                "average_review_hours": round(sum(review_hours) / len(review_hours), 1) if review_hours else 0.0,
            },
            "selected": await self.detail(str(selected.id)) if selected else None,
            "tabs": [
                {"key": "pending", "label": "Pending Review"},
                {"key": "changes", "label": "Changes Requested"},
                {"key": "approved", "label": "Approved"},
                {"key": "rejected", "label": "Rejected"},
            ],
        }

    async def detail(self, batch_id: str) -> Optional[dict]:
        batch = (
            await self.db.execute(
                self._mine(select(ProjectBatch))
                .options(
                    selectinload(ProjectBatch.members).selectinload(ProjectBatchMember.student),
                    selectinload(ProjectBatch.base_paper),
                    selectinload(ProjectBatch.guide),
                )
                .where(ProjectBatch.id == batch_id)
            )
        ).scalar_one_or_none()
        if batch is None:
            return None

        checks = self._checklist(batch)
        passed = sum(1 for c in checks if c["passed"])
        bp = batch.base_paper

        return {
            "id": str(batch.id),
            "batch_code": batch.batch_code,
            "title": batch.title,
            "abstract": batch.abstract,
            "base_paper_title": bp.title if bp else None,
            "base_paper_url": bp.url if bp else None,
            "base_paper_status": bp.status.value if bp else "missing",
            "guide": batch.guide.full_name if batch.guide else None,
            "submitted_at": batch.submitted_at,
            "faculty_note": batch.faculty_note,
            "status_key": batch.registration_status.value,
            "members": [
                {
                    "name": m.student.full_name if m.student else None,
                    "roll_number": m.student.roll_number if m.student else None,
                    "is_lead": m.is_lead,
                }
                for m in batch.members if m.is_active
            ],
            "checklist": checks,
            "checks_passed": passed,
            "checks_total": len(checks),
            "can_approve": passed == len(checks),
        }

    # ------------------------------------------------------------ actions

    async def decide(self, batch_ids: Sequence[str], decision: str, note: Optional[str]) -> dict:
        stmt = (
            self._mine(select(ProjectBatch))
            .options(
                selectinload(ProjectBatch.members).selectinload(ProjectBatchMember.student),
                selectinload(ProjectBatch.base_paper),
            )
            .where(ProjectBatch.id.in_(list(batch_ids)))
        )
        batches = list((await self.db.execute(stmt)).scalars().unique().all())
        now = datetime.utcnow()

        applied, skipped = [], []
        for batch in batches:
            if decision == "approve":
                checks = self._checklist(batch)
                failed = [c["label"] for c in checks if not c["passed"]]
                # Approval is gated on the same checklist the screen shows, so
                # the button and the API can never disagree.
                if failed:
                    skipped.append({"batch_code": batch.batch_code, "reason": "; ".join(failed)})
                    continue
                batch.registration_status = BatchRegistrationStatus.APPROVED
                batch.resolved_at = now
            elif decision == "reject":
                batch.registration_status = BatchRegistrationStatus.REJECTED
                batch.resolved_at = now
            elif decision == "request_changes":
                batch.registration_status = BatchRegistrationStatus.CHANGES_REQUESTED
            else:
                raise ValueError(f"Unknown decision: {decision}")

            if note:
                batch.faculty_note = note
            applied.append(batch.batch_code)

        await self.db.commit()
        return {"applied": applied, "skipped": skipped}

    async def assign_reviewer(self, batch_ids: Sequence[str], reviewer_id: str) -> int:
        reviewer = (await self.db.execute(select(User).where(User.id == reviewer_id))).scalar_one_or_none()
        if reviewer is None:
            raise ValueError("Reviewer not found")
        batches = list(
            (await self.db.execute(self._mine(select(ProjectBatch)).where(ProjectBatch.id.in_(list(batch_ids))))).scalars().all()
        )
        for batch in batches:
            batch.reviewer_id = reviewer.id
        await self.db.commit()
        return len(batches)

    async def send_reminders(self, record_ids: Sequence[str], kind: str) -> int:
        """
        Stamps last_reminder_at so the queue shows when a record was last
        chased. It does NOT send email - there is no dispatch pipeline wired up.
        """
        now = datetime.utcnow()
        model = ProjectBatch if kind == "batch" else StudentEnrollment
        records = list(
            (await self.db.execute(select(model).where(model.id.in_(list(record_ids))))).scalars().all()
        )
        for record in records:
            record.last_reminder_at = now
        await self.db.commit()
        return len(records)
