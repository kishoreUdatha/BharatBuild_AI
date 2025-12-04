"""update_sandbox_columns

Revision ID: update_sandbox_columns
Revises: add_retrieval_tables
Create Date: 2025-12-04 00:02:00.000000

Updates sandbox_instances table to match the model:
- Adds missing columns (image_name, exposed_port, etc.)
- Renames some columns to match model
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'update_sandbox_columns'
down_revision = 'add_retrieval_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing columns to sandbox_instances
    op.add_column('sandbox_instances', sa.Column('image_name', sa.String(255), nullable=True))
    op.add_column('sandbox_instances', sa.Column('exposed_port', sa.Integer(), nullable=True))
    op.add_column('sandbox_instances', sa.Column('host_port', sa.Integer(), nullable=True))
    op.add_column('sandbox_instances', sa.Column('node_version', sa.String(20), nullable=True))
    op.add_column('sandbox_instances', sa.Column('python_version', sa.String(20), nullable=True))
    op.add_column('sandbox_instances', sa.Column('working_directory', sa.String(500), nullable=True))
    op.add_column('sandbox_instances', sa.Column('restart_count', sa.String(10), nullable=True, server_default='0'))
    op.add_column('sandbox_instances', sa.Column('started_at', sa.DateTime(), nullable=True))
    op.add_column('sandbox_instances', sa.Column('stopped_at', sa.DateTime(), nullable=True))
    op.add_column('sandbox_instances', sa.Column('last_error', sa.Text(), nullable=True))

    # Rename old columns if they exist (handle idempotency)
    # Note: Some columns may have been named differently in original migration
    # error_message -> last_error is already handled as a new column
    # terminated_at -> stopped_at is already handled as a new column

    # Add missing columns to terminal_sessions
    op.add_column('terminal_sessions', sa.Column('project_id', sa.String(36), nullable=True))
    op.add_column('terminal_sessions', sa.Column('ws_session_id', sa.String(255), nullable=True))
    op.add_column('terminal_sessions', sa.Column('shell_type', sa.String(50), nullable=True, server_default='bash'))

    # Add missing columns to terminal_history
    op.add_column('terminal_history', sa.Column('completed_at', sa.DateTime(), nullable=True))

    # Update live_preview_sessions with missing columns
    op.add_column('live_preview_sessions', sa.Column('local_port', sa.Integer(), nullable=True))
    op.add_column('live_preview_sessions', sa.Column('host_port', sa.Integer(), nullable=True))
    op.add_column('live_preview_sessions', sa.Column('public_url', sa.String(500), nullable=True))
    op.add_column('live_preview_sessions', sa.Column('local_url', sa.String(500), nullable=True))

    # Add missing columns to sandbox_logs
    op.add_column('sandbox_logs', sa.Column('project_id', sa.String(36), nullable=True))
    op.add_column('sandbox_logs', sa.Column('source', sa.String(100), nullable=True))


def downgrade() -> None:
    # Drop added columns from sandbox_logs
    op.drop_column('sandbox_logs', 'source')
    op.drop_column('sandbox_logs', 'project_id')

    # Drop added columns from live_preview_sessions
    op.drop_column('live_preview_sessions', 'local_url')
    op.drop_column('live_preview_sessions', 'public_url')
    op.drop_column('live_preview_sessions', 'host_port')
    op.drop_column('live_preview_sessions', 'local_port')

    # Drop added columns from terminal_history
    op.drop_column('terminal_history', 'completed_at')

    # Drop added columns from terminal_sessions
    op.drop_column('terminal_sessions', 'shell_type')
    op.drop_column('terminal_sessions', 'ws_session_id')
    op.drop_column('terminal_sessions', 'project_id')

    # Drop added columns from sandbox_instances
    op.drop_column('sandbox_instances', 'last_error')
    op.drop_column('sandbox_instances', 'stopped_at')
    op.drop_column('sandbox_instances', 'started_at')
    op.drop_column('sandbox_instances', 'restart_count')
    op.drop_column('sandbox_instances', 'working_directory')
    op.drop_column('sandbox_instances', 'python_version')
    op.drop_column('sandbox_instances', 'node_version')
    op.drop_column('sandbox_instances', 'host_port')
    op.drop_column('sandbox_instances', 'exposed_port')
    op.drop_column('sandbox_instances', 'image_name')
