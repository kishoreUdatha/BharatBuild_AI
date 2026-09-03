"""
The Tasks & Blockers screen: board, register, blocker queue and analysis.

Kept apart from `project_tracker`, which answers "how are the projects doing".
This answers "what is stopping work and who is clearing it" - a different
question with a different unit. There the row is a project; here it is a task
or a blocker, and a coordinator working this screen is chasing people rather
than reviewing progress.

Three things are derived rather than stored, for the same reason health is in
the tracker: a stored figure is a promise to keep it updated.

* **Age** - days since a task was created or a blocker reported.
* **Capacity** - a student's open workload against a normal load. Nobody
  maintains a per-student capacity field, so one taken from the roster would
  be wrong within a fortnight.
* **SLA bands** - resolution time bucketed from the two timestamps.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.institution_time import humanise, local_today
from app.models.faculty import ProjectBatch, ProjectStage
from app.models.project_tracking import (
    BlockerCategory,
    BlockerStatus,
    ProjectBlocker,
    ProjectTask,
    TaskAttachment,
    TaskComment,
    TaskDependency,
    TaskPriority,
    TaskStatus,
)
from app.models.user import User
from app.services.project_tracker import STAGE_LABELS

# What one student can reasonably carry at once. Used only to express load as
# a percentage; it is a yardstick, not a limit, and nothing is refused for
# exceeding it.
NORMAL_LOAD = 8

CATEGORY_LABELS = {
    BlockerCategory.TECHNICAL: "Technical / API",
    BlockerCategory.DATA: "Data / Dataset",
    BlockerCategory.APPROVAL: "Approval / Review",
    BlockerCategory.TEAM: "Team / Ownership",
    BlockerCategory.DOCUMENTATION: "Documentation",
}

BOARD_COLUMNS = [
    (TaskStatus.OPEN, "To Do"),
    (TaskStatus.IN_PROGRESS, "In Progress"),
    (TaskStatus.BLOCKED, "Blocked"),
    (TaskStatus.DONE, "Done"),
]


def _days(since: Optional[datetime], until: Optional[datetime] = None) -> Optional[int]:
    if since is None:
        return None
    return max(0, ((until or datetime.utcnow()) - since).days)


class TaskBoard:
    """Reads for the Tasks & Blockers screen, confined to one college."""

    def __init__(self, db: AsyncSession, college_id=None):
        self.db = db
        self.college_id = college_id

    # ---------------------------------------------------------------- loading

    async def _batches(self, academic_year: str, **f) -> List[ProjectBatch]:
        stmt = (
            select(ProjectBatch)
            .options(selectinload(ProjectBatch.members),
                     selectinload(ProjectBatch.guide))
            .where(ProjectBatch.academic_year == academic_year)
            .where(ProjectBatch.is_active.is_(True))
        )
        if self.college_id:
            stmt = stmt.where(ProjectBatch.college_id == self.college_id)
        for column, value in (
            (ProjectBatch.department, f.get("department")),
            (ProjectBatch.section, f.get("section")),
            (ProjectBatch.year, f.get("year")),
            (ProjectBatch.semester, f.get("semester")),
            (ProjectBatch.batch_code, f.get("batch_code")),
            (ProjectBatch.guide_id, f.get("guide_id")),
        ):
            if value:
                stmt = stmt.where(column == value)
        return list((await self.db.execute(stmt)).scalars().unique().all())

    async def _tasks(self, batch_ids) -> List[ProjectTask]:
        if not batch_ids:
            return []
        return list((await self.db.execute(
            select(ProjectTask)
            .options(selectinload(ProjectTask.assignee))
            .where(ProjectTask.batch_id.in_(batch_ids))
        )).scalars().unique().all())

    async def _counts(self, task_ids) -> Dict[str, Dict[str, int]]:
        """Comment, attachment and dependency counts, three queries not 3N."""
        out: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"comments": 0, "attachments": 0, "dependencies": 0})
        if not task_ids:
            return out
        for model, key, column in (
            (TaskComment, "comments", TaskComment.task_id),
            (TaskAttachment, "attachments", TaskAttachment.task_id),
            (TaskDependency, "dependencies", TaskDependency.task_id),
        ):
            rows = (await self.db.execute(
                select(column, func.count()).where(column.in_(task_ids)).group_by(column)
            )).all()
            for task_id, n in rows:
                out[str(task_id)][key] = n
        return out

    async def _blockers(self, batch_ids) -> List[ProjectBlocker]:
        if not batch_ids:
            return []
        return list((await self.db.execute(
            select(ProjectBlocker)
            .options(selectinload(ProjectBlocker.reported_by),
                     selectinload(ProjectBlocker.resolution_owner),
                     selectinload(ProjectBlocker.task))
            .where(ProjectBlocker.batch_id.in_(batch_ids))
        )).scalars().unique().all())

    # ------------------------------------------------------------ serialising

    def _task_row(self, t: ProjectTask, batch: ProjectBatch,
                  counts: Dict[str, Dict[str, int]], today: date) -> Dict[str, Any]:
        overdue = (t.status != TaskStatus.DONE and t.due_date and t.due_date < today)
        c = counts.get(str(t.id), {"comments": 0, "attachments": 0, "dependencies": 0})
        stage = None
        if t.stage:
            try:
                stage = STAGE_LABELS[ProjectStage(str(t.stage).lower())]
            except (ValueError, KeyError):
                stage = str(t.stage).replace("_", " ").title()
        return {
            "id": str(t.id),
            "title": t.title,
            "batch_code": batch.batch_code,
            "project_title": batch.title,
            "assignee": t.assignee.full_name if t.assignee else None,
            "assignee_id": str(t.assignee_id) if t.assignee_id else None,
            "priority": t.priority.value,
            "status": t.status.value,
            "progress": t.progress or 0,
            "stage": stage,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "due_display": t.due_date.strftime("%d %b") if t.due_date else None,
            "created_display": t.created_at.strftime("%d %b") if t.created_at else None,
            "age_days": _days(t.created_at),
            "overdue": bool(overdue),
            "blocked_reason": t.blocked_reason,
            "comments": c["comments"],
            "attachments": c["attachments"],
            "dependencies": c["dependencies"],
        }

    def _blocker_row(self, b: ProjectBlocker, codes: Dict[str, str]) -> Dict[str, Any]:
        age = _days(b.reported_at, b.resolved_at)
        return {
            "id": str(b.id),
            "title": b.title,
            "batch_code": codes.get(str(b.batch_id), "—"),
            "category": b.category.value,
            "category_label": CATEGORY_LABELS.get(b.category, b.category.value),
            "severity": b.severity.value,
            "status": b.status.value,
            "root_cause": b.root_cause,
            "impact": b.impact,
            "reported_by": b.reported_by.full_name if b.reported_by else None,
            "reported_at": humanise(b.reported_at) if b.reported_at else None,
            "owner": b.resolution_owner.full_name if b.resolution_owner else None,
            "owner_id": str(b.resolution_owner_id) if b.resolution_owner_id else None,
            "target_resolution": (b.target_resolution.isoformat()
                                  if b.target_resolution else None),
            "resolved_at": humanise(b.resolved_at) if b.resolved_at else None,
            "resolution_note": b.resolution_note,
            "task_title": b.task.title if b.task else None,
            "age_days": age,
        }

    # ------------------------------------------------------------------ board

    async def board(self, academic_year: str, **f) -> Dict[str, Any]:
        """Counters, the four board columns, and the register beneath them."""
        today = local_today()
        batches = await self._batches(academic_year, **f)
        by_id = {str(b.id): b for b in batches}
        tasks = await self._tasks([b.id for b in batches])
        counts = await self._counts([t.id for t in tasks])

        # The batch and team dropdowns are built from everything in the branch
        # and section, not from the current selection. Built from the filtered
        # set they collapsed to the one batch already chosen, so switching team
        # meant clearing the filter first.
        scope = {k: v for k, v in f.items() if k != "batch_code"}
        catalogue_batches = (batches if not f.get("batch_code")
                             else await self._batches(academic_year, **scope))

        rows = [self._task_row(t, by_id[str(t.batch_id)], counts, today)
                for t in tasks if str(t.batch_id) in by_id]

        # Filters that need the derived values run after them.
        if f.get("assignee_id"):
            rows = [r for r in rows if r["assignee_id"] == str(f["assignee_id"])]
        if f.get("priority"):
            rows = [r for r in rows if r["priority"] == str(f["priority"]).lower()]
        if f.get("status"):
            rows = [r for r in rows if r["status"] == str(f["status"]).lower()]
        if f.get("unassigned"):
            rows = [r for r in rows if not r["assignee_id"]]
        if f.get("due") == "overdue":
            rows = [r for r in rows if r["overdue"]]
        elif f.get("due") == "today":
            rows = [r for r in rows if r["due_date"] == today.isoformat()]
        elif f.get("due") == "week":
            horizon = (today + timedelta(days=7)).isoformat()
            rows = [r for r in rows
                    if r["due_date"] and today.isoformat() <= r["due_date"] <= horizon]
        if f.get("search"):
            needle = str(f["search"]).strip().lower()
            rows = [r for r in rows if needle in " ".join(str(x or "") for x in (
                r["title"], r["batch_code"], r["project_title"],
                r["assignee"], r["blocked_reason"])).lower()]

        columns = []
        for status, label in BOARD_COLUMNS:
            in_column = [r for r in rows if r["status"] == status.value]
            in_column.sort(key=lambda r: (
                not r["overdue"],
                {"high": 0, "medium": 1, "low": 2}[r["priority"]],
                r["due_date"] or "9999",
            ))
            columns.append({"status": status.value, "label": label,
                            "count": len(in_column), "cards": in_column[:25]})

        return {
            "kpis": self._kpis(rows, today),
            "options": await self._options(catalogue_batches, batches, tasks),
            "columns": columns,
            "rows": sorted(rows, key=lambda r: (
                {"critical": 0, "high": 0, "medium": 1, "low": 2}.get(r["priority"], 1),
                not r["overdue"], r["due_date"] or "9999")),
            "total": len(rows),
            "academic_year": academic_year,
        }

    async def _options(self, catalogue_batches, selected, tasks) -> Dict[str, Any]:
        """
        What the dropdowns should offer.

        The people list is the *team roster*, not the set of students who
        happen to have tasks. Those differ, and the difference is the useful
        part: CSE-B-003 has four members and only three carry work, so the
        fourth - inactive, nothing assigned - is exactly the person a
        coordinator opened this screen to find. Building the list from tasks
        made her invisible.
        """
        # Each batch carries its own branch, section and team number, so the
        # screen can narrow one dropdown by the one above it without a round
        # trip per level. The team number is the trailing part of the code -
        # CSE-A-007 is team 7 of section A - which is how a coordinator refers
        # to them out loud.
        catalogue = []
        for b in sorted(catalogue_batches, key=lambda x: x.batch_code):
            parts = b.batch_code.split("-")
            team = parts[-1] if len(parts) > 1 and parts[-1].isdigit() else None
            catalogue.append({
                "code": b.batch_code,
                "department": b.department,
                "section": b.section,
                "team": team,
                "team_label": (f"Team {int(team)}" if team else b.batch_code),
            })

        # The roster follows the *selection*, not the catalogue. The catalogue
        # stays wide so the batch dropdown does not collapse to the one already
        # chosen; using it here instead listed every student in the section.
        member_ids = {str(m.student_id) for b in selected for m in (b.members or [])}
        inactive = {str(m.student_id) for b in selected for m in (b.members or [])
                    if not m.is_active}
        loaded = 0
        names: Dict[str, str] = {}
        if member_ids:
            rows = (await self.db.execute(
                select(User).where(User.id.in_(list(member_ids)))
            )).scalars().all()
            names = {str(u.id): u.full_name or u.email for u in rows}
            loaded = len(rows)

        # Whoever already has work, in case a task was assigned to somebody
        # who has since left the team - they still need to be selectable.
        for t in tasks:
            if t.assignee_id and t.assignee:
                names.setdefault(str(t.assignee_id), t.assignee.full_name)

        with_tasks = {str(t.assignee_id) for t in tasks if t.assignee_id}
        assignees = [
            {"id": k,
             "name": v,
             "is_active": k not in inactive,
             "has_tasks": k in with_tasks}
            for k, v in sorted(names.items(), key=lambda kv: kv[1] or "")
        ]
        return {
            "catalogue": catalogue,
            "departments": sorted({b.department for b in catalogue_batches if b.department}),
            "sections": sorted({b.section for b in catalogue_batches if b.section}),
            "batches": [c["code"] for c in catalogue],
            "assignees": assignees,
            "priorities": [p.value for p in TaskPriority],
            "statuses": [s.value for s in TaskStatus],
            "due": ["overdue", "today", "week"],
        }

    def _kpis(self, rows, today: date) -> List[Dict[str, Any]]:
        total = len(rows)
        done = sum(1 for r in rows if r["status"] == "done")
        progress = sum(1 for r in rows if r["status"] == "in_progress")
        todo = sum(1 for r in rows if r["status"] == "open")
        blocked = sum(1 for r in rows if r["status"] == "blocked")
        overdue = sum(1 for r in rows if r["overdue"])
        unassigned = sum(1 for r in rows if not r["assignee_id"])
        rate = round(done / total * 100) if total else 0
        return [
            {"id": "total", "value": total, "label": "Total Tasks"},
            {"id": "done", "value": done, "label": "Completed", "tone": "ok"},
            {"id": "progress", "value": progress, "label": "In Progress"},
            {"id": "todo", "value": todo, "label": "To Do"},
            {"id": "overdue", "value": overdue, "label": "Overdue",
             "tone": "danger" if overdue else "ok"},
            {"id": "blocked", "value": blocked, "label": "Blocked",
             "tone": "danger" if blocked else "ok"},
            {"id": "unassigned", "value": unassigned, "label": "Unassigned",
             "tone": "warn" if unassigned else "ok"},
            {"id": "rate", "value": f"{rate}%", "label": "Completion Rate"},
        ]

    # --------------------------------------------------------------- blockers

    async def blockers(self, academic_year: str, **f) -> Dict[str, Any]:
        """The resolution queue, the category analysis and the SLA figures."""
        batches = await self._batches(academic_year, **f)
        codes = {str(b.id): b.batch_code for b in batches}
        rows = [self._blocker_row(b, codes)
                for b in await self._blockers([b.id for b in batches])]

        open_rows = [r for r in rows if r["status"] != "resolved"]
        resolved = [r for r in rows if r["status"] == "resolved"]

        # Oldest and most severe first - that is the order they should be
        # worked, and a queue sorted any other way is decoration.
        rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        open_rows.sort(key=lambda r: (rank.get(r["severity"], 2), -(r["age_days"] or 0)))

        analysis = Counter(r["category_label"] for r in open_rows)

        bands = {"<24h": 0, "1-3 days": 0, "4-7 days": 0, ">7 days": 0}
        for r in resolved:
            age = r["age_days"] or 0
            if age < 1:
                bands["<24h"] += 1
            elif age <= 3:
                bands["1-3 days"] += 1
            elif age <= 7:
                bands["4-7 days"] += 1
            else:
                bands[">7 days"] += 1
        settled = len(resolved)
        average = (round(sum(r["age_days"] or 0 for r in resolved) / settled, 1)
                   if settled else None)

        return {
            "queue": open_rows,
            "resolved_count": settled,
            "analysis": [{"label": k, "count": v} for k, v in analysis.most_common()],
            "sla": {
                "bands": [{"label": k, "count": v,
                           "percent": round(v / settled * 100) if settled else 0}
                          for k, v in bands.items()],
                "average_days": average,
                "resolved": settled,
            },
        }

    # --------------------------------------------------------------- workload

    async def workload(self, academic_year: str, **f) -> Dict[str, Any]:
        """
        What each student is carrying, and how much of it is in trouble.

        Load is expressed against a normal load rather than a stored capacity:
        a per-student capacity column would need maintaining by somebody, and
        an unmaintained one is worse than an honest yardstick.
        """
        today = local_today()
        batches = await self._batches(academic_year, **f)
        by_id = {str(b.id): b for b in batches}
        tasks = await self._tasks([b.id for b in batches])

        per_student: Dict[str, Dict[str, Any]] = {}
        for t in tasks:
            if not t.assignee_id or str(t.batch_id) not in by_id:
                continue
            key = str(t.assignee_id)
            row = per_student.setdefault(key, {
                "id": key,
                "name": t.assignee.full_name if t.assignee else "Student",
                "tasks": 0, "overdue": 0, "blocked": 0, "done": 0,
            })
            if t.status == TaskStatus.DONE:
                row["done"] += 1
                continue
            row["tasks"] += 1
            if t.due_date and t.due_date < today:
                row["overdue"] += 1
            if t.status == TaskStatus.BLOCKED:
                row["blocked"] += 1

        rows = list(per_student.values())
        for r in rows:
            r["load_percent"] = min(150, round(r["tasks"] / NORMAL_LOAD * 100))
        rows.sort(key=lambda r: (-r["overdue"] - r["blocked"], -r["tasks"]))

        # Which batches are carrying the overdue work, for the corner chart.
        overdue_by_batch = Counter()
        for t in tasks:
            if (t.status != TaskStatus.DONE and t.due_date and t.due_date < today
                    and str(t.batch_id) in by_id):
                overdue_by_batch[by_id[str(t.batch_id)].batch_code] += 1

        return {
            "students": rows,
            "normal_load": NORMAL_LOAD,
            "overdue_by_batch": [{"batch_code": c, "count": n}
                                 for c, n in overdue_by_batch.most_common(6)],
        }

    # ---------------------------------------------------------------- insight

    async def insight(self, academic_year: str) -> Dict[str, Any]:
        """
        One sentence about the blockers, from the data.

        Counts what the open blockers actually hold up: dependent tasks and
        the milestones those tasks belong to. Arithmetic, not a model - the
        same reason the tracker's insight is derived.
        """
        batches = await self._batches(academic_year)
        ids = [b.id for b in batches]
        blockers = [b for b in await self._blockers(ids)
                    if b.status != BlockerStatus.RESOLVED]
        if not blockers:
            return {"headline": "Nothing is blocked.", "detail": "",
                    "critical": 0, "downstream": 0, "milestones": 0}

        critical = [b for b in blockers if b.severity.value == "critical"]
        blocked_task_ids = [b.task_id for b in blockers if b.task_id]

        downstream = 0
        if blocked_task_ids:
            downstream = await self.db.scalar(
                select(func.count(TaskDependency.id))
                .where(TaskDependency.depends_on_id.in_(blocked_task_ids))
            ) or 0

        stages = {b.task.stage for b in blockers if b.task and b.task.stage}
        worst = Counter(CATEGORY_LABELS.get(b.category, b.category.value)
                        for b in (critical or blockers))
        top = worst.most_common(1)[0][0] if worst else ""

        n = len(critical) or len(blockers)
        word = "critical blockers" if critical and n != 1 else \
               "critical blocker" if critical else \
               "blockers" if n != 1 else "blocker"
        return {
            "headline": (
                f"{n} {word} affect {downstream} downstream task"
                f"{'' if downstream == 1 else 's'} and {len(stages)} milestone"
                f"{'' if len(stages) == 1 else 's'}."
            ),
            "detail": f"Most of them are {top.lower()}." if top else "",
            "critical": len(critical),
            "downstream": downstream,
            "milestones": len(stages),
        }
