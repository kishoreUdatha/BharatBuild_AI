"""
Alembic Migration Helpers - Reusable functions for idempotent migrations

Usage in migrations:
    from alembic.helpers import (
        create_enum_safe,
        create_table_safe,
        create_index_safe,
        seed_data_safe
    )

    def upgrade():
        create_enum_safe(op, 'myenum', ['value1', 'value2'])
        create_table_safe(op, 'mytable', '''
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL
        ''')
        create_index_safe(op, 'ix_mytable_name', 'mytable', ['name'])
        seed_data_safe(op, 'mytable', 'name', "INSERT INTO mytable (name) VALUES ('default')")
"""

from alembic import op


def create_enum_safe(operation, enum_name: str, values: list):
    """
    Create an enum type safely (idempotent - won't fail if exists)

    Args:
        operation: The alembic op object
        enum_name: Name of the enum type
        values: List of enum values
    """
    values_str = ", ".join([f"'{v}'" for v in values])
    operation.execute(f"""
        DO $$ BEGIN
            CREATE TYPE {enum_name} AS ENUM ({values_str});
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)


def drop_enum_safe(operation, enum_name: str):
    """
    Drop an enum type safely (idempotent)
    """
    operation.execute(f"DROP TYPE IF EXISTS {enum_name} CASCADE")


def create_table_safe(operation, table_name: str, columns_sql: str):
    """
    Create a table safely using IF NOT EXISTS

    Args:
        operation: The alembic op object
        table_name: Name of the table
        columns_sql: SQL for columns (without CREATE TABLE wrapper)
    """
    operation.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {columns_sql}
        )
    """)


def drop_table_safe(operation, table_name: str):
    """
    Drop a table safely (idempotent)
    """
    operation.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")


def create_index_safe(operation, index_name: str, table_name: str, columns: list):
    """
    Create an index safely using IF NOT EXISTS

    Args:
        operation: The alembic op object
        index_name: Name of the index
        table_name: Name of the table
        columns: List of column names
    """
    columns_str = ", ".join(columns)
    operation.execute(f"""
        CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns_str})
    """)


def drop_index_safe(operation, index_name: str, table_name: str = None):
    """
    Drop an index safely (idempotent)
    """
    if table_name:
        operation.execute(f"DROP INDEX IF EXISTS {index_name}")
    else:
        operation.execute(f"DROP INDEX IF EXISTS {index_name}")


def seed_data_safe(operation, table_name: str, check_column: str, check_value: str, insert_sql: str):
    """
    Insert seed data only if it doesn't exist

    Args:
        operation: The alembic op object
        table_name: Name of the table to check
        check_column: Column to check for existing data
        check_value: Value to check (use SQL string format)
        insert_sql: Full INSERT SQL statement
    """
    operation.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM {table_name} WHERE {check_column} = {check_value}) THEN
                {insert_sql};
            END IF;
        END $$;
    """)


def seed_if_empty(operation, table_name: str, insert_sql: str):
    """
    Insert seed data only if table is empty

    Args:
        operation: The alembic op object
        table_name: Name of the table to check
        insert_sql: Full INSERT SQL statement
    """
    operation.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM {table_name} LIMIT 1) THEN
                {insert_sql};
            END IF;
        END $$;
    """)


def add_column_safe(operation, table_name: str, column_name: str, column_type: str, default: str = None):
    """
    Add a column safely (won't fail if exists)

    Args:
        operation: The alembic op object
        table_name: Name of the table
        column_name: Name of the column
        column_type: SQL type of the column
        default: Optional default value
    """
    default_clause = f" DEFAULT {default}" if default else ""
    operation.execute(f"""
        DO $$
        BEGIN
            ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}{default_clause};
        EXCEPTION
            WHEN duplicate_column THEN null;
        END $$;
    """)


def drop_column_safe(operation, table_name: str, column_name: str):
    """
    Drop a column safely (won't fail if doesn't exist)
    """
    operation.execute(f"""
        ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column_name}
    """)


# Template for new migrations
MIGRATION_TEMPLATE = '''
"""
{description}

Revision ID: {revision_id}
Revises: {down_revision}
Create Date: {create_date}
"""

import sys
from pathlib import Path

# Add alembic directory to path for helpers import
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from helpers import (
    create_enum_safe,
    create_table_safe,
    create_index_safe,
    seed_data_safe,
    seed_if_empty,
    drop_enum_safe,
    drop_table_safe,
    drop_index_safe
)

# revision identifiers, used by Alembic.
revision = '{revision_id}'
down_revision = '{down_revision}'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Example: Create enum
    # create_enum_safe(op, 'mystatus', ['active', 'inactive', 'pending'])

    # Example: Create table
    # create_table_safe(op, 'mytable', """
    #     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    #     name VARCHAR(255) NOT NULL,
    #     status mystatus DEFAULT 'active',
    #     created_at TIMESTAMP DEFAULT NOW()
    # """)

    # Example: Create index
    # create_index_safe(op, 'ix_mytable_name', 'mytable', ['name'])

    # Example: Seed data (only if table is empty)
    # seed_if_empty(op, 'mytable', "INSERT INTO mytable (name) VALUES ('Default')")

    pass


def downgrade() -> None:
    # drop_index_safe(op, 'ix_mytable_name')
    # drop_table_safe(op, 'mytable')
    # drop_enum_safe(op, 'mystatus')
    pass
'''
