"""Student registration: join codes, seat state and per-student payments.

The faculty portal treated batch membership as a settled fact. The student
side needs the states before that: a seat can be allocated and invited before
the student accepts it, and each member pays their own share, so a batch can
sit part-paid.

Guarded with IF NOT EXISTS / duplicate_object because `main.py` runs
`create_all` at startup, so these objects may already exist when this runs.

Revision ID: add_student_registration
Revises: add_academics
"""

from alembic import op
import sqlalchemy as sa

revision = 'add_student_registration'
down_revision = 'add_academics'
branch_labels = None
depends_on = None


# Labels are the Python enum MEMBER NAMES, uppercase. SQLAlchemy's Enum(PyEnum)
# persists members by name, so a type created with the lowercase *values* here
# would be rejected on the first insert.
ENUMS = {
    "memberinvitestatus": ["INVITED", "JOINED", "DECLINED"],
    "paymentstatus": ["PENDING", "PAID", "FAILED", "REFUNDED"],
}


def upgrade() -> None:
    for name, values in ENUMS.items():
        labels = ", ".join(f"'{v}'" for v in values)
        op.execute(f"""
            DO $$ BEGIN
                CREATE TYPE {name} AS ENUM ({labels});
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """)

    op.execute("ALTER TABLE project_batches ADD COLUMN IF NOT EXISTS join_code VARCHAR(40);")
    op.execute("ALTER TABLE project_batches ADD COLUMN IF NOT EXISTS team_size INTEGER NOT NULL DEFAULT 4;")
    op.execute("ALTER TABLE project_batches ADD COLUMN IF NOT EXISTS project_fee INTEGER NOT NULL DEFAULT 15000;")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_project_batches_join_code ON project_batches (join_code);")

    # Existing rows are real memberships, so they default to joined and
    # confirmed - anything else would retro-invalidate the faculty portal.
    op.execute("""
        ALTER TABLE project_batch_members
        ADD COLUMN IF NOT EXISTS invite_status memberinvitestatus NOT NULL DEFAULT 'JOINED';
    """)
    op.execute("""
        ALTER TABLE project_batch_members
        ADD COLUMN IF NOT EXISTS seat_confirmed BOOLEAN NOT NULL DEFAULT TRUE;
    """)
    op.execute("ALTER TABLE project_batch_members ADD COLUMN IF NOT EXISTS invited_at TIMESTAMP;")
    op.execute("ALTER TABLE project_batch_members ADD COLUMN IF NOT EXISTS invite_reminded_at TIMESTAMP;")
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_project_batch_members_invite_status
        ON project_batch_members (invite_status);
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS registration_payments (
            id UUID PRIMARY KEY,
            batch_id UUID NOT NULL REFERENCES project_batches(id) ON DELETE CASCADE,
            student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            amount INTEGER NOT NULL,
            status paymentstatus NOT NULL DEFAULT 'PENDING',
            method VARCHAR(40),
            reference VARCHAR(80),
            receipt_number VARCHAR(40),
            paid_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP,
            CONSTRAINT uq_registration_payment UNIQUE (batch_id, student_id)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_registration_payments_batch_id ON registration_payments (batch_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_registration_payments_student_id ON registration_payments (student_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_registration_payments_status ON registration_payments (status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_registration_payments_receipt ON registration_payments (receipt_number);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS registration_payments CASCADE;")
    for col in ("invite_status", "seat_confirmed", "invited_at", "invite_reminded_at"):
        op.execute(f"ALTER TABLE project_batch_members DROP COLUMN IF EXISTS {col};")
    for col in ("join_code", "team_size", "project_fee"):
        op.execute(f"ALTER TABLE project_batches DROP COLUMN IF EXISTS {col};")
    for name in ENUMS:
        op.execute(f"DROP TYPE IF EXISTS {name};")
