"""
Tasks - the work underneath a batch's stories.

A story says what the team is delivering; a task says who is doing which piece
of it by when. Most tasks break a story down, but not all of them: writing the
report or booking a demo slot belongs to the project rather than to any one
story, so `story_id` stays optional and the screen shows both.

Overdue is computed here, from the due date against today, and never stored.
A stored flag would be wrong every morning until something rewrote it.
"""

from collections import defaultdict
from datetime import date, datetime
from math import ceil
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_planning import ProjectUserStory
from app.models.faculty import ProjectBatch
from app.models.project_tracking import ProjectTask, TaskPriority, TaskStatus
from app.models.user import User
from app.services.user_stories import StoryError, UserStoryService, _pct, _person

STATUS_LABELS = {
    TaskStatus.OPEN: "Open",
    TaskStatus.IN_PROGRESS: "In Progress",
    TaskStatus.BLOCKED: "Blocked",
    TaskStatus.DONE: "Done",
}

PRIORITY_LABELS = {
    TaskPriority.HIGH: "High",
    TaskPriority.MEDIUM: "Medium",
    TaskPriority.LOW: "Low",
}

assert set(STATUS_LABELS) == set(TaskStatus)
assert set(PRIORITY_LABELS) == set(TaskPriority)

# Work nobody has finished. Used for the overdue count and the board's default
# reading of "outstanding", so both mean the same thing.
OPEN_STATES = {TaskStatus.OPEN, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED}

SORTS = {
    "due_asc": ("Due Date (Soonest)", lambda r: (r["due_date"] or date.max, r["title"]), False),
    "due_desc": ("Due Date (Latest)", lambda r: (r["due_date"] or date.min, r["title"]), True),
    "created_desc": ("Created (Newest)", lambda r: r["created_at"] or datetime.min, True),
    "priority": ("Priority", lambda r: {"high": 0, "medium": 1, "low": 2}[r["priority"]], False),
    "status": ("Status", lambda r: list(STATUS_LABELS).index(TaskStatus(r["status"])), False),
}


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.stories = UserStoryService(db)

    async def _tasks(self, batch_id) -> List[ProjectTask]:
        return (await self.db.execute(
            select(ProjectTask)
            .where(ProjectTask.batch_id == batch_id)
            .options(
                selectinload(ProjectTask.assignee),
                selectinload(ProjectTask.story),
            )
            .order_by(ProjectTask.created_at)
        )).scalars().all()

    async def _backlog(self, batch_id) -> List[ProjectUserStory]:
        return (await self.db.execute(
            select(ProjectUserStory)
            .where(ProjectUserStory.batch_id == batch_id)
            .where(ProjectUserStory.moved_to_backlog_at.isnot(None))
            .order_by(ProjectUserStory.key)
        )).scalars().all()

    def _row(self, task: ProjectTask, today: date) -> dict:
        due = task.due_date
        return {
            "id": str(task.id),
            "title": task.title,
            "detail": task.detail,
            "status": task.status.value,
            "status_label": STATUS_LABELS[task.status],
            "priority": task.priority.value,
            "priority_label": PRIORITY_LABELS[task.priority],
            "assignee": _person(task.assignee),
            "due_date": due,
            # Not stored: a flag written yesterday would be wrong this morning.
            "overdue": bool(due and due < today and task.status in OPEN_STATES),
            "days_left": (due - today).days if due else None,
            "progress": task.progress or 0,
            "blocked_reason": task.blocked_reason,
            "story": ({"id": str(task.story.id), "key": task.story.key,
                       "title": task.story.title} if task.story else None),
            "completed_at": task.completed_at,
            "created_at": task.created_at,
        }

    async def board(
        self,
        batch: ProjectBatch,
        *,
        search: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
        story: Optional[str] = None,
        overdue: Optional[bool] = None,
        sort: str = "due_asc",
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        tasks = await self._tasks(batch.id)
        today = date.today()
        rows = [self._row(t, today) for t in tasks]

        def keep(r: dict) -> bool:
            if status and r["status"] != status:
                return False
            if priority and r["priority"] != priority:
                return False
            if assignee:
                if assignee == "unassigned":
                    if r["assignee"] is not None:
                        return False
                elif not r["assignee"] or r["assignee"]["id"] != assignee:
                    return False
            if story:
                # "standalone" is the useful opposite of "belongs to a story":
                # project work that no backlog item accounts for.
                if story == "standalone":
                    if r["story"] is not None:
                        return False
                elif not r["story"] or r["story"]["key"] != story:
                    return False
            if overdue and not r["overdue"]:
                return False
            if search:
                needle = search.lower()
                blob = " ".join(filter(None, [
                    r["title"], r["detail"], r["blocked_reason"],
                    r["story"]["key"] if r["story"] else None,
                    r["assignee"]["name"] if r["assignee"] else None,
                ])).lower()
                if needle not in blob:
                    return False
            return True

        matched = [r for r in rows if keep(r)]
        _, key_of, reverse = SORTS.get(sort, SORTS["due_asc"])
        matched.sort(key=key_of, reverse=reverse)

        total = len(matched)
        per_page = max(1, min(per_page, 200))
        pages = max(1, ceil(total / per_page)) if total else 1
        page = max(1, min(page, pages))
        window = matched[(page - 1) * per_page: page * per_page]

        counted = {s: sum(1 for r in matched if r["status"] == s.value) for s in TaskStatus}
        overdue_count = sum(1 for r in matched if r["overdue"])
        done = counted[TaskStatus.DONE]

        backlog = await self._backlog(batch.id)
        roster = self.stories._roster(batch)

        return {
            "header": {
                "batch_id": str(batch.id),
                "batch_code": batch.batch_code,
                "project_title": batch.title,
                "department": batch.department,
                "section": batch.section,
                "guide": batch.guide.full_name if batch.guide else None,
            },
            "kpis": [
                {"id": "total", "value": total, "label": "Total Tasks", "percent": None},
                {"id": "open", "value": counted[TaskStatus.OPEN], "label": "Open",
                 "percent": _pct(counted[TaskStatus.OPEN], total)},
                {"id": "in_progress", "value": counted[TaskStatus.IN_PROGRESS],
                 "label": "In Progress", "percent": _pct(counted[TaskStatus.IN_PROGRESS], total)},
                {"id": "blocked", "value": counted[TaskStatus.BLOCKED], "label": "Blocked",
                 "percent": _pct(counted[TaskStatus.BLOCKED], total)},
                {"id": "done", "value": done, "label": "Done", "percent": _pct(done, total)},
                {"id": "overdue", "value": overdue_count, "label": "Overdue",
                 "percent": _pct(overdue_count, total)},
            ],
            "rows": window,
            "total": total,
            "page": page,
            "pages": pages,
            "per_page": per_page,
            "sort": sort,
            "counts": {
                "total": total,
                "overdue": overdue_count,
                **{s.value: counted[s] for s in TaskStatus},
            },
            "filters": {
                "statuses": [{"value": s.value, "label": STATUS_LABELS[s]} for s in TaskStatus],
                "priorities": [{"value": p.value, "label": PRIORITY_LABELS[p]}
                               for p in TaskPriority],
                "assignees": [_person(m.student) for m in roster],
                "stories": [{"value": s.key, "label": f"{s.key} · {s.title}"} for s in backlog],
                "sorts": [{"value": k, "label": v[0]} for k, v in SORTS.items()],
            },
            "students": self._workload(batch, rows, today),
        }

    def _workload(self, batch: ProjectBatch, rows: List[dict], today: date) -> List[dict]:
        """Per-member load, from the roster so a member holding nothing shows."""
        held: Dict[str, dict] = defaultdict(
            lambda: {"tasks": 0, "done": 0, "overdue": 0, "blocked": 0})
        for r in rows:
            who = r["assignee"]
            if who is None:
                continue
            entry = held[who["id"]]
            entry["tasks"] += 1
            if r["status"] == TaskStatus.DONE.value:
                entry["done"] += 1
            if r["overdue"]:
                entry["overdue"] += 1
            if r["status"] == TaskStatus.BLOCKED.value:
                entry["blocked"] += 1

        cards = []
        for member in self.stories._roster(batch):
            person = _person(member.student)
            stats = held.get(person["id"], {"tasks": 0, "done": 0, "overdue": 0, "blocked": 0})
            cards.append({
                **person,
                **stats,
                "percent": int(round(_pct(stats["done"], stats["tasks"]))),
            })
        cards.sort(key=lambda c: (-c["overdue"], -c["tasks"], c["name"]))
        return cards

    # -------------------------------------------------------------- writing

    async def _task(self, batch: ProjectBatch, task_id: str) -> ProjectTask:
        task = (await self.db.execute(
            select(ProjectTask)
            .where(ProjectTask.id == task_id)
            .where(ProjectTask.batch_id == batch.id)
            .options(selectinload(ProjectTask.assignee), selectinload(ProjectTask.story))
        )).scalars().first()
        if task is None:
            raise StoryError("That task is not on this batch.")
        return task

    async def _story_or_none(self, batch: ProjectBatch,
                             story_id: Optional[str]) -> Optional[ProjectUserStory]:
        if not story_id:
            return None
        story = next((s for s in await self._backlog(batch.id) if str(s.id) == str(story_id)),
                     None)
        if story is None:
            raise StoryError("That story is not on this batch's backlog.")
        return story

    @staticmethod
    def _apply_status(task: ProjectTask, status: TaskStatus) -> None:
        task.status = status
        # Finishing a task is what sets its completion date and its progress;
        # asking the trainer to keep three fields agreeing would guarantee
        # they eventually do not.
        if status == TaskStatus.DONE:
            task.completed_at = task.completed_at or datetime.utcnow()
            task.progress = 100
        else:
            task.completed_at = None
            if task.progress >= 100:
                task.progress = 90 if status == TaskStatus.IN_PROGRESS else 0
        if status != TaskStatus.BLOCKED:
            task.blocked_reason = None

    async def create(self, batch: ProjectBatch, payload: dict, user: User) -> dict:
        title = (payload.get("title") or "").strip()
        if not title:
            raise StoryError("A task needs a title.")

        assignee = self.stories._member_or_none(batch, payload.get("assignee_id"))
        story = await self._story_or_none(batch, payload.get("story_id"))
        status = TaskStatus(payload.get("status") or "open")
        if status == TaskStatus.BLOCKED and not (payload.get("blocked_reason") or "").strip():
            raise StoryError("Say what is blocking the task.")

        task = ProjectTask(
            batch_id=batch.id,
            story_id=story.id if story else None,
            title=title[:300],
            detail=(payload.get("detail") or "").strip() or None,
            assignee_id=assignee.id if assignee else None,
            priority=TaskPriority(payload.get("priority") or "medium"),
            due_date=payload.get("due_date"),
            blocked_reason=((payload.get("blocked_reason") or "").strip() or None),
            progress=int(payload.get("progress") or 0),
            created_by_id=user.id,
        )
        self._apply_status(task, status)
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return {"id": str(task.id), "title": task.title}

    async def update(self, batch: ProjectBatch, task_id: str, payload: dict) -> dict:
        task = await self._task(batch, task_id)

        if payload.get("title"):
            task.title = payload["title"].strip()[:300]
        if "detail" in payload:
            task.detail = (payload["detail"] or "").strip() or None
        if "due_date" in payload:
            task.due_date = payload["due_date"]
        if payload.get("priority"):
            task.priority = TaskPriority(payload["priority"])
        if "assignee_id" in payload:
            assignee = self.stories._member_or_none(batch, payload["assignee_id"])
            task.assignee_id = assignee.id if assignee else None
        if "story_id" in payload:
            story = await self._story_or_none(batch, payload["story_id"])
            task.story_id = story.id if story else None
        if payload.get("progress") is not None:
            progress = int(payload["progress"])
            if not 0 <= progress <= 100:
                raise StoryError("Progress must be between 0 and 100.")
            task.progress = progress
        if "blocked_reason" in payload:
            task.blocked_reason = (payload["blocked_reason"] or "").strip() or None

        if payload.get("status"):
            status = TaskStatus(payload["status"])
            reason = task.blocked_reason
            if status == TaskStatus.BLOCKED and not reason:
                raise StoryError("Say what is blocking the task.")
            self._apply_status(task, status)

        task.updated_at = datetime.utcnow()
        await self.db.commit()
        return {"id": str(task.id), "title": task.title, "status": task.status.value}
