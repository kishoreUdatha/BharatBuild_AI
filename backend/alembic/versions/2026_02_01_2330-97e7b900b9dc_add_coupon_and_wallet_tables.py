"""Add coupon and wallet tables

Revision ID: 97e7b900b9dc
Revises: campus_drive_002
Create Date: 2026-02-01 23:30:53.882882

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '97e7b900b9dc'
down_revision = 'campus_drive_002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types first
    couponcategory = sa.Enum('STUDENT', 'FACULTY', 'COLLEGE', 'MEDIA', name='couponcategory')
    couponstatus = sa.Enum('ACTIVE', 'INACTIVE', 'EXPIRED', name='couponstatus')
    wallettransactiontype = sa.Enum('CREDIT', 'DEBIT', 'WITHDRAWAL', 'REFUND', name='wallettransactiontype')
    wallettransactionsource = sa.Enum('COUPON_REWARD', 'PURCHASE', 'WITHDRAWAL', 'ADMIN_CREDIT', 'ADMIN_DEBIT', 'REFUND', name='wallettransactionsource')

    # Create coupons table
    op.create_table('coupons',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('owner_id', sa.String(length=36), nullable=False),
        sa.Column('category', couponcategory, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('discount_amount', sa.Integer(), nullable=False, server_default='10000'),
        sa.Column('reward_amount', sa.Integer(), nullable=False, server_default='10000'),
        sa.Column('total_uses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_discount_given', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_reward_earned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', couponstatus, nullable=False, server_default='ACTIVE'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('valid_from', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_coupons_category', 'coupons', ['category'], unique=False)
    op.create_index('ix_coupons_code', 'coupons', ['code'], unique=True)
    op.create_index('ix_coupons_owner', 'coupons', ['owner_id'], unique=False)
    op.create_index('ix_coupons_status', 'coupons', ['status'], unique=False)

    # Create wallets table
    op.create_table('wallets',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('balance', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_earned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_withdrawn', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('ix_wallets_user', 'wallets', ['user_id'], unique=True)

    # Create wallet_transactions table
    op.create_table('wallet_transactions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('wallet_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('transaction_type', wallettransactiontype, nullable=False),
        sa.Column('source', wallettransactionsource, nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('balance_after', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('reference_id', sa.String(length=100), nullable=True),
        sa.Column('reference_type', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_wallet_transactions_source', 'wallet_transactions', ['source'], unique=False)
    op.create_index('ix_wallet_transactions_type', 'wallet_transactions', ['transaction_type'], unique=False)
    op.create_index('ix_wallet_transactions_user', 'wallet_transactions', ['user_id'], unique=False)
    op.create_index('ix_wallet_transactions_wallet', 'wallet_transactions', ['wallet_id'], unique=False)

    # Create coupon_usages table
    op.create_table('coupon_usages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('coupon_id', sa.String(length=36), nullable=False),
        sa.Column('applied_by_id', sa.String(length=36), nullable=False),
        sa.Column('owner_id', sa.String(length=36), nullable=False),
        sa.Column('order_id', sa.String(length=100), nullable=True),
        sa.Column('transaction_id', sa.String(length=36), nullable=True),
        sa.Column('original_amount', sa.Integer(), nullable=False),
        sa.Column('discount_given', sa.Integer(), nullable=False),
        sa.Column('final_amount', sa.Integer(), nullable=False),
        sa.Column('reward_given', sa.Integer(), nullable=False),
        sa.Column('wallet_transaction_id', sa.String(length=36), nullable=True),
        sa.Column('applied_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['applied_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['coupon_id'], ['coupons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['wallet_transaction_id'], ['wallet_transactions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_coupon_usages_coupon', 'coupon_usages', ['coupon_id'], unique=False)
    op.create_index('ix_coupon_usages_order', 'coupon_usages', ['order_id'], unique=False)
    op.create_index('ix_coupon_usages_owner', 'coupon_usages', ['owner_id'], unique=False)
    op.create_index('ix_coupon_usages_user', 'coupon_usages', ['applied_by_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order (respect foreign keys)
    op.drop_index('ix_coupon_usages_user', table_name='coupon_usages')
    op.drop_index('ix_coupon_usages_owner', table_name='coupon_usages')
    op.drop_index('ix_coupon_usages_order', table_name='coupon_usages')
    op.drop_index('ix_coupon_usages_coupon', table_name='coupon_usages')
    op.drop_table('coupon_usages')

    op.drop_index('ix_wallet_transactions_wallet', table_name='wallet_transactions')
    op.drop_index('ix_wallet_transactions_user', table_name='wallet_transactions')
    op.drop_index('ix_wallet_transactions_type', table_name='wallet_transactions')
    op.drop_index('ix_wallet_transactions_source', table_name='wallet_transactions')
    op.drop_table('wallet_transactions')

    op.drop_index('ix_wallets_user', table_name='wallets')
    op.drop_table('wallets')

    op.drop_index('ix_coupons_status', table_name='coupons')
    op.drop_index('ix_coupons_owner', table_name='coupons')
    op.drop_index('ix_coupons_code', table_name='coupons')
    op.drop_index('ix_coupons_category', table_name='coupons')
    op.drop_table('coupons')

    # Drop enum types
    sa.Enum(name='wallettransactionsource').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='wallettransactiontype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='couponstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='couponcategory').drop(op.get_bind(), checkfirst=True)
