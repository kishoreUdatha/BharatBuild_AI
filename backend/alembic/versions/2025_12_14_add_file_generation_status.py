"""Add file generation status tracking

Revision ID: add_file_gen_status
Revises: add_is_saved_column
Create Date: 2025-12-14

This migration adds:
- generation_status: Track file generation progress (planned/generating/completed/failed/skipped)
- generation_order: Order of file in generation plan
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_file_gen_status'
down_revision = 'add_is_saved_column'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add generation_status enum type
    generation_status_enum = sa.Enum(
        'planned', 'generating', 'completed', 'failed', 'skipped',
        name='filegenerationstatus'
    )
    generation_status_enum.create(op.get_bind(), checkfirst=True)

    # Add generation_status column to project_files
    op.add_column(
        'project_files',
        sa.Column(
            'generation_status',
            sa.Enum('planned', 'generating', 'completed', 'failed', 'skipped', name='filegenerationstatus'),
            nullable=False,
            server_default='completed'  # Default for existing files
        )
    )

    # Add generation_order column
    op.add_column(
        'project_files',
        sa.Column('generation_order', sa.Integer(), nullable=True)
    )

    # Add index for generation_status queries
    op.create_index(
        'ix_project_files_generation_status',
        'project_files',
        ['generation_status']
    )


def downgrade() -> None:
    # Remove index
    op.drop_index('ix_project_files_generation_status', table_name='project_files')

    # Remove columns
    op.drop_column('project_files', 'generation_order')
    op.drop_column('project_files', 'generation_status')

    # Remove enum type
    sa.Enum(name='filegenerationstatus').drop(op.get_bind(), checkfirst=True)
