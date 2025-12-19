"""
Admin Billing & Revenue endpoints.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import Optional
import math

from app.core.database import get_db
from app.models import User, Subscription, Transaction, Plan, AuditLog
from app.modules.auth.dependencies import get_current_admin
from app.schemas.admin import (
    RevenueResponse, RevenueData,
    AdminTransactionResponse, AdminTransactionsResponse,
    AdminSubscriptionResponse, AdminSubscriptionsResponse
)

router = APIRouter()


@router.get("/revenue", response_model=RevenueResponse)
async def get_revenue(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get revenue analytics"""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # Total revenue
    total_revenue_result = await db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.status == "success"
        )
    )
    total_revenue = float(total_revenue_result or 0) / 100

    # Revenue this month
    revenue_this_month_result = await db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.status == "success",
                Transaction.created_at >= month_start
            )
        )
    )
    revenue_this_month = float(revenue_this_month_result or 0) / 100

    # Revenue last month
    revenue_last_month_result = await db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.status == "success",
                Transaction.created_at >= last_month_start,
                Transaction.created_at < month_start
            )
        )
    )
    revenue_last_month = float(revenue_last_month_result or 0) / 100

    # Calculate growth percentage
    if revenue_last_month > 0:
        growth_percentage = ((revenue_this_month - revenue_last_month) / revenue_last_month) * 100
    else:
        growth_percentage = 100.0 if revenue_this_month > 0 else 0.0

    # Daily revenue for the period
    daily_revenue = []
    for i in range(days):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        day_revenue = await db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                and_(
                    Transaction.status == "success",
                    Transaction.created_at >= day_start,
                    Transaction.created_at < day_end
                )
            )
        )
        day_count = await db.scalar(
            select(func.count(Transaction.id)).where(
                and_(
                    Transaction.status == "success",
                    Transaction.created_at >= day_start,
                    Transaction.created_at < day_end
                )
            )
        )

        daily_revenue.append(RevenueData(
            date=day_start.strftime("%Y-%m-%d"),
            amount=float(day_revenue or 0) / 100,
            currency="INR",
            transactions_count=day_count or 0
        ))

    daily_revenue.reverse()

    # Monthly revenue (last 12 months)
    monthly_revenue = []
    for i in range(12):
        month = now - timedelta(days=i * 30)
        month_s = month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i == 0:
            month_e = now
        else:
            month_e = (month_s + timedelta(days=32)).replace(day=1)

        month_rev = await db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                and_(
                    Transaction.status == "success",
                    Transaction.created_at >= month_s,
                    Transaction.created_at < month_e
                )
            )
        )
        month_count = await db.scalar(
            select(func.count(Transaction.id)).where(
                and_(
                    Transaction.status == "success",
                    Transaction.created_at >= month_s,
                    Transaction.created_at < month_e
                )
            )
        )

        monthly_revenue.append(RevenueData(
            date=month_s.strftime("%Y-%m"),
            amount=float(month_rev or 0) / 100,
            currency="INR",
            transactions_count=month_count or 0
        ))

    monthly_revenue.reverse()

    return RevenueResponse(
        total_revenue=total_revenue,
        revenue_this_month=revenue_this_month,
        revenue_last_month=revenue_last_month,
        growth_percentage=round(growth_percentage, 2),
        daily_revenue=daily_revenue,
        monthly_revenue=monthly_revenue
    )


@router.get("/transactions", response_model=AdminTransactionsResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: str = Query("created_at", regex="^(created_at|amount|status)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List all transactions with filtering and pagination"""

    query = select(Transaction, User).join(User, Transaction.user_id == User.id)

    conditions = []
    if status:
        conditions.append(Transaction.status == status)
    if user_id:
        conditions.append(Transaction.user_id == user_id)
    if start_date:
        conditions.append(Transaction.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        conditions.append(Transaction.created_at <= datetime.fromisoformat(end_date))

    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(
        select(Transaction).where(and_(*conditions) if conditions else True).subquery()
    )
    total = await db.scalar(count_query)

    # Apply sorting
    sort_column = getattr(Transaction, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for txn, user in rows:
        items.append(AdminTransactionResponse(
            id=str(txn.id),
            user_id=str(txn.user_id),
            user_email=user.email,
            user_name=user.full_name,
            amount=txn.amount,
            currency=txn.currency or "INR",
            status=txn.status,
            description=txn.description,
            razorpay_payment_id=txn.razorpay_payment_id,
            created_at=txn.created_at,
            completed_at=txn.completed_at
        ))

    return AdminTransactionsResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
        total_pages=math.ceil((total or 0) / page_size) if total and total > 0 else 1
    )


@router.get("/subscriptions", response_model=AdminSubscriptionsResponse)
async def list_subscriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    plan_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List all subscriptions with filtering and pagination"""

    query = (
        select(Subscription, User, Plan)
        .join(User, Subscription.user_id == User.id)
        .join(Plan, Subscription.plan_id == Plan.id)
    )

    conditions = []
    if status:
        conditions.append(Subscription.status == status)
    if plan_id:
        conditions.append(Subscription.plan_id == plan_id)

    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    base_query = select(Subscription)
    if conditions:
        base_query = base_query.where(and_(*conditions))
    count_query = select(func.count()).select_from(base_query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Subscription.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for sub, user, plan in rows:
        items.append(AdminSubscriptionResponse(
            id=str(sub.id),
            user_id=str(sub.user_id),
            user_email=user.email,
            user_name=user.full_name,
            plan_name=plan.name,
            plan_type=plan.plan_type.value if hasattr(plan.plan_type, 'value') else str(plan.plan_type),
            status=sub.status,
            current_period_start=sub.current_period_start,
            current_period_end=sub.current_period_end,
            created_at=sub.created_at
        ))

    return AdminSubscriptionsResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
        total_pages=math.ceil((total or 0) / page_size) if total and total > 0 else 1
    )


@router.post("/refund/{transaction_id}")
async def process_refund(
    transaction_id: str,
    request: Request,
    reason: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Process a refund for a transaction"""
    txn = await db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if txn.status != "success":
        raise HTTPException(status_code=400, detail="Can only refund successful transactions")

    if txn.status == "refunded":
        raise HTTPException(status_code=400, detail="Transaction already refunded")

    # Mark as refunded
    txn.status = "refunded"
    txn.extra_metadata = txn.extra_metadata or {}
    txn.extra_metadata["refund_reason"] = reason
    txn.extra_metadata["refunded_by"] = str(current_admin.id)
    txn.extra_metadata["refunded_at"] = datetime.utcnow().isoformat()

    await db.commit()

    # Log action
    log = AuditLog(
        admin_id=str(current_admin.id),
        action="transaction_refunded",
        target_type="transaction",
        target_id=transaction_id,
        details={"amount": txn.amount, "reason": reason},
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(log)
    await db.commit()

    return {"message": f"Refund of ₹{txn.amount / 100:.2f} processed successfully"}


@router.get("/stats")
async def get_billing_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get billing statistics summary"""
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Total revenue
    total_revenue = await db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.status == "success"
        )
    )

    # Revenue this month
    revenue_this_month = await db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.status == "success",
                Transaction.created_at >= month_start
            )
        )
    )

    # Total transactions
    total_transactions = await db.scalar(select(func.count(Transaction.id)))
    successful_transactions = await db.scalar(
        select(func.count(Transaction.id)).where(Transaction.status == "success")
    )

    # Subscription stats
    total_subscriptions = await db.scalar(select(func.count(Subscription.id)))
    active_subscriptions = await db.scalar(
        select(func.count(Subscription.id)).where(Subscription.status == "active")
    )

    # Average transaction value
    avg_transaction = await db.scalar(
        select(func.avg(Transaction.amount)).where(Transaction.status == "success")
    )

    return {
        "total_revenue": float(total_revenue or 0) / 100,
        "revenue_this_month": float(revenue_this_month or 0) / 100,
        "total_transactions": total_transactions or 0,
        "successful_transactions": successful_transactions or 0,
        "total_subscriptions": total_subscriptions or 0,
        "active_subscriptions": active_subscriptions or 0,
        "average_transaction_value": float(avg_transaction or 0) / 100,
        "currency": "INR"
    }
