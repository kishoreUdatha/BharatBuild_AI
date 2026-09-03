"""add roster import tables

Revision ID: add_import_runs
Revises: add_approval_workflow
Create Date: 2026-08-19

Import runs, their per-row issues and step timeline - the audit trail behind
the Import History tab.
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_import_runs'
down_revision = 'add_approval_workflow'
branch_labels = None
depends_on = None

GUID = sa.String(36)

ENUMS = {
    'importtype': ['STUDENT_LIST', 'BATCH_ALLOCATION', 'PROJECT_DETAILS', 'BASE_PAPER_METADATA'],
    'importstatus': ['PROCESSING', 'SUCCESSFUL', 'PARTIALLY_IMPORTED', 'FAILED'],
    'issueseverity': ['ERROR', 'DUPLICATE'],
}


def _enum(name):
    from sqlalchemy.dialects import postgresql
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

    if not _exists('import_runs'):
        op.create_table(
            'import_runs',
            sa.Column('id', GUID, primary_key=True),
            sa.Column('import_code', sa.String(32), nullable=False, unique=True),
            sa.Column('file_name', sa.String(255), nullable=False),
            sa.Column('file_size', sa.Integer(), server_default='0'),
            sa.Column('file_content', sa.LargeBinary(), nullable=True),
            sa.Column('import_type', _enum('importtype'), nullable=False),
            sa.Column('department', sa.String(100), nullable=True),
            sa.Column('academic_year', sa.String(20), nullable=False),
            sa.Column('status', _enum('importstatus'), nullable=False, server_default='PROCESSING'),
            sa.Column('rows_total', sa.Integer(), server_default='0'),
            sa.Column('rows_imported', sa.Integer(), server_default='0'),
            sa.Column('rows_failed', sa.Integer(), server_default='0'),
            sa.Column('rows_duplicate', sa.Integer(), server_default='0'),
            sa.Column('imported_by_id', GUID, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('is_archived', sa.Boolean(), server_default=sa.false()),
        )
        for col in ('import_code', 'import_type', 'department', 'academic_year',
                    'status', 'imported_by_id', 'started_at', 'is_archived'):
            op.create_index(f'ix_import_runs_{col}', 'import_runs', [col])

    if not _exists('import_row_issues'):
        op.create_table(
            'import_row_issues',
            sa.Column('id', GUID, primary_key=True),
            sa.Column('run_id', GUID, sa.ForeignKey('import_runs.id', ondelete='CASCADE'), nullable=False),
            sa.Column('row_number', sa.Integer(), nullable=False),
            sa.Column('field', sa.String(64), nullable=True),
            sa.Column('message', sa.String(255), nullable=False),
            sa.Column('raw_value', sa.Text(), nullable=True),
            sa.Column('severity', _enum('issueseverity'), nullable=False, server_default='ERROR'),
        )
        op.create_index('ix_import_row_issues_run_id', 'import_row_issues', ['run_id'])

    if not _exists('import_events'):
        op.create_table(
            'import_events',
            sa.Column('id', GUID, primary_key=True),
            sa.Column('run_id', GUID, sa.ForeignKey('import_runs.id', ondelete='CASCADE'), nullable=False),
            sa.Column('step', sa.String(64), nullable=False),
            sa.Column('actor', sa.String(120), nullable=True),
            sa.Column('note', sa.String(255), nullable=True),
            sa.Column('occurred_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('is_warning', sa.Boolean(), server_default=sa.false()),
        )
        op.create_index('ix_import_events_run_id', 'import_events', ['run_id'])


def downgrade() -> None:
    for table in ('import_events', 'import_row_issues', 'import_runs'):
        op.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
    for name in ENUMS:
        op.execute(f'DROP TYPE IF EXISTS {name}')
