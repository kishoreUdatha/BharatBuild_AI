"""Academic structure: departments, sections, faculty roles, subjects, notices.

Sections used to exist only as a string column on enrollments and batches.
These tables give a section the metadata the Departments & Sections screen
needs - capacity, room, timetable, coordinator, publication status - without
taking ownership of the student roster, which stays in student_enrollments.

Everything is guarded with IF NOT EXISTS / duplicate_object because
`main.py` runs `create_all` at startup, so on a freshly bootstrapped
database these objects may already be present when the migration runs.

Revision ID: add_academics
Revises: add_batch_detail
"""

from alembic import op
import sqlalchemy as sa

from app.core.types import GUID

revision = 'add_academics'
down_revision = 'add_batch_detail'
branch_labels = None
depends_on = None


# Labels are the Python enum MEMBER NAMES, uppercase. SQLAlchemy's Enum(PyEnum)
# persists members by name, so a type created from the lowercase *values* is
# rejected on the first insert - which only shows up on a database built by
# alembic before create_all has run.
ENUMS = {
    "sectionstatus": ["PUBLISHED", "DRAFT", "ARCHIVED"],
    "subjectkind": ["CORE", "LAB", "ELECTIVE"],
    "noticeseverity": ["INFO", "WARNING", "CRITICAL"],
    "updaterequeststatus": ["OPEN", "ACKNOWLEDGED", "RESOLVED", "DECLINED"],
}


def _create_enums() -> None:
    for name, values in ENUMS.items():
        labels = ", ".join(f"'{v}'" for v in values)
        op.execute(f"""
            DO $$ BEGIN
                CREATE TYPE {name} AS ENUM ({labels});
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """)


def upgrade() -> None:
    _create_enums()

    op.execute("""
        CREATE TABLE IF NOT EXISTS academic_departments (
            id UUID PRIMARY KEY,
            school VARCHAR(120) NOT NULL,
            code VARCHAR(20) NOT NULL,
            name VARCHAR(160) NOT NULL,
            academic_year VARCHAR(20) NOT NULL,
            hod_id UUID REFERENCES users(id) ON DELETE SET NULL,
            dept_coordinator_id UUID REFERENCES users(id) ON DELETE SET NULL,
            project_coordinator_id UUID REFERENCES users(id) ON DELETE SET NULL,
            display_order INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP,
            CONSTRAINT uq_department_code_year UNIQUE (code, academic_year)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_academic_departments_school ON academic_departments (school);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_academic_departments_code ON academic_departments (code);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_academic_departments_academic_year ON academic_departments (academic_year);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS academic_sections (
            id UUID PRIMARY KEY,
            department_id UUID NOT NULL REFERENCES academic_departments(id) ON DELETE CASCADE,
            year VARCHAR(20) NOT NULL,
            semester VARCHAR(10) NOT NULL,
            name VARCHAR(10) NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 64,
            room VARCHAR(40),
            schedule_days VARCHAR(60),
            schedule_time VARCHAR(60),
            coordinator_id UUID REFERENCES users(id) ON DELETE SET NULL,
            status sectionstatus NOT NULL DEFAULT 'DRAFT',
            timetable_published BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP,
            CONSTRAINT uq_section_dept_year_sem_name UNIQUE (department_id, year, semester, name)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_academic_sections_department_id ON academic_sections (department_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_academic_sections_year ON academic_sections (year);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_academic_sections_semester ON academic_sections (semester);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_academic_sections_name ON academic_sections (name);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_academic_sections_status ON academic_sections (status);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS section_faculty_assignments (
            id UUID PRIMARY KEY,
            section_id UUID NOT NULL REFERENCES academic_sections(id) ON DELETE CASCADE,
            faculty_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role VARCHAR(60) NOT NULL,
            responsibility VARCHAR(160),
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_section_faculty_role UNIQUE (section_id, faculty_id, role)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_section_faculty_section_id ON section_faculty_assignments (section_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_section_faculty_faculty_id ON section_faculty_assignments (faculty_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_section_faculty_role ON section_faculty_assignments (role);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS section_subjects (
            id UUID PRIMARY KEY,
            section_id UUID NOT NULL REFERENCES academic_sections(id) ON DELETE CASCADE,
            code VARCHAR(30),
            title VARCHAR(160) NOT NULL,
            kind subjectkind NOT NULL DEFAULT 'CORE',
            credits INTEGER,
            faculty_id UUID REFERENCES users(id) ON DELETE SET NULL,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_section_subjects_section_id ON section_subjects (section_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_section_subjects_kind ON section_subjects (kind);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS department_notices (
            id UUID PRIMARY KEY,
            department_id UUID NOT NULL REFERENCES academic_departments(id) ON DELETE CASCADE,
            title VARCHAR(200) NOT NULL,
            detail TEXT,
            window_label VARCHAR(80),
            due_at TIMESTAMP,
            severity noticeseverity NOT NULL DEFAULT 'INFO',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_department_notices_department_id ON department_notices (department_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_department_notices_due_at ON department_notices (due_at);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS section_update_requests (
            id UUID PRIMARY KEY,
            section_id UUID REFERENCES academic_sections(id) ON DELETE CASCADE,
            department_id UUID NOT NULL REFERENCES academic_departments(id) ON DELETE CASCADE,
            requested_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            kind VARCHAR(60) NOT NULL,
            note TEXT NOT NULL,
            status updaterequeststatus NOT NULL DEFAULT 'OPEN',
            resolution_note TEXT,
            resolved_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_section_update_requests_section_id ON section_update_requests (section_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_section_update_requests_department_id ON section_update_requests (department_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_section_update_requests_status ON section_update_requests (status);")


def downgrade() -> None:
    for table in ("section_update_requests", "department_notices", "section_subjects",
                  "section_faculty_assignments", "academic_sections", "academic_departments"):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
    for name in ENUMS:
        op.execute(f"DROP TYPE IF EXISTS {name};")
