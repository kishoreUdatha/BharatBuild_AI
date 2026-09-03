"""
Give the Milestones screen a cohort with a real approval trail.

The panels on that screen are about slippage and sign-off: which dates have
moved, what is waiting on a reviewer, what evidence is missing. A seed where
every milestone is planned and untouched shows an empty approval queue and a
flat health donut, which demonstrates nothing.

So this creates milestones at every stage of the trail - some approved, some
sent back, some waiting, some slipping - with checklists, evidence in all four
states, and dependencies between them.

Deterministic: the same seed produces the same trail.
"""
import asyncio
import random
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.core.institution_time import local_today
from app.models.faculty import ProjectBatch, ProjectStage
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
from app.models.user import User, UserRole

ACADEMIC_YEAR = "2026-27"
SEED = 20260824

# Named the way teams name them, not the way the eight fixed stages are.
PLAN = [
    ("Dataset Preparation", ProjectStage.REQUIREMENTS,
     ["Sources identified", "Licence confirmed", "Cleaning script written"],
     ["Dataset manifest", "Licence email"]),
    ("Model Prototype", ProjectStage.SYSTEM_DESIGN,
     ["Baseline chosen", "First run complete", "Metrics recorded"],
     ["Notebook", "Metrics sheet"]),
    ("API Integration", ProjectStage.DEVELOPMENT,
     ["REST endpoints complete", "Authentication complete",
      "Weather API pending", "Integration tests in progress"],
     ["API Specification", "Postman Collection", "Demo URL", "Test Results"]),
    ("Model Training", ProjectStage.DEVELOPMENT,
     ["Training set frozen", "Hyperparameters tuned"],
     ["Training log"]),
    ("Test Completion", ProjectStage.TESTING,
     ["Unit tests pass", "Integration tests pass", "Coverage above 60%"],
     ["Test report"]),
    ("Documentation", ProjectStage.DOCUMENTATION,
     ["Chapters 1-3 drafted", "Diagrams included"],
     ["Report draft"]),
    ("Review 3", ProjectStage.FINAL_REVIEW,
     ["Slides ready", "Demo rehearsed"],
     ["Presentation", "Demo recording"]),
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

        ids = [b.id for b in batches]
        old = (await db.execute(
            select(ProjectMilestone.id).where(ProjectMilestone.batch_id.in_(ids))
        )).scalars().all()
        if old:
            for model in (MilestoneDependency, MilestoneEvidence, MilestoneChecklistItem):
                col = (model.milestone_id if model is not MilestoneDependency
                       else model.milestone_id)
                await db.execute(delete(model).where(col.in_(old)))
            await db.execute(delete(MilestoneDependency)
                             .where(MilestoneDependency.depends_on_id.in_(old)))
            await db.execute(delete(ProjectMilestone)
                             .where(ProjectMilestone.id.in_(old)))
        await db.flush()

        today = local_today()
        made = checks = evidence = deps = 0
        approved = waiting = sent_back = slipping = 0

        for index, batch in enumerate(batches):
            start = batch.start_date or (today - timedelta(days=120))
            target = batch.target_completion or (today + timedelta(days=90))
            span = max(1, (target - start).days)
            members = [m for m in (batch.members or []) if m.is_active]

            # How far this batch has got. Earlier milestones are settled,
            # the current one is live, later ones have not begun.
            reached = min(len(PLAN) - 1,
                          int((batch.overall_progress or 0) / 100 * len(PLAN)))

            created = []
            for position, (name, stage, checklist, artefacts) in enumerate(PLAN):
                # Settled milestones sit back where they happened, spread over
                # the months already gone. The ones still ahead are planned at
                # a working cadence - a few days apart, not a month - because
                # that is how teams actually plan the next fortnight, and a
                # tracker showing one bar per project per month is unreadable.
                if position < reached:
                    planned = start + timedelta(
                        days=round(span * (position + 1) / (len(PLAN) + 1)))
                else:
                    ahead = position - reached
                    planned = today + timedelta(days=ahead * rng.randint(4, 6) - 1)

                if position < reached:
                    progress = 100
                    # Most settled milestones are signed off; a few are still
                    # sitting in the queue, which is what fills the panel.
                    if rng.random() < 0.78:
                        approval = ApprovalState.APPROVED
                        approved += 1
                    else:
                        approval = ApprovalState.REVIEW_READY
                        waiting += 1
                    forecast = planned
                elif position == reached:
                    progress = rng.choice([20, 35, 50, 65, 80])
                    if rng.random() < 0.25:
                        approval = ApprovalState.CHANGES_REQUESTED
                        sent_back += 1
                    elif rng.random() < 0.4:
                        approval = ApprovalState.PENDING
                    else:
                        approval = ApprovalState.NOT_READY
                    # Some current milestones have already slipped: the team's
                    # own forecast is later than the plan.
                    slip = rng.choices([0, 3, 8], weights=[55, 30, 15])[0]
                    forecast = planned + timedelta(days=slip)
                    if slip:
                        slipping += 1
                else:
                    progress = 0
                    approval = ApprovalState.NOT_READY
                    forecast = planned

                # When it actually landed: a few days either side of plan.
                landed = datetime.combine(
                    planned + timedelta(days=rng.randint(-3, 5)),
                    datetime.min.time())

                m = ProjectMilestone(
                    batch_id=batch.id,
                    name=name,
                    stage=stage.name,
                    priority=rng.choices(
                        [MilestonePriority.CRITICAL, MilestonePriority.HIGH,
                         MilestonePriority.MEDIUM, MilestonePriority.LOW],
                        weights=[12, 33, 40, 15])[0],
                    status=(MilestoneStatus.COMPLETE if progress >= 100
                            else MilestoneStatus.NOT_STARTED),
                    approval=approval,
                    owner_id=(rng.choice(members).student_id if members else None),
                    reviewer_id=batch.guide_id or (staff[0].id if staff else None),
                    planned_start=planned - timedelta(days=rng.randint(4, 10)),
                    planned_date=planned,
                    forecast_date=forecast,
                    progress=progress,
                    position=position,
                    # Stamped near when the milestone was actually due, not
                    # "now". Everything completing today made the fortnightly
                    # delta read as though the entire cohort finished this week.
                    completed_at=(landed if progress >= 100 else None),
                    approved_at=((landed + timedelta(days=rng.randint(0, 4)))
                                 if approval == ApprovalState.APPROVED else None),
                    approved_by_id=(batch.guide_id
                                    if approval == ApprovalState.APPROVED else None),
                    review_note=("Tighten the evaluation section."
                                 if approval == ApprovalState.CHANGES_REQUESTED else None),
                    # Planned when the project started, not when this script
                    # ran. Stamping every row with "now" made the whole cohort
                    # look as though it had been created in the last fortnight.
                    created_at=datetime.combine(
                        start + timedelta(days=rng.randint(0, 10)),
                        datetime.min.time()),
                )
                db.add(m)
                await db.flush()
                created.append(m)
                made += 1

                done_count = (len(checklist) if progress >= 100
                              else round(len(checklist) * progress / 100))
                for cpos, label in enumerate(checklist):
                    db.add(MilestoneChecklistItem(
                        milestone_id=m.id, label=label,
                        is_done=1 if cpos < done_count else 0, position=cpos))
                    checks += 1

                for epos, label in enumerate(artefacts):
                    if progress >= 100:
                        state = (EvidenceStatus.VERIFIED
                                 if approval == ApprovalState.APPROVED
                                 else EvidenceStatus.UPLOADED)
                    elif progress > 40 and epos == 0:
                        state = rng.choice([EvidenceStatus.UPLOADED,
                                            EvidenceStatus.AVAILABLE])
                    else:
                        state = EvidenceStatus.PENDING
                    db.add(MilestoneEvidence(
                        milestone_id=m.id, label=label, status=state, position=epos,
                        submitted_at=(datetime.utcnow()
                                      if state != EvidenceStatus.PENDING else None),
                        verified_at=(datetime.utcnow()
                                     if state == EvidenceStatus.VERIFIED else None)))
                    evidence += 1

            # Each milestone waits on the one before it - that is what makes
            # the dependency alerts point at something real.
            for a, b in zip(created, created[1:]):
                db.add(MilestoneDependency(milestone_id=b.id, depends_on_id=a.id))
                deps += 1

        await db.commit()
        print(f"  milestones        : {made}")
        print(f"    approved        : {approved}")
        print(f"    awaiting review : {waiting}")
        print(f"    changes asked   : {sent_back}")
        print(f"    slipping        : {slipping}")
        print(f"  checklist items   : {checks}")
        print(f"  evidence rows     : {evidence}")
        print(f"  dependencies      : {deps}")
        print(f"  across            : {len(batches)} batches")


async def main() -> None:
    await seed(random.Random(SEED))


if __name__ == "__main__":
    asyncio.run(main())
