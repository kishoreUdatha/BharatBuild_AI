"""Excused status, per-mark remarks, and a submitted-session record.

Revision ID: add_attendance_detail
Revises: add_attendance_sessions
Create Date: 2026-09-05
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.types import GUID

revision = 'add_attendance_detail'
down_revision = 'add_attendance_sessions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Postgres can add an enum value inside a transaction; it just cannot be
    # used until this one commits, which is fine - nothing here writes it.
    op.execute("ALTER TYPE attendancestatus ADD VALUE IF NOT EXISTS 'EXCUSED'")

    op.add_column('attendance_records', sa.Column('remarks', sa.String(300), nullable=True))

    op.create_table(
        'attendance_session_logs',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('college_id', GUID(), sa.ForeignKey('colleges.id'), nullable=False),
        sa.Column('trainer_id', GUID(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('attendance_date', sa.Date(), nullable=False),
        # The type already exists from add_attendance_sessions, so reuse it
        # rather than trying to create it a second time.
        sa.Column('session',
                  postgresql.ENUM('FORENOON', 'AFTERNOON', name='attendancesession',
                                  create_type=False),
                  nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('trainer_id', 'attendance_date', 'session',
                            name='uq_session_log_per_trainer'),
    )
    op.create_index('ix_attendance_session_logs_college_id',
                    'attendance_session_logs', ['college_id'])
    op.create_index('ix_attendance_session_logs_trainer_id',
                    'attendance_session_logs', ['trainer_id'])
    op.create_index('ix_attendance_session_logs_attendance_date',
                    'attendance_session_logs', ['attendance_date'])


def downgrade() -> None:
    op.drop_table('attendance_session_logs')
    op.drop_column('attendance_records', 'remarks')
    # An enum value cannot be removed in Postgres; rows using EXCUSED become
    # ABSENT so the column stays readable if the type is ever rebuilt.
    op.execute("UPDATE attendance_records SET status = 'ABSENT' WHERE status = 'EXCUSED'")
