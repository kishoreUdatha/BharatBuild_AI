"""Each student's own git identity inside the shared batch repository.

The repository is one per batch; the people committing to it are not, and git
records only whatever email each of them configured locally. This table is the
link from those emails back to a student.

Revision ID: add_git_identities
Revises: add_story_commits
Create Date: 2026-09-02
"""
import sqlalchemy as sa
from alembic import op

from app.core.types import GUID

revision = 'add_git_identities'
down_revision = 'add_story_commits'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'student_git_identities',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('batch_id', GUID(),
                  sa.ForeignKey('project_batches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('student_id', GUID(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(30), nullable=True),
        sa.Column('username', sa.String(120), nullable=True),
        sa.Column('emails', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('verify_code', sa.String(16), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_commit_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('batch_id', 'student_id', name='uq_git_identity_per_student'),
    )
    op.create_index('ix_git_identity_batch', 'student_git_identities', ['batch_id'])
    op.create_index('ix_student_git_identities_student_id',
                    'student_git_identities', ['student_id'])


def downgrade() -> None:
    op.drop_index('ix_student_git_identities_student_id',
                  table_name='student_git_identities')
    op.drop_index('ix_git_identity_batch', table_name='student_git_identities')
    op.drop_table('student_git_identities')
