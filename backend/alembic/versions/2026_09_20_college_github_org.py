"""Which GitHub organisation a college's project repositories live in.

A batch's repository is created in its own college's organisation, through a
GitHub App that college installs. Per college rather than one shared
namespace: the college keeps its students' work, its member list stays its
own, and handing the organisation over if they leave is a transfer rather than
an extraction.

Both columns are optional. A college that has not installed the App simply
gets no repository created and connects one by hand, exactly as before.

Revision ID: college_github_org
Revises: batch_workspace
"""
import sqlalchemy as sa
from alembic import op

revision = 'college_github_org'
down_revision = 'batch_workspace'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('colleges',
                  sa.Column('github_org', sa.String(120), nullable=True))
    op.add_column('colleges',
                  sa.Column('github_installation_id', sa.String(40),
                            nullable=True))


def downgrade() -> None:
    op.drop_column('colleges', 'github_installation_id')
    op.drop_column('colleges', 'github_org')
