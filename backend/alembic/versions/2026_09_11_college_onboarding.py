"""Domains and a default fee on a college, and the self-serve tenant.

`resolve_for_signup` matched a typed college name against the colleges table,
so anybody could type a paying college's name and land inside its tenant. The
domains added here are the replacement: a claim a student cannot simply type.

The SELF-SERVE row is referenced by `self_serve_tenant` but has never existed,
so every unmatched signup got college_id = NULL and failed closed silently.

Revision ID: college_onboarding
Revises: backfill_join_codes
Create Date: 2026-09-11
"""
import sqlalchemy as sa
from alembic import op

revision = 'college_onboarding'
down_revision = 'backfill_join_codes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('colleges', sa.Column(
        'email_domains', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('colleges', sa.Column(
        'default_project_fee', sa.Integer(), nullable=False, server_default='15000'))

    bind = op.get_bind()
    exists = bind.execute(sa.text(
        "SELECT 1 FROM colleges WHERE code = 'SELF-SERVE'")).first()
    if not exists:
        bind.execute(sa.text("""
            INSERT INTO colleges (id, name, code, country, is_active,
                                  is_self_serve, email_domains,
                                  default_project_fee, created_at)
            VALUES (gen_random_uuid(), 'Individual Students', 'SELF-SERVE',
                    'India', true, true, '[]', 0, now())
        """))


def downgrade() -> None:
    op.drop_column('colleges', 'default_project_fee')
    op.drop_column('colleges', 'email_domains')
    # The self-serve row stays: accounts point at it, and removing it would
    # orphan them.
