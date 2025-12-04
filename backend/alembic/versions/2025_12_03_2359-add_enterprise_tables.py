"""add_enterprise_tables

Revision ID: add_enterprise_tables
Revises: 2bd5160026e3
Create Date: 2025-12-03 23:59:00.000000

Adds 8 new enterprise tables:
- project_messages: Chat history between user and AI agents
- sandbox_instances: Docker container tracking
- sandbox_logs: Container stdout/stderr logs
- terminal_sessions: WebSocket terminal sessions
- terminal_history: Command history
- live_preview_sessions: Preview URLs and ports
- snapshots: Project checkpoints
- project_file_versions: Git-like file versioning
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_enterprise_tables'
down_revision = '2bd5160026e3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create project_messages table
    op.create_table('project_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('agent_type', sa.String(length=50), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tokens_used', sa.Integer(), default=0),
        sa.Column('model_used', sa.String(length=100), nullable=True),
        sa.Column('extra_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_project_messages_project_id', 'project_messages', ['project_id'], unique=False)
    op.create_index('ix_project_messages_role', 'project_messages', ['role'], unique=False)
    op.create_index('ix_project_messages_created_at', 'project_messages', ['created_at'], unique=False)

    # 2. Create sandbox_instances table
    op.create_table('sandbox_instances',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('docker_container_id', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), default='pending'),
        sa.Column('port_mappings', sa.JSON(), nullable=True),
        sa.Column('environment', sa.JSON(), nullable=True),
        sa.Column('cpu_limit', sa.String(length=20), nullable=True),
        sa.Column('memory_limit', sa.String(length=20), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('terminated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sandbox_instances_project_id', 'sandbox_instances', ['project_id'], unique=False)
    op.create_index('ix_sandbox_instances_status', 'sandbox_instances', ['status'], unique=False)
    op.create_index('ix_sandbox_instances_docker_id', 'sandbox_instances', ['docker_container_id'], unique=False)

    # 3. Create sandbox_logs table
    op.create_table('sandbox_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('sandbox_id', sa.String(length=36), nullable=False),
        sa.Column('log_type', sa.String(length=50), default='stdout'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['sandbox_id'], ['sandbox_instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sandbox_logs_sandbox_id', 'sandbox_logs', ['sandbox_id'], unique=False)
    op.create_index('ix_sandbox_logs_log_type', 'sandbox_logs', ['log_type'], unique=False)
    op.create_index('ix_sandbox_logs_created_at', 'sandbox_logs', ['created_at'], unique=False)

    # 4. Create terminal_sessions table
    op.create_table('terminal_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('sandbox_id', sa.String(length=36), nullable=False),
        sa.Column('session_name', sa.String(length=100), nullable=True),
        sa.Column('pty_pid', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_activity', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['sandbox_id'], ['sandbox_instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_terminal_sessions_sandbox_id', 'terminal_sessions', ['sandbox_id'], unique=False)
    op.create_index('ix_terminal_sessions_is_active', 'terminal_sessions', ['is_active'], unique=False)

    # 5. Create terminal_history table
    op.create_table('terminal_history',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('command', sa.Text(), nullable=False),
        sa.Column('output', sa.Text(), nullable=True),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('executed_at', sa.DateTime(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['terminal_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_terminal_history_session_id', 'terminal_history', ['session_id'], unique=False)
    op.create_index('ix_terminal_history_executed_at', 'terminal_history', ['executed_at'], unique=False)

    # 6. Create live_preview_sessions table
    op.create_table('live_preview_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('sandbox_id', sa.String(length=36), nullable=False),
        sa.Column('preview_url', sa.String(length=500), nullable=True),
        sa.Column('internal_port', sa.Integer(), nullable=False),
        sa.Column('external_port', sa.Integer(), nullable=True),
        sa.Column('protocol', sa.String(length=10), default='http'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_accessed', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['sandbox_id'], ['sandbox_instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_live_preview_sessions_sandbox_id', 'live_preview_sessions', ['sandbox_id'], unique=False)
    op.create_index('ix_live_preview_sessions_is_active', 'live_preview_sessions', ['is_active'], unique=False)

    # 7. Create snapshots table
    op.create_table('snapshots',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('snapshot_json', sa.JSON(), nullable=False),
        sa.Column('file_count', sa.Integer(), default=0),
        sa.Column('total_size_bytes', sa.Integer(), default=0),
        sa.Column('created_by', sa.String(length=50), default='user'),
        sa.Column('trigger', sa.String(length=100), nullable=True),
        sa.Column('s3_key', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_snapshots_project_id', 'snapshots', ['project_id'], unique=False)
    op.create_index('ix_snapshots_created_at', 'snapshots', ['created_at'], unique=False)

    # 8. Create project_file_versions table
    op.create_table('project_file_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('file_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('s3_url', sa.String(length=500), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('size_bytes', sa.Integer(), default=0),
        sa.Column('diff_patch', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=50), nullable=True),
        sa.Column('change_type', sa.String(length=50), nullable=True),
        sa.Column('change_summary', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['project_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_file_versions_file_id', 'project_file_versions', ['file_id'], unique=False)
    op.create_index('ix_file_versions_project_id', 'project_file_versions', ['project_id'], unique=False)
    op.create_index('ix_file_versions_version', 'project_file_versions', ['version'], unique=False)
    op.create_index('ix_file_versions_created_at', 'project_file_versions', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key dependencies)

    # 8. Drop project_file_versions
    op.drop_index('ix_file_versions_created_at', table_name='project_file_versions')
    op.drop_index('ix_file_versions_version', table_name='project_file_versions')
    op.drop_index('ix_file_versions_project_id', table_name='project_file_versions')
    op.drop_index('ix_file_versions_file_id', table_name='project_file_versions')
    op.drop_table('project_file_versions')

    # 7. Drop snapshots
    op.drop_index('ix_snapshots_created_at', table_name='snapshots')
    op.drop_index('ix_snapshots_project_id', table_name='snapshots')
    op.drop_table('snapshots')

    # 6. Drop live_preview_sessions
    op.drop_index('ix_live_preview_sessions_is_active', table_name='live_preview_sessions')
    op.drop_index('ix_live_preview_sessions_sandbox_id', table_name='live_preview_sessions')
    op.drop_table('live_preview_sessions')

    # 5. Drop terminal_history
    op.drop_index('ix_terminal_history_executed_at', table_name='terminal_history')
    op.drop_index('ix_terminal_history_session_id', table_name='terminal_history')
    op.drop_table('terminal_history')

    # 4. Drop terminal_sessions
    op.drop_index('ix_terminal_sessions_is_active', table_name='terminal_sessions')
    op.drop_index('ix_terminal_sessions_sandbox_id', table_name='terminal_sessions')
    op.drop_table('terminal_sessions')

    # 3. Drop sandbox_logs
    op.drop_index('ix_sandbox_logs_created_at', table_name='sandbox_logs')
    op.drop_index('ix_sandbox_logs_log_type', table_name='sandbox_logs')
    op.drop_index('ix_sandbox_logs_sandbox_id', table_name='sandbox_logs')
    op.drop_table('sandbox_logs')

    # 2. Drop sandbox_instances
    op.drop_index('ix_sandbox_instances_docker_id', table_name='sandbox_instances')
    op.drop_index('ix_sandbox_instances_status', table_name='sandbox_instances')
    op.drop_index('ix_sandbox_instances_project_id', table_name='sandbox_instances')
    op.drop_table('sandbox_instances')

    # 1. Drop project_messages
    op.drop_index('ix_project_messages_created_at', table_name='project_messages')
    op.drop_index('ix_project_messages_role', table_name='project_messages')
    op.drop_index('ix_project_messages_project_id', table_name='project_messages')
    op.drop_table('project_messages')
