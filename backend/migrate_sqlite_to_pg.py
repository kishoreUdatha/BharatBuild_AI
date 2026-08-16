"""
Migrate all data from SQLite (test_bharatbuild.db) to PostgreSQL (Docker port 5433)
Handles: boolean conversion, FK ordering, type mismatches
"""
import sqlite3
import psycopg2

SQLITE_PATH = "test_bharatbuild.db"
PG_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "bharatbuild_db",
    "user": "bharatbuild",
    "password": "bharatbuild123"
}

# Order matters for FK constraints
TABLE_ORDER = [
    "users",
    "projects",
    "project_files",
    "project_messages",
    "token_balances",
    "token_usage",
    "token_usage_logs",
]

def get_pg_column_types(pg_conn, table_name):
    """Get column names and types from PostgreSQL"""
    cur = pg_conn.cursor()
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = %s AND table_schema = 'public'
        ORDER BY ordinal_position
    """, (table_name,))
    return {row[0]: row[1] for row in cur.fetchall()}

def get_table_columns(sqlite_conn, table_name):
    """Get column names for a SQLite table"""
    cur = sqlite_conn.cursor()
    cur.execute(f"PRAGMA table_info([{table_name}])")
    return [row[1] for row in cur.fetchall()]

def convert_value(val, pg_type):
    """Convert a SQLite value to PostgreSQL-compatible type"""
    if val is None:
        return None
    if pg_type == 'boolean':
        if isinstance(val, int):
            return True if val else False
        if isinstance(val, str):
            return val.lower() in ('1', 'true', 'yes')
        return bool(val)
    if pg_type in ('jsonb', 'json'):
        if isinstance(val, str):
            return val
        return str(val) if val else None
    if isinstance(val, bytes):
        try:
            return val.decode('utf-8')
        except:
            return val
    return val

def migrate_table(sqlite_conn, pg_conn, table_name):
    """Migrate a single table with type conversion"""
    sqlite_cur = sqlite_conn.cursor()
    pg_cur = pg_conn.cursor()
    
    # Get columns and types
    sqlite_cols = get_table_columns(sqlite_conn, table_name)
    pg_col_types = get_pg_column_types(pg_conn, table_name)
    
    if not pg_col_types:
        print(f"  [SKIP] Table '{table_name}' not in PostgreSQL")
        return 0
    
    # Common columns only
    common_cols = [c for c in sqlite_cols if c in pg_col_types]
    if not common_cols:
        print(f"  [SKIP] No common columns")
        return 0
    
    # Fetch all data
    cols_str = ", ".join([f"[{c}]" for c in common_cols])
    sqlite_cur.execute(f"SELECT {cols_str} FROM [{table_name}]")
    rows = sqlite_cur.fetchall()
    
    if not rows:
        return 0
    
    # Disable FK checks temporarily, clear table
    pg_cur.execute("SET session_replication_role = 'replica';")
    pg_cur.execute(f'DELETE FROM "{table_name}"')
    
    # Build INSERT
    pg_cols_str = ", ".join([f'"{c}"' for c in common_cols])
    placeholders = ", ".join(["%s"] * len(common_cols))
    insert_sql = f'INSERT INTO "{table_name}" ({pg_cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
    
    inserted = 0
    errors = 0
    for row in rows:
        converted = []
        for i, val in enumerate(row):
            col_name = common_cols[i]
            pg_type = pg_col_types.get(col_name, 'text')
            converted.append(convert_value(val, pg_type))
        
        try:
            pg_cur.execute(insert_sql, converted)
            inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 2:
                print(f"    ERR: {str(e)[:120]}")
            pg_conn.rollback()
            pg_cur.execute("SET session_replication_role = 'replica';")
    
    # Re-enable FK checks
    pg_cur.execute("SET session_replication_role = 'origin';")
    pg_conn.commit()
    
    return inserted, errors

def main():
    print("=" * 50)
    print("SQLite -> PostgreSQL Migration")
    print("=" * 50)
    
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    pg_conn = psycopg2.connect(**PG_CONFIG)
    pg_conn.autocommit = False
    
    # Get tables with data
    cur = sqlite_conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version'")
    all_tables = [r[0] for r in cur.fetchall()]
    
    # Count rows
    table_counts = {}
    for t in all_tables:
        cur.execute(f"SELECT COUNT(*) FROM [{t}]")
        count = cur.fetchone()[0]
        if count > 0:
            table_counts[t] = count
    
    print(f"\nTables with data: {len(table_counts)}")
    for t, c in table_counts.items():
        print(f"  {t}: {c} rows")
    
    # Migrate in FK order first, then remaining
    ordered = [t for t in TABLE_ORDER if t in table_counts]
    remaining = [t for t in table_counts if t not in TABLE_ORDER]
    migration_order = ordered + remaining
    
    print(f"\nMigration order: {migration_order}")
    print("-" * 50)
    
    total_inserted = 0
    total_errors = 0
    
    for table_name in migration_order:
        row_count = table_counts[table_name]
        print(f"\n  {table_name} ({row_count} rows)...", end=" ")
        result = migrate_table(sqlite_conn, pg_conn, table_name)
        if isinstance(result, tuple):
            ins, err = result
        else:
            ins, err = result, 0
        total_inserted += ins
        total_errors += err
        print(f"OK ({ins} inserted, {err} errors)" if err else f"OK ({ins} inserted)")
    
    print("\n" + "=" * 50)
    print(f"DONE: {total_inserted} rows migrated, {total_errors} errors")
    
    # Verify
    pg_cur = pg_conn.cursor()
    for table_name in migration_order:
        pg_cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        count = pg_cur.fetchone()[0]
        print(f"  PG {table_name}: {count} rows")
    
    sqlite_conn.close()
    pg_conn.close()

if __name__ == "__main__":
    main()
