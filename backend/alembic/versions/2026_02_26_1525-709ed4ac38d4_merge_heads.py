"""merge_heads

Revision ID: 709ed4ac38d4
Revises: binary_mbgl_2025, naac_rbac_001
Create Date: 2026-02-26 15:25:20.928525

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '709ed4ac38d4'
down_revision = ('binary_mbgl_2025', 'naac_rbac_001')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
