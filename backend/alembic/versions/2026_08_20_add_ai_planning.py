"""AI planning: epics, drafted user stories and their trainer review state.

Every AI-drafted story carries its own review status and the trainer who set
it, so the approval screen never has to infer whether something was looked at.

Revision ID: add_ai_planning
Revises: add_verification_codes
"""

from alembic import op

revision = 'add_ai_planning'
down_revision = 'add_verification_codes'
branch_labels = None
depends_on = None

# Labels are the Python enum MEMBER NAMES, uppercase - SQLAlchemy persists
# Enum(PyEnum) members by name, not by value.
ENUMS = {
    "storyreviewstatus": ["NEEDS_REVIEW", "REVIEWED", "APPROVED", "REJECTED", "REVISION_REQUESTED"],
    "storypriority": ["HIGH", "MEDIUM", "LOW"],
    "criterionkind": ["ACCEPTANCE", "DEFINITION_OF_DONE"],
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

    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_planning_runs (
            id UUID PRIMARY KEY,
            batch_id UUID NOT NULL REFERENCES project_batches(id) ON DELETE CASCADE,
            model_label VARCHAR(80),
            source_summary TEXT,
            quality_percent INTEGER,
            story_count INTEGER DEFAULT 0,
            epic_count INTEGER DEFAULT 0,
            generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            generated_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            is_current BOOLEAN DEFAULT TRUE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_runs_batch ON ai_planning_runs (batch_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_runs_current ON ai_planning_runs (is_current);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS project_epics (
            id UUID PRIMARY KEY,
            batch_id UUID NOT NULL REFERENCES project_batches(id) ON DELETE CASCADE,
            key VARCHAR(20) NOT NULL,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            position INTEGER DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_epic_batch_key UNIQUE (batch_id, key)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_epics_batch ON project_epics (batch_id);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS project_user_stories (
            id UUID PRIMARY KEY,
            batch_id UUID NOT NULL REFERENCES project_batches(id) ON DELETE CASCADE,
            epic_id UUID REFERENCES project_epics(id) ON DELETE SET NULL,
            run_id UUID REFERENCES ai_planning_runs(id) ON DELETE SET NULL,
            key VARCHAR(20) NOT NULL,
            title VARCHAR(240) NOT NULL,
            narrative TEXT,
            dependencies VARCHAR(300),
            story_points INTEGER DEFAULT 0,
            priority storypriority NOT NULL DEFAULT 'MEDIUM',
            ai_confidence DOUBLE PRECISION,
            review_status storyreviewstatus NOT NULL DEFAULT 'NEEDS_REVIEW',
            trainer_comment TEXT,
            reviewed_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            reviewed_at TIMESTAMP,
            moved_to_backlog_at TIMESTAMP,
            position INTEGER DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP,
            CONSTRAINT uq_story_batch_key UNIQUE (batch_id, key)
        );
    """)
    for idx, col in [("batch", "batch_id"), ("epic", "epic_id"), ("status", "review_status"),
                     ("priority", "priority"), ("key", "key")]:
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_stories_{idx} ON project_user_stories ({col});")

    op.execute("""
        CREATE TABLE IF NOT EXISTS story_criteria (
            id UUID PRIMARY KEY,
            story_id UUID NOT NULL REFERENCES project_user_stories(id) ON DELETE CASCADE,
            kind criterionkind NOT NULL,
            text TEXT NOT NULL,
            met BOOLEAN NOT NULL DEFAULT TRUE,
            position INTEGER DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_criteria_story ON story_criteria (story_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_criteria_kind ON story_criteria (kind);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS story_revision_requests (
            id UUID PRIMARY KEY,
            story_id UUID NOT NULL REFERENCES project_user_stories(id) ON DELETE CASCADE,
            note TEXT NOT NULL,
            requested_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            requested_at TIMESTAMP NOT NULL DEFAULT NOW(),
            resolved_at TIMESTAMP
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_revisions_story ON story_revision_requests (story_id);")


def downgrade() -> None:
    for t in ("story_revision_requests", "story_criteria", "project_user_stories",
              "project_epics", "ai_planning_runs"):
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE;")
    for name in ENUMS:
        op.execute(f"DROP TYPE IF EXISTS {name};")
