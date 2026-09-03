"""The file store: one row per stored blob, and the columns that point at it.

Before this, `batch_documents`, `base_papers` and `project_submissions` all
described files with no way to record where the bytes were, so every download
button on those screens promised something that could not be produced.

Blobs are content-addressed by SHA-256, which is unique: uploading the same
PDF twice reuses the row rather than storing it again.

Guarded with IF NOT EXISTS because `main.py` runs `create_all` at startup, so
these objects may already exist when this runs.

Ids are VARCHAR(36), not UUID: `app.core.types.GUID` renders as a 36-character
string on this deployment, and a UUID column here would not take a foreign key
against `users.id`.

Revision ID: add_file_store
Revises: add_ai_planning
"""

from alembic import op
import sqlalchemy as sa

revision = 'add_file_store'
down_revision = 'add_ai_planning'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS stored_files (
            id VARCHAR(36) PRIMARY KEY,
            sha256 VARCHAR(64) NOT NULL UNIQUE,
            backend VARCHAR(16) NOT NULL DEFAULT 'local',
            storage_key VARCHAR(500) NOT NULL,
            original_name VARCHAR(255) NOT NULL,
            mime_type VARCHAR(120) NOT NULL,
            byte_size INTEGER NOT NULL,
            page_count INTEGER,
            uploaded_by_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
            uploaded_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_stored_files_sha256 ON stored_files (sha256)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stored_files_uploaded_at ON stored_files (uploaded_at)")

    # SET NULL rather than CASCADE: losing a blob must not silently delete the
    # document row that recorded it was uploaded and verified.
    for table in ("batch_documents", "base_papers", "project_submissions"):
        op.execute(f"""
            ALTER TABLE {table}
            ADD COLUMN IF NOT EXISTS file_id VARCHAR(36)
            REFERENCES stored_files(id) ON DELETE SET NULL
        """)
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_file_id ON {table} (file_id)")


def downgrade() -> None:
    for table in ("batch_documents", "base_papers", "project_submissions"):
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_file_id")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS file_id")
    op.execute("DROP TABLE IF EXISTS stored_files")
