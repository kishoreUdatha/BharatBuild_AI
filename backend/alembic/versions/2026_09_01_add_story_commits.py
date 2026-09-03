"""Commits pushed to a batch's repository, linked to stories by key.

Also gives batch_integrations a webhook secret, so a push can be verified as
coming from the repository it claims to.

Revision ID: add_story_commits
Revises: add_story_stages
Create Date: 2026-09-01
"""
import sqlalchemy as sa
from alembic import op

from app.core.types import GUID

revision = 'add_story_commits'
down_revision = 'add_story_stages'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'story_commits',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('batch_id', GUID(),
                  sa.ForeignKey('project_batches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('story_id', GUID(),
                  sa.ForeignKey('project_user_stories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('sha', sa.String(64), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('url', sa.String(500), nullable=True),
        sa.Column('branch', sa.String(200), nullable=True),
        sa.Column('author_name', sa.String(160), nullable=True),
        sa.Column('author_email', sa.String(200), nullable=True),
        sa.Column('author_id', GUID(),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('provider', sa.String(30), nullable=True),
        sa.Column('committed_at', sa.DateTime(), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        # A webhook retry must not double-record the same commit.
        sa.UniqueConstraint('batch_id', 'sha', name='uq_commit_per_batch'),
    )
    op.create_index('ix_story_commits_batch_id', 'story_commits', ['batch_id'])
    op.create_index('ix_story_commits_story_id', 'story_commits', ['story_id'])
    op.create_index('ix_story_commits_sha', 'story_commits', ['sha'])
    op.create_index('ix_story_commits_committed_at', 'story_commits', ['committed_at'])
    op.create_index('ix_story_commits_story_time', 'story_commits',
                    ['story_id', 'committed_at'])

    # The shared secret the repository signs its pushes with.
    op.add_column('batch_integrations', sa.Column('secret', sa.String(80), nullable=True))


def downgrade() -> None:
    op.drop_column('batch_integrations', 'secret')
    op.drop_index('ix_story_commits_story_time', table_name='story_commits')
    op.drop_index('ix_story_commits_committed_at', table_name='story_commits')
    op.drop_index('ix_story_commits_sha', table_name='story_commits')
    op.drop_index('ix_story_commits_story_id', table_name='story_commits')
    op.drop_index('ix_story_commits_batch_id', table_name='story_commits')
    op.drop_table('story_commits')
