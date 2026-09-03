"""add approval workflow fields

Revision ID: add_approval_workflow
Revises: add_student_profile_state
Create Date: 2026-08-19

Submission/SLA timestamps, reviewer, abstract and reminder tracking behind the
Incomplete Registrations and Approval Queue tabs.
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_approval_workflow'
down_revision = 'add_student_profile_state'
branch_labels = None
depends_on = None

BATCH_COLS = [
    ('abstract', 'TEXT'),
    ('submitted_at', 'TIMESTAMP'),
    ('review_due_at', 'TIMESTAMP'),
    ('reviewer_id', 'VARCHAR(36)'),
    ('faculty_note', 'TEXT'),
    ('resolved_at', 'TIMESTAMP'),
    ('last_reminder_at', 'TIMESTAMP'),
]


def upgrade() -> None:
    # REJECTED is a new member of an existing enum.
    op.execute("ALTER TYPE batchregistrationstatus ADD VALUE IF NOT EXISTS 'REJECTED'")

    for name, sql_type in BATCH_COLS:
        op.execute(f"ALTER TABLE project_batches ADD COLUMN IF NOT EXISTS {name} {sql_type}")
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_project_batches_submitted_at
        ON project_batches (submitted_at)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_project_batches_review_due_at
        ON project_batches (review_due_at)
    """)
    op.execute("""
        ALTER TABLE student_enrollments
        ADD COLUMN IF NOT EXISTS last_reminder_at TIMESTAMP
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_project_batches_review_due_at")
    op.execute("DROP INDEX IF EXISTS ix_project_batches_submitted_at")
    for name, _ in BATCH_COLS:
        op.execute(f"ALTER TABLE project_batches DROP COLUMN IF EXISTS {name}")
    op.execute("ALTER TABLE student_enrollments DROP COLUMN IF EXISTS last_reminder_at")
    # Enum members cannot be removed in PostgreSQL without recreating the type.
