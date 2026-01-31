"""Add lab reports and semester progress tables

Revision ID: add_lab_reports
Revises: 2026_01_28_add_lab_assistance_tables
Create Date: 2026-01-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_lab_reports'
down_revision = '2026_01_28_add_lab_assistance_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create lab report status enum
    op.execute("CREATE TYPE labreportstatus AS ENUM ('not_submitted', 'submitted', 'under_review', 'approved', 'rejected', 'resubmit_required')")

    # Create lab_reports table
    op.create_table(
        'lab_reports',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('enrollment_id', sa.String(36), sa.ForeignKey('lab_enrollments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lab_id', sa.String(36), sa.ForeignKey('labs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),

        # Report Details
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),

        # File Upload
        sa.Column('file_url', sa.String(500), nullable=True),
        sa.Column('file_name', sa.String(255), nullable=True),
        sa.Column('file_size', sa.Integer, nullable=True),

        # Status
        sa.Column('status', postgresql.ENUM('not_submitted', 'submitted', 'under_review', 'approved', 'rejected', 'resubmit_required', name='labreportstatus', create_type=False), default='not_submitted'),

        # Faculty Review
        sa.Column('reviewed_by', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('review_comments', sa.Text, nullable=True),
        sa.Column('grade', sa.String(10), nullable=True),
        sa.Column('marks', sa.Float, nullable=True),

        # Submission tracking
        sa.Column('submission_count', sa.Integer, default=0),
        sa.Column('max_submissions', sa.Integer, default=3),

        # Timestamps
        sa.Column('submitted_at', sa.DateTime, nullable=True),
        sa.Column('reviewed_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),

        # Deadline
        sa.Column('deadline', sa.DateTime, nullable=True),
    )

    # Create indexes for lab_reports
    op.create_index('ix_lab_reports_enrollment_id', 'lab_reports', ['enrollment_id'])
    op.create_index('ix_lab_reports_lab_id', 'lab_reports', ['lab_id'])
    op.create_index('ix_lab_reports_user_id', 'lab_reports', ['user_id'])

    # Create semester_progress table
    op.create_table(
        'semester_progress',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('semester', postgresql.ENUM('sem_1', 'sem_2', 'sem_3', 'sem_4', 'sem_5', 'sem_6', 'sem_7', 'sem_8', name='semester', create_type=False), nullable=False),
        sa.Column('branch', postgresql.ENUM('cse', 'it', 'ece', 'eee', 'me', 'ce', 'ai_ml', 'data_science', name='branch', create_type=False), nullable=False),

        # Progress metrics
        sa.Column('total_labs', sa.Integer, default=0),
        sa.Column('labs_completed', sa.Integer, default=0),
        sa.Column('labs_in_progress', sa.Integer, default=0),

        # Reports
        sa.Column('reports_submitted', sa.Integer, default=0),
        sa.Column('reports_approved', sa.Integer, default=0),

        # Overall scores
        sa.Column('average_mcq_score', sa.Float, default=0.0),
        sa.Column('average_coding_score', sa.Float, default=0.0),
        sa.Column('overall_grade', sa.String(10), nullable=True),

        # Status
        sa.Column('is_completed', sa.Boolean, default=False),
        sa.Column('completed_at', sa.DateTime, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create index for semester_progress
    op.create_index('ix_semester_progress_user_id', 'semester_progress', ['user_id'])


def downgrade() -> None:
    op.drop_table('semester_progress')
    op.drop_table('lab_reports')
    op.execute("DROP TYPE labreportstatus")
