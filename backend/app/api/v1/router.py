from fastapi import APIRouter
from app.api.v1.endpoints import auth, projects, api_keys, billing, tokens, streaming, bolt, automation, orchestrator, logs, execution, documents, adventure, resume, download, containers, preview, preview_proxy, jobs, agentic, classify, sync, payments, import_project, paper, feedback, sandbox, workspace, log_stream, retrieval, users, sdk_agents, errors, autofixer_metrics, health, workshop
from app.api.v1.endpoints.admin import admin_router

api_router = APIRouter()

# Include deep health check endpoints (use /health/ready for ALB)
api_router.include_router(health.router)

# Simple health check endpoint for ALB (backward compatible)
# NOTE: For better reliability, configure ALB to use /api/v1/health/ready instead
@api_router.get("/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint for load balancer (backward compatible)"""
    return {"status": "healthy", "service": "bharatbuild-backend"}


# TEMPORARY: Database fix endpoint - DELETE AFTER USE
@api_router.get("/fix-db", tags=["Admin"])
async def fix_database():
    """Drop orphaned indexes, tables, and enum types - ONE TIME USE ONLY"""
    import asyncpg
    from urllib.parse import urlparse
    from app.core.config import settings

    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(db_url)

    conn = await asyncpg.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip("/")
    )

    results = []
    try:
        # Drop all indexes
        for idx in ["ix_workspaces_user_id", "ix_workspaces_name", "ix_projects_user_id", "ix_users_email"]:
            await conn.execute(f'DROP INDEX IF EXISTS "{idx}" CASCADE')
            results.append(f"Dropped index {idx}")

        # Drop all tables
        for tbl in ["chat_messages", "workspaces", "projects", "documents", "uml_diagrams", "users"]:
            await conn.execute(f'DROP TABLE IF EXISTS "{tbl}" CASCADE')
            results.append(f"Dropped table {tbl}")

        # Drop enum types
        for enum_type in ["userrole", "projectmode", "projectstatus"]:
            await conn.execute(f'DROP TYPE IF EXISTS {enum_type} CASCADE')
            results.append(f"Dropped type {enum_type}")

        # List remaining
        remaining = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        results.append(f"Remaining tables: {[r['tablename'] for r in remaining]}")

        remaining_idx = await conn.fetch("SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname NOT LIKE 'pg_%'")
        results.append(f"Remaining indexes: {[r['indexname'] for r in remaining_idx]}")
    finally:
        await conn.close()

    return {"status": "done", "results": results}


# TEMPORARY: Check projects endpoint - DELETE AFTER USE
@api_router.get("/check-projects", tags=["Admin"])
async def check_projects():
    """Check projects in database"""
    import asyncpg
    from urllib.parse import urlparse
    from app.core.config import settings

    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(db_url)

    conn = await asyncpg.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip("/")
    )

    results = {}
    try:
        # Get projects
        projects = await conn.fetch("""
            SELECT id, title, status, s3_path, s3_zip_key, created_at, user_id
            FROM projects
            ORDER BY created_at DESC
            LIMIT 10
        """)
        results["projects"] = [dict(p) for p in projects]
        results["project_count"] = len(projects)

        # Get project files count
        files = await conn.fetch("SELECT COUNT(*) as count FROM project_files")
        results["project_files_count"] = files[0]["count"] if files else 0

        # Get users
        users = await conn.fetch("SELECT id, email FROM users LIMIT 5")
        results["users"] = [dict(u) for u in users]

        # Get documents
        docs = await conn.fetch("""
            SELECT id, project_id, doc_type, title, file_url, file_path, created_at
            FROM documents
            ORDER BY created_at DESC
            LIMIT 10
        """)
        results["documents"] = [dict(d) for d in docs]
        results["documents_count"] = len(docs)

    finally:
        await conn.close()

    return results


# TEMPORARY: Create tables endpoint - DELETE AFTER USE
@api_router.get("/create-tables", tags=["Admin"])
async def create_tables():
    """Create database tables using fresh SQLAlchemy engine to avoid connection pool issues"""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool
    from app.core.database import Base
    import app.models  # Import all models
    import asyncpg
    from urllib.parse import urlparse
    from app.core.config import settings

    results = []

    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(db_url)

    # Step 1: Drop schema via raw connection
    conn = await asyncpg.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip("/")
    )

    try:
        # Drop schema if exists (ignore errors)
        try:
            await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        except Exception:
            pass

        # Create schema
        await conn.execute("CREATE SCHEMA IF NOT EXISTS public")
        await conn.execute("GRANT ALL ON SCHEMA public TO bharatbuild_admin")
        await conn.execute("GRANT ALL ON SCHEMA public TO public")
        results.append("Schema reset done")
    except Exception as e:
        results.append(f"Schema error: {str(e)}")
    finally:
        await conn.close()

    # Step 2: Create fresh engine with NullPool (no connection caching)
    fresh_engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )

    try:
        async with fresh_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        results.append("Tables created via fresh SQLAlchemy engine")

        # Verify
        pg_conn = await asyncpg.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip("/")
        )
        try:
            tables = await pg_conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            results.append(f"Tables: {[r['tablename'] for r in tables]}")
        finally:
            await pg_conn.close()

    except Exception as e:
        results.append(f"Create error: {str(e)}")
    finally:
        await fresh_engine.dispose()

    return {"status": "done", "results": results}

api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(classify.router, prefix="/classify", tags=["Prompt Classification"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["API Keys"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
api_router.include_router(tokens.router, prefix="/tokens", tags=["Token Management"])
api_router.include_router(streaming.router, prefix="/streaming", tags=["Streaming"])
api_router.include_router(bolt.router, tags=["Bolt AI Editor"])
api_router.include_router(automation.router, tags=["Automation Engine"])
api_router.include_router(orchestrator.router, tags=["Dynamic Orchestrator"])
api_router.include_router(logs.router, tags=["Logs"])
api_router.include_router(execution.router, prefix="/execution", tags=["Project Execution"])
api_router.include_router(documents.router, prefix="/documents", tags=["Document Generation"])
api_router.include_router(adventure.router, tags=["Project Adventure"])
api_router.include_router(resume.router, prefix="/resume", tags=["Resume & Recovery"])
api_router.include_router(download.router, prefix="/download", tags=["Download & Temp Storage"])
api_router.include_router(containers.router, tags=["Container Execution"])
# NOTE: Old preview.py removed - replaced by preview_proxy.py (Bolt.new-style reverse proxy w/ Docker internal IP)
api_router.include_router(preview_proxy.router, tags=["Preview Reverse Proxy"])
api_router.include_router(jobs.router, tags=["Job Storage"])
api_router.include_router(agentic.router, tags=["Agentic CLI"])
api_router.include_router(sync.router, tags=["File Sync"])
api_router.include_router(import_project.router, prefix="/import", tags=["Project Import & Analysis"])
api_router.include_router(paper.router, prefix="/paper", tags=["IEEE Paper Analysis"])
api_router.include_router(feedback.router, tags=["User Feedback"])
api_router.include_router(sandbox.router, prefix="/sandbox", tags=["Sandbox Management"])
api_router.include_router(workspace.router, prefix="/workspace", tags=["Workspace Management"])
api_router.include_router(log_stream.router, prefix="/log-stream", tags=["Log Stream WebSocket"])
api_router.include_router(retrieval.router, tags=["Project Retrieval"])
api_router.include_router(users.router, prefix="/users", tags=["User Management"])
api_router.include_router(workshop.router, tags=["Workshop Enrollment"])
api_router.include_router(sdk_agents.router, tags=["SDK Agents"])
api_router.include_router(errors.router, prefix="/errors", tags=["Unified Error Handler"])
api_router.include_router(autofixer_metrics.router, prefix="/autofixer", tags=["Auto-Fixer Metrics"])
api_router.include_router(admin_router)

