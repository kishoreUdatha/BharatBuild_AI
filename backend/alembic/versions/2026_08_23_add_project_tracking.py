"""Tasks, deliverables and integrations for the project tracker.

The tracking screen answers questions the database could not: how many tasks
are overdue, which projects are blocked and why, how far along each deliverable
is, and whether a repository is connected. Three tables and one column.

`batch_stage_progress` gains `planned_date`. The eight stages already record
what percent is done and when it completed - what was missing is when it was
*meant* to, which is the whole point of a milestone timeline showing planned
beside actual.

Ids are VARCHAR(36) to match `app.core.types.GUID` on this deployment.

Revision ID: add_project_tracking
Revises: tenant_academics
"""

from alembic import op

revision = 'add_project_tracking'
down_revision = 'tenant_academics'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- planned dates on the existing stages -------------------------------
    op.execute("ALTER TABLE batch_stage_progress ADD COLUMN IF NOT EXISTS planned_date DATE")

    # --- tasks and blockers -------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE taskpriority AS ENUM ('HIGH', 'MEDIUM', 'LOW');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE taskstatus AS ENUM ('OPEN', 'IN_PROGRESS', 'BLOCKED', 'DONE');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS project_tasks (
            id VARCHAR(36) PRIMARY KEY,
            batch_id VARCHAR(36) NOT NULL REFERENCES project_batches (id) ON DELETE CASCADE,
            title VARCHAR(300) NOT NULL,
            detail TEXT,
            assignee_id VARCHAR(36) REFERENCES users (id) ON DELETE SET NULL,
            priority taskpriority NOT NULL DEFAULT 'MEDIUM',
            status taskstatus NOT NULL DEFAULT 'OPEN',
            due_date DATE,
            completed_at TIMESTAMP,
            blocked_reason VARCHAR(300),
            created_by_id VARCHAR(36) REFERENCES users (id) ON DELETE SET NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP
        )
    """)
    for col in ("batch_id", "assignee_id", "priority", "status", "due_date"):
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_project_tasks_{col} ON project_tasks ({col})")

    # --- deliverables -------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE deliverablestatus AS ENUM ('PENDING', 'AVAILABLE', 'VERIFIED');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS project_deliverables (
            id VARCHAR(36) PRIMARY KEY,
            batch_id VARCHAR(36) NOT NULL REFERENCES project_batches (id) ON DELETE CASCADE,
            name VARCHAR(120) NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            status deliverablestatus NOT NULL DEFAULT 'PENDING',
            evidence_url VARCHAR(500),
            file_id VARCHAR(36) REFERENCES stored_files (id) ON DELETE SET NULL,
            position INTEGER DEFAULT 0,
            updated_at TIMESTAMP,
            CONSTRAINT uq_deliverable_per_batch UNIQUE (batch_id, name)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_deliverables_batch_id "
               "ON project_deliverables (batch_id)")

    # --- integrations -------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE integrationkind AS ENUM
                ('REPOSITORY', 'BUILD', 'DEPLOYMENT', 'REVIEW');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE integrationstate AS ENUM
                ('NOT_CONNECTED', 'CONNECTED', 'PASSED', 'FAILED', 'LIVE', 'SCHEDULED');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS batch_integrations (
            id VARCHAR(36) PRIMARY KEY,
            batch_id VARCHAR(36) NOT NULL REFERENCES project_batches (id) ON DELETE CASCADE,
            kind integrationkind NOT NULL,
            state integrationstate NOT NULL DEFAULT 'NOT_CONNECTED',
            detail VARCHAR(200),
            url VARCHAR(500),
            updated_at TIMESTAMP,
            CONSTRAINT uq_integration_per_batch UNIQUE (batch_id, kind)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_batch_integrations_batch_id "
               "ON batch_integrations (batch_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS batch_integrations")
    op.execute("DROP TABLE IF EXISTS project_deliverables")
    op.execute("DROP TABLE IF EXISTS project_tasks")
    op.execute("ALTER TABLE batch_stage_progress DROP COLUMN IF EXISTS planned_date")
    for t in ("integrationstate", "integrationkind", "deliverablestatus",
              "taskstatus", "taskpriority"):
        op.execute(f"DROP TYPE IF EXISTS {t}")
