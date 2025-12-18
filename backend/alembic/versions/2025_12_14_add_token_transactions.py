"""Add token_transactions table for detailed token tracking

Revision ID: add_token_transactions
Revises: add_file_gen_status
Create Date: 2025-12-14

This migration adds:
- token_transactions table: Detailed per-request token usage tracking
- Matches the TokenTransaction model in app/models/token_balance.py
- Uses String(36) for UUIDs for cross-database compatibility
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'add_token_transactions'
down_revision = 'add_file_gen_status'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if table already exists in the database"""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Skip if table already exists (created by SQLAlchemy create_all or previous run)
    if table_exists('token_transactions'):
        return

    # Create token_transactions table matching TokenTransaction model
    op.create_table(
        'token_transactions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True),

        # Transaction type: usage, purchase, refund, bonus, monthly_reset
        sa.Column('transaction_type', sa.String(50), nullable=False),

        # Token balance tracking
        sa.Column('tokens_before', sa.Integer(), nullable=False),
        sa.Column('tokens_changed', sa.Integer(), nullable=False),
        sa.Column('tokens_after', sa.Integer(), nullable=False),

        # Details
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('agent_type', sa.String(50), nullable=True),
        sa.Column('model_used', sa.String(100), nullable=True),

        # Token breakdown
        sa.Column('input_tokens', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('cache_read_tokens', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('cache_creation_tokens', sa.Integer(), nullable=True, server_default='0'),

        # Cost estimates
        sa.Column('estimated_cost_usd', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('estimated_cost_inr', sa.Integer(), nullable=True, server_default='0'),

        # Metadata
        sa.Column('extra_metadata', sa.JSON(), nullable=True),

        # Timestamp
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create index for created_at (commonly queried)
    op.create_index('ix_token_transactions_created_at', 'token_transactions', ['created_at'])
    op.create_index('ix_token_transactions_user_id', 'token_transactions', ['user_id'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_token_transactions_user_id', table_name='token_transactions')
    op.drop_index('ix_token_transactions_created_at', table_name='token_transactions')

    # Drop table
    op.drop_table('token_transactions')
