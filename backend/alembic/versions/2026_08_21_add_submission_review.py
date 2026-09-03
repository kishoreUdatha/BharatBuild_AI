"""Submissions become reviewable: a stage, a version, and a verdict with a reason.

`project_submissions` recorded that something was handed in and whether it was
accepted, but not which stage it belonged to, who judged it, or why it was
turned down - so a rejected submission gave a team nothing to act on.

The stage column is what makes a submission mean something: accepting one is
what moves the batch's tracked progress forward.

Guarded with IF NOT EXISTS because `main.py` runs `create_all` at startup, so
these columns may already exist when this runs. Ids are VARCHAR(36) to match
`app.core.types.GUID` on this deployment.

Revision ID: add_submission_review
Revises: add_file_store
"""

from alembic import op
import sqlalchemy as sa

revision = 'add_submission_review'
down_revision = 'add_file_store'
branch_labels = None
depends_on = None

# The Python enum MEMBER NAMES, uppercase - SQLAlchemy's Enum(PyEnum) persists
# members by name, so a type created with the lowercase values would fail on
# the first insert.
STAGES = [
    "TOPIC_APPROVAL", "BASE_PAPER", "REQUIREMENTS", "SYSTEM_DESIGN",
    "DEVELOPMENT", "TESTING", "DOCUMENTATION", "FINAL_REVIEW",
]


def upgrade() -> None:
    labels = ", ".join(f"'{s}'" for s in STAGES)
    op.execute(f"""
        DO $$ BEGIN
            CREATE TYPE projectstage AS ENUM ({labels});
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        ALTER TABLE project_submissions
            ADD COLUMN IF NOT EXISTS stage projectstage,
            ADD COLUMN IF NOT EXISTS version VARCHAR(16) DEFAULT 'v1.0',
            ADD COLUMN IF NOT EXISTS reviewed_by_id VARCHAR(36)
                REFERENCES users(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS faculty_note TEXT,
            ADD COLUMN IF NOT EXISTS superseded_by_id VARCHAR(36)
                REFERENCES project_submissions(id) ON DELETE SET NULL
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_submissions_stage "
               "ON project_submissions (stage)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_project_submissions_stage")
    op.execute("""
        ALTER TABLE project_submissions
            DROP COLUMN IF EXISTS stage,
            DROP COLUMN IF EXISTS version,
            DROP COLUMN IF EXISTS reviewed_by_id,
            DROP COLUMN IF EXISTS faculty_note,
            DROP COLUMN IF EXISTS superseded_by_id
    """)
