"""
Rate Limiting for BharatBuild AI API
====================================
Implements rate limiting using slowapi with Redis backend.

Rate limits are tiered by user type:
- Anonymous: 30 req/min
- Free users: 60 req/min
- Premium users: 200 req/min
- Admin: 1000 req/min

Special endpoints have their own limits:
- /auth/login: 5 req/min (brute force protection)
- /auth/register: 3 req/min
- /orchestrator/execute: 10 req/min (expensive AI operations)
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from typing import Optional, Callable
import redis.asyncio as redis

from app.core.config import settings
from app.core.logging_config import logger


def get_user_identifier(request: Request) -> str:
    """
    Get rate limit key based on user authentication.

    Priority:
    1. Authenticated user ID (from JWT)
    2. API key (for CLI/integrations)
    3. IP address (for anonymous users)
    """
    # Try to get user from request state (set by auth middleware)
    user_id = getattr(request.state, 'user_id', None)
    if user_id:
        return f"user:{user_id}"

    # Try to get API key from header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key[:16]}"  # Use first 16 chars for privacy

    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


def get_rate_limit_tier(request: Request) -> str:
    """
    Determine rate limit tier based on user subscription.

    Returns: 'anonymous', 'free', 'premium', or 'admin'
    """
    # Check if user is authenticated
    user = getattr(request.state, 'user', None)
    if not user:
        return 'anonymous'

    # Check if admin
    if getattr(user, 'is_superuser', False):
        return 'admin'

    # Check subscription tier
    # This would ideally check the subscription from database
    # For now, use is_verified as a proxy (can be enhanced)
    if getattr(user, 'is_verified', False):
        return 'premium'

    return 'free'


# Rate limit configurations per tier
RATE_LIMITS = {
    'anonymous': f"{settings.RATE_LIMIT_PER_MINUTE}/(1 minute)",  # 60/minute default
    'free': "60/(1 minute)",
    'premium': "200/(1 minute)",
    'admin': "1000/(1 minute)",
}

# Special endpoint rate limits
ENDPOINT_LIMITS = {
    '/api/v1/auth/login': "5/(1 minute)",
    '/api/v1/auth/register': "3/(1 minute)",
    '/api/v1/auth/forgot-password': "3/(1 minute)",
    '/api/v1/auth/resend-verification': "3/(1 minute)",
    '/api/v1/orchestrator/execute': "10/(1 minute)",
    '/api/v1/billing/subscribe': "5/(1 minute)",
    '/api/v1/payments/create-order': "10/(1 minute)",
}


def dynamic_rate_limit(request: Request) -> str:
    """
    Dynamic rate limit based on endpoint and user tier.
    """
    # Check for endpoint-specific limits
    path = request.url.path
    if path in ENDPOINT_LIMITS:
        return ENDPOINT_LIMITS[path]

    # Use tier-based limits
    tier = get_rate_limit_tier(request)
    return RATE_LIMITS.get(tier, RATE_LIMITS['anonymous'])


# Create Redis storage for rate limiting (if available)
def get_redis_storage():
    """Get Redis storage URL for rate limiting"""
    try:
        # Use Redis URL from settings
        return settings.REDIS_URL
    except Exception:
        return None


# Create limiter instance
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/(1 minute)"],
    storage_uri=get_redis_storage(),
    strategy="fixed-window",  # or "moving-window" for smoother limiting
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors.

    Returns a user-friendly JSON response with:
    - Error message
    - Retry-After header
    - Current limits info
    """
    retry_after = exc.detail.split(":")[-1].strip() if exc.detail else "60"

    logger.warning(
        f"[RateLimit] Exceeded for {get_user_identifier(request)}: {exc.detail}"
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please slow down.",
            "detail": str(exc.detail),
            "retry_after_seconds": int(retry_after) if retry_after.isdigit() else 60,
            "tier": get_rate_limit_tier(request),
            "upgrade_hint": (
                "Upgrade to Premium for higher rate limits"
                if get_rate_limit_tier(request) in ['anonymous', 'free']
                else None
            )
        },
        headers={
            "Retry-After": retry_after,
            "X-RateLimit-Limit": str(settings.RATE_LIMIT_PER_MINUTE),
        }
    )


# Decorator for applying custom rate limits to specific endpoints
def rate_limit(limit: str):
    """
    Decorator for applying custom rate limits to endpoints.

    Usage:
        @router.post("/my-endpoint")
        @rate_limit("5/(1 minute)")
        async def my_endpoint():
            ...
    """
    return limiter.limit(limit, key_func=get_user_identifier)


# Pre-configured rate limiters for common use cases
def strict_rate_limit():
    """Very strict rate limit for sensitive operations (3/min)"""
    return limiter.limit("3/(1 minute)", key_func=get_user_identifier)


def auth_rate_limit():
    """Rate limit for auth endpoints (5/min)"""
    return limiter.limit("5/(1 minute)", key_func=get_user_identifier)


def ai_operation_rate_limit():
    """Rate limit for expensive AI operations (10/min)"""
    return limiter.limit("10/(1 minute)", key_func=get_user_identifier)


def standard_rate_limit():
    """Standard rate limit (60/min)"""
    return limiter.limit("60/(1 minute)", key_func=get_user_identifier)


def premium_rate_limit():
    """Higher rate limit for premium features (200/min)"""
    return limiter.limit("200/(1 minute)", key_func=get_user_identifier)
