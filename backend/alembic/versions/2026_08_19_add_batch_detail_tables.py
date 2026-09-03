"""add batch registration detail tables

Revision ID: add_batch_detail
Revises: add_import_runs
Create Date: 2026-08-19

Objectives, methodology, scope, technology stack, supporting papers, versioned
documents, approval events and the activity audit log - everything behind the
seven tabs of Batch Registration Details.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'add_batch_detail'
down_revision = 'add_import_runs'
branch_labels = None
depends_on = None

GUID = sa.String(36)

ENUMS = {
    'itemstatus': ['COMPLETE', 'IN_PROGRESS', 'PENDING'],
    'scopekind': ['IN_SCOPE', 'OUT_OF_SCOPE', 'DELIVERABLE', 'OUTCOME'],
    'documentstatus': ['VERIFIED', 'AWAITING_VERIFICATION', 'CHANGES_REQUESTED', 'MISSING'],
    'approvaleventkind': ['SUBMITTED', 'REVIEW_STARTED', 'CHANGES_REQUESTED', 'RESUBMITTED',
                          'DOCUMENTS_VERIFIED', 'FINAL_REVIEW', 'APPROVED', 'REJECTED'],
    'activityseverity': ['INFO', 'SUCCESS', 'WARNING', 'CRITICAL'],
}

# New scalar columns on existing tables: (table, column, type)
NEW_COLUMNS = [
    ('project_batches', 'domain', 'VARCHAR(160)'),
    ('project_batches', 'problem_statement', 'TEXT'),
    ('project_batches', 'keywords', 'VARCHAR(400)'),
    ('project_batches', 'internal_note', 'TEXT'),
    ('project_batches', 'start_date', 'DATE'),
    ('project_batches', 'target_completion', 'DATE'),
    ('project_batches', 'weekly_effort_hours', 'INTEGER'),
    ('project_batch_members', 'responsibility', 'VARCHAR(120)'),
    ('project_batch_members', 'joined_at', 'TIMESTAMP'),
    ('base_papers', 'publisher', 'VARCHAR(160)'),
    ('base_papers', 'publication_type', 'VARCHAR(80)'),
    ('base_papers', 'volume', 'VARCHAR(40)'),
    ('base_papers', 'pages', 'VARCHAR(60)'),
    ('base_papers', 'doi', 'VARCHAR(160)'),
    ('base_papers', 'indexing', 'VARCHAR(160)'),
    ('base_papers', 'quartile', 'VARCHAR(16)'),
    ('base_papers', 'file_name', 'VARCHAR(255)'),
    ('base_papers', 'file_size', 'INTEGER'),
    ('base_papers', 'page_count', 'INTEGER'),
    ('base_papers', 'abstract_summary', 'TEXT'),
    ('base_papers', 'dataset', 'TEXT'),
    ('base_papers', 'improvement_note', 'TEXT'),
    ('base_papers', 'current_limitation', 'TEXT'),
    ('base_papers', 'similarity_percent', 'DOUBLE PRECISION'),
    ('base_papers', 'relevance_score', 'INTEGER'),
    ('base_papers', 'methodology_score', 'INTEGER'),
    ('base_papers', 'recency_score', 'INTEGER'),
    ('base_papers', 'credibility_score', 'INTEGER'),
    ('base_papers', 'faculty_note', 'TEXT'),
    ('base_papers', 'uploaded_by_id', 'VARCHAR(36)'),
    ('base_papers', 'uploaded_at', 'TIMESTAMP'),
]


def _enum(name):
    return postgresql.ENUM(*ENUMS[name], name=name, create_type=False)


def _exists(table):
    return sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    for name, values in ENUMS.items():
        labels = ', '.join(f"'{v}'" for v in values)
        op.execute(f"""
            DO $$ BEGIN
                CREATE TYPE {name} AS ENUM ({labels});
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
        """)

    for table, column, sql_type in NEW_COLUMNS:
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {sql_type}")

    def simple(name, extra):
        if _exists(name):
            return
        op.create_table(
            name,
            sa.Column('id', GUID, primary_key=True),
            sa.Column('batch_id', GUID, sa.ForeignKey('project_batches.id', ondelete='CASCADE'), nullable=False),
            *extra,
        )
        op.create_index(f'ix_{name}_batch_id', name, ['batch_id'])

    simple('project_objectives', [
        sa.Column('position', sa.Integer(), server_default='0'),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('status', _enum('itemstatus'), nullable=False, server_default='PENDING'),
    ])
    simple('project_methodology_steps', [
        sa.Column('position', sa.Integer(), server_default='0'),
        sa.Column('title', sa.String(120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
    ])
    simple('project_scope_items', [
        sa.Column('kind', _enum('scopekind'), nullable=False),
        sa.Column('position', sa.Integer(), server_default='0'),
        sa.Column('text', sa.Text(), nullable=False),
    ])
    simple('project_technologies', [
        sa.Column('layer', sa.String(60), nullable=False),
        sa.Column('name', sa.String(80), nullable=False),
        sa.Column('position', sa.Integer(), server_default='0'),
    ])
    simple('supporting_papers', [
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('authors', sa.String(255), nullable=True),
        sa.Column('source', sa.String(160), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('doi', sa.String(160), nullable=True),
        sa.Column('purpose', sa.String(120), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
    ])
    simple('novel_contributions', [
        sa.Column('position', sa.Integer(), server_default='0'),
        sa.Column('text', sa.Text(), nullable=False),
    ])

    for name in ('paper_metrics', 'paper_key_methods'):
        if _exists(name):
            continue
        cols = [
            sa.Column('id', GUID, primary_key=True),
            sa.Column('base_paper_id', GUID, sa.ForeignKey('base_papers.id', ondelete='CASCADE'), nullable=False),
            sa.Column('name', sa.String(80 if name == 'paper_key_methods' else 40), nullable=False),
            sa.Column('position', sa.Integer(), server_default='0'),
        ]
        if name == 'paper_metrics':
            cols.insert(3, sa.Column('value', sa.String(40), nullable=False))
        op.create_table(name, *cols)
        op.create_index(f'ix_{name}_base_paper_id', name, ['base_paper_id'])

    if not _exists('batch_documents'):
        op.create_table(
            'batch_documents',
            sa.Column('id', GUID, primary_key=True),
            sa.Column('batch_id', GUID, sa.ForeignKey('project_batches.id', ondelete='CASCADE'), nullable=False),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('category', sa.String(80), nullable=False),
            sa.Column('version', sa.String(16), server_default='v1.0'),
            sa.Column('file_size', sa.Integer(), server_default='0'),
            sa.Column('page_count', sa.Integer(), nullable=True),
            sa.Column('mime_type', sa.String(120), nullable=True),
            sa.Column('status', _enum('documentstatus'), nullable=False, server_default='AWAITING_VERIFICATION'),
            sa.Column('is_required', sa.Boolean(), server_default=sa.false()),
            sa.Column('faculty_note', sa.Text(), nullable=True),
            sa.Column('similarity_percent', sa.Float(), nullable=True),
            sa.Column('virus_scan_passed', sa.Boolean(), server_default=sa.true()),
            sa.Column('uploaded_by_id', GUID, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('verified_by_id', GUID, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('verified_at', sa.DateTime(), nullable=True),
            sa.Column('superseded_by_id', GUID, nullable=True),
        )
        for col in ('batch_id', 'category', 'status', 'uploaded_at'):
            op.create_index(f'ix_batch_documents_{col}', 'batch_documents', [col])

    if not _exists('approval_events'):
        op.create_table(
            'approval_events',
            sa.Column('id', GUID, primary_key=True),
            sa.Column('batch_id', GUID, sa.ForeignKey('project_batches.id', ondelete='CASCADE'), nullable=False),
            sa.Column('cycle', sa.Integer(), server_default='1'),
            sa.Column('kind', _enum('approvaleventkind'), nullable=False),
            sa.Column('title', sa.String(160), nullable=False),
            sa.Column('body', sa.Text(), nullable=True),
            sa.Column('status_label', sa.String(60), nullable=True),
            sa.Column('actor_id', GUID, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('actor_role', sa.String(60), nullable=True),
            sa.Column('occurred_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('duration_minutes', sa.Integer(), nullable=True),
            sa.Column('is_private', sa.Boolean(), server_default=sa.false()),
        )
        for col in ('batch_id', 'cycle', 'kind', 'occurred_at'):
            op.create_index(f'ix_approval_events_{col}', 'approval_events', [col])

    if not _exists('activity_logs'):
        op.create_table(
            'activity_logs',
            sa.Column('id', GUID, primary_key=True),
            sa.Column('event_code', sa.String(32), nullable=False, unique=True),
            sa.Column('batch_id', GUID, sa.ForeignKey('project_batches.id', ondelete='CASCADE'), nullable=True),
            sa.Column('actor_id', GUID, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('actor_name', sa.String(120), nullable=True),
            sa.Column('actor_role', sa.String(60), nullable=True),
            sa.Column('activity', sa.String(255), nullable=False),
            sa.Column('module', sa.String(60), nullable=False),
            sa.Column('details', sa.Text(), nullable=True),
            sa.Column('status_label', sa.String(60), nullable=True),
            sa.Column('severity', _enum('activityseverity'), nullable=False, server_default='INFO'),
            sa.Column('ip_address', sa.String(64), nullable=True),
            sa.Column('user_agent', sa.String(255), nullable=True),
            sa.Column('source', sa.String(80), nullable=True),
            sa.Column('occurred_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('changed_field', sa.String(80), nullable=True),
            sa.Column('previous_value', sa.String(255), nullable=True),
            sa.Column('current_value', sa.String(255), nullable=True),
        )
        for col in ('event_code', 'batch_id', 'actor_id', 'module', 'severity', 'occurred_at'):
            op.create_index(f'ix_activity_logs_{col}', 'activity_logs', [col])


def downgrade() -> None:
    for table in ('activity_logs', 'approval_events', 'batch_documents', 'paper_key_methods',
                  'paper_metrics', 'novel_contributions', 'supporting_papers',
                  'project_technologies', 'project_scope_items',
                  'project_methodology_steps', 'project_objectives'):
        op.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
    for table, column, _ in NEW_COLUMNS:
        op.execute(f'ALTER TABLE {table} DROP COLUMN IF EXISTS {column}')
    for name in ENUMS:
        op.execute(f'DROP TYPE IF EXISTS {name}')
