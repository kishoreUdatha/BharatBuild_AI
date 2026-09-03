"""
Reporting, owning, escalating and resolving a blocker.

The lifecycle is the reason blockers became records rather than a sentence on
a task, so the rules that make the lifecycle mean anything live here:

* a blocker cannot be reported without saying what is actually wrong;
* resolving one requires a note, because "resolved" with no explanation tells
  the next person nothing and makes the SLA figures unauditable;
* escalating requires an owner, since escalating to nobody is just a louder
  way of leaving it open.

Every action goes through `FacultyAuthority`, the same gate the rest of the
portal uses.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.faculty import ProjectBatch
from app.models.project_tracking import (
    BlockerCategory,
    BlockerSeverity,
    BlockerStatus,
    ProjectBlocker,
    ProjectTask,
    TaskComment,
    TaskDependency,
    TaskStatus,
)
from app.models.user import User, UserRole, COLLEGE_STAFF_ROLES
from app.services.activity_log import record
from app.services.faculty_authority import FacultyAuthority
from app.services.project_tracker_actions import TrackerError


class BlockerActions:
    def __init__(self, db: AsyncSession, college_id=None):
        self.db = db
        self.college_id = college_id

    # ---------------------------------------------------------------- lookups

    async def _batch(self, identifier: str) -> ProjectBatch:
        stmt = (
            select(ProjectBatch)
            .options(selectinload(ProjectBatch.members))
            .where(ProjectBatch.batch_code == identifier)
        )
        if self.college_id:
            stmt = stmt.where(ProjectBatch.college_id == self.college_id)
        batch = (await self.db.execute(stmt)).scalars().unique().first()
        if batch is None:
            raise TrackerError(f"No batch found with the code {identifier}.")
        return batch

    async def _blocker(self, blocker_id: str) -> ProjectBlocker:
        row = (await self.db.execute(
            select(ProjectBlocker)
            .options(selectinload(ProjectBlocker.task))
            .where(ProjectBlocker.id == blocker_id)
        )).scalars().unique().first()
        if row is None:
            raise TrackerError("That blocker no longer exists.")
        if self.college_id:
            owner = (await self.db.execute(
                select(ProjectBatch.college_id)
                .where(ProjectBatch.id == row.batch_id)
            )).scalar_one_or_none()
            if owner != self.college_id:
                # Same answer as "does not exist", deliberately.
                raise TrackerError("That blocker no longer exists.")
        return row

    async def _may_manage(self, user: User, batch: ProjectBatch, doing: str) -> None:
        if await FacultyAuthority(self.db).can_manage(user, batch):
            return
        raise TrackerError(
            f"You do not have authority to {doing} for {batch.batch_code}. "
            "Its guide, section coordinator or the department coordinator can.")

    @staticmethod
    def _text(value: Optional[str], limit: int, field: str, required=True) -> Optional[str]:
        cleaned = (value or "").strip()
        if not cleaned:
            if required:
                raise TrackerError(f"{field} cannot be empty.")
            return None
        return cleaned[:limit]

    @staticmethod
    def _parse_date(value: Optional[str], field: str) -> Optional[date]:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise TrackerError(f"{field} must be a date like 2026-08-30.")

    # ----------------------------------------------------------------- report

    async def report(self, user: User, identifier: str,
                     payload: Dict[str, Any]) -> Dict[str, Any]:
        batch = await self._batch(identifier)
        await self._may_manage(user, batch, "report a blocker")

        title = self._text(payload.get("title"), 300, "Blocker")
        # The root cause is what makes the analysis panel worth reading. A
        # blocker filed as "API broken" cannot be counted, chased or learned
        # from, so it is required at the point somebody still knows the answer.
        root_cause = self._text(payload.get("root_cause"), 2000,
                                "What is actually causing this")

        try:
            category = BlockerCategory(str(payload.get("category", "technical")).lower())
            severity = BlockerSeverity(str(payload.get("severity", "medium")).lower())
        except ValueError:
            raise TrackerError(
                "Category must be technical, data, approval, team or documentation, "
                "and severity one of critical, high, medium or low.")

        task_id = payload.get("task_id") or None
        if task_id:
            task = (await self.db.execute(
                select(ProjectTask).where(ProjectTask.id == task_id)
            )).scalar_one_or_none()
            if task is None or str(task.batch_id) != str(batch.id):
                raise TrackerError("That task does not belong to this batch.")
            # A blocked task should say so - otherwise the board and the queue
            # disagree about the same piece of work.
            task.status = TaskStatus.BLOCKED
            task.blocked_reason = title[:300]

        blocker = ProjectBlocker(
            batch_id=batch.id,
            task_id=task_id,
            title=title,
            category=category,
            severity=severity,
            status=BlockerStatus.OPEN,
            root_cause=root_cause,
            impact=self._text(payload.get("impact"), 2000, "Impact", required=False),
            reported_by_id=user.id,
            reported_at=datetime.utcnow(),
            resolution_owner_id=payload.get("resolution_owner_id") or None,
            target_resolution=self._parse_date(
                payload.get("target_resolution"), "Target resolution"),
        )
        self.db.add(blocker)
        await self.db.flush()
        await record(self.db, batch_id=batch.id, actor=user,
                     activity=f"Blocker reported: {title}", module="Tracking")
        await self.db.commit()
        return {"id": str(blocker.id), "message": f"Reported “{title}”."}

    # ------------------------------------------------------------- lifecycle

    async def assign(self, user: User, blocker_id: str, owner_id: str,
                     target_resolution: Optional[str] = None) -> Dict[str, Any]:
        blocker = await self._blocker(blocker_id)
        batch = await self._batch_of(blocker)
        await self._may_manage(user, batch, "assign a blocker")

        owner = (await self.db.execute(
            select(User).where(User.id == owner_id)
        )).scalar_one_or_none()
        if owner is None:
            raise TrackerError("That person does not have an account.")
        if owner.role not in (*COLLEGE_STAFF_ROLES, UserRole.ADMIN):
            # Most blockers are somebody outside the team not having done
            # something. Handing one back to a student is how it stalls.
            raise TrackerError(
                "A blocker is owned by a staff member - the person who can clear it.")

        blocker.resolution_owner_id = owner.id
        if target_resolution:
            blocker.target_resolution = self._parse_date(
                target_resolution, "Target resolution")
        await record(self.db, batch_id=batch.id, actor=user,
                     activity=f"Blocker assigned to {owner.full_name}: {blocker.title}",
                     module="Tracking")
        await self.db.commit()
        return {"message": f"Assigned to {owner.full_name}."}

    async def escalate(self, user: User, blocker_id: str, note: str = "") -> Dict[str, Any]:
        blocker = await self._blocker(blocker_id)
        batch = await self._batch_of(blocker)
        await self._may_manage(user, batch, "escalate a blocker")

        if blocker.status == BlockerStatus.RESOLVED:
            raise TrackerError("That blocker is already resolved.")
        if not blocker.resolution_owner_id:
            raise TrackerError(
                "Give the blocker an owner before escalating it - escalating to "
                "nobody is just a louder way of leaving it open.")

        blocker.status = BlockerStatus.ESCALATED
        if blocker.severity != BlockerSeverity.CRITICAL:
            blocker.severity = BlockerSeverity.CRITICAL
        await record(self.db, batch_id=batch.id, actor=user,
                     activity=f"Blocker escalated: {blocker.title}"
                              + (f" — {note.strip()[:160]}" if note.strip() else ""),
                     module="Tracking")
        await self.db.commit()
        return {"message": "Escalated."}

    async def resolve(self, user: User, blocker_id: str, note: str) -> Dict[str, Any]:
        blocker = await self._blocker(blocker_id)
        batch = await self._batch_of(blocker)
        await self._may_manage(user, batch, "resolve a blocker")

        if blocker.status == BlockerStatus.RESOLVED:
            raise TrackerError("That blocker is already resolved.")
        cleaned = self._text(note, 2000, "How it was resolved")

        blocker.status = BlockerStatus.RESOLVED
        blocker.resolved_at = datetime.utcnow()
        blocker.resolution_note = cleaned

        # Release the task, unless something else is still blocking it.
        if blocker.task_id:
            others = (await self.db.execute(
                select(ProjectBlocker)
                .where(ProjectBlocker.task_id == blocker.task_id)
                .where(ProjectBlocker.id != blocker.id)
                .where(ProjectBlocker.status != BlockerStatus.RESOLVED)
            )).scalars().first()
            task = (await self.db.execute(
                select(ProjectTask).where(ProjectTask.id == blocker.task_id)
            )).scalar_one_or_none()
            if task is not None and others is None:
                task.status = TaskStatus.IN_PROGRESS
                task.blocked_reason = None

        await record(self.db, batch_id=batch.id, actor=user,
                     activity=f"Blocker resolved: {blocker.title}", module="Tracking")
        await self.db.commit()
        days = max(0, (blocker.resolved_at - blocker.reported_at).days)
        return {"message": f"Resolved after {days} day{'' if days == 1 else 's'}."}

    async def _batch_of(self, blocker: ProjectBlocker) -> ProjectBatch:
        batch = (await self.db.execute(
            select(ProjectBatch)
            .options(selectinload(ProjectBatch.members))
            .where(ProjectBatch.id == blocker.batch_id)
        )).scalars().unique().first()
        if batch is None:
            raise TrackerError("That batch no longer exists.")
        return batch

    # ------------------------------------------------------- task bulk edits

    async def bulk_task_edit(self, user: User, task_ids,
                             payload: Dict[str, Any]) -> Dict[str, Any]:
        """Assign, re-prioritise, re-date or complete several tasks at once."""
        if not task_ids:
            raise TrackerError("Select at least one task first.")

        changed, refused = 0, 0
        for task_id in task_ids:
            task = (await self.db.execute(
                select(ProjectTask).where(ProjectTask.id == task_id)
            )).scalar_one_or_none()
            if task is None:
                refused += 1
                continue
            batch = await self._batch_by_id(task.batch_id)
            if batch is None or not await FacultyAuthority(self.db).can_manage(user, batch):
                refused += 1
                continue

            if payload.get("assignee_id") is not None:
                assignee_id = payload["assignee_id"] or None
                if assignee_id:
                    members = {str(m.student_id) for m in (batch.members or [])}
                    if str(assignee_id) not in members:
                        refused += 1
                        continue
                task.assignee_id = assignee_id
            if payload.get("priority"):
                from app.models.project_tracking import TaskPriority
                try:
                    task.priority = TaskPriority(str(payload["priority"]).lower())
                except ValueError:
                    raise TrackerError("Priority must be high, medium or low.")
            if payload.get("due_date"):
                task.due_date = self._parse_date(payload["due_date"], "Due date")
            if payload.get("status"):
                try:
                    new_status = TaskStatus(str(payload["status"]).lower())
                except ValueError:
                    raise TrackerError("Status must be open, in_progress, blocked or done.")
                if new_status == TaskStatus.BLOCKED:
                    raise TrackerError(
                        "Blocking work needs a reason, so report a blocker instead.")
                task.status = new_status
                task.completed_at = (datetime.utcnow()
                                     if new_status == TaskStatus.DONE else None)
                if new_status != TaskStatus.BLOCKED:
                    task.blocked_reason = None
            changed += 1

        await self.db.commit()
        if not changed:
            raise TrackerError("None of the selected tasks could be changed.")
        message = f"{changed} task{'' if changed == 1 else 's'} updated"
        if refused:
            message += f". {refused} skipped - not yours to manage."
        return {"changed": changed, "skipped": refused, "message": message}

    async def _batch_by_id(self, batch_id) -> Optional[ProjectBatch]:
        stmt = (
            select(ProjectBatch)
            .options(selectinload(ProjectBatch.members))
            .where(ProjectBatch.id == batch_id)
        )
        if self.college_id:
            stmt = stmt.where(ProjectBatch.college_id == self.college_id)
        return (await self.db.execute(stmt)).scalars().unique().first()

    # --------------------------------------------------------------- comments

    async def comment(self, user: User, task_id: str, body: str) -> Dict[str, Any]:
        task = (await self.db.execute(
            select(ProjectTask).where(ProjectTask.id == task_id)
        )).scalar_one_or_none()
        if task is None:
            raise TrackerError("That task no longer exists.")
        batch = await self._batch_by_id(task.batch_id)
        if batch is None:
            raise TrackerError("That task no longer exists.")
        await self._may_manage(user, batch, "comment on a task")

        text = self._text(body, 4000, "Comment")
        self.db.add(TaskComment(task_id=task.id, author_id=user.id, body=text))
        await self.db.commit()
        return {"message": "Comment added."}

    async def add_dependency(self, user: User, task_id: str,
                             depends_on_id: str) -> Dict[str, Any]:
        if str(task_id) == str(depends_on_id):
            raise TrackerError("A task cannot wait on itself.")
        task = (await self.db.execute(
            select(ProjectTask).where(ProjectTask.id == task_id)
        )).scalar_one_or_none()
        other = (await self.db.execute(
            select(ProjectTask).where(ProjectTask.id == depends_on_id)
        )).scalar_one_or_none()
        if task is None or other is None:
            raise TrackerError("One of those tasks no longer exists.")
        if str(task.batch_id) != str(other.batch_id):
            raise TrackerError("Tasks can only depend on others in the same project.")

        batch = await self._batch_by_id(task.batch_id)
        if batch is None:
            raise TrackerError("That batch no longer exists.")
        await self._may_manage(user, batch, "link tasks")

        exists = (await self.db.execute(
            select(TaskDependency)
            .where(TaskDependency.task_id == task.id)
            .where(TaskDependency.depends_on_id == other.id)
        )).scalars().first()
        if exists:
            return {"message": "That link already exists."}

        # A one-step cycle is the one worth catching cheaply; deeper cycles are
        # rare in an eight-stage project and would cost a graph walk per link.
        reverse = (await self.db.execute(
            select(TaskDependency)
            .where(TaskDependency.task_id == other.id)
            .where(TaskDependency.depends_on_id == task.id)
        )).scalars().first()
        if reverse:
            raise TrackerError(
                f"“{other.title}” already waits on this one, so linking them "
                "the other way would make a loop.")

        self.db.add(TaskDependency(task_id=task.id, depends_on_id=other.id))
        await self.db.commit()
        return {"message": f"“{task.title}” now waits on “{other.title}”."}
