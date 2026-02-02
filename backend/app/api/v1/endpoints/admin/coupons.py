"""
Admin Coupon Management Endpoints

Endpoints for admins to create, manage, and analyze coupons.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_admin
from app.models.user import User
from app.models.audit_log import AuditLog
from app.services.coupon_service import coupon_service
from app.schemas.coupon import (
    CouponCreate,
    CouponUpdate,
    CouponResponse,
    CouponListResponse,
    CouponUsageResponse,
    CouponUsageListResponse,
    CouponAnalytics,
    CouponStatsResponse,
)

router = APIRouter(prefix="/coupons", tags=["Admin - Coupons"])


async def log_admin_action(
    db: AsyncSession,
    admin_id: str,
    action: str,
    target_type: str,
    target_id: str = None,
    details: dict = None,
    request: Request = None
):
    """Log an admin action to audit log"""
    log = AuditLog(
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=request.client.host if request else None,
    )
    db.add(log)
    await db.commit()


@router.get("", response_model=CouponListResponse)
async def list_coupons(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category: student, faculty, college, media"),
    status: Optional[str] = Query(None, description="Filter by status: active, inactive, expired"),
    search: Optional[str] = Query(None, description="Search by code or name"),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all coupons with pagination and filters

    Filters:
    - category: student, faculty, college, media
    - status: active, inactive, expired
    - search: Search in code and name
    """
    coupons, total = await coupon_service.list_coupons(
        db=db,
        page=page,
        page_size=page_size,
        category=category,
        status=status,
        search=search
    )

    return CouponListResponse(
        coupons=[
            CouponResponse(
                id=str(c.id),
                code=c.code,
                owner_id=str(c.owner_id) if c.owner_id else None,
                owner_name=c.owner_name,
                owner_email=c.owner_email,
                owner_phone=c.owner_phone,
                category=c.category.value,
                name=c.name,
                description=c.description,
                discount_amount=c.discount_amount,
                discount_amount_inr=c.discount_amount / 100,
                reward_amount=c.reward_amount,
                reward_amount_inr=c.reward_amount / 100,
                total_uses=c.total_uses,
                total_discount_given=c.total_discount_given,
                total_reward_earned=c.total_reward_earned,
                status=c.status.value,
                is_active=c.is_active,
                valid_from=c.valid_from,
                valid_until=c.valid_until,
                created_at=c.created_at
            )
            for c in coupons
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
async def create_coupon(
    coupon_data: CouponCreate,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new coupon code

    The coupon will be assigned to the specified owner who will earn
    rewards when the coupon is used.

    Args:
        code: Unique coupon code (will be uppercased)
        owner_id: User ID who will earn rewards
        category: student, faculty, college, or media
        discount_amount: Discount for applier in paise (default 10000 = ₹100)
        reward_amount: Reward for owner in paise (default 10000 = ₹100)
        valid_from: Start date (optional, defaults to now)
        valid_until: Expiry date (optional, null = no expiry)
    """
    try:
        coupon = await coupon_service.create_coupon(
            db=db,
            coupon_data=coupon_data,
            created_by_id=str(admin.id)
        )

        # Log admin action
        await log_admin_action(
            db=db,
            admin_id=str(admin.id),
            action="create_coupon",
            target_type="coupon",
            target_id=str(coupon.id),
            details={
                "code": coupon.code,
                "owner_name": coupon.owner_name,
                "owner_email": coupon.owner_email,
                "category": coupon.category.value,
                "discount_amount": coupon.discount_amount,
                "reward_amount": coupon.reward_amount,
            },
            request=request
        )

        return CouponResponse(
            id=str(coupon.id),
            code=coupon.code,
            owner_id=str(coupon.owner_id) if coupon.owner_id else None,
            owner_name=coupon.owner_name,
            owner_email=coupon.owner_email,
            owner_phone=coupon.owner_phone,
            category=coupon.category.value,
            name=coupon.name,
            description=coupon.description,
            discount_amount=coupon.discount_amount,
            discount_amount_inr=coupon.discount_amount / 100,
            reward_amount=coupon.reward_amount,
            reward_amount_inr=coupon.reward_amount / 100,
            total_uses=coupon.total_uses,
            total_discount_given=coupon.total_discount_given,
            total_reward_earned=coupon.total_reward_earned,
            status=coupon.status.value,
            is_active=coupon.is_active,
            valid_from=coupon.valid_from,
            valid_until=coupon.valid_until,
            created_at=coupon.created_at
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/analytics", response_model=CouponAnalytics)
async def get_coupon_analytics(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get overall coupon analytics

    Returns:
    - Total and active coupon counts
    - Total uses across all coupons
    - Total discount given and rewards paid
    - Breakdown by category
    - Top performing coupons
    """
    analytics = await coupon_service.get_coupon_analytics(db)

    return CouponAnalytics(
        total_coupons=analytics["total_coupons"],
        active_coupons=analytics["active_coupons"],
        total_uses=analytics["total_uses"],
        total_discount_given=analytics["total_discount_given"],
        total_discount_given_inr=analytics["total_discount_given_inr"],
        total_rewards_paid=analytics["total_rewards_paid"],
        total_rewards_paid_inr=analytics["total_rewards_paid_inr"],
        coupons_by_category=analytics["coupons_by_category"],
        top_coupons=[
            CouponResponse(
                id=str(c.id),
                code=c.code,
                owner_id=str(c.owner_id),
                owner_name=c.owner_name,
                owner_email=c.owner_email,
                owner_phone=c.owner_phone,
                category=c.category.value,
                name=c.name,
                description=c.description,
                discount_amount=c.discount_amount,
                discount_amount_inr=c.discount_amount / 100,
                reward_amount=c.reward_amount,
                reward_amount_inr=c.reward_amount / 100,
                total_uses=c.total_uses,
                total_discount_given=c.total_discount_given,
                total_reward_earned=c.total_reward_earned,
                status=c.status.value,
                is_active=c.is_active,
                valid_from=c.valid_from,
                valid_until=c.valid_until,
                created_at=c.created_at
            )
            for c in analytics["top_coupons"]
        ]
    )


@router.get("/{coupon_id}", response_model=CouponResponse)
async def get_coupon(
    coupon_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get coupon details by ID
    """
    coupon = await coupon_service.get_coupon_by_id(db, coupon_id)

    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    return CouponResponse(
        id=str(coupon.id),
        code=coupon.code,
        owner_id=str(coupon.owner_id) if coupon.owner_id else None,
        owner_name=coupon.owner_name,
        owner_email=coupon.owner_email,
        owner_phone=coupon.owner_phone,
        category=coupon.category.value,
        name=coupon.name,
        description=coupon.description,
        discount_amount=coupon.discount_amount,
        discount_amount_inr=coupon.discount_amount / 100,
        reward_amount=coupon.reward_amount,
        reward_amount_inr=coupon.reward_amount / 100,
        total_uses=coupon.total_uses,
        total_discount_given=coupon.total_discount_given,
        total_reward_earned=coupon.total_reward_earned,
        status=coupon.status.value,
        is_active=coupon.is_active,
        valid_from=coupon.valid_from,
        valid_until=coupon.valid_until,
        created_at=coupon.created_at
    )


@router.put("/{coupon_id}", response_model=CouponResponse)
async def update_coupon(
    coupon_id: str,
    update_data: CouponUpdate,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update coupon details

    Can update:
    - name, description
    - discount_amount, reward_amount
    - status, is_active
    - valid_until
    """
    coupon = await coupon_service.update_coupon(db, coupon_id, update_data)

    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    # Log admin action
    await log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action="update_coupon",
        target_type="coupon",
        target_id=coupon_id,
        details=update_data.model_dump(exclude_unset=True),
        request=request
    )

    return CouponResponse(
        id=str(coupon.id),
        code=coupon.code,
        owner_id=str(coupon.owner_id) if coupon.owner_id else None,
        owner_name=coupon.owner_name,
        owner_email=coupon.owner_email,
        owner_phone=coupon.owner_phone,
        category=coupon.category.value,
        name=coupon.name,
        description=coupon.description,
        discount_amount=coupon.discount_amount,
        discount_amount_inr=coupon.discount_amount / 100,
        reward_amount=coupon.reward_amount,
        reward_amount_inr=coupon.reward_amount / 100,
        total_uses=coupon.total_uses,
        total_discount_given=coupon.total_discount_given,
        total_reward_earned=coupon.total_reward_earned,
        status=coupon.status.value,
        is_active=coupon.is_active,
        valid_from=coupon.valid_from,
        valid_until=coupon.valid_until,
        created_at=coupon.created_at
    )


@router.delete("/{coupon_id}")
async def deactivate_coupon(
    coupon_id: str,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate a coupon

    Note: This doesn't delete the coupon, just marks it as inactive.
    Historical data is preserved for analytics.
    """
    success = await coupon_service.deactivate_coupon(db, coupon_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    # Log admin action
    await log_admin_action(
        db=db,
        admin_id=str(admin.id),
        action="deactivate_coupon",
        target_type="coupon",
        target_id=coupon_id,
        details={},
        request=request
    )

    return {"message": "Coupon deactivated successfully"}


@router.get("/{coupon_id}/usages", response_model=CouponUsageListResponse)
async def get_coupon_usages(
    coupon_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get usage history for a specific coupon

    Returns list of all times this coupon was used, including:
    - Who applied it
    - Discount given
    - Reward credited
    - When it was used
    """
    usages, total = await coupon_service.get_coupon_usages(
        db=db,
        coupon_id=coupon_id,
        page=page,
        page_size=page_size
    )

    return CouponUsageListResponse(
        usages=[
            CouponUsageResponse(
                id=str(u.id),
                coupon_id=str(u.coupon_id),
                coupon_code=u.coupon.code if u.coupon else "",
                applied_by_id=str(u.applied_by_id),
                applied_by_name=u.applied_by.full_name if u.applied_by else None,
                applied_by_email=u.applied_by.email if u.applied_by else None,
                owner_id=str(u.owner_id),
                owner_name=u.coupon.owner_name if u.coupon else None,
                order_id=u.order_id,
                original_amount=u.original_amount,
                discount_given=u.discount_given,
                final_amount=u.final_amount,
                reward_given=u.reward_given,
                applied_at=u.applied_at
            )
            for u in usages
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{coupon_id}/stats", response_model=CouponStatsResponse)
async def get_coupon_stats(
    coupon_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed statistics for a specific coupon
    """
    coupon = await coupon_service.get_coupon_by_id(db, coupon_id)

    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    # Get recent usages
    usages, total = await coupon_service.get_coupon_usages(
        db=db,
        coupon_id=coupon_id,
        page=1,
        page_size=10
    )

    coupon_response = CouponResponse(
        id=str(coupon.id),
        code=coupon.code,
        owner_id=str(coupon.owner_id) if coupon.owner_id else None,
        owner_name=coupon.owner_name,
        owner_email=coupon.owner_email,
        owner_phone=coupon.owner_phone,
        category=coupon.category.value,
        name=coupon.name,
        description=coupon.description,
        discount_amount=coupon.discount_amount,
        discount_amount_inr=coupon.discount_amount / 100,
        reward_amount=coupon.reward_amount,
        reward_amount_inr=coupon.reward_amount / 100,
        total_uses=coupon.total_uses,
        total_discount_given=coupon.total_discount_given,
        total_reward_earned=coupon.total_reward_earned,
        status=coupon.status.value,
        is_active=coupon.is_active,
        valid_from=coupon.valid_from,
        valid_until=coupon.valid_until,
        created_at=coupon.created_at
    )

    return CouponStatsResponse(
        coupon=coupon_response,
        usage_count=total,
        total_discount=coupon.total_discount_given,
        total_reward=coupon.total_reward_earned,
        recent_usages=[
            CouponUsageResponse(
                id=str(u.id),
                coupon_id=str(u.coupon_id),
                coupon_code=u.coupon.code if u.coupon else "",
                applied_by_id=str(u.applied_by_id),
                applied_by_name=u.applied_by.full_name if u.applied_by else None,
                applied_by_email=u.applied_by.email if u.applied_by else None,
                owner_id=str(u.owner_id),
                owner_name=None,
                order_id=u.order_id,
                original_amount=u.original_amount,
                discount_given=u.discount_given,
                final_amount=u.final_amount,
                reward_given=u.reward_given,
                applied_at=u.applied_at
            )
            for u in usages
        ],
        daily_usage=[]  # TODO: Implement daily usage aggregation
    )
