"""Add owner_name and owner_email to coupons table

Revision ID: add_owner_name_coupons
Revises: add_coupon_wallet_tables
Create Date: 2024-02-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_owner_name_coupons'
down_revision = '97e7b900b9dc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add owner_name column (required)
    op.add_column('coupons', sa.Column('owner_name', sa.String(100), nullable=True))

    # Add owner_email column (required)
    op.add_column('coupons', sa.Column('owner_email', sa.String(255), nullable=True))

    # Add owner_phone column (required)
    op.add_column('coupons', sa.Column('owner_phone', sa.String(15), nullable=True))

    # Update existing rows to have default values
    op.execute("UPDATE coupons SET owner_name = 'Unknown' WHERE owner_name IS NULL")
    op.execute("UPDATE coupons SET owner_email = 'unknown@example.com' WHERE owner_email IS NULL")
    op.execute("UPDATE coupons SET owner_phone = '0000000000' WHERE owner_phone IS NULL")

    # Make columns NOT NULL after data migration
    op.alter_column('coupons', 'owner_name', nullable=False)
    op.alter_column('coupons', 'owner_email', nullable=False)
    op.alter_column('coupons', 'owner_phone', nullable=False)

    # Make owner_id nullable (no longer required)
    op.alter_column('coupons', 'owner_id', nullable=True)


def downgrade() -> None:
    # Make owner_id required again
    op.alter_column('coupons', 'owner_id', nullable=False)

    # Drop the new columns
    op.drop_column('coupons', 'owner_phone')
    op.drop_column('coupons', 'owner_email')
    op.drop_column('coupons', 'owner_name')
