"""A platform operations manager.

Between the operator and a college: they run every college's day to day and
the trainers working across them, without reaching the business itself -
revenue, plans and API keys stay behind `is_superuser`.

Revision ID: manager_role
Revises: assign_whole_college
Create Date: 2026-09-15
"""
import sqlalchemy as sa
from alembic import op

revision = 'manager_role'
down_revision = 'assign_whole_college'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Outside a transaction: Postgres will not add an enum value inside one.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'MANAGER'")


def downgrade() -> None:
    # Postgres cannot drop an enum value. Accounts holding it would have to be
    # moved to another role first, which is not something a migration should
    # decide.
    pass
