"""
Coupon Service - Business logic for coupon and wallet operations

Handles:
- Coupon validation and application
- Wallet management and transactions
- Reward distribution
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import Optional, List, Tuple
import logging

from app.models.coupon import (
    Coupon,
    CouponUsage,
    CouponStatus,
    CouponCategory,
    Wallet,
    WalletTransaction,
    WalletTransactionType,
    WalletTransactionSource,
)
from app.models.user import User
from app.schemas.coupon import (
    CouponCreate,
    CouponUpdate,
    CouponResponse,
    CouponValidateResponse,
    CouponUsageResponse,
    WalletResponse,
    WalletTransactionResponse,
)

logger = logging.getLogger(__name__)


class CouponService:
    """Service for managing coupons and rewards"""

    # ==================== COUPON CRUD ====================

    async def create_coupon(
        self,
        db: AsyncSession,
        coupon_data: CouponCreate,
        created_by_id: str
    ) -> Coupon:
        """
        Create a new coupon (Admin only)

        Args:
            db: Database session
            coupon_data: Coupon creation data
            created_by_id: Admin user ID who is creating the coupon

        Returns:
            Created Coupon object
        """
        # Check if code already exists
        existing = await db.execute(
            select(Coupon).where(Coupon.code == coupon_data.code.upper())
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Coupon code '{coupon_data.code}' already exists")

        # Create coupon with owner details
        coupon = Coupon(
            code=coupon_data.code.upper(),
            owner_name=coupon_data.owner_name,
            owner_email=coupon_data.owner_email,
            owner_phone=coupon_data.owner_phone,
            owner_id=None,  # No linked user account required
            category=CouponCategory(coupon_data.category.value),
            name=coupon_data.name,
            description=coupon_data.description,
            discount_amount=coupon_data.discount_amount,
            reward_amount=coupon_data.reward_amount,
            valid_from=coupon_data.valid_from or datetime.utcnow(),
            valid_until=coupon_data.valid_until,
            created_by=created_by_id,
            status=CouponStatus.ACTIVE,
            is_active=True,
        )

        db.add(coupon)
        await db.commit()
        await db.refresh(coupon)

        logger.info(f"Created coupon {coupon.code} for owner {coupon.owner_name}")
        return coupon

    async def get_coupon_by_id(
        self,
        db: AsyncSession,
        coupon_id: str
    ) -> Optional[Coupon]:
        """Get coupon by ID"""
        result = await db.execute(
            select(Coupon)
            .options(selectinload(Coupon.owner))
            .where(Coupon.id == coupon_id)
        )
        return result.scalar_one_or_none()

    async def get_coupon_by_code(
        self,
        db: AsyncSession,
        code: str
    ) -> Optional[Coupon]:
        """Get coupon by code"""
        result = await db.execute(
            select(Coupon)
            .options(selectinload(Coupon.owner))
            .where(Coupon.code == code.upper())
        )
        return result.scalar_one_or_none()

    async def list_coupons(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Coupon], int]:
        """
        List coupons with pagination and filters

        Returns:
            Tuple of (coupons list, total count)
        """
        query = select(Coupon).options(selectinload(Coupon.owner))

        # Apply filters
        conditions = []
        if category:
            conditions.append(Coupon.category == CouponCategory(category))
        if status:
            conditions.append(Coupon.status == CouponStatus(status))
        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    Coupon.code.ilike(search_term),
                    Coupon.name.ilike(search_term),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count(Coupon.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = (await db.execute(count_query)).scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(Coupon.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        coupons = list(result.scalars().all())

        return coupons, total

    async def update_coupon(
        self,
        db: AsyncSession,
        coupon_id: str,
        update_data: CouponUpdate
    ) -> Optional[Coupon]:
        """Update coupon details"""
        coupon = await self.get_coupon_by_id(db, coupon_id)
        if not coupon:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if value is None:
                continue
            if field == 'status':
                value = CouponStatus(value)
            elif field == 'category':
                value = CouponCategory(value)
            setattr(coupon, field, value)

        coupon.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(coupon)

        logger.info(f"Updated coupon {coupon.code}")
        return coupon

    async def deactivate_coupon(
        self,
        db: AsyncSession,
        coupon_id: str
    ) -> bool:
        """Deactivate a coupon"""
        coupon = await self.get_coupon_by_id(db, coupon_id)
        if not coupon:
            return False

        coupon.is_active = False
        coupon.status = CouponStatus.INACTIVE
        coupon.updated_at = datetime.utcnow()
        await db.commit()

        logger.info(f"Deactivated coupon {coupon.code}")
        return True

    # ==================== COUPON VALIDATION ====================

    async def validate_coupon(
        self,
        db: AsyncSession,
        code: str,
        amount: int,
        user_id: str
    ) -> CouponValidateResponse:
        """
        Validate if a coupon can be applied

        Args:
            db: Database session
            code: Coupon code to validate
            amount: Order amount in paise
            user_id: User trying to apply the coupon

        Returns:
            CouponValidateResponse with validation result
        """
        coupon = await self.get_coupon_by_code(db, code)

        # Check if coupon exists
        if not coupon:
            return CouponValidateResponse(
                valid=False,
                code=code.upper(),
                message="Invalid coupon code"
            )

        # Check if coupon is active
        if not coupon.is_active or coupon.status != CouponStatus.ACTIVE:
            return CouponValidateResponse(
                valid=False,
                code=code.upper(),
                message="This coupon is no longer active"
            )

        # Check validity period
        now = datetime.utcnow()
        if coupon.valid_from and now < coupon.valid_from:
            return CouponValidateResponse(
                valid=False,
                code=code.upper(),
                message="This coupon is not yet valid"
            )

        if coupon.valid_until and now > coupon.valid_until:
            # Update status to expired
            coupon.status = CouponStatus.EXPIRED
            await db.commit()
            return CouponValidateResponse(
                valid=False,
                code=code.upper(),
                message="This coupon has expired"
            )

        # Check if user is trying to use their own coupon
        if str(coupon.owner_id) == str(user_id):
            return CouponValidateResponse(
                valid=False,
                code=code.upper(),
                message="You cannot use your own coupon code"
            )

        # Calculate discount
        discount = coupon.discount_amount
        final_amount = max(0, amount - discount)

        # Get owner name
        owner_name = None
        if coupon.owner:
            owner_name = coupon.owner.full_name or coupon.owner.email.split('@')[0]

        return CouponValidateResponse(
            valid=True,
            code=coupon.code,
            message=f"Coupon applied! You save ₹{discount/100:.0f}",
            discount_amount=discount,
            discount_amount_inr=discount / 100,
            final_amount=final_amount,
            final_amount_inr=final_amount / 100,
            coupon_id=str(coupon.id),
            owner_name=owner_name
        )

    # ==================== COUPON APPLICATION ====================

    async def apply_coupon(
        self,
        db: AsyncSession,
        code: str,
        applied_by_id: str,
        order_id: str,
        original_amount: int,
        discount_amount: int,
        final_amount: int,
        transaction_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[CouponUsage]]:
        """
        Apply coupon after successful payment

        This method:
        1. Records the coupon usage
        2. Updates coupon statistics
        3. Credits reward to owner's wallet

        Args:
            db: Database session
            code: Coupon code
            applied_by_id: User who applied the coupon
            order_id: Razorpay order ID
            original_amount: Original price in paise
            discount_amount: Discount given in paise
            final_amount: Final amount paid in paise
            transaction_id: Optional transaction ID

        Returns:
            Tuple of (success, message, coupon_usage)
        """
        coupon = await self.get_coupon_by_code(db, code)

        if not coupon:
            return False, "Invalid coupon code", None

        if coupon.owner_id is not None and str(coupon.owner_id) == str(applied_by_id):
            return False, "Cannot use your own coupon", None

        # Skip full tracking if coupon has no owner (can't track usage without owner)
        if coupon.owner_id is None:
            logger.info(f"Coupon {coupon.code} has no owner_id - skipping usage tracking, only updating stats")
            # Just update coupon statistics
            coupon.total_uses += 1
            coupon.total_discount_given += discount_amount
            coupon.updated_at = datetime.utcnow()
            await db.commit()
            return True, "Coupon applied successfully (no owner rewards)", None

        try:
            # Create coupon usage record (only when owner exists)
            coupon_usage = CouponUsage(
                coupon_id=coupon.id,
                applied_by_id=applied_by_id,
                owner_id=coupon.owner_id,
                order_id=order_id,
                transaction_id=transaction_id,
                original_amount=original_amount,
                discount_given=discount_amount,
                final_amount=final_amount,
                reward_given=coupon.reward_amount,
            )
            db.add(coupon_usage)

            # Update coupon statistics
            coupon.total_uses += 1
            coupon.total_discount_given += discount_amount
            coupon.total_reward_earned += coupon.reward_amount
            coupon.updated_at = datetime.utcnow()

            # Credit reward to owner's wallet
            if coupon.reward_amount > 0:
                wallet_transaction = await self._credit_wallet(
                    db=db,
                    user_id=str(coupon.owner_id),
                    amount=coupon.reward_amount,
                    source=WalletTransactionSource.COUPON_REWARD,
                    description=f"Reward for coupon {coupon.code} used by a customer",
                    reference_id=str(coupon_usage.id),
                    reference_type="coupon_usage"
                )

                # Link wallet transaction to coupon usage
                coupon_usage.wallet_transaction_id = wallet_transaction.id

            await db.commit()
            await db.refresh(coupon_usage)

            logger.info(
                f"Coupon {coupon.code} applied by {applied_by_id}. "
                f"Discount: ₹{discount_amount/100:.0f}, "
                f"Reward to owner: ₹{coupon.reward_amount/100:.0f}"
            )

            return True, "Coupon applied successfully", coupon_usage

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to apply coupon {code}: {e}")
            return False, f"Failed to apply coupon: {str(e)}", None

    # ==================== WALLET MANAGEMENT ====================

    async def _ensure_wallet_exists(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Wallet:
        """Ensure a wallet exists for the user, create if not"""
        result = await db.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        wallet = result.scalar_one_or_none()

        if not wallet:
            wallet = Wallet(
                user_id=user_id,
                balance=0,
                total_earned=0,
                total_used=0,
                total_withdrawn=0,
            )
            db.add(wallet)
            await db.commit()
            await db.refresh(wallet)
            logger.info(f"Created wallet for user {user_id}")

        return wallet

    async def get_wallet(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Wallet:
        """Get user's wallet, create if doesn't exist"""
        return await self._ensure_wallet_exists(db, user_id)

    async def _credit_wallet(
        self,
        db: AsyncSession,
        user_id: str,
        amount: int,
        source: WalletTransactionSource,
        description: str,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None
    ) -> WalletTransaction:
        """
        Credit amount to user's wallet

        Args:
            db: Database session
            user_id: User ID
            amount: Amount in paise to credit
            source: Source of the credit
            description: Transaction description
            reference_id: Optional reference ID
            reference_type: Optional reference type

        Returns:
            WalletTransaction record
        """
        wallet = await self._ensure_wallet_exists(db, user_id)

        # Update wallet balance
        wallet.balance += amount
        wallet.total_earned += amount
        wallet.updated_at = datetime.utcnow()

        # Create transaction record
        transaction = WalletTransaction(
            wallet_id=wallet.id,
            user_id=user_id,
            transaction_type=WalletTransactionType.CREDIT,
            source=source,
            amount=amount,
            balance_after=wallet.balance,
            description=description,
            reference_id=reference_id,
            reference_type=reference_type,
        )
        db.add(transaction)

        logger.info(f"Credited ₹{amount/100:.0f} to wallet of user {user_id}")
        return transaction

    async def debit_wallet(
        self,
        db: AsyncSession,
        user_id: str,
        amount: int,
        source: WalletTransactionSource,
        description: str,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None
    ) -> Tuple[bool, str, Optional[WalletTransaction]]:
        """
        Debit amount from user's wallet

        Returns:
            Tuple of (success, message, transaction)
        """
        wallet = await self._ensure_wallet_exists(db, user_id)

        if wallet.balance < amount:
            return False, "Insufficient wallet balance", None

        # Update wallet balance
        wallet.balance -= amount
        wallet.total_used += amount
        wallet.updated_at = datetime.utcnow()

        # Create transaction record
        transaction = WalletTransaction(
            wallet_id=wallet.id,
            user_id=user_id,
            transaction_type=WalletTransactionType.DEBIT,
            source=source,
            amount=amount,
            balance_after=wallet.balance,
            description=description,
            reference_id=reference_id,
            reference_type=reference_type,
        )
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        logger.info(f"Debited ₹{amount/100:.0f} from wallet of user {user_id}")
        return True, "Wallet debited successfully", transaction

    async def get_wallet_transactions(
        self,
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[WalletTransaction], int, int]:
        """
        Get user's wallet transactions

        Returns:
            Tuple of (transactions, total count, current balance)
        """
        wallet = await self._ensure_wallet_exists(db, user_id)

        # Get total count
        count_result = await db.execute(
            select(func.count(WalletTransaction.id))
            .where(WalletTransaction.wallet_id == wallet.id)
        )
        total = count_result.scalar() or 0

        # Get transactions
        result = await db.execute(
            select(WalletTransaction)
            .where(WalletTransaction.wallet_id == wallet.id)
            .order_by(WalletTransaction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        transactions = list(result.scalars().all())

        return transactions, total, wallet.balance

    # ==================== COUPON USAGE HISTORY ====================

    async def get_coupon_usages(
        self,
        db: AsyncSession,
        coupon_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[CouponUsage], int]:
        """Get usage history for a specific coupon"""
        # Get total count
        count_result = await db.execute(
            select(func.count(CouponUsage.id))
            .where(CouponUsage.coupon_id == coupon_id)
        )
        total = count_result.scalar() or 0

        # Get usages
        result = await db.execute(
            select(CouponUsage)
            .options(
                selectinload(CouponUsage.applied_by),
                selectinload(CouponUsage.coupon)
            )
            .where(CouponUsage.coupon_id == coupon_id)
            .order_by(CouponUsage.applied_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        usages = list(result.scalars().all())

        return usages, total

    async def get_user_coupon_usages(
        self,
        db: AsyncSession,
        owner_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[CouponUsage], int]:
        """Get coupon usages where user is the owner (earned rewards)"""
        # Get total count
        count_result = await db.execute(
            select(func.count(CouponUsage.id))
            .where(CouponUsage.owner_id == owner_id)
        )
        total = count_result.scalar() or 0

        # Get usages
        result = await db.execute(
            select(CouponUsage)
            .options(
                selectinload(CouponUsage.applied_by),
                selectinload(CouponUsage.coupon)
            )
            .where(CouponUsage.owner_id == owner_id)
            .order_by(CouponUsage.applied_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        usages = list(result.scalars().all())

        return usages, total

    # ==================== USER'S OWN COUPON ====================

    async def get_user_coupon(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[Coupon]:
        """Get coupon owned by user (if any)"""
        result = await db.execute(
            select(Coupon)
            .where(
                and_(
                    Coupon.owner_id == user_id,
                    Coupon.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()

    # ==================== ANALYTICS ====================

    async def get_coupon_analytics(
        self,
        db: AsyncSession
    ) -> dict:
        """Get overall coupon analytics for admin"""
        # Total coupons
        total_coupons = (await db.execute(
            select(func.count(Coupon.id))
        )).scalar() or 0

        # Active coupons
        active_coupons = (await db.execute(
            select(func.count(Coupon.id))
            .where(Coupon.is_active == True)
        )).scalar() or 0

        # Total uses
        total_uses = (await db.execute(
            select(func.count(CouponUsage.id))
        )).scalar() or 0

        # Total discount given
        total_discount = (await db.execute(
            select(func.coalesce(func.sum(CouponUsage.discount_given), 0))
        )).scalar() or 0

        # Total rewards paid
        total_rewards = (await db.execute(
            select(func.coalesce(func.sum(CouponUsage.reward_given), 0))
        )).scalar() or 0

        # Coupons by category
        category_counts = {}
        for category in CouponCategory:
            count = (await db.execute(
                select(func.count(Coupon.id))
                .where(Coupon.category == category)
            )).scalar() or 0
            category_counts[category.value] = count

        # Top 5 coupons by usage
        top_coupons_result = await db.execute(
            select(Coupon)
            .options(selectinload(Coupon.owner))
            .order_by(Coupon.total_uses.desc())
            .limit(5)
        )
        top_coupons = list(top_coupons_result.scalars().all())

        return {
            "total_coupons": total_coupons,
            "active_coupons": active_coupons,
            "total_uses": total_uses,
            "total_discount_given": total_discount,
            "total_discount_given_inr": total_discount / 100,
            "total_rewards_paid": total_rewards,
            "total_rewards_paid_inr": total_rewards / 100,
            "coupons_by_category": category_counts,
            "top_coupons": top_coupons,
        }


# Singleton instance
coupon_service = CouponService()
