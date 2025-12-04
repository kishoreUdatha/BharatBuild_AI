from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.models.token_balance import TokenTransaction, TokenPurchase
from app.modules.auth.dependencies import get_current_user, get_optional_current_user
from app.utils.token_manager import token_manager
from app.core.logging_config import logger

router = APIRouter()


class TokenBalanceResponse(BaseModel):
    """Token balance response (like Bolt.new)"""
    total_tokens: int
    used_tokens: int
    remaining_tokens: int
    monthly_allowance: int
    monthly_used: int
    monthly_remaining: int
    monthly_used_percentage: float
    premium_tokens: int
    premium_remaining: int
    rollover_tokens: int
    month_reset_date: Optional[str] = None
    total_requests: int
    requests_today: int
    last_request_at: Optional[str] = None


class TokenTransactionResponse(BaseModel):
    """Token transaction response"""
    type: str
    tokens: int
    description: str = None
    agent: str = None
    timestamp: str

    class Config:
        from_attributes = True


class TokenPurchaseRequest(BaseModel):
    """Token purchase request"""
    package: str  # 'starter', 'pro', 'unlimited'


class TokenPurchaseResponse(BaseModel):
    """Token purchase response"""
    package_name: str
    tokens_purchased: int
    amount_paid: int
    currency: str
    payment_url: str = None


@router.get("/balance", response_model=TokenBalanceResponse)
async def get_token_balance(
    user_id: Optional[str] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current token balance (like Bolt.new)

    Shows:
    - Total tokens
    - Used tokens
    - Remaining tokens
    - Monthly allowance
    - Premium tokens
    - Rollover tokens

    In development mode, returns mock data if not authenticated.
    """
    # Return mock data in dev mode if not authenticated
    if user_id is None:
        if settings.is_dev_mode():
            mock_data = settings.get_mock_token_data()
            return TokenBalanceResponse(
                total_tokens=mock_data["total_tokens"],
                used_tokens=mock_data["used_tokens"],
                remaining_tokens=mock_data["remaining_tokens"],
                monthly_allowance=mock_data["monthly_allowance"],
                monthly_used=mock_data["monthly_used"],
                monthly_remaining=mock_data["monthly_remaining"],
                monthly_used_percentage=round((mock_data["monthly_used"] / mock_data["monthly_allowance"]) * 100, 1) if mock_data["monthly_allowance"] > 0 else 0,
                premium_tokens=mock_data["total_tokens"] - mock_data["monthly_allowance"],
                premium_remaining=mock_data["total_tokens"] - mock_data["monthly_allowance"],
                rollover_tokens=0,
                month_reset_date=None,
                total_requests=10,
                requests_today=2,
                last_request_at=None
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

    balance_info = await token_manager.get_balance_info(db, user_id)

    return TokenBalanceResponse(
        total_tokens=balance_info["total_tokens"],
        used_tokens=balance_info["used_tokens"],
        remaining_tokens=balance_info["remaining_tokens"],
        monthly_allowance=balance_info["monthly_allowance"],
        monthly_used=balance_info["monthly_used"],
        monthly_remaining=balance_info["monthly_remaining"],
        monthly_used_percentage=balance_info["monthly_used_percentage"],
        premium_tokens=balance_info["premium_tokens"],
        premium_remaining=balance_info["premium_remaining"],
        rollover_tokens=balance_info["rollover_tokens"],
        month_reset_date=balance_info["month_reset_date"],
        total_requests=balance_info["total_requests"],
        requests_today=balance_info["requests_today"],
        last_request_at=balance_info["last_request_at"]
    )


@router.get("/transactions", response_model=List[TokenTransactionResponse])
async def get_token_transactions(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get token transaction history (like Bolt.new transaction log)

    Shows detailed history of all token usage, purchases, and bonuses
    """
    result = await db.execute(
        select(TokenTransaction)
        .where(TokenTransaction.user_id == current_user.id)
        .order_by(TokenTransaction.created_at.desc())
        .limit(limit)
    )
    transactions = result.scalars().all()

    return [
        TokenTransactionResponse(
            type=t.transaction_type,
            tokens=t.tokens_changed,
            description=t.description,
            agent=t.agent_type,
            timestamp=t.created_at.isoformat()
        )
        for t in transactions
    ]


@router.get("/analytics")
async def get_token_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get token usage analytics (like Bolt.new/Lovable.dev analytics)

    Provides:
    - Usage trends
    - Most used agents
    - Cost breakdown
    - Efficiency metrics
    """
    # Get all transactions for analytics
    result = await db.execute(
        select(TokenTransaction)
        .where(TokenTransaction.user_id == current_user.id)
        .order_by(TokenTransaction.created_at.desc())
    )
    transactions = result.scalars().all()

    # Calculate analytics
    total_usage = sum(abs(t.tokens_changed) for t in transactions if t.tokens_changed < 0)
    total_added = sum(t.tokens_changed for t in transactions if t.tokens_changed > 0)

    # Agent usage breakdown
    agent_usage = {}
    for t in transactions:
        if t.agent_type and t.tokens_changed < 0:
            agent_usage[t.agent_type] = agent_usage.get(t.agent_type, 0) + abs(t.tokens_changed)

    # Model usage
    model_usage = {}
    for t in transactions:
        if t.model_used and t.tokens_changed < 0:
            model_usage[t.model_used] = model_usage.get(t.model_used, 0) + abs(t.tokens_changed)

    # Cost breakdown
    total_cost_usd = sum(t.estimated_cost_usd or 0 for t in transactions) / 100  # Convert from cents
    total_cost_inr = sum(t.estimated_cost_inr or 0 for t in transactions) / 100  # Convert from paise

    return {
        "total_tokens_used": total_usage,
        "total_tokens_added": total_added,
        "total_transactions": len(transactions),
        "agent_usage_breakdown": agent_usage,
        "model_usage_breakdown": model_usage,
        "estimated_cost": {
            "usd": round(total_cost_usd, 2),
            "inr": round(total_cost_inr, 2)
        },
        "average_tokens_per_request": round(total_usage / len(transactions), 2) if transactions else 0
    }


@router.post("/purchase", response_model=TokenPurchaseResponse)
async def purchase_tokens(
    purchase_data: TokenPurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Purchase token package (like Bolt.new pricing)

    Packages are configurable via environment variables.
    """
    # Token packages from config
    packages = settings.get_token_packages()

    if purchase_data.package not in packages or not packages[purchase_data.package]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid package. Choose: starter, pro, or unlimited"
        )

    package = packages[purchase_data.package]

    # Create Razorpay order (simplified - implement Razorpay integration)
    # For now, we'll create a pending purchase record

    purchase = TokenPurchase(
        user_id=current_user.id,
        package_name=package["name"],
        tokens_purchased=package["tokens"],
        amount_paid=package["price"],
        currency="INR",
        payment_status="pending"
    )

    db.add(purchase)
    await db.commit()
    await db.refresh(purchase)

    logger.info(f"Created token purchase for user {current_user.id}: {package['name']}")

    # Get payment URL from config
    payment_url = settings.get_payment_url(str(purchase.id))

    return TokenPurchaseResponse(
        package_name=package["name"],
        tokens_purchased=package["tokens"],
        amount_paid=package["price"],
        currency="INR",
        payment_url=payment_url
    )


@router.post("/redeem-code")
async def redeem_promo_code(
    promo_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Redeem promo code for bonus tokens (like Bolt.new/Lovable.dev)

    Promo codes are configurable via environment variables or database.
    """
    # Get promo codes from config
    promo_codes = settings.get_promo_codes()

    if promo_code not in promo_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid promo code"
        )

    bonus_tokens = promo_codes[promo_code]

    # Add bonus tokens
    balance = await token_manager.add_tokens(
        db=db,
        user_id=str(current_user.id),
        tokens_to_add=bonus_tokens,
        transaction_type="bonus",
        description=f"Promo code: {promo_code}",
        is_premium=True
    )

    logger.info(f"User {current_user.id} redeemed promo code: {promo_code}")

    return {
        "message": "Promo code redeemed successfully!",
        "bonus_tokens": bonus_tokens,
        "new_balance": balance.remaining_tokens
    }


@router.get("/packages")
async def get_token_packages():
    """
    Get available token packages (like Bolt.new pricing page)

    Packages are configurable via environment variables.
    """
    # Get packages from config
    packages = settings.get_token_packages()
    monthly_plans = settings.get_monthly_plans()

    # Build response with package details
    package_list = []
    for pkg_id, pkg in packages.items():
        if pkg:
            package_list.append({
                "id": pkg_id,
                "name": pkg.get("name", pkg_id.title()),
                "tokens": pkg.get("tokens", 0),
                "price": pkg.get("price", 0) // 100,  # Convert paise to rupees for display
                "currency": "INR",
                "popular": pkg_id == "pro",
                "features": _get_package_features(pkg_id, pkg.get("tokens", 0))
            })

    # Build monthly plans response
    monthly_list = []
    for plan_id, plan in monthly_plans.items():
        if plan:
            monthly_list.append({
                "id": plan_id if plan_id != "pro" else "pro_monthly",
                "name": plan.get("name", plan_id.title()),
                "price": plan.get("price", 0) // 100,  # Convert paise to rupees for display
                "tokens_per_month": plan.get("tokens", 0),
                "features": _get_plan_features(plan_id, plan.get("tokens", 0))
            })

    return {
        "packages": package_list,
        "monthly_plans": monthly_list
    }


def _get_package_features(pkg_id: str, tokens: int) -> list:
    """Get features list for a package"""
    base_features = [
        f"{tokens:,} tokens",
        "All AI agents",
    ]

    if pkg_id == "starter":
        return base_features + ["Valid for 3 months", "Priority support"]
    elif pkg_id == "pro":
        return base_features + ["Valid for 6 months", "Priority support", "Advanced analytics"]
    elif pkg_id == "unlimited":
        return base_features + ["Valid for 12 months", "Dedicated support", "Advanced analytics", "Custom integrations"]

    return base_features


def _get_plan_features(plan_id: str, tokens: int) -> list:
    """Get features list for a monthly plan"""
    rollover = tokens // 2

    if plan_id == "free":
        return [
            f"{tokens:,} tokens/month",
            f"Rollover up to {rollover:,} tokens",
            "Basic support"
        ]
    elif plan_id == "basic":
        return [
            f"{tokens:,} tokens/month",
            f"Rollover up to {rollover:,} tokens",
            "Priority support"
        ]
    else:  # pro
        return [
            f"{tokens:,} tokens/month",
            f"Rollover up to {rollover:,} tokens",
            "Priority support",
            "Advanced analytics"
        ]
