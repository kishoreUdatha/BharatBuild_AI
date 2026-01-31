"""Add lab assistance tables

Revision ID: lab_assistance_001
Revises: 2026_01_23_add_coding_columns
Create Date: 2026-01-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'lab_assistance_001'
down_revision = 'campus_drive_002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE branch AS ENUM ('cse', 'it', 'ece', 'eee', 'me', 'ce', 'ai_ml', 'data_science')")
    op.execute("CREATE TYPE semester AS ENUM ('sem_1', 'sem_2', 'sem_3', 'sem_4', 'sem_5', 'sem_6', 'sem_7', 'sem_8')")
    op.execute("CREATE TYPE difficultylevel AS ENUM ('easy', 'medium', 'hard')")
    op.execute("CREATE TYPE questiontype AS ENUM ('mcq', 'coding', 'short_answer')")
    op.execute("CREATE TYPE programminglanguage AS ENUM ('c', 'cpp', 'java', 'python', 'javascript', 'sql', 'shell', 'assembly', 'verilog', 'matlab', 'r', 'go', 'rust', 'kotlin', 'swift', 'dart', 'php', 'ruby', 'typescript', 'html_css')")
    op.execute("CREATE TYPE submissionstatus AS ENUM ('pending', 'running', 'passed', 'failed', 'error', 'timeout')")
    op.execute("CREATE TYPE topicstatus AS ENUM ('not_started', 'in_progress', 'completed')")

    # Create labs table
    op.create_table(
        'labs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('branch', sa.Enum('cse', 'it', 'ece', 'eee', 'me', 'ce', 'ai_ml', 'data_science', name='branch'), nullable=False),
        sa.Column('semester', sa.Enum('sem_1', 'sem_2', 'sem_3', 'sem_4', 'sem_5', 'sem_6', 'sem_7', 'sem_8', name='semester'), nullable=False),
        sa.Column('technologies', postgresql.JSON, nullable=True),
        sa.Column('total_topics', sa.Integer, default=0),
        sa.Column('total_mcqs', sa.Integer, default=0),
        sa.Column('total_coding_problems', sa.Integer, default=0),
        sa.Column('faculty_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_labs_branch', 'labs', ['branch'])
    op.create_index('ix_labs_semester', 'labs', ['semester'])

    # Create lab_topics table
    op.create_table(
        'lab_topics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lab_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('labs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('week_number', sa.Integer, default=1),
        sa.Column('order_index', sa.Integer, default=0),
        sa.Column('concept_content', sa.Text, nullable=True),
        sa.Column('video_url', sa.String(500), nullable=True),
        sa.Column('mcq_count', sa.Integer, default=0),
        sa.Column('coding_count', sa.Integer, default=0),
        sa.Column('prerequisites', postgresql.JSON, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lab_topics_lab_id', 'lab_topics', ['lab_id'])

    # Create lab_mcqs table
    op.create_table(
        'lab_mcqs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lab_topics.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_text', sa.Text, nullable=False),
        sa.Column('options', postgresql.JSON, nullable=False),
        sa.Column('correct_option', sa.Integer, nullable=False),
        sa.Column('explanation', sa.Text, nullable=True),
        sa.Column('difficulty', sa.Enum('easy', 'medium', 'hard', name='difficultylevel'), default='medium'),
        sa.Column('marks', sa.Float, default=1.0),
        sa.Column('time_limit_seconds', sa.Integer, default=60),
        sa.Column('tags', postgresql.JSON, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lab_mcqs_topic_id', 'lab_mcqs', ['topic_id'])

    # Create lab_coding_problems table
    op.create_table(
        'lab_coding_problems',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lab_topics.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('difficulty', sa.Enum('easy', 'medium', 'hard', name='difficultylevel'), default='medium'),
        sa.Column('max_score', sa.Integer, default=100),
        sa.Column('supported_languages', postgresql.JSON, nullable=False),
        sa.Column('starter_code', postgresql.JSON, nullable=True),
        sa.Column('solution_code', postgresql.JSON, nullable=True),
        sa.Column('test_cases', postgresql.JSON, nullable=False),
        sa.Column('time_limit_ms', sa.Integer, default=2000),
        sa.Column('memory_limit_mb', sa.Integer, default=256),
        sa.Column('hints', postgresql.JSON, nullable=True),
        sa.Column('tags', postgresql.JSON, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lab_coding_problems_topic_id', 'lab_coding_problems', ['topic_id'])

    # Create lab_enrollments table
    op.create_table(
        'lab_enrollments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lab_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('labs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('section', sa.String(10), nullable=True),
        sa.Column('overall_progress', sa.Float, default=0.0),
        sa.Column('mcq_score', sa.Float, default=0.0),
        sa.Column('coding_score', sa.Float, default=0.0),
        sa.Column('total_score', sa.Float, default=0.0),
        sa.Column('topics_completed', sa.Integer, default=0),
        sa.Column('mcqs_attempted', sa.Integer, default=0),
        sa.Column('mcqs_correct', sa.Integer, default=0),
        sa.Column('problems_solved', sa.Integer, default=0),
        sa.Column('class_rank', sa.Integer, nullable=True),
        sa.Column('enrolled_at', sa.DateTime, nullable=False),
        sa.Column('last_activity', sa.DateTime, nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lab_enrollments_lab_id', 'lab_enrollments', ['lab_id'])
    op.create_index('ix_lab_enrollments_user_id', 'lab_enrollments', ['user_id'])

    # Create lab_topic_progress table
    op.create_table(
        'lab_topic_progress',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('enrollment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lab_enrollments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lab_topics.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.Enum('not_started', 'in_progress', 'completed', name='topicstatus'), default='not_started'),
        sa.Column('concept_read', sa.Boolean, default=False),
        sa.Column('concept_read_at', sa.DateTime, nullable=True),
        sa.Column('mcq_attempted', sa.Integer, default=0),
        sa.Column('mcq_correct', sa.Integer, default=0),
        sa.Column('mcq_score', sa.Float, default=0.0),
        sa.Column('coding_attempted', sa.Integer, default=0),
        sa.Column('coding_solved', sa.Integer, default=0),
        sa.Column('coding_score', sa.Float, default=0.0),
        sa.Column('progress_percentage', sa.Float, default=0.0),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lab_topic_progress_enrollment_id', 'lab_topic_progress', ['enrollment_id'])
    op.create_index('ix_lab_topic_progress_topic_id', 'lab_topic_progress', ['topic_id'])

    # Create lab_mcq_responses table
    op.create_table(
        'lab_mcq_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('enrollment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lab_enrollments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mcq_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lab_mcqs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('selected_option', sa.Integer, nullable=True),
        sa.Column('is_correct', sa.Boolean, default=False),
        sa.Column('marks_obtained', sa.Float, default=0.0),
        sa.Column('time_taken_seconds', sa.Integer, nullable=True),
        sa.Column('answered_at', sa.DateTime, nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lab_mcq_responses_enrollment_id', 'lab_mcq_responses', ['enrollment_id'])
    op.create_index('ix_lab_mcq_responses_mcq_id', 'lab_mcq_responses', ['mcq_id'])

    # Create lab_coding_submissions table
    op.create_table(
        'lab_coding_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('problem_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lab_coding_problems.id', ondelete='CASCADE'), nullable=False),
        sa.Column('language', sa.Enum('c', 'cpp', 'java', 'python', 'javascript', 'sql', 'shell', 'assembly', 'verilog', 'matlab', 'r', 'go', 'rust', 'kotlin', 'swift', 'dart', 'php', 'ruby', 'typescript', 'html_css', name='programminglanguage'), nullable=False),
        sa.Column('code', sa.Text, nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'passed', 'failed', 'error', 'timeout', name='submissionstatus'), default='pending'),
        sa.Column('test_results', postgresql.JSON, nullable=True),
        sa.Column('tests_passed', sa.Integer, default=0),
        sa.Column('tests_total', sa.Integer, default=0),
        sa.Column('score', sa.Float, default=0.0),
        sa.Column('execution_time_ms', sa.Integer, nullable=True),
        sa.Column('memory_used_mb', sa.Float, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('error_type', sa.String(100), nullable=True),
        sa.Column('submitted_at', sa.DateTime, nullable=False),
        sa.Column('executed_at', sa.DateTime, nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lab_coding_submissions_user_id', 'lab_coding_submissions', ['user_id'])
    op.create_index('ix_lab_coding_submissions_problem_id', 'lab_coding_submissions', ['problem_id'])

    # Create lab_quiz_sessions table
    op.create_table(
        'lab_quiz_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('enrollment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lab_enrollments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lab_topics.id', ondelete='CASCADE'), nullable=False),
        sa.Column('total_questions', sa.Integer, nullable=False),
        sa.Column('time_limit_minutes', sa.Integer, default=15),
        sa.Column('question_ids', postgresql.JSON, nullable=False),
        sa.Column('current_question_index', sa.Integer, default=0),
        sa.Column('answers', postgresql.JSON, nullable=True),
        sa.Column('score', sa.Float, nullable=True),
        sa.Column('correct_count', sa.Integer, nullable=True),
        sa.Column('is_completed', sa.Boolean, default=False),
        sa.Column('started_at', sa.DateTime, nullable=False),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lab_quiz_sessions_enrollment_id', 'lab_quiz_sessions', ['enrollment_id'])
    op.create_index('ix_lab_quiz_sessions_topic_id', 'lab_quiz_sessions', ['topic_id'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('lab_quiz_sessions')
    op.drop_table('lab_coding_submissions')
    op.drop_table('lab_mcq_responses')
    op.drop_table('lab_topic_progress')
    op.drop_table('lab_enrollments')
    op.drop_table('lab_coding_problems')
    op.drop_table('lab_mcqs')
    op.drop_table('lab_topics')
    op.drop_table('labs')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS topicstatus')
    op.execute('DROP TYPE IF EXISTS submissionstatus')
    op.execute('DROP TYPE IF EXISTS programminglanguage')
    op.execute('DROP TYPE IF EXISTS questiontype')
    op.execute('DROP TYPE IF EXISTS difficultylevel')
    op.execute('DROP TYPE IF EXISTS semester')
    op.execute('DROP TYPE IF EXISTS branch')
