"""
Deep Health Check Endpoints for Production Reliability

This module provides comprehensive health checks that verify all critical dependencies
before the application accepts traffic. This prevents issues like registration failures
due to undetected database/Redis/email connectivity problems.

Endpoints:
- /health/live  - Basic liveness (app is running)
- /health/ready - Readiness check (all dependencies working)
- /health/deep  - Detailed diagnostics for debugging
"""

from fastapi import APIRouter, HTTPException, status
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio
import time

from app.core.config import settings
from app.core.logging_config import logger


router = APIRouter(prefix="/health", tags=["Health Checks"])


async def check_database() -> Dict[str, Any]:
    """Check database connectivity and basic operations"""
    start = time.time()
    try:
        from app.core.database import get_session_local
        from sqlalchemy import text

        session_factory = get_session_local()
        async with session_factory() as session:
            # Simple query to verify connection
            result = await session.execute(text("SELECT 1 as health"))
            row = result.fetchone()

            # Check if users table exists and is accessible
            try:
                await session.execute(text("SELECT COUNT(*) FROM users LIMIT 1"))
                tables_ok = True
            except Exception:
                tables_ok = False

            latency = (time.time() - start) * 1000
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "connection": "ok",
                "tables_ready": tables_ok,
                "message": "Database connection successful"
            }
    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.error(f"[HealthCheck] Database check failed: {e}")
        return {
            "status": "unhealthy",
            "latency_ms": round(latency, 2),
            "connection": "failed",
            "tables_ready": False,
            "error": str(e),
            "message": "Database connection failed - registration will not work"
        }


async def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity"""
    start = time.time()
    try:
        import redis.asyncio as redis

        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        await client.set("health_check", "ok", ex=10)
        value = await client.get("health_check")
        await client.close()

        latency = (time.time() - start) * 1000
        return {
            "status": "healthy" if value == "ok" else "degraded",
            "latency_ms": round(latency, 2),
            "connection": "ok",
            "message": "Redis connection successful"
        }
    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.warning(f"[HealthCheck] Redis check failed: {e}")
        return {
            "status": "unhealthy",
            "latency_ms": round(latency, 2),
            "connection": "failed",
            "error": str(e),
            "message": "Redis connection failed - rate limiting may not work"
        }


async def check_email_config() -> Dict[str, Any]:
    """Check email service configuration (not actual connectivity)"""
    try:
        if settings.USE_SENDGRID and settings.SENDGRID_API_KEY:
            return {
                "status": "healthy",
                "provider": "sendgrid",
                "configured": True,
                "message": "SendGrid API key configured"
            }
        elif settings.SMTP_USER and settings.SMTP_PASSWORD:
            return {
                "status": "healthy",
                "provider": "smtp",
                "configured": True,
                "host": settings.SMTP_HOST,
                "message": "SMTP credentials configured"
            }
        else:
            return {
                "status": "degraded",
                "provider": "none",
                "configured": False,
                "message": "Email not configured - verification emails will fail"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Email configuration check failed"
        }


async def check_storage() -> Dict[str, Any]:
    """Check S3/MinIO storage configuration"""
    try:
        if settings.USE_MINIO:
            return {
                "status": "healthy",
                "provider": "minio",
                "endpoint": settings.MINIO_ENDPOINT,
                "bucket": settings.effective_bucket_name,
                "configured": bool(settings.AWS_ACCESS_KEY_ID),
                "message": "MinIO configured"
            }
        else:
            return {
                "status": "healthy",
                "provider": "s3",
                "region": settings.AWS_REGION,
                "bucket": settings.effective_bucket_name,
                "configured": bool(settings.AWS_ACCESS_KEY_ID),
                "message": "S3 configured"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Storage configuration check failed"
        }


def check_critical_env_vars() -> Dict[str, Any]:
    """Verify all critical environment variables are set"""
    missing = []
    warnings = []

    # Critical vars that will break registration
    critical_vars = {
        "DATABASE_URL": settings.DATABASE_URL,
        "SECRET_KEY": settings.SECRET_KEY,
        "JWT_SECRET_KEY": settings.JWT_SECRET_KEY,
    }

    # Important vars that should be set for production
    important_vars = {
        "REDIS_URL": settings.REDIS_URL,
        "ANTHROPIC_API_KEY": settings.ANTHROPIC_API_KEY,
    }

    for name, value in critical_vars.items():
        if not value or value in ["CHANGE_ME", "your-secret-key"]:
            missing.append(name)

    for name, value in important_vars.items():
        if not value or "CHANGE_ME" in str(value):
            warnings.append(name)

    if missing:
        return {
            "status": "unhealthy",
            "missing_critical": missing,
            "warnings": warnings,
            "message": f"Missing critical env vars: {', '.join(missing)}"
        }
    elif warnings:
        return {
            "status": "degraded",
            "missing_critical": [],
            "warnings": warnings,
            "message": f"Some env vars not configured: {', '.join(warnings)}"
        }
    else:
        return {
            "status": "healthy",
            "missing_critical": [],
            "warnings": [],
            "message": "All critical environment variables configured"
        }


@router.get("/live")
async def liveness_check():
    """
    Liveness probe - indicates the application is running.

    Use this for Kubernetes/ECS liveness probes.
    Returns 200 if the process is alive.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "app": settings.APP_NAME,
        "version": "1.0.0"
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness probe - indicates the application can handle requests.

    Use this for Kubernetes/ECS readiness probes and load balancer health checks.
    Returns 200 only if all critical dependencies are working.

    CRITICAL: Load balancer should use this endpoint, NOT /health
    If this returns unhealthy, registration and other features will fail.
    """
    # Run all checks in parallel
    db_check, redis_check = await asyncio.gather(
        check_database(),
        check_redis(),
        return_exceptions=True
    )
    # Sync function - call directly
    env_check = check_critical_env_vars()

    # Handle exceptions
    if isinstance(db_check, Exception):
        db_check = {"status": "unhealthy", "error": str(db_check)}
    if isinstance(redis_check, Exception):
        redis_check = {"status": "unhealthy", "error": str(redis_check)}
    if isinstance(env_check, Exception):
        env_check = {"status": "unhealthy", "error": str(env_check)}

    # Determine overall status
    # Database is CRITICAL - without it, registration fails
    is_ready = db_check.get("status") == "healthy" and db_check.get("tables_ready", False)

    response = {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": db_check,
            "redis": redis_check,
            "environment": env_check
        }
    }

    if not is_ready:
        logger.warning(f"[HealthCheck] Readiness check failed: {response}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response
        )

    return response


@router.get("/deep")
async def deep_health_check():
    """
    Deep health check with full diagnostics.

    Use this for debugging and monitoring dashboards.
    Provides detailed information about all dependencies.
    """
    start_time = time.time()

    # Run all checks in parallel
    results = await asyncio.gather(
        check_database(),
        check_redis(),
        check_email_config(),
        check_storage(),
        return_exceptions=True
    )

    db_check, redis_check, email_check, storage_check = results

    # Handle exceptions
    checks = {}
    for name, result in [
        ("database", db_check),
        ("redis", redis_check),
        ("email", email_check),
        ("storage", storage_check)
    ]:
        if isinstance(result, Exception):
            checks[name] = {"status": "unhealthy", "error": str(result)}
        else:
            checks[name] = result

    checks["environment"] = check_critical_env_vars()

    # Calculate overall health
    statuses = [c.get("status", "unknown") for c in checks.values()]
    if "unhealthy" in statuses:
        overall = "unhealthy"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    total_time = (time.time() - start_time) * 1000

    response = {
        "status": overall,
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "total_check_time_ms": round(total_time, 2),
        "checks": checks,
        "registration_ready": (
            checks["database"].get("status") == "healthy" and
            checks["database"].get("tables_ready", False)
        )
    }

    if overall == "unhealthy":
        logger.error(f"[HealthCheck] Deep check unhealthy: {response}")

    return response


@router.get("/registration")
async def registration_health_check():
    """
    Specific health check for registration functionality.

    Verifies all dependencies needed for user registration are working:
    - Database connection and tables
    - Email service (for verification emails)

    Use this to diagnose registration issues.
    """
    db_check = await check_database()
    email_check = await check_email_config()

    can_register = (
        db_check.get("status") == "healthy" and
        db_check.get("tables_ready", False)
    )

    can_send_verification = email_check.get("status") in ["healthy", "degraded"]

    response = {
        "can_register": can_register,
        "can_send_verification_email": can_send_verification,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": db_check,
            "email": email_check
        },
        "troubleshooting": []
    }

    if not can_register:
        if db_check.get("status") != "healthy":
            response["troubleshooting"].append(
                "Database connection failed. Check DATABASE_URL and network connectivity."
            )
        if not db_check.get("tables_ready"):
            response["troubleshooting"].append(
                "Database tables not created. Run /api/v1/create-tables or apply migrations."
            )

    if not can_send_verification:
        response["troubleshooting"].append(
            "Email not configured. Users can still register but won't receive verification emails."
        )

    if not can_register:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response
        )

    return response
