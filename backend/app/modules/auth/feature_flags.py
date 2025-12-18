"""
Plan-based feature control for BharatBuild.

Features are controlled by:
1. User's subscription plan (primary)
2. Global feature flags (can disable for ALL users)

This allows monetization through plans while maintaining admin override capability.
"""
from fastapi import HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional

from app.core.database import get_db
from app.models.user import User
from app.models.system_setting import SystemSetting
from app.models.billing import Plan, Subscription, SubscriptionStatus
from app.modules.auth.dependencies import get_current_user


# Default features for users without a plan (Free tier)
# FREE users can only: preview project structure, run code
# Project generation and all documents require Premium plan upgrade
FREE_TIER_FEATURES = {
    "agentic_mode": False,
    "document_generation": False,  # BLOCKED - requires Premium
    "code_execution": True,  # Allow basic code execution for free
    "api_access": False,
    "priority_queue": False,
    # Plan-based features - blocked for free tier
    "project_generation": False,  # BLOCKED - requires Premium (was True for preview)
    "code_preview": True,  # Can preview code structure only
    "bug_fixing": False,  # BLOCKED - upgrade required
    "srs_document": False,  # BLOCKED - upgrade required
    "sds_document": False,  # BLOCKED - upgrade required
    "project_report": False,  # BLOCKED - upgrade required
    "ppt_generation": False,  # BLOCKED - upgrade required
    "viva_questions": False,  # BLOCKED - upgrade required
    "plagiarism_check": False,  # BLOCKED - upgrade required
    "download_files": False,  # BLOCKED - upgrade required
}


async def get_global_feature_flag(db: AsyncSession, feature_name: str) -> bool:
    """
    Check if a feature is globally enabled by admin.
    Returns True if enabled or not set (default to enabled).
    """
    key = f"features.{feature_name}"
    setting = await db.scalar(select(SystemSetting).where(SystemSetting.key == key))

    if setting is None:
        return True  # Default to enabled if not set

    return bool(setting.value)


async def has_token_purchase(db: AsyncSession, user_id: str) -> bool:
    """Check if user has a valid token purchase (Premium via payment)."""
    from app.models.token_balance import TokenPurchase, TokenBalance

    # Check token_purchases table
    result = await db.execute(
        select(TokenPurchase).where(and_(
            TokenPurchase.user_id == user_id,
            TokenPurchase.payment_status == "success",
            TokenPurchase.is_expired == False
        )).limit(1)
    )
    if result.scalar_one_or_none():
        return True

    # Fallback: Check premium_tokens in balance
    balance_result = await db.execute(
        select(TokenBalance).where(and_(
            TokenBalance.user_id == user_id,
            TokenBalance.premium_tokens > 0
        ))
    )
    return balance_result.scalar_one_or_none() is not None


async def get_user_plan(db: AsyncSession, user_id: str) -> Optional[Plan]:
    """Get user's active subscription plan."""
    result = await db.execute(
        select(Plan)
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(and_(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ))
    )
    return result.scalar_one_or_none()


async def check_feature_access(
    db: AsyncSession,
    user: User,
    feature_name: str
) -> dict:
    """
    Check if user has access to a feature.

    Returns:
        {
            "allowed": bool,
            "reason": str,  # Why access was denied
            "upgrade_to": str,  # Suggested plan to upgrade to
            "current_plan": str  # User's current plan
        }
    """
    # 1. Check global feature flag first (admin can disable for everyone)
    global_enabled = await get_global_feature_flag(db, feature_name)
    if not global_enabled:
        return {
            "allowed": False,
            "reason": f"Feature '{feature_name.replace('_', ' ')}' is currently disabled for maintenance",
            "upgrade_to": None,
            "current_plan": None
        }

    # 2. Check if user has token purchase (Premium via payment)
    # TokenPurchase grants ALL premium features
    if await has_token_purchase(db, str(user.id)):
        return {
            "allowed": True,
            "reason": None,
            "upgrade_to": None,
            "current_plan": "Premium"
        }

    # 3. Check user's subscription plan
    plan = await get_user_plan(db, str(user.id))

    if plan is None:
        # User has no active subscription - use free tier
        current_plan = "Free"
        feature_allowed = FREE_TIER_FEATURES.get(feature_name, False)
    else:
        current_plan = plan.name
        # Check plan's feature_flags
        feature_flags = plan.feature_flags or {}
        feature_allowed = feature_flags.get(feature_name, False)

    if feature_allowed:
        return {
            "allowed": True,
            "reason": None,
            "upgrade_to": None,
            "current_plan": current_plan
        }

    # Feature not allowed - suggest upgrade
    upgrade_suggestions = {
        "agentic_mode": "Student",
        "document_generation": "Pro",
        "code_execution": "Student",
        "api_access": "Pro",
    }

    return {
        "allowed": False,
        "reason": f"Your {current_plan} plan doesn't include {feature_name.replace('_', ' ')}",
        "upgrade_to": upgrade_suggestions.get(feature_name, "Pro"),
        "current_plan": current_plan
    }


async def require_feature_access(
    feature_name: str,
    db: AsyncSession,
    user: User
) -> None:
    """
    Require a feature to be accessible, raise 403 if not.
    Used as a dependency in endpoints.
    """
    result = await check_feature_access(db, user, feature_name)

    if not result["allowed"]:
        detail = {
            "error": "feature_not_available",
            "message": result["reason"],
            "feature": feature_name,
            "current_plan": result["current_plan"],
            "upgrade_to": result["upgrade_to"]
        }
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


def require_feature(feature_name: str):
    """
    Dependency factory to require a feature.

    Usage:
        @router.post("/generate")
        async def generate(
            current_user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
            _: None = Depends(require_feature("agentic_mode"))
        ):
            ...
    """
    async def feature_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        await require_feature_access(feature_name, db, current_user)

    return feature_checker


# Pre-built dependencies for common features
require_agentic_mode = require_feature("agentic_mode")
require_document_generation = require_feature("document_generation")
require_code_execution = require_feature("code_execution")
require_api_access = require_feature("api_access")
