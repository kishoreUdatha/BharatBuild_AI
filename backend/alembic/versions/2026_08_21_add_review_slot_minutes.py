"""A review knows how long it is.

`project_reviews` recorded when a review starts but not how long it runs, so
nothing could tell whether two bookings overlap. Anything checking for a
double-booked reviewer had to assume a fixed length, which flagged a
back-to-back round of fifteen-minute slots as a pile of clashes.

Existing rows take the twenty-minute default that code was assuming anyway, so
nothing changes meaning.

Revision ID: add_review_slot_minutes
Revises: add_submission_review
"""

from alembic import op
import sqlalchemy as sa

revision = 'add_review_slot_minutes'
down_revision = 'add_submission_review'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE project_reviews
        ADD COLUMN IF NOT EXISTS slot_minutes INTEGER NOT NULL DEFAULT 20
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE project_reviews DROP COLUMN IF EXISTS slot_minutes")
