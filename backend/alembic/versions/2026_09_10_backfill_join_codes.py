"""Give existing batches a join code.

Batches created by the faculty seeder were written without one, so every
invite link resolved to "?code=" and joining by code could not work at all -
the resolver matches on join_code alone.

The code is rebuilt from batch_code so it lands on the same value the batch
would have been given had it been created through the normal path.

Revision ID: backfill_join_codes
Revises: payment_gateway_id
Create Date: 2026-09-10
"""
import re

import sqlalchemy as sa
from alembic import op

revision = 'backfill_join_codes'
down_revision = 'payment_gateway_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, batch_code, department, section, year "
        "FROM project_batches WHERE join_code IS NULL"
    )).fetchall()

    taken = {c for (c,) in bind.execute(sa.text(
        "SELECT join_code FROM project_batches WHERE join_code IS NOT NULL"
    )).fetchall()}

    for row in rows:
        seq = re.search(r"(\d+)\s*$", row.batch_code or "")
        if seq is None:
            # Nothing to derive from; leave it null rather than invent a code
            # that collides with a real one later.
            continue
        digit = re.match(r"\s*(\d+)", row.year or "")
        code = (f"BB-{row.department or 'GEN'}-"
                f"{digit.group(1) if digit else '4'}{row.section or 'X'}-"
                f"{int(seq.group(1)):03d}")
        # join_code is unique; a clash means two batches share a cohort and
        # sequence, so the batch code goes on the end to separate them.
        if code in taken:
            code = f"{code}-{row.batch_code}"
        taken.add(code)
        bind.execute(
            sa.text("UPDATE project_batches SET join_code = :code WHERE id = :id"),
            {"code": code, "id": row.id})


def downgrade() -> None:
    # Nothing to undo: a batch without a join code cannot be joined, and
    # blanking them again would break every invite link already shared.
    pass
