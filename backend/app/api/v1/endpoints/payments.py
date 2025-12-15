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
from app.models.billing import Transaction, TransactionStatus
from app.models.token_balance import TokenPurchase
from app.modules.auth.dependencies import get_current_user
from app.utils.token_manager import token_manager

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


class CreateOrderResponse(BaseModel):
    """Response with Razorpay order details"""
    order_id: str
    amount: int  # in paise
    currency: str
    key_id: str  # Razorpay key for frontend
    package_name: str
    tokens: int
    notes: dict


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
    amount = request.amount if request.amount else package["price"]
    tokens = package["tokens"]

    try:
        # Create Razorpay order
        # Receipt must be max 40 chars - use short format
        receipt = f"bb_{str(current_user.id)[:8]}_{int(datetime.utcnow().timestamp())}"
        order_data = {
            "amount": amount,  # Amount in paise
            "currency": "INR",
            "receipt": receipt,
            "notes": {
                "user_id": str(current_user.id),
                "user_email": current_user.email,
                "package": request.package,
                "tokens": tokens
            }
        }

        razorpay_order = razorpay_client.order.create(data=order_data)

        logger.info(f"[Payment] Created Razorpay order: {razorpay_order['id']} for user {current_user.id}")

        # Store pending transaction in database
        transaction = Transaction(
            user_id=current_user.id,
            razorpay_order_id=razorpay_order["id"],
            amount=amount,
            currency="INR",
            status=TransactionStatus.PENDING,
            description=f"Token purchase: {package['name']} ({tokens:,} tokens)",
            extra_metadata={
                "package": request.package,
                "tokens": tokens,
                "package_name": package["name"]
            }
        )

        db.add(transaction)
        await db.commit()

        return CreateOrderResponse(
            order_id=razorpay_order["id"],
            amount=amount,
            currency="INR",
            key_id=settings.RAZORPAY_KEY_ID,
            package_name=package["name"],
            tokens=tokens,
            notes=order_data["notes"]
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

            await db.commit()

            logger.info(f"[Payment] Successfully credited {tokens_to_add} tokens to user {current_user.id}")

            return PaymentStatusResponse(
                status="success",
                message=f"Payment successful! {tokens_to_add:,} tokens added to your account.",
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
