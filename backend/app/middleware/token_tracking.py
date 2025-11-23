from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time

from app.utils.token_manager import token_manager
from app.core.database import AsyncSessionLocal
from app.core.logging_config import logger


class TokenTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for real-time token tracking (like Bolt.new)

    Features:
    - Track token usage per request
    - Enforce token limits
    - Real-time balance updates
    - Request rate limiting
    """

    async def dispatch(self, request: Request, call_next):
        # Skip token tracking for auth and public endpoints
        skip_paths = ["/docs", "/redoc", "/openapi.json", "/health", "/auth"]

        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)

        # Get user from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)

        if not user_id:
            # No user authenticated, proceed normally
            return await call_next(request)

        # Check token balance before processing
        async with AsyncSessionLocal() as db:
            try:
                balance = await token_manager.get_or_create_balance(db, user_id)

                # Check daily request limit
                if balance.requests_today >= balance.max_requests_per_day:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Daily request limit reached ({balance.max_requests_per_day}). Please upgrade your plan or wait until tomorrow."
                    )

                # Check if user has any tokens
                if balance.remaining_tokens <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail="Insufficient tokens. Please purchase more tokens to continue."
                    )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Token tracking error: {e}")
                # Don't block request on tracking errors
                pass

        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Add token info to response headers (like Bolt.new)
        async with AsyncSessionLocal() as db:
            try:
                balance = await token_manager.get_or_create_balance(db, user_id)
                response.headers["X-Tokens-Remaining"] = str(balance.remaining_tokens)
                response.headers["X-Tokens-Used-Today"] = str(balance.monthly_used)
                response.headers["X-Requests-Today"] = str(balance.requests_today)
                response.headers["X-Process-Time"] = str(round(process_time, 3))
            except Exception as e:
                logger.error(f"Error adding token headers: {e}")

        return response
