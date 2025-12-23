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
from app.core.database import get_engine, Base, close_db
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


async def validate_critical_config():
    """Validate critical configuration at startup - fail fast if missing"""
    errors = []
    warnings = []

    # Critical: Without these, the app cannot function
    if not settings.DATABASE_URL:
        errors.append("DATABASE_URL is not set")

    if not settings.SECRET_KEY or settings.SECRET_KEY == "CHANGE_ME":
        errors.append("SECRET_KEY is not set or using default value")

    if not settings.JWT_SECRET_KEY or settings.JWT_SECRET_KEY == "CHANGE_ME":
        errors.append("JWT_SECRET_KEY is not set or using default value")

    # Critical for AI generation
    if not settings.ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY is not set - AI generation will NOT work!")

    # Warnings: App can function but some features may not work
    if not settings.REDIS_URL:
        warnings.append("REDIS_URL not set - rate limiting disabled")

    if errors:
        for err in errors:
            logger.critical(f"[Startup] CRITICAL: {err}")
        raise RuntimeError(f"Missing critical configuration: {', '.join(errors)}")

    for warn in warnings:
        logger.warning(f"[Startup] WARNING: {warn}")

    logger.info("[Startup] ✓ Critical configuration validated")
    return True


async def validate_claude_api():
    """Test Claude API connection at startup"""
    try:
        from app.utils.claude_client import ClaudeClient
        client = ClaudeClient()

        logger.info("[Startup] Testing Claude API connection...")
        response = await client.generate(
            prompt="Say OK",
            system_prompt="Respond with only: OK",
            model="haiku",
            max_tokens=10,
            temperature=0
        )

        content = response.get("content", "")
        if content:
            logger.info(f"[Startup] ✓ Claude API connection verified (model: {settings.CLAUDE_HAIKU_MODEL})")
            return True
        else:
            logger.error("[Startup] ✗ Claude API returned empty response")
            return False

    except Exception as e:
        error_msg = str(e).lower()
        if "authentication" in error_msg or "api key" in error_msg or "401" in error_msg:
            logger.critical(f"[Startup] ✗ Claude API key is INVALID: {e}")
            raise RuntimeError("ANTHROPIC_API_KEY is invalid - AI generation will not work!")
        elif "rate" in error_msg or "429" in error_msg:
            logger.warning(f"[Startup] Claude API rate limited (will retry later): {e}")
            return True  # Don't fail startup for rate limits
        else:
            logger.error(f"[Startup] ✗ Claude API connection failed: {e}")
            # Don't fail startup for network issues - might be temporary
            return False


async def ensure_database_ready():
    """Ensure database tables exist - critical for registration to work"""
    from sqlalchemy import text
    from app.core.database import get_session_local, Base, get_engine
    import app.models  # Import all models so metadata knows about them

    try:
        # First, check if users table exists (quick check)
        session_factory = get_session_local()
        async with session_factory() as session:
            try:
                await session.execute(text("SELECT 1 FROM users LIMIT 1"))
                logger.info("[Startup] Database tables already exist")
                return True
            except Exception:
                # Tables don't exist, need to create them
                logger.warning("[Startup] Database tables not found, creating...")

        # Create tables using fresh engine
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("[Startup] Database tables created successfully")
        return True

    except Exception as e:
        logger.error(f"[Startup] Failed to ensure database ready: {e}")
        logger.error("[Startup] Registration and other features may not work!")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    logger.info("=" * 60)
    logger.info("Starting BharatBuild AI Platform...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Version: {settings.API_VERSION}")
    logger.info("=" * 60)

    # Step 1: Validate critical configuration (fail fast!)
    await validate_critical_config()

    # Step 2: Ensure database tables exist (prevents registration failures)
    db_ready = await ensure_database_ready()
    if not db_ready:
        logger.warning("[Startup] Database not ready - some features may fail")

    # Step 3: Validate Claude API connection (critical for AI generation)
    claude_ready = await validate_claude_api()
    if not claude_ready:
        logger.warning("[Startup] Claude API not ready - AI generation may fail")

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

    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-driven platform for academic projects, code automation, and product building",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    redirect_slashes=False  # Prevent 307 redirects that break CORS
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

# 4. CORS - Origins from CORS_ORIGINS_STR in .env
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
