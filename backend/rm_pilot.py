import asyncio
from sqlalchemy import delete, select
from app.core.database import AsyncSessionLocal
from app.models.milestones import (MilestoneChecklistItem, MilestoneDependency,
                                   MilestoneEvidence, ProjectMilestone)

async def main():
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(ProjectMilestone)
                .where(ProjectMilestone.name == "Pilot Deployment"))).scalars().all()
        for r in rows:
            for model in (MilestoneChecklistItem, MilestoneEvidence):
                await db.execute(delete(model).where(model.milestone_id == r.id))
            await db.execute(delete(MilestoneDependency)
                             .where(MilestoneDependency.milestone_id == r.id))
            await db.execute(delete(ProjectMilestone).where(ProjectMilestone.id == r.id))
        await db.commit()
        print("removed test milestones:", len(rows))
asyncio.run(main())
