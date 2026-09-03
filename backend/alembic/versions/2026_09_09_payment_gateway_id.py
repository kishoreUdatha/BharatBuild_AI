"""Keep the gateway order and payment ids apart on a registration payment.

The order id has to survive, because the webhook arrives naming the order and
has to find the row. The payment id is what a refund is raised against, so it
gets a column of its own instead of overwriting the order.

Revision ID: payment_gateway_id
Revises: payment_recorded_by
Create Date: 2026-09-09
"""
import sqlalchemy as sa
from alembic import op

revision = 'payment_gateway_id'
down_revision = 'payment_recorded_by'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('registration_payments',
                  sa.Column('gateway_payment_id', sa.String(80), nullable=True))
    op.create_index('ix_registration_payments_gateway_payment_id',
                    'registration_payments', ['gateway_payment_id'])


def downgrade() -> None:
    op.drop_index('ix_registration_payments_gateway_payment_id',
                  table_name='registration_payments')
    op.drop_column('registration_payments', 'gateway_payment_id')
