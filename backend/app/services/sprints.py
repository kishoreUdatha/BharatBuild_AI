"""
Sprints - the time boxes a batch's approved stories are scheduled into.

The User Stories screen answers "what is this story doing"; this one answers
"is this sprint going to land". So every figure here is a roll-up of the
stories actually scheduled into the sprint - its points, how many of them are
done, and what is left - rather than anything typed in separately. A sprint
cannot claim progress its stories do not have.

Unscheduled work is reported alongside the sprints for the same reason: a
plan that looks complete while eleven stories sit outside every sprint is not
a plan, and the screen should say so.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_planning import ProjectUserStory
from app.models.backlog import ProjectSprint, SprintState, StoryWorkflowStatus
from app.models.faculty import ProjectBatch
from app.services.user_stories import (
    SPRINT_STATE_LABELS,
    StoryError,
    UserStoryService,
    _pct,
    _person,
    _window,
)


def _joined_on(story, start: date, end: date) -> date:
    """The day a story became part of the sprint's commitment."""
    made = story.created_at.date() if story.created_at else None
    if made is not None and start <= made <= end:
        return made
    return start


class SprintService:
    """Reads and writes sprints. `StoryError` is the refusal type, as elsewhere."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.stories = UserStoryService(db)

    async def _sprints(self, batch_id) -> List[ProjectSprint]:
        return (await self.db.execute(
            select(ProjectSprint)
            .where(ProjectSprint.batch_id == batch_id)
            .order_by(ProjectSprint.position, ProjectSprint.key)
        )).scalars().all()

    async def _scheduled(self, batch_id) -> List[ProjectUserStory]:
        """The backlog, which is the only thing a sprint can contain."""
        return (await self.db.execute(
            select(ProjectUserStory)
            .where(ProjectUserStory.batch_id == batch_id)
            .where(ProjectUserStory.moved_to_backlog_at.isnot(None))
            .options(
                selectinload(ProjectUserStory.assignee),
                selectinload(ProjectUserStory.epic),
            )
            .order_by(ProjectUserStory.key)
        )).scalars().all()

    @staticmethod
    def _story_line(story: ProjectUserStory) -> dict:
        return {
            "id": str(story.id),
            "key": story.key,
            "title": story.title,
            "status": story.workflow_status.value,
            "status_label": story.workflow_status.value.replace("_", " ").title(),
            "story_points": story.story_points or 0,
            "assignee": _person(story.assignee),
            "epic_key": story.epic.key if story.epic else None,
        }

    def _roll_up(self, sprint: Optional[ProjectSprint],
                 stories: List[ProjectUserStory], today: date) -> dict:
        points = sum(s.story_points or 0 for s in stories)
        done = [s for s in stories if s.workflow_status == StoryWorkflowStatus.DONE]
        done_points = sum(s.story_points or 0 for s in done)
        counts = {
            status.value: sum(1 for s in stories if s.workflow_status == status)
            for status in StoryWorkflowStatus
        }

        # Days left is only meaningful while the sprint is running, and only
        # from its own end date - a sprint with no dates gets None, not zero.
        days_left = None
        if sprint is not None and sprint.end_date and sprint.state == SprintState.ACTIVE:
            days_left = (sprint.end_date - today).days

        return {
            "stories": len(stories),
            "points": points,
            "done": len(done),
            "done_points": done_points,
            "percent": int(round(_pct(len(done), len(stories)))),
            "points_percent": int(round(_pct(done_points, points))),
            "counts": counts,
            "days_left": days_left,
            # Past its end date with work still open. Stated rather than
            # inferred on the screen, so both places agree on what "late" is.
            "overdue": bool(
                sprint is not None and sprint.end_date
                and sprint.state != SprintState.COMPLETED
                and sprint.end_date < today
                and len(done) < len(stories)
            ),
        }

    async def board(self, batch: ProjectBatch) -> dict:
        sprints = await self._sprints(batch.id)
        backlog = await self._scheduled(batch.id)
        today = date.today()

        by_sprint = {str(s.id): [] for s in sprints}
        unscheduled: List[ProjectUserStory] = []
        for story in backlog:
            if story.sprint_id and str(story.sprint_id) in by_sprint:
                by_sprint[str(story.sprint_id)].append(story)
            else:
                unscheduled.append(story)

        rows = []
        for sprint in sprints:
            held = by_sprint[str(sprint.id)]
            rows.append({
                "id": str(sprint.id),
                "key": sprint.key,
                "name": sprint.name,
                "goal": sprint.goal,
                "state": sprint.state.value,
                "state_label": SPRINT_STATE_LABELS[sprint.state],
                "start_date": sprint.start_date,
                "end_date": sprint.end_date,
                "window": _window(sprint),
                **self._roll_up(sprint, held, today),
                "story_rows": [self._story_line(s) for s in held],
            })

        active = next((r for r in rows if r["state"] == SprintState.ACTIVE.value), None)
        planned = [r for r in rows if r["state"] == SprintState.PLANNED.value]
        completed = [r for r in rows if r["state"] == SprintState.COMPLETED.value]

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
                {"id": "sprints", "value": len(rows), "label": "Sprints", "hint": None},
                {"id": "active", "value": 1 if active else 0, "label": "Active",
                 "hint": active["name"] if active else "None running"},
                {"id": "planned", "value": len(planned), "label": "Planned", "hint": None},
                {"id": "completed", "value": len(completed), "label": "Completed", "hint": None},
                {"id": "scheduled", "value": len(backlog) - len(unscheduled),
                 "label": "Stories Scheduled", "hint": f"of {len(backlog)} in the backlog"},
                {"id": "unscheduled", "value": len(unscheduled), "label": "Unscheduled",
                 "hint": "Not in any sprint"},
            ],
            "rows": rows,
            "unscheduled": {
                **self._roll_up(None, unscheduled, today),
                "story_rows": [self._story_line(s) for s in unscheduled],
            },
            "states": [{"value": s.value, "label": SPRINT_STATE_LABELS[s]} for s in SprintState],
            "backlog_total": len(backlog),
        }

    # -------------------------------------------------------------- writing

    async def _sprint(self, batch: ProjectBatch, sprint_id: str) -> ProjectSprint:
        sprint = (await self.db.execute(
            select(ProjectSprint)
            .where(ProjectSprint.id == sprint_id)
            .where(ProjectSprint.batch_id == batch.id)
        )).scalars().first()
        if sprint is None:
            raise StoryError("That sprint is not on this batch.")
        return sprint

    async def create(self, batch: ProjectBatch, payload: dict) -> dict:
        name = (payload.get("name") or "").strip()
        if not name:
            raise StoryError("A sprint needs a name.")
        existing = await self._sprints(batch.id)
        if any(s.name.lower() == name.lower() for s in existing):
            raise StoryError(f"{name} already exists on this batch.")

        start, end = payload.get("start_date"), payload.get("end_date")
        if start and end and end < start:
            raise StoryError("A sprint cannot end before it starts.")

        state = SprintState(payload.get("state") or "planned")
        if state == SprintState.ACTIVE:
            await self._stand_down_others(existing)

        sprint = ProjectSprint(
            batch_id=batch.id,
            key=f"SP-{len(existing) + 1:02d}",
            name=name[:80],
            goal=((payload.get("goal") or "").strip() or None),
            start_date=start,
            end_date=end,
            state=state,
            position=len(existing),
        )
        self.db.add(sprint)
        await self.db.commit()
        await self.db.refresh(sprint)
        return {"id": str(sprint.id), "key": sprint.key, "name": sprint.name}

    @staticmethod
    async def _stand_down_others(sprints: List[ProjectSprint],
                                 keep: Optional[ProjectSprint] = None) -> None:
        """
        One sprint runs at a time.

        A team works through a backlog in sequence, so two active sprints
        would make "the current sprint" meaningless on every other screen.
        Starting one moves any other running sprint back to planned rather
        than refusing, which is what the trainer meant by starting this one.
        """
        for other in sprints:
            if other is not keep and other.state == SprintState.ACTIVE:
                other.state = SprintState.PLANNED

    async def burndown(self, batch: ProjectBatch, sprint_id: str) -> dict:
        """
        Points remaining on each day of one sprint, against the ideal line.

        Remaining is measured from `completed_at`, not from today's status: a
        story finished on Tuesday has to come off Tuesday's total, or the line
        only ever describes the present and the shape of the sprint is lost.

        Scope changes are part of the picture, so a story added mid-sprint
        raises the line rather than being backdated - that is the honest read
        of what the team was carrying that day.
        """
        sprint = await self._sprint(batch, sprint_id)

        stories = (await self.db.execute(
            select(ProjectUserStory)
            .where(ProjectUserStory.sprint_id == sprint.id)
        )).scalars().all()

        total = sum(st.story_points or 0 for st in stories)

        start = sprint.start_date
        end = sprint.end_date
        if start is None or end is None or end < start:
            # Without dates there is no axis to draw against.
            return {
                "sprint": {"id": str(sprint.id), "name": sprint.name,
                           "state": sprint.state.value, "goal": sprint.goal,
                           "start_date": start, "end_date": end},
                "total_points": total,
                "days": [],
                "unscheduled": True,
            }

        span = (end - start).days
        today = date.today()

        days = []
        for offset in range(span + 1):
            day = start + timedelta(days=offset)

            done_by_day = sum(
                (st.story_points or 0) for st in stories
                if st.completed_at is not None and st.completed_at.date() <= day
            )
            # Scope as it stood that day. A story created during the sprint
            # joins on its own day - that is the scope change worth seeing.
            # One created outside the window (before it, or attached to it
            # afterwards) counts from day one: it was part of the commitment,
            # and dating it by a stray timestamp would empty the chart.
            scope_by_day = sum(
                (st.story_points or 0) for st in stories
                if _joined_on(st, start, end) <= day
            )
            ideal = total * (1 - offset / span) if span else 0.0

            days.append({
                "date": day,
                "day": offset + 1,
                # The future has no actual line: drawing one to zero would
                # claim work that has not happened.
                "remaining": (scope_by_day - done_by_day) if day <= today else None,
                "ideal": round(ideal, 1),
                "completed": done_by_day,
                "scope": scope_by_day,
                "is_today": day == today,
            })

        burned = sum(
            (st.story_points or 0) for st in stories if st.completed_at is not None
        )
        elapsed = [d for d in days if d["remaining"] is not None]
        latest = elapsed[-1] if elapsed else None

        return {
            "sprint": {"id": str(sprint.id), "name": sprint.name,
                       "state": sprint.state.value, "goal": sprint.goal,
                       "start_date": start, "end_date": end},
            "total_points": total,
            "completed_points": burned,
            "remaining_points": (latest["remaining"] if latest else total),
            "days": days,
            "story_count": len(stories),
            # Where the team stands against the guide: negative is ahead.
            "variance": (round(latest["remaining"] - latest["ideal"], 1)
                         if latest else 0),
            "unscheduled": False,
        }

    async def update(self, batch: ProjectBatch, sprint_id: str, payload: dict) -> dict:
        sprint = await self._sprint(batch, sprint_id)
        sprints = await self._sprints(batch.id)

        if payload.get("name"):
            name = payload["name"].strip()[:80]
            if any(s.name.lower() == name.lower() and s.id != sprint.id for s in sprints):
                raise StoryError(f"{name} already exists on this batch.")
            sprint.name = name

        if "goal" in payload:
            sprint.goal = (payload["goal"] or "").strip()[:300] or None
        if "start_date" in payload:
            sprint.start_date = payload["start_date"]
        if "end_date" in payload:
            sprint.end_date = payload["end_date"]
        if (sprint.start_date and sprint.end_date
                and sprint.end_date < sprint.start_date):
            raise StoryError("A sprint cannot end before it starts.")

        if payload.get("state"):
            state = SprintState(payload["state"])
            if state == SprintState.ACTIVE:
                await self._stand_down_others(sprints, keep=sprint)
            sprint.state = state

        await self.db.commit()
        return {"id": str(sprint.id), "name": sprint.name, "state": sprint.state.value}

    async def schedule(self, batch: ProjectBatch, sprint_id: Optional[str],
                       story_ids: List[str]) -> dict:
        """
        Move stories into a sprint, or out of every sprint when sprint_id is None.

        Only backlog stories can be scheduled: anything still in AI planning has
        not been agreed to yet, and putting it in a sprint would schedule work
        nobody has approved.
        """
        sprint = await self._sprint(batch, sprint_id) if sprint_id else None
        backlog = {str(s.id): s for s in await self._scheduled(batch.id)}

        moved = []
        for story_id in story_ids:
            story = backlog.get(str(story_id))
            if story is None:
                raise StoryError("One of those stories is not on this batch's backlog.")
            story.sprint_id = sprint.id if sprint else None
            moved.append(story.key)

        if not moved:
            raise StoryError("No stories were selected.")
        await self.db.commit()
        return {
            "moved": moved,
            "count": len(moved),
            "sprint": sprint.name if sprint else None,
        }
