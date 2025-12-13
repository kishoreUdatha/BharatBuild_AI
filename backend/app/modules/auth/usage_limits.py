"""
Usage Limits Module
===================
Tracks user usage against plan limits and enforces feature access.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import datetime, timedelta

from app.models.user import User
from app.models.billing import Plan, Subscription, SubscriptionStatus, PlanType
from app.models.usage import UsageLog, TokenUsage


@dataclass
class UsageLimitCheck:
    """Result of a usage limit check"""
    allowed: bool
    reason: Optional[str] = None
    message: Optional[str] = None  # Success message (e.g., "You can create 2 more projects")
    current_usage: int = 0
    limit: Optional[int] = None
    reset_at: Optional[datetime] = None


@dataclass
class UserLimits:
    """User's current plan limits"""
    plan_name: str
    plan_type: PlanType
    token_limit: Optional[int] = None
    project_limit: Optional[int] = None
    api_calls_limit: Optional[int] = None
    code_generations_per_day: Optional[int] = None
    auto_fixes_per_day: Optional[int] = None
    documents_per_month: Optional[int] = None
    concurrent_executions: int = 1
    execution_timeout_minutes: int = 5
    allowed_models: List[str] = field(default_factory=lambda: ["haiku"])
    feature_flags: Dict[str, Any] = field(default_factory=dict)
    max_files_per_project: Optional[int] = None  # None = unlimited

    @property
    def is_unlimited(self) -> bool:
        """Check if user has unlimited access (Pro plan typically)"""
        return self.token_limit is None


# Default limits for FREE users (no subscription)
# FREE users can only generate 3 files to preview the project structure
FREE_LIMITS = UserLimits(
    plan_name="Free",
    plan_type=PlanType.FREE,
    token_limit=10000,
    project_limit=1,
    api_calls_limit=100,
    code_generations_per_day=5,
    auto_fixes_per_day=0,
    documents_per_month=0,
    concurrent_executions=1,
    execution_timeout_minutes=5,
    allowed_models=["haiku"],
    feature_flags={
        "project_generation": True,
        "code_preview": True,
        "bug_fixing": False,
        "srs_document": False,
        "sds_document": False,
        "project_report": False,
        "ppt_generation": False,
        "viva_questions": False,
        "plagiarism_check": False,
        "code_execution": True,
        "download_files": False
    },
    max_files_per_project=3  # FREE users only get 3 files as preview
)


async def get_user_limits(user: User, db: AsyncSession) -> UserLimits:
    """Get user's current plan limits"""
    # Get active subscription
    result = await db.execute(
        select(Subscription).join(Plan).where(
            and_(
                Subscription.user_id == user.id,
                Subscription.status == SubscriptionStatus.ACTIVE
            )
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        return FREE_LIMITS

    # Get the plan
    plan_result = await db.execute(
        select(Plan).where(Plan.id == subscription.plan_id)
    )
    plan = plan_result.scalar_one_or_none()

    if not plan:
        return FREE_LIMITS

    feature_flags = plan.feature_flags or {}
    # Get max_files from feature_flags, None means unlimited (Premium)
    max_files = feature_flags.get("max_files_per_project", None)

    return UserLimits(
        plan_name=plan.name,
        plan_type=plan.plan_type,
        token_limit=plan.token_limit,
        project_limit=plan.project_limit,
        api_calls_limit=plan.api_calls_limit,
        code_generations_per_day=plan.code_generations_per_day,
        auto_fixes_per_day=plan.auto_fixes_per_day,
        documents_per_month=plan.documents_per_month,
        concurrent_executions=plan.concurrent_executions or 1,
        execution_timeout_minutes=plan.execution_timeout_minutes or 5,
        allowed_models=plan.allowed_models or ["haiku"],
        feature_flags=feature_flags,
        max_files_per_project=max_files
    )


async def check_token_limit(user: User, db: AsyncSession, tokens_needed: int = 0) -> UsageLimitCheck:
    """Check if user has tokens remaining"""
    limits = await get_user_limits(user, db)

    if limits.token_limit is None:
        return UsageLimitCheck(allowed=True)

    # Get current token usage this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    usage_result = await db.execute(
        select(func.sum(TokenUsage.total_tokens)).where(
            and_(
                TokenUsage.user_id == user.id,
                TokenUsage.date >= month_start
            )
        )
    )
    current_usage = usage_result.scalar() or 0

    if current_usage + tokens_needed > limits.token_limit:
        return UsageLimitCheck(
            allowed=False,
            reason=f"Token limit exceeded. You've used {current_usage:,} of {limits.token_limit:,} tokens this month.",
            current_usage=current_usage,
            limit=limits.token_limit
        )

    return UsageLimitCheck(
        allowed=True,
        current_usage=current_usage,
        limit=limits.token_limit
    )


async def check_project_limit(user: User, db: AsyncSession) -> UsageLimitCheck:
    """
    Check if user can create more projects.

    Two-stage completion model:
    - Only COMPLETED projects (code + documents generated) count against the limit
    - PARTIAL_COMPLETED (code done, documents pending) does NOT count

    Status breakdown:
    - COMPLETED: Code + all documents generated → COUNTS against limit
    - PARTIAL_COMPLETED: Code done, documents pending → Does NOT count
    - IN_PROGRESS: Currently generating → Does NOT count
    - PROCESSING: Being processed → Does NOT count
    - DRAFT: Just created → Does NOT count
    - FAILED: Generation failed → Does NOT count
    - CANCELLED: User cancelled → Does NOT count

    This allows users to:
    1. Generate code freely (PARTIAL_COMPLETED)
    2. Only use a "project slot" when documents are generated (COMPLETED)
    """
    from app.models.project import Project, ProjectStatus

    limits = await get_user_limits(user, db)

    if limits.project_limit is None:
        return UsageLimitCheck(allowed=True)

    # Only count FULLY COMPLETED projects (code + documents)
    # PARTIAL_COMPLETED (code only) does NOT count against the limit
    project_count_result = await db.execute(
        select(func.count(Project.id)).where(
            and_(
                Project.user_id == user.id,
                Project.status == ProjectStatus.COMPLETED  # Only fully completed
            )
        )
    )
    current_count = project_count_result.scalar() or 0

    if current_count >= limits.project_limit:
        return UsageLimitCheck(
            allowed=False,
            reason=f"Project limit reached. You have {current_count} fully completed project(s). Upgrade your plan for more projects.",
            current_usage=current_count,
            limit=limits.project_limit
        )

    return UsageLimitCheck(
        allowed=True,
        current_usage=current_count,
        limit=limits.project_limit,
        message=f"You can complete {limits.project_limit - current_count} more project(s) with documents"
    )


async def check_api_rate_limit(user: User, db: AsyncSession) -> UsageLimitCheck:
    """Check API rate limits"""
    limits = await get_user_limits(user, db)

    if limits.api_calls_limit is None:
        return UsageLimitCheck(allowed=True)

    # Count API calls today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    usage_result = await db.execute(
        select(func.count(UsageLog.id)).where(
            and_(
                UsageLog.user_id == user.id,
                UsageLog.created_at >= today_start
            )
        )
    )
    current_count = usage_result.scalar() or 0

    if current_count >= limits.api_calls_limit:
        return UsageLimitCheck(
            allowed=False,
            reason=f"Daily API rate limit reached ({limits.api_calls_limit} calls/day)",
            current_usage=current_count,
            limit=limits.api_calls_limit,
            reset_at=today_start + timedelta(days=1)
        )

    return UsageLimitCheck(
        allowed=True,
        current_usage=current_count,
        limit=limits.api_calls_limit
    )


async def require_feature(user: User, db: AsyncSession, feature_name: str) -> None:
    """Require a feature to be enabled, raise 403 if not"""
    limits = await get_user_limits(user, db)
    feature_flags = limits.feature_flags or {}

    if not feature_flags.get(feature_name, False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "feature_not_available",
                "message": f"Feature '{feature_name.replace('_', ' ')}' requires Premium plan",
                "feature": feature_name,
                "current_plan": limits.plan_name,
                "upgrade_to": "Premium"
            }
        )


async def check_all_limits(user: User, db: AsyncSession, tokens_needed: int = 0) -> UsageLimitCheck:
    """Check all usage limits at once"""
    # Check token limit
    token_check = await check_token_limit(user, db, tokens_needed)
    if not token_check.allowed:
        return token_check

    # Check API rate limit
    rate_check = await check_api_rate_limit(user, db)
    if not rate_check.allowed:
        return rate_check

    return UsageLimitCheck(allowed=True)


async def check_document_generation_limit(user: User, db: AsyncSession) -> UsageLimitCheck:
    """Check if user can generate more documents this month"""
    from app.models.document import Document

    limits = await get_user_limits(user, db)

    if limits.documents_per_month is None:
        return UsageLimitCheck(allowed=True)

    # Count documents generated this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    doc_count_result = await db.execute(
        select(func.count(Document.id)).where(
            and_(
                Document.user_id == user.id,
                Document.created_at >= month_start
            )
        )
    )
    current_count = doc_count_result.scalar() or 0

    if current_count >= limits.documents_per_month:
        return UsageLimitCheck(
            allowed=False,
            reason=f"Document generation limit reached. You've generated {current_count} of {limits.documents_per_month} documents this month.",
            current_usage=current_count,
            limit=limits.documents_per_month
        )

    return UsageLimitCheck(
        allowed=True,
        current_usage=current_count,
        limit=limits.documents_per_month
    )


async def check_document_type(user: User, db: AsyncSession, doc_type: str) -> UsageLimitCheck:
    """Check if user has access to specific document type"""
    limits = await get_user_limits(user, db)
    feature_flags = limits.feature_flags or {}

    doc_type_features = {
        "srs": "srs_document",
        "sds": "sds_document",
        "project_report": "project_report",
        "ppt": "ppt_generation",
        "viva_qa": "viva_questions"
    }

    feature_name = doc_type_features.get(doc_type)
    if feature_name and not feature_flags.get(feature_name, False):
        return UsageLimitCheck(
            allowed=False,
            reason=f"'{doc_type.replace('_', ' ').title()}' generation requires Premium plan"
        )

    return UsageLimitCheck(allowed=True)


async def check_bug_fixing_limit(user: User, db: AsyncSession) -> UsageLimitCheck:
    """Check if user can auto-fix more bugs today"""
    limits = await get_user_limits(user, db)

    if limits.auto_fixes_per_day is None:
        return UsageLimitCheck(allowed=True)

    if limits.auto_fixes_per_day == 0:
        return UsageLimitCheck(
            allowed=False,
            reason="Auto bug fixing requires Premium plan"
        )

    # Count fixes today (would need a fixes table to track)
    # For now, just allow if limit > 0
    return UsageLimitCheck(allowed=True, limit=limits.auto_fixes_per_day)


async def check_code_generation_limit(user: User, db: AsyncSession) -> UsageLimitCheck:
    """Check code generation daily limit"""
    limits = await get_user_limits(user, db)

    if limits.code_generations_per_day is None:
        return UsageLimitCheck(allowed=True)

    # Count code generations today (would need proper tracking)
    # For now, just return allowed
    return UsageLimitCheck(
        allowed=True,
        limit=limits.code_generations_per_day
    )


async def check_model_access(user: User, db: AsyncSession, model: str) -> UsageLimitCheck:
    """Check if user has access to a specific model"""
    limits = await get_user_limits(user, db)

    if model not in limits.allowed_models:
        return UsageLimitCheck(
            allowed=False,
            reason=f"Model '{model}' is not available on your plan. Allowed: {', '.join(limits.allowed_models)}"
        )

    return UsageLimitCheck(allowed=True)


async def deduct_tokens(user: User, db: AsyncSession, tokens_used: int, model: str = "haiku") -> None:
    """Deduct tokens from user's usage"""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Get or create today's usage record
    result = await db.execute(
        select(TokenUsage).where(
            and_(
                TokenUsage.user_id == user.id,
                TokenUsage.date == today
            )
        )
    )
    usage = result.scalar_one_or_none()

    if usage:
        usage.total_tokens += tokens_used
        usage.total_requests += 1
        if model == "haiku":
            usage.haiku_tokens += tokens_used
        elif model == "sonnet":
            usage.sonnet_tokens += tokens_used
    else:
        usage = TokenUsage(
            user_id=user.id,
            date=today,
            total_tokens=tokens_used,
            total_requests=1,
            haiku_tokens=tokens_used if model == "haiku" else 0,
            sonnet_tokens=tokens_used if model == "sonnet" else 0
        )
        db.add(usage)

    await db.commit()


async def log_api_usage(
    user: User,
    db: AsyncSession,
    endpoint: str,
    method: str = "POST",
    tokens_used: int = 0,
    model: str = None,
    status_code: int = 200,
    response_time: int = None,
    ip_address: str = None,
    user_agent: str = None
) -> None:
    """Log API usage for rate limiting and analytics"""
    log = UsageLog(
        user_id=user.id,
        endpoint=endpoint,
        method=method,
        tokens_used=tokens_used,
        model_used=model,
        status_code=status_code,
        response_time=response_time,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(log)
    await db.commit()


async def get_current_token_usage(user: User, db: AsyncSession) -> int:
    """Get user's current token usage for the month"""
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    usage_result = await db.execute(
        select(func.sum(TokenUsage.total_tokens)).where(
            and_(
                TokenUsage.user_id == user.id,
                TokenUsage.date >= month_start
            )
        )
    )
    return usage_result.scalar() or 0
