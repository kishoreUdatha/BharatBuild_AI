"""Attendance is taken twice a day, so the register is per session.

Existing rows become forenoon: a single daily register was taken in the
morning, which is the honest reading of what they record.

Revision ID: add_attendance_sessions
Revises: add_integration_actor
Create Date: 2026-09-04
"""
import sqlalchemy as sa
from alembic import op

revision = 'add_attendance_sessions'
down_revision = 'add_integration_actor'
branch_labels = None
depends_on = None

SESSION = sa.Enum('FORENOON', 'AFTERNOON', name='attendancesession')


def upgrade() -> None:
    bind = op.get_bind()
    SESSION.create(bind, checkfirst=True)
    op.add_column('attendance_records',
                  sa.Column('session', SESSION, nullable=False,
                            server_default='FORENOON'))
    op.create_index('ix_attendance_records_session', 'attendance_records', ['session'])
    # The old key allowed one row per day; the new one allows one per session.
    op.drop_constraint('uq_attendance_student_date', 'attendance_records',
                       type_='unique')
    op.create_unique_constraint('uq_attendance_student_session', 'attendance_records',
                                ['student_id', 'attendance_date', 'session'])


def downgrade() -> None:
    # An afternoon row would collide with its morning under the old key, so it
    # goes before the constraint comes back.
    op.execute("DELETE FROM attendance_records WHERE session = 'AFTERNOON'")
    op.drop_constraint('uq_attendance_student_session', 'attendance_records',
                       type_='unique')
    op.create_unique_constraint('uq_attendance_student_date', 'attendance_records',
                                ['student_id', 'attendance_date'])
    op.drop_index('ix_attendance_records_session', table_name='attendance_records')
    op.drop_column('attendance_records', 'session')
    SESSION.drop(op.get_bind(), checkfirst=True)
