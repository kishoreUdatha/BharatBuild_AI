"""
The writes behind the tracking screen: tasks, deliverables and integrations.

Kept apart from `project_tracker`, which only reads. Every action here goes
through `FacultyAuthority` first, so the rule about who may change a batch is
the one the rest of the portal already uses rather than a second, weaker copy
invented for this screen.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.institution_time import local_today
from app.models.faculty import BatchStageProgress, ProjectBatch, ProjectStage
from app.models.project_tracking import (
    BatchIntegration,
    DeliverableStatus,
    IntegrationKind,
    IntegrationState,
    ProjectDeliverable,
    ProjectTask,
    TaskPriority,
    TaskStatus,
)
from app.models.user import User
from app.services.activity_log import record
from app.services.faculty_authority import FacultyAuthority
from app.services.project_tracker import STANDARD_DELIVERABLES


class TrackerError(Exception):
    """Something the person can fix, phrased for them rather than for a log."""


class TrackerActions:
    def __init__(self, db: AsyncSession, college_id=None):
        self.db = db
        self.college_id = college_id

    # ---------------------------------------------------------------- lookups

    async def _batch(self, identifier: str) -> ProjectBatch:
        stmt = (
            select(ProjectBatch)
            .options(selectinload(ProjectBatch.members),
                     selectinload(ProjectBatch.stage_progress))
            .where(ProjectBatch.batch_code == identifier)
        )
        if self.college_id:
            stmt = stmt.where(ProjectBatch.college_id == self.college_id)
        batch = (await self.db.execute(stmt)).scalars().unique().first()
        if batch is None:
            # Indistinguishable from "belongs to another college" on purpose.
            raise TrackerError(f"No batch found with the code {identifier}.")
        return batch

    async def _may_manage(self, user: User, batch: ProjectBatch, doing: str) -> None:
        allowed = await FacultyAuthority(self.db).can_manage(user, batch)
        if not allowed:
            raise TrackerError(
                f"You do not have authority to {doing} for {batch.batch_code}. "
                "Its guide, section coordinator or the department coordinator can."
            )

    @staticmethod
    def _parse_date(value: Optional[str], field: str) -> Optional[date]:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise TrackerError(f"{field} must be a date like 2026-08-24.")

    @staticmethod
    def _text(value: Optional[str], limit: int, field: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise TrackerError(f"{field} cannot be empty.")
        if len(cleaned) > limit:
            raise TrackerError(f"{field} must be {limit} characters or fewer.")
        return cleaned

    # ------------------------------------------------------------------ tasks

    async def add_task(self, user: User, identifier: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        batch = await self._batch(identifier)
        await self._may_manage(user, batch, "add a task")

        title = self._text(payload.get("title"), 300, "Task")
        due = self._parse_date(payload.get("due_date"), "Due date")

        assignee_id = payload.get("assignee_id") or None
        if assignee_id:
            member_ids = {str(m.student_id) for m in (batch.members or [])}
            if str(assignee_id) not in member_ids:
                raise TrackerError("That student is not a member of this batch.")

        try:
            priority = TaskPriority(str(payload.get("priority", "medium")).lower())
        except ValueError:
            raise TrackerError("Priority must be high, medium or low.")

        task = ProjectTask(
            batch_id=batch.id,
            title=title,
            detail=(payload.get("detail") or "").strip() or None,
            assignee_id=assignee_id,
            priority=priority,
            due_date=due,
            created_by_id=user.id,
        )
        self.db.add(task)
        await self.db.flush()
        await record(self.db, batch_id=batch.id, actor=user,
                     activity=f"Added task: {title}", module="Tracking")
        await self.db.commit()
        return {"id": str(task.id), "message": f"Added “{title}”."}

    async def update_task(self, user: User, task_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        task = (await self.db.execute(
            select(ProjectTask).where(ProjectTask.id == task_id)
        )).scalar_one_or_none()
        if task is None:
            raise TrackerError("That task no longer exists.")
        batch = await self._batch_by_id(task.batch_id)
        await self._may_manage(user, batch, "change a task")

        if "status" in payload:
            try:
                status = TaskStatus(str(payload["status"]).lower())
            except ValueError:
                raise TrackerError("Status must be open, in_progress, blocked or done.")

            # A blocker without a reason is a dead end for whoever reads it
            # next - the reason is the only part that lets anyone act.
            if status == TaskStatus.BLOCKED:
                reason = (payload.get("blocked_reason") or task.blocked_reason or "").strip()
                if not reason:
                    raise TrackerError("Say what is blocking this task before marking it blocked.")
                task.blocked_reason = reason[:300]
            else:
                task.blocked_reason = None

            task.status = status
            task.completed_at = datetime.utcnow() if status == TaskStatus.DONE else None

        if "priority" in payload:
            try:
                task.priority = TaskPriority(str(payload["priority"]).lower())
            except ValueError:
                raise TrackerError("Priority must be high, medium or low.")
        if "due_date" in payload:
            task.due_date = self._parse_date(payload["due_date"], "Due date")
        if "title" in payload:
            task.title = self._text(payload["title"], 300, "Task")
        if "assignee_id" in payload:
            assignee_id = payload["assignee_id"] or None
            if assignee_id:
                member_ids = {str(m.student_id) for m in (batch.members or [])}
                if str(assignee_id) not in member_ids:
                    raise TrackerError("That student is not a member of this batch.")
            task.assignee_id = assignee_id

        await record(self.db, batch_id=batch.id, actor=user,
                     activity=f"Updated task: {task.title}", module="Tracking")
        await self.db.commit()
        return {"message": "Task updated."}

    async def _batch_by_id(self, batch_id) -> ProjectBatch:
        stmt = (
            select(ProjectBatch)
            .options(selectinload(ProjectBatch.members))
            .where(ProjectBatch.id == batch_id)
        )
        if self.college_id:
            stmt = stmt.where(ProjectBatch.college_id == self.college_id)
        batch = (await self.db.execute(stmt)).scalars().unique().first()
        if batch is None:
            raise TrackerError("That batch no longer exists.")
        return batch

    # ----------------------------------------------------------- deliverables

    async def ensure_deliverables(self, batch: ProjectBatch) -> None:
        """
        Give a batch the standard set if it has none.

        Created lazily rather than at batch creation so existing batches gain
        them too, without a data migration that would guess at their progress.
        """
        existing = (await self.db.execute(
            select(ProjectDeliverable.name).where(ProjectDeliverable.batch_id == batch.id)
        )).scalars().all()
        if existing:
            return
        for position, name in enumerate(STANDARD_DELIVERABLES):
            self.db.add(ProjectDeliverable(
                batch_id=batch.id, name=name, progress=0,
                status=DeliverableStatus.PENDING, position=position))

    async def set_deliverable(self, user: User, deliverable_id: str,
                              payload: Dict[str, Any]) -> Dict[str, Any]:
        row = (await self.db.execute(
            select(ProjectDeliverable).where(ProjectDeliverable.id == deliverable_id)
        )).scalar_one_or_none()
        if row is None:
            raise TrackerError("That deliverable no longer exists.")
        batch = await self._batch_by_id(row.batch_id)
        await self._may_manage(user, batch, "change a deliverable")

        if "progress" in payload:
            try:
                progress = int(payload["progress"])
            except (TypeError, ValueError):
                raise TrackerError("Progress must be a whole number.")
            if not 0 <= progress <= 100:
                raise TrackerError("Progress must be between 0 and 100.")
            row.progress = progress
        if "status" in payload:
            try:
                row.status = DeliverableStatus(str(payload["status"]).lower())
            except ValueError:
                raise TrackerError("Status must be pending, available or verified.")
        if "evidence_url" in payload:
            row.evidence_url = (payload["evidence_url"] or "").strip()[:500] or None

        # Verified means somebody looked at a finished thing.
        if row.status == DeliverableStatus.VERIFIED and row.progress < 100:
            row.progress = 100

        await record(self.db, batch_id=batch.id, actor=user,
                     activity=f"Updated deliverable: {row.name}", module="Tracking")
        await self.db.commit()
        return {"message": f"{row.name} updated."}

    # ----------------------------------------------------------- integrations

    async def set_integration(self, user: User, identifier: str,
                              payload: Dict[str, Any]) -> Dict[str, Any]:
        batch = await self._batch(identifier)
        await self._may_manage(user, batch, "record integration status")
        try:
            kind = IntegrationKind(str(payload.get("kind", "")).lower())
            state = IntegrationState(str(payload.get("state", "")).lower())
        except ValueError:
            raise TrackerError(
                "Kind must be repository, build, deployment or review, and state "
                "one of not_connected, connected, passed, failed, live or scheduled.")

        row = (await self.db.execute(
            select(BatchIntegration)
            .where(BatchIntegration.batch_id == batch.id)
            .where(BatchIntegration.kind == kind)
        )).scalar_one_or_none()
        if row is None:
            row = BatchIntegration(batch_id=batch.id, kind=kind)
            self.db.add(row)
        row.state = state
        row.detail = (payload.get("detail") or "").strip()[:200] or None
        row.url = (payload.get("url") or "").strip()[:500] or None

        await record(self.db, batch_id=batch.id, actor=user,
                     activity=f"{kind.value.title()} marked "
                              f"{state.value.replace('_', ' ')}",
                     module="Tracking")
        await self.db.commit()
        return {"message": f"{kind.value.title()} updated."}

    # -------------------------------------------------------------- milestone

    async def set_milestone(self, user: User, identifier: str,
                            payload: Dict[str, Any]) -> Dict[str, Any]:
        """Give a stage a planned date, or record that it has landed."""
        batch = await self._batch(identifier)
        await self._may_manage(user, batch, "change a milestone")
        try:
            stage = ProjectStage(str(payload.get("stage", "")).lower())
        except ValueError:
            raise TrackerError("That is not one of the eight project stages.")

        row = next((r for r in (batch.stage_progress or []) if r.stage == stage), None)
        if row is None:
            row = BatchStageProgress(batch_id=batch.id, stage=stage, percent=0.0)
            self.db.add(row)
            await self.db.flush()

        if "planned_date" in payload:
            planned = self._parse_date(payload["planned_date"], "Planned date")
            if planned and batch.start_date and planned < batch.start_date:
                raise TrackerError("A milestone cannot be planned before the project starts.")
            row.planned_date = planned
        if "percent" in payload:
            try:
                percent = float(payload["percent"])
            except (TypeError, ValueError):
                raise TrackerError("Percent must be a number.")
            if not 0 <= percent <= 100:
                raise TrackerError("Percent must be between 0 and 100.")
            row.percent = percent
            row.completed_at = datetime.utcnow() if percent >= 99.5 else None

        await record(self.db, batch_id=batch.id, actor=user,
                     activity="Milestone updated: "
                              f"{stage.value.replace('_', ' ').title()}",
                     module="Tracking")
        await self.db.commit()
        return {"message": "Milestone updated."}

    # ------------------------------------------------------------------ bulk

    async def request_update(self, user: User, batch_codes, note: str = "") -> Dict[str, Any]:
        """
        Ask several teams for a progress update.

        Recorded on each batch's activity log rather than sent: there is no
        mail or messaging channel configured, so a "sent" claim would be a
        lie. The teams see it on their own workspace, and the log is what a
        coordinator can point at later.
        """
        if not batch_codes:
            raise TrackerError("Select at least one project first.")

        asked, refused = [], []
        for code in batch_codes:
            batch = await self._batch(code)
            if not await FacultyAuthority(self.db).can_manage(user, batch):
                refused.append(code)
                continue
            batch.last_reminder_at = datetime.utcnow()
            await record(
                self.db, batch_id=batch.id, actor=user,
                activity="Progress update requested"
                         + (f": {note.strip()[:160]}" if note.strip() else ""),
                module="Tracking",
            )
            asked.append(code)
        await self.db.commit()

        if not asked:
            raise TrackerError(
                "You do not have authority over any of the selected projects.")
        message = f"Update requested from {len(asked)} project" + \
                  ("s" if len(asked) != 1 else "")
        if refused:
            # Say what did not happen. A partial success reported as a success
            # is how people find out days later that half the teams were
            # never asked.
            message += f". {len(refused)} skipped - not yours to manage."
        return {"asked": asked, "skipped": refused, "message": message}

    async def add_milestone_date(self, user: User, batch_codes,
                                 stage: str, planned_date: str) -> Dict[str, Any]:
        """Set the same planned date on one stage across several projects."""
        if not batch_codes:
            raise TrackerError("Select at least one project first.")
        updated, refused = [], []
        for code in batch_codes:
            try:
                await self.set_milestone(
                    user, code, {"stage": stage, "planned_date": planned_date})
                updated.append(code)
            except TrackerError:
                refused.append(code)
        if not updated:
            raise TrackerError(
                "None of the selected projects could be changed. Check the "
                "stage name and that these projects are yours to manage.")
        message = f"Milestone dated on {len(updated)} project" + \
                  ("s" if len(updated) != 1 else "")
        if refused:
            message += f". {len(refused)} skipped."
        return {"updated": updated, "skipped": refused, "message": message}
