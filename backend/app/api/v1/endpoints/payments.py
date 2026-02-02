"""
RAZORPAY PAYMENT INTEGRATION
============================
Complete payment flow with order creation, verification, and webhooks.

Flow:
1. User clicks Buy → /payments/create-order → Returns Razorpay order_id
2. Frontend opens Razorpay checkout with order_id
3. User completes payment → Razorpay redirects with payment details
4. Frontend calls /payments/verify → Verify signature & credit tokens
5. Webhook /payments/webhook → Backup verification for failed redirects
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import hmac
import hashlib
import json

from app.core.database import get_db
from app.core.config import settings
from app.core.logging_config import logger
from app.models.user import User
from app.models.billing import Transaction, TransactionStatus, Subscription, SubscriptionStatus, Plan, PlanType
from app.models.token_balance import TokenPurchase
from app.modules.auth.dependencies import get_current_user
from app.utils.token_manager import token_manager
from dateutil.relativedelta import relativedelta
from app.services.coupon_service import coupon_service

# Razorpay client initialization
try:
    import razorpay
    razorpay_client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )
    RAZORPAY_AVAILABLE = bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)
except ImportError:
    razorpay_client = None
    RAZORPAY_AVAILABLE = False
    logger.warning("Razorpay SDK not installed. Payment features disabled.")


router = APIRouter()


# ========== Request/Response Models ==========

class CreateOrderRequest(BaseModel):
    """Request to create a payment order"""
    package: str  # 'starter', 'pro', 'unlimited' or plan name
    amount: Optional[int] = None  # Override amount in paise (for custom)
    coupon_code: Optional[str] = None  # Optional coupon code for discount


class CreateOrderResponse(BaseModel):
    """Response with Razorpay order details"""
    order_id: str
    amount: int  # in paise (after discount)
    original_amount: int  # in paise (before discount)
    discount_amount: int  # in paise
    currency: str
    key_id: str  # Razorpay key for frontend
    package_name: str
    tokens: int
    notes: dict
    coupon_applied: Optional[str] = None  # Coupon code if applied
    coupon_message: Optional[str] = None  # Message about coupon


class VerifyPaymentRequest(BaseModel):
    """Request to verify payment after checkout"""
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class PaymentStatusResponse(BaseModel):
    """Payment status response"""
    status: str
    message: str
    tokens_credited: Optional[int] = None
    new_balance: Optional[int] = None


# ========== Payment Endpoints ==========

@router.post("/create-order", response_model=CreateOrderResponse)
async def create_payment_order(
    request: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a Razorpay order for token purchase.

    This is step 1 of the payment flow:
    1. Creates order in Razorpay
    2. Stores pending transaction in DB
    3. Returns order_id for frontend checkout
    """
    if not RAZORPAY_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment service not configured. Please contact support."
        )

    # Get package details
    packages = settings.get_token_packages()

    logger.info(f"[Payment] Received package: '{request.package}', available: {list(packages.keys())}")

    if request.package not in packages or not packages[request.package]:
        logger.warning(f"[Payment] Invalid package '{request.package}'. Available: {list(packages.keys())}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid package '{request.package}'. Choose: {', '.join(packages.keys())}"
        )

    package = packages[request.package]
    original_amount = request.amount if request.amount else package["price"]
    tokens = package["tokens"]

    # Validate and apply coupon if provided
    coupon_applied = None
    coupon_message = None
    discount_amount = 0
    coupon_id = None

    if request.coupon_code:
        coupon_validation = await coupon_service.validate_coupon(
            db=db,
            code=request.coupon_code,
            amount=original_amount,
            user_id=str(current_user.id)
        )

        if coupon_validation.valid:
            discount_amount = coupon_validation.discount_amount
            coupon_applied = coupon_validation.code
            coupon_message = coupon_validation.message
            coupon_id = coupon_validation.coupon_id
            logger.info(f"[Payment] Coupon {coupon_applied} applied. Discount: ₹{discount_amount/100:.0f}")
        else:
            # Coupon invalid - return error
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=coupon_validation.message
            )

    # Calculate final amount after discount
    amount = max(0, original_amount - discount_amount)

    try:
        # Create Razorpay order
        # Receipt must be max 40 chars - use short format
        receipt = f"bb_{str(current_user.id)[:8]}_{int(datetime.utcnow().timestamp())}"
        order_notes = {
            "user_id": str(current_user.id),
            "user_email": current_user.email,
            "package": request.package,
            "tokens": tokens,
            "original_amount": original_amount,
            "discount_amount": discount_amount,
        }

        # Add coupon info to notes if applied
        if coupon_applied:
            order_notes["coupon_code"] = coupon_applied
            order_notes["coupon_id"] = coupon_id

        order_data = {
            "amount": amount,  # Amount in paise (after discount)
            "currency": "INR",
            "receipt": receipt,
            "notes": order_notes
        }

        razorpay_order = razorpay_client.order.create(data=order_data)

        logger.info(f"[Payment] Created Razorpay order: {razorpay_order['id']} for user {current_user.id}" +
                   (f" with coupon {coupon_applied}" if coupon_applied else ""))

        # Store pending transaction in database
        transaction_metadata = {
            "package": request.package,
            "tokens": tokens,
            "package_name": package["name"],
            "original_amount": original_amount,
            "discount_amount": discount_amount,
        }

        # Add coupon info to metadata if applied
        if coupon_applied:
            transaction_metadata["coupon_code"] = coupon_applied
            transaction_metadata["coupon_id"] = coupon_id

        description = f"Token purchase: {package['name']} ({tokens:,} tokens)"
        if coupon_applied:
            description += f" (Coupon: {coupon_applied}, Discount: ₹{discount_amount/100:.0f})"

        transaction = Transaction(
            user_id=current_user.id,
            razorpay_order_id=razorpay_order["id"],
            amount=amount,
            currency="INR",
            status=TransactionStatus.PENDING,
            description=description,
            extra_metadata=transaction_metadata
        )

        db.add(transaction)
        await db.commit()

        return CreateOrderResponse(
            order_id=razorpay_order["id"],
            amount=amount,
            original_amount=original_amount,
            discount_amount=discount_amount,
            currency="INR",
            key_id=settings.RAZORPAY_KEY_ID,
            package_name=package["name"],
            tokens=tokens,
            notes=order_data["notes"],
            coupon_applied=coupon_applied,
            coupon_message=coupon_message
        )

    except Exception as e:
        logger.error(f"[Payment] Order creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment order. Please try again."
        )


@router.post("/verify", response_model=PaymentStatusResponse)
async def verify_payment(
    request: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify payment after Razorpay checkout completion.

    This is step 2 of the payment flow:
    1. Verify Razorpay signature
    2. Update transaction status
    3. Credit tokens to user account
    """
    if not RAZORPAY_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment service not configured"
        )

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

    # Verify Razorpay signature
    try:
        # Generate expected signature
        message = f"{request.razorpay_order_id}|{request.razorpay_payment_id}"
        expected_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, request.razorpay_signature):
            logger.warning(f"[Payment] Invalid signature for order {request.razorpay_order_id}")

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

        # Credit tokens to user
        tokens_to_add = transaction.extra_metadata.get("tokens", 0)
        package_name = transaction.extra_metadata.get("package_name", "Token Pack")

        if tokens_to_add > 0:
            balance = await token_manager.add_tokens(
                db=db,
                user_id=str(current_user.id),
                tokens_to_add=tokens_to_add,
                transaction_type="purchase",
                description=f"Purchased {package_name}",
                is_premium=True
            )

            # Create TokenPurchase record for plan status tracking
            # This record is used by get_user_limits() to grant Premium access
            token_purchase = TokenPurchase(
                user_id=current_user.id,
                package_name=package_name,
                tokens_purchased=tokens_to_add,
                amount_paid=transaction.amount,
                currency="INR",
                payment_id=request.razorpay_payment_id,
                payment_status="success",
                valid_from=datetime.utcnow(),
                valid_until=None,  # Lifetime access
                is_expired=False
            )
            db.add(token_purchase)

            # ================================================================
            # CREATE SUBSCRIPTION RECORD FOR PRO STATUS
            # This ensures user is recognized as PRO across the entire app:
            # - Document generation (SRS, PPT, Report, Viva Q&A)
            # - Dashboard showing PRO status
            # - All subscription-based feature checks
            # ================================================================
            try:
                # Find existing PRO plan or create one
                pro_plan_result = await db.execute(
                    select(Plan).where(
                        Plan.plan_type == PlanType.PRO,
                        Plan.is_active == True
                    ).limit(1)
                )
                pro_plan = pro_plan_result.scalar_one_or_none()

                # If no PRO plan exists in database, create one
                if not pro_plan:
                    pro_plan = Plan(
                        name="PRO Plan",
                        slug="pro-token-purchase",
                        plan_type=PlanType.PRO,
                        description="PRO access via token purchase - Full features including academic documents",
                        price=transaction.amount,
                        currency="INR",
                        billing_period="lifetime",
                        token_limit=None,  # Unlimited
                        project_limit=None,  # Unlimited
                        documents_per_month=None,  # Unlimited
                        document_types_allowed=["report", "srs", "sds", "ppt", "viva"],
                        features=["unlimited_tokens", "all_documents", "priority_support", "academic_docs"],
                        allowed_models=["haiku", "sonnet", "opus"],
                        priority_queue=True,
                        is_active=True
                    )
                    db.add(pro_plan)
                    await db.flush()  # Get the plan ID without committing
                    logger.info(f"[Payment] Created PRO plan for token purchases: {pro_plan.id}")

                # Cancel any existing active subscriptions for this user
                existing_subs = await db.execute(
                    select(Subscription).where(
                        Subscription.user_id == current_user.id,
                        Subscription.status == SubscriptionStatus.ACTIVE
                    )
                )
                for existing_sub in existing_subs.scalars().all():
                    existing_sub.status = SubscriptionStatus.CANCELLED
                    existing_sub.cancelled_at = datetime.utcnow()
                    logger.info(f"[Payment] Cancelled existing subscription: {existing_sub.id}")

                # Create new PRO subscription
                now = datetime.utcnow()
                new_subscription = Subscription(
                    user_id=current_user.id,
                    plan_id=pro_plan.id,
                    status=SubscriptionStatus.ACTIVE,
                    razorpay_subscription_id=None,  # One-time purchase, not recurring
                    razorpay_customer_id=None,
                    current_period_start=now,
                    current_period_end=now + relativedelta(years=100),  # Lifetime access
                    cancel_at_period_end=False
                )
                db.add(new_subscription)
                logger.info(f"[Payment] Created PRO subscription for user {current_user.id}")

            except Exception as sub_error:
                # Log error but don't fail the payment - tokens are already credited
                # User still gets tokens, subscription is a bonus
                logger.error(f"[Payment] Failed to create subscription record (non-fatal): {sub_error}")

            # ================================================================
            # APPLY COUPON IF ONE WAS USED
            # Credit reward to coupon owner's wallet
            # ================================================================
            coupon_code = transaction.extra_metadata.get("coupon_code")
            if coupon_code:
                try:
                    original_amount = transaction.extra_metadata.get("original_amount", transaction.amount)
                    discount_amount = transaction.extra_metadata.get("discount_amount", 0)

                    success, message, coupon_usage = await coupon_service.apply_coupon(
                        db=db,
                        code=coupon_code,
                        applied_by_id=str(current_user.id),
                        order_id=request.razorpay_order_id,
                        original_amount=original_amount,
                        discount_amount=discount_amount,
                        final_amount=transaction.amount,
                        transaction_id=str(transaction.id)
                    )

                    if success:
                        logger.info(f"[Payment] Coupon {coupon_code} applied successfully. "
                                   f"Reward credited to owner.")
                    else:
                        logger.warning(f"[Payment] Failed to apply coupon {coupon_code}: {message}")

                except Exception as coupon_error:
                    # Don't fail payment if coupon application fails
                    logger.error(f"[Payment] Coupon application error (non-fatal): {coupon_error}")

            await db.commit()

            logger.info(f"[Payment] Successfully credited {tokens_to_add} tokens to user {current_user.id}")

            success_message = f"Payment successful! {tokens_to_add:,} tokens added to your account."
            if coupon_code:
                success_message += f" Coupon {coupon_code} applied."

            return PaymentStatusResponse(
                status="success",
                message=success_message,
                tokens_credited=tokens_to_add,
                new_balance=balance.remaining_tokens
            )

        await db.commit()

        return PaymentStatusResponse(
            status="success",
            message="Payment verified successfully!",
            tokens_credited=0
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Payment] Verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment verification failed. Please contact support."
        )


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_razorpay_signature: str = Header(None, alias="X-Razorpay-Signature")
):
    """
    Razorpay webhook endpoint for payment events.

    This is a backup verification mechanism that handles:
    - payment.captured
    - payment.failed
    - order.paid

    Configure this URL in Razorpay Dashboard: /api/v1/payments/webhook
    """
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.warning("[Webhook] Webhook secret not configured")
        return {"status": "skipped", "reason": "webhook not configured"}

    try:
        # Get raw body for signature verification
        body = await request.body()
        body_str = body.decode()

        # Verify webhook signature
        expected_signature = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        if not x_razorpay_signature or not hmac.compare_digest(expected_signature, x_razorpay_signature):
            logger.warning("[Webhook] Invalid webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )

        # Parse webhook payload
        payload = json.loads(body_str)
        event = payload.get("event")

        logger.info(f"[Webhook] Received event: {event}")

        if event == "payment.captured":
            await _handle_payment_captured(payload, db)
        elif event == "payment.failed":
            await _handle_payment_failed(payload, db)
        elif event == "order.paid":
            await _handle_order_paid(payload, db)

        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Webhook] Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}


async def _handle_payment_captured(payload: dict, db: AsyncSession):
    """Handle payment.captured webhook event"""
    payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment.get("order_id")
    payment_id = payment.get("id")

    if not order_id:
        logger.warning("[Webhook] No order_id in payment.captured event")
        return

    # Find transaction
    result = await db.execute(
        select(Transaction).where(Transaction.razorpay_order_id == order_id)
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        logger.warning(f"[Webhook] Transaction not found for order {order_id}")
        return

    # Skip if already processed
    if transaction.status == TransactionStatus.SUCCESS:
        logger.info(f"[Webhook] Transaction {order_id} already processed")
        return

    # Update transaction
    transaction.razorpay_payment_id = payment_id
    transaction.status = TransactionStatus.SUCCESS
    transaction.completed_at = datetime.utcnow()
    transaction.updated_at = datetime.utcnow()

    # Credit tokens if not already credited
    tokens_to_add = transaction.extra_metadata.get("tokens", 0)
    package_name = transaction.extra_metadata.get("package_name", "Token Pack")
    if tokens_to_add > 0:
        await token_manager.add_tokens(
            db=db,
            user_id=str(transaction.user_id),
            tokens_to_add=tokens_to_add,
            transaction_type="purchase",
            description=f"Webhook: {transaction.description}",
            is_premium=True
        )

        # Create TokenPurchase record for plan status tracking
        token_purchase = TokenPurchase(
            user_id=transaction.user_id,
            package_name=package_name,
            tokens_purchased=tokens_to_add,
            amount_paid=transaction.amount,
            currency="INR",
            payment_id=payment_id,
            payment_status="success",
            valid_from=datetime.utcnow(),
            valid_until=None,
            is_expired=False
        )
        db.add(token_purchase)

        # ================================================================
        # CREATE SUBSCRIPTION RECORD FOR PRO STATUS (Webhook backup)
        # Same logic as /verify endpoint for consistency
        # ================================================================
        try:
            # Find existing PRO plan or create one
            pro_plan_result = await db.execute(
                select(Plan).where(
                    Plan.plan_type == PlanType.PRO,
                    Plan.is_active == True
                ).limit(1)
            )
            pro_plan = pro_plan_result.scalar_one_or_none()

            if not pro_plan:
                pro_plan = Plan(
                    name="PRO Plan",
                    slug="pro-token-purchase",
                    plan_type=PlanType.PRO,
                    description="PRO access via token purchase",
                    price=transaction.amount,
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

            # Cancel existing subscriptions
            existing_subs = await db.execute(
                select(Subscription).where(
                    Subscription.user_id == transaction.user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE
                )
            )
            for existing_sub in existing_subs.scalars().all():
                existing_sub.status = SubscriptionStatus.CANCELLED
                existing_sub.cancelled_at = datetime.utcnow()

            # Create PRO subscription
            now = datetime.utcnow()
            new_subscription = Subscription(
                user_id=transaction.user_id,
                plan_id=pro_plan.id,
                status=SubscriptionStatus.ACTIVE,
                current_period_start=now,
                current_period_end=now + relativedelta(years=100),
                cancel_at_period_end=False
            )
            db.add(new_subscription)
            logger.info(f"[Webhook] Created PRO subscription for user {transaction.user_id}")

        except Exception as sub_error:
            logger.error(f"[Webhook] Failed to create subscription (non-fatal): {sub_error}")

        # ================================================================
        # APPLY COUPON IF ONE WAS USED (Webhook backup)
        # ================================================================
        coupon_code = transaction.extra_metadata.get("coupon_code") if transaction.extra_metadata else None
        if coupon_code:
            try:
                original_amount = transaction.extra_metadata.get("original_amount", transaction.amount)
                discount_amount = transaction.extra_metadata.get("discount_amount", 0)

                success, message, coupon_usage = await coupon_service.apply_coupon(
                    db=db,
                    code=coupon_code,
                    applied_by_id=str(transaction.user_id),
                    order_id=order_id,
                    original_amount=original_amount,
                    discount_amount=discount_amount,
                    final_amount=transaction.amount,
                    transaction_id=str(transaction.id)
                )

                if success:
                    logger.info(f"[Webhook] Coupon {coupon_code} applied successfully")
                else:
                    logger.warning(f"[Webhook] Failed to apply coupon {coupon_code}: {message}")

            except Exception as coupon_error:
                logger.error(f"[Webhook] Coupon application error (non-fatal): {coupon_error}")

    await db.commit()
    logger.info(f"[Webhook] Processed payment.captured for order {order_id}")


async def _handle_payment_failed(payload: dict, db: AsyncSession):
    """Handle payment.failed webhook event"""
    payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment.get("order_id")

    if not order_id:
        return

    # Update transaction status
    await db.execute(
        update(Transaction)
        .where(Transaction.razorpay_order_id == order_id)
        .values(
            status=TransactionStatus.FAILED,
            updated_at=datetime.utcnow()
        )
    )
    await db.commit()
    logger.info(f"[Webhook] Marked transaction {order_id} as failed")


async def _handle_order_paid(payload: dict, db: AsyncSession):
    """Handle order.paid webhook event (backup for payment.captured)"""
    order = payload.get("payload", {}).get("order", {}).get("entity", {})
    order_id = order.get("id")

    if order_id:
        # Delegate to payment.captured handler logic
        await _handle_payment_captured({
            "payload": {
                "payment": {
                    "entity": {
                        "order_id": order_id,
                        "id": order.get("payment_id")
                    }
                }
            }
        }, db)


# ========== Payment Status Endpoints ==========

@router.get("/status/{order_id}")
async def get_payment_status(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment status for an order"""
    result = await db.execute(
        select(Transaction).where(
            Transaction.razorpay_order_id == order_id,
            Transaction.user_id == current_user.id
        )
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    return {
        "order_id": order_id,
        "status": transaction.status.value,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "package": transaction.extra_metadata.get("package_name") if transaction.extra_metadata else None,
        "tokens": transaction.extra_metadata.get("tokens") if transaction.extra_metadata else None,
        "created_at": transaction.created_at.isoformat(),
        "completed_at": transaction.completed_at.isoformat() if transaction.completed_at else None
    }


@router.get("/history")
async def get_payment_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment history for current user"""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    transactions = result.scalars().all()

    return {
        "transactions": [
            {
                "order_id": t.razorpay_order_id,
                "payment_id": t.razorpay_payment_id,
                "amount": t.amount,
                "currency": t.currency,
                "status": t.status.value,
                "description": t.description,
                "package": t.extra_metadata.get("package_name") if t.extra_metadata else None,
                "tokens": t.extra_metadata.get("tokens") if t.extra_metadata else None,
                "created_at": t.created_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None
            }
            for t in transactions
        ],
        "total": len(transactions)
    }
