from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class PlanType(str, enum.Enum):
    """Plan types"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status"""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class TransactionStatus(str, enum.Enum):
    """Transaction status"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class Plan(Base):
    """Subscription plan model"""
    __tablename__ = "plans"

    id = Column(GUID, primary_key=True, default=generate_uuid)

    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    plan_type = Column(SQLEnum(PlanType), nullable=False)

    description = Column(Text, nullable=True)

    # Pricing
    price = Column(Integer, nullable=False)  # in paise/cents
    currency = Column(String(10), default="INR")
    billing_period = Column(String(20), default="monthly")  # monthly, yearly

    # Limits
    token_limit = Column(Integer, nullable=True)  # null = unlimited
    project_limit = Column(Integer, nullable=True)
    api_calls_limit = Column(Integer, nullable=True)

    # Features
    features = Column(JSON, default=list)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")

    def __repr__(self):
        return f"<Plan {self.name}>"


class Subscription(Base):
    """User subscription model"""
    __tablename__ = "subscriptions"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(GUID, ForeignKey("plans.id", ondelete="SET NULL"), nullable=True)

    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False)

    # Razorpay
    razorpay_subscription_id = Column(String(255), unique=True, nullable=True)
    razorpay_customer_id = Column(String(255), nullable=True)

    # Billing period
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)

    # Cancellation
    cancel_at_period_end = Column(Boolean, default=False)
    cancelled_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    transactions = relationship("Transaction", back_populates="subscription", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Subscription {self.user_id}>"


class Transaction(Base):
    """Payment transaction model"""
    __tablename__ = "transactions"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subscription_id = Column(GUID, ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True)

    # Razorpay
    razorpay_payment_id = Column(String(255), unique=True, nullable=True)
    razorpay_order_id = Column(String(255), nullable=True)
    razorpay_signature = Column(String(500), nullable=True)

    # Amount
    amount = Column(Integer, nullable=False)  # in paise/cents
    currency = Column(String(10), default="INR")

    # Status
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)

    # Description
    description = Column(Text, nullable=True)

    # Metadata
    extra_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    subscription = relationship("Subscription", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction {self.razorpay_payment_id}>"
