"""Sprints, delivery state, comments and events on user stories.

AI planning stopped at approval: a story reached the product backlog
unassigned, unscheduled and unstarted, and nothing recorded what happened to
it after that. The User Stories screen is that next step, so the story row
gains its sprint, assignee and workflow status, and three tables arrive with
it - the sprints themselves, the comments left on a story, and an append-only
record of what changed.

`project_tasks` gains `story_id`. Tasks already existed against a batch; what
was missing was saying which backlog item a piece of work breaks down.

Ids are VARCHAR(36) to match `app.core.types.GUID` on this deployment.

Revision ID: add_story_delivery
Revises: add_trainer_role
Create Date: 2026-08-31
"""

from alembic import op

revision = 'add_story_delivery'
down_revision = 'add_trainer_role'
branch_labels = None
depends_on = None

# Labels are the Python enum MEMBER NAMES, uppercase - SQLAlchemy persists
# Enum(PyEnum) members by name, not by value.
ENUMS = {
    "sprintstate": ["PLANNED", "ACTIVE", "COMPLETED"],
    "storyworkflowstatus": ["TO_DO", "IN_PROGRESS", "IN_REVIEW", "DONE"],
    "storytype": ["STORY", "TASK", "BUG", "SPIKE"],
    "storyeventkind": ["CREATED", "IMPORTED", "ASSIGNED", "STATUS_CHANGED",
                       "SPRINT_CHANGED", "PRIORITY_CHANGED", "POINTS_CHANGED",
                       "EDITED", "COMMENTED"],
}


def upgrade() -> None:
    for name, values in ENUMS.items():
        labels = ", ".join(f"'{v}'" for v in values)
        op.execute(f"""
            DO $$ BEGIN
                CREATE TYPE {name} AS ENUM ({labels});
            EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """)

    # --- sprints ------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS project_sprints (
            id VARCHAR(36) PRIMARY KEY,
            batch_id VARCHAR(36) NOT NULL REFERENCES project_batches (id) ON DELETE CASCADE,
            key VARCHAR(20) NOT NULL,
            name VARCHAR(80) NOT NULL,
            goal VARCHAR(300),
            start_date DATE,
            end_date DATE,
            state sprintstate NOT NULL DEFAULT 'PLANNED',
            position INTEGER DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_sprint_batch_key UNIQUE (batch_id, key)
        )
    """)
    for col in ("batch_id", "key", "state"):
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_project_sprints_{col} "
                   f"ON project_sprints ({col})")

    # --- delivery state on the story itself ---------------------------------
    op.execute("""
        ALTER TABLE project_user_stories
            ADD COLUMN IF NOT EXISTS story_type storytype NOT NULL DEFAULT 'STORY',
            ADD COLUMN IF NOT EXISTS workflow_status storyworkflowstatus NOT NULL DEFAULT 'TO_DO',
            ADD COLUMN IF NOT EXISTS assignee_id VARCHAR(36) REFERENCES users (id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS sprint_id VARCHAR(36) REFERENCES project_sprints (id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS created_by_id VARCHAR(36) REFERENCES users (id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS started_at TIMESTAMP,
            ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP
    """)
    for col in ("story_type", "workflow_status", "assignee_id", "sprint_id"):
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_project_user_stories_{col} "
                   f"ON project_user_stories ({col})")

    # --- comments and events ------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS story_comments (
            id VARCHAR(36) PRIMARY KEY,
            story_id VARCHAR(36) NOT NULL REFERENCES project_user_stories (id) ON DELETE CASCADE,
            author_id VARCHAR(36) REFERENCES users (id) ON DELETE SET NULL,
            author_name VARCHAR(120),
            body TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_story_comments_story_id "
               "ON story_comments (story_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_story_comments_created_at "
               "ON story_comments (created_at)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS story_events (
            id VARCHAR(36) PRIMARY KEY,
            story_id VARCHAR(36) NOT NULL REFERENCES project_user_stories (id) ON DELETE CASCADE,
            actor_id VARCHAR(36) REFERENCES users (id) ON DELETE SET NULL,
            actor_name VARCHAR(120),
            kind storyeventkind NOT NULL,
            summary VARCHAR(300) NOT NULL,
            from_value VARCHAR(120),
            to_value VARCHAR(120),
            occurred_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    for col in ("story_id", "kind", "occurred_at"):
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_story_events_{col} ON story_events ({col})")

    # --- which backlog item a task breaks down ------------------------------
    op.execute("""
        ALTER TABLE project_tasks
            ADD COLUMN IF NOT EXISTS story_id VARCHAR(36)
                REFERENCES project_user_stories (id) ON DELETE SET NULL
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_tasks_story_id "
               "ON project_tasks (story_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_project_tasks_story_id")
    op.execute("ALTER TABLE project_tasks DROP COLUMN IF EXISTS story_id")
    op.execute("DROP TABLE IF EXISTS story_events")
    op.execute("DROP TABLE IF EXISTS story_comments")
    op.execute("""
        ALTER TABLE project_user_stories
            DROP COLUMN IF EXISTS story_type,
            DROP COLUMN IF EXISTS workflow_status,
            DROP COLUMN IF EXISTS assignee_id,
            DROP COLUMN IF EXISTS sprint_id,
            DROP COLUMN IF EXISTS created_by_id,
            DROP COLUMN IF EXISTS started_at,
            DROP COLUMN IF EXISTS completed_at
    """)
    op.execute("DROP TABLE IF EXISTS project_sprints")
    for name in ENUMS:
        op.execute(f"DROP TYPE IF EXISTS {name}")
