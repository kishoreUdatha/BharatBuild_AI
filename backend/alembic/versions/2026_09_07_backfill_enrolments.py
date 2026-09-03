"""Enrol students who are in a batch but have no enrolment for its year.

Everything on the registration screen is gated on an enrolment, which is
normally created when a coordinator imports the roster. A student who signed
up themselves and joined with a batch code never got one, so the screen told
them their college had not enrolled them while they sat in one of its batches.

Only what the batch already states is written. Nothing is invented, and the
profile stays unverified - joining a batch is not the registration desk
confirming who somebody is.

Revision ID: backfill_enrolments
Revises: backfill_user_college
Create Date: 2026-09-07
"""
from alembic import op

revision = 'backfill_enrolments'
down_revision = 'backfill_user_college'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO student_enrollments (
            id, college_id, student_id, department, section, year, semester,
            academic_year, is_registered, is_active, profile_status, created_at
        )
        SELECT
            gen_random_uuid()::varchar,
            b.college_id,
            m.student_id,
            b.department,
            b.section,
            COALESCE(b.year, '4th Year'),
            b.semester,
            b.academic_year,
            TRUE,
            TRUE,
            'VERIFICATION_PENDING',
            NOW()
          FROM project_batch_members m
          JOIN project_batches b ON b.id = m.batch_id
         WHERE m.is_active
           AND b.college_id IS NOT NULL
           AND NOT EXISTS (
                 SELECT 1 FROM student_enrollments e
                  WHERE e.student_id = m.student_id
                    AND e.academic_year = b.academic_year
               )
        -- A student in two batches of the same year would otherwise violate
        -- uq_enrollment_student_year mid-statement.
        ON CONFLICT (student_id, academic_year) DO NOTHING
    """)


def downgrade() -> None:
    # These rows are indistinguishable from ones a coordinator created, and
    # removing them would put the students back on a screen telling them they
    # are not enrolled. Left in place deliberately.
    pass
