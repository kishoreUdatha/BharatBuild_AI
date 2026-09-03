"""Who entered a registration payment, and any note with it.

Null means the student paid online and the gateway recorded it. A name means a
coordinator entered a cash or transfer payment on their behalf - which is the
first thing anybody asks when a payment goes missing.

Revision ID: payment_recorded_by
Revises: backfill_enrolments
Create Date: 2026-09-08
"""
import sqlalchemy as sa
from alembic import op

from app.core.types import GUID

revision = 'payment_recorded_by'
down_revision = 'backfill_enrolments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('registration_payments',
                  sa.Column('recorded_by_id', GUID(), nullable=True))
    op.add_column('registration_payments',
                  sa.Column('note', sa.String(200), nullable=True))
    op.create_foreign_key('fk_payment_recorded_by', 'registration_payments',
                          'users', ['recorded_by_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_payment_recorded_by', 'registration_payments',
                       type_='foreignkey')
    op.drop_column('registration_payments', 'note')
    op.drop_column('registration_payments', 'recorded_by_id')
