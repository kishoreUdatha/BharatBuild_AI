"""Give the portal a tenant, so it can hold more than one college.

Until now no table in the project portal recorded which institution its rows
belonged to. `project_batches` carried department, section, year, semester and
academic year, and nothing that said *whose*. The list endpoints therefore had
nothing to filter on, and a faculty account created at an unrelated college
could read every batch, every student, and download the full student roster
with names, roll numbers, mobile numbers and email addresses.

Four tables sit at a root and are stamped here. Fifteen more reach a college
through `batch_id`, and two beyond those through `base_paper_id`, so they need
no column of their own.

`attendance_records` is the awkward one: it holds `student_id` and
`marked_by_id` but no `batch_id`, so it cannot inherit and is stamped directly.

Three unique keys become composite. A second college would otherwise collide
on the first two and share rows on the third:

    project_batches.batch_code   every college has a CSE section A
    activity_logs.event_code     a global counter, so codes collide
    stored_files.sha256          identical uploads collapse into one row

`join_code` is deliberately left globally unique. It is a secret a student
types to join a batch, and global uniqueness is what stops a code minted at
one college resolving to a batch at another.

Ids are VARCHAR(36) to match `app.core.types.GUID` on this deployment.

Revision ID: add_tenant_isolation
Revises: add_review_slot_minutes
"""

from alembic import op

revision = 'add_tenant_isolation'
down_revision = 'add_review_slot_minutes'
branch_labels = None
depends_on = None

# The tables that carry a college of their own.
ROOTS = ("project_batches", "student_enrollments", "attendance_records", "stored_files")

HOME_CODE = "SGIT"
HOME_NAME = "Sri Guru Institute of Technology"
SELF_SERVE_CODE = "SELF-SERVE"
SELF_SERVE_NAME = "Individual Students"


def upgrade() -> None:
    # --- the tenant root ---------------------------------------------------
    # The colleges table already existed but was referenced by no endpoint or
    # service. Adopting it costs nothing; it only gains a flag marking the
    # tenant that individually signed-up students belong to, so they never
    # land inside a paying college's rosters and exports.
    op.execute("""
        CREATE TABLE IF NOT EXISTS colleges (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            code VARCHAR(50) NOT NULL UNIQUE,
            address TEXT,
            city VARCHAR(100),
            state VARCHAR(100),
            country VARCHAR(100) DEFAULT 'India',
            email VARCHAR(255),
            phone VARCHAR(20),
            website VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP
        )
    """)
    op.execute("ALTER TABLE colleges ADD COLUMN IF NOT EXISTS is_self_serve BOOLEAN DEFAULT FALSE")

    op.execute(f"""
        INSERT INTO colleges (id, name, code, is_active, is_self_serve, created_at)
        SELECT gen_random_uuid()::text, '{HOME_NAME}', '{HOME_CODE}', TRUE, FALSE, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM colleges WHERE code = '{HOME_CODE}')
    """)
    op.execute(f"""
        INSERT INTO colleges (id, name, code, is_active, is_self_serve, created_at)
        SELECT gen_random_uuid()::text, '{SELF_SERVE_NAME}', '{SELF_SERVE_CODE}', TRUE, TRUE, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM colleges WHERE code = '{SELF_SERVE_CODE}')
    """)

    # --- columns, nullable first so the migration cannot fail on old rows ---
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS college_id VARCHAR(36)")
    for table in ROOTS:
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS college_id VARCHAR(36)")
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_college_id ON {table} (college_id)")

    # --- backfill ----------------------------------------------------------
    # Everything that exists today belongs to the one college that has been
    # using the system.
    op.execute(f"""
        UPDATE users SET college_id = (SELECT id FROM colleges WHERE code = '{HOME_CODE}')
        WHERE college_id IS NULL
    """)
    for table in ROOTS:
        op.execute(f"""
            UPDATE {table} SET college_id = (SELECT id FROM colleges WHERE code = '{HOME_CODE}')
            WHERE college_id IS NULL
        """)

    # --- tighten -----------------------------------------------------------
    # Only the portal tables. `users` stays nullable: accounts outside the
    # portal - developers, api partners - legitimately belong to no college.
    for table in ROOTS:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN college_id SET NOT NULL")
        op.execute(f"""
            ALTER TABLE {table}
            ADD CONSTRAINT fk_{table}_college
            FOREIGN KEY (college_id) REFERENCES colleges (id) ON DELETE RESTRICT
        """)

    # --- unique keys become per-college ------------------------------------
    op.execute("ALTER TABLE project_batches DROP CONSTRAINT IF EXISTS project_batches_batch_code_key")
    op.execute("DROP INDEX IF EXISTS ix_project_batches_batch_code")
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_batches_batch_code ON project_batches (batch_code)")
    op.execute("""
        ALTER TABLE project_batches
        ADD CONSTRAINT uq_batch_code_per_college UNIQUE (college_id, batch_code)
    """)

    op.execute("ALTER TABLE activity_logs DROP CONSTRAINT IF EXISTS activity_logs_event_code_key")
    op.execute("DROP INDEX IF EXISTS ix_activity_logs_event_code")
    op.execute("CREATE INDEX IF NOT EXISTS ix_activity_logs_event_code ON activity_logs (event_code)")

    op.execute("ALTER TABLE stored_files DROP CONSTRAINT IF EXISTS stored_files_sha256_key")
    op.execute("DROP INDEX IF EXISTS ix_stored_files_sha256")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stored_files_sha256 ON stored_files (sha256)")
    op.execute("""
        ALTER TABLE stored_files
        ADD CONSTRAINT uq_stored_file_per_college UNIQUE (college_id, sha256)
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE stored_files DROP CONSTRAINT IF EXISTS uq_stored_file_per_college")
    op.execute("ALTER TABLE project_batches DROP CONSTRAINT IF EXISTS uq_batch_code_per_college")
    for table in ROOTS:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS fk_{table}_college")
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_college_id")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS college_id")
    op.execute("ALTER TABLE colleges DROP COLUMN IF EXISTS is_self_serve")
