"""Where a platform trainer may work.

Trainers are BharatBuild's staff, not a college's, and one trainer teaches
several sections across several colleges. `users.college_id` holds one value,
so it cannot express that: today a trainer is pinned to whichever college they
were seeded into and can never see the others.

Their reach moves to explicit per-section assignments. Existing trainers are
backfilled from the sections they already manage, so nobody's access changes
on the day this runs - and their `college_id` is cleared, since a platform
trainer is not a member of a customer's tenant.

Revision ID: trainer_assignments
Revises: college_project_types
Create Date: 2026-09-13
"""
import sqlalchemy as sa
from alembic import op

from app.core.types import GUID

revision = 'trainer_assignments'
down_revision = 'college_project_types'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'trainer_assignments',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('trainer_id', GUID(), nullable=False),
        sa.Column('college_id', GUID(), nullable=False),
        sa.Column('department', sa.String(100), nullable=False),
        sa.Column('section', sa.String(10), nullable=True),
        sa.Column('academic_year', sa.String(20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False,
                  server_default=sa.true()),
        sa.Column('assigned_by_id', GUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['trainer_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['college_id'], ['colleges.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trainer_id', 'college_id', 'department', 'section',
                            'academic_year', name='uq_trainer_assignment'),
    )
    for column in ('trainer_id', 'college_id', 'department', 'section',
                   'academic_year', 'is_active'):
        op.create_index(f'ix_trainer_assignments_{column}',
                        'trainer_assignments', [column])

    bind = op.get_bind()

    # Backfill from what each trainer already reaches, so access on the day
    # after this migration is exactly what it was the day before.
    rows = bind.execute(sa.text("""
        SELECT DISTINCT u.id AS trainer_id, b.college_id, b.department,
                        b.section, b.academic_year
        FROM users u
        JOIN project_batches b
          ON b.guide_id = u.id OR b.reviewer_id = u.id
        WHERE u.role = 'TRAINER' AND b.college_id IS NOT NULL
    """)).fetchall()

    for row in rows:
        bind.execute(sa.text("""
            INSERT INTO trainer_assignments
                (id, trainer_id, college_id, department, section,
                 academic_year, is_active, created_at)
            VALUES (gen_random_uuid(), :trainer, :college, :dept, :section,
                    :year, true, now())
            ON CONFLICT ON CONSTRAINT uq_trainer_assignment DO NOTHING
        """), {"trainer": row.trainer_id, "college": row.college_id,
               "dept": row.department, "section": row.section,
               "year": row.academic_year})

    # A platform trainer is not a member of a customer's tenant. Cleared only
    # for those who now have an assignment to stand on, so nobody is stranded
    # by this migration.
    bind.execute(sa.text("""
        UPDATE users SET college_id = NULL
        WHERE role = 'TRAINER'
          AND id IN (SELECT DISTINCT trainer_id FROM trainer_assignments)
    """))


def downgrade() -> None:
    # Put each trainer back into the first college they were assigned to,
    # otherwise they would be left with neither a tenant nor a table.
    bind = op.get_bind()
    bind.execute(sa.text("""
        UPDATE users u SET college_id = a.college_id
        FROM (SELECT DISTINCT ON (trainer_id) trainer_id, college_id
              FROM trainer_assignments ORDER BY trainer_id, created_at) a
        WHERE u.id = a.trainer_id AND u.college_id IS NULL
    """))
    op.drop_table('trainer_assignments')
