"""
Auto-Fixer Metrics API Endpoint

Production monitoring for the auto-fixer system.
Provides insights into:
- Fix success/failure rates
- Rate limiting status
- Circuit breaker status
- Cache hit rates
- Per-technology metrics
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any

from app.services.production_autofixer import (
    get_global_metrics,
    _global_rate_limiter,
    _global_circuit_breaker,
    _global_fix_cache,
)
from app.core.logging_config import logger

router = APIRouter()


@router.get("/metrics")
async def get_autofixer_metrics() -> Dict[str, Any]:
    """
    Get production auto-fixer metrics.

    Returns:
    - Global statistics
    - Rate limiter status
    - Circuit breaker status
    - Cache statistics
    """
    try:
        global_metrics = get_global_metrics()

        # Get detailed rate limiter info
        rate_limiter_details = {
            "active_projects": len(_global_rate_limiter._fix_times),
            "max_per_minute": _global_rate_limiter.max_per_minute,
            "max_per_hour": _global_rate_limiter.max_per_hour,
        }

        # Get detailed circuit breaker info
        circuit_breaker_details = {
            "failure_threshold": _global_circuit_breaker.failure_threshold,
            "recovery_time_seconds": _global_circuit_breaker.recovery_time,
            "open_circuits": sum(1 for v in _global_circuit_breaker._open_time.values() if v is not None),
            "projects_with_failures": len([k for k, v in _global_circuit_breaker._failures.items() if v > 0]),
        }

        # Get cache stats
        cache_details = {
            "cached_fixes": len(_global_fix_cache._cache),
            "max_size": _global_fix_cache.max_size,
            "ttl_seconds": _global_fix_cache.ttl,
            "cache_utilization": f"{(len(_global_fix_cache._cache) / _global_fix_cache.max_size) * 100:.1f}%",
        }

        return {
            "status": "healthy",
            "global_metrics": global_metrics,
            "rate_limiter": rate_limiter_details,
            "circuit_breaker": circuit_breaker_details,
            "cache": cache_details,
        }

    except Exception as e:
        logger.error(f"Error getting autofixer metrics: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@router.get("/health")
async def autofixer_health_check() -> Dict[str, Any]:
    """
    Health check for auto-fixer system.

    Returns simple status for load balancer health checks.
    """
    try:
        # Check if core components are accessible
        _ = get_global_metrics()

        # Check if too many circuits are open (system under stress)
        open_circuits = sum(1 for v in _global_circuit_breaker._open_time.values() if v is not None)
        active_projects = len(_global_rate_limiter._fix_times)

        if open_circuits > 10:
            return {
                "status": "degraded",
                "reason": f"Too many open circuits: {open_circuits}",
            }

        return {
            "status": "healthy",
            "active_projects": active_projects,
            "open_circuits": open_circuits,
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@router.post("/reset-circuit/{project_id}")
async def reset_circuit_breaker(project_id: str) -> Dict[str, Any]:
    """
    Manually reset circuit breaker for a project.

    Use when a project was fixed externally and needs to resume auto-fixing.
    """
    try:
        _global_circuit_breaker._failures[project_id] = 0
        _global_circuit_breaker._open_time[project_id] = None

        return {
            "status": "success",
            "message": f"Circuit breaker reset for project {project_id}",
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@router.post("/clear-cache")
async def clear_fix_cache() -> Dict[str, Any]:
    """
    Clear the fix cache.

    Use when deploying new fix patterns and want to retry cached errors.
    """
    try:
        cache_size = len(_global_fix_cache._cache)
        _global_fix_cache._cache.clear()

        return {
            "status": "success",
            "message": f"Cleared {cache_size} cached fixes",
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }
