"""A department code belongs to a college, not to the platform.

`uq_department_code_year` was (code, academic_year). The first college to
create a "CSE" therefore owned that code across the whole platform, and no
second college could have one - which every engineering college does. The same
gap let a batch be created against another college's section: the lookup in
batch creation matched on code and year alone, so Vignan's ECE batches were
validated against Sri Guru's ECE.

Revision ID: department_per_college
Revises: import_run_college
"""
from alembic import op

revision = 'department_per_college'
down_revision = 'import_run_college'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint('uq_department_code_year', 'academic_departments',
                       type_='unique')
    op.create_unique_constraint(
        'uq_department_code_year_college', 'academic_departments',
        ['code', 'academic_year', 'college_id'])


def downgrade() -> None:
    # Only reversible while no two colleges share a code in one year.
    op.drop_constraint('uq_department_code_year_college',
                       'academic_departments', type_='unique')
    op.create_unique_constraint('uq_department_code_year',
                                'academic_departments',
                                ['code', 'academic_year'])
