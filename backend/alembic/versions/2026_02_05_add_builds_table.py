"""add_builds_table

Revision ID: a1b2c3d4e5f6
Revises: add_learning_mode_tables
Create Date: 2026-02-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'add_owner_name_coupons'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table exists before creating (idempotent migration)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # Create builds table if not exists
    if 'builds' not in existing_tables:
        # Create enum types first
        build_platform = sa.Enum('android', 'ios', name='buildplatform')
        build_status = sa.Enum(
            'pending', 'configuring', 'queued', 'in_progress',
            'completed', 'failed', 'cancelled',
            name='buildstatus'
        )

        op.create_table('builds',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('project_id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('platform', build_platform, nullable=False),
            sa.Column('status', build_status, nullable=False, server_default='pending'),
            sa.Column('eas_build_id', sa.String(length=255), nullable=True),
            sa.Column('progress', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('artifact_url', sa.String(length=500), nullable=True),
            sa.Column('s3_key', sa.String(length=500), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('build_config', sa.JSON(), nullable=True),
            sa.Column('celery_task_id', sa.String(length=255), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

        # Create indexes
        op.create_index('ix_builds_project_id', 'builds', ['project_id'], unique=False)
        op.create_index('ix_builds_user_id', 'builds', ['user_id'], unique=False)
        op.create_index('ix_builds_status', 'builds', ['status'], unique=False)
        op.create_index('ix_builds_platform', 'builds', ['platform'], unique=False)
        op.create_index('ix_builds_created_at', 'builds', ['created_at'], unique=False)
        op.create_index('ix_builds_user_platform', 'builds', ['user_id', 'platform'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_builds_user_platform', table_name='builds')
    op.drop_index('ix_builds_created_at', table_name='builds')
    op.drop_index('ix_builds_platform', table_name='builds')
    op.drop_index('ix_builds_status', table_name='builds')
    op.drop_index('ix_builds_user_id', table_name='builds')
    op.drop_index('ix_builds_project_id', table_name='builds')

    # Drop table
    op.drop_table('builds')

    # Drop enum types
    sa.Enum(name='buildstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='buildplatform').drop(op.get_bind(), checkfirst=True)
