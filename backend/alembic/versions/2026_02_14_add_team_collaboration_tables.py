"""add_team_collaboration_tables

Revision ID: b5c6d7e8f9a0
Revises: a1b2c3d4e5f6
Create Date: 2026-02-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timedelta

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6g7h8'
down_revision = 'b2c3d4e5f6g7'  # Points to add_datasets_table
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if tables exist before creating (idempotent migration)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # Create enum types first (check if they exist)
    team_role = sa.Enum('leader', 'member', 'viewer', name='teamrole')
    team_status = sa.Enum('active', 'archived', 'disbanded', name='teamstatus')
    invitation_status = sa.Enum('pending', 'accepted', 'declined', 'expired', 'cancelled', name='invitationstatus')
    task_status = sa.Enum('todo', 'in_progress', 'in_review', 'completed', 'blocked', name='teamtaskstatus')
    task_priority = sa.Enum('low', 'medium', 'high', 'urgent', name='taskpriority')

    # Create teams table
    if 'teams' not in existing_tables:
        op.create_table('teams',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('project_id', sa.String(length=36), nullable=False),
            sa.Column('created_by', sa.String(length=36), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', team_status, nullable=False, server_default='active'),
            sa.Column('max_members', sa.Integer(), nullable=False, server_default='3'),
            sa.Column('allow_member_invite', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('project_id')
        )

        # Create indexes for teams
        op.create_index('ix_teams_project_id', 'teams', ['project_id'], unique=True)
        op.create_index('ix_teams_status', 'teams', ['status'], unique=False)
        op.create_index('ix_teams_created_by', 'teams', ['created_by'], unique=False)

    # Create team_members table
    if 'team_members' not in existing_tables:
        op.create_table('team_members',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('team_id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('role', team_role, nullable=False, server_default='member'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('workspace_branch', sa.String(length=255), nullable=True),
            sa.Column('joined_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('last_active', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

        # Create indexes for team_members
        op.create_index('ix_team_members_team_id', 'team_members', ['team_id'], unique=False)
        op.create_index('ix_team_members_user_id', 'team_members', ['user_id'], unique=False)
        op.create_index('ix_team_members_team_user', 'team_members', ['team_id', 'user_id'], unique=True)

    # Create team_tasks table
    if 'team_tasks' not in existing_tables:
        op.create_table('team_tasks',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('team_id', sa.String(length=36), nullable=False),
            sa.Column('assignee_id', sa.String(length=36), nullable=True),
            sa.Column('created_by', sa.String(length=36), nullable=False),
            sa.Column('title', sa.String(length=500), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', task_status, nullable=False, server_default='todo'),
            sa.Column('priority', task_priority, nullable=False, server_default='medium'),
            sa.Column('estimated_hours', sa.Integer(), nullable=True),
            sa.Column('actual_hours', sa.Integer(), nullable=True),
            sa.Column('order_index', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('file_paths', sa.JSON(), nullable=True),
            sa.Column('ai_generated', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('ai_complexity_score', sa.Integer(), nullable=True),
            sa.Column('ai_dependencies', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('due_date', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['assignee_id'], ['team_members.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

        # Create indexes for team_tasks
        op.create_index('ix_team_tasks_team_id', 'team_tasks', ['team_id'], unique=False)
        op.create_index('ix_team_tasks_assignee_id', 'team_tasks', ['assignee_id'], unique=False)
        op.create_index('ix_team_tasks_status', 'team_tasks', ['status'], unique=False)
        op.create_index('ix_team_tasks_priority', 'team_tasks', ['priority'], unique=False)
        op.create_index('ix_team_tasks_team_status', 'team_tasks', ['team_id', 'status'], unique=False)

    # Create team_invitations table
    if 'team_invitations' not in existing_tables:
        op.create_table('team_invitations',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('team_id', sa.String(length=36), nullable=False),
            sa.Column('inviter_id', sa.String(length=36), nullable=False),
            sa.Column('invitee_id', sa.String(length=36), nullable=True),
            sa.Column('invitee_email', sa.String(length=255), nullable=False),
            sa.Column('token', sa.String(length=255), nullable=False),
            sa.Column('role', team_role, nullable=False, server_default='member'),
            sa.Column('status', invitation_status, nullable=False, server_default='pending'),
            sa.Column('message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('responded_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['inviter_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['invitee_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )

        # Create indexes for team_invitations
        op.create_index('ix_team_invitations_team_id', 'team_invitations', ['team_id'], unique=False)
        op.create_index('ix_team_invitations_invitee_email', 'team_invitations', ['invitee_email'], unique=False)
        op.create_index('ix_team_invitations_invitee_id', 'team_invitations', ['invitee_id'], unique=False)
        op.create_index('ix_team_invitations_token', 'team_invitations', ['token'], unique=True)
        op.create_index('ix_team_invitations_status', 'team_invitations', ['status'], unique=False)


def downgrade() -> None:
    # Drop indexes and tables in reverse order

    # Drop team_invitations
    op.drop_index('ix_team_invitations_status', table_name='team_invitations')
    op.drop_index('ix_team_invitations_token', table_name='team_invitations')
    op.drop_index('ix_team_invitations_invitee_id', table_name='team_invitations')
    op.drop_index('ix_team_invitations_invitee_email', table_name='team_invitations')
    op.drop_index('ix_team_invitations_team_id', table_name='team_invitations')
    op.drop_table('team_invitations')

    # Drop team_tasks
    op.drop_index('ix_team_tasks_team_status', table_name='team_tasks')
    op.drop_index('ix_team_tasks_priority', table_name='team_tasks')
    op.drop_index('ix_team_tasks_status', table_name='team_tasks')
    op.drop_index('ix_team_tasks_assignee_id', table_name='team_tasks')
    op.drop_index('ix_team_tasks_team_id', table_name='team_tasks')
    op.drop_table('team_tasks')

    # Drop team_members
    op.drop_index('ix_team_members_team_user', table_name='team_members')
    op.drop_index('ix_team_members_user_id', table_name='team_members')
    op.drop_index('ix_team_members_team_id', table_name='team_members')
    op.drop_table('team_members')

    # Drop teams
    op.drop_index('ix_teams_created_by', table_name='teams')
    op.drop_index('ix_teams_status', table_name='teams')
    op.drop_index('ix_teams_project_id', table_name='teams')
    op.drop_table('teams')

    # Drop enum types
    sa.Enum(name='taskpriority').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='teamtaskstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='invitationstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='teamstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='teamrole').drop(op.get_bind(), checkfirst=True)
