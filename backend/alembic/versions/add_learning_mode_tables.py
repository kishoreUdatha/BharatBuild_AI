"""Add learning mode tables

Revision ID: add_learning_mode
Revises:
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_learning_mode'
down_revision = None  # Update this to point to the previous migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create project_learning_progress table
    op.create_table(
        'project_learning_progress',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Checkpoint 1: Code Understanding
        sa.Column('checkpoint_1_completed', sa.Boolean(), nullable=True, default=False),
        sa.Column('files_reviewed', postgresql.JSONB(), nullable=True, default=[]),
        sa.Column('explanations_viewed', postgresql.JSONB(), nullable=True, default={}),

        # Checkpoint 2: Concept Quiz
        sa.Column('checkpoint_2_score', sa.Float(), nullable=True),
        sa.Column('checkpoint_2_passed', sa.Boolean(), nullable=True, default=False),
        sa.Column('checkpoint_2_attempts', sa.Integer(), nullable=True, default=0),
        sa.Column('quiz_answers', postgresql.JSONB(), nullable=True, default={}),
        sa.Column('quiz_completed_at', sa.DateTime(), nullable=True),

        # Checkpoint 3: Viva Review
        sa.Column('checkpoint_3_completed', sa.Boolean(), nullable=True, default=False),
        sa.Column('viva_questions_reviewed', sa.Integer(), nullable=True, default=0),
        sa.Column('viva_total_questions', sa.Integer(), nullable=True, default=0),

        # Download eligibility
        sa.Column('can_download', sa.Boolean(), nullable=True, default=False),
        sa.Column('download_unlocked_at', sa.DateTime(), nullable=True),

        # Certificate tracking
        sa.Column('certificate_generated', sa.Boolean(), nullable=True, default=False),
        sa.Column('certificate_id', sa.String(length=100), nullable=True),
        sa.Column('certificate_generated_at', sa.DateTime(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('certificate_id')
    )

    # Create indexes for project_learning_progress
    op.create_index(
        'ix_learning_progress_project_user',
        'project_learning_progress',
        ['project_id', 'user_id'],
        unique=True
    )
    op.create_index(
        'ix_learning_progress_user_id',
        'project_learning_progress',
        ['user_id']
    )

    # Create learning_quiz_questions table
    op.create_table(
        'learning_quiz_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Question content
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(length=50), nullable=True, default='multiple_choice'),
        sa.Column('options', postgresql.JSONB(), nullable=False),
        sa.Column('correct_option', sa.Integer(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),

        # Code context
        sa.Column('related_file', sa.String(length=500), nullable=True),
        sa.Column('code_snippet', sa.Text(), nullable=True),

        # Metadata
        sa.Column('concept', sa.String(length=255), nullable=True),
        sa.Column('difficulty', sa.String(length=50), nullable=True, default='medium'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=True),

        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create index for quiz questions
    op.create_index(
        'ix_quiz_questions_project_id',
        'learning_quiz_questions',
        ['project_id']
    )

    # Create learning_file_explanations table
    op.create_table(
        'learning_file_explanations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),

        # File info
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_language', sa.String(length=50), nullable=True),

        # Explanation content
        sa.Column('simple_explanation', sa.Text(), nullable=True),
        sa.Column('technical_explanation', sa.Text(), nullable=True),
        sa.Column('key_concepts', postgresql.JSONB(), nullable=True, default=[]),

        # Learning aids
        sa.Column('analogies', postgresql.JSONB(), nullable=True, default=[]),
        sa.Column('code_walkthrough', postgresql.JSONB(), nullable=True, default=[]),
        sa.Column('best_practices', postgresql.JSONB(), nullable=True, default=[]),
        sa.Column('common_pitfalls', postgresql.JSONB(), nullable=True, default=[]),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=True),

        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create index for file explanations
    op.create_index(
        'ix_file_explanations_project_file',
        'learning_file_explanations',
        ['project_id', 'file_path']
    )

    # Create learning_certificates table
    op.create_table(
        'learning_certificates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('certificate_id', sa.String(length=100), nullable=False),

        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Student info (snapshot)
        sa.Column('student_name', sa.String(length=255), nullable=False),
        sa.Column('student_email', sa.String(length=255), nullable=False),

        # Project info (snapshot)
        sa.Column('project_title', sa.String(length=500), nullable=False),
        sa.Column('project_domain', sa.String(length=255), nullable=True),
        sa.Column('tech_stack', postgresql.JSONB(), nullable=True, default=[]),

        # Learning metrics
        sa.Column('quiz_score', sa.Float(), nullable=False),
        sa.Column('quiz_attempts', sa.Integer(), nullable=True, default=1),
        sa.Column('files_reviewed', sa.Integer(), nullable=True, default=0),
        sa.Column('viva_questions_reviewed', sa.Integer(), nullable=True, default=0),
        sa.Column('total_learning_time_minutes', sa.Integer(), nullable=True),

        # Certificate file
        sa.Column('pdf_s3_key', sa.String(length=500), nullable=True),

        # Timestamps
        sa.Column('issued_at', sa.DateTime(), nullable=True),

        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('certificate_id')
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('learning_certificates')
    op.drop_index('ix_file_explanations_project_file', table_name='learning_file_explanations')
    op.drop_table('learning_file_explanations')
    op.drop_index('ix_quiz_questions_project_id', table_name='learning_quiz_questions')
    op.drop_table('learning_quiz_questions')
    op.drop_index('ix_learning_progress_user_id', table_name='project_learning_progress')
    op.drop_index('ix_learning_progress_project_user', table_name='project_learning_progress')
    op.drop_table('project_learning_progress')
