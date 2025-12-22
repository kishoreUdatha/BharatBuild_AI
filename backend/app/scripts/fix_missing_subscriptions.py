"""
Fix Missing Subscriptions Script
================================
This script finds users who have TokenPurchase records but NO active Subscription,
and creates PRO subscriptions for them.

Run with: python -m app.scripts.fix_missing_subscriptions

This is a ONE-TIME migration script to fix historical data.
"""

import asyncio
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_local
from app.core.logging_config import logger
from app.models.billing import Plan, PlanType, Subscription, SubscriptionStatus
from app.models.token_balance import TokenPurchase

# Use relativedelta for date math
try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    # Fallback if dateutil not available
    from datetime import timedelta
    class relativedelta:
        def __init__(self, years=0):
            self.delta = timedelta(days=years * 365)
        def __radd__(self, other):
            return other + self.delta


async def get_or_create_pro_plan(db: AsyncSession) -> Plan:
    """Get existing PRO plan or create one"""
    result = await db.execute(
        select(Plan).where(
            Plan.plan_type == PlanType.PRO,
            Plan.is_active == True
        ).limit(1)
    )
    pro_plan = result.scalar_one_or_none()

    if not pro_plan:
        pro_plan = Plan(
            name="PRO Plan",
            slug="pro-token-purchase",
            plan_type=PlanType.PRO,
            description="PRO access via token purchase - Full features including academic documents",
            price=449900,  # Default price
            currency="INR",
            billing_period="lifetime",
            token_limit=None,
            project_limit=None,
            documents_per_month=None,
            document_types_allowed=["report", "srs", "sds", "ppt", "viva"],
            features=["unlimited_tokens", "all_documents", "priority_support", "academic_docs"],
            allowed_models=["haiku", "sonnet", "opus"],
            priority_queue=True,
            is_active=True
        )
        db.add(pro_plan)
        await db.flush()
        logger.info(f"Created PRO plan: {pro_plan.id}")

    return pro_plan


async def fix_missing_subscriptions():
    """
    Find users with TokenPurchase but no Subscription and create PRO subscriptions.
    """
    session_factory = get_session_local()
    async with session_factory() as db:
        try:
            # Get all users with successful token purchases
            token_purchases_result = await db.execute(
                select(TokenPurchase).where(
                    TokenPurchase.payment_status == "success",
                    TokenPurchase.is_expired == False
                )
            )
            token_purchases = token_purchases_result.scalars().all()

            if not token_purchases:
                logger.info("No token purchases found")
                return

            logger.info(f"Found {len(token_purchases)} token purchases to check")

            # Get PRO plan
            pro_plan = await get_or_create_pro_plan(db)

            fixed_count = 0
            skipped_count = 0

            for purchase in token_purchases:
                user_id = purchase.user_id

                # Check if user already has active subscription
                existing_sub_result = await db.execute(
                    select(Subscription).where(
                        Subscription.user_id == user_id,
                        Subscription.status == SubscriptionStatus.ACTIVE
                    ).limit(1)
                )
                existing_sub = existing_sub_result.scalar_one_or_none()

                if existing_sub:
                    logger.info(f"User {user_id} already has active subscription, skipping")
                    skipped_count += 1
                    continue

                # Create subscription for this user
                now = datetime.utcnow()
                new_subscription = Subscription(
                    user_id=user_id,
                    plan_id=pro_plan.id,
                    status=SubscriptionStatus.ACTIVE,
                    razorpay_subscription_id=None,
                    razorpay_customer_id=None,
                    current_period_start=purchase.valid_from or now,
                    current_period_end=now + relativedelta(years=100),
                    cancel_at_period_end=False
                )
                db.add(new_subscription)
                fixed_count += 1
                logger.info(f"Created PRO subscription for user {user_id}")

            await db.commit()

            logger.info(f"Migration complete: {fixed_count} subscriptions created, {skipped_count} skipped")
            print(f"\n✅ Migration complete!")
            print(f"   - Subscriptions created: {fixed_count}")
            print(f"   - Users already subscribed: {skipped_count}")

        except Exception as e:
            await db.rollback()
            logger.error(f"Migration failed: {e}")
            print(f"\n❌ Migration failed: {e}")
            raise


async def main():
    """Main entry point"""
    print("\n" + "=" * 60)
    print("FIX MISSING SUBSCRIPTIONS MIGRATION")
    print("=" * 60)
    print("\nThis script will:")
    print("1. Find users with TokenPurchase records")
    print("2. Check if they have an active Subscription")
    print("3. Create PRO subscription if missing")
    print("\n" + "-" * 60)

    confirm = input("\nProceed? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Cancelled.")
        return

    await fix_missing_subscriptions()


if __name__ == "__main__":
    asyncio.run(main())
