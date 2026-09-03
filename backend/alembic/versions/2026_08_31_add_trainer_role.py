"""Add TRAINER to the userrole enum.

The trainer portal previously ran on the faculty role - a trainer was a
faculty account acting in a different capacity. Trainer is now its own role,
so the Postgres enum backing `users.role` needs the new label.

Revision ID: add_trainer_role
Revises: add_milestones
Create Date: 2026-08-31
"""
from alembic import op

revision = 'add_trainer_role'
down_revision = 'add_milestones'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLAlchemy stores the enum *name*, so the label is upper case to match
    # STUDENT / FACULTY / ADMIN already in the type. IF NOT EXISTS keeps this
    # safe to re-run. Postgres 12+ allows ADD VALUE inside a transaction as
    # long as the new value is not used in that same transaction.
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'TRAINER'")


def downgrade() -> None:
    # Postgres cannot remove a value from an enum type; undoing this means
    # recreating the type and rewriting every dependent column, which is not
    # worth doing automatically. Accounts on the trainer role would have to be
    # moved to faculty first.
    pass
