import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal
from app.models.faculty import ProjectBatch
from app.models.project_tracking import ProjectTask
from app.models.user import User

async def main():
    async with AsyncSessionLocal() as db:
        for code in ("CSE-B-003", "CSE-B-001"):
            b = (await db.execute(select(ProjectBatch)
                 .options(selectinload(ProjectBatch.members))
                 .where(ProjectBatch.batch_code == code))).scalars().unique().first()
            ids = [m.student_id for m in b.members]
            names = {str(u.id): u.full_name for u in (await db.execute(
                select(User).where(User.id.in_(ids)))).scalars().all()}
            with_tasks = {str(t.assignee_id) for t in (await db.execute(
                select(ProjectTask).where(ProjectTask.batch_id == b.id))).scalars().all()
                if t.assignee_id}
            print(f"{code}: {len(b.members)} members")
            for m in b.members:
                k = str(m.student_id)
                print(f"   {names.get(k,'?'):18} active={m.is_active} "
                      f"has_tasks={'yes' if k in with_tasks else 'NO'}")

asyncio.run(main())
