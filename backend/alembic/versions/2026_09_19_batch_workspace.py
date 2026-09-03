"""A batch owns its workspace, not one of its students.

`projects.batch_id` gave the team a shared project, but a project hangs off a
workspace and every workspace belonged to one user, with `ondelete=CASCADE`
both from user to workspace and from workspace to project. Filing the team's
project under a member's workspace would therefore have reintroduced exactly
the loss `batch_project` removed: delete that student, lose four people's work.

Revision ID: batch_workspace
Revises: batch_project
"""
import sqlalchemy as sa
from alembic import op

from app.core.types import GUID

revision = 'batch_workspace'
down_revision = 'batch_project'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('workspaces', sa.Column('batch_id', GUID(), nullable=True))
    op.create_index('ix_workspaces_batch_id', 'workspaces', ['batch_id'])
    op.create_unique_constraint('uq_workspace_per_batch', 'workspaces',
                                ['batch_id'])
    op.create_foreign_key('fk_workspaces_batch', 'workspaces',
                          'project_batches', ['batch_id'], ['id'],
                          ondelete='CASCADE')

    op.alter_column('workspaces', 'user_id', existing_type=GUID(),
                    nullable=True)
    op.drop_constraint('workspaces_user_id_fkey', 'workspaces',
                       type_='foreignkey')
    op.create_foreign_key('workspaces_user_id_fkey', 'workspaces', 'users',
                          ['user_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('workspaces_user_id_fkey', 'workspaces',
                       type_='foreignkey')
    op.create_foreign_key('workspaces_user_id_fkey', 'workspaces', 'users',
                          ['user_id'], ['id'], ondelete='CASCADE')
    op.alter_column('workspaces', 'user_id', existing_type=GUID(),
                    nullable=False)

    op.drop_constraint('fk_workspaces_batch', 'workspaces', type_='foreignkey')
    op.drop_constraint('uq_workspace_per_batch', 'workspaces', type_='unique')
    op.drop_index('ix_workspaces_batch_id', table_name='workspaces')
    op.drop_column('workspaces', 'batch_id')
