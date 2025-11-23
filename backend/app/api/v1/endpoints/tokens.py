from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.token_balance import TokenTransaction, TokenPurchase
from app.modules.auth.dependencies import get_current_user
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
    current_user: User = Depends(get_current_user),
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
    """
    balance_info = await token_manager.get_balance_info(db, str(current_user.id))

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

    Packages:
    - Starter: 50K tokens - ₹99
    - Pro: 200K tokens - ₹349
    - Unlimited: 1M tokens - ₹1499
    """
    # Token packages
    packages = {
        "starter": {"tokens": 50000, "price": 9900, "name": "Starter Pack"},
        "pro": {"tokens": 200000, "price": 34900, "name": "Pro Pack"},
        "unlimited": {"tokens": 1000000, "price": 149900, "name": "Unlimited Pack"}
    }

    if purchase_data.package not in packages:
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

    # In production, integrate with Razorpay here
    payment_url = f"https://payment.example.com/pay/{purchase.id}"

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

    Example codes:
    - WELCOME2024: 10K bonus tokens
    - LAUNCH50: 50K bonus tokens
    """
    # Promo codes database (in production, store in DB)
    promo_codes = {
        "WELCOME2024": 10000,
        "LAUNCH50": 50000,
        "BETA100": 100000
    }

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
    """
    return {
        "packages": [
            {
                "id": "starter",
                "name": "Starter Pack",
                "tokens": 50000,
                "price": 99,
                "currency": "INR",
                "features": [
                    "50,000 tokens",
                    "Valid for 3 months",
                    "All AI agents",
                    "Priority support"
                ]
            },
            {
                "id": "pro",
                "name": "Pro Pack",
                "tokens": 200000,
                "price": 349,
                "currency": "INR",
                "popular": True,
                "features": [
                    "200,000 tokens",
                    "Valid for 6 months",
                    "All AI agents",
                    "Priority support",
                    "Advanced analytics"
                ]
            },
            {
                "id": "unlimited",
                "name": "Unlimited Pack",
                "tokens": 1000000,
                "price": 1499,
                "currency": "INR",
                "features": [
                    "1,000,000 tokens",
                    "Valid for 12 months",
                    "All AI agents",
                    "Dedicated support",
                    "Advanced analytics",
                    "Custom integrations"
                ]
            }
        ],
        "monthly_plans": [
            {
                "id": "free",
                "name": "Free Tier",
                "price": 0,
                "tokens_per_month": 10000,
                "features": [
                    "10,000 tokens/month",
                    "Rollover up to 5,000 tokens",
                    "Basic support"
                ]
            },
            {
                "id": "basic",
                "name": "Basic",
                "price": 299,
                "tokens_per_month": 50000,
                "features": [
                    "50,000 tokens/month",
                    "Rollover up to 25,000 tokens",
                    "Priority support"
                ]
            },
            {
                "id": "pro_monthly",
                "name": "Pro",
                "price": 999,
                "tokens_per_month": 250000,
                "features": [
                    "250,000 tokens/month",
                    "Rollover up to 125,000 tokens",
                    "Priority support",
                    "Advanced analytics"
                ]
            }
        ]
    }
