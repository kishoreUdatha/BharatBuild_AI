"""Labels on a user story.

The trainer import template carries a Labels column - comma separated tags
like "authentication,frontend". They were being read and thrown away, which
makes an import lossy in a way nobody would notice until they went looking
for the tag. One column ends that.

Revision ID: add_story_labels
Revises: add_story_delivery
Create Date: 2026-09-01
"""

from alembic import op

revision = 'add_story_labels'
down_revision = 'add_story_delivery'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE project_user_stories ADD COLUMN IF NOT EXISTS labels VARCHAR(300)")


def downgrade() -> None:
    op.execute("ALTER TABLE project_user_stories DROP COLUMN IF EXISTS labels")
