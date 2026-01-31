"""Add faculty tests tables

Revision ID: faculty_tests_001
Revises:
Create Date: 2026-01-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'faculty_tests_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    op.execute("CREATE TYPE teststatus AS ENUM ('draft', 'scheduled', 'live', 'completed', 'evaluating')")
    op.execute("CREATE TYPE aicontrollevel AS ENUM ('blocked', 'limited', 'hints_only')")
    op.execute("CREATE TYPE testquestiontype AS ENUM ('coding', 'sql', 'ml', 'analytics', 'mcq')")
    op.execute("CREATE TYPE testquestiondifficulty AS ENUM ('easy', 'medium', 'hard')")
    op.execute("CREATE TYPE studentsessionstatus AS ENUM ('not_started', 'active', 'idle', 'suspicious', 'submitted', 'force_submitted')")
    op.execute("CREATE TYPE alertseverity AS ENUM ('low', 'medium', 'high')")

    # Create faculty_tests table
    op.create_table(
        'faculty_tests',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('lab_id', sa.String(36), nullable=True),
        sa.Column('lab_name', sa.String(100), nullable=True),
        sa.Column('faculty_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('duration_minutes', sa.Integer, default=60),
        sa.Column('max_marks', sa.Integer, default=100),
        sa.Column('passing_marks', sa.Integer, default=40),
        sa.Column('ai_control', postgresql.ENUM('blocked', 'limited', 'hints_only', name='aicontrollevel', create_type=False), default='blocked'),
        sa.Column('ai_usage_limit', sa.Integer, default=0),
        sa.Column('enable_tab_switch_detection', sa.Boolean, default=True),
        sa.Column('max_tab_switches', sa.Integer, default=5),
        sa.Column('enable_copy_paste_block', sa.Boolean, default=True),
        sa.Column('randomize_questions', sa.Boolean, default=False),
        sa.Column('randomize_options', sa.Boolean, default=True),
        sa.Column('status', postgresql.ENUM('draft', 'scheduled', 'live', 'completed', 'evaluating', name='teststatus', create_type=False), default='draft'),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('assigned_sections', postgresql.JSON, default=[]),
        sa.Column('total_participants', sa.Integer, default=0),
        sa.Column('submitted_count', sa.Integer, default=0),
        sa.Column('avg_score', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create test_questions table
    op.create_table(
        'test_questions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('test_id', sa.String(36), sa.ForeignKey('faculty_tests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('question_type', postgresql.ENUM('coding', 'sql', 'ml', 'analytics', 'mcq', name='testquestiontype', create_type=False), default='coding'),
        sa.Column('difficulty', postgresql.ENUM('easy', 'medium', 'hard', name='testquestiondifficulty', create_type=False), default='medium'),
        sa.Column('marks', sa.Integer, default=10),
        sa.Column('time_estimate_minutes', sa.Integer, default=15),
        sa.Column('partial_credit', sa.Boolean, default=True),
        sa.Column('options', postgresql.JSON, nullable=True),
        sa.Column('correct_answer', sa.String(500), nullable=True),
        sa.Column('starter_code', sa.Text, nullable=True),
        sa.Column('solution_code', sa.Text, nullable=True),
        sa.Column('test_cases', postgresql.JSON, nullable=True),
        sa.Column('hidden_test_cases', postgresql.JSON, nullable=True),
        sa.Column('topic', sa.String(100), nullable=True),
        sa.Column('tags', postgresql.JSON, default=[]),
        sa.Column('order_index', sa.Integer, default=0),
        sa.Column('source_question_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create test_sessions table
    op.create_table(
        'test_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('test_id', sa.String(36), sa.ForeignKey('faculty_tests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('student_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('student_name', sa.String(100), nullable=True),
        sa.Column('student_roll', sa.String(50), nullable=True),
        sa.Column('student_email', sa.String(255), nullable=True),
        sa.Column('status', postgresql.ENUM('not_started', 'active', 'idle', 'suspicious', 'submitted', 'force_submitted', name='studentsessionstatus', create_type=False), default='not_started'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('time_spent_seconds', sa.Integer, default=0),
        sa.Column('current_question_index', sa.Integer, default=0),
        sa.Column('questions_attempted', sa.Integer, default=0),
        sa.Column('progress_percentage', sa.Float, default=0.0),
        sa.Column('tab_switches', sa.Integer, default=0),
        sa.Column('copy_paste_attempts', sa.Integer, default=0),
        sa.Column('ai_usage_count', sa.Integer, default=0),
        sa.Column('ai_usage_percentage', sa.Float, default=0.0),
        sa.Column('suspicious_activities', postgresql.JSON, default=[]),
        sa.Column('auto_score', sa.Float, nullable=True),
        sa.Column('manual_score', sa.Float, nullable=True),
        sa.Column('total_score', sa.Float, nullable=True),
        sa.Column('percentage', sa.Float, nullable=True),
        sa.Column('is_evaluated', sa.Boolean, default=False),
        sa.Column('evaluated_by', sa.String(36), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('feedback', sa.Text, nullable=True),
        sa.Column('last_activity_description', sa.String(255), default='Not started'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create test_responses table
    op.create_table(
        'test_responses',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('test_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', sa.String(36), sa.ForeignKey('test_questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('answer', sa.Text, nullable=True),
        sa.Column('code', sa.Text, nullable=True),
        sa.Column('language', sa.String(50), nullable=True),
        sa.Column('execution_output', sa.Text, nullable=True),
        sa.Column('test_cases_passed', sa.Integer, default=0),
        sa.Column('test_cases_total', sa.Integer, default=0),
        sa.Column('execution_time_ms', sa.Integer, nullable=True),
        sa.Column('memory_used_kb', sa.Integer, nullable=True),
        sa.Column('is_correct', sa.Boolean, nullable=True),
        sa.Column('auto_score', sa.Float, nullable=True),
        sa.Column('manual_score', sa.Float, nullable=True),
        sa.Column('final_score', sa.Float, nullable=True),
        sa.Column('time_spent_seconds', sa.Integer, default=0),
        sa.Column('attempts', sa.Integer, default=1),
        sa.Column('ai_similarity_score', sa.Float, nullable=True),
        sa.Column('plagiarism_score', sa.Float, nullable=True),
        sa.Column('first_viewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create test_alerts table
    op.create_table(
        'test_alerts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('test_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('severity', postgresql.ENUM('low', 'medium', 'high', name='alertseverity', create_type=False), default='medium'),
        sa.Column('message', sa.String(500), nullable=False),
        sa.Column('details', postgresql.JSON, nullable=True),
        sa.Column('is_resolved', sa.Boolean, default=False),
        sa.Column('resolved_by', sa.String(36), nullable=True),
        sa.Column('resolution_note', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create question_bank table
    op.create_table(
        'question_bank',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('question_type', postgresql.ENUM('coding', 'sql', 'ml', 'analytics', 'mcq', name='testquestiontype', create_type=False), default='coding'),
        sa.Column('difficulty', postgresql.ENUM('easy', 'medium', 'hard', name='testquestiondifficulty', create_type=False), default='medium'),
        sa.Column('faculty_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('lab_id', sa.String(36), nullable=True),
        sa.Column('suggested_marks', sa.Integer, default=10),
        sa.Column('time_estimate_minutes', sa.Integer, default=15),
        sa.Column('options', postgresql.JSON, nullable=True),
        sa.Column('correct_answer', sa.String(500), nullable=True),
        sa.Column('starter_code', sa.Text, nullable=True),
        sa.Column('solution_code', sa.Text, nullable=True),
        sa.Column('test_cases', postgresql.JSON, nullable=True),
        sa.Column('hidden_test_cases', postgresql.JSON, nullable=True),
        sa.Column('topic', sa.String(100), nullable=True),
        sa.Column('tags', postgresql.JSON, default=[]),
        sa.Column('times_used', sa.Integer, default=0),
        sa.Column('avg_score', sa.Float, nullable=True),
        sa.Column('avg_time_taken', sa.Float, nullable=True),
        sa.Column('is_public', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes
    op.create_index('ix_faculty_tests_faculty_id', 'faculty_tests', ['faculty_id'])
    op.create_index('ix_faculty_tests_status', 'faculty_tests', ['status'])
    op.create_index('ix_test_questions_test_id', 'test_questions', ['test_id'])
    op.create_index('ix_test_sessions_test_id', 'test_sessions', ['test_id'])
    op.create_index('ix_test_sessions_student_id', 'test_sessions', ['student_id'])
    op.create_index('ix_test_responses_session_id', 'test_responses', ['session_id'])
    op.create_index('ix_test_alerts_session_id', 'test_alerts', ['session_id'])
    op.create_index('ix_question_bank_faculty_id', 'question_bank', ['faculty_id'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_question_bank_faculty_id')
    op.drop_index('ix_test_alerts_session_id')
    op.drop_index('ix_test_responses_session_id')
    op.drop_index('ix_test_sessions_student_id')
    op.drop_index('ix_test_sessions_test_id')
    op.drop_index('ix_test_questions_test_id')
    op.drop_index('ix_faculty_tests_status')
    op.drop_index('ix_faculty_tests_faculty_id')

    # Drop tables
    op.drop_table('question_bank')
    op.drop_table('test_alerts')
    op.drop_table('test_responses')
    op.drop_table('test_sessions')
    op.drop_table('test_questions')
    op.drop_table('faculty_tests')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS alertseverity")
    op.execute("DROP TYPE IF EXISTS studentsessionstatus")
    op.execute("DROP TYPE IF EXISTS testquestiondifficulty")
    op.execute("DROP TYPE IF EXISTS testquestiontype")
    op.execute("DROP TYPE IF EXISTS aicontrollevel")
    op.execute("DROP TYPE IF EXISTS teststatus")
