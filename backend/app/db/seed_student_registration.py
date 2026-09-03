"""
Student Registration Seeder - join codes, seat state and payment shares.

    python -m app.db.seed_student_registration

Idempotent: it recomputes join codes and fees for every batch in the target
year and rebuilds that year's registration payments.

Existing memberships stay joined and confirmed - they are real rows the
faculty portal already reports on. Only a small, deterministic slice is left
part-registered so the student screen has something honest to show: every
fourth batch keeps its last seat un-accepted.

Payments are never seeded. A share becomes a row when a student opens one, and
only the gateway marks it paid - an invented receipt would tell a student their
money had arrived when none ever did.
"""

import asyncio
import random
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal, init_db
from app.models.faculty import (
    MemberInviteStatus,
    ProjectBatch,
    ProjectBatchMember,
    RegistrationPayment,
)

ACADEMIC_YEAR = "2026-27"
PROJECT_FEE = 15000
TEAM_SIZE = 4


def join_code(batch: ProjectBatch, index: int) -> str:
    """
    Student-facing code, e.g. BB-CSE-4A-014.

    Derived from the batch's own department/year/section so a coordinator
    reading it out can tell at a glance which cohort it belongs to.
    """
    year_digit = (batch.year or "4th Year")[0]
    section = batch.section or "X"
    return f"BB-{batch.department}-{year_digit}{section}-{index:03d}"


async def seed(rng: random.Random) -> None:
    async with AsyncSessionLocal() as db:
        batches = (await db.execute(
            select(ProjectBatch)
            .where(ProjectBatch.academic_year == ACADEMIC_YEAR)
            .options(selectinload(ProjectBatch.members))
            .order_by(ProjectBatch.batch_code)
        )).scalars().all()

        if not batches:
            print(f"No batches for {ACADEMIC_YEAR}; run seed_faculty first.")
            return

        await db.execute(
            delete(RegistrationPayment).where(
                RegistrationPayment.batch_id.in_([b.id for b in batches])
            )
        )
        await db.flush()

        now = datetime.utcnow()
        counters: dict[tuple, int] = {}
        pending_seats = 0

        for position, batch in enumerate(batches):
            key = (batch.department, batch.year, batch.section)
            counters[key] = counters.get(key, 0) + 1
            batch.join_code = join_code(batch, counters[key])
            batch.team_size = TEAM_SIZE
            batch.project_fee = PROJECT_FEE

            members = sorted(
                [m for m in batch.members if m.is_active],
                key=lambda m: (not m.is_lead, str(m.student_id)),
            )
            share = PROJECT_FEE // max(1, TEAM_SIZE)

            # Every 4th batch keeps its last seat invited but not accepted.
            seat_open = position % 4 == 3 and len(members) > 1

            for i, member in enumerate(members):
                last = i == len(members) - 1
                if seat_open and last:
                    member.invite_status = MemberInviteStatus.INVITED
                    member.seat_confirmed = False
                    member.invited_at = now - timedelta(days=2)
                    pending_seats += 1
                    # An un-accepted seat has nothing to pay yet.
                    continue

                member.invite_status = MemberInviteStatus.JOINED
                member.seat_confirmed = True
                member.invited_at = member.invited_at or (now - timedelta(days=6))

                # No payment row is seeded. A share becomes a row when the
                # student opens one, and it is only ever marked paid by the
                # gateway - so nothing here can claim money that never arrived.

        await db.commit()
        print(f"Seeded {len(batches)} batches: {pending_seats} seats awaiting "
              f"acceptance. No payments seeded - those come from real ones.")


async def main() -> None:
    print("Seeding student registration state...")
    await init_db()
    await seed(random.Random(20260820))


if __name__ == "__main__":
    asyncio.run(main())
