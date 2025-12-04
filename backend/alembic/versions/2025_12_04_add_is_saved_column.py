"""add_is_saved_column_to_projects

Revision ID: add_is_saved_column
Revises: update_sandbox_columns
Create Date: 2025-12-04 02:30:00.000000

Adds is_saved column to projects table
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_is_saved_column'
down_revision = 'update_sandbox_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_saved column to projects table
    op.add_column('projects', sa.Column('is_saved', sa.Boolean(), nullable=True, server_default='false'))


def downgrade() -> None:
    # Drop is_saved column from projects table
    op.drop_column('projects', 'is_saved')
