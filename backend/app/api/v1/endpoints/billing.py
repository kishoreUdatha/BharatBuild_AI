"""
SUBSCRIPTION & BILLING API
===========================
Complete billing management for BharatBuild AI.

Features:
- Subscription plans (Free, Basic, Pro, Enterprise)
- Usage tracking and limits
- Plan upgrades/downgrades
- Billing history
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from enum import Enum

from app.core.database import get_db
from app.core.config import settings
from app.core.logging_config import logger
from app.models.user import User
from app.models.billing import Plan, PlanType, Subscription, SubscriptionStatus, Transaction, TransactionStatus
from app.models.token_balance import TokenBalance
from app.models.usage import UsageLog
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.usage_limits import check_all_limits
from app.services.email_service import email_service

router = APIRouter()


# ========== Response Models ==========

class PlanFeature(BaseModel):
    name: str
    included: bool
    limit: Optional[str] = None


class PlanResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan_type: str
    description: Optional[str]
    price: int  # in paise
    price_display: str  # formatted price
    currency: str
    billing_period: str
    token_limit: Optional[int]
    project_limit: Optional[int]
    features: List[str]
    is_popular: bool = False


class SubscriptionResponse(BaseModel):
    id: str
    plan: PlanResponse
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    days_remaining: int


class UsageResponse(BaseModel):
    tokens_used: int
    tokens_remaining: int
    tokens_limit: Optional[int]
    projects_created: int
    projects_limit: Optional[int]
    api_calls_today: int
    usage_percentage: float
    reset_date: Optional[datetime]


class BillingOverviewResponse(BaseModel):
    subscription: Optional[SubscriptionResponse]
    usage: UsageResponse
    next_billing_date: Optional[datetime]
    next_billing_amount: Optional[int]


# ========== Default Plans Configuration ==========
# Single project package for BharatBuild AI - ₹4,499 one-time

DEFAULT_PLANS = [
    # ========== COMPLETE PROJECT PACKAGE ==========
    # 1 complete project with all documentation for ₹4,499
    {
        "name": "Complete Project Package",
        "slug": "complete",
        "plan_type": PlanType.ENTERPRISE,
        "description": "1 complete project with full code and all documentation",
        "price": 449900,  # ₹4,499 one-time
        "currency": "INR",
        "billing_period": "one_time",
        # Core Limits - 1 Project
        "token_limit": 500000,  # Internal limit per project (hidden from user)
        "project_limit": 1,  # 1 project per purchase
        "api_calls_limit": None,  # Unlimited within the project
        # Code Generation - All Unlimited
        "code_generations_per_day": None,
        "max_files_per_project": None,
        "max_lines_per_generation": None,
        # Bug Fixing - All Unlimited
        "auto_fixes_per_day": None,
        "auto_fixes_per_month": None,
        # Document Generation - All Unlimited
        "documents_per_month": None,
        "document_types_allowed": ["report", "srs", "sds", "ppt", "viva"],
        # Execution - Maximum
        "concurrent_executions": 5,
        "execution_timeout_minutes": 60,
        "sandbox_hours_per_day": None,  # Unlimited
        # Models - All including Opus
        "allowed_models": ["haiku", "sonnet", "opus"],
        "priority_queue": True,
        # Feature Flags - Everything enabled
        "feature_flags": {
            "code_generation": True,
            "all_templates": True,
            "preview": True,
            "export_zip": True,
            "github_export": True,
            "bug_fixing": True,
            "document_generation": True,
            "project_report": True,
            "srs_document": True,
            "sds_document": True,
            "ppt_presentation": True,
            "viva_questions": True,
            "agentic_mode": True,
            "custom_workflows": True,
            "api_access": True,
            "team_collaboration": True,
            "priority_support": True,
            "dedicated_support": True,
        },
        "features": [
            # 1 Complete Project
            "1 Complete project",
            "Full working code",
            "Lifetime access to code",
            # Code Generation
            "Full code generation for any project",
            "Web Apps (React, Next.js, Vue)",
            "Mobile Apps (React Native, Flutter)",
            "Backend APIs (Node.js, Python, FastAPI)",
            "Full-Stack Applications",
            "Real-time code preview",
            "Live code editing",
            "Multiple file generation",
            "Folder structure creation",
            "Package.json & dependencies setup",
            "Database schema generation",
            "API endpoint generation",
            # Bug Fixing
            "Unlimited automatic bug fixing",
            "AI-powered error detection",
            "Instant code fixes",
            "Syntax error correction",
            "Logic error detection",
            "Runtime error fixing",
            "Code optimization suggestions",
            "Security vulnerability detection",
            # Project Report
            "Project Report (60-80 pages)",
            "Complete IEEE format documentation",
            "Title page with project details",
            "Certificate page",
            "Abstract (project summary)",
            "Table of contents",
            "Chapter 1: Introduction",
            "Chapter 2: Literature Review",
            "Chapter 3: System Requirements",
            "Chapter 4: System Design",
            "Chapter 5: Implementation",
            "Chapter 6: Testing & Results",
            "Chapter 7: Conclusion & Future Scope",
            "References (IEEE format)",
            "Appendix with code snippets",
            # SRS Document
            "SRS Document (IEEE 830 standard)",
            "Functional requirements",
            "Non-functional requirements",
            "Use case diagrams",
            "Use case descriptions",
            # SDS Document
            "SDS Document (full design)",
            "System architecture",
            "High-level design (HLD)",
            "Low-level design (LLD)",
            "Class diagrams",
            "Sequence diagrams",
            "Activity diagrams",
            "ER diagrams",
            "Data flow diagrams (DFD)",
            "Component diagrams",
            "Database schema design",
            # PPT Presentation
            "PPT Presentation (20-25 slides)",
            "Professional slide design",
            "Problem statement",
            "Objectives of the project",
            "System architecture slide",
            "Technology stack used",
            "Screenshots & demos",
            "Conclusion slide",
            "Future enhancements",
            # Viva Q&A
            "Viva Q&A Preparation",
            "50+ potential viva questions",
            "Detailed answers for each question",
            "Project-specific questions",
            "Technology-related questions",
            "Tips for viva presentation",
            # Export
            "Download complete project as ZIP",
            "Export directly to GitHub",
            "GitHub repository creation",
            "README.md generation",
            "Export documentation as PDF",
            "Export documentation as DOCX",
            "Export PPT as PPTX",
            # AI Models
            "Access to Claude Haiku (fast)",
            "Access to Claude Sonnet (balanced)",
            "Access to Claude Opus (powerful)",
            "Priority processing queue",
            "Faster response times",
            # Support
            "Priority email support",
            "Chat support",
            "Help documentation",
            "Video tutorials",
            "Sample projects",
            "Template library",
            "Cancel anytime"
        ]
    }
]


def format_price(price_paise: int, currency: str = "INR") -> str:
    """Format price for display"""
    if price_paise == 0:
        return "Free"
    if currency == "INR":
        return f"₹{price_paise / 100:,.0f}"
    return f"${price_paise / 100:,.2f}"


# ========== Plan Endpoints ==========

@router.get("/plans", response_model=List[PlanResponse])
async def get_plans(db: AsyncSession = Depends(get_db)):
    """
    Get all available subscription plans.
    Returns plans from database, or default plans if none exist.
    """
    # Try to get plans from database
    result = await db.execute(
        select(Plan).where(Plan.is_active == True).order_by(Plan.price)
    )
    db_plans = result.scalars().all()

    if db_plans:
        return [
            PlanResponse(
                id=str(plan.id),
                name=plan.name,
                slug=plan.slug,
                plan_type=plan.plan_type.value,
                description=plan.description,
                price=plan.price,
                price_display=format_price(plan.price, plan.currency),
                currency=plan.currency,
                billing_period=plan.billing_period,
                token_limit=plan.token_limit,
                project_limit=plan.project_limit,
                features=plan.features or [],
                is_popular=(plan.plan_type == PlanType.PRO)
            )
            for plan in db_plans
        ]

    # Return default plans if database is empty
    return [
        PlanResponse(
            id=plan["slug"],
            name=plan["name"],
            slug=plan["slug"],
            plan_type=plan["plan_type"].value,
            description=plan["description"],
            price=plan["price"],
            price_display=format_price(plan["price"], plan["currency"]),
            currency=plan["currency"],
            billing_period=plan["billing_period"],
            token_limit=plan["token_limit"],
            project_limit=plan["project_limit"],
            features=plan["features"],
            is_popular=(plan["plan_type"] == PlanType.PRO)
        )
        for plan in DEFAULT_PLANS
    ]


@router.get("/plans/{plan_slug}", response_model=PlanResponse)
async def get_plan(plan_slug: str, db: AsyncSession = Depends(get_db)):
    """Get a specific plan by slug"""
    # Try database first
    result = await db.execute(
        select(Plan).where(Plan.slug == plan_slug, Plan.is_active == True)
    )
    plan = result.scalar_one_or_none()

    if plan:
        return PlanResponse(
            id=str(plan.id),
            name=plan.name,
            slug=plan.slug,
            plan_type=plan.plan_type.value,
            description=plan.description,
            price=plan.price,
            price_display=format_price(plan.price, plan.currency),
            currency=plan.currency,
            billing_period=plan.billing_period,
            token_limit=plan.token_limit,
            project_limit=plan.project_limit,
            features=plan.features or [],
            is_popular=(plan.plan_type == PlanType.PRO)
        )

    # Check default plans
    for default_plan in DEFAULT_PLANS:
        if default_plan["slug"] == plan_slug:
            return PlanResponse(
                id=default_plan["slug"],
                name=default_plan["name"],
                slug=default_plan["slug"],
                plan_type=default_plan["plan_type"].value,
                description=default_plan["description"],
                price=default_plan["price"],
                price_display=format_price(default_plan["price"], default_plan["currency"]),
                currency=default_plan["currency"],
                billing_period=default_plan["billing_period"],
                token_limit=default_plan["token_limit"],
                project_limit=default_plan["project_limit"],
                features=default_plan["features"],
                is_popular=(default_plan["plan_type"] == PlanType.PRO)
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Plan not found"
    )


# ========== Subscription Endpoints ==========

@router.get("/subscription", response_model=Optional[SubscriptionResponse])
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's active subscription"""
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE
        )
        .order_by(Subscription.created_at.desc())
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        return None

    plan = subscription.plan
    days_remaining = max(0, (subscription.current_period_end - datetime.utcnow()).days)

    return SubscriptionResponse(
        id=str(subscription.id),
        plan=PlanResponse(
            id=str(plan.id) if plan else "free",
            name=plan.name if plan else "Free",
            slug=plan.slug if plan else "free",
            plan_type=plan.plan_type.value if plan else "free",
            description=plan.description if plan else None,
            price=plan.price if plan else 0,
            price_display=format_price(plan.price, plan.currency) if plan else "Free",
            currency=plan.currency if plan else "INR",
            billing_period=plan.billing_period if plan else "monthly",
            token_limit=plan.token_limit if plan else 10000,
            project_limit=plan.project_limit if plan else 3,
            features=plan.features if plan else [],
            is_popular=False
        ),
        status=subscription.status.value,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        days_remaining=days_remaining
    )


# ========== Usage Endpoints ==========

@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's usage statistics"""
    # Get token balance
    result = await db.execute(
        select(TokenBalance).where(TokenBalance.user_id == current_user.id)
    )
    token_balance = result.scalar_one_or_none()

    # Get project count
    from app.models.project import Project
    project_result = await db.execute(
        select(func.count(Project.id)).where(Project.user_id == current_user.id)
    )
    projects_created = project_result.scalar() or 0

    # Get today's API calls
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    api_calls_result = await db.execute(
        select(func.count(UsageLog.id)).where(
            UsageLog.user_id == current_user.id,
            UsageLog.timestamp >= today_start
        )
    )
    api_calls_today = api_calls_result.scalar() or 0

    # Get user's plan limits
    sub_result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE
        )
    )
    subscription = sub_result.scalar_one_or_none()

    # Default to free plan limits
    token_limit = 10000
    project_limit = 3

    if subscription and subscription.plan:
        token_limit = subscription.plan.token_limit
        project_limit = subscription.plan.project_limit

    # Calculate usage
    tokens_used = token_balance.tokens_used if token_balance else 0
    tokens_remaining = token_balance.remaining_tokens if token_balance else token_limit

    # Calculate percentage (avoid division by zero)
    if token_limit and token_limit > 0:
        usage_percentage = min(100, (tokens_used / token_limit) * 100)
    else:
        usage_percentage = 0  # Unlimited plan

    # Calculate reset date (first of next month)
    now = datetime.utcnow()
    if now.month == 12:
        reset_date = datetime(now.year + 1, 1, 1)
    else:
        reset_date = datetime(now.year, now.month + 1, 1)

    return UsageResponse(
        tokens_used=tokens_used,
        tokens_remaining=tokens_remaining,
        tokens_limit=token_limit,
        projects_created=projects_created,
        projects_limit=project_limit,
        api_calls_today=api_calls_today,
        usage_percentage=round(usage_percentage, 1),
        reset_date=reset_date
    )


@router.get("/overview", response_model=BillingOverviewResponse)
async def get_billing_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get complete billing overview for the user"""
    # Get subscription
    subscription = await get_current_subscription(current_user, db)

    # Get usage
    usage = await get_usage(current_user, db)

    # Calculate next billing
    next_billing_date = None
    next_billing_amount = None

    if subscription and not subscription.cancel_at_period_end:
        next_billing_date = subscription.current_period_end
        next_billing_amount = subscription.plan.price

    return BillingOverviewResponse(
        subscription=subscription,
        usage=usage,
        next_billing_date=next_billing_date,
        next_billing_amount=next_billing_amount
    )


# ========== Transaction History ==========

@router.get("/transactions")
async def get_transactions(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's transaction history"""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    transactions = result.scalars().all()

    # Get total count
    count_result = await db.execute(
        select(func.count(Transaction.id)).where(Transaction.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    return {
        "transactions": [
            {
                "id": str(t.id),
                "amount": t.amount,
                "amount_display": format_price(t.amount, t.currency),
                "currency": t.currency,
                "status": t.status.value,
                "description": t.description,
                "razorpay_order_id": t.razorpay_order_id,
                "razorpay_payment_id": t.razorpay_payment_id,
                "created_at": t.created_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None
            }
            for t in transactions
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


# ========== Admin: Seed Default Plans ==========

@router.post("/admin/seed-plans", include_in_schema=False)
async def seed_default_plans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Seed default plans into database (Admin only).
    This should be called once during initial setup.
    """
    # Check if user is admin
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    created_plans = []

    for plan_data in DEFAULT_PLANS:
        # Check if plan already exists
        result = await db.execute(
            select(Plan).where(Plan.slug == plan_data["slug"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Plan {plan_data['slug']} already exists, skipping")
            continue

        plan = Plan(
            name=plan_data["name"],
            slug=plan_data["slug"],
            plan_type=plan_data["plan_type"],
            description=plan_data["description"],
            price=plan_data["price"],
            currency=plan_data["currency"],
            billing_period=plan_data["billing_period"],
            token_limit=plan_data["token_limit"],
            project_limit=plan_data["project_limit"],
            api_calls_limit=plan_data["api_calls_limit"],
            features=plan_data["features"],
            is_active=True
        )

        db.add(plan)
        created_plans.append(plan_data["name"])

    await db.commit()

    logger.info(f"Seeded {len(created_plans)} plans: {created_plans}")

    return {
        "status": "success",
        "created_plans": created_plans,
        "total": len(created_plans)
    }


# ========== Subscription Management ==========

class SubscribeRequest(BaseModel):
    plan_slug: str


class CancelSubscriptionRequest(BaseModel):
    reason: Optional[str] = None
    cancel_immediately: bool = False


@router.post("/subscribe")
async def subscribe_to_plan(
    request: SubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Subscribe to a plan. For paid plans, returns Razorpay order details.
    For free plan, creates subscription immediately.
    """
    # Get the plan
    result = await db.execute(
        select(Plan).where(Plan.slug == request.plan_slug, Plan.is_active == True)
    )
    plan = result.scalar_one_or_none()

    # If not in DB, check default plans
    plan_data = None
    if not plan:
        for default_plan in DEFAULT_PLANS:
            if default_plan["slug"] == request.plan_slug:
                plan_data = default_plan
                break

    if not plan and not plan_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )

    # Check if user already has an active subscription
    existing_result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE
        )
    )
    existing_subscription = existing_result.scalar_one_or_none()

    # Get plan price
    price = plan.price if plan else plan_data["price"]
    plan_name = plan.name if plan else plan_data["name"]

    # Free plan - create subscription immediately
    if price == 0:
        if existing_subscription:
            # Cancel existing subscription
            existing_subscription.status = SubscriptionStatus.CANCELLED
            existing_subscription.cancelled_at = datetime.utcnow()

        # Create new subscription
        now = datetime.utcnow()
        subscription = Subscription(
            user_id=current_user.id,
            plan_id=plan.id if plan else None,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )

        db.add(subscription)
        await db.commit()

        logger.log_auth_event(
            event="subscription_created",
            success=True,
            user_email=current_user.email,
            plan=request.plan_slug
        )

        return {
            "status": "success",
            "message": f"Successfully subscribed to {plan_name} plan",
            "subscription_id": str(subscription.id),
            "requires_payment": False
        }

    # Paid plan - create Razorpay order
    try:
        import razorpay
        from app.core.config import settings

        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment service not configured"
            )

        razorpay_client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        # Create Razorpay order
        order_data = {
            "amount": price,
            "currency": "INR",
            "receipt": f"sub_{current_user.id}_{datetime.utcnow().timestamp()}",
            "notes": {
                "user_id": str(current_user.id),
                "user_email": current_user.email,
                "plan_slug": request.plan_slug,
                "plan_name": plan_name,
                "type": "subscription"
            }
        }

        razorpay_order = razorpay_client.order.create(data=order_data)

        # Store pending transaction
        transaction = Transaction(
            user_id=current_user.id,
            razorpay_order_id=razorpay_order["id"],
            amount=price,
            currency="INR",
            status=TransactionStatus.PENDING,
            description=f"Subscription: {plan_name}",
            extra_metadata={
                "plan_slug": request.plan_slug,
                "plan_name": plan_name,
                "type": "subscription"
            }
        )

        db.add(transaction)
        await db.commit()

        logger.info(f"[Billing] Created subscription order {razorpay_order['id']} for user {current_user.id}")

        return {
            "status": "pending_payment",
            "message": "Complete payment to activate subscription",
            "requires_payment": True,
            "order_id": razorpay_order["id"],
            "amount": price,
            "amount_display": format_price(price, "INR"),
            "currency": "INR",
            "key_id": settings.RAZORPAY_KEY_ID,
            "plan_name": plan_name
        }

    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment service not available"
        )
    except Exception as e:
        logger.error(f"[Billing] Subscription order creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription order"
        )


class VerifySubscriptionRequest(BaseModel):
    """Request to verify subscription payment after checkout"""
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.post("/verify")
async def verify_subscription_payment(
    request: VerifySubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify subscription payment after Razorpay checkout.

    This is step 2 of the subscription flow:
    1. Verify Razorpay signature
    2. Create subscription record
    3. Grant user access to plan features
    """
    import hmac
    import hashlib

    # Find the pending transaction
    result = await db.execute(
        select(Transaction).where(
            Transaction.razorpay_order_id == request.razorpay_order_id,
            Transaction.user_id == current_user.id,
            Transaction.status == TransactionStatus.PENDING
        )
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found or already processed"
        )

    # Check if this is a subscription transaction
    metadata = transaction.extra_metadata or {}
    if metadata.get("type") not in ["subscription", "upgrade"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is for subscription payments. Use /payments/verify for token purchases."
        )

    # Verify Razorpay signature
    try:
        message = f"{request.razorpay_order_id}|{request.razorpay_payment_id}"
        expected_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, request.razorpay_signature):
            logger.warning(f"[Billing] Invalid signature for order {request.razorpay_order_id}")

            # Update transaction as failed
            transaction.status = TransactionStatus.FAILED
            transaction.updated_at = datetime.utcnow()
            await db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment verification failed. Invalid signature."
            )

        # Signature valid - update transaction
        transaction.razorpay_payment_id = request.razorpay_payment_id
        transaction.razorpay_signature = request.razorpay_signature
        transaction.status = TransactionStatus.SUCCESS
        transaction.completed_at = datetime.utcnow()
        transaction.updated_at = datetime.utcnow()

        # Get plan details from transaction metadata
        plan_slug = metadata.get("plan_slug")

        # Get the plan from database
        plan_result = await db.execute(
            select(Plan).where(Plan.slug == plan_slug, Plan.is_active == True)
        )
        plan = plan_result.scalar_one_or_none()

        if not plan:
            logger.error(f"[Billing] Plan {plan_slug} not found for verified payment")
            # Still mark transaction as success but log the issue
            await db.commit()
            return {
                "status": "success",
                "message": "Payment successful but plan not found. Please contact support.",
                "payment_id": request.razorpay_payment_id
            }

        # Cancel any existing active subscriptions
        existing_result = await db.execute(
            select(Subscription).where(
                Subscription.user_id == current_user.id,
                Subscription.status == SubscriptionStatus.ACTIVE
            )
        )
        existing_subscription = existing_result.scalars().all()
        for old_sub in existing_subscription:
            old_sub.status = SubscriptionStatus.CANCELLED
            old_sub.cancelled_at = datetime.utcnow()

        # Create new subscription
        now = datetime.utcnow()
        billing_period = plan.billing_period or "monthly"

        # Calculate period end based on billing type
        if billing_period == "one_time":
            # One-time purchases get lifetime access (10 years)
            period_end = now + timedelta(days=3650)
        elif billing_period == "yearly":
            period_end = now + timedelta(days=365)
        else:  # monthly
            period_end = now + timedelta(days=30)

        subscription = Subscription(
            user_id=current_user.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=period_end,
        )

        db.add(subscription)

        # Link transaction to subscription
        transaction.subscription_id = subscription.id

        await db.commit()
        await db.refresh(subscription)

        logger.info(f"[Billing] Subscription created for user {current_user.id}, plan: {plan.name}")

        # Send purchase confirmation email (async, don't block response)
        try:
            import asyncio
            asyncio.create_task(
                email_service.send_purchase_confirmation_email(
                    to_email=current_user.email,
                    user_name=current_user.full_name,
                    plan_name=plan.name,
                    amount=transaction.amount,
                    payment_id=request.razorpay_payment_id
                )
            )
            logger.info(f"[Billing] Purchase confirmation email queued for {current_user.email}")
        except Exception as email_error:
            # Don't fail subscription if email fails
            logger.warning(f"[Billing] Failed to send confirmation email: {email_error}")

        return {
            "status": "success",
            "message": f"Successfully subscribed to {plan.name}!",
            "subscription_id": str(subscription.id),
            "plan_name": plan.name,
            "plan_slug": plan.slug,
            "features": plan.feature_flags or {},
            "valid_until": period_end.isoformat(),
            "payment_id": request.razorpay_payment_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Billing] Subscription verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment verification failed. Please contact support."
        )


@router.post("/cancel")
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel current subscription"""
    # Get active subscription
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )

    if request.cancel_immediately:
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.utcnow()
        message = "Subscription cancelled immediately"
    else:
        subscription.cancel_at_period_end = True
        subscription.cancelled_at = datetime.utcnow()
        message = f"Subscription will be cancelled at the end of billing period ({subscription.current_period_end.strftime('%Y-%m-%d')})"

    await db.commit()

    logger.log_auth_event(
        event="subscription_cancelled",
        success=True,
        user_email=current_user.email,
        reason=request.reason,
        immediately=request.cancel_immediately
    )

    return {
        "status": "success",
        "message": message,
        "cancelled_at": subscription.cancelled_at.isoformat(),
        "effective_until": subscription.current_period_end.isoformat() if not request.cancel_immediately else None
    }


@router.post("/reactivate")
async def reactivate_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reactivate a cancelled subscription (before period end)"""
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.cancel_at_period_end == True
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription pending cancellation found"
        )

    subscription.cancel_at_period_end = False
    subscription.cancelled_at = None

    await db.commit()

    logger.info(f"[Billing] Subscription reactivated for user {current_user.id}")

    return {
        "status": "success",
        "message": "Subscription reactivated successfully"
    }


@router.post("/upgrade")
async def upgrade_subscription(
    request: SubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upgrade to a higher plan.
    Prorates the difference if upgrading mid-cycle.
    """
    # Get current subscription
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE
        )
    )
    current_subscription = result.scalar_one_or_none()

    # Get new plan
    plan_result = await db.execute(
        select(Plan).where(Plan.slug == request.plan_slug, Plan.is_active == True)
    )
    new_plan = plan_result.scalar_one_or_none()

    if not new_plan:
        # Check default plans
        for default_plan in DEFAULT_PLANS:
            if default_plan["slug"] == request.plan_slug:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Please seed plans to database first using /billing/admin/seed-plans"
                )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )

    # Calculate prorated amount
    current_price = current_subscription.plan.price if current_subscription and current_subscription.plan else 0
    new_price = new_plan.price

    if new_price <= current_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /billing/subscribe for downgrades or same-tier changes"
        )

    # Calculate days remaining in current period
    if current_subscription:
        days_remaining = max(0, (current_subscription.current_period_end - datetime.utcnow()).days)
        days_in_period = 30
        prorated_credit = int((current_price * days_remaining) / days_in_period)
        amount_due = new_price - prorated_credit
    else:
        amount_due = new_price
        prorated_credit = 0

    # Create payment order for the difference
    try:
        import razorpay
        from app.core.config import settings

        razorpay_client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        order_data = {
            "amount": max(100, amount_due),  # Minimum ₹1
            "currency": "INR",
            "receipt": f"upgrade_{current_user.id}_{datetime.utcnow().timestamp()}",
            "notes": {
                "user_id": str(current_user.id),
                "plan_slug": request.plan_slug,
                "type": "upgrade",
                "prorated_credit": prorated_credit
            }
        }

        razorpay_order = razorpay_client.order.create(data=order_data)

        # Store transaction
        transaction = Transaction(
            user_id=current_user.id,
            subscription_id=current_subscription.id if current_subscription else None,
            razorpay_order_id=razorpay_order["id"],
            amount=amount_due,
            currency="INR",
            status=TransactionStatus.PENDING,
            description=f"Upgrade to {new_plan.name}",
            extra_metadata={
                "type": "upgrade",
                "new_plan_id": str(new_plan.id),
                "new_plan_slug": new_plan.slug,
                "prorated_credit": prorated_credit
            }
        )

        db.add(transaction)
        await db.commit()

        return {
            "status": "pending_payment",
            "message": f"Pay {format_price(amount_due, 'INR')} to upgrade to {new_plan.name}",
            "order_id": razorpay_order["id"],
            "amount": amount_due,
            "amount_display": format_price(amount_due, "INR"),
            "prorated_credit": prorated_credit,
            "prorated_credit_display": format_price(prorated_credit, "INR"),
            "key_id": settings.RAZORPAY_KEY_ID
        }

    except Exception as e:
        logger.error(f"[Billing] Upgrade order creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create upgrade order"
        )


# ========== Usage Limits Status ==========

@router.get("/limits")
async def get_usage_limits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive usage limits status.

    Returns current usage vs limits for:
    - Tokens (monthly)
    - Projects (total)
    - API calls (daily)
    - Available features

    This endpoint is useful for:
    - Showing usage bars in the UI
    - Checking before starting expensive operations
    - Displaying upgrade prompts when near limits
    """
    limits = await check_all_limits(current_user, db)
    return {
        "success": True,
        "allowed": limits.allowed,
        "reason": limits.reason,
        "current_usage": limits.current_usage,
        "limit": limits.limit
    }


# ========== Plan Status (Simple 2-tier) ==========

@router.get("/status")
async def get_plan_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's plan status with remaining projects.

    Simple response for the 2-tier plan system:
    - Free: 0 projects, demo only
    - Premium: 2 projects with all features

    Used by frontend to show:
    - Current plan name
    - Projects used / remaining
    - Feature access
    - Upgrade prompt if on free plan
    """
    from app.models.project import Project
    from app.modules.auth.usage_limits import get_user_limits

    # Get user's limits from subscription
    limits = await get_user_limits(current_user, db)

    # Get current project count
    project_result = await db.execute(
        select(func.count(Project.id)).where(Project.user_id == current_user.id)
    )
    projects_created = project_result.scalar() or 0

    # Calculate remaining projects
    projects_remaining = None
    if limits.project_limit is not None:
        projects_remaining = max(0, limits.project_limit - projects_created)

    # Get feature flags
    feature_flags = limits.feature_flags or {}

    # Determine if user needs to upgrade
    is_free_plan = limits.plan_type.value == "free"
    needs_upgrade = is_free_plan or (projects_remaining is not None and projects_remaining == 0)

    return {
        "success": True,
        "plan": {
            "name": limits.plan_name,
            "type": limits.plan_type.value,
            "is_free": is_free_plan,
            "is_premium": limits.plan_type.value == "pro"
        },
        "projects": {
            "created": projects_created,
            "limit": limits.project_limit,
            "remaining": projects_remaining,
            "can_create": projects_remaining is None or projects_remaining > 0
        },
        "features": {
            "project_generation": feature_flags.get("project_generation", False),
            "bug_fixing": feature_flags.get("bug_fixing", False),
            "srs_document": feature_flags.get("srs_document", False),
            "sds_document": feature_flags.get("sds_document", False),
            "project_report": feature_flags.get("project_report", False),
            "ppt_generation": feature_flags.get("ppt_generation", False),
            "viva_questions": feature_flags.get("viva_questions", False),
            "plagiarism_check": feature_flags.get("plagiarism_check", False),
            "code_execution": feature_flags.get("code_execution", False),
            "download_files": feature_flags.get("download_files", False)
        },
        "needs_upgrade": needs_upgrade,
        "upgrade_message": (
            "Upgrade to Premium to create projects with all features"
            if is_free_plan else
            "You've used all your projects. Purchase again for more."
            if projects_remaining == 0 else None
        )
    }
