"""Add TESTING and BLOCKED to the story workflow.

Testing sits between building and the guide's review; Blocked is where a story
waits on something outside the team.

Revision ID: add_story_stages
Revises: add_story_attachments
Create Date: 2026-09-01
"""
from alembic import op

revision = 'add_story_stages'
down_revision = 'add_story_attachments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLAlchemy stores the enum name, so the labels are upper case to match
    # TO_DO / IN_PROGRESS / DONE already in the type.
    op.execute("ALTER TYPE storyworkflowstatus ADD VALUE IF NOT EXISTS 'TESTING'")
    op.execute("ALTER TYPE storyworkflowstatus ADD VALUE IF NOT EXISTS 'BLOCKED'")


def downgrade() -> None:
    # Postgres cannot drop a value from an enum type. Undoing this means
    # recreating the type and rewriting the column, and any story sitting in
    # one of these stages would have to be moved first.
    pass
