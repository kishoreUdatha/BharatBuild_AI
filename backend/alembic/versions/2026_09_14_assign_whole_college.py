"""Assign a trainer to a college, not to each of its sections.

A trainer takes several branches and several sections at an institution, so
listing them one by one is data entry that goes stale every term - a new
section appears and the trainer silently cannot see it. The college is the
unit: assign that, and everything inside it follows.

`department` and `section` stay on the table and become optional. Null means
the whole college, which is the normal case; a value still narrows, for the
occasional trainer brought in for one branch.

Existing rows are consolidated: one row per trainer per college, replacing the
per-section rows the previous migration derived. Nobody loses reach - they gain
the rest of the college they were already teaching in.

Revision ID: assign_whole_college
Revises: trainer_assignments
Create Date: 2026-09-14
"""
import sqlalchemy as sa
from alembic import op

revision = 'assign_whole_college'
down_revision = 'trainer_assignments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('trainer_assignments', 'department',
                    existing_type=sa.String(100), nullable=True)

    bind = op.get_bind()
    # One row per trainer per college per year, with no branch or section.
    pairs = bind.execute(sa.text("""
        SELECT DISTINCT trainer_id, college_id, academic_year
        FROM trainer_assignments WHERE is_active = true
    """)).fetchall()

    bind.execute(sa.text("DELETE FROM trainer_assignments"))
    for row in pairs:
        bind.execute(sa.text("""
            INSERT INTO trainer_assignments
                (id, trainer_id, college_id, department, section,
                 academic_year, is_active, created_at)
            VALUES (gen_random_uuid(), :trainer, :college, NULL, NULL,
                    :year, true, now())
        """), {"trainer": row.trainer_id, "college": row.college_id,
               "year": row.academic_year})


def downgrade() -> None:
    # A null department cannot be expressed once the column is required again,
    # so those rows would have to be re-derived by hand. Left as a no-op
    # rather than inventing branches nobody assigned.
    pass
