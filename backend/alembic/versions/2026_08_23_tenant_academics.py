"""Extend tenancy to the academic structure.

The first tenancy migration covered the project portal but missed the six
tables in `app/models/academics.py`, which is what the department tree and the
structure CSV are built from - so an outsider could still read another
college's schools, departments, sections, capacities and student-guide ratios.

Only `academic_departments` is a root. The other five reach a college through
`department_id` or `section_id`, so they need no column of their own:

    academic_sections            -> department_id
    section_faculty_assignments  -> section_id
    section_subjects             -> section_id
    department_notices           -> department_id
    section_update_requests      -> department_id

Revision ID: tenant_academics
Revises: add_tenant_isolation
"""

from alembic import op

revision = 'tenant_academics'
down_revision = 'add_tenant_isolation'
branch_labels = None
depends_on = None

HOME_CODE = "SGIT"


def upgrade() -> None:
    op.execute("ALTER TABLE academic_departments ADD COLUMN IF NOT EXISTS college_id VARCHAR(36)")
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_academic_departments_college_id
        ON academic_departments (college_id)
    """)
    op.execute(f"""
        UPDATE academic_departments
        SET college_id = (SELECT id FROM colleges WHERE code = '{HOME_CODE}')
        WHERE college_id IS NULL
    """)
    op.execute("ALTER TABLE academic_departments ALTER COLUMN college_id SET NOT NULL")
    op.execute("""
        ALTER TABLE academic_departments
        ADD CONSTRAINT fk_academic_departments_college
        FOREIGN KEY (college_id) REFERENCES colleges (id) ON DELETE RESTRICT
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE academic_departments DROP CONSTRAINT IF EXISTS fk_academic_departments_college")
    op.execute("DROP INDEX IF EXISTS ix_academic_departments_college_id")
    op.execute("ALTER TABLE academic_departments DROP COLUMN IF EXISTS college_id")
