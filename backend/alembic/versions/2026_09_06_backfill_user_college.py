"""Place existing accounts in the college their work already belongs to.

`users.college_id` is the tenancy key, but almost nothing set it: accounts
created by signing up carried none, and the seeders only set it on staff. The
rows written *for* those users took their college from the batch instead, so
the data looked correct while every query scoped by `tenant_of(user)` skipped
the account entirely.

Nothing is guessed. A student takes the college of the batch they are in; a
guide or reviewer takes the college of the batches they run. An account with
no such link is left alone - it has no institution to infer, and inventing one
would put somebody in a college they do not belong to.

Revision ID: backfill_user_college
Revises: add_attendance_detail
Create Date: 2026-09-06
"""
from alembic import op

revision = 'backfill_user_college'
down_revision = 'add_attendance_detail'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Students: from the active batch they belong to. A student in two batches
    # of different colleges would be a data problem in its own right, so the
    # subquery is bounded to one row rather than picked over.
    op.execute("""
        UPDATE users u
           SET college_id = sub.college_id
          FROM (
                SELECT m.student_id, MIN(b.college_id::text) AS college_id
                  FROM project_batch_members m
                  JOIN project_batches b ON b.id = m.batch_id
                 WHERE b.college_id IS NOT NULL
                 GROUP BY m.student_id
                HAVING COUNT(DISTINCT b.college_id) = 1
               ) AS sub
         WHERE u.id = sub.student_id
           AND u.college_id IS NULL
    """)

    # Staff: from the batches they guide or review.
    op.execute("""
        UPDATE users u
           SET college_id = sub.college_id
          FROM (
                SELECT staff_id, MIN(college_id::text) AS college_id
                  FROM (
                        SELECT guide_id AS staff_id, college_id
                          FROM project_batches
                         WHERE guide_id IS NOT NULL AND college_id IS NOT NULL
                         UNION ALL
                        SELECT reviewer_id, college_id
                          FROM project_batches
                         WHERE reviewer_id IS NOT NULL AND college_id IS NOT NULL
                       ) AS owned
                 GROUP BY staff_id
                HAVING COUNT(DISTINCT college_id) = 1
               ) AS sub
         WHERE u.id = sub.staff_id
           AND u.college_id IS NULL
    """)

    # Students with an enrolment but no batch yet - the department they are
    # enrolled in belongs to a college.
    op.execute("""
        UPDATE users u
           SET college_id = sub.college_id
          FROM (
                SELECT e.student_id, MIN(e.college_id::text) AS college_id
                  FROM student_enrollments e
                 WHERE e.college_id IS NOT NULL
                 GROUP BY e.student_id
                HAVING COUNT(DISTINCT e.college_id) = 1
               ) AS sub
         WHERE u.id = sub.student_id
           AND u.college_id IS NULL
    """)


def downgrade() -> None:
    # Nothing to undo: the column was empty for these rows and clearing it
    # again would only re-create the bug this fixed.
    pass
