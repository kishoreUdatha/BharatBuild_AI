"""Who connected a batch's repository, and when.

Either the trainer or the batch leader can do it - on a student project the
lead usually owns the repo - so the screen has to say which of them did.

Revision ID: add_integration_actor
Revises: add_git_identities
Create Date: 2026-09-03
"""
import sqlalchemy as sa
from alembic import op

from app.core.types import GUID

revision = 'add_integration_actor'
down_revision = 'add_git_identities'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('batch_integrations',
                  sa.Column('connected_by', GUID(), nullable=True))
    op.add_column('batch_integrations',
                  sa.Column('connected_at', sa.DateTime(), nullable=True))
    op.create_foreign_key('fk_integration_connected_by', 'batch_integrations',
                          'users', ['connected_by'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_integration_connected_by', 'batch_integrations',
                       type_='foreignkey')
    op.drop_column('batch_integrations', 'connected_at')
    op.drop_column('batch_integrations', 'connected_by')
