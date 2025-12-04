from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import calendar
import uuid as uuid_module

from app.models.token_balance import TokenBalance, TokenTransaction, TokenPurchase
from app.models.user import User
from app.core.config import settings
from app.core.logging_config import logger


def to_str(value: Union[str, uuid_module.UUID]) -> str:
    """Convert UUID to string if needed - SQLite needs strings"""
    if isinstance(value, uuid_module.UUID):
        return str(value)
    return value


class TokenManager:
    """
    Token management system (like Bolt.new & Lovable.dev)

    Features:
    - Real-time token balance tracking
    - Transaction history
    - Monthly allowance with rollover
    - Premium token packages
    - Usage analytics
    """

    @staticmethod
    async def get_or_create_balance(
        db: AsyncSession,
        user_id: Union[str, uuid_module.UUID]
    ) -> TokenBalance:
        """Get or create token balance for user"""
        user_uuid = to_str(user_id)
        result = await db.execute(
            select(TokenBalance).where(TokenBalance.user_id == user_uuid)
        )
        balance = result.scalar_one_or_none()

        if not balance:
            # Create new balance with initial allowance from config
            free_tier_tokens = settings.FREE_TIER_TOKENS
            monthly_allowance = settings.FREE_TIER_MONTHLY_ALLOWANCE
            balance = TokenBalance(
                user_id=user_uuid,
                total_tokens=free_tier_tokens,
                remaining_tokens=free_tier_tokens,
                monthly_allowance=monthly_allowance,
                month_reset_date=TokenManager._get_next_month_date()
            )
            db.add(balance)
            await db.commit()
            await db.refresh(balance)
            logger.info(f"Created token balance for user {user_id}")

        return balance

    @staticmethod
    async def check_and_deduct_tokens(
        db: AsyncSession,
        user_id: Union[str, uuid_module.UUID],
        tokens_required: int,
        project_id: Optional[Union[str, uuid_module.UUID]] = None,
        agent_type: Optional[str] = None,
        model_used: str = "haiku"
    ) -> tuple[bool, Optional[str]]:
        """
        Check if user has enough tokens and deduct them

        Returns:
            (success: bool, error_message: Optional[str])
        """
        balance = await TokenManager.get_or_create_balance(db, user_id)

        # Check monthly reset
        if balance.month_reset_date and datetime.utcnow() >= balance.month_reset_date:
            await TokenManager._reset_monthly_allowance(db, balance)

        # Check if enough tokens available
        total_available = balance.remaining_tokens

        if total_available < tokens_required:
            shortage = tokens_required - total_available
            return False, f"Insufficient tokens. Need {shortage} more tokens. Current balance: {total_available}"

        # Deduct tokens (priority: monthly → rollover → premium)
        monthly_available = balance.monthly_allowance - balance.monthly_used
        premium_available = balance.premium_tokens - balance.premium_used

        tokens_to_deduct = tokens_required
        monthly_deducted = 0
        premium_deducted = 0
        rollover_deducted = 0

        # 1. Use monthly allowance first
        if monthly_available > 0:
            monthly_deducted = min(tokens_to_deduct, monthly_available)
            balance.monthly_used += monthly_deducted
            tokens_to_deduct -= monthly_deducted

        # 2. Use rollover tokens
        if tokens_to_deduct > 0 and balance.rollover_tokens > 0:
            rollover_deducted = min(tokens_to_deduct, balance.rollover_tokens)
            balance.rollover_tokens -= rollover_deducted
            tokens_to_deduct -= rollover_deducted

        # 3. Use premium tokens
        if tokens_to_deduct > 0 and premium_available > 0:
            premium_deducted = min(tokens_to_deduct, premium_available)
            balance.premium_used += premium_deducted
            tokens_to_deduct -= premium_deducted

        # Update totals
        balance.used_tokens += tokens_required
        balance.remaining_tokens = (
            (balance.monthly_allowance - balance.monthly_used) +
            balance.rollover_tokens +
            (balance.premium_tokens - balance.premium_used)
        )
        balance.total_requests += 1
        balance.requests_today += 1
        balance.last_request_at = datetime.utcnow()

        await db.commit()

        # Record transaction
        await TokenManager.record_transaction(
            db=db,
            user_id=user_id,
            project_id=project_id,
            transaction_type="usage",
            tokens_changed=-tokens_required,
            tokens_before=total_available,
            tokens_after=balance.remaining_tokens,
            agent_type=agent_type,
            model_used=model_used,
            description=f"Token usage for {agent_type or 'project'}"
        )

        logger.info(
            f"Deducted {tokens_required} tokens from user {user_id}. "
            f"Remaining: {balance.remaining_tokens}"
        )

        return True, None

    @staticmethod
    async def add_tokens(
        db: AsyncSession,
        user_id: Union[str, uuid_module.UUID],
        tokens_to_add: int,
        transaction_type: str = "purchase",
        description: str = "Token purchase",
        is_premium: bool = True
    ) -> TokenBalance:
        """Add tokens to user balance"""
        balance = await TokenManager.get_or_create_balance(db, user_id)

        tokens_before = balance.remaining_tokens

        if is_premium:
            balance.premium_tokens += tokens_to_add
        else:
            balance.monthly_allowance += tokens_to_add

        balance.total_tokens += tokens_to_add
        balance.remaining_tokens += tokens_to_add

        await db.commit()

        # Record transaction
        await TokenManager.record_transaction(
            db=db,
            user_id=user_id,
            transaction_type=transaction_type,
            tokens_changed=tokens_to_add,
            tokens_before=tokens_before,
            tokens_after=balance.remaining_tokens,
            description=description
        )

        logger.info(f"Added {tokens_to_add} tokens to user {user_id}")

        return balance

    @staticmethod
    async def record_transaction(
        db: AsyncSession,
        user_id: Union[str, uuid_module.UUID],
        transaction_type: str,
        tokens_changed: int,
        tokens_before: int,
        tokens_after: int,
        project_id: Optional[Union[str, uuid_module.UUID]] = None,
        agent_type: Optional[str] = None,
        model_used: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TokenTransaction:
        """Record a token transaction"""

        # Calculate cost estimate
        from app.utils.claude_client import claude_client
        cost_usd = 0
        cost_inr = 0

        if input_tokens > 0 or output_tokens > 0:
            cost_usd = claude_client.calculate_cost(
                input_tokens, output_tokens, model_used or "haiku"
            )
            cost_inr = claude_client.calculate_cost_in_paise(
                input_tokens, output_tokens, model_used or "haiku"
            )

        transaction = TokenTransaction(
            user_id=to_str(user_id),
            project_id=to_str(project_id) if project_id else None,
            transaction_type=transaction_type,
            tokens_before=tokens_before,
            tokens_changed=tokens_changed,
            tokens_after=tokens_after,
            description=description,
            agent_type=agent_type,
            model_used=model_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=int(cost_usd * 100),  # Convert to cents
            estimated_cost_inr=cost_inr,
            metadata=metadata
        )

        db.add(transaction)
        await db.commit()

        return transaction

    @staticmethod
    async def get_balance_info(
        db: AsyncSession,
        user_id: Union[str, uuid_module.UUID]
    ) -> Dict[str, Any]:
        """Get comprehensive balance information (like Bolt.new dashboard)"""
        user_uuid = to_str(user_id)
        balance = await TokenManager.get_or_create_balance(db, user_uuid)

        # Get recent transactions
        result = await db.execute(
            select(TokenTransaction)
            .where(TokenTransaction.user_id == user_uuid)
            .order_by(TokenTransaction.created_at.desc())
            .limit(10)
        )
        recent_transactions = result.scalars().all()

        # Calculate statistics
        monthly_used_percentage = (
            (balance.monthly_used / balance.monthly_allowance * 100)
            if balance.monthly_allowance > 0 else 0
        )

        return {
            "total_tokens": balance.total_tokens,
            "used_tokens": balance.used_tokens,
            "remaining_tokens": balance.remaining_tokens,
            "monthly_allowance": balance.monthly_allowance,
            "monthly_used": balance.monthly_used,
            "monthly_remaining": balance.monthly_allowance - balance.monthly_used,
            "monthly_used_percentage": round(monthly_used_percentage, 2),
            "premium_tokens": balance.premium_tokens,
            "premium_used": balance.premium_used,
            "premium_remaining": balance.premium_tokens - balance.premium_used,
            "rollover_tokens": balance.rollover_tokens,
            "month_reset_date": balance.month_reset_date.isoformat() if balance.month_reset_date else None,
            "total_requests": balance.total_requests,
            "requests_today": balance.requests_today,
            "last_request_at": balance.last_request_at.isoformat() if balance.last_request_at else None,
            "max_tokens_per_request": balance.max_tokens_per_request,
            "max_requests_per_day": balance.max_requests_per_day,
            "recent_transactions": [
                {
                    "type": t.transaction_type,
                    "tokens": t.tokens_changed,
                    "description": t.description,
                    "agent": t.agent_type,
                    "timestamp": t.created_at.isoformat()
                }
                for t in recent_transactions
            ]
        }

    @staticmethod
    async def _reset_monthly_allowance(
        db: AsyncSession,
        balance: TokenBalance
    ):
        """Reset monthly allowance and handle rollover"""
        # Calculate rollover (unused tokens from current month)
        unused_monthly = balance.monthly_allowance - balance.monthly_used

        # Add to rollover (max 50% of monthly allowance)
        max_rollover = balance.monthly_allowance // 2
        rollover_to_add = min(unused_monthly, max_rollover)

        balance.rollover_tokens += rollover_to_add
        balance.monthly_used = 0
        balance.requests_today = 0
        balance.month_reset_date = TokenManager._get_next_month_date()

        await db.commit()

        logger.info(
            f"Reset monthly allowance for user {balance.user_id}. "
            f"Rollover: {rollover_to_add} tokens"
        )

    @staticmethod
    def _get_next_month_date() -> datetime:
        """Get first day of next month"""
        today = datetime.utcnow()
        if today.month == 12:
            return datetime(today.year + 1, 1, 1)
        else:
            return datetime(today.year, today.month + 1, 1)


# Singleton instance
token_manager = TokenManager()
