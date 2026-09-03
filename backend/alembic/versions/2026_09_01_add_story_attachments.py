"""Attachments and a due date on a user story.

A story could carry acceptance criteria and a sprint but not the design PDF
the criteria referred to, and not the date it was actually wanted by. Both are
on the single-story page, so both need somewhere to live.

Attachments point at `stored_files`, the same content-addressed store the batch
documents use - so the same PDF attached by three teammates is stored once, and
nothing the browser sends decides where bytes land.

Revision ID: add_story_attachments
Revises: add_story_labels
Create Date: 2026-09-01
"""

from alembic import op

revision = 'add_story_attachments'
down_revision = 'add_story_labels'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Attaching and removing a file are things that happened to the story, so
    # the history has to be able to say so.
    for label in ("ATTACHED", "DETACHED"):
        op.execute(f"ALTER TYPE storyeventkind ADD VALUE IF NOT EXISTS '{label}'")

    op.execute("ALTER TABLE project_user_stories ADD COLUMN IF NOT EXISTS due_date DATE")
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_user_stories_due_date "
               "ON project_user_stories (due_date)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS story_attachments (
            id VARCHAR(36) PRIMARY KEY,
            story_id VARCHAR(36) NOT NULL REFERENCES project_user_stories (id) ON DELETE CASCADE,
            file_id VARCHAR(36) NOT NULL REFERENCES stored_files (id),
            name VARCHAR(255) NOT NULL,
            uploaded_by_id VARCHAR(36) REFERENCES users (id) ON DELETE SET NULL,
            uploaded_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    for col in ("story_id", "uploaded_at"):
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_story_attachments_{col} "
                   f"ON story_attachments ({col})")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS story_attachments")
    op.execute("DROP INDEX IF EXISTS ix_project_user_stories_due_date")
    op.execute("ALTER TABLE project_user_stories DROP COLUMN IF EXISTS due_date")
