"""
Admin Plan Management endpoints.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import Optional
import math

from app.core.database import get_db
from app.models import User, Plan, Subscription, AuditLog
from app.models.billing import PlanType
from app.modules.auth.dependencies import get_current_admin
from app.schemas.admin import AdminPlanCreate, AdminPlanUpdate, AdminPlanResponse

router = APIRouter()


# Default plans - Simple 2-tier for student projects
# FREE: Generate project structure & preview, but no bug fixing, docs, or download
# PREMIUM: Full access to 1 project with all features
DEFAULT_PLANS = [
    {
        "name": "Free",
        "slug": "free",
        "plan_type": PlanType.FREE,
        "description": "Preview project structure - Upgrade for full access",
        "price": 0,
        "currency": "INR",
        "billing_period": "one_time",
        "token_limit": 10000,  # Enough for structure generation
        "project_limit": 1,  # Can create 1 project (structure only)
        "code_generations_per_day": 5,
        "auto_fixes_per_day": 0,
        "documents_per_month": 0,
        "concurrent_executions": 1,
        "execution_timeout_minutes": 5,
        "allowed_models": ["haiku"],
        "feature_flags": {
            "project_generation": True,  # Can generate project structure
            "code_preview": True,  # Can preview code
            "bug_fixing": False,  # BLOCKED - upgrade required
            "srs_document": False,  # BLOCKED - upgrade required
            "sds_document": False,  # BLOCKED - upgrade required
            "project_report": False,  # BLOCKED - upgrade required
            "ppt_generation": False,  # BLOCKED - upgrade required
            "viva_questions": False,  # BLOCKED - upgrade required
            "plagiarism_check": False,  # BLOCKED - upgrade required
            "code_execution": True,  # Can preview/run code
            "download_files": False,  # BLOCKED - upgrade required
            "max_files_per_project": 3  # FREE users only get 3 files as preview
        },
        "is_active": True
    },
    {
        "name": "Premium",
        "slug": "premium",
        "plan_type": PlanType.PRO,
        "description": "1 Complete Project with all documents",
        "price": 449900,  # ₹4,499 in paise
        "currency": "INR",
        "billing_period": "one_time",
        "token_limit": None,
        "project_limit": 1,  # 1 project only
        "code_generations_per_day": None,
        "auto_fixes_per_day": None,
        "documents_per_month": None,
        "concurrent_executions": 3,
        "execution_timeout_minutes": 30,
        "allowed_models": ["haiku", "sonnet"],
        "feature_flags": {
            "project_generation": True,
            "bug_fixing": True,
            "srs_document": True,
            "sds_document": True,
            "project_report": True,
            "ppt_generation": True,
            "viva_questions": True,
            "plagiarism_check": True,
            "code_execution": True,
            "download_files": True
        },
        "is_active": True
    }
]


async def seed_default_plans(db: AsyncSession) -> dict:
    """Seed default plans if they don't exist"""
    created = []
    skipped = []

    for plan_data in DEFAULT_PLANS:
        existing = await db.scalar(
            select(Plan).where(Plan.slug == plan_data["slug"])
        )

        if existing:
            skipped.append(plan_data["name"])
            continue

        plan = Plan(**plan_data)
        db.add(plan)
        created.append(plan_data["name"])

    if created:
        await db.commit()

    return {"created": created, "skipped": skipped}


@router.post("/seed")
async def seed_plans(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Seed default plans with feature configurations"""
    result = await seed_default_plans(db)

    if result["created"]:
        # Log action
        log = AuditLog(
            admin_id=str(current_admin.id),
            action="plans_seeded",
            target_type="plan",
            target_id=None,
            details=result,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )
        db.add(log)
        await db.commit()

    return {
        "message": "Plans seeded successfully",
        **result
    }


@router.get("")
async def list_plans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List all plans with subscriber counts"""
    query = select(Plan)

    if is_active is not None:
        query = query.where(Plan.is_active == is_active)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Plan.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    plans = result.scalars().all()

    items = []
    for plan in plans:
        # Get subscriber count
        subscribers = await db.scalar(
            select(func.count(Subscription.id)).where(
                Subscription.plan_id == plan.id,
                Subscription.status == "active"
            )
        )

        items.append(AdminPlanResponse(
            id=str(plan.id),
            name=plan.name,
            slug=plan.slug,
            plan_type=plan.plan_type.value if hasattr(plan.plan_type, 'value') else str(plan.plan_type),
            price=plan.price,
            currency=plan.currency or "INR",
            billing_period=plan.billing_period or "monthly",
            token_limit=plan.token_limit,
            project_limit=plan.project_limit,
            feature_flags=plan.feature_flags or {},
            allowed_models=plan.allowed_models or [],
            subscribers_count=subscribers or 0,
            is_active=plan.is_active,
            created_at=plan.created_at
        ))

    return {
        "items": items,
        "total": total or 0,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil((total or 0) / page_size) if total and total > 0 else 1
    }


@router.get("/{plan_id}", response_model=AdminPlanResponse)
async def get_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get a specific plan by ID"""
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    subscribers = await db.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.plan_id == plan.id,
            Subscription.status == "active"
        )
    )

    return AdminPlanResponse(
        id=str(plan.id),
        name=plan.name,
        slug=plan.slug,
        plan_type=plan.plan_type.value if hasattr(plan.plan_type, 'value') else str(plan.plan_type),
        price=plan.price,
        currency=plan.currency or "INR",
        billing_period=plan.billing_period or "monthly",
        token_limit=plan.token_limit,
        project_limit=plan.project_limit,
        feature_flags=plan.feature_flags or {},
        allowed_models=plan.allowed_models or [],
        subscribers_count=subscribers or 0,
        is_active=plan.is_active,
        created_at=plan.created_at
    )


@router.post("")
async def create_plan(
    plan_data: AdminPlanCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Create a new subscription plan"""
    from app.models.billing import PlanType

    # Check if slug already exists
    existing = await db.scalar(select(Plan).where(Plan.slug == plan_data.slug))
    if existing:
        raise HTTPException(status_code=400, detail="Plan with this slug already exists")

    # Create plan
    try:
        plan_type = PlanType(plan_data.plan_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid plan type: {plan_data.plan_type}")

    plan = Plan(
        name=plan_data.name,
        slug=plan_data.slug,
        plan_type=plan_type,
        price=plan_data.price,
        currency=plan_data.currency,
        billing_period=plan_data.billing_period,
        token_limit=plan_data.token_limit,
        project_limit=plan_data.project_limit,
        api_calls_limit=plan_data.api_calls_limit,
        code_generations_per_day=plan_data.code_generations_per_day,
        auto_fixes_per_day=plan_data.auto_fixes_per_day,
        documents_per_month=plan_data.documents_per_month,
        concurrent_executions=plan_data.concurrent_executions,
        execution_timeout_minutes=plan_data.execution_timeout_minutes,
        allowed_models=plan_data.allowed_models,
        feature_flags=plan_data.feature_flags,
        is_active=plan_data.is_active
    )

    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    # Log action
    log = AuditLog(
        admin_id=str(current_admin.id),
        action="plan_created",
        target_type="plan",
        target_id=str(plan.id),
        details={"name": plan.name, "slug": plan.slug, "price": plan.price},
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(log)
    await db.commit()

    return {
        "message": "Plan created successfully",
        "plan_id": str(plan.id)
    }


@router.patch("/{plan_id}")
async def update_plan(
    plan_id: str,
    plan_data: AdminPlanUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Update an existing plan"""
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    changes = {}

    if plan_data.name is not None and plan_data.name != plan.name:
        changes["name"] = {"old": plan.name, "new": plan_data.name}
        plan.name = plan_data.name

    if plan_data.price is not None and plan_data.price != plan.price:
        changes["price"] = {"old": plan.price, "new": plan_data.price}
        plan.price = plan_data.price

    if plan_data.token_limit is not None and plan_data.token_limit != plan.token_limit:
        changes["token_limit"] = {"old": plan.token_limit, "new": plan_data.token_limit}
        plan.token_limit = plan_data.token_limit

    if plan_data.project_limit is not None and plan_data.project_limit != plan.project_limit:
        changes["project_limit"] = {"old": plan.project_limit, "new": plan_data.project_limit}
        plan.project_limit = plan_data.project_limit

    if plan_data.feature_flags is not None:
        changes["feature_flags"] = {"old": plan.feature_flags, "new": plan_data.feature_flags}
        plan.feature_flags = plan_data.feature_flags

    if plan_data.is_active is not None and plan_data.is_active != plan.is_active:
        changes["is_active"] = {"old": plan.is_active, "new": plan_data.is_active}
        plan.is_active = plan_data.is_active

    if changes:
        plan.updated_at = datetime.utcnow()
        await db.commit()

        # Log action
        log = AuditLog(
            admin_id=str(current_admin.id),
            action="plan_updated",
            target_type="plan",
            target_id=plan_id,
            details={"changes": changes},
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )
        db.add(log)
        await db.commit()

    return {"message": "Plan updated successfully"}


@router.delete("/{plan_id}")
async def delete_plan(
    plan_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Delete a plan (only if no active subscribers)"""
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Check for active subscribers
    active_subscribers = await db.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.plan_id == plan.id,
            Subscription.status == "active"
        )
    )

    if active_subscribers and active_subscribers > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete plan with {active_subscribers} active subscribers"
        )

    plan_name = plan.name
    await db.delete(plan)
    await db.commit()

    # Log action
    log = AuditLog(
        admin_id=str(current_admin.id),
        action="plan_deleted",
        target_type="plan",
        target_id=plan_id,
        details={"name": plan_name},
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(log)
    await db.commit()

    return {"message": f"Plan '{plan_name}' deleted successfully"}


@router.get("/{plan_id}/subscribers")
async def get_plan_subscribers(
    plan_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get subscribers for a specific plan"""
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    query = (
        select(Subscription, User)
        .join(User, Subscription.user_id == User.id)
        .where(Subscription.plan_id == plan_id)
    )

    # Get total count
    count_query = select(func.count()).select_from(
        select(Subscription).where(Subscription.plan_id == plan_id).subquery()
    )
    total = await db.scalar(count_query)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Subscription.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for sub, user in rows:
        items.append({
            "subscription_id": str(sub.id),
            "user_id": str(user.id),
            "user_email": user.email,
            "user_name": user.full_name,
            "status": sub.status,
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None
        })

    return {
        "plan_name": plan.name,
        "items": items,
        "total": total or 0,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil((total or 0) / page_size) if total and total > 0 else 1
    }
