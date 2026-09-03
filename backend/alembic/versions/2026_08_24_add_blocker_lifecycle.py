"""Blockers as records, plus task comments, attachments and dependencies.

A blocker used to be one sentence on a task - enough for a red chip and
nothing else. It could not be assigned to whoever was able to clear it, it
could not be escalated, and nobody could answer why resolution took eleven
days. `project_blockers` carries the lifecycle: who reported it, the category
(fixed, so it can be counted), severity, root cause, impact, the owner who has
to clear it, a target date, and when it actually cleared.

Three smaller tables round out the board and register: comments and
attachments give the counts every card shows, and dependencies are what let a
task say "4 prerequisite tasks".

`project_tasks` gains `stage` - which of the eight milestones the work belongs
to - and `progress`, for work that is neither untouched nor finished.

Ids are VARCHAR(36) to match `app.core.types.GUID` on this deployment.

Revision ID: add_blocker_lifecycle
Revises: add_project_tracking
"""

from alembic import op

revision = 'add_blocker_lifecycle'
down_revision = 'add_project_tracking'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- task columns -------------------------------------------------------
    # projectstage already exists, created with batch_stage_progress.
    op.execute("ALTER TABLE project_tasks ADD COLUMN IF NOT EXISTS stage projectstage")
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_tasks_stage ON project_tasks (stage)")
    op.execute("ALTER TABLE project_tasks ADD COLUMN IF NOT EXISTS progress INTEGER NOT NULL DEFAULT 0")

    # --- blockers -----------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE blockercategory AS ENUM
                ('TECHNICAL', 'DATA', 'APPROVAL', 'TEAM', 'DOCUMENTATION');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE blockerseverity AS ENUM ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE blockerstatus AS ENUM ('OPEN', 'ESCALATED', 'RESOLVED');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS project_blockers (
            id VARCHAR(36) PRIMARY KEY,
            batch_id VARCHAR(36) NOT NULL REFERENCES project_batches (id) ON DELETE CASCADE,
            task_id VARCHAR(36) REFERENCES project_tasks (id) ON DELETE SET NULL,
            title VARCHAR(300) NOT NULL,
            category blockercategory NOT NULL DEFAULT 'TECHNICAL',
            severity blockerseverity NOT NULL DEFAULT 'MEDIUM',
            status blockerstatus NOT NULL DEFAULT 'OPEN',
            root_cause TEXT,
            impact TEXT,
            reported_by_id VARCHAR(36) REFERENCES users (id) ON DELETE SET NULL,
            reported_at TIMESTAMP NOT NULL DEFAULT NOW(),
            resolution_owner_id VARCHAR(36) REFERENCES users (id) ON DELETE SET NULL,
            target_resolution DATE,
            resolved_at TIMESTAMP,
            resolution_note TEXT,
            updated_at TIMESTAMP
        )
    """)
    for col in ("batch_id", "task_id", "category", "severity", "status",
                "reported_at", "resolution_owner_id"):
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_project_blockers_{col} "
                   f"ON project_blockers ({col})")

    # --- comments, attachments, dependencies --------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS task_comments (
            id VARCHAR(36) PRIMARY KEY,
            task_id VARCHAR(36) NOT NULL REFERENCES project_tasks (id) ON DELETE CASCADE,
            author_id VARCHAR(36) REFERENCES users (id) ON DELETE SET NULL,
            body TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_task_comments_task_id ON task_comments (task_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS task_attachments (
            id VARCHAR(36) PRIMARY KEY,
            task_id VARCHAR(36) NOT NULL REFERENCES project_tasks (id) ON DELETE CASCADE,
            file_id VARCHAR(36) NOT NULL REFERENCES stored_files (id) ON DELETE CASCADE,
            uploaded_by_id VARCHAR(36) REFERENCES users (id) ON DELETE SET NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_task_attachments_task_id "
               "ON task_attachments (task_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS task_dependencies (
            id VARCHAR(36) PRIMARY KEY,
            task_id VARCHAR(36) NOT NULL REFERENCES project_tasks (id) ON DELETE CASCADE,
            depends_on_id VARCHAR(36) NOT NULL REFERENCES project_tasks (id) ON DELETE CASCADE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_task_dependency UNIQUE (task_id, depends_on_id)
        )
    """)
    for col in ("task_id", "depends_on_id"):
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_task_dependencies_{col} "
                   f"ON task_dependencies ({col})")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS task_dependencies")
    op.execute("DROP TABLE IF EXISTS task_attachments")
    op.execute("DROP TABLE IF EXISTS task_comments")
    op.execute("DROP TABLE IF EXISTS project_blockers")
    op.execute("DROP TYPE IF EXISTS blockerstatus")
    op.execute("DROP TYPE IF EXISTS blockerseverity")
    op.execute("DROP TYPE IF EXISTS blockercategory")
    op.execute("ALTER TABLE project_tasks DROP COLUMN IF EXISTS progress")
    op.execute("DROP INDEX IF EXISTS ix_project_tasks_stage")
    op.execute("ALTER TABLE project_tasks DROP COLUMN IF EXISTS stage")
