"""add_retrieval_tables

Revision ID: add_retrieval_tables
Revises: add_enterprise_tables
Create Date: 2025-12-04 00:01:00.000000

Adds 3 new tables for Bolt.new-style project retrieval:
- project_file_trees: Cached file tree structure for instant UI rendering
- project_plans: AI-generated project plans (plan.json)
- agent_states: Agent state for resumption capability
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_retrieval_tables'
down_revision = 'add_enterprise_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create project_file_trees table
    op.create_table('project_file_trees',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('tree_json', sa.JSON(), nullable=False),
        sa.Column('files_index', sa.JSON(), nullable=True),
        sa.Column('total_files', sa.String(length=20), default='0'),
        sa.Column('total_folders', sa.String(length=20), default='0'),
        sa.Column('total_size_bytes', sa.String(length=50), default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', name='uq_project_file_trees_project_id')
    )
    op.create_index('ix_project_file_trees_project_id', 'project_file_trees', ['project_id'], unique=False)

    # 2. Create project_plans table
    op.create_table('project_plans',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('plan_json', sa.JSON(), nullable=False),
        sa.Column('version', sa.String(length=20), default='1.0'),
        sa.Column('status', sa.String(length=50), default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', name='uq_project_plans_project_id')
    )
    op.create_index('ix_project_plans_project_id', 'project_plans', ['project_id'], unique=False)

    # 3. Create agent_states table
    op.create_table('agent_states',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('agent_type', sa.String(length=50), nullable=False),
        sa.Column('state_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), default='idle'),
        sa.Column('current_action', sa.String(length=255), nullable=True),
        sa.Column('progress', sa.String(length=10), default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.String(length=10), default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_states_project_id', 'agent_states', ['project_id'], unique=False)
    op.create_index('ix_agent_states_agent_type', 'agent_states', ['agent_type'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order

    # 3. Drop agent_states
    op.drop_index('ix_agent_states_agent_type', table_name='agent_states')
    op.drop_index('ix_agent_states_project_id', table_name='agent_states')
    op.drop_table('agent_states')

    # 2. Drop project_plans
    op.drop_index('ix_project_plans_project_id', table_name='project_plans')
    op.drop_table('project_plans')

    # 1. Drop project_file_trees
    op.drop_index('ix_project_file_trees_project_id', table_name='project_file_trees')
    op.drop_table('project_file_trees')
