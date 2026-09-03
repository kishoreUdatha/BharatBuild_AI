"""Which projects a college runs, and what each one costs.

A college typically runs Major and Minor projects side by side, and a minor
project rarely costs what a major one does. A single `default_project_fee`
would quietly overcharge one of them, and every batch dropdown would offer
project types the college does not run.

Existing colleges are given the two common types, both priced at whatever
their default already was - that is what they were effectively charging, so
nobody's fee changes as a result of this migration.

Revision ID: college_project_types
Revises: college_onboarding
Create Date: 2026-09-12
"""
import json

import sqlalchemy as sa
from alembic import op

revision = 'college_project_types'
down_revision = 'college_onboarding'
branch_labels = None
depends_on = None

DEFAULTS = ["Major Project", "Minor Project"]


def upgrade() -> None:
    op.add_column('colleges', sa.Column(
        'project_types', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('colleges', sa.Column(
        'project_fees', sa.JSON(), nullable=False, server_default='{}'))

    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, default_project_fee, is_self_serve FROM colleges")).fetchall()
    for row in rows:
        if row.is_self_serve:
            # Individual students are not running a college's project cycle.
            continue
        fee = int(row.default_project_fee or 0)
        bind.execute(
            sa.text("UPDATE colleges SET project_types = :types, "
                    "project_fees = :fees WHERE id = :id"),
            {"types": json.dumps(DEFAULTS),
             "fees": json.dumps({t: fee for t in DEFAULTS}),
             "id": row.id})


def downgrade() -> None:
    op.drop_column('colleges', 'project_fees')
    op.drop_column('colleges', 'project_types')
