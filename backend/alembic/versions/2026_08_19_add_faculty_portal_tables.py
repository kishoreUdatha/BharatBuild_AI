"""add faculty portal tables

Revision ID: add_faculty_portal
Revises: add_student_section
Create Date: 2026-08-19

Sections, project batches, stage progress, reviews, attendance, base papers
and submissions - the tables behind the faculty dashboard.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_faculty_portal'
down_revision = 'add_student_section'
branch_labels = None
depends_on = None


# GUID columns are VARCHAR(36) everywhere in this schema (see app/core/types.py).
GUID = sa.String(36)

ENUM_VALUES = {
    'projectstage': [
        'TOPIC_APPROVAL', 'BASE_PAPER', 'REQUIREMENTS', 'SYSTEM_DESIGN',
        'DEVELOPMENT', 'TESTING', 'DOCUMENTATION', 'FINAL_REVIEW',
    ],
    'attendancestatus': ['PRESENT', 'ABSENT', 'LATE'],
    'reviewstatus': ['SCHEDULED', 'COMPLETED', 'CANCELLED'],
    'basepaperstatus': ['VERIFIED', 'PENDING', 'MISSING'],
    'submissionstatus': ['PENDING', 'VERIFIED', 'REJECTED'],
}


def _enum(name: str):
    """
    Reference an existing type rather than defining it.

    create_type=False matters: without it SQLAlchemy emits CREATE TYPE again
    for every table that uses the enum, which fails once the type exists.
    """
    return postgresql.ENUM(*ENUM_VALUES[name], name=name, create_type=False)


def _table_exists(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    # CREATE TYPE has no IF NOT EXISTS, and app.main runs Base.metadata.create_all
    # on startup, so the types may already be here. Guard each one.
    for name, values in ENUM_VALUES.items():
        labels = ', '.join(f"'{v}'" for v in values)
        op.execute(f"""
            DO $$ BEGIN
                CREATE TYPE {name} AS ENUM ({labels});
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
        """)

    if not _table_exists('student_enrollments'):
        op.create_table(
            'student_enrollments',
            sa.Column('id', GUID, primary_key=True),
            sa.Column('student_id', GUID, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('department', sa.String(100), nullable=False),
            sa.Column('section', sa.String(10), nullable=True),
            sa.Column('year', sa.String(20), nullable=False),
            sa.Column('semester', sa.String(10), nullable=True),
            sa.Column('academic_year', sa.String(20), nullable=False),
            sa.Column('is_registered', sa.Boolean(), server_default=sa.true()),
            sa.Column('is_active', sa.Boolean(), server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('student_id', 'academic_year', name='uq_enrollment_student_year'),
        )
        op.create_index('ix_student_enrollments_student_id', 'student_enrollments', ['student_id'])
        op.create_index('ix_student_enrollments_department', 'student_enrollments', ['department'])
        op.create_index('ix_student_enrollments_section', 'student_enrollments', ['section'])
        op.create_index('ix_student_enrollments_academic_year', 'student_enrollments', ['academic_year'])

    if not _table_exists('project_batches'):
        op.create_table(
            'project_batches',
            sa.Column('id', GUID, primary_key=True),
            sa.Column('batch_code', sa.String(50), nullable=False, unique=True),
            sa.Column('title', sa.String(255), nullable=True),
            sa.Column('department', sa.String(100), nullable=False),
            sa.Column('section', sa.String(10), nullable=True),
            sa.Column('year', sa.String(20), nullable=True),
            sa.Column('semester', sa.String(10), nullable=True),
            sa.Column('academic_year', sa.String(20), nullable=False),
            sa.Column('project_type', sa.String(50), server_default='Major Project'),
            sa.Column('guide_id', GUID, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('overall_progress', sa.Float(), server_default='0'),
            sa.Column('is_active', sa.Boolean(), server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_project_batches_batch_code', 'project_batches', ['batch_code'])
        op.create_index('ix_project_batches_department', 'project_batches', ['department'])
        op.create_index('ix_project_batches_section', 'project_batches', ['section'])
        op.create_index('ix_project_batches_academic_year', 'project_batches', ['academic_year'])
        op.create_index('ix_project_batches_project_type', 'project_batches', ['project_type'])
        op.create_index('ix_project_batches_guide_id', 'project_batches', ['guide_id'])

    if not _table_exists('project_batch_members'):
        op.create_table(
            'project_batch_members',
            sa.Column('id', GUID, primary_key=True),
            sa.Column('batch_id', GUID, sa.ForeignKey('project_batches.id', ondelete='CASCADE'), nullable=False),
            sa.Column('student_id', GUID, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('is_lead', sa.Boolean(), server_default=sa.false()),
            sa.Column('is_active', sa.Boolean(), server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('batch_id', 'student_id', name='uq_batch_member'),
        )
        op.create_index('ix_project_batch_members_batch_id', 'project_batch_members', ['batch_id'])
        op.create_index('ix_project_batch_members_student_id', 'project_batch_members', ['student_id'])

    if not _table_exists('batch_stage_progress'):
        op.create_table(
            'batch_stage_progress',
            sa.Column('id', GUID, primary_key=True),
            sa.Column('batch_id', GUID, sa.ForeignKey('project_batches.id', ondelete='CASCADE'), nullable=False),
            sa.Column('stage', _enum('projectstage'), nullable=False),
            sa.Column('percent', sa.Float(), server_default='0'),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('batch_id', 'stage', name='uq_batch_stage'),
        )
        op.create_index('ix_batch_stage_progress_batch_id', 'batch_stage_progress', ['batch_id'])
        op.create_index('ix_batch_stage_progress_stage', 'batch_stage_progress', ['stage'])

    if not _table_exists('project_reviews'):
        op.create_table(
            'project_reviews',
            sa.Column('id', GUID, primary_key=True),
            sa.Column('batch_id', GUID, sa.ForeignKey('project_batches.id', ondelete='CASCADE'), nullable=False),
            sa.Column('review_type', sa.String(100), nullable=False),
            sa.Column('scheduled_at', sa.DateTime(), nullable=False),
            sa.Column('status', _enum('reviewstatus'), server_default='SCHEDULED'),
            sa.Column('reviewer_id', GUID, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('remarks', sa.Text(), nullable=True),
            sa.Column('score', sa.Float(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_project_reviews_batch_id', 'project_reviews', ['batch_id'])
        op.create_index('ix_project_reviews_scheduled_at', 'project_reviews', ['scheduled_at'])
        op.create_index('ix_project_reviews_status', 'project_reviews', ['status'])

    if not _table_exists('attendance_records'):
        op.create_table(
            'attendance_records',
            sa.Column('id', GUID, primary_key=True),
            sa.Column('student_id', GUID, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('attendance_date', sa.Date(), nullable=False),
            sa.Column('status', _enum('attendancestatus'), nullable=False),
            sa.Column('department', sa.String(100), nullable=True),
            sa.Column('section', sa.String(10), nullable=True),
            sa.Column('academic_year', sa.String(20), nullable=True),
            sa.Column('marked_by_id', GUID, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('student_id', 'attendance_date', name='uq_attendance_student_date'),
        )
        op.create_index('ix_attendance_records_student_id', 'attendance_records', ['student_id'])
        op.create_index('ix_attendance_records_attendance_date', 'attendance_records', ['attendance_date'])
        op.create_index('ix_attendance_records_department', 'attendance_records', ['department'])
        op.create_index('ix_attendance_records_section', 'attendance_records', ['section'])
        op.create_index('ix_attendance_records_academic_year', 'attendance_records', ['academic_year'])

    if not _table_exists('base_papers'):
        op.create_table(
            'base_papers',
            sa.Column('id', GUID, primary_key=True),
            sa.Column('batch_id', GUID, sa.ForeignKey('project_batches.id', ondelete='CASCADE'), nullable=False, unique=True),
            sa.Column('title', sa.String(500), nullable=True),
            sa.Column('authors', sa.String(500), nullable=True),
            sa.Column('publication', sa.String(255), nullable=True),
            sa.Column('year', sa.Integer(), nullable=True),
            sa.Column('url', sa.Text(), nullable=True),
            sa.Column('status', _enum('basepaperstatus'), server_default='MISSING'),
            sa.Column('verified_by_id', GUID, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('verified_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_base_papers_batch_id', 'base_papers', ['batch_id'])
        op.create_index('ix_base_papers_status', 'base_papers', ['status'])

    if not _table_exists('project_submissions'):
        op.create_table(
            'project_submissions',
            sa.Column('id', GUID, primary_key=True),
            sa.Column('batch_id', GUID, sa.ForeignKey('project_batches.id', ondelete='CASCADE'), nullable=False),
            sa.Column('document_type', sa.String(100), nullable=False),
            sa.Column('title', sa.String(500), nullable=True),
            sa.Column('file_url', sa.Text(), nullable=True),
            sa.Column('status', _enum('submissionstatus'), server_default='PENDING'),
            sa.Column('submitted_by_id', GUID, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('submitted_at', sa.DateTime(), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_project_submissions_batch_id', 'project_submissions', ['batch_id'])
        op.create_index('ix_project_submissions_status', 'project_submissions', ['status'])
        op.create_index('ix_project_submissions_submitted_at', 'project_submissions', ['submitted_at'])


def downgrade() -> None:
    for table in (
        'project_submissions',
        'base_papers',
        'attendance_records',
        'project_reviews',
        'batch_stage_progress',
        'project_batch_members',
        'project_batches',
        'student_enrollments',
    ):
        op.execute(f'DROP TABLE IF EXISTS {table} CASCADE')

    for name in ENUM_VALUES:
        op.execute(f'DROP TYPE IF EXISTS {name}')
