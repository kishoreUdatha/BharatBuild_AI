# Container port config updated + Bolt.new-style reverse proxy (preview_proxy.py replaces preview.py)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
import time

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging_config import logger
from app.core.middleware import (
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
)
from app.core.rate_limiter import limiter, rate_limit_exceeded_handler
from app.api.v1.router import api_router
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.services.temp_session_storage import temp_storage
from app.services.sandbox_cleanup import sandbox_cleanup
from app.services.fix_executor import execute_fix
from app.api.v1.endpoints.log_stream import log_stream_manager
import app.models  # Import models so metadata knows about them


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    logger.info("Starting BharatBuild AI Platform...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Version: {settings.API_VERSION}")

    # Skip automatic table creation on startup - use /api/v1/create-tables endpoint instead
    # This avoids race conditions between workers when multiple uvicorn workers try to create tables
    logger.info("Skipping automatic table creation - use /api/v1/create-tables endpoint if tables don't exist")

    # Clean up any leftover temp sessions from previous runs
    temp_storage.cleanup_all()
    logger.info("Cleaned up old temp sessions")

    # Start background cleanup task for temp storage
    await temp_storage.start_cleanup_task()
    logger.info("Started temp storage cleanup task (1hr TTL)")

    # Start sandbox cleanup service (Bolt.new style ephemeral storage)
    if settings.SANDBOX_CLEANUP_ENABLED:
        # Configure sandbox cleanup from settings
        sandbox_cleanup.sandbox_path = Path(settings.SANDBOX_PATH)
        sandbox_cleanup.idle_timeout = timedelta(minutes=settings.SANDBOX_IDLE_TIMEOUT_MINUTES)
        sandbox_cleanup.cleanup_interval = timedelta(minutes=settings.SANDBOX_CLEANUP_INTERVAL_MINUTES)
        sandbox_cleanup.min_age = timedelta(minutes=settings.SANDBOX_MIN_AGE_MINUTES)

        await sandbox_cleanup.start()
        logger.info(
            f"Started sandbox cleanup service - "
            f"Path: {settings.SANDBOX_PATH}, "
            f"Idle timeout: {settings.SANDBOX_IDLE_TIMEOUT_MINUTES}min, "
            f"Interval: {settings.SANDBOX_CLEANUP_INTERVAL_MINUTES}min"
        )
    else:
        logger.info("Sandbox cleanup service disabled")

    # ========== AUTO-FIX SETUP (Bolt.new Magic!) ==========
    # Register fix callback so errors are fixed automatically
    log_stream_manager.set_fix_callback(execute_fix)
    logger.info("Auto-fix callback registered - errors will be fixed automatically!")

    yield

    # Shutdown
    logger.info("Shutting down BharatBuild AI Platform...")

    # Stop sandbox cleanup service
    if settings.SANDBOX_CLEANUP_ENABLED:
        await sandbox_cleanup.stop()
        logger.info("Stopped sandbox cleanup service")

    # Stop cleanup task
    temp_storage.stop_cleanup_task()

    # Clean up all temp sessions
    temp_storage.cleanup_all()
    logger.info("Cleaned up all temp sessions")

    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-driven platform for academic projects, code automation, and product building",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Add middleware (order matters - last added runs first)
# 1. Request logging (runs first for all requests)
app.add_middleware(RequestLoggingMiddleware)

# 2. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 3. Request size limit (10MB default)
app.add_middleware(RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024)

# 4. CORS - Allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://localhost:3005",
        "http://localhost:3006",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
        "http://127.0.0.1:3004",
        "http://127.0.0.1:3005",
        "http://127.0.0.1:3006",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*", "X-Request-ID", "X-Response-Time"],
)

# GZipMiddleware - but we need to skip it for SSE endpoints
# app.add_middleware(GZipMiddleware, minimum_size=1000)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


# TEMPORARY: One-time database fix endpoint - DELETE AFTER USE
@app.get("/fix-db-indexes", tags=["Admin"])
async def fix_db_indexes():
    """Drop orphaned indexes and recreate tables - ONE TIME USE"""
    import asyncpg
    from urllib.parse import urlparse

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
        await conn.execute('DROP INDEX IF EXISTS "ix_workspaces_user_id" CASCADE')
        results.append("Dropped ix_workspaces_user_id")

        await conn.execute('DROP INDEX IF EXISTS "ix_workspaces_name" CASCADE')
        results.append("Dropped ix_workspaces_name")

        await conn.execute('DROP INDEX IF EXISTS "ix_projects_user_id" CASCADE')
        results.append("Dropped ix_projects_user_id")

        await conn.execute('DROP INDEX IF EXISTS "ix_users_email" CASCADE')
        results.append("Dropped ix_users_email")

        # Drop all tables
        await conn.execute('DROP TABLE IF EXISTS workspaces CASCADE')
        results.append("Dropped workspaces table")

        await conn.execute('DROP TABLE IF EXISTS projects CASCADE')
        results.append("Dropped projects table")

        await conn.execute('DROP TABLE IF EXISTS chat_messages CASCADE')
        results.append("Dropped chat_messages table")

        await conn.execute('DROP TABLE IF EXISTS users CASCADE')
        results.append("Dropped users table")

        # List remaining objects
        remaining = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        results.append(f"Remaining tables: {[r['tablename'] for r in remaining]}")

        remaining_idx = await conn.fetch("SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname NOT LIKE 'pg_%'")
        results.append(f"Remaining indexes: {[r['indexname'] for r in remaining_idx]}")

    finally:
        await conn.close()

    return {"status": "done", "results": results}


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to BharatBuild AI Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Include API router
app.include_router(api_router, prefix=f"/api/{settings.API_VERSION}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG
    )
