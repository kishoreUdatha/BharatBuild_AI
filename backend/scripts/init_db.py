#!/usr/bin/env python3
"""
Database Initialization Script for BharatBuild AI

This script:
1. Tests database connectivity
2. Runs Alembic migrations
3. Creates any missing tables
4. Seeds initial data if needed

Usage:
    python scripts/init_db.py              # Full init
    python scripts/init_db.py --migrate    # Only run migrations
    python scripts/init_db.py --check      # Only check connectivity
    python scripts/init_db.py --seed       # Run with seed data
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_connection() -> bool:
    """Test database connectivity"""
    print("\n[InitDB] Testing database connection...")

    try:
        from sqlalchemy import create_engine, text
        from app.core.config import settings

        # Convert async URL to sync
        db_url = settings.DATABASE_URL
        if "+asyncpg" in db_url:
            db_url = db_url.replace("+asyncpg", "")
        elif "postgresql+asyncpg" in db_url:
            db_url = db_url.replace("postgresql+asyncpg", "postgresql")

        print(f"[InitDB] Connecting to: {db_url.split('@')[1] if '@' in db_url else 'database'}")

        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()

        print("[InitDB] Database connection successful!")
        return True

    except Exception as e:
        print(f"[InitDB] ERROR: Database connection failed: {e}")
        return False


def run_migrations() -> bool:
    """Run Alembic migrations"""
    print("\n[InitDB] Running database migrations...")

    try:
        from alembic.config import Config
        from alembic import command

        # Find alembic.ini
        backend_dir = Path(__file__).resolve().parent.parent
        alembic_ini = backend_dir / "alembic.ini"

        if not alembic_ini.exists():
            print(f"[InitDB] ERROR: alembic.ini not found at {alembic_ini}")
            return False

        # Change to backend directory
        os.chdir(backend_dir)

        # Create Alembic config
        alembic_cfg = Config(str(alembic_ini))

        # Show current revision
        print("[InitDB] Current database revision:")
        try:
            command.current(alembic_cfg)
        except Exception as e:
            print(f"[InitDB] No current revision (fresh database): {e}")

        # Run upgrade to head
        print("\n[InitDB] Upgrading to latest revision...")
        command.upgrade(alembic_cfg, "head")

        print("[InitDB] Migrations completed successfully!")

        # Show new revision
        print("\n[InitDB] New database revision:")
        command.current(alembic_cfg)

        return True

    except Exception as e:
        print(f"[InitDB] ERROR: Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def create_tables() -> bool:
    """Create database tables using SQLAlchemy"""
    print("\n[InitDB] Creating/verifying database tables...")

    try:
        from app.core.database import Base, engine
        # Import all models to register them
        from app import models  # noqa

        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)

        print("[InitDB] Database tables created/verified!")
        return True

    except Exception as e:
        print(f"[InitDB] ERROR: Table creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def seed_data() -> bool:
    """Seed initial data"""
    print("\n[InitDB] Seeding initial data...")

    try:
        from app.core.database import async_session
        from app.models.user import User
        from app.core.security import get_password_hash
        from sqlalchemy import select

        async with async_session() as session:
            # Check if admin user exists
            result = await session.execute(
                select(User).where(User.email == "admin@bharatbuild.ai")
            )
            existing_admin = result.scalar_one_or_none()

            if not existing_admin:
                # Create admin user
                admin_user = User(
                    email="admin@bharatbuild.ai",
                    hashed_password=get_password_hash("admin123"),  # Change in production!
                    full_name="Admin User",
                    is_active=True,
                    is_superuser=True,
                    role="admin"
                )
                session.add(admin_user)
                await session.commit()
                print("[InitDB] Admin user created (email: admin@bharatbuild.ai)")
            else:
                print("[InitDB] Admin user already exists")

        print("[InitDB] Seed data completed!")
        return True

    except Exception as e:
        print(f"[InitDB] WARNING: Seed data failed: {e}")
        # Don't fail on seed errors
        return True


def show_table_status():
    """Show current table status"""
    print("\n[InitDB] Database Table Status:")
    print("-" * 50)

    try:
        from sqlalchemy import create_engine, inspect
        from app.core.config import settings

        # Convert async URL to sync
        db_url = settings.DATABASE_URL
        if "+asyncpg" in db_url:
            db_url = db_url.replace("+asyncpg", "")
        elif "postgresql+asyncpg" in db_url:
            db_url = db_url.replace("postgresql+asyncpg", "postgresql")

        engine = create_engine(db_url)
        inspector = inspect(engine)

        tables = inspector.get_table_names()
        print(f"Total tables: {len(tables)}")
        print("\nTables:")
        for table in sorted(tables):
            columns = inspector.get_columns(table)
            print(f"  - {table} ({len(columns)} columns)")

    except Exception as e:
        print(f"[InitDB] Could not inspect tables: {e}")


async def main():
    """Main initialization function"""
    parser = argparse.ArgumentParser(description="BharatBuild AI Database Initialization")
    parser.add_argument("--check", action="store_true", help="Only check connectivity")
    parser.add_argument("--migrate", action="store_true", help="Only run migrations")
    parser.add_argument("--tables", action="store_true", help="Only create tables")
    parser.add_argument("--seed", action="store_true", help="Include seed data")
    parser.add_argument("--status", action="store_true", help="Show table status")

    args = parser.parse_args()

    print("=" * 50)
    print("  BharatBuild AI - Database Initialization")
    print("=" * 50)

    success = True

    # Always test connection first
    if not test_connection():
        print("\n[InitDB] FAILED: Cannot connect to database")
        sys.exit(1)

    if args.check:
        print("\n[InitDB] Connection check completed!")
        sys.exit(0)

    if args.status:
        show_table_status()
        sys.exit(0)

    # Run migrations
    if args.migrate or not (args.tables):
        if not run_migrations():
            print("[InitDB] WARNING: Migrations had issues, trying table creation...")
            success = False

    # Create tables (as fallback or if requested)
    if args.tables or not success:
        if not await create_tables():
            print("[InitDB] FAILED: Could not create tables")
            sys.exit(1)

    # Seed data if requested
    if args.seed:
        await seed_data()

    # Show final status
    show_table_status()

    print("\n" + "=" * 50)
    print("  Database Initialization Complete!")
    print("=" * 50)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
