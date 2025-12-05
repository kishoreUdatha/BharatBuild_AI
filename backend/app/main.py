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
from app.api.v1.router import api_router
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

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")

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

# Add middleware - Allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# GZipMiddleware - but we need to skip it for SSE endpoints
# app.add_middleware(GZipMiddleware, minimum_size=1000)


# Note: We don't use @app.middleware("http") here because it buffers
# streaming responses. The timing headers are added in individual endpoints
# or we skip timing for SSE endpoints.


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
