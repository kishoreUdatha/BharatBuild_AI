"""
AI Planning Seeder - drafted epics and user stories per batch.

    python -m app.db.seed_ai_planning

Idempotent: rebuilds the planning rows for the target academic year.

Stories are derived from each batch's own objectives, methodology steps and
technology stack, so the AI Story Approval screen shows work that matches the
project it belongs to rather than generic filler. A deterministic slice is
left needing review, because a screen whose whole purpose is reviewing drafts
is useless with nothing outstanding.
"""

import asyncio
import random
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal, init_db
from app.models.ai_planning import (
    AiPlanningRun,
    CriterionKind,
    ProjectEpic,
    ProjectUserStory,
    StoryCriterion,
    StoryPriority,
    StoryReviewStatus,
)
from app.models.batch_detail import ProjectMethodologyStep, ProjectObjective, ProjectTechnology
from app.models.faculty import ProjectBatch

ACADEMIC_YEAR = "2026-27"
MODEL_LABEL = "claude-sonnet-4.5"

EPICS = [
    ("Data Foundation", "Collecting, validating and preparing the project's data."),
    ("Modelling", "Building, comparing and tuning the core models."),
    ("Delivery", "Exposing the result through an interface users can reach."),
    ("Evaluation", "Measuring the system and evidencing the outcome."),
]

# Story shapes per epic, filled from the batch's own project details.
TEMPLATES = {
    0: [
        ("Prepare and validate {domain} dataset", "data engineer",
         "prepare a validated dataset", "the models train on trustworthy inputs"),
        ("Integrate {tech} data source", "data engineer",
         "integrate a reliable {tech} source", "the pipeline can use live data"),
    ],
    1: [
        ("Build baseline {domain} model", "ML engineer",
         "build a baseline model", "later work has something to beat"),
        ("Compare ensemble models", "ML engineer",
         "compare candidate models", "we pick the strongest approach on evidence"),
    ],
    2: [
        ("Create {domain} dashboard", "front-end developer",
         "expose results in a dashboard", "a reviewer can see the output without running code"),
        ("Expose prediction API", "back-end developer",
         "serve predictions over an API", "other systems can consume the result"),
    ],
    3: [
        ("Evaluate model performance", "ML engineer",
         "measure the model against agreed metrics", "the claim in the report is backed by numbers"),
        ("Document results and limitations", "student",
         "write up results and limitations", "the examiner can judge the work honestly"),
    ],
}

ACCEPTANCE = [
    "{title} returns results for the configured range",
    "Inputs are validated before processing",
    "Errors and retries are handled",
    "Responses are cached to reduce repeat cost",
    "Usage and rate-limit status are logged",
    "Rate-limit and fallback behaviour is defined",
]

DEFINITION_OF_DONE = [
    "Code is committed to repository",
    "Unit tests are written and passing",
    "Integration test with API is successful",
    "Error handling is implemented",
    "Documentation is updated in the wiki",
]

DEPENDENCIES = [
    None, "Faculty API key required", "Dataset access approval pending",
    None, "Depends on baseline model", None,
]


async def seed(rng: random.Random) -> None:
    async with AsyncSessionLocal() as db:
        batches = (await db.execute(
            select(ProjectBatch)
            .where(ProjectBatch.academic_year == ACADEMIC_YEAR)
            .where(ProjectBatch.is_active.is_(True))
            .options(
                selectinload(ProjectBatch.objectives),
                selectinload(ProjectBatch.technologies),
                selectinload(ProjectBatch.methodology),
                selectinload(ProjectBatch.guide),
            )
            .order_by(ProjectBatch.batch_code)
        )).scalars().all()

        if not batches:
            print(f"No batches for {ACADEMIC_YEAR}; run seed_faculty first.")
            return

        ids = [b.id for b in batches]
        await db.execute(delete(AiPlanningRun).where(AiPlanningRun.batch_id.in_(ids)))
        await db.execute(delete(ProjectUserStory).where(ProjectUserStory.batch_id.in_(ids)))
        await db.execute(delete(ProjectEpic).where(ProjectEpic.batch_id.in_(ids)))
        await db.flush()

        now = datetime.utcnow()
        total_stories = 0

        for b_index, batch in enumerate(batches):
            domain_word = (batch.domain or "project").split("/")[0].strip().lower()
            techs = [t.name for t in batch.technologies] or ["REST"]

            run = AiPlanningRun(
                batch_id=batch.id,
                model_label=MODEL_LABEL,
                source_summary=(
                    f"{len(batch.objectives)} objectives, {len(batch.methodology)} methodology "
                    f"steps and {len(techs)} technologies from the approved registration."
                ),
                generated_at=now - timedelta(days=1, hours=b_index % 6),
                generated_by_id=batch.guide_id,
                is_current=True,
            )
            db.add(run)
            await db.flush()

            confidences = []
            story_seq = 101

            for e_index, (epic_title, epic_desc) in enumerate(EPICS):
                epic = ProjectEpic(
                    batch_id=batch.id,
                    key=f"EP-{e_index + 1:02d}",
                    title=epic_title,
                    description=epic_desc,
                    position=e_index,
                )
                db.add(epic)
                await db.flush()

                for t_index, (title_t, role, want, why) in enumerate(TEMPLATES[e_index]):
                    title = title_t.format(domain=domain_word, tech=techs[t_index % len(techs)])
                    ordinal = e_index * 2 + t_index

                    # Deterministic, but varied across batches so the portal is
                    # not a wall of identical rows.
                    needs_review = (ordinal + b_index) % 3 == 1
                    confidence = 84 + ((ordinal * 7 + b_index * 3) % 14)
                    points = [3, 5, 8, 8, 5, 5, 3, 8][ordinal]
                    priority = (StoryPriority.HIGH if ordinal < 3
                                else StoryPriority.MEDIUM if ordinal < 6
                                else StoryPriority.LOW)
                    confidences.append(confidence)

                    story = ProjectUserStory(
                        batch_id=batch.id,
                        epic_id=epic.id,
                        run_id=run.id,
                        key=f"US-{story_seq}",
                        title=title,
                        narrative=(f"As a {role}, I want to {want.format(tech=techs[t_index % len(techs)])} "
                                   f"so that {why}."),
                        dependencies=DEPENDENCIES[ordinal % len(DEPENDENCIES)],
                        story_points=points,
                        priority=priority,
                        ai_confidence=float(confidence),
                        review_status=(StoryReviewStatus.NEEDS_REVIEW if needs_review
                                       else StoryReviewStatus.REVIEWED),
                        reviewed_by_id=None if needs_review else batch.guide_id,
                        reviewed_at=None if needs_review else now - timedelta(hours=ordinal + 2),
                        position=ordinal,
                    )
                    db.add(story)
                    await db.flush()
                    story_seq += 1
                    total_stories += 1

                    # A story that still needs review is exactly one that has an
                    # unmet acceptance criterion - the counts on screen agree
                    # because they are the same rows.
                    unmet_at = 5 if needs_review else None
                    for c_index, text in enumerate(ACCEPTANCE):
                        db.add(StoryCriterion(
                            story_id=story.id,
                            kind=CriterionKind.ACCEPTANCE,
                            text=text.format(title=title.split()[0]),
                            met=c_index != unmet_at,
                            position=c_index,
                        ))
                    for c_index, text in enumerate(DEFINITION_OF_DONE):
                        db.add(StoryCriterion(
                            story_id=story.id,
                            kind=CriterionKind.DEFINITION_OF_DONE,
                            text=text,
                            met=True,
                            position=c_index,
                        ))

            run.story_count = story_seq - 101
            run.epic_count = len(EPICS)
            run.quality_percent = int(round(sum(confidences) / len(confidences)))

        await db.commit()
        print(f"Seeded planning for {len(batches)} batches: "
              f"{len(EPICS)} epics and {total_stories // len(batches)} stories each.")


async def main() -> None:
    print("Seeding AI planning drafts...")
    await init_db()
    await seed(random.Random(20260820))


if __name__ == "__main__":
    asyncio.run(main())
