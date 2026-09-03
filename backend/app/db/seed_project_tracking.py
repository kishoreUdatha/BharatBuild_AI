"""
Fill the project tracker with a cohort that behaves like a real one.

The screen is only worth looking at when the numbers disagree with each other -
most batches fine, a few slipping, one or two genuinely stuck. A seed where
every project is 60% done and nothing is blocked shows a working screen and
tells you nothing about whether it works.

Deterministic: the same seed produces the same cohort, so a screenshot taken
today matches one taken next week.
"""
import asyncio
import random
from datetime import date, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
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
from app.services.project_tracker import STAGE_ORDER, STANDARD_DELIVERABLES

ACADEMIC_YEAR = "2026-27"
SEED = 20260823

TASK_TITLES = [
    "Optimize model training", "Complete weather API", "Add unit tests",
    "Complete API documentation", "Wire up the dashboard", "Clean the dataset",
    "Write the test plan", "Prepare the demo script", "Fix the login redirect",
    "Draft chapter 3", "Set up CI", "Review peer feedback",
]

BLOCKERS = [
    "Weather API key pending from faculty",
    "Waiting on lab GPU allocation",
    "Dataset licence not yet approved",
    "Hardware kit not issued",
]


async def seed(rng: random.Random) -> None:
    async with AsyncSessionLocal() as db:
        batches = (await db.execute(
            select(ProjectBatch)
            .options(selectinload(ProjectBatch.members),
                     selectinload(ProjectBatch.stage_progress))
            .where(ProjectBatch.academic_year == ACADEMIC_YEAR)
            .where(ProjectBatch.is_active.is_(True))
            .order_by(ProjectBatch.batch_code)
        )).scalars().unique().all()
        if not batches:
            print(f"No batches for {ACADEMIC_YEAR}; run seed_faculty first.")
            return

        ids = [b.id for b in batches]
        for model in (ProjectTask, ProjectDeliverable, BatchIntegration):
            await db.execute(delete(model).where(model.batch_id.in_(ids)))
        await db.flush()

        today = local_today()
        tasks = deliverables = integrations = milestones = 0

        for index, batch in enumerate(batches):
            start = batch.start_date or (today - timedelta(days=120))
            target = batch.target_completion or (today + timedelta(days=90))
            span = max(1, (target - start).days)

            # --- milestones: planned dates, and a realistic staircase -------
            #
            # The faculty seed leaves every stage part-done - topic approval at
            # 94%, base paper at 96% - which reads oddly on a timeline. Real
            # stages are close to binary: the topic was approved or it was not.
            # Everything before the current stage is therefore finished and
            # carries a real completion date, the current one is part-done, and
            # the rest have not started.
            overall_now = batch.overall_progress or 0
            reached = min(len(STAGE_ORDER) - 1,
                          int(overall_now / 100 * len(STAGE_ORDER)))
            rows = {r.stage: r for r in (batch.stage_progress or [])}
            for position, stage in enumerate(STAGE_ORDER):
                row = rows.get(stage)
                if row is None:
                    row = BatchStageProgress(batch_id=batch.id, stage=stage, percent=0.0)
                    db.add(row)
                    rows[stage] = row
                planned = start + timedelta(
                    days=round(span * (position + 1) / (len(STAGE_ORDER) + 1)))
                row.planned_date = planned

                if position < reached:
                    row.percent = 100.0
                    # Landed a few days either side of plan, so "actual" is
                    # worth a column rather than echoing "planned".
                    slip = rng.randint(-3, 6)
                    row.completed_at = datetime.combine(
                        planned + timedelta(days=slip), datetime.min.time())
                elif position == reached:
                    row.percent = float(max(5, min(95, round(
                        (overall_now / 100 * len(STAGE_ORDER) - reached) * 100))))
                    row.completed_at = None
                else:
                    row.percent = 0.0
                    row.completed_at = None
                milestones += 1

            # --- the standard artefacts, progressed in step with the project
            overall = batch.overall_progress or 0
            for position, name in enumerate(STANDARD_DELIVERABLES):
                # Earlier deliverables run ahead of later ones, the way real
                # work does - the report is never written before the code.
                lead = 1.0 - (position / (len(STANDARD_DELIVERABLES) * 1.4))
                progress = max(0, min(100, round(overall * lead + rng.uniform(-8, 8))))
                if progress >= 100:
                    state = DeliverableStatus.VERIFIED
                elif progress >= 60:
                    state = DeliverableStatus.AVAILABLE
                else:
                    state = DeliverableStatus.PENDING
                db.add(ProjectDeliverable(
                    batch_id=batch.id, name=name, progress=progress,
                    status=state, position=position,
                    evidence_url=("https://example.invalid/demo"
                                  if name == "Demo URL" and progress > 50 else None)))
                deliverables += 1

            # --- tasks ------------------------------------------------------
            count = rng.randint(4, 8)
            chosen = rng.sample(TASK_TITLES, count)
            members = [m for m in (batch.members or []) if m.is_active]
            for title in chosen:
                due = today + timedelta(days=rng.randint(-9, 21))
                roll = rng.random()
                if roll < 0.45:
                    status = TaskStatus.DONE
                elif roll < 0.70:
                    status = TaskStatus.IN_PROGRESS
                elif roll < 0.80 and index % 6 == 0:
                    status = TaskStatus.BLOCKED
                else:
                    status = TaskStatus.OPEN
                db.add(ProjectTask(
                    batch_id=batch.id,
                    title=title,
                    assignee_id=(rng.choice(members).student_id if members else None),
                    priority=rng.choices(
                        [TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW],
                        weights=[25, 50, 25])[0],
                    status=status,
                    due_date=due,
                    completed_at=(datetime.utcnow() if status == TaskStatus.DONE else None),
                    blocked_reason=(rng.choice(BLOCKERS)
                                    if status == TaskStatus.BLOCKED else None),
                ))
                tasks += 1

            # --- integrations ----------------------------------------------
            # Roughly one batch in five has never connected a repository, which
            # is what makes the "repositories not connected" alert mean anything.
            if index % 5 != 4:
                db.add(BatchIntegration(
                    batch_id=batch.id, kind=IntegrationKind.REPOSITORY,
                    state=IntegrationState.CONNECTED,
                    detail=f"Last commit {rng.randint(1, 40)}h ago"))
                db.add(BatchIntegration(
                    batch_id=batch.id, kind=IntegrationKind.BUILD,
                    state=(IntegrationState.PASSED if rng.random() > 0.2
                           else IntegrationState.FAILED),
                    detail="CI"))
                db.add(BatchIntegration(
                    batch_id=batch.id, kind=IntegrationKind.DEPLOYMENT,
                    state=(IntegrationState.LIVE if overall > 55
                           else IntegrationState.NOT_CONNECTED),
                    detail="Staging" if overall > 55 else None))
                integrations += 3

        await db.commit()
        print(f"  milestones dated : {milestones}")
        print(f"  deliverables     : {deliverables}")
        print(f"  tasks            : {tasks}")
        print(f"  integrations     : {integrations}")
        print(f"  across           : {len(batches)} batches")


async def main() -> None:
    await seed(random.Random(SEED))


if __name__ == "__main__":
    asyncio.run(main())
