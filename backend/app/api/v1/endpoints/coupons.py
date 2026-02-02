"""
Coupon API Endpoints - Public endpoints for coupon validation and wallet management

Endpoints:
- POST /coupons/validate - Validate a coupon code at checkout
- POST /coupons/apply - Apply coupon after successful payment
- GET /coupons/my-coupon - Get user's own coupon and wallet info
- GET /coupons/wallet - Get user's wallet balance
- GET /coupons/wallet/transactions - Get wallet transaction history
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.models.user import User
from app.services.coupon_service import coupon_service
from app.schemas.coupon import (
    CouponValidateRequest,
    CouponValidateResponse,
    CouponApplyRequest,
    CouponApplyResponse,
    MyCouponResponse,
    WalletResponse,
    WalletTransactionListResponse,
    CouponUsageResponse,
    CouponResponse,
)

router = APIRouter(prefix="/coupons", tags=["Coupons"])


@router.post("/validate", response_model=CouponValidateResponse)
async def validate_coupon(
    request: CouponValidateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate a coupon code before payment

    This endpoint checks if a coupon code is valid and returns the discount amount.
    Call this when user enters a coupon code at checkout.

    Returns:
        - valid: Whether the coupon is valid
        - discount_amount: Amount to deduct (in paise)
        - final_amount: Amount after discount (in paise)
        - message: User-friendly message
    """
    response = await coupon_service.validate_coupon(
        db=db,
        code=request.code,
        amount=request.amount,
        user_id=str(current_user.id)
    )
    return response


@router.post("/apply", response_model=CouponApplyResponse)
async def apply_coupon(
    request: CouponApplyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Apply coupon after successful payment

    Call this endpoint AFTER payment is verified successfully.
    This will:
    1. Record the coupon usage
    2. Credit reward to coupon owner's wallet

    Args:
        code: The coupon code that was applied
        order_id: Razorpay order ID
        original_amount: Original price before discount (in paise)
        discount_amount: Discount given (in paise)
        final_amount: Final amount paid (in paise)
        transaction_id: Optional transaction ID from database
    """
    success, message, coupon_usage = await coupon_service.apply_coupon(
        db=db,
        code=request.code,
        applied_by_id=str(current_user.id),
        order_id=request.order_id,
        original_amount=request.original_amount,
        discount_amount=request.discount_amount,
        final_amount=request.final_amount,
        transaction_id=request.transaction_id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    # Get owner's updated wallet balance
    coupon = await coupon_service.get_coupon_by_code(db, request.code)
    owner_wallet = await coupon_service.get_wallet(db, str(coupon.owner_id))

    return CouponApplyResponse(
        success=True,
        message=message,
        coupon_usage_id=str(coupon_usage.id) if coupon_usage else None,
        discount_given=coupon_usage.discount_given if coupon_usage else None,
        reward_credited=coupon_usage.reward_given if coupon_usage else None,
        owner_wallet_balance=owner_wallet.balance
    )


@router.get("/my-coupon", response_model=MyCouponResponse)
async def get_my_coupon(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's own coupon details and wallet info

    Returns the coupon code owned by the user (if any) along with:
    - Wallet balance
    - Total earnings
    - Recent usages (people who used their coupon)
    """
    # Get user's coupon
    coupon = await coupon_service.get_user_coupon(db, str(current_user.id))

    # Get wallet
    wallet = await coupon_service.get_wallet(db, str(current_user.id))

    # Get recent usages if user has a coupon
    recent_usages = []
    total_uses = 0
    if coupon:
        usages, total = await coupon_service.get_user_coupon_usages(
            db, str(current_user.id), page=1, page_size=5
        )
        total_uses = total
        recent_usages = [
            CouponUsageResponse(
                id=str(u.id),
                coupon_id=str(u.coupon_id),
                coupon_code=u.coupon.code if u.coupon else "",
                applied_by_id=str(u.applied_by_id),
                applied_by_name=u.applied_by.full_name if u.applied_by else None,
                applied_by_email=u.applied_by.email if u.applied_by else None,
                owner_id=str(u.owner_id),
                owner_name=None,  # Don't expose owner name to owner
                order_id=u.order_id,
                original_amount=u.original_amount,
                discount_given=u.discount_given,
                final_amount=u.final_amount,
                reward_given=u.reward_given,
                applied_at=u.applied_at
            )
            for u in usages
        ]

    # Build coupon response if exists
    coupon_response = None
    if coupon:
        coupon_response = CouponResponse(
            id=str(coupon.id),
            code=coupon.code,
            owner_id=str(coupon.owner_id),
            owner_name=current_user.full_name,
            owner_email=current_user.email,
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

    return MyCouponResponse(
        coupon=coupon_response,
        has_coupon=coupon is not None,
        wallet_balance=wallet.balance,
        wallet_balance_inr=wallet.balance / 100,
        total_earnings=wallet.total_earned,
        total_earnings_inr=wallet.total_earned / 100,
        total_uses=total_uses,
        recent_usages=recent_usages
    )


@router.get("/wallet", response_model=WalletResponse)
async def get_wallet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's wallet balance and stats
    """
    wallet = await coupon_service.get_wallet(db, str(current_user.id))

    return WalletResponse(
        id=str(wallet.id),
        user_id=str(wallet.user_id),
        balance=wallet.balance,
        balance_inr=wallet.balance / 100,
        total_earned=wallet.total_earned,
        total_used=wallet.total_used,
        total_withdrawn=wallet.total_withdrawn,
        created_at=wallet.created_at,
        updated_at=wallet.updated_at
    )


@router.get("/wallet/transactions", response_model=WalletTransactionListResponse)
async def get_wallet_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's wallet transaction history

    Returns paginated list of all credits and debits to the wallet.
    """
    from app.schemas.coupon import WalletTransactionResponse

    transactions, total, current_balance = await coupon_service.get_wallet_transactions(
        db=db,
        user_id=str(current_user.id),
        page=page,
        page_size=page_size
    )

    return WalletTransactionListResponse(
        transactions=[
            WalletTransactionResponse(
                id=str(t.id),
                wallet_id=str(t.wallet_id),
                user_id=str(t.user_id),
                transaction_type=t.transaction_type.value,
                source=t.source.value,
                amount=t.amount,
                amount_inr=t.amount / 100,
                balance_after=t.balance_after,
                description=t.description,
                reference_id=t.reference_id,
                reference_type=t.reference_type,
                created_at=t.created_at
            )
            for t in transactions
        ],
        total=total,
        page=page,
        page_size=page_size,
        current_balance=current_balance,
        current_balance_inr=current_balance / 100
    )


@router.get("/earnings", response_model=dict)
async def get_my_earnings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary of user's coupon earnings

    Returns a quick overview of earnings from referral coupons.
    """
    # Get user's coupon
    coupon = await coupon_service.get_user_coupon(db, str(current_user.id))

    # Get wallet
    wallet = await coupon_service.get_wallet(db, str(current_user.id))

    return {
        "has_coupon": coupon is not None,
        "coupon_code": coupon.code if coupon else None,
        "total_uses": coupon.total_uses if coupon else 0,
        "total_earned": wallet.total_earned,
        "total_earned_inr": wallet.total_earned / 100,
        "wallet_balance": wallet.balance,
        "wallet_balance_inr": wallet.balance / 100,
        "reward_per_use": coupon.reward_amount if coupon else 0,
        "reward_per_use_inr": (coupon.reward_amount / 100) if coupon else 0,
    }
