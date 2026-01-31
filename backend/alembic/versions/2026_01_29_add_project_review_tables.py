"""Add project review tables

Revision ID: add_project_reviews
Revises:
Create Date: 2026-01-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_project_reviews'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE projecttype AS ENUM ('mini_project', 'major_project')")
    op.execute("CREATE TYPE reviewtype AS ENUM ('review_1', 'review_2', 'review_3', 'final_review')")
    op.execute("CREATE TYPE reviewstatus AS ENUM ('scheduled', 'in_progress', 'completed', 'rescheduled', 'cancelled')")

    # Create student_projects table
    op.create_table(
        'student_projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('project_type', postgresql.ENUM('mini_project', 'major_project', name='projecttype', create_type=False), default='mini_project'),
        sa.Column('technology_stack', sa.String(500), nullable=True),
        sa.Column('domain', sa.String(255), nullable=True),
        sa.Column('team_name', sa.String(255), nullable=True),
        sa.Column('team_size', sa.Integer, default=1),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('guide_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('guide_name', sa.String(255), nullable=True),
        sa.Column('batch', sa.String(50), nullable=True),
        sa.Column('semester', sa.Integer, nullable=True),
        sa.Column('department', sa.String(255), nullable=True),
        sa.Column('github_url', sa.String(500), nullable=True),
        sa.Column('demo_url', sa.String(500), nullable=True),
        sa.Column('documentation_url', sa.String(500), nullable=True),
        sa.Column('current_review', sa.Integer, default=0),
        sa.Column('total_score', sa.Float, default=0.0),
        sa.Column('average_score', sa.Float, default=0.0),
        sa.Column('is_approved', sa.Boolean, default=False),
        sa.Column('is_completed', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create project_team_members table
    op.create_table(
        'project_team_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('student_projects.id'), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('roll_number', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('role', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )

    # Create project_reviews table
    op.create_table(
        'project_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('student_projects.id'), nullable=False),
        sa.Column('review_type', postgresql.ENUM('review_1', 'review_2', 'review_3', 'final_review', name='reviewtype', create_type=False), nullable=False),
        sa.Column('review_number', sa.Integer, nullable=False),
        sa.Column('scheduled_date', sa.DateTime, nullable=False),
        sa.Column('scheduled_time', sa.String(20), nullable=True),
        sa.Column('venue', sa.String(255), nullable=True),
        sa.Column('duration_minutes', sa.Integer, default=30),
        sa.Column('status', postgresql.ENUM('scheduled', 'in_progress', 'completed', 'rescheduled', 'cancelled', name='reviewstatus', create_type=False), default='scheduled'),
        sa.Column('innovation_score', sa.Float, default=0.0),
        sa.Column('technical_score', sa.Float, default=0.0),
        sa.Column('implementation_score', sa.Float, default=0.0),
        sa.Column('documentation_score', sa.Float, default=0.0),
        sa.Column('presentation_score', sa.Float, default=0.0),
        sa.Column('total_score', sa.Float, default=0.0),
        sa.Column('strengths', sa.Text, nullable=True),
        sa.Column('weaknesses', sa.Text, nullable=True),
        sa.Column('suggestions', sa.Text, nullable=True),
        sa.Column('overall_feedback', sa.Text, nullable=True),
        sa.Column('action_items', sa.Text, nullable=True),
        sa.Column('next_review_focus', sa.Text, nullable=True),
        sa.Column('student_present', sa.Boolean, default=True),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
    )

    # Create review_panel_members table
    op.create_table(
        'review_panel_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('review_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_reviews.id'), nullable=False),
        sa.Column('faculty_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('designation', sa.String(255), nullable=True),
        sa.Column('department', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('role', sa.String(50), default='member'),
        sa.Column('is_lead', sa.Boolean, default=False),
        sa.Column('is_present', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )

    # Create review_scores table
    op.create_table(
        'review_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('review_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_reviews.id'), nullable=False),
        sa.Column('panel_member_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('review_panel_members.id'), nullable=False),
        sa.Column('faculty_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('innovation_score', sa.Float, default=0.0),
        sa.Column('technical_score', sa.Float, default=0.0),
        sa.Column('implementation_score', sa.Float, default=0.0),
        sa.Column('documentation_score', sa.Float, default=0.0),
        sa.Column('presentation_score', sa.Float, default=0.0),
        sa.Column('total_score', sa.Float, default=0.0),
        sa.Column('comments', sa.Text, nullable=True),
        sa.Column('private_notes', sa.Text, nullable=True),
        sa.Column('scored_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes
    op.create_index('ix_student_projects_batch', 'student_projects', ['batch'])
    op.create_index('ix_student_projects_semester', 'student_projects', ['semester'])
    op.create_index('ix_student_projects_department', 'student_projects', ['department'])
    op.create_index('ix_project_reviews_scheduled_date', 'project_reviews', ['scheduled_date'])
    op.create_index('ix_project_reviews_status', 'project_reviews', ['status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_project_reviews_status')
    op.drop_index('ix_project_reviews_scheduled_date')
    op.drop_index('ix_student_projects_department')
    op.drop_index('ix_student_projects_semester')
    op.drop_index('ix_student_projects_batch')

    # Drop tables
    op.drop_table('review_scores')
    op.drop_table('review_panel_members')
    op.drop_table('project_reviews')
    op.drop_table('project_team_members')
    op.drop_table('student_projects')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS reviewstatus")
    op.execute("DROP TYPE IF EXISTS reviewtype")
    op.execute("DROP TYPE IF EXISTS projecttype")
