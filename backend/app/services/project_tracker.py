"""
Everything the Project Tracking screen shows, assembled in one place.

The screen is one question asked at several zoom levels - how is the cohort
doing, which batches need me today, and what exactly is wrong with this one -
so the same definitions of phase and health have to hold at all three. They
live here rather than in the endpoint, because a batch that reads "Critical" in
the table and "On Track" in the side panel is worse than either being wrong.

Health is deliberately derived rather than stored. A stored flag is a promise
to keep it updated, and nobody does; a derived one cannot drift from the facts
it is drawn from.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.institution_time import humanise, local_today
from app.models.batch_detail import ActivityLog
from app.models.faculty import (
    BasePaperStatus,
    BatchStageProgress,
    ProjectBatch,
    ProjectReview,
    ProjectStage,
    ReviewStatus,
)
from app.models.project_tracking import (
    BatchIntegration,
    DeliverableStatus,
    ProjectDeliverable,
    ProjectTask,
    TaskStatus,
)
from app.models.user import User
from app.services.project_schedule import (
    describe,
    expected_progress,
    is_behind,
    schedule_state,
)

# The stage a batch is "in" is the first one not yet finished. Labels match the
# milestone timeline so the phase chip and the timeline never disagree.
STAGE_LABELS = {
    ProjectStage.TOPIC_APPROVAL: "Topic Approval",
    ProjectStage.BASE_PAPER: "Base Paper",
    ProjectStage.REQUIREMENTS: "Requirements",
    ProjectStage.SYSTEM_DESIGN: "Design",
    ProjectStage.DEVELOPMENT: "Development",
    ProjectStage.TESTING: "Testing",
    ProjectStage.DOCUMENTATION: "Documentation",
    ProjectStage.FINAL_REVIEW: "Final Review",
}
STAGE_ORDER = list(STAGE_LABELS.keys())

# The artefacts every batch owes. Created with the batch so a team can see the
# gap from day one rather than discovering it at submission.
STANDARD_DELIVERABLES = [
    "Source Code", "Requirements", "Design Document",
    "Test Report", "Presentation", "Demo URL", "Base Paper",
]

# Health bands.
ON_TRACK = "On Track"
AT_RISK = "At Risk"
NEEDS_ATTENTION = "Needs Attention"
CRITICAL = "Critical"

_COMPLETE = 99.5   # float percentages never land exactly on 100


def _stage_map(batch: ProjectBatch) -> Dict[ProjectStage, BatchStageProgress]:
    return {row.stage: row for row in (batch.stage_progress or [])}


def current_phase(batch: ProjectBatch) -> str:
    """The first stage that is not finished - what the team is working on now."""
    rows = _stage_map(batch)
    for stage in STAGE_ORDER:
        row = rows.get(stage)
        if row is None or (row.percent or 0) < _COMPLETE:
            return STAGE_LABELS[stage]
    return "Complete"


def _overdue_reviews(batch: ProjectBatch, now: datetime) -> int:
    return sum(1 for r in (batch.reviews or [])
               if r.status == ReviewStatus.SCHEDULED and r.scheduled_at < now)


def health_of(
    batch: ProjectBatch,
    tasks: Sequence[ProjectTask],
    now: datetime,
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """
    How much trouble this batch is in, and why.

    Four independent signals, because a project fails in more than one way: it
    can be behind its own schedule, blocked on somebody else, carrying overdue
    work, or missing the base paper that gates approval. The reasons travel
    with the verdict so the screen can say *why* rather than just showing a
    red chip.
    """
    today = today or local_today()
    reasons: List[str] = []

    expected = expected_progress(batch.start_date, batch.target_completion, today)
    behind = is_behind(batch.overall_progress, expected)
    if behind:
        reasons.append(describe(batch.overall_progress, expected))

    blocked = [t for t in tasks if t.status == TaskStatus.BLOCKED]
    if blocked:
        reasons.append(f"{len(blocked)} blocked task" + ("s" if len(blocked) > 1 else ""))

    overdue = [t for t in tasks
               if t.status != TaskStatus.DONE and t.due_date and t.due_date < today]
    if overdue:
        reasons.append(f"{len(overdue)} overdue task" + ("s" if len(overdue) > 1 else ""))

    late_reviews = _overdue_reviews(batch, now)
    if late_reviews:
        reasons.append(f"{late_reviews} review not recorded")

    bp = batch.base_paper
    if bp is None or bp.status == BasePaperStatus.MISSING:
        reasons.append("no base paper")

    inactive = sum(1 for m in (batch.members or []) if not m.is_active)
    if inactive:
        reasons.append(f"{inactive} inactive member" + ("s" if inactive > 1 else ""))

    # Blocked work is the loudest signal: unlike being behind, the team cannot
    # fix it alone. Two or more problems is also critical - they compound.
    if blocked or len(reasons) >= 3:
        label = CRITICAL
    elif behind or late_reviews:
        label = AT_RISK
    elif reasons:
        label = NEEDS_ATTENTION
    else:
        label = ON_TRACK

    return {
        "health": label,
        "reasons": reasons,
        "behind": behind,
        "expected_progress": None if expected is None else int(round(expected)),
        "schedule_state": schedule_state(batch.overall_progress, expected),
        "blocked_tasks": len(blocked),
        "overdue_tasks": len(overdue),
        "overdue_reviews": late_reviews,
    }


class ProjectTracker:
    """Reads for the tracking screen. All queries are confined to one college."""

    def __init__(self, db: AsyncSession, college_id=None):
        self.db = db
        self.college_id = college_id

    # ---------------------------------------------------------------- helpers

    def _mine(self, stmt):
        if self.college_id:
            return stmt.where(ProjectBatch.college_id == self.college_id)
        return stmt

    async def _batches(
        self,
        academic_year: str,
        department: Optional[str] = None,
        section: Optional[str] = None,
        year: Optional[str] = None,
        semester: Optional[str] = None,
        guide_id: Optional[str] = None,
    ) -> List[ProjectBatch]:
        stmt = (
            self._mine(select(ProjectBatch))
            .options(
                selectinload(ProjectBatch.members),
                selectinload(ProjectBatch.base_paper),
                selectinload(ProjectBatch.reviews),
                selectinload(ProjectBatch.stage_progress),
                selectinload(ProjectBatch.guide),
            )
            .where(ProjectBatch.academic_year == academic_year)
            .where(ProjectBatch.is_active.is_(True))
        )
        if department:
            stmt = stmt.where(ProjectBatch.department == department)
        if section:
            stmt = stmt.where(ProjectBatch.section == section)
        if year:
            stmt = stmt.where(ProjectBatch.year == year)
        if semester:
            stmt = stmt.where(ProjectBatch.semester == semester)
        if guide_id:
            stmt = stmt.where(ProjectBatch.guide_id == guide_id)
        return list((await self.db.execute(stmt)).scalars().unique().all())

    async def _tasks_by_batch(self, batch_ids) -> Dict[str, List[ProjectTask]]:
        if not batch_ids:
            return {}
        rows = (await self.db.execute(
            select(ProjectTask)
            .options(selectinload(ProjectTask.assignee))
            .where(ProjectTask.batch_id.in_(batch_ids))
        )).scalars().unique().all()
        out: Dict[str, List[ProjectTask]] = {}
        for t in rows:
            out.setdefault(str(t.batch_id), []).append(t)
        return out

    async def _deliverables_by_batch(self, batch_ids) -> Dict[str, List[ProjectDeliverable]]:
        if not batch_ids:
            return {}
        rows = (await self.db.execute(
            select(ProjectDeliverable)
            .where(ProjectDeliverable.batch_id.in_(batch_ids))
            .order_by(ProjectDeliverable.position)
        )).scalars().all()
        out: Dict[str, List[ProjectDeliverable]] = {}
        for d in rows:
            out.setdefault(str(d.batch_id), []).append(d)
        return out

    # ------------------------------------------------------------------ table

    async def overview(
        self,
        academic_year: str,
        department: Optional[str] = None,
        section: Optional[str] = None,
        year: Optional[str] = None,
        semester: Optional[str] = None,
        guide_id: Optional[str] = None,
        phase: Optional[str] = None,
        health: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 10,
    ) -> Dict[str, Any]:
        """The whole screen above the fold: counters, then the filtered table."""
        now = datetime.utcnow()
        today = local_today()

        batches = await self._batches(
            academic_year, department, section, year, semester, guide_id)
        ids = [b.id for b in batches]
        tasks = await self._tasks_by_batch(ids)
        deliverables = await self._deliverables_by_batch(ids)

        rows = []
        for b in batches:
            bt = tasks.get(str(b.id), [])
            bd = deliverables.get(str(b.id), [])
            verdict = health_of(b, bt, now, today)
            stages = _stage_map(b)
            done_stages = sum(1 for s in STAGE_ORDER
                              if (stages.get(s).percent if stages.get(s) else 0) >= _COMPLETE)
            rows.append({
                "id": str(b.id),
                "batch_code": b.batch_code,
                "title": b.title,
                "section": b.section,
                "department": b.department,
                "guide_name": b.guide.full_name if b.guide else None,
                "guide_id": str(b.guide_id) if b.guide_id else None,
                "members": [
                    {"id": str(m.student_id), "is_active": m.is_active}
                    for m in (b.members or [])
                ],
                "member_count": len(b.members or []),
                "active_members": sum(1 for m in (b.members or []) if m.is_active),
                "current_phase": current_phase(b),
                "progress": int(round(b.overall_progress or 0)),
                "milestones_done": done_stages,
                "milestones_total": len(STAGE_ORDER),
                "tasks_done": sum(1 for t in bt if t.status == TaskStatus.DONE),
                "tasks_total": len(bt),
                "deliverables_done": sum(
                    1 for d in bd if d.status == DeliverableStatus.VERIFIED),
                "deliverables_total": len(bd),
                "next_due": self._next_due(b, bt, now),
                "last_activity": None,   # filled below in one query
                **verdict,
            })

        # Last activity, one query rather than one per row.
        if ids:
            latest = (await self.db.execute(
                select(ActivityLog.batch_id, func.max(ActivityLog.occurred_at))
                .where(ActivityLog.batch_id.in_(ids))
                .group_by(ActivityLog.batch_id)
            )).all()
            seen = {str(bid): at for bid, at in latest}
            for r in rows:
                at = seen.get(r["id"])
                r["last_activity"] = humanise(at) if at else None

        # Filters that depend on the derived values have to run after them.
        if phase and phase.lower() not in ("all", ""):
            rows = [r for r in rows if r["current_phase"] == phase]
        if health and health.lower() not in ("all", ""):
            rows = [r for r in rows if r["health"] == health]
        if search:
            needle = search.strip().lower()
            rows = [r for r in rows if needle in " ".join(
                str(x or "") for x in (r["batch_code"], r["title"], r["guide_name"])
            ).lower()]

        rows.sort(key=lambda r: (
            {CRITICAL: 0, AT_RISK: 1, NEEDS_ATTENTION: 2, ON_TRACK: 3}[r["health"]],
            r["batch_code"],
        ))

        total = len(rows)
        start = max(0, (page - 1) * per_page)
        page_rows = rows[start:start + per_page]

        return {
            "kpis": self._kpis(rows, batches, tasks, deliverables, now, today),
            "rows": page_rows,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max(1, -(-total // per_page)),
            "academic_year": academic_year,
        }

    def _next_due(self, batch: ProjectBatch, tasks, now: datetime) -> Optional[Dict[str, Any]]:
        """The next thing with a date on it - a review or a task, whichever is sooner."""
        candidates = []
        for r in (batch.reviews or []):
            if r.status == ReviewStatus.SCHEDULED and r.scheduled_at >= now:
                candidates.append((r.scheduled_at.date(), r.review_type))
        for t in tasks:
            if t.status != TaskStatus.DONE and t.due_date:
                candidates.append((t.due_date, t.title))
        if not candidates:
            return None
        when, what = min(candidates, key=lambda x: x[0])
        return {"label": what, "date": when.isoformat(),
                "display": when.strftime("%d %b")}

    def _kpis(self, rows, batches, tasks, deliverables, now, today) -> List[Dict[str, Any]]:
        all_tasks = [t for group in tasks.values() for t in group]
        done = [t for t in all_tasks if t.status == TaskStatus.DONE]
        overdue = [t for t in all_tasks
                   if t.status != TaskStatus.DONE and t.due_date and t.due_date < today]
        blocked_batches = sum(1 for r in rows if r["blocked_tasks"])
        milestones_done = sum(r["milestones_done"] for r in rows)
        milestones_total = sum(r["milestones_total"] for r in rows)
        reviews_due = sum(
            1 for b in batches for r in (b.reviews or [])
            if r.status == ReviewStatus.SCHEDULED and now <= r.scheduled_at <= now + timedelta(days=7)
        )
        avg = round(sum(r["progress"] for r in rows) / len(rows)) if rows else 0
        return [
            {"id": "active", "value": len(rows), "label": "Active Projects"},
            {"id": "progress", "value": f"{avg}%", "label": "Portfolio Progress"},
            {"id": "milestones", "value": f"{milestones_done} / {milestones_total}",
             "label": "Milestones Done"},
            {"id": "tasks", "value": f"{len(done)} / {len(all_tasks)}",
             "label": "Tasks Completed"},
            {"id": "overdue", "value": len(overdue), "label": "Overdue Tasks",
             "tone": "warn" if overdue else "ok"},
            {"id": "blocked", "value": blocked_batches, "label": "Blocked Projects",
             "tone": "danger" if blocked_batches else "ok"},
            {"id": "reviews", "value": reviews_due, "label": "Reviews Due"},
        ]

    # ----------------------------------------------------------------- detail

    async def detail(self, identifier: str, academic_year: str) -> Optional[Dict[str, Any]]:
        """One project in full: the side panel and the three lower cards."""
        stmt = (
            self._mine(select(ProjectBatch))
            .options(
                selectinload(ProjectBatch.members),
                selectinload(ProjectBatch.base_paper),
                selectinload(ProjectBatch.reviews),
                selectinload(ProjectBatch.stage_progress),
                selectinload(ProjectBatch.guide),
            )
            .where(ProjectBatch.batch_code == identifier)
        )
        batch = (await self.db.execute(stmt)).scalars().unique().first()
        if batch is None:
            return None

        now, today = datetime.utcnow(), local_today()
        tasks = (await self._tasks_by_batch([batch.id])).get(str(batch.id), [])
        deliverables = (await self._deliverables_by_batch([batch.id])).get(str(batch.id), [])
        verdict = health_of(batch, tasks, now, today)

        members = (await self.db.execute(
            select(User).where(User.id.in_([m.student_id for m in (batch.members or [])]))
        )).scalars().all() if batch.members else []
        names = {str(u.id): u.full_name for u in members}

        integrations = (await self.db.execute(
            select(BatchIntegration).where(BatchIntegration.batch_id == batch.id)
        )).scalars().all()

        activity = (await self.db.execute(
            select(ActivityLog)
            .where(ActivityLog.batch_id == batch.id)
            .order_by(ActivityLog.occurred_at.desc())
            .limit(8)
        )).scalars().all()

        stages = _stage_map(batch)
        return {
            "batch_code": batch.batch_code,
            "title": batch.title,
            "progress": int(round(batch.overall_progress or 0)),
            "current_phase": current_phase(batch),
            "guide_name": batch.guide.full_name if batch.guide else None,
            "team": [
                {"id": str(m.student_id),
                 "name": names.get(str(m.student_id), "Student"),
                 "is_lead": m.is_lead,
                 "is_active": m.is_active}
                for m in (batch.members or [])
            ],
            "integrations": [
                {"kind": i.kind.value, "state": i.state.value,
                 "detail": i.detail, "url": i.url}
                for i in integrations
            ],
            "workstreams": [
                {"stage": s.value,
                 "label": STAGE_LABELS[s],
                 "percent": int(round((stages.get(s).percent if stages.get(s) else 0)))}
                for s in STAGE_ORDER
            ],
            "milestones": [
                {"stage": s.value,
                 "label": STAGE_LABELS[s],
                 "planned": (stages.get(s).planned_date.isoformat()
                             if stages.get(s) and stages.get(s).planned_date else None),
                 "actual": (stages.get(s).completed_at.date().isoformat()
                            if stages.get(s) and stages.get(s).completed_at else None),
                 "percent": int(round((stages.get(s).percent if stages.get(s) else 0))),
                 "status": self._milestone_status(stages.get(s), today)}
                for s in STAGE_ORDER
            ],
            "tasks": [self._task_row(t, today) for t in sorted(
                tasks, key=lambda t: (t.status == TaskStatus.DONE,
                                      t.due_date or date.max))],
            "deliverables": [
                {"id": str(d.id), "name": d.name, "progress": d.progress,
                 "status": d.status.value, "evidence_url": d.evidence_url}
                for d in deliverables
            ],
            "activity": [
                {"code": a.event_code,
                 "summary": a.activity,
                 "module": a.module,
                 "actor": a.actor_name,
                 "at": humanise(a.occurred_at)}
                for a in activity
            ],
            **verdict,
        }

    @staticmethod
    def _milestone_status(row: Optional[BatchStageProgress], today: date) -> str:
        if row is None or not (row.percent or 0):
            if row is not None and row.planned_date and row.planned_date < today:
                return "Overdue"
            return "Upcoming"
        if (row.percent or 0) >= _COMPLETE:
            return "Complete"
        if row.planned_date and row.planned_date < today:
            return "Overdue"
        return "In Progress"

    @staticmethod
    def _task_row(t: ProjectTask, today: date) -> Dict[str, Any]:
        overdue = (t.status != TaskStatus.DONE and t.due_date and t.due_date < today)
        return {
            "id": str(t.id),
            "title": t.title,
            "assignee": t.assignee.full_name if t.assignee else None,
            "assignee_id": str(t.assignee_id) if t.assignee_id else None,
            "priority": t.priority.value,
            "status": t.status.value,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "due_display": t.due_date.strftime("%d %b") if t.due_date else None,
            "overdue": bool(overdue),
            "blocked_reason": t.blocked_reason,
        }

    # ----------------------------------------------------------------- alerts

    async def alerts(self, academic_year: str) -> Dict[str, Any]:
        """The counters in the corner, and what is coming up across the cohort."""
        now, today = datetime.utcnow(), local_today()
        batches = await self._batches(academic_year)
        ids = [b.id for b in batches]
        tasks = await self._tasks_by_batch(ids)

        blocked = inactive = 0
        upcoming: List[Dict[str, Any]] = []
        for b in batches:
            bt = tasks.get(str(b.id), [])
            v = health_of(b, bt, now, today)
            if v["blocked_tasks"]:
                blocked += 1
            if any(not m.is_active for m in (b.members or [])):
                inactive += 1
            nxt = self._next_due(b, bt, now)
            if nxt:
                upcoming.append({"batch_code": b.batch_code, "health": v["health"], **nxt})

        all_tasks = [t for g in tasks.values() for t in g]
        overdue = sum(1 for t in all_tasks
                      if t.status != TaskStatus.DONE and t.due_date and t.due_date < today)
        unconnected = len(batches) - (await self.db.scalar(
            select(func.count(func.distinct(BatchIntegration.batch_id)))
            .where(BatchIntegration.batch_id.in_(ids))
        ) or 0) if ids else 0

        upcoming.sort(key=lambda u: u["date"])
        return {
            "alerts": [
                {"id": "blocked", "count": blocked, "label": "Projects blocked", "tone": "danger"},
                {"id": "overdue", "count": overdue, "label": "Overdue tasks", "tone": "warn"},
                {"id": "inactive", "count": inactive, "label": "Inactive teams", "tone": "warn"},
                {"id": "repos", "count": max(0, unconnected),
                 "label": "Repositories not connected", "tone": "slate"},
            ],
            "upcoming": upcoming[:6],
        }

    # ------------------------------------------------------- cohort-wide tabs
    #
    # The table answers "which projects need me". These answer "what is
    # outstanding across every project" - the same rows regrouped by the thing
    # rather than by the batch, which is how a coordinator chases one kind of
    # work at a time.

    async def milestones(self, academic_year: str, **filters) -> Dict[str, Any]:
        """Every milestone in the cohort, soonest first, overdue at the top."""
        today = local_today()
        batches = await self._batches(academic_year, **filters)
        rows = []
        for b in batches:
            stages = _stage_map(b)
            for stage in STAGE_ORDER:
                row = stages.get(stage)
                status = ProjectTracker._milestone_status(row, today)
                if status == "Complete":
                    continue
                rows.append({
                    "batch_code": b.batch_code,
                    "title": b.title,
                    "guide_name": b.guide.full_name if b.guide else None,
                    "label": STAGE_LABELS[stage],
                    "planned": (row.planned_date.isoformat()
                                if row and row.planned_date else None),
                    "percent": int(round(row.percent if row else 0)),
                    "status": status,
                })
        rows.sort(key=lambda r: (r["status"] != "Overdue", r["planned"] or "9999"))
        return {"items": rows, "count": len(rows)}

    async def tasks(self, academic_year: str, only_open: bool = True,
                    **filters) -> Dict[str, Any]:
        """Every task, blocked first, then overdue, then by due date."""
        today = local_today()
        batches = await self._batches(academic_year, **filters)
        by_batch = {str(b.id): b for b in batches}
        grouped = await self._tasks_by_batch([b.id for b in batches])
        rows = []
        for batch_id, group in grouped.items():
            b = by_batch.get(batch_id)
            if b is None:
                continue
            for t in group:
                if only_open and t.status == TaskStatus.DONE:
                    continue
                row = ProjectTracker._task_row(t, today)
                # `title` is the task's own. The project's goes under a
                # separate key - overwriting it printed the project name in
                # the task column and lost the task entirely.
                row.update({"batch_code": b.batch_code,
                            "project_title": b.title,
                            "guide_name": b.guide.full_name if b.guide else None})
                rows.append(row)
        rows.sort(key=lambda r: (
            r["status"] != "blocked", not r["overdue"], r["due_date"] or "9999"))
        return {"items": rows, "count": len(rows)}

    async def deliverables(self, academic_year: str, **filters) -> Dict[str, Any]:
        """Every deliverable, least finished first."""
        batches = await self._batches(academic_year, **filters)
        by_batch = {str(b.id): b for b in batches}
        grouped = await self._deliverables_by_batch([b.id for b in batches])
        rows = []
        for batch_id, group in grouped.items():
            b = by_batch.get(batch_id)
            if b is None:
                continue
            for d in group:
                rows.append({
                    "id": str(d.id), "batch_code": b.batch_code, "title": b.title,
                    "name": d.name, "progress": d.progress,
                    "status": d.status.value, "evidence_url": d.evidence_url,
                })
        rows.sort(key=lambda r: (r["progress"], r["batch_code"]))
        return {"items": rows, "count": len(rows)}

    async def activity(self, academic_year: str, limit: int = 60,
                       **filters) -> Dict[str, Any]:
        """The cohort's activity feed, newest first."""
        batches = await self._batches(academic_year, **filters)
        ids = [b.id for b in batches]
        codes = {str(b.id): b.batch_code for b in batches}
        if not ids:
            return {"items": [], "count": 0}
        rows = (await self.db.execute(
            select(ActivityLog)
            .where(ActivityLog.batch_id.in_(ids))
            .order_by(ActivityLog.occurred_at.desc())
            .limit(limit)
        )).scalars().all()
        return {
            "items": [{
                "code": a.event_code,
                "batch_code": codes.get(str(a.batch_id), "—"),
                "summary": a.activity,
                "module": a.module,
                "actor": a.actor_name,
                "at": humanise(a.occurred_at),
            } for a in rows],
            "count": len(rows),
        }

    # ---------------------------------------------------------------- insight

    async def insight(self, academic_year: str) -> Dict[str, Any]:
        """
        The one sentence worth putting at the bottom of the screen.

        Derived from the data rather than generated: the projects most likely
        to miss their next milestone are the ones already behind *and* carrying
        a blocker, which is arithmetic, not judgement. A model is not needed
        for it, and using one would make the sentence unreproducible and put a
        running cost against a screen refresh.
        """
        now, today = datetime.utcnow(), local_today()
        batches = await self._batches(academic_year)
        tasks = await self._tasks_by_batch([b.id for b in batches])

        at_risk = []
        for b in batches:
            bt = tasks.get(str(b.id), [])
            v = health_of(b, bt, now, today)
            if v["health"] == CRITICAL:
                at_risk.append((b.batch_code, v["reasons"]))
        at_risk.sort(key=lambda x: -len(x[1]))

        if not at_risk:
            return {"headline": "No project is currently critical.",
                    "codes": [], "causes": []}

        codes = [c for c, _ in at_risk[:2]]
        causes = Counter()
        for _, reasons in at_risk:
            for r in reasons:
                causes[r.split(" ", 1)[-1] if r[0].isdigit() else r] += 1
        top = [c for c, _ in causes.most_common(3)]
        listed = " and ".join(codes) if len(codes) > 1 else codes[0]
        return {
            "headline": (
                f"{listed} may miss their next milestone."
                if len(codes) > 1 else f"{listed} may miss its next milestone."
            ),
            "detail": "Across the critical projects the commonest causes are "
                      + ", ".join(top) + "."
            if top else "",
            "codes": codes,
            "causes": top,
            "critical_count": len(at_risk),
        }
