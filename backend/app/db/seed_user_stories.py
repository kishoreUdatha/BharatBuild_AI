"""
User Stories seeder - moves approved drafts onto the backlog and runs them.

    python -m app.db.seed_user_stories

Idempotent: rebuilds sprints, assignments, delivery status, story tasks,
comments and events for the target academic year.

One batch in four is deliberately left in AI planning with nothing moved
across. The User Stories screen has an empty state that explains what is
holding the backlog up, and a seeder that populated every batch would mean
nobody ever saw it.

Nothing here invents stories. It takes the ones AI planning drafted, approves
them the way a trainer would, and then does what the trainer does next -
schedules them, hands them out and moves them along.
"""

import asyncio
import random
from datetime import date, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal, init_db
from app.models.ai_planning import ProjectUserStory, StoryReviewStatus
from app.models.backlog import (
    ProjectSprint,
    SprintState,
    StoryComment,
    StoryEvent,
    StoryEventKind,
    StoryType,
    StoryWorkflowStatus,
)
from app.models.faculty import ProjectBatch, ProjectBatchMember
from app.models.project_tracking import ProjectTask, TaskPriority, TaskStatus

ACADEMIC_YEAR = "2026-27"

# The delivery mix, one entry per story position. Roughly the shape a real
# board has a few weeks in: most of it still ahead, a little of it finished.
FLOW = [
    StoryWorkflowStatus.DONE,
    StoryWorkflowStatus.DONE,
    StoryWorkflowStatus.IN_REVIEW,
    StoryWorkflowStatus.IN_PROGRESS,
    StoryWorkflowStatus.IN_PROGRESS,
    StoryWorkflowStatus.TO_DO,
    StoryWorkflowStatus.TO_DO,
    StoryWorkflowStatus.TO_DO,
]

SPRINTS = [
    ("Sprint 1", "Data foundation in place", SprintState.COMPLETED, -42, -29),
    ("Sprint 2", "Baseline model and pipeline", SprintState.COMPLETED, -28, -15),
    ("Sprint 3", "Delivery surface and evaluation", SprintState.ACTIVE, -14, -1),
    ("Sprint 4", "Documentation and final review", SprintState.PLANNED, 0, 13),
]

# Which sprint a story lands in, by how far along it is. Finished work sits in
# a closed sprint; work nobody has started is either in the current one or
# still unscheduled, which is what a trainer opens this screen to fix.
SPRINT_FOR = {
    StoryWorkflowStatus.DONE: 0,
    StoryWorkflowStatus.IN_REVIEW: 1,
    StoryWorkflowStatus.IN_PROGRESS: 2,
    StoryWorkflowStatus.TO_DO: 2,
}

TASKS = [
    ("Write the data contract", TaskStatus.DONE),
    ("Wire the endpoint and its tests", TaskStatus.IN_PROGRESS),
    ("Record the demo for the review", TaskStatus.OPEN),
]

COMMENTS = [
    "Split the validation out if it grows past this sprint.",
    "Check this against the acceptance criteria before you move it to review.",
    "Good - keep the error handling in the same place as the retry.",
]


async def seed(rng: random.Random) -> None:
    async with AsyncSessionLocal() as db:
        batches = (await db.execute(
            select(ProjectBatch)
            .where(ProjectBatch.academic_year == ACADEMIC_YEAR)
            .where(ProjectBatch.is_active.is_(True))
            .options(
                selectinload(ProjectBatch.members).selectinload(ProjectBatchMember.student),
                selectinload(ProjectBatch.guide),
            )
            .order_by(ProjectBatch.batch_code)
        )).scalars().all()

        if not batches:
            print(f"No batches for {ACADEMIC_YEAR}; run seed_faculty first.")
            return

        ids = [b.id for b in batches]
        story_ids = (await db.execute(
            select(ProjectUserStory.id).where(ProjectUserStory.batch_id.in_(ids))
        )).scalars().all()
        if not story_ids:
            print("No drafted stories; run seed_ai_planning first.")
            return

        # Clear what this seeder owns, and only what it owns: tasks written
        # against a story, not the batch-level tasks the tracker seeder makes.
        await db.execute(delete(StoryEvent).where(StoryEvent.story_id.in_(story_ids)))
        await db.execute(delete(StoryComment).where(StoryComment.story_id.in_(story_ids)))
        await db.execute(delete(ProjectTask).where(ProjectTask.story_id.in_(story_ids)))
        await db.execute(delete(ProjectSprint).where(ProjectSprint.batch_id.in_(ids)))
        await db.flush()

        today = date.today()
        now = datetime.utcnow()
        moved_batches = 0
        assigned_stories = 0

        for b_index, batch in enumerate(batches):
            stories = (await db.execute(
                select(ProjectUserStory)
                .where(ProjectUserStory.batch_id == batch.id)
                .order_by(ProjectUserStory.position, ProjectUserStory.key)
            )).scalars().all()
            if not stories:
                continue

            # Reset delivery state first, so a batch left in planning this run
            # does not keep an assignee from the last one.
            for story in stories:
                story.workflow_status = StoryWorkflowStatus.TO_DO
                story.story_type = StoryType.STORY
                story.assignee_id = None
                story.sprint_id = None
                story.started_at = None
                story.completed_at = None
                story.moved_to_backlog_at = None

            # One batch in four stays upstream, so the empty state is real.
            if b_index % 4 == 3:
                continue

            members = [m for m in batch.members if m.is_active and m.student is not None]
            sprints = []
            for position, (name, goal, state, start_offset, end_offset) in enumerate(SPRINTS):
                sprint = ProjectSprint(
                    batch_id=batch.id,
                    key=f"SP-{position + 1:02d}",
                    name=name,
                    goal=goal,
                    start_date=today + timedelta(days=start_offset),
                    end_date=today + timedelta(days=end_offset),
                    state=state,
                    position=position,
                )
                db.add(sprint)
                sprints.append(sprint)
            await db.flush()

            for s_index, story in enumerate(stories):
                flow = FLOW[(s_index + b_index) % len(FLOW)]
                story.review_status = StoryReviewStatus.APPROVED
                story.reviewed_by_id = batch.guide_id
                story.reviewed_at = now - timedelta(days=20, hours=s_index)
                story.moved_to_backlog_at = now - timedelta(days=19)
                story.workflow_status = flow
                story.story_type = (StoryType.BUG if (s_index + b_index) % 11 == 4
                                    else StoryType.SPIKE if (s_index + b_index) % 13 == 7
                                    else StoryType.STORY)

                # The last To Do story of each batch is left unassigned and
                # unscheduled: that is the work the screen exists to hand out.
                trailing = flow == StoryWorkflowStatus.TO_DO and s_index == len(stories) - 1
                if members and not trailing:
                    student = members[(s_index + b_index) % len(members)].student
                    story.assignee_id = student.id
                    story.sprint_id = sprints[SPRINT_FOR[flow]].id
                    assigned_stories += 1
                else:
                    student = None

                if flow != StoryWorkflowStatus.TO_DO:
                    story.started_at = now - timedelta(days=12 - s_index)
                if flow == StoryWorkflowStatus.DONE:
                    story.completed_at = now - timedelta(days=6 - (s_index % 4))

                actor = batch.guide
                actor_name = actor.full_name if actor else "AI Planning"
                db.add(StoryEvent(
                    story_id=story.id, actor_id=None, actor_name="AI Planning",
                    kind=StoryEventKind.CREATED,
                    summary=f"{story.key} drafted and approved",
                    occurred_at=now - timedelta(days=20, hours=s_index),
                ))
                if student is not None:
                    db.add(StoryEvent(
                        story_id=story.id,
                        actor_id=batch.guide_id, actor_name=actor_name,
                        kind=StoryEventKind.ASSIGNED,
                        summary=f"Assigned to {student.full_name}",
                        to_value=student.full_name,
                        occurred_at=now - timedelta(days=18, hours=s_index),
                    ))
                if flow != StoryWorkflowStatus.TO_DO:
                    db.add(StoryEvent(
                        story_id=story.id,
                        actor_id=batch.guide_id, actor_name=actor_name,
                        kind=StoryEventKind.STATUS_CHANGED,
                        summary="Status changed",
                        from_value="To Do",
                        to_value=flow.value.replace("_", " ").title(),
                        occurred_at=now - timedelta(days=12 - s_index),
                    ))

                # Tasks and comments on the work that is actually moving; a
                # story nobody has started has nothing to say about it yet.
                if flow in (StoryWorkflowStatus.IN_PROGRESS, StoryWorkflowStatus.IN_REVIEW):
                    for t_index, (title, task_status) in enumerate(TASKS):
                        db.add(ProjectTask(
                            batch_id=batch.id,
                            story_id=story.id,
                            title=title,
                            assignee_id=story.assignee_id,
                            priority=TaskPriority.MEDIUM,
                            status=task_status,
                            due_date=today + timedelta(days=3 + t_index),
                            progress=100 if task_status == TaskStatus.DONE else 40,
                            created_by_id=batch.guide_id,
                        ))
                    db.add(StoryComment(
                        story_id=story.id,
                        author_id=batch.guide_id,
                        author_name=actor_name,
                        body=COMMENTS[(s_index + b_index) % len(COMMENTS)],
                        created_at=now - timedelta(days=4, hours=s_index),
                    ))
                    db.add(StoryEvent(
                        story_id=story.id,
                        actor_id=batch.guide_id, actor_name=actor_name,
                        kind=StoryEventKind.COMMENTED, summary="Comment added",
                        occurred_at=now - timedelta(days=4, hours=s_index),
                    ))

            moved_batches += 1

        await db.commit()
        print(f"Backlog seeded for {moved_batches} of {len(batches)} batches: "
              f"{len(SPRINTS)} sprints each and {assigned_stories} stories assigned. "
              f"{len(batches) - moved_batches} left in AI planning.")


async def main() -> None:
    print("Seeding user story backlogs...")
    await init_db()
    await seed(random.Random(20260831))


if __name__ == "__main__":
    asyncio.run(main())
