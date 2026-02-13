"""add_team_extended_features

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-02-14 12:00:00.000000

Adds:
- Task comments for discussions
- Team activity feed
- Chat message persistence
- Code review requests
- Task time tracking
- Team milestones/sprints
- Member skills
- Team notifications
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'd4e5f6g7h8i9'
down_revision = 'c3d4e5f6g7h8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # Create enum types
    activity_type = sa.Enum(
        'team_created', 'member_joined', 'member_left', 'member_removed',
        'task_created', 'task_updated', 'task_assigned', 'task_completed', 'task_commented',
        'file_created', 'file_modified', 'file_deleted', 'code_merged',
        'review_requested', 'review_completed',
        'milestone_created', 'milestone_completed', 'chat_message',
        name='activitytype'
    )
    review_status = sa.Enum('pending', 'in_review', 'approved', 'changes_requested', 'rejected', name='reviewstatus')
    notification_type = sa.Enum(
        'mention', 'task_assigned', 'task_due_soon', 'task_overdue',
        'review_requested', 'review_completed', 'milestone_due_soon',
        'invitation_received', 'member_joined',
        name='notificationtype'
    )
    milestone_status = sa.Enum('planning', 'active', 'completed', 'cancelled', name='milestonestatus')

    # 1. Create team_milestones table first (referenced by team_tasks)
    if 'team_milestones' not in existing_tables:
        op.create_table('team_milestones',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('team_id', sa.String(length=36), nullable=False),
            sa.Column('created_by', sa.String(length=36), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', milestone_status, nullable=False, server_default='planning'),
            sa.Column('start_date', sa.DateTime(), nullable=True),
            sa.Column('due_date', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('progress', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('order_index', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_team_milestones_team_id', 'team_milestones', ['team_id'])
        op.create_index('ix_team_milestones_status', 'team_milestones', ['status'])
        op.create_index('ix_team_milestones_due_date', 'team_milestones', ['due_date'])

    # 2. Add milestone_id to team_tasks if not exists
    try:
        op.add_column('team_tasks', sa.Column('milestone_id', sa.String(length=36), nullable=True))
        op.create_foreign_key('fk_team_tasks_milestone', 'team_tasks', 'team_milestones', ['milestone_id'], ['id'], ondelete='SET NULL')
        op.create_index('ix_team_tasks_milestone_id', 'team_tasks', ['milestone_id'])
    except Exception:
        pass  # Column may already exist

    # 3. Create task_comments table
    if 'task_comments' not in existing_tables:
        op.create_table('task_comments',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('task_id', sa.String(length=36), nullable=False),
            sa.Column('author_id', sa.String(length=36), nullable=False),
            sa.Column('parent_id', sa.String(length=36), nullable=True),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('mentions', sa.JSON(), nullable=True),
            sa.Column('is_edited', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(['task_id'], ['team_tasks.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['parent_id'], ['task_comments.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_task_comments_task_id', 'task_comments', ['task_id'])
        op.create_index('ix_task_comments_author_id', 'task_comments', ['author_id'])
        op.create_index('ix_task_comments_parent_id', 'task_comments', ['parent_id'])
        op.create_index('ix_task_comments_created_at', 'task_comments', ['created_at'])

    # 4. Create team_activities table
    if 'team_activities' not in existing_tables:
        op.create_table('team_activities',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('team_id', sa.String(length=36), nullable=False),
            sa.Column('actor_id', sa.String(length=36), nullable=True),
            sa.Column('activity_type', activity_type, nullable=False),
            sa.Column('description', sa.String(length=500), nullable=False),
            sa.Column('target_type', sa.String(length=50), nullable=True),
            sa.Column('target_id', sa.String(length=36), nullable=True),
            sa.Column('metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_team_activities_team_id', 'team_activities', ['team_id'])
        op.create_index('ix_team_activities_actor_id', 'team_activities', ['actor_id'])
        op.create_index('ix_team_activities_activity_type', 'team_activities', ['activity_type'])
        op.create_index('ix_team_activities_created_at', 'team_activities', ['created_at'])
        op.create_index('ix_team_activities_team_created', 'team_activities', ['team_id', 'created_at'])

    # 5. Create team_chat_messages table
    if 'team_chat_messages' not in existing_tables:
        op.create_table('team_chat_messages',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('team_id', sa.String(length=36), nullable=False),
            sa.Column('sender_id', sa.String(length=36), nullable=True),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('mentions', sa.JSON(), nullable=True),
            sa.Column('message_type', sa.String(length=20), nullable=True, server_default='text'),
            sa.Column('attachment_url', sa.String(length=500), nullable=True),
            sa.Column('attachment_name', sa.String(length=255), nullable=True),
            sa.Column('is_edited', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_team_chat_messages_team_id', 'team_chat_messages', ['team_id'])
        op.create_index('ix_team_chat_messages_sender_id', 'team_chat_messages', ['sender_id'])
        op.create_index('ix_team_chat_messages_created_at', 'team_chat_messages', ['created_at'])
        op.create_index('ix_team_chat_messages_team_created', 'team_chat_messages', ['team_id', 'created_at'])

    # 6. Create code_reviews table
    if 'code_reviews' not in existing_tables:
        op.create_table('code_reviews',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('team_id', sa.String(length=36), nullable=False),
            sa.Column('requester_id', sa.String(length=36), nullable=False),
            sa.Column('reviewer_id', sa.String(length=36), nullable=True),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', review_status, nullable=False, server_default='pending'),
            sa.Column('file_paths', sa.JSON(), nullable=False),
            sa.Column('feedback', sa.Text(), nullable=True),
            sa.Column('comments', sa.JSON(), nullable=True),
            sa.Column('task_id', sa.String(length=36), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.Column('reviewed_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['requester_id'], ['team_members.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['reviewer_id'], ['team_members.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['task_id'], ['team_tasks.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_code_reviews_team_id', 'code_reviews', ['team_id'])
        op.create_index('ix_code_reviews_requester_id', 'code_reviews', ['requester_id'])
        op.create_index('ix_code_reviews_reviewer_id', 'code_reviews', ['reviewer_id'])
        op.create_index('ix_code_reviews_status', 'code_reviews', ['status'])
        op.create_index('ix_code_reviews_created_at', 'code_reviews', ['created_at'])

    # 7. Create task_time_logs table
    if 'task_time_logs' not in existing_tables:
        op.create_table('task_time_logs',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('task_id', sa.String(length=36), nullable=False),
            sa.Column('member_id', sa.String(length=36), nullable=False),
            sa.Column('description', sa.String(length=500), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('ended_at', sa.DateTime(), nullable=True),
            sa.Column('duration_minutes', sa.Integer(), nullable=True),
            sa.Column('is_running', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['task_id'], ['team_tasks.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['member_id'], ['team_members.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_task_time_logs_task_id', 'task_time_logs', ['task_id'])
        op.create_index('ix_task_time_logs_member_id', 'task_time_logs', ['member_id'])
        op.create_index('ix_task_time_logs_started_at', 'task_time_logs', ['started_at'])

    # 8. Create member_skills table
    if 'member_skills' not in existing_tables:
        op.create_table('member_skills',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('member_id', sa.String(length=36), nullable=False),
            sa.Column('skill_name', sa.String(length=100), nullable=False),
            sa.Column('proficiency_level', sa.Integer(), nullable=True, server_default='3'),
            sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['member_id'], ['team_members.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_member_skills_member_id', 'member_skills', ['member_id'])
        op.create_index('ix_member_skills_skill_name', 'member_skills', ['skill_name'])
        op.create_index('ix_member_skills_member_skill', 'member_skills', ['member_id', 'skill_name'], unique=True)

    # 9. Create team_notifications table
    if 'team_notifications' not in existing_tables:
        op.create_table('team_notifications',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('team_id', sa.String(length=36), nullable=False),
            sa.Column('actor_id', sa.String(length=36), nullable=True),
            sa.Column('notification_type', notification_type, nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('message', sa.Text(), nullable=True),
            sa.Column('target_type', sa.String(length=50), nullable=True),
            sa.Column('target_id', sa.String(length=36), nullable=True),
            sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('read_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_team_notifications_user_id', 'team_notifications', ['user_id'])
        op.create_index('ix_team_notifications_team_id', 'team_notifications', ['team_id'])
        op.create_index('ix_team_notifications_is_read', 'team_notifications', ['is_read'])
        op.create_index('ix_team_notifications_created_at', 'team_notifications', ['created_at'])
        op.create_index('ix_team_notifications_user_unread', 'team_notifications', ['user_id', 'is_read'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('team_notifications')
    op.drop_table('member_skills')
    op.drop_table('task_time_logs')
    op.drop_table('code_reviews')
    op.drop_table('team_chat_messages')
    op.drop_table('team_activities')
    op.drop_table('task_comments')

    # Remove milestone_id from team_tasks
    op.drop_constraint('fk_team_tasks_milestone', 'team_tasks', type_='foreignkey')
    op.drop_index('ix_team_tasks_milestone_id', table_name='team_tasks')
    op.drop_column('team_tasks', 'milestone_id')

    op.drop_table('team_milestones')

    # Drop enum types
    sa.Enum(name='milestonestatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='notificationtype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='reviewstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='activitytype').drop(op.get_bind(), checkfirst=True)
