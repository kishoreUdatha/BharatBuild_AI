"""add_workspaces_table

Revision ID: 2bd5160026e3
Revises: 22b8a8e697ea
Create Date: 2025-12-03 23:05:02.240632

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2bd5160026e3'
down_revision = '22b8a8e697ea'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table exists before creating (idempotent migration)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # Create workspaces table if not exists
    if 'workspaces' not in existing_tables:
        op.create_table('workspaces',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_default', sa.Boolean(), nullable=True),
            sa.Column('storage_path', sa.String(length=500), nullable=True),
            sa.Column('s3_prefix', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_workspaces_is_default', 'workspaces', ['is_default'], unique=False)
        op.create_index('ix_workspaces_user_id', 'workspaces', ['user_id'], unique=False)

    # Add workspace_id column to projects table if not exists
    columns = [col['name'] for col in inspector.get_columns('projects')]
    if 'workspace_id' not in columns:
        op.add_column('projects', sa.Column('workspace_id', sa.String(length=36), nullable=True))
        op.create_index('ix_projects_workspace_id', 'projects', ['workspace_id'], unique=False)
        op.create_foreign_key('fk_projects_workspace_id', 'projects', 'workspaces', ['workspace_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    # Remove workspace_id from projects
    op.drop_constraint('fk_projects_workspace_id', 'projects', type_='foreignkey')
    op.drop_index('ix_projects_workspace_id', table_name='projects')
    op.drop_column('projects', 'workspace_id')

    # Drop workspaces table
    op.drop_index('ix_workspaces_user_id', table_name='workspaces')
    op.drop_index('ix_workspaces_is_default', table_name='workspaces')
    op.drop_table('workspaces')
