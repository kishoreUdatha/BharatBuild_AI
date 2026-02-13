"""add_datasets_table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table exists before creating (idempotent migration)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # Create datasets table if not exists
    if 'datasets' not in existing_tables:
        # Create enum types first
        dataset_status = sa.Enum(
            'pending', 'validated', 'ready', 'failed',
            name='datasetstatus'
        )
        dataset_type = sa.Enum('csv', name='datasettype')

        op.create_table('datasets',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('project_id', sa.String(length=36), nullable=True),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('original_filename', sa.String(length=500), nullable=False),
            sa.Column('s3_key', sa.String(length=1000), nullable=False),
            sa.Column('content_hash', sa.String(length=64), nullable=True),
            sa.Column('size_bytes', sa.Integer(), nullable=False),
            sa.Column('dataset_type', dataset_type, nullable=False, server_default='csv'),
            sa.Column('row_count', sa.Integer(), nullable=True),
            sa.Column('column_count', sa.Integer(), nullable=True),
            sa.Column('columns', sa.JSON(), nullable=True),
            sa.Column('target_column', sa.String(length=255), nullable=True),
            sa.Column('feature_columns', sa.JSON(), nullable=True),
            sa.Column('status', dataset_status, nullable=False, server_default='pending'),
            sa.Column('validation_errors', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

        # Create indexes
        op.create_index('ix_datasets_user_id', 'datasets', ['user_id'], unique=False)
        op.create_index('ix_datasets_project_id', 'datasets', ['project_id'], unique=False)
        op.create_index('ix_datasets_status', 'datasets', ['status'], unique=False)
        op.create_index('ix_datasets_created_at', 'datasets', ['created_at'], unique=False)
        op.create_index('ix_datasets_user_status', 'datasets', ['user_id', 'status'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_datasets_user_status', table_name='datasets')
    op.drop_index('ix_datasets_created_at', table_name='datasets')
    op.drop_index('ix_datasets_status', table_name='datasets')
    op.drop_index('ix_datasets_project_id', table_name='datasets')
    op.drop_index('ix_datasets_user_id', table_name='datasets')

    # Drop table
    op.drop_table('datasets')

    # Drop enum types
    sa.Enum(name='datasetstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='datasettype').drop(op.get_bind(), checkfirst=True)
