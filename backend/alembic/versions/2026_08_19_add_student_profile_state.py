"""add profile state to student_enrollments

Revision ID: add_student_profile_state
Revises: add_batch_reg_status
Create Date: 2026-08-19

Verification state, contact/declaration flags and invitation status behind the
Student Registrations tab.
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_student_profile_state'
down_revision = 'add_batch_reg_status'
branch_labels = None
depends_on = None

VALUES = ['VERIFIED', 'VERIFICATION_PENDING', 'PROFILE_INCOMPLETE']


def upgrade() -> None:
    labels = ', '.join(f"'{v}'" for v in VALUES)
    op.execute(f"""
        DO $$ BEGIN
            CREATE TYPE studentprofilestatus AS ENUM ({labels});
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        ALTER TABLE student_enrollments
        ADD COLUMN IF NOT EXISTS profile_status studentprofilestatus
        NOT NULL DEFAULT 'VERIFICATION_PENDING';
    """)
    for col in ('contact_verified', 'declaration_signed', 'invitation_accepted'):
        op.execute(f"""
            ALTER TABLE student_enrollments
            ADD COLUMN IF NOT EXISTS {col} BOOLEAN NOT NULL DEFAULT FALSE;
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_student_enrollments_profile_status
        ON student_enrollments (profile_status);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_student_enrollments_profile_status")
    for col in ('invitation_accepted', 'declaration_signed', 'contact_verified', 'profile_status'):
        op.execute(f"ALTER TABLE student_enrollments DROP COLUMN IF EXISTS {col}")
    op.execute("DROP TYPE IF EXISTS studentprofilestatus")
