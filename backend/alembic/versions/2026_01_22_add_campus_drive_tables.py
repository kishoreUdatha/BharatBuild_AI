"""add campus drive tables

Revision ID: campus_drive_001
Revises: 2025_12_14_add_token_transactions
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'campus_drive_001'
down_revision = None  # Will be auto-detected
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE questioncategory AS ENUM ('logical', 'technical', 'ai_ml', 'english')")
    op.execute("CREATE TYPE questiondifficulty AS ENUM ('easy', 'medium', 'hard')")
    op.execute("CREATE TYPE registrationstatus AS ENUM ('registered', 'quiz_in_progress', 'quiz_completed', 'qualified', 'not_qualified')")

    # Create campus_drives table
    op.create_table(
        'campus_drives',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('registration_start', sa.DateTime, default=sa.func.now()),
        sa.Column('registration_end', sa.DateTime, nullable=True),
        sa.Column('quiz_date', sa.DateTime, nullable=True),
        sa.Column('quiz_duration_minutes', sa.Integer, default=60),
        sa.Column('passing_percentage', sa.Float, default=60.0),
        sa.Column('total_questions', sa.Integer, default=30),
        sa.Column('logical_questions', sa.Integer, default=5),
        sa.Column('technical_questions', sa.Integer, default=10),
        sa.Column('ai_ml_questions', sa.Integer, default=10),
        sa.Column('english_questions', sa.Integer, default=5),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create campus_drive_questions table
    op.create_table(
        'campus_drive_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('campus_drive_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campus_drives.id', ondelete='CASCADE'), nullable=True),
        sa.Column('question_text', sa.Text, nullable=False),
        sa.Column('category', sa.Enum('logical', 'technical', 'ai_ml', 'english', name='questioncategory'), nullable=False),
        sa.Column('difficulty', sa.Enum('easy', 'medium', 'hard', name='questiondifficulty'), default='medium'),
        sa.Column('options', postgresql.JSON, nullable=False),
        sa.Column('correct_option', sa.Integer, nullable=False),
        sa.Column('marks', sa.Float, default=1.0),
        sa.Column('is_global', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )

    # Create campus_drive_registrations table
    op.create_table(
        'campus_drive_registrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('campus_drive_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campus_drives.id', ondelete='CASCADE'), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('college_name', sa.String(255), nullable=False),
        sa.Column('department', sa.String(255), nullable=False),
        sa.Column('year_of_study', sa.String(50), nullable=False),
        sa.Column('roll_number', sa.String(50), nullable=True),
        sa.Column('cgpa', sa.Float, nullable=True),
        sa.Column('status', sa.Enum('registered', 'quiz_in_progress', 'quiz_completed', 'qualified', 'not_qualified', name='registrationstatus'), default='registered'),
        sa.Column('quiz_start_time', sa.DateTime, nullable=True),
        sa.Column('quiz_end_time', sa.DateTime, nullable=True),
        sa.Column('quiz_score', sa.Float, nullable=True),
        sa.Column('total_marks', sa.Float, nullable=True),
        sa.Column('percentage', sa.Float, nullable=True),
        sa.Column('is_qualified', sa.Boolean, default=False),
        sa.Column('logical_score', sa.Float, default=0),
        sa.Column('technical_score', sa.Float, default=0),
        sa.Column('ai_ml_score', sa.Float, default=0),
        sa.Column('english_score', sa.Float, default=0),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create campus_drive_responses table
    op.create_table(
        'campus_drive_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('registration_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campus_drive_registrations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campus_drive_questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('selected_option', sa.Integer, nullable=True),
        sa.Column('is_correct', sa.Boolean, default=False),
        sa.Column('marks_obtained', sa.Float, default=0),
        sa.Column('answered_at', sa.DateTime, default=sa.func.now()),
    )

    # Create indexes
    op.create_index('ix_campus_drive_registrations_email', 'campus_drive_registrations', ['email'])
    op.create_index('ix_campus_drive_registrations_drive_id', 'campus_drive_registrations', ['campus_drive_id'])
    op.create_index('ix_campus_drive_questions_category', 'campus_drive_questions', ['category'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_campus_drive_questions_category', table_name='campus_drive_questions')
    op.drop_index('ix_campus_drive_registrations_drive_id', table_name='campus_drive_registrations')
    op.drop_index('ix_campus_drive_registrations_email', table_name='campus_drive_registrations')

    # Drop tables
    op.drop_table('campus_drive_responses')
    op.drop_table('campus_drive_registrations')
    op.drop_table('campus_drive_questions')
    op.drop_table('campus_drives')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS registrationstatus")
    op.execute("DROP TYPE IF EXISTS questiondifficulty")
    op.execute("DROP TYPE IF EXISTS questioncategory")
