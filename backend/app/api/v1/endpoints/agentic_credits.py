"""
Credit metering for the agentic endpoints.

The credit system was wired into the orchestrator path (web project generation)
but not into /api/v1/agentic/chat/stream, which is the endpoint the CLI sends
every turn to. Measured against a running backend: a 7,085-token CLI turn left
remaining_tokens, used_tokens and total_requests all unchanged. CLI traffic was
entirely unmetered.

Two things to know about the shape of this:

1. Deduction has to use its own database session. These endpoints stream, and
   the request-scoped session from Depends(get_db) is closed once the handler
   returns the StreamingResponse — before the generator has produced a single
   token. dynamic_orchestrator.py hit the same wall and opened `async_session()`
   for exactly this reason.

2. Deduction must never break a turn the user has already paid for in wall-clock
   time. The model has answered by the time we get here; failing the response
   because the ledger write failed would throw away real work. Failures are
   logged loudly and swallowed, which is the standard direction for this trade
   (Stripe does the same on post-charge bookkeeping).
"""

from typing import Any, Dict, Optional

from sqlalchemy import select

from app.core.logging_config import logger
from app.models.user import User


# Charged before we know the real usage, purely to keep an empty account from
# starting a turn. The true cost is deducted afterwards from actual usage.
MIN_CREDITS_TO_START = 1.0


async def check_credits_or_402(user: User, db) -> None:
    """
    Refuse a turn when the user has nothing left.

    Raises HTTPException(402). The CLI already understands that status:
    proxy-model.ts turns it into "Insufficient credits. Top up at
    app.bharatbuild.in" rather than a raw HTTP error.
    """
    from fastapi import HTTPException
    from app.modules.auth.usage_limits import check_credits_available

    try:
        check = await check_credits_available(user, db, credits_needed=MIN_CREDITS_TO_START)
    except Exception as exc:
        # A broken checker must not lock every user out of the product. Fail
        # open, but say so — this used to be silent on the client side and an
        # absent credit system was indistinguishable from a working one.
        logger.error(f"[AgenticCredits] Credit check failed, allowing request: {exc}", exc_info=True)
        return

    if not check.allowed:
        logger.info(f"[AgenticCredits] Refused user {user.id}: {check.reason}")
        raise HTTPException(status_code=402, detail=check.reason or "No credits remaining.")


def registry_id(model_name: str) -> str:
    """
    Match the id the API uses to the id the registry is keyed by.

    The registry keys versions with a dot ("claude-haiku-4.5") while the client
    and claude_client use a hyphen ("claude-haiku-4-5"). Every lookup therefore
    missed, calculate_credits returned 0.0, and the per-model multiplier - 0.4x
    for haiku, 2.2x for opus - was never applied. Left alone, haiku turns would
    have been billed at the 1.0x fallback: two and a half times their real cost.
    """
    import re

    return re.sub(r"(\d)-(\d)", r"\1.\2", model_name or "")


def credits_for(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """
    Convert token usage to credits using the shared registry, so the CLI is
    charged on the same scale as everything else.
    """
    from app.config.model_registry import model_registry

    try:
        credits = model_registry.calculate_credits(model_name, input_tokens, output_tokens)
        if not credits:
            # Try the registry's own spelling before giving up on the model.
            normalised = registry_id(model_name)
            if normalised != model_name:
                credits = model_registry.calculate_credits(normalised, input_tokens, output_tokens)
    except Exception as exc:
        logger.warning(f"[AgenticCredits] calculate_credits failed for '{model_name}': {exc}")
        credits = 0.0

    if credits and credits > 0:
        return credits

    # An unknown model id returns 0.0 from the registry. Charging nothing for a
    # model we failed to recognise is how usage silently becomes free, so fall
    # back to the registry's own base rate: 1 credit per 1,000 tokens at 1x.
    total = max(0, input_tokens) + max(0, output_tokens)
    if total == 0:
        return 0.0
    fallback = total / 1000
    logger.warning(
        f"[AgenticCredits] Unknown model '{model_name}', charging base rate: "
        f"{fallback:.3f} credits for {total} tokens"
    )
    return fallback


async def deduct_and_report(
    user_id: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
) -> Dict[str, Any]:
    """
    Deduct the turn's credits and return what to tell the client.

    Opens its own session (see module docstring). Returns the fields
    proxy-model.ts already reads — credits_deducted, credits_remaining,
    model_used — which the server has never sent until now.
    """
    from app.core.database import async_session
    from app.models.token_balance import TokenBalance
    from app.modules.auth.usage_limits import deduct_credits

    credits = credits_for(model_name, input_tokens, output_tokens)
    result: Dict[str, Any] = {
        "credits_deducted": round(credits, 4),
        "credits_remaining": -1,  # -1 means "unknown", not "empty"
        "model_used": model_name,
    }

    if credits <= 0:
        return result

    try:
        async with async_session() as db:
            ok = await deduct_credits(
                user_id=str(user_id),
                credits_used=credits,
                db=db,
                model=model_name,
                agent_type="cli",
            )
            if not ok:
                # No balance row exists for this user. Worth a warning: it means
                # the account can spend without limit.
                logger.warning(f"[AgenticCredits] No balance to deduct from for user {user_id}")
                result["credits_deducted"] = 0.0
                return result

            balance = (
                await db.execute(select(TokenBalance).where(TokenBalance.user_id == str(user_id)))
            ).scalar_one_or_none()
            if balance is not None:
                result["credits_remaining"] = float(balance.remaining_tokens)
    except Exception as exc:
        # The turn already happened. Losing the ledger write is bad; throwing
        # away the user's answer over it is worse.
        logger.error(f"[AgenticCredits] Deduction failed for user {user_id}: {exc}", exc_info=True)
        result["credits_deducted"] = 0.0

    return result


def usage_from_message(message: Any) -> tuple[int, int]:
    """Pull (input, output) token counts off an Anthropic message, defensively."""
    usage = getattr(message, "usage", None)
    if usage is None:
        return 0, 0
    return int(getattr(usage, "input_tokens", 0) or 0), int(getattr(usage, "output_tokens", 0) or 0)
