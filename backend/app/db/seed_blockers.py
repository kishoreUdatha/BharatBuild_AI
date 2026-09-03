"""
Give the Tasks & Blockers screen a cohort with a real blocker history.

The panels on that screen are about time and cause: how long blockers sit, how
often each category recurs, who ends up owning them. A seed with five open
blockers and no resolved ones shows an empty SLA chart and a flat analysis bar,
which proves nothing about either.

So this creates a *history* - mostly resolved, at a spread of ages, across all
five categories - and leaves a smaller set open for the queue to work on.

Deterministic: the same seed produces the same history.
"""
import asyncio
import random
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.core.institution_time import local_today
from app.models.faculty import ProjectBatch, ProjectStage
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
from app.models.user import User, UserRole

ACADEMIC_YEAR = "2026-27"
SEED = 20260824

# Each blocker is a category, a plausible title, and the cause behind it -
# the cause is what makes the analysis panel worth reading.
TEMPLATES = [
    (BlockerCategory.TECHNICAL, "Integrate Weather API",
     "College weather API key not provisioned",
     "Forecast endpoint, integration testing and Review 3 evidence"),
    (BlockerCategory.TECHNICAL, "Deploy to staging",
     "Staging credentials expired and not reissued",
     "Demo URL and the deployment milestone"),
    (BlockerCategory.DATA, "Train classification model",
     "Dataset unavailable - licence not yet approved",
     "Model prototype and the test report"),
    (BlockerCategory.DATA, "Clean the sensor dataset",
     "Raw exports missing two months of readings",
     "Requirements sign-off"),
    (BlockerCategory.APPROVAL, "Requirements sign-off",
     "Base paper still awaiting verification",
     "Design and everything after it"),
    (BlockerCategory.APPROVAL, "Review feedback outstanding",
     "Review 2 outcome never recorded",
     "The team cannot act on comments they have not received"),
    (BlockerCategory.TEAM, "Member replacement",
     "One member inactive since the second week",
     "Two workstreams with no owner"),
    (BlockerCategory.DOCUMENTATION, "Chapter 3 draft",
     "Report template not circulated",
     "Documentation milestone"),
]

STAGES = [
    ProjectStage.REQUIREMENTS, ProjectStage.SYSTEM_DESIGN,
    ProjectStage.DEVELOPMENT, ProjectStage.TESTING, ProjectStage.DOCUMENTATION,
]

COMMENTS = [
    "Chased the lab today, no response yet.",
    "Team has a workaround for the demo but not for the report.",
    "Raised with the department office this morning.",
    "Partially unblocked - one of the two files arrived.",
]


async def seed(rng: random.Random) -> None:
    async with AsyncSessionLocal() as db:
        batches = (await db.execute(
            select(ProjectBatch)
            .options(selectinload(ProjectBatch.members))
            .where(ProjectBatch.academic_year == ACADEMIC_YEAR)
            .where(ProjectBatch.is_active.is_(True))
            .order_by(ProjectBatch.batch_code)
        )).scalars().unique().all()
        if not batches:
            print(f"No batches for {ACADEMIC_YEAR}; run seed_faculty first.")
            return

        staff = (await db.execute(
            select(User).where(User.role == UserRole.FACULTY).order_by(User.email)
        )).scalars().all()
        if not staff:
            print("No faculty accounts; run seed_faculty first.")
            return

        ids = [b.id for b in batches]
        await db.execute(delete(ProjectBlocker).where(ProjectBlocker.batch_id.in_(ids)))

        tasks = (await db.execute(
            select(ProjectTask).where(ProjectTask.batch_id.in_(ids))
        )).scalars().all()
        by_batch = {}
        for t in tasks:
            by_batch.setdefault(str(t.batch_id), []).append(t)

        task_ids = [t.id for t in tasks]
        if task_ids:
            await db.execute(delete(TaskComment).where(TaskComment.task_id.in_(task_ids)))
            await db.execute(delete(TaskDependency)
                             .where(TaskDependency.task_id.in_(task_ids)))
        await db.flush()

        now = datetime.utcnow()
        today = local_today()
        opened = resolved = comments = deps = staged = 0

        for index, batch in enumerate(batches):
            batch_tasks = by_batch.get(str(batch.id), [])

            # --- stage and progress on the existing tasks -------------------
            for position, t in enumerate(batch_tasks):
                t.stage = STAGES[position % len(STAGES)].name
                if t.status == TaskStatus.DONE:
                    t.progress = 100
                elif t.status == TaskStatus.IN_PROGRESS:
                    t.progress = rng.choice([25, 40, 55, 70, 85])
                else:
                    t.progress = 0
                staged += 1

            # --- dependencies: later work waits on earlier work -------------
            for a, b in zip(batch_tasks, batch_tasks[1:]):
                if rng.random() < 0.45:
                    db.add(TaskDependency(task_id=b.id, depends_on_id=a.id))
                    deps += 1

            # --- comments ---------------------------------------------------
            for t in batch_tasks:
                for _ in range(rng.choice([0, 0, 1, 1, 2, 3])):
                    db.add(TaskComment(
                        task_id=t.id,
                        author_id=rng.choice(staff).id,
                        body=rng.choice(COMMENTS),
                        created_at=now - timedelta(days=rng.randint(0, 20)),
                    ))
                    comments += 1

            # --- blocker history --------------------------------------------
            # Most are behind us. That is what fills the SLA chart and makes an
            # average resolution time mean anything.
            for _ in range(rng.randint(1, 3)):
                category, title, cause, impact = rng.choice(TEMPLATES)
                age = rng.randint(1, 24)
                reported = now - timedelta(days=age, hours=rng.randint(0, 20))
                owner = rng.choice(staff)

                # Only unfinished work can be blocked. Blocking a completed
                # task left cards reading "blocked" at 100%, which is not a
                # state any project can actually be in.
                open_tasks = [t for t in batch_tasks if t.status != TaskStatus.DONE]
                blocked_task = None
                if open_tasks and rng.random() < 0.75:
                    blocked_task = rng.choice(open_tasks)

                settle = rng.random()
                if settle < 0.72:
                    took = min(age, rng.choices([0, 2, 5, 11],
                                                weights=[45, 30, 15, 10])[0])
                    status = BlockerStatus.RESOLVED
                    resolved_at = reported + timedelta(days=took,
                                                       hours=rng.randint(1, 20))
                    note = "Cleared by the department office."
                    resolved += 1
                else:
                    status = (BlockerStatus.ESCALATED if age > 5 and rng.random() < 0.4
                              else BlockerStatus.OPEN)
                    resolved_at, note = None, None
                    opened += 1
                    if blocked_task is not None:
                        blocked_task.status = TaskStatus.BLOCKED
                        blocked_task.blocked_reason = title

                db.add(ProjectBlocker(
                    batch_id=batch.id,
                    task_id=blocked_task.id if blocked_task is not None else None,
                    title=title,
                    category=category,
                    severity=(BlockerSeverity.CRITICAL if status == BlockerStatus.ESCALATED
                              else rng.choices(
                                  [BlockerSeverity.CRITICAL, BlockerSeverity.HIGH,
                                   BlockerSeverity.MEDIUM, BlockerSeverity.LOW],
                                  weights=[15, 30, 40, 15])[0]),
                    status=status,
                    root_cause=cause,
                    impact=impact,
                    reported_by_id=(rng.choice(batch.members).student_id
                                    if batch.members else None),
                    reported_at=reported,
                    resolution_owner_id=owner.id if rng.random() < 0.8 else None,
                    target_resolution=(today + timedelta(days=rng.randint(1, 10))
                                       if status != BlockerStatus.RESOLVED else None),
                    resolved_at=resolved_at,
                    resolution_note=note,
                ))

        await db.commit()
        print(f"  blockers open     : {opened}")
        print(f"  blockers resolved : {resolved}")
        print(f"  task comments     : {comments}")
        print(f"  dependencies      : {deps}")
        print(f"  tasks staged      : {staged}")
        print(f"  across            : {len(batches)} batches")


async def main() -> None:
    await seed(random.Random(SEED))


if __name__ == "__main__":
    asyncio.run(main())
