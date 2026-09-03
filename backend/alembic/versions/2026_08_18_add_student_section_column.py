"""add section column to users table

Revision ID: add_student_section
Revises: add_subscription_reminder
Create Date: 2026-08-18

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_student_section'
down_revision = 'add_subscription_reminder'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Student section (e.g. "A", "B", "C") captured during registration.
    # IF NOT EXISTS because Base.metadata.create_all may have already added it
    # on databases that were bootstrapped from the models rather than migrations.
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS section VARCHAR(10);
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE users
        DROP COLUMN IF EXISTS section;
    """)
