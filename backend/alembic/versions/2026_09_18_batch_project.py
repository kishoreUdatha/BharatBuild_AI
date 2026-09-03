"""One shared project per batch.

Four students on a batch work on one project, the way four developers share
one repository. `projects` had no notion of that: every project had exactly
one owner, so a team either worked in one member's personal project - losing
it if that account went away - or in four unconnected ones.

Two changes. `batch_id` says which batch a project belongs to, uniquely, and
membership of that batch becomes the access rule. `user_id` becomes nullable
and SET NULL, so removing the student who opened the project no longer
cascade-deletes three teammates' work.

Revision ID: batch_project
Revises: department_per_college
"""
import sqlalchemy as sa
from alembic import op

from app.core.types import GUID

revision = 'batch_project'
down_revision = 'department_per_college'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('batch_id', GUID(), nullable=True))
    op.create_index('ix_projects_batch_id', 'projects', ['batch_id'])
    op.create_unique_constraint('uq_project_per_batch', 'projects', ['batch_id'])
    op.create_foreign_key('fk_projects_batch', 'projects', 'project_batches',
                          ['batch_id'], ['id'], ondelete='CASCADE')

    # The owner becomes optional, and stops taking the project with them.
    op.alter_column('projects', 'user_id', existing_type=GUID(), nullable=True)
    op.drop_constraint('projects_user_id_fkey', 'projects', type_='foreignkey')
    op.create_foreign_key('projects_user_id_fkey', 'projects', 'users',
                          ['user_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('projects_user_id_fkey', 'projects', type_='foreignkey')
    op.create_foreign_key('projects_user_id_fkey', 'projects', 'users',
                          ['user_id'], ['id'], ondelete='CASCADE')
    # Only reversible while no project has lost its owner.
    op.alter_column('projects', 'user_id', existing_type=GUID(), nullable=False)

    op.drop_constraint('fk_projects_batch', 'projects', type_='foreignkey')
    op.drop_constraint('uq_project_per_batch', 'projects', type_='unique')
    op.drop_index('ix_projects_batch_id', table_name='projects')
    op.drop_column('projects', 'batch_id')
