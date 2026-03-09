"""Add subscription reminder tracking fields

Revision ID: add_subscription_reminder
Revises:
Create Date: 2026-03-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_subscription_reminder'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add subscription reminder tracking fields to users table
    op.add_column('users', sa.Column('reminder_2_hour_sent', sa.Boolean(), nullable=True, default=False))
    op.add_column('users', sa.Column('reminder_2_hour_sent_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('reminder_3_day_sent', sa.Boolean(), nullable=True, default=False))
    op.add_column('users', sa.Column('reminder_3_day_sent_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('reminder_7_day_sent', sa.Boolean(), nullable=True, default=False))
    op.add_column('users', sa.Column('reminder_7_day_sent_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'reminder_7_day_sent_at')
    op.drop_column('users', 'reminder_7_day_sent')
    op.drop_column('users', 'reminder_3_day_sent_at')
    op.drop_column('users', 'reminder_3_day_sent')
    op.drop_column('users', 'reminder_2_hour_sent_at')
    op.drop_column('users', 'reminder_2_hour_sent')
