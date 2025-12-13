"""Add token_transactions table for detailed token tracking

Revision ID: add_token_transactions
Revises: add_file_gen_status
Create Date: 2025-12-14

This migration adds:
- token_transactions table: Detailed per-request token usage tracking
- AgentType enum: planner, writer, fixer, verifier, document, etc.
- OperationType enum: plan_project, generate_file, generate_srs, etc.
- Indexes for efficient querying by user, project, and date
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'add_token_transactions'
down_revision = 'add_file_gen_status'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create AgentType enum
    agent_type_enum = sa.Enum(
        'planner', 'writer', 'fixer', 'verifier', 'runner',
        'document', 'enhancer', 'chat', 'other',
        name='agenttype'
    )
    agent_type_enum.create(op.get_bind(), checkfirst=True)

    # Create OperationType enum
    operation_type_enum = sa.Enum(
        'plan_project', 'plan_structure',
        'generate_file', 'generate_batch', 'regenerate_file',
        'fix_error', 'fix_imports', 'auto_fix',
        'verify_code', 'verify_imports',
        'generate_srs', 'generate_report', 'generate_ppt', 'generate_viva', 'generate_uml',
        'chat_message', 'chat_enhance',
        'other',
        name='operationtype'
    )
    operation_type_enum.create(op.get_bind(), checkfirst=True)

    # Create token_transactions table
    op.create_table(
        'token_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('agent_type', sa.Enum('planner', 'writer', 'fixer', 'verifier', 'runner', 'document', 'enhancer', 'chat', 'other', name='agenttype'), nullable=False, server_default='other'),
        sa.Column('operation', sa.Enum('plan_project', 'plan_structure', 'generate_file', 'generate_batch', 'regenerate_file', 'fix_error', 'fix_imports', 'auto_fix', 'verify_code', 'verify_imports', 'generate_srs', 'generate_report', 'generate_ppt', 'generate_viva', 'generate_uml', 'chat_message', 'chat_enhance', 'other', name='operationtype'), nullable=False, server_default='other'),
        sa.Column('model', sa.String(50), nullable=False, server_default='haiku'),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_paise', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes for efficient queries
    op.create_index('ix_token_tx_user_id', 'token_transactions', ['user_id'])
    op.create_index('ix_token_tx_project_id', 'token_transactions', ['project_id'])
    op.create_index('ix_token_tx_created_at', 'token_transactions', ['created_at'])
    op.create_index('ix_token_tx_user_project', 'token_transactions', ['user_id', 'project_id'])
    op.create_index('ix_token_tx_user_date', 'token_transactions', ['user_id', 'created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_token_tx_user_date', table_name='token_transactions')
    op.drop_index('ix_token_tx_user_project', table_name='token_transactions')
    op.drop_index('ix_token_tx_created_at', table_name='token_transactions')
    op.drop_index('ix_token_tx_project_id', table_name='token_transactions')
    op.drop_index('ix_token_tx_user_id', table_name='token_transactions')

    # Drop table
    op.drop_table('token_transactions')

    # Drop enums
    sa.Enum(name='operationtype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='agenttype').drop(op.get_bind(), checkfirst=True)
