"""add coding columns to campus drive tables

Revision ID: campus_drive_002
Revises: campus_drive_001
Create Date: 2026-01-23

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'campus_drive_002'
down_revision = 'campus_drive_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'coding' value to questioncategory enum
    op.execute("""
        ALTER TYPE questioncategory ADD VALUE IF NOT EXISTS 'coding';
    """)

    # Add coding_questions column to campus_drives table
    op.execute("""
        ALTER TABLE campus_drives
        ADD COLUMN IF NOT EXISTS coding_questions INTEGER DEFAULT 5;
    """)

    # Add coding_score column to campus_drive_registrations table
    op.execute("""
        ALTER TABLE campus_drive_registrations
        ADD COLUMN IF NOT EXISTS coding_score FLOAT DEFAULT 0;
    """)


def downgrade() -> None:
    # Remove coding_score column
    op.execute("""
        ALTER TABLE campus_drive_registrations
        DROP COLUMN IF EXISTS coding_score;
    """)

    # Remove coding_questions column
    op.execute("""
        ALTER TABLE campus_drives
        DROP COLUMN IF EXISTS coding_questions;
    """)

    # Note: Cannot remove enum value in PostgreSQL without recreating the type
    # The 'coding' value will remain in the enum
