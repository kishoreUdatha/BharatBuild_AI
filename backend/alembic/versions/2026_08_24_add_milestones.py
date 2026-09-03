"""Milestones with owners, evidence, checklists and an approval trail.

`batch_stage_progress` tracks the eight fixed stages - a percentage and two
dates each - and stays as the coarse shape of a project. Milestones are finer
and different in kind: named by the team, owned by a student, reviewed by a
staff member, and backed by evidence.

Approval is a column of its own rather than a status value because "finished"
and "signed off" are different states. Conflating them is how a project
reaches its final review with nothing actually accepted.

Ids are VARCHAR(36) to match `app.core.types.GUID` on this deployment.

Revision ID: add_milestones
Revises: add_blocker_lifecycle
"""

from alembic import op

revision = 'add_milestones'
down_revision = 'add_blocker_lifecycle'
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name, values in (
        ("milestonepriority", "'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'"),
        ("milestonestatus",
         "'NOT_STARTED', 'UPCOMING', 'IN_PROGRESS', 'DELAYED', 'BLOCKED', 'COMPLETE'"),
        ("approvalstate",
         "'NOT_READY', 'PENDING', 'REVIEW_READY', 'APPROVED', 'CHANGES_REQUESTED'"),
        ("evidencestatus", "'PENDING', 'UPLOADED', 'AVAILABLE', 'VERIFIED'"),
    ):
        op.execute(f"""
            DO $$ BEGIN
                CREATE TYPE {name} AS ENUM ({values});
            EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS project_milestones (
            id VARCHAR(36) PRIMARY KEY,
            batch_id VARCHAR(36) NOT NULL REFERENCES project_batches (id) ON DELETE CASCADE,
            name VARCHAR(200) NOT NULL,
            detail TEXT,
            stage projectstage,
            priority milestonepriority NOT NULL DEFAULT 'MEDIUM',
            status milestonestatus NOT NULL DEFAULT 'NOT_STARTED',
            approval approvalstate NOT NULL DEFAULT 'NOT_READY',
            owner_id VARCHAR(36) REFERENCES users (id) ON DELETE SET NULL,
            reviewer_id VARCHAR(36) REFERENCES users (id) ON DELETE SET NULL,
            planned_start DATE,
            planned_date DATE,
            forecast_date DATE,
            completed_at TIMESTAMP,
            progress INTEGER NOT NULL DEFAULT 0,
            position INTEGER DEFAULT 0,
            approved_by_id VARCHAR(36) REFERENCES users (id) ON DELETE SET NULL,
            approved_at TIMESTAMP,
            review_note TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP,
            CONSTRAINT uq_milestone_per_batch UNIQUE (batch_id, name)
        )
    """)
    for col in ("batch_id", "stage", "priority", "status", "approval",
                "owner_id", "reviewer_id", "planned_date"):
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_project_milestones_{col} "
                   f"ON project_milestones ({col})")

    op.execute("""
        CREATE TABLE IF NOT EXISTS milestone_checklist_items (
            id VARCHAR(36) PRIMARY KEY,
            milestone_id VARCHAR(36) NOT NULL
                REFERENCES project_milestones (id) ON DELETE CASCADE,
            label VARCHAR(300) NOT NULL,
            is_done INTEGER NOT NULL DEFAULT 0,
            position INTEGER DEFAULT 0,
            updated_at TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_milestone_checklist_milestone_id "
               "ON milestone_checklist_items (milestone_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS milestone_evidence (
            id VARCHAR(36) PRIMARY KEY,
            milestone_id VARCHAR(36) NOT NULL
                REFERENCES project_milestones (id) ON DELETE CASCADE,
            label VARCHAR(200) NOT NULL,
            status evidencestatus NOT NULL DEFAULT 'PENDING',
            file_id VARCHAR(36) REFERENCES stored_files (id) ON DELETE SET NULL,
            url VARCHAR(500),
            submitted_by_id VARCHAR(36) REFERENCES users (id) ON DELETE SET NULL,
            submitted_at TIMESTAMP,
            verified_by_id VARCHAR(36) REFERENCES users (id) ON DELETE SET NULL,
            verified_at TIMESTAMP,
            position INTEGER DEFAULT 0
        )
    """)
    for col in ("milestone_id", "status"):
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_milestone_evidence_{col} "
                   f"ON milestone_evidence ({col})")

    op.execute("""
        CREATE TABLE IF NOT EXISTS milestone_dependencies (
            id VARCHAR(36) PRIMARY KEY,
            milestone_id VARCHAR(36) NOT NULL
                REFERENCES project_milestones (id) ON DELETE CASCADE,
            depends_on_id VARCHAR(36) NOT NULL
                REFERENCES project_milestones (id) ON DELETE CASCADE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_milestone_dependency UNIQUE (milestone_id, depends_on_id)
        )
    """)
    for col in ("milestone_id", "depends_on_id"):
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_milestone_dependencies_{col} "
                   f"ON milestone_dependencies ({col})")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS milestone_dependencies")
    op.execute("DROP TABLE IF EXISTS milestone_evidence")
    op.execute("DROP TABLE IF EXISTS milestone_checklist_items")
    op.execute("DROP TABLE IF EXISTS project_milestones")
    for name in ("evidencestatus", "approvalstate", "milestonestatus",
                 "milestonepriority"):
        op.execute(f"DROP TYPE IF EXISTS {name}")
