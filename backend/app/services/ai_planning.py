"""
AI Story Approval - the trainer's review of AI-drafted epics and stories.

The rule the screen exists to enforce: nothing reaches the product backlog
without a trainer deciding on it. This service reports state and records those
decisions; it never approves anything on the model's behalf, and the AI
confidence figure is advisory only - it gates nothing.
"""

from collections import Counter
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_planning import (
    AiPlanningRun,
    CriterionKind,
    ProjectEpic,
    ProjectUserStory,
    StoryCriterion,
    StoryPriority,
    StoryRevisionRequest,
    StoryReviewStatus,
)
from app.core.logging_config import logger
from app.models.faculty import ProjectBatch
from app.models.user import User
from app.services.story_generator import GenerationError, StoryGenerator

STATUS_LABELS = {
    StoryReviewStatus.NEEDS_REVIEW: "Needs Review",
    StoryReviewStatus.REVIEWED: "Reviewed",
    StoryReviewStatus.APPROVED: "Approved",
    StoryReviewStatus.REJECTED: "Rejected",
    StoryReviewStatus.REVISION_REQUESTED: "Revision Requested",
}

# A story counts as settled once a trainer has formed a view on it.
SETTLED = {StoryReviewStatus.REVIEWED, StoryReviewStatus.APPROVED, StoryReviewStatus.REJECTED}

# Nobody has ruled on these, so regenerating over them destroys nothing.
UNDECIDED = {StoryReviewStatus.NEEDS_REVIEW, StoryReviewStatus.REVISION_REQUESTED}

assert set(STATUS_LABELS) == set(StoryReviewStatus), (
    f"STATUS_LABELS is missing: {set(StoryReviewStatus) - set(STATUS_LABELS)}"
)


class PlanningError(Exception):
    """A refusal the caller can show the trainer as-is."""


class AiPlanningService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------- loading

    async def load_batch(self, identifier: str) -> Optional[ProjectBatch]:
        # The generator reads objectives, methodology, technologies and scope to
        # build its prompt. Lazy-loading those under async raises MissingGreenlet,
        # so they are fetched up front rather than discovered at call time.
        stmt = select(ProjectBatch).options(
            selectinload(ProjectBatch.guide),
            selectinload(ProjectBatch.objectives),
            selectinload(ProjectBatch.methodology),
            selectinload(ProjectBatch.technologies),
            selectinload(ProjectBatch.scope_items),
        )
        key = identifier.strip()
        stmt = stmt.where(
            (ProjectBatch.batch_code == key) | (ProjectBatch.join_code == key.upper())
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def _stories(self, batch_id) -> List[ProjectUserStory]:
        return (await self.db.execute(
            select(ProjectUserStory)
            .where(ProjectUserStory.batch_id == batch_id)
            .options(
                selectinload(ProjectUserStory.epic),
                selectinload(ProjectUserStory.criteria),
                selectinload(ProjectUserStory.reviewed_by),
                selectinload(ProjectUserStory.revisions),
            )
            .order_by(ProjectUserStory.position, ProjectUserStory.key)
        )).scalars().all()

    async def _epics(self, batch_id) -> List[ProjectEpic]:
        return (await self.db.execute(
            select(ProjectEpic)
            .where(ProjectEpic.batch_id == batch_id)
            .order_by(ProjectEpic.position)
        )).scalars().all()

    async def _run(self, batch_id) -> Optional[AiPlanningRun]:
        return (await self.db.execute(
            select(AiPlanningRun)
            .where(AiPlanningRun.batch_id == batch_id)
            .order_by(AiPlanningRun.generated_at.desc())
        )).scalars().first()

    # ------------------------------------------------------------ fragments

    @staticmethod
    def _criteria(story: ProjectUserStory, kind: CriterionKind) -> List[StoryCriterion]:
        return sorted((c for c in story.criteria if c.kind == kind), key=lambda c: c.position)

    def _acceptance_progress(self, story: ProjectUserStory) -> tuple:
        rows = self._criteria(story, CriterionKind.ACCEPTANCE)
        return sum(1 for c in rows if c.met), len(rows)

    def _row(self, story: ProjectUserStory) -> dict:
        met, total = self._acceptance_progress(story)
        return {
            "id": str(story.id),
            "key": story.key,
            "title": story.title,
            "epic_key": story.epic.key if story.epic else None,
            "epic_title": story.epic.title if story.epic else None,
            "acceptance_met": met,
            "acceptance_total": total,
            "acceptance_complete": total > 0 and met == total,
            "story_points": story.story_points,
            "priority": story.priority.value,
            "priority_label": story.priority.value.title(),
            "ai_confidence": int(story.ai_confidence) if story.ai_confidence is not None else None,
            "review_status": story.review_status.value,
            "review_status_label": STATUS_LABELS[story.review_status],
        }

    def _detail(self, story: ProjectUserStory) -> dict:
        met, total = self._acceptance_progress(story)
        pending = sorted(
            (r for r in story.revisions if r.resolved_at is None),
            key=lambda r: r.requested_at, reverse=True,
        )
        return {
            **self._row(story),
            "narrative": story.narrative,
            "dependencies": story.dependencies,
            "trainer_comment": story.trainer_comment,
            "reviewed_by": (story.reviewed_by.full_name if story.reviewed_by else None),
            "reviewed_at": story.reviewed_at,
            "acceptance_criteria": [
                {"id": str(c.id), "text": c.text, "met": c.met}
                for c in self._criteria(story, CriterionKind.ACCEPTANCE)
            ],
            "definition_of_done": [
                {"id": str(c.id), "text": c.text, "met": c.met}
                for c in self._criteria(story, CriterionKind.DEFINITION_OF_DONE)
            ],
            "acceptance_label": f"{met} / {total}",
            "open_revision": (
                {"note": pending[0].note, "requested_at": pending[0].requested_at}
                if pending else None
            ),
        }

    # ----------------------------------------------------------------- view

    async def board(
        self,
        batch: ProjectBatch,
        *,
        search: Optional[str] = None,
        status: Optional[str] = None,
        epic: Optional[str] = None,
        priority: Optional[str] = None,
        confidence: Optional[str] = None,
        selected_key: Optional[str] = None,
    ) -> dict:
        stories = await self._stories(batch.id)
        epics = await self._epics(batch.id)
        run = await self._run(batch.id)

        total = len(stories)
        needs = [s for s in stories if s.review_status == StoryReviewStatus.NEEDS_REVIEW]
        reviewed = [s for s in stories if s.review_status in SETTLED]
        approved = [s for s in stories if s.review_status == StoryReviewStatus.APPROVED]
        in_backlog = [s for s in stories if s.moved_to_backlog_at is not None]

        def keep(s: ProjectUserStory) -> bool:
            if status and status != "all":
                if status == "needs_review" and s.review_status != StoryReviewStatus.NEEDS_REVIEW:
                    return False
                if status == "reviewed" and s.review_status not in (
                        StoryReviewStatus.REVIEWED, StoryReviewStatus.APPROVED):
                    return False
                if status == "rejected" and s.review_status != StoryReviewStatus.REJECTED:
                    return False
            if epic and (not s.epic or s.epic.key != epic):
                return False
            if priority and s.priority.value != priority:
                return False
            if confidence:
                value = s.ai_confidence or 0
                if confidence == "high" and value < 90:
                    return False
                if confidence == "medium" and not (80 <= value < 90):
                    return False
                if confidence == "low" and value >= 80:
                    return False
            if search:
                needle = search.lower()
                blob = " ".join(filter(None, [s.key, s.title, s.narrative])).lower()
                if needle not in blob:
                    return False
            return True

        visible = [s for s in stories if keep(s)]
        selected = next((s for s in stories if s.key == selected_key), None)
        if selected is None:
            selected = next((s for s in visible if s.review_status == StoryReviewStatus.NEEDS_REVIEW),
                            visible[0] if visible else None)

        quality = (int(round(sum(s.ai_confidence or 0 for s in stories) / total))
                   if total else None)

        return {
            "header": {
                "batch_id": str(batch.id),
                "batch_code": batch.batch_code,
                "join_code": batch.join_code,
                "display_name": f"Batch {(batch.join_code or batch.batch_code).rsplit('-', 1)[-1]}",
                "project_title": batch.title,
                "department": batch.department,
                "guide": batch.guide.full_name if batch.guide else None,
            },
            "run": {
                "model": run.model_label if run else None,
                "generated_at": run.generated_at if run else None,
                "source_summary": run.source_summary if run else None,
                "quality_percent": run.quality_percent if run else None,
            } if run else None,
            "stages": self._stages(total, len(reviewed), len(in_backlog)),
            "kpis": [
                {"id": "epics", "value": str(len(epics)), "label": "Epics"},
                {"id": "drafts", "value": str(total), "label": "Draft Stories"},
                {"id": "reviewed", "value": str(len(reviewed)), "label": "Reviewed"},
                {"id": "needs", "value": str(len(needs)), "label": "Need Review"},
                {"id": "points", "value": str(sum(s.story_points or 0 for s in stories)),
                 "label": "Story Points"},
                {"id": "quality", "value": f"{quality}%" if quality is not None else "—",
                 "label": "AI Quality"},
            ],
            "rows": [self._row(s) for s in visible],
            "selected": self._detail(selected) if selected else None,
            "epics": [{"key": e.key, "title": e.title} for e in epics],
            "priorities": [p.value for p in StoryPriority],
            "counts": {
                "total": total,
                "reviewed": len(reviewed),
                "needs_review": len(needs),
                "approved": len(approved),
                "rejected": sum(1 for s in stories if s.review_status == StoryReviewStatus.REJECTED),
                "in_backlog": len(in_backlog),
                "showing": len(visible),
            },
            "checklist": self._checklist(stories),
            "can_continue": len(needs) == 0 and total > 0,
            "after_approval": [
                "Approved stories enter Product Backlog.",
                "Stories remain unassigned and unscheduled.",
                "Students cannot see them yet.",
                "Trainer selects sprint and assignee later.",
            ],
            "governance": (
                "AI cannot approve, publish or assign stories. "
                "Final decisions are always made by the trainer."
            ),
        }

    @staticmethod
    def _stages(total: int, reviewed: int, in_backlog: int) -> List[dict]:
        """The five-step strip. Later steps stay locked, and say what unlocks them."""
        analysed = total > 0
        drafted = total > 0
        approval_done = total > 0 and reviewed == total
        backlog_done = in_backlog > 0
        rows = [
            ("analysed", "Project Analysed", analysed, None),
            ("drafted", "Draft Stories Generated", drafted, None),
            ("approval", "Trainer Approval", approval_done, None),
            ("backlog", "Product Backlog", backlog_done, "Unlocked after all stories are reviewed"),
            ("sprint", "Sprint Planning", False, "Unlocked after stories enter backlog"),
        ]
        out, current_taken = [], False
        for key, label, done, locked_note in rows:
            if done:
                state = "complete"
            elif not current_taken:
                state, current_taken = "active", True
            else:
                state = "locked"
            out.append({
                "key": key, "label": label, "state": state,
                "note": ("Complete" if state == "complete"
                         else "Active" if state == "active"
                         else locked_note or "Locked"),
            })
        return out

    def _checklist(self, stories: List[ProjectUserStory]) -> dict:
        """
        Five gates, every one counted from the stories themselves so the figure
        beside a gate and the table below it can never disagree.
        """
        total = len(stories)
        with_epic = sum(1 for s in stories if s.epic_id is not None)
        titles = Counter(s.title.strip().lower() for s in stories)
        duplicates = sum(1 for c in titles.values() if c > 1)
        complete_ac = sum(1 for s in stories if self._acceptance_progress(s)[0]
                          == self._acceptance_progress(s)[1] and self._acceptance_progress(s)[1] > 0)
        needs_dependency_review = [
            s for s in stories
            if s.dependencies and s.review_status == StoryReviewStatus.NEEDS_REVIEW
        ]
        unpointed = [s for s in stories if not s.story_points]
        needs = sum(1 for s in stories if s.review_status == StoryReviewStatus.NEEDS_REVIEW)

        items = [
            {"key": "scope", "label": "Scope aligned with project goals",
             "passed": total > 0 and with_epic == total,
             "detail": "Passed" if with_epic == total else f"{total - with_epic} unassigned"},
            {"key": "duplicates", "label": "No duplicate or overlapping stories",
             "passed": duplicates == 0,
             "detail": "Passed" if duplicates == 0 else f"{duplicates} duplicated"},
            {"key": "acceptance", "label": "Acceptance criteria quality",
             "passed": total > 0 and complete_ac == total,
             "detail": "Passed" if complete_ac == total else f"{complete_ac} / {total} complete"},
            {"key": "dependencies", "label": "Dependencies reviewed",
             "passed": not needs_dependency_review,
             "detail": "Passed" if not needs_dependency_review
                       else f"{len(needs_dependency_review)} outstanding"},
            {"key": "points", "label": "Story points confirmed",
             "passed": not unpointed,
             "detail": "Passed" if not unpointed else f"{len(unpointed)} unpointed"},
        ]
        return {
            "items": items,
            "passed": sum(1 for i in items if i["passed"]),
            "total": len(items),
            "outstanding": needs,
            "outstanding_label": (
                f"{needs} stor{'ies' if needs != 1 else 'y'} still need review" if needs
                else "Every story has been reviewed"
            ),
        }

    # ------------------------------------------------------------- mutations

    async def _story(self, batch: ProjectBatch, story_id: str) -> ProjectUserStory:
        story = (await self.db.execute(
            select(ProjectUserStory)
            .where(ProjectUserStory.id == story_id)
            .options(selectinload(ProjectUserStory.criteria),
                     selectinload(ProjectUserStory.revisions))
        )).scalar_one_or_none()
        if story is None or str(story.batch_id) != str(batch.id):
            # Same reason the batch routes check: an id in the URL proves nothing
            # about the caller's right to it.
            raise PlanningError("That story is not part of this batch.")
        return story

    async def decide(
        self, batch: ProjectBatch, story_id: str, decision: str, user: User,
        *, note: Optional[str] = None,
    ) -> dict:
        story = await self._story(batch, story_id)

        if decision == "approve":
            met, total = self._acceptance_progress(story)
            if total and met < total:
                open_count = total - met
                raise PlanningError(
                    f"{story.key} has {open_count} acceptance "
                    f"criteri{'on' if open_count == 1 else 'a'} still open. "
                    f"Resolve {'it' if open_count == 1 else 'them'} or request a revision "
                    "before approving."
                )
            story.review_status = StoryReviewStatus.APPROVED
        elif decision == "reject":
            story.review_status = StoryReviewStatus.REJECTED
        elif decision == "reviewed":
            story.review_status = StoryReviewStatus.REVIEWED
        elif decision == "request_revision":
            if not (note or "").strip():
                raise PlanningError("Say what needs redrafting so the revision is actionable.")
            story.review_status = StoryReviewStatus.REVISION_REQUESTED
            self.db.add(StoryRevisionRequest(
                story_id=story.id, note=note.strip(), requested_by_id=user.id,
            ))
        else:
            raise PlanningError("Unknown decision.")

        if note is not None and decision != "request_revision":
            story.trainer_comment = note.strip() or None
        story.reviewed_by_id = user.id
        story.reviewed_at = datetime.utcnow()
        await self.db.commit()
        return {"key": story.key, "review_status": story.review_status.value}

    async def update(self, batch: ProjectBatch, story_id: str, payload: dict, user: User) -> dict:
        story = await self._story(batch, story_id)
        if "story_points" in payload and payload["story_points"] is not None:
            points = int(payload["story_points"])
            if points < 0 or points > 100:
                raise PlanningError("Story points must be between 0 and 100.")
            story.story_points = points
        if payload.get("priority"):
            try:
                story.priority = StoryPriority(payload["priority"])
            except ValueError:
                raise PlanningError("Priority must be high, medium or low.")
        if "trainer_comment" in payload:
            comment = (payload["trainer_comment"] or "").strip()
            if len(comment) > 500:
                raise PlanningError("Keep the comment under 500 characters.")
            story.trainer_comment = comment or None
        if "dependencies" in payload:
            story.dependencies = (payload["dependencies"] or "").strip() or None
        await self.db.commit()
        return self._detail(await self._story(batch, story_id))

    async def mark_reviewed(self, batch: ProjectBatch, story_ids: List[str], user: User) -> dict:
        stories = await self._stories(batch.id)
        wanted = set(story_ids)
        touched = []
        for s in stories:
            if str(s.id) in wanted and s.review_status == StoryReviewStatus.NEEDS_REVIEW:
                s.review_status = StoryReviewStatus.REVIEWED
                s.reviewed_by_id = user.id
                s.reviewed_at = datetime.utcnow()
                touched.append(s.key)
        await self.db.commit()
        return {"marked": touched, "count": len(touched)}

    async def move_to_backlog(self, batch: ProjectBatch, user: User) -> dict:
        """
        Move the approved set across.

        Refused while anything is unreviewed - that is the whole point of the
        gate, and letting it through 'just this once' would make the Product
        Backlog step meaningless.
        """
        stories = await self._stories(batch.id)
        outstanding = [s for s in stories if s.review_status == StoryReviewStatus.NEEDS_REVIEW]
        if outstanding:
            raise PlanningError(
                f"{len(outstanding)} stor{'ies' if len(outstanding) != 1 else 'y'} "
                "still need review. Resolve them before moving anything to the backlog."
            )
        approved = [s for s in stories if s.review_status == StoryReviewStatus.APPROVED]
        if not approved:
            raise PlanningError("No stories are approved yet, so there is nothing to move.")

        now = datetime.utcnow()
        for s in approved:
            s.moved_to_backlog_at = now
        await self.db.commit()
        return {"moved": [s.key for s in approved], "count": len(approved)}

    # ---------------------------------------------------------- regeneration

    async def _runs(self, batch_id) -> List[AiPlanningRun]:
        return (await self.db.execute(
            select(AiPlanningRun).where(AiPlanningRun.batch_id == batch_id)
        )).scalars().all()

    async def preview_regeneration(self, batch: ProjectBatch, scope: str) -> dict:
        """
        What a regeneration would destroy, before it runs.

        Surfaced so that "replace everything" is a counted decision rather than
        a surprise.
        """
        stories = await self._stories(batch.id)
        decided = [s for s in stories if s.review_status in SETTLED]
        undecided = [s for s in stories if s.review_status in UNDECIDED]
        return {
            "scope": scope,
            "total": len(stories),
            "undecided": len(undecided),
            "decided": len(decided),
            "will_replace": len(stories) if scope == "all" else len(undecided),
            "decisions_discarded": len(decided) if scope == "all" else 0,
        }

    async def regenerate(
        self, batch: ProjectBatch, user: User, *, scope: str = "pending",
        confirm: bool = False, model: Optional[str] = None,
    ) -> dict:
        """
        Redraft stories from the project details.

        `pending` replaces only what nobody has ruled on. `all` replaces the lot
        and needs explicit confirmation, because it discards recorded trainer
        decisions - and the count of what it would discard is reported rather
        than buried.
        """
        if scope not in ("pending", "all"):
            raise PlanningError("Scope must be pending or all.")

        plan = await self.preview_regeneration(batch, scope)
        if scope == "all" and plan["decisions_discarded"] and not confirm:
            raise PlanningError(
                f"Replacing every story discards {plan['decisions_discarded']} recorded "
                "decision(s). Confirm to proceed, or regenerate only the pending stories."
            )
        if scope == "pending" and plan["undecided"] == 0:
            raise PlanningError(
                "Every story has already been ruled on, so nothing is pending to redraft. "
                "Use replace-all if you want to start again."
            )

        existing = await self._stories(batch.id)
        keep = [s for s in existing if s.review_status in SETTLED] if scope == "pending" else []
        keep_ids = {s.id for s in keep}
        target = plan["will_replace"]

        generator = StoryGenerator(model)
        try:
            draft = await generator.generate(batch, target, user_id=user.id)
        except GenerationError as exc:
            # Nothing has been written yet, so the existing backlog is intact.
            raise PlanningError(str(exc))

        now = datetime.utcnow()
        for old in await self._runs(batch.id):
            old.is_current = False

        run = AiPlanningRun(
            batch_id=batch.id,
            model_label=draft["model"],
            source_summary=(
                f"{len(batch.objectives)} objectives, {len(batch.methodology)} methodology steps "
                f"and {len(batch.technologies)} technologies; scope={scope}."
            ),
            generated_at=now,
            generated_by_id=user.id,
            is_current=True,
            story_count=len(draft["stories"]) + len(keep),
            epic_count=len(draft["epics"]),
        )
        self.db.add(run)
        await self.db.flush()

        # Drop only the stories this scope replaces. Kept ones are untouched, so
        # their decision, comment and reviewer survive verbatim.
        replaced = []
        for story in existing:
            if story.id in keep_ids:
                continue
            replaced.append(story.key)
            await self.db.delete(story)
        await self.db.flush()

        epics_by_key = {}
        if scope == "all":
            for epic in await self._epics(batch.id):
                await self.db.delete(epic)
            await self.db.flush()
        else:
            epics_by_key = {e.key: e for e in await self._epics(batch.id)}

        for e in draft["epics"]:
            if e["key"] in epics_by_key:
                continue
            epic = ProjectEpic(
                batch_id=batch.id, key=e["key"], title=e["title"],
                description=e["description"], position=e["position"],
            )
            self.db.add(epic)
            await self.db.flush()
            epics_by_key[e["key"]] = epic

        # Continue past every key this batch has used, including the ones just
        # retired. Recycling a key would let a regenerated story inherit the
        # identity of a deleted one, so notes and comments elsewhere would
        # silently point at different content.
        used = {s.key for s in existing} | {s.key for s in keep}
        next_num = 101
        created = []
        for item in draft["stories"]:
            while f"US-{next_num}" in used:
                next_num += 1
            key = f"US-{next_num}"
            used.add(key)
            next_num += 1

            epic = epics_by_key.get(item["epic_key"]) if item["epic_key"] else None
            story = ProjectUserStory(
                batch_id=batch.id,
                epic_id=epic.id if epic else None,
                run_id=run.id,
                key=key,
                title=item["title"],
                narrative=item["narrative"],
                dependencies=item["dependencies"],
                story_points=item["story_points"],
                priority=StoryPriority(item["priority"]),
                ai_confidence=item["ai_confidence"],
                # Always. A regeneration can never approve its own output.
                review_status=StoryReviewStatus.NEEDS_REVIEW,
                position=len(keep) + item["position"],
            )
            self.db.add(story)
            await self.db.flush()
            created.append(key)

            for i, text in enumerate(item["acceptance_criteria"]):
                self.db.add(StoryCriterion(story_id=story.id, kind=CriterionKind.ACCEPTANCE,
                                           text=text, met=True, position=i))
            for i, text in enumerate(item["definition_of_done"]):
                self.db.add(StoryCriterion(story_id=story.id,
                                           kind=CriterionKind.DEFINITION_OF_DONE,
                                           text=text, met=True, position=i))

        scores = [s["ai_confidence"] for s in draft["stories"] if s["ai_confidence"] is not None]
        run.quality_percent = int(round(sum(scores) / len(scores))) if scores else None

        await self.db.commit()
        logger.info(f"[Planning] {user.email} regenerated {len(created)} stories on "
                    f"{batch.batch_code} (scope={scope}, kept={len(keep)})")
        return {
            "scope": scope,
            "model": draft["model"],
            "created": created,
            "created_count": len(created),
            "kept_count": len(keep),
            "replaced_count": len(replaced),
            "decisions_discarded": plan["decisions_discarded"],
        }
