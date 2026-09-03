"""add registration_status to project_batches

Revision ID: add_batch_reg_status
Revises: add_faculty_portal
Create Date: 2026-08-19

Where a batch sits in the registration workflow, behind the Student & Batch
Registrations screen.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_batch_reg_status'
down_revision = 'add_faculty_portal'
branch_labels = None
depends_on = None

VALUES = ['DRAFT', 'INCOMPLETE', 'SUBMITTED', 'PENDING_APPROVAL', 'CHANGES_REQUESTED', 'APPROVED']


def upgrade() -> None:
    labels = ', '.join(f"'{v}'" for v in VALUES)
    # CREATE TYPE has no IF NOT EXISTS, and app.main runs create_all on startup.
    op.execute(f"""
        DO $$ BEGIN
            CREATE TYPE batchregistrationstatus AS ENUM ({labels});
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        ALTER TABLE project_batches
        ADD COLUMN IF NOT EXISTS registration_status batchregistrationstatus
        NOT NULL DEFAULT 'DRAFT';
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_project_batches_registration_status
        ON project_batches (registration_status);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_project_batches_registration_status")
    op.execute("ALTER TABLE project_batches DROP COLUMN IF EXISTS registration_status")
    op.execute("DROP TYPE IF EXISTS batchregistrationstatus")
