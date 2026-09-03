"""Give an import run the college it belongs to.

An import run rewrites one college's rosters and keeps the uploaded file, so
it is that college's record - but it carried no college at all. The history
query therefore had nothing to filter on, and every faculty account could list
every college's imports and open the uploaded roster behind each one.

Existing rows are backfilled from whoever ran them. A run uploaded by a
platform trainer has no college to inherit and stays null, which the service
reads as "from before this column" and leaves visible to its own college
rather than orphaning it.

Revision ID: import_run_college
Revises: manager_role
"""
import sqlalchemy as sa
from alembic import op

from app.core.types import GUID

revision = 'import_run_college'
down_revision = 'manager_role'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = {c['name'] for c in sa.inspect(bind).get_columns('import_runs')}
    if 'college_id' in existing:
        return

    op.add_column('import_runs',
                  sa.Column('college_id', GUID(), nullable=True))
    op.create_index('ix_import_runs_college_id', 'import_runs', ['college_id'])
    op.create_foreign_key('fk_import_runs_college', 'import_runs', 'colleges',
                          ['college_id'], ['id'], ondelete='SET NULL')

    # From the person who ran it. Their college is the one the roster landed
    # in, because the import service writes every row into the uploader's
    # tenant.
    op.execute("""
        UPDATE import_runs AS r
           SET college_id = u.college_id
          FROM users AS u
         WHERE u.id = r.imported_by_id
           AND u.college_id IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_constraint('fk_import_runs_college', 'import_runs',
                       type_='foreignkey')
    op.drop_index('ix_import_runs_college_id', table_name='import_runs')
    op.drop_column('import_runs', 'college_id')
