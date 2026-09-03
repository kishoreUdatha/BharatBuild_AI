"""
Approving milestones, requesting changes, and chasing evidence.

The rules here are what make the approval trail worth keeping:

* a milestone cannot be approved on nothing - if evidence was asked for, it
  has to be there and verified before anyone signs it off;
* requesting changes needs a reason, or the owner learns only that they were
  refused;
* approving is a decision by a named person at a known time, so both are
  recorded and it cannot be quietly re-approved.

Everything goes through `FacultyAuthority`, the same gate as the rest of the
portal.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.faculty import ProjectBatch
from app.models.milestones import (
    ApprovalState,
    EvidenceStatus,
    MilestoneChecklistItem,
    MilestoneDependency,
    MilestoneEvidence,
    MilestonePriority,
    MilestoneStatus,
    ProjectMilestone,
)
from app.models.user import User
from app.services.activity_log import record
from app.services.faculty_authority import FacultyAuthority
from app.services.project_tracker_actions import TrackerError


class MilestoneActions:
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

    async def _milestone(self, milestone_id: str):
        m = (await self.db.execute(
            select(ProjectMilestone).where(ProjectMilestone.id == milestone_id)
        )).scalar_one_or_none()
        if m is None:
            raise TrackerError("That milestone no longer exists.")
        stmt = (
            select(ProjectBatch)
            .options(selectinload(ProjectBatch.members))
            .where(ProjectBatch.id == m.batch_id)
        )
        if self.college_id:
            stmt = stmt.where(ProjectBatch.college_id == self.college_id)
        batch = (await self.db.execute(stmt)).scalars().unique().first()
        if batch is None:
            # Same answer as "does not exist" for another college's milestone.
            raise TrackerError("That milestone no longer exists.")
        return m, batch

    async def _may_manage(self, user: User, batch: ProjectBatch, doing: str) -> None:
        if await FacultyAuthority(self.db).can_manage(user, batch):
            return
        raise TrackerError(
            f"You do not have authority to {doing} for {batch.batch_code}. "
            "Its guide, section coordinator or the department coordinator can.")

    @staticmethod
    def _text(value: Optional[str], limit: int, field: str, required=True):
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
            raise TrackerError(f"{field} must be a date like 2026-09-05.")

    # ------------------------------------------------------------------ create

    async def add(self, user: User, identifier: str,
                  payload: Dict[str, Any]) -> Dict[str, Any]:
        batch = await self._batch(identifier)
        await self._may_manage(user, batch, "add a milestone")

        name = self._text(payload.get("name"), 200, "Milestone name")
        existing = (await self.db.execute(
            select(ProjectMilestone)
            .where(ProjectMilestone.batch_id == batch.id)
            .where(ProjectMilestone.name == name)
        )).scalars().first()
        if existing:
            raise TrackerError(f"{batch.batch_code} already has a milestone called “{name}”.")

        planned = self._parse_date(payload.get("planned_date"), "Planned date")
        start = self._parse_date(payload.get("planned_start"), "Planned start")
        if start and planned and start > planned:
            raise TrackerError("A milestone cannot start after the date it is due.")

        owner_id = payload.get("owner_id") or None
        if owner_id:
            members = {str(m.student_id) for m in (batch.members or [])}
            if str(owner_id) not in members:
                raise TrackerError("The owner must be a member of this batch.")

        try:
            priority = MilestonePriority(str(payload.get("priority", "medium")).lower())
        except ValueError:
            raise TrackerError("Priority must be critical, high, medium or low.")

        milestone = ProjectMilestone(
            batch_id=batch.id,
            name=name,
            detail=self._text(payload.get("detail"), 2000, "Detail", required=False),
            stage=(str(payload["stage"]).upper() if payload.get("stage") else None),
            priority=priority,
            owner_id=owner_id,
            reviewer_id=payload.get("reviewer_id") or batch.guide_id,
            planned_start=start,
            planned_date=planned,
            forecast_date=self._parse_date(payload.get("forecast_date"), "Forecast date"),
        )
        self.db.add(milestone)
        await self.db.flush()

        for position, label in enumerate(payload.get("checklist") or []):
            text = (label or "").strip()
            if text:
                self.db.add(MilestoneChecklistItem(
                    milestone_id=milestone.id, label=text[:300], position=position))

        await record(self.db, batch_id=batch.id, actor=user,
                     activity=f"Milestone added: {name}", module="Tracking")
        await self.db.commit()
        return {"id": str(milestone.id), "message": f"Added “{name}”."}

    # --------------------------------------------------------------- lifecycle

    async def update(self, user: User, milestone_id: str,
                     payload: Dict[str, Any]) -> Dict[str, Any]:
        m, batch = await self._milestone(milestone_id)
        await self._may_manage(user, batch, "change a milestone")

        if "progress" in payload:
            try:
                progress = int(payload["progress"])
            except (TypeError, ValueError):
                raise TrackerError("Progress must be a whole number.")
            if not 0 <= progress <= 100:
                raise TrackerError("Progress must be between 0 and 100.")
            m.progress = progress
            m.completed_at = datetime.utcnow() if progress >= 100 else None
        if "forecast_date" in payload:
            m.forecast_date = self._parse_date(payload["forecast_date"], "Forecast date")
        if "planned_date" in payload:
            m.planned_date = self._parse_date(payload["planned_date"], "Planned date")
        if "priority" in payload:
            try:
                m.priority = MilestonePriority(str(payload["priority"]).lower())
            except ValueError:
                raise TrackerError("Priority must be critical, high, medium or low.")
        if "owner_id" in payload:
            owner_id = payload["owner_id"] or None
            if owner_id:
                members = {str(x.student_id) for x in (batch.members or [])}
                if str(owner_id) not in members:
                    raise TrackerError("The owner must be a member of this batch.")
            m.owner_id = owner_id
        if payload.get("blocked") is True:
            m.status = MilestoneStatus.BLOCKED
        elif payload.get("blocked") is False and m.status == MilestoneStatus.BLOCKED:
            m.status = MilestoneStatus.IN_PROGRESS

        await record(self.db, batch_id=batch.id, actor=user,
                     activity=f"Milestone updated: {m.name}", module="Tracking")
        await self.db.commit()
        return {"message": f"{m.name} updated."}

    async def submit_for_review(self, user: User, milestone_id: str) -> Dict[str, Any]:
        m, batch = await self._milestone(milestone_id)
        await self._may_manage(user, batch, "submit a milestone")
        if m.approval == ApprovalState.APPROVED:
            raise TrackerError("That milestone is already approved.")
        m.approval = ApprovalState.REVIEW_READY
        await record(self.db, batch_id=batch.id, actor=user,
                     activity=f"Milestone submitted for review: {m.name}",
                     module="Tracking")
        await self.db.commit()
        return {"message": f"{m.name} sent for review."}

    async def approve(self, user: User, milestone_id: str,
                      note: str = "") -> Dict[str, Any]:
        m, batch = await self._milestone(milestone_id)
        await self._may_manage(user, batch, "approve a milestone")
        if m.approval == ApprovalState.APPROVED:
            raise TrackerError("That milestone is already approved.")

        # Approving on unverified evidence makes the trail worthless: the
        # record would say a reviewer accepted something nobody had looked at.
        outstanding = (await self.db.execute(
            select(MilestoneEvidence)
            .where(MilestoneEvidence.milestone_id == m.id)
            .where(MilestoneEvidence.status != EvidenceStatus.VERIFIED)
        )).scalars().all()
        if outstanding:
            names = ", ".join(e.label for e in outstanding[:3])
            raise TrackerError(
                f"{len(outstanding)} piece(s) of evidence are not verified yet "
                f"({names}). Verify them, or remove what is not needed.")

        m.approval = ApprovalState.APPROVED
        m.approved_by_id = user.id
        m.approved_at = datetime.utcnow()
        m.review_note = (note or "").strip()[:2000] or None
        if m.progress < 100:
            m.progress = 100
            m.completed_at = datetime.utcnow()

        await record(self.db, batch_id=batch.id, actor=user,
                     activity=f"Milestone approved: {m.name}", module="Tracking")
        await self.db.commit()
        return {"message": f"{m.name} approved."}

    async def request_changes(self, user: User, milestone_id: str,
                              note: str) -> Dict[str, Any]:
        m, batch = await self._milestone(milestone_id)
        await self._may_manage(user, batch, "review a milestone")
        # Without a reason the owner learns only that they were refused.
        cleaned = self._text(note, 2000, "What needs changing")

        m.approval = ApprovalState.CHANGES_REQUESTED
        m.review_note = cleaned
        m.approved_by_id = None
        m.approved_at = None
        await record(self.db, batch_id=batch.id, actor=user,
                     activity=f"Changes requested on {m.name}: {cleaned[:120]}",
                     module="Tracking")
        await self.db.commit()
        return {"message": f"Changes requested on {m.name}."}

    # ---------------------------------------------------------------- evidence

    async def request_evidence(self, user: User, milestone_ids,
                               label: str = "Evidence") -> Dict[str, Any]:
        """Ask several milestones for a named piece of evidence."""
        if not milestone_ids:
            raise TrackerError("Select at least one milestone first.")
        text = self._text(label, 200, "Evidence name")

        asked, refused = 0, 0
        for milestone_id in milestone_ids:
            try:
                m, batch = await self._milestone(milestone_id)
                await self._may_manage(user, batch, "request evidence")
            except TrackerError:
                refused += 1
                continue
            exists = (await self.db.execute(
                select(MilestoneEvidence)
                .where(MilestoneEvidence.milestone_id == m.id)
                .where(MilestoneEvidence.label == text)
            )).scalars().first()
            if exists:
                continue
            self.db.add(MilestoneEvidence(
                milestone_id=m.id, label=text, status=EvidenceStatus.PENDING))
            if m.approval == ApprovalState.NOT_READY:
                m.approval = ApprovalState.PENDING
            await record(self.db, batch_id=batch.id, actor=user,
                         activity=f"Evidence requested on {m.name}: {text}",
                         module="Tracking")
            asked += 1

        await self.db.commit()
        if not asked and refused:
            raise TrackerError(
                "You do not have authority over any of the selected milestones.")
        message = f"Evidence requested on {asked} milestone" + ("s" if asked != 1 else "")
        if refused:
            message += f". {refused} skipped - not yours to manage."
        return {"asked": asked, "skipped": refused, "message": message}

    async def verify_evidence(self, user: User, evidence_id: str,
                              accept: bool = True) -> Dict[str, Any]:
        row = (await self.db.execute(
            select(MilestoneEvidence).where(MilestoneEvidence.id == evidence_id)
        )).scalar_one_or_none()
        if row is None:
            raise TrackerError("That evidence no longer exists.")
        m, batch = await self._milestone(row.milestone_id)
        await self._may_manage(user, batch, "verify evidence")

        if accept:
            if row.status == EvidenceStatus.PENDING:
                raise TrackerError(
                    "Nothing has been supplied for this yet, so there is "
                    "nothing to verify.")
            row.status = EvidenceStatus.VERIFIED
            row.verified_by_id = user.id
            row.verified_at = datetime.utcnow()
            outcome = "verified"
        else:
            row.status = EvidenceStatus.PENDING
            row.verified_by_id = None
            row.verified_at = None
            outcome = "sent back"

        await record(self.db, batch_id=batch.id, actor=user,
                     activity=f"Evidence {outcome} on {m.name}: {row.label}",
                     module="Tracking")
        await self.db.commit()
        return {"message": f"{row.label} {outcome}."}

    # --------------------------------------------------------------- checklist

    async def toggle_checklist(self, user: User, item_id: str,
                               done: bool) -> Dict[str, Any]:
        item = (await self.db.execute(
            select(MilestoneChecklistItem).where(MilestoneChecklistItem.id == item_id)
        )).scalar_one_or_none()
        if item is None:
            raise TrackerError("That checklist item no longer exists.")
        m, batch = await self._milestone(item.milestone_id)
        await self._may_manage(user, batch, "change a checklist")

        item.is_done = 1 if done else 0

        # Progress follows the checklist when there is one - two numbers that
        # can disagree is one number too many.
        items = (await self.db.execute(
            select(MilestoneChecklistItem)
            .where(MilestoneChecklistItem.milestone_id == m.id)
        )).scalars().all()
        if items:
            m.progress = round(sum(1 for i in items if i.is_done) / len(items) * 100)
            m.completed_at = datetime.utcnow() if m.progress >= 100 else None

        await self.db.commit()
        return {"message": "Checklist updated.", "progress": m.progress}

    async def add_dependency(self, user: User, milestone_id: str,
                             depends_on_id: str) -> Dict[str, Any]:
        if str(milestone_id) == str(depends_on_id):
            raise TrackerError("A milestone cannot wait on itself.")
        m, batch = await self._milestone(milestone_id)
        other, other_batch = await self._milestone(depends_on_id)
        if str(m.batch_id) != str(other.batch_id):
            raise TrackerError(
                "Milestones can only depend on others in the same project.")
        await self._may_manage(user, batch, "link milestones")

        reverse = (await self.db.execute(
            select(MilestoneDependency)
            .where(MilestoneDependency.milestone_id == other.id)
            .where(MilestoneDependency.depends_on_id == m.id)
        )).scalars().first()
        if reverse:
            raise TrackerError(
                f"“{other.name}” already waits on this one, so linking them "
                "the other way would make a loop.")

        exists = (await self.db.execute(
            select(MilestoneDependency)
            .where(MilestoneDependency.milestone_id == m.id)
            .where(MilestoneDependency.depends_on_id == other.id)
        )).scalars().first()
        if exists:
            return {"message": "That link already exists."}

        self.db.add(MilestoneDependency(milestone_id=m.id, depends_on_id=other.id))
        await self.db.commit()
        return {"message": f"“{m.name}” now waits on “{other.name}”."}

    # ------------------------------------------------------------------ bulk

    async def bulk(self, user: User, milestone_ids,
                   action: str, value: Optional[str] = None) -> Dict[str, Any]:
        """
        Approve, re-date or chase several milestones at once.

        Each one still goes through the same rules as the single-milestone
        path - a bulk button that skipped the evidence check would make the
        approval trail meaningless in exactly the cases people use bulk for.
        Refusals are counted and reported rather than swallowed.
        """
        if not milestone_ids:
            raise TrackerError("Select at least one milestone first.")

        done, refused, blocked = 0, 0, []
        for milestone_id in milestone_ids:
            try:
                if action == "approve":
                    await self.approve(user, milestone_id, "")
                elif action == "due_date":
                    if not value:
                        raise TrackerError("Choose a date first.")
                    await self.update(user, milestone_id, {"planned_date": value})
                elif action == "request_update":
                    await self.request_evidence(user, [milestone_id], value or "Evidence")
                else:
                    raise TrackerError("That is not an action this screen offers.")
                done += 1
            except TrackerError as exc:
                message = str(exc)
                if "not verified" in message:
                    blocked.append(message.split("(")[-1].rstrip(").")[:40])
                refused += 1

        if not done:
            # Say why, not just that it failed.
            if blocked:
                raise TrackerError(
                    f"None could be approved - evidence is still unverified on "
                    f"{refused} of them.")
            raise TrackerError("None of the selected milestones could be changed.")

        word = {"approve": "approved", "due_date": "re-dated",
                "request_update": "chased"}.get(action, "updated")
        message = f"{done} milestone{'' if done == 1 else 's'} {word}"
        if refused:
            message += f". {refused} skipped"
            if blocked:
                message += " - evidence not verified"
            message += "."
        return {"done": done, "skipped": refused, "message": message}
