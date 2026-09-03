"""
Trainer workspace - the five screens either side of AI story approval.

Everything here is scoped by `FacultyAuthority.managed_batch_ids`, so a trainer
sees the batches they actually answer for rather than the whole department.
That scoping is the point of the portal: the faculty portal is the
coordinator's wide view, this is the trainer's own worklist.
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from math import ceil
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academics import AcademicDepartment, AcademicSection, SectionFacultyAssignment
from app.models.ai_planning import ProjectUserStory, StoryReviewStatus
from app.models.backlog import ProjectSprint
from app.models.project_tracking import ProjectTask, TaskStatus
from app.models.batch_detail import BatchDocument, DocumentStatus
from app.models.faculty import (
    BasePaper,
    BasePaperStatus,
    ProjectBatch,
    ProjectBatchMember,
    ProjectReview,
    ProjectSubmission,
    ReviewStatus,
    STAGE_LABELS,
    SubmissionStatus,
)
from app.models.user import User
from app.services import submissions as submission_service
from app.services.faculty_authority import FacultyAuthority


def _name(user: Optional[User]) -> Optional[str]:
    if user is None:
        return None
    return user.full_name or user.email.split("@")[0]


def _pct(part: int, whole: int) -> int:
    return int(round(part / whole * 100)) if whole else 0


class TrainerWorkspaceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.authority = FacultyAuthority(db)

    # ---------------------------------------------------------------- scope

    async def _scope(self, user: User, academic_year: str) -> List[ProjectBatch]:
        ids = await self.authority.managed_batch_ids(user, academic_year)
        if not ids:
            return []
        return (await self.db.execute(
            select(ProjectBatch)
            .where(ProjectBatch.id.in_(list(ids)))
            .where(ProjectBatch.is_active.is_(True))
            .options(
                selectinload(ProjectBatch.guide),
                selectinload(ProjectBatch.members).selectinload(ProjectBatchMember.student),
                selectinload(ProjectBatch.reviews),
                selectinload(ProjectBatch.stage_progress),
                selectinload(ProjectBatch.base_paper),
                # Chained: the shared row builder reads a submission's file and
                # both its people, and any relationship left lazy here raises
                # instead of loading once we are outside the greenlet.
                selectinload(ProjectBatch.submissions).selectinload(ProjectSubmission.file),
                selectinload(ProjectBatch.submissions).selectinload(ProjectSubmission.submitted_by),
                selectinload(ProjectBatch.submissions).selectinload(ProjectSubmission.reviewed_by),
            )
            .order_by(ProjectBatch.batch_code)
        )).scalars().all()

    @staticmethod
    def _role_on(batch: ProjectBatch, user: User) -> str:
        """Why this batch is on the trainer's list - useful when it is not obvious."""
        if batch.guide_id and str(batch.guide_id) == str(user.id):
            return "Guide"
        if batch.reviewer_id and str(batch.reviewer_id) == str(user.id):
            return "Reviewer"
        return "Coordinator"

    # ------------------------------------------------------------------ home

    async def pending(self, user: User, academic_year: str) -> dict:
        """
        What is waiting on this trainer, as counts only.

        Deliberately its own query rather than a call into `home` or
        `evidence`: this runs on every page load to draw a badge, so it must
        not pay for the batches, members, reviews and submissions those two
        load. It counts rows in the database and returns integers.

        Keyed by the nav destination, so a new badge later is a new key here
        rather than a new endpoint.
        """
        ids = await self.authority.managed_batch_ids(user, academic_year)
        if not ids:
            return {"counts": {}, "total": 0}

        waiting = (await self.db.execute(
            select(func.count())
            .select_from(BatchDocument)
            .where(BatchDocument.batch_id.in_(list(ids)))
            .where(BatchDocument.status == DocumentStatus.AWAITING_VERIFICATION)
            # A superseded row was replaced by a newer upload; nobody needs to
            # verify a version that is no longer current.
            .where(BatchDocument.superseded_by_id.is_(None))
        )).scalar() or 0

        # Only non-zero entries. A badge reading "0" is a worse answer than no
        # badge - it draws the eye to say nothing happened.
        counts = {k: v for k, v in {"/trainer/evidence": waiting}.items() if v}
        return {"counts": counts, "total": sum(counts.values())}

    async def home(self, user: User, academic_year: str) -> dict:
        """
        The worklist: what is waiting on this trainer, most urgent first.

        Every figure comes from the same scope the other screens use, so a count
        here always resolves to rows that can actually be opened.
        """
        rows = await self._scope(user, academic_year)
        story_state = await self._story_state([b.id for b in rows])
        now = datetime.utcnow()
        soon = now + timedelta(days=7)

        docs = (await self.db.execute(
            select(BatchDocument).where(BatchDocument.batch_id.in_([b.id for b in rows]))
        )).scalars().all() if rows else []
        awaiting_docs = [d for d in docs if d.status == DocumentStatus.AWAITING_VERIFICATION]
        missing_required = [d for d in docs
                            if d.is_required and d.status == DocumentStatus.MISSING]

        overdue, due_soon = [], []
        for b in rows:
            for r in b.reviews:
                if r.status != ReviewStatus.SCHEDULED:
                    continue
                entry = {
                    "id": str(r.id),
                    "batch_code": b.batch_code,
                    "batch_title": b.title,
                    "review_type": r.review_type,
                    "scheduled_at": r.scheduled_at,
                    "days": (r.scheduled_at - now).days,
                }
                if r.scheduled_at < now:
                    overdue.append(entry)
                elif r.scheduled_at <= soon:
                    due_soon.append(entry)
        overdue.sort(key=lambda e: e["scheduled_at"])
        due_soon.sort(key=lambda e: e["scheduled_at"])

        story_queue = sorted(
            (
                {
                    "batch_code": b.batch_code,
                    "batch_title": b.title,
                    "needs_review": story_state.get(str(b.id), {}).get("needs_review", 0),
                    "total": story_state.get(str(b.id), {}).get("total", 0),
                }
                for b in rows
                if story_state.get(str(b.id), {}).get("needs_review", 0)
            ),
            key=lambda e: -e["needs_review"],
        )
        stories_pending = sum(e["needs_review"] for e in story_queue)

        def plural(n, word, suffix="s"):
            return f"{word}{suffix if n != 1 else ''}"

        # One queue ordered by what actually blocks people. Anything at zero is
        # dropped rather than shown as a reassuring "0".
        attention = [
            {"id": "reviews_overdue", "count": len(overdue), "severity": "critical",
             "label": f"{len(overdue)} {plural(len(overdue), 'review')} overdue",
             "hint": "Students are waiting on a decision that was already due.",
             "href": "/trainer/reviews?status=overdue"},
            {"id": "required_missing", "count": len(missing_required), "severity": "critical",
             "label": f"{len(missing_required)} required "
                      f"{plural(len(missing_required), 'document')} missing",
             "hint": "A registration cannot be approved while these are absent.",
             "href": "/trainer/evidence"},
            {"id": "stories_pending", "count": stories_pending, "severity": "warning",
             "label": f"{stories_pending} AI-drafted "
                      f"{'story' if stories_pending == 1 else 'stories'} awaiting your review",
             "hint": "Nothing reaches a product backlog until you decide.",
             "href": "/trainer/ai-planning"},
            {"id": "documents_awaiting", "count": len(awaiting_docs), "severity": "warning",
             "label": f"{len(awaiting_docs)} {plural(len(awaiting_docs), 'document')} "
                      "awaiting verification",
             "hint": "Uploaded by students and not yet checked.",
             "href": "/trainer/evidence?status=outstanding"},
            {"id": "reviews_soon", "count": len(due_soon), "severity": "info",
             "label": f"{len(due_soon)} {plural(len(due_soon), 'review')} due this week",
             "hint": "Scheduled within the next seven days.",
             "href": "/trainer/reviews?status=scheduled"},
        ]
        attention = [a for a in attention if a["count"] > 0]

        behind = sorted(
            (
                {
                    "batch_code": b.batch_code,
                    "batch_title": b.title,
                    "section": b.section,
                    "progress": int(round(b.overall_progress or 0)),
                    "overdue": sum(1 for r in b.reviews
                                   if r.status == ReviewStatus.SCHEDULED and r.scheduled_at < now),
                }
                for b in rows
            ),
            key=lambda e: (-e["overdue"], e["progress"]),
        )[:5]

        students = sum(1 for b in rows for m in b.members if m.is_active)
        return {
            "trainer": _name(user),
            "academic_year": academic_year,
            "scope": {
                "batches": len(rows),
                "students": students,
                "average_progress": (
                    int(round(sum(b.overall_progress or 0 for b in rows) / len(rows)))
                    if rows else 0
                ),
            },
            "attention": attention,
            "clear": not attention,
            "overdue_reviews": overdue[:5],
            "story_queue": story_queue[:5],
            "needs_attention": behind,
        }

    # ------------------------------------------------------------ my batches

    # Status is not a stored column. Derived in one place so the column, the
    # filter and the KPI row can never disagree about what a word means.
    #
    # "Review" counts only a review that has come due - not one merely booked.
    # Nearly every batch has a future review on the calendar at all times, so
    # keying off any scheduled review labelled the whole list Review and left
    # In Progress permanently empty.
    @staticmethod
    def _list_status(progress: int, due_reviews: int) -> str:
        if progress >= 100:
            return "Completed"
        if due_reviews:
            return "Review"
        return "In Progress"

    async def batches(
        self,
        user: User,
        academic_year: str,
        *,
        search: Optional[str] = None,
        department: Optional[str] = None,
        section: Optional[str] = None,
        batch_no: Optional[str] = None,
        project_status: Optional[str] = None,
        semester: Optional[str] = None,
        guide: Optional[str] = None,
        batch_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort: str = "latest",
        page: int = 1,
        per_page: int = 10,
    ) -> dict:
        rows = await self._scope(user, academic_year)
        story_state = await self._story_state([b.id for b in rows])
        delivery = await self._delivery_state([b.id for b in rows])
        now = datetime.utcnow()

        cards = []
        for b in rows:
            members = [m for m in b.members if m.is_active]
            pending = [r for r in b.reviews if r.status == ReviewStatus.SCHEDULED]
            overdue = [r for r in pending if r.scheduled_at < now]
            stories = story_state.get(str(b.id), {})
            work = delivery.get(str(b.id), {})
            progress = int(round(b.overall_progress or 0))
            # "CSE-D-D1" -> "D1"; the sheet's Batch No, rebuilt from the code.
            tail = (b.batch_code or "").rsplit("-", 1)
            cards.append({
                "id": str(b.id),
                "batch_code": b.batch_code,
                "batch_no": tail[1] if len(tail) == 2 else None,
                "title": b.title,
                "section": b.section,
                "year": b.year,
                "semester": b.semester,
                "department": b.department,
                "project_type": b.project_type,
                "guide": b.guide.full_name if b.guide else None,
                "guide_id": str(b.guide_id) if b.guide_id else None,
                "my_role": self._role_on(b, user),
                "members": len(members),
                "team_size": b.team_size or 4,
                # Roll number first: it is the identifier a college actually
                # uses, and it is what distinguishes one student from another
                # on screen. Names alone are useless here - a roster whose
                # names all read "Student 22CS001" collapses to one initial.
                "team": [
                    {
                        "roll": (m.student.roll_number or "").upper(),
                        "name": m.student.full_name,
                    }
                    for m in members if m.student
                ],
                "student_names": [
                    m.student.full_name for m in members if m.student and m.student.full_name
                ],
                "progress": progress,
                "status": self._list_status(progress, len(overdue)),
                "registration_status": b.registration_status.value.replace("_", " ").title(),
                "registration_status_key": b.registration_status.value,
                "reviews_pending": len(pending),
                "reviews_overdue": len(overdue),
                "stories_total": stories.get("total", 0),
                "stories_needs_review": stories.get("needs_review", 0),
                "stories_in_backlog": stories.get("in_backlog", 0),
                "sprints_total": work.get("sprints", 0),
                "tasks_total": work.get("tasks", 0),
                "tasks_open": work.get("open", 0),
                "tasks_overdue": work.get("overdue", 0),
                "base_paper": (b.base_paper.status.value if b.base_paper else "missing"),
                "created_at": b.created_at,
            })

        # Options come from the whole scope, so a filter never hides its own
        # value and leave the control empty on the next render.
        def options(key: str) -> List[str]:
            return sorted({c[key] for c in cards if c.get(key)})

        filter_options = {
            "departments": options("department"),
            "sections": options("section"),
            "batch_nos": options("batch_no"),
            "semesters": options("semester"),
            "guides": options("guide"),
            "types": options("project_type"),
            "statuses": ["In Progress", "Review", "Completed"],
        }

        def keep(c: dict) -> bool:
            if search:
                needle = search.lower()
                blob = " ".join(filter(None, [
                    c["batch_code"], c["title"], c["section"], c["batch_no"], c["guide"],
                ])).lower()
                if needle not in blob:
                    return False
            if department and c["department"] != department:
                return False
            if section and c["section"] != section:
                return False
            if batch_no and c["batch_no"] != batch_no:
                return False
            if project_status and c["status"] != project_status:
                return False
            if semester and c["semester"] != semester:
                return False
            if guide and c["guide"] != guide:
                return False
            if batch_type and c["project_type"] != batch_type:
                return False
            created = c["created_at"]
            if date_from and created and created.date().isoformat() < date_from:
                return False
            if date_to and created and created.date().isoformat() > date_to:
                return False
            return True

        matched = [c for c in cards if keep(c)]

        SORTS = {
            "latest": lambda c: (c["created_at"] or datetime.min, c["batch_code"]),
            "oldest": lambda c: (c["created_at"] or datetime.min, c["batch_code"]),
            "code": lambda c: c["batch_code"] or "",
            "progress": lambda c: c["progress"],
            "students": lambda c: c["members"],
        }
        key = SORTS.get(sort, SORTS["latest"])
        matched.sort(key=key, reverse=sort in {"latest", "progress", "students"})

        # KPIs describe what is on screen: filter the list and they follow, so
        # the count in the header and the tiles above it always agree.
        completed = [c for c in matched if c["status"] == "Completed"]
        total = len(matched)
        per_page = max(1, min(per_page, 100))
        pages = max(1, ceil(total / per_page))
        page = max(1, min(page, pages))
        window = matched[(page - 1) * per_page: page * per_page]

        return {
            "academic_year": academic_year,
            "rows": window,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "sort": sort,
            "filters": filter_options,
            "stats": {
                "total_batches": total,
                "active_batches": total - len(completed),
                "completed_batches": len(completed),
                "pending_reviews": sum(c["reviews_pending"] for c in matched),
                "total_students": sum(c["members"] for c in matched),
            },
            "kpis": [
                {"id": "batches", "value": str(total), "label": "Batches"},
                {"id": "students", "value": str(sum(c["members"] for c in matched)),
                 "label": "Students"},
                {"id": "reviews", "value": str(sum(c["reviews_pending"] for c in matched)),
                 "label": "Reviews Pending"},
                {"id": "overdue", "value": str(sum(c["reviews_overdue"] for c in matched)),
                 "label": "Reviews Overdue"},
                {"id": "stories", "value": str(sum(c["stories_needs_review"] for c in matched)),
                 "label": "Stories to Review"},
            ],
        }

    async def _story_state(self, batch_ids: List) -> Dict[str, dict]:
        if not batch_ids:
            return {}
        rows = (await self.db.execute(
            select(ProjectUserStory.batch_id, ProjectUserStory.review_status,
                   ProjectUserStory.moved_to_backlog_at)
            .where(ProjectUserStory.batch_id.in_(batch_ids))
        )).all()
        out: Dict[str, dict] = defaultdict(
            lambda: {"total": 0, "needs_review": 0, "in_backlog": 0})
        for batch_id, status, moved_at in rows:
            entry = out[str(batch_id)]
            entry["total"] += 1
            if status == StoryReviewStatus.NEEDS_REVIEW:
                entry["needs_review"] += 1
            # What the User Stories screen can actually show: approved and
            # moved across. A batch mid-review has drafts but no backlog.
            if moved_at is not None:
                entry["in_backlog"] += 1
        return out

    async def _delivery_state(self, batch_ids: List) -> Dict[str, dict]:
        """
        Sprint and task counts per batch, for the Sprints and Tasks pickers.

        Two grouped reads rather than a query per card: the list shows 45
        batches, and 90 round trips to print two numbers each would be the
        whole cost of the screen.
        """
        if not batch_ids:
            return {}
        out: Dict[str, dict] = defaultdict(
            lambda: {"sprints": 0, "tasks": 0, "open": 0, "overdue": 0})

        for batch_id, in (await self.db.execute(
            select(ProjectSprint.batch_id).where(ProjectSprint.batch_id.in_(batch_ids))
        )).all():
            out[str(batch_id)]["sprints"] += 1

        today = datetime.utcnow().date()
        for batch_id, task_status, due in (await self.db.execute(
            select(ProjectTask.batch_id, ProjectTask.status, ProjectTask.due_date)
            .where(ProjectTask.batch_id.in_(batch_ids))
        )).all():
            entry = out[str(batch_id)]
            entry["tasks"] += 1
            if task_status != TaskStatus.DONE:
                entry["open"] += 1
                # Overdue is derived from the date every time it is asked for;
                # nothing stores it, so nothing can go stale overnight.
                if due and due < today:
                    entry["overdue"] += 1
        return out

    # --------------------------------------------------------------- reviews

    async def reviews(self, user: User, academic_year: str, *, status: Optional[str] = None) -> dict:
        rows = await self._scope(user, academic_year)
        by_batch = {str(b.id): b for b in rows}
        now = datetime.utcnow()

        entries = []
        for b in rows:
            for r in b.reviews:
                overdue = r.status == ReviewStatus.SCHEDULED and r.scheduled_at < now
                state = ("overdue" if overdue
                         else r.status.value)
                if status and status != "all" and state != status:
                    continue
                entries.append({
                    "id": str(r.id),
                    "batch_code": b.batch_code,
                    # The trainer can act on these, so the row carries what the
                    # mutation endpoints need rather than making the UI guess.
                    "can_complete": r.status == ReviewStatus.SCHEDULED,
                    "batch_title": b.title,
                    "section": b.section,
                    "review_type": r.review_type,
                    "scheduled_at": r.scheduled_at,
                    "status": state,
                    "status_label": ("Overdue" if overdue else r.status.value.title()),
                    "score": r.score,
                    "remarks": r.remarks,
                    "completed_at": r.completed_at,
                    "days_out": (r.scheduled_at - now).days,
                })
        entries.sort(key=lambda e: e["scheduled_at"])

        counts = Counter(e["status"] for e in entries)
        return {
            "rows": entries,
            "kpis": [
                {"id": "overdue", "value": str(counts.get("overdue", 0)), "label": "Overdue"},
                {"id": "scheduled", "value": str(counts.get("scheduled", 0)), "label": "Scheduled"},
                {"id": "completed", "value": str(counts.get("completed", 0)), "label": "Completed"},
                {"id": "batches", "value": str(len(by_batch)), "label": "Across Batches"},
            ],
            "statuses": ["all", "overdue", "scheduled", "completed", "cancelled"],
        }

    # ---------------------------------------------------------- student work

    async def student_work(self, user: User, academic_year: str,
                           *, batch: Optional[str] = None) -> dict:
        rows = await self._scope(user, academic_year)
        if batch:
            rows = [b for b in rows if b.batch_code == batch]

        batches = []
        for b in rows:
            stages = sorted(b.stage_progress, key=lambda s: s.stage.value)
            submissions = sorted(b.submissions, key=lambda s: s.submitted_at, reverse=True)
            pending = [s for s in submissions if s.status == SubmissionStatus.PENDING]
            batches.append({
                "batch_code": b.batch_code,
                "title": b.title,
                "section": b.section,
                "progress": int(round(b.overall_progress or 0)),
                "members": [
                    {
                        "name": _name(m.student),
                        "roll_number": m.student.roll_number if m.student else None,
                        "is_lead": bool(m.is_lead),
                        "responsibility": m.responsibility,
                    }
                    for m in sorted(b.members, key=lambda m: (not m.is_lead, str(m.student_id)))
                    if m.is_active
                ],
                "stages": [
                    {"stage": STAGE_LABELS.get(s.stage, s.stage.value),
                     "percent": int(round(s.percent or 0)),
                     "complete": (s.percent or 0) >= 100}
                    for s in stages
                ],
                # Built by the submissions service rather than projected here,
                # so the trainer's list and the faculty's cannot disagree about
                # what a submission is or who may act on it.
                "submissions": [
                    submission_service.row(s, can_manage=True) for s in submissions[:6]
                ],
                "pending_submissions": len(pending),
            })

        return {
            "rows": batches,
            "kpis": [
                {"id": "batches", "value": str(len(batches)), "label": "Batches"},
                {"id": "students", "value": str(sum(len(b["members"]) for b in batches)),
                 "label": "Students"},
                {"id": "pending", "value": str(sum(b["pending_submissions"] for b in batches)),
                 "label": "Awaiting Review"},
                {"id": "progress",
                 "value": f"{int(round(sum(b['progress'] for b in batches) / len(batches)))}%"
                          if batches else "—",
                 "label": "Average Progress"},
            ],
        }

    # -------------------------------------------------------------- evidence

    async def evidence(self, user: User, academic_year: str,
                       *, status: Optional[str] = None) -> dict:
        """
        Every artefact collected against the trainer's batches, in one list.

        Documents, base papers and submissions live in three tables because they
        behave differently; a trainer chasing missing evidence does not care, so
        they are folded into one view with a common verification state.
        """
        rows = await self._scope(user, academic_year)
        ids = [b.id for b in rows]
        by_id = {str(b.id): b for b in rows}

        documents = (await self.db.execute(
            select(BatchDocument).where(BatchDocument.batch_id.in_(ids))
        )).scalars().all() if ids else []

        items = []
        for d in documents:
            b = by_id.get(str(d.batch_id))
            if b is None:
                continue
            items.append({
                "kind": "Document",
                # Only documents have a decision endpoint. Base papers are
                # verified with the paper, and submissions have no decision
                # route yet - so the row says plainly whether it can be acted on
                # rather than offering a button that would fail.
                "id": str(d.id),
                "actionable": d.status != DocumentStatus.MISSING,
                "batch_code": b.batch_code,
                "name": d.name,
                "category": d.category,
                "state": d.status.value,
                "state_label": d.status.value.replace("_", " ").title(),
                "verified": d.status == DocumentStatus.VERIFIED,
                "required": bool(d.is_required),
                "at": d.uploaded_at,
            })
        for b in rows:
            if b.base_paper:
                items.append({
                    "kind": "Base Paper",
                    "id": None,
                    "actionable": False,
                    "batch_code": b.batch_code,
                    "name": b.base_paper.title or "Untitled paper",
                    "category": "Base Paper",
                    "state": b.base_paper.status.value,
                    "state_label": b.base_paper.status.value.title(),
                    "verified": b.base_paper.status == BasePaperStatus.VERIFIED,
                    "required": True,
                    "at": b.base_paper.uploaded_at,
                })
            for s in b.submissions:
                items.append({
                    "kind": "Submission",
                    "id": None,
                    "actionable": False,
                    "batch_code": b.batch_code,
                    "name": s.title or s.document_type,
                    "category": s.document_type,
                    "state": s.status.value,
                    "state_label": s.status.value.title(),
                    "verified": s.status == SubmissionStatus.VERIFIED,
                    "required": False,
                    "at": s.submitted_at,
                })

        if status and status != "all":
            wanted = status == "verified"
            items = [i for i in items if i["verified"] == wanted]

        items.sort(key=lambda i: (i["batch_code"], i["kind"], i["name"]))
        verified = sum(1 for i in items if i["verified"])
        missing = sum(1 for i in items if i["required"] and not i["verified"])

        return {
            "rows": items,
            "kpis": [
                {"id": "items", "value": str(len(items)), "label": "Artefacts"},
                {"id": "verified", "value": str(verified), "label": "Verified"},
                {"id": "outstanding", "value": str(len(items) - verified), "label": "Outstanding"},
                {"id": "required", "value": str(missing), "label": "Required & Missing"},
            ],
            "coverage": _pct(verified, len(items)),
        }

    # --------------------------------------------------------------- reports

    async def reports(self, user: User, academic_year: str) -> dict:
        rows = await self._scope(user, academic_year)
        story_state = await self._story_state([b.id for b in rows])
        now = datetime.utcnow()

        by_section: Dict[str, dict] = defaultdict(
            lambda: {"batches": 0, "students": 0, "progress": [], "pending": 0, "overdue": 0}
        )
        for b in rows:
            entry = by_section[b.section or "Unassigned"]
            entry["batches"] += 1
            entry["students"] += sum(1 for m in b.members if m.is_active)
            entry["progress"].append(b.overall_progress or 0)
            pending = [r for r in b.reviews if r.status == ReviewStatus.SCHEDULED]
            entry["pending"] += len(pending)
            entry["overdue"] += sum(1 for r in pending if r.scheduled_at < now)

        sections = [
            {
                "section": name,
                "batches": v["batches"],
                "students": v["students"],
                "progress": int(round(sum(v["progress"]) / len(v["progress"]))) if v["progress"] else 0,
                "reviews_pending": v["pending"],
                "reviews_overdue": v["overdue"],
            }
            for name, v in sorted(by_section.items())
        ]

        stage_totals: Dict[str, List[float]] = defaultdict(list)
        for b in rows:
            for s in b.stage_progress:
                stage_totals[STAGE_LABELS.get(s.stage, s.stage.value)].append(s.percent or 0)

        stories_total = sum(v["total"] for v in story_state.values())
        stories_pending = sum(v["needs_review"] for v in story_state.values())

        return {
            "academic_year": academic_year,
            "sections": sections,
            "stages": [
                {"stage": name, "percent": int(round(sum(v) / len(v)))}
                for name, v in stage_totals.items()
            ],
            "kpis": [
                {"id": "batches", "value": str(len(rows)), "label": "Batches"},
                {"id": "students",
                 "value": str(sum(1 for b in rows for m in b.members if m.is_active)),
                 "label": "Students"},
                {"id": "progress",
                 "value": f"{int(round(sum(b.overall_progress or 0 for b in rows) / len(rows)))}%"
                          if rows else "—",
                 "label": "Average Progress"},
                {"id": "stories", "value": f"{stories_total - stories_pending}/{stories_total}",
                 "label": "Stories Reviewed"},
            ],
        }

    # -------------------------------------------------------------- settings

    async def settings(self, user: User, academic_year: str) -> dict:
        assignments = (await self.db.execute(
            select(SectionFacultyAssignment)
            .where(SectionFacultyAssignment.faculty_id == user.id)
            .options(
                selectinload(SectionFacultyAssignment.section)
                .selectinload(AcademicSection.department)
            )
        )).scalars().all()
        scoped = [
            a for a in assignments
            if a.section and a.section.department
            and a.section.department.academic_year == academic_year
        ]

        offices = (await self.db.execute(
            select(AcademicDepartment)
            .where(AcademicDepartment.academic_year == academic_year)
            .where((AcademicDepartment.hod_id == user.id)
                   | (AcademicDepartment.dept_coordinator_id == user.id)
                   | (AcademicDepartment.project_coordinator_id == user.id))
        )).scalars().all()

        titles = []
        for d in offices:
            if str(d.hod_id) == str(user.id):
                titles.append({"department": d.code, "role": "Head of Department"})
            if str(d.dept_coordinator_id) == str(user.id):
                titles.append({"department": d.code, "role": "Department Coordinator"})
            if str(d.project_coordinator_id) == str(user.id):
                titles.append({"department": d.code, "role": "Project Coordinator"})

        managed = await self.authority.managed_batch_ids(user, academic_year)
        return {
            "profile": {
                "name": _name(user),
                "email": user.email,
                "department": user.department,
                "college": user.college_name,
                "role": user.role.value.title(),
            },
            "academic_year": academic_year,
            "section_roles": [
                {
                    "department": a.section.department.code,
                    "year": a.section.year,
                    "semester": a.section.semester,
                    "section": a.section.name,
                    "role": a.role,
                    "responsibility": a.responsibility,
                }
                for a in sorted(scoped, key=lambda a: (a.section.department.code,
                                                       a.section.year, a.section.name, a.role))
            ],
            "department_offices": titles,
            "managed_batches": len(managed),
        }
