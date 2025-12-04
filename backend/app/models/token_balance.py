from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import os

from app.core.database import Base
from app.core.types import GUID, generate_uuid

# Get defaults from environment or use fallback values
# Note: These are evaluated at import time, settings may not be available yet
_FREE_TIER_MONTHLY_ALLOWANCE = int(os.getenv("FREE_TIER_MONTHLY_ALLOWANCE", "10000"))
_MAX_TOKENS_PER_REQUEST = int(os.getenv("MAX_TOKENS_PER_REQUEST", "8192"))
_MAX_REQUESTS_PER_DAY = int(os.getenv("MAX_REQUESTS_PER_DAY", "100"))


class TokenBalance(Base):
    """User token balance (like Bolt.new & Lovable.dev)"""
    __tablename__ = "token_balances"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Token Balance
    total_tokens = Column(Integer, default=0, nullable=False)  # Total tokens purchased/allocated
    used_tokens = Column(Integer, default=0, nullable=False)   # Tokens consumed
    remaining_tokens = Column(Integer, default=0, nullable=False)  # Available tokens

    # Monthly allowance (subscription-based)
    monthly_allowance = Column(Integer, default=_FREE_TIER_MONTHLY_ALLOWANCE, nullable=False)
    monthly_used = Column(Integer, default=0, nullable=False)
    month_reset_date = Column(DateTime, nullable=True)

    # Premium tokens (purchased separately)
    premium_tokens = Column(Integer, default=0, nullable=False)
    premium_used = Column(Integer, default=0, nullable=False)

    # Rollover tokens (unused from previous month)
    rollover_tokens = Column(Integer, default=0, nullable=False)

    # Limits (configurable via environment)
    max_tokens_per_request = Column(Integer, default=_MAX_TOKENS_PER_REQUEST, nullable=False)
    max_requests_per_day = Column(Integer, default=_MAX_REQUESTS_PER_DAY, nullable=False)

    # Tracking
    total_requests = Column(Integer, default=0, nullable=False)
    last_request_at = Column(DateTime, nullable=True)
    requests_today = Column(Integer, default=0, nullable=False)
    last_reset_date = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TokenBalance user_id={self.user_id} remaining={self.remaining_tokens}>"


class TokenTransaction(Base):
    """Individual token transaction (like Bolt.new transaction history)"""
    __tablename__ = "token_transactions"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)

    # Transaction type
    transaction_type = Column(String(50), nullable=False)  # 'usage', 'purchase', 'refund', 'bonus', 'monthly_reset'

    # Tokens
    tokens_before = Column(Integer, nullable=False)
    tokens_changed = Column(Integer, nullable=False)  # Positive for addition, negative for usage
    tokens_after = Column(Integer, nullable=False)

    # Details
    description = Column(String(500), nullable=True)
    agent_type = Column(String(50), nullable=True)  # Which agent used tokens
    model_used = Column(String(100), nullable=True)  # haiku or sonnet

    # Token breakdown
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cache_read_tokens = Column(Integer, default=0)  # Claude caching
    cache_creation_tokens = Column(Integer, default=0)

    # Cost
    estimated_cost_usd = Column(Integer, default=0)  # In cents
    estimated_cost_inr = Column(Integer, default=0)  # In paise

    # Metadata
    extra_metadata = Column(JSON, nullable=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<TokenTransaction {self.transaction_type} tokens={self.tokens_changed}>"


class TokenPurchase(Base):
    """Token purchase history (like Bolt.new pricing plans)"""
    __tablename__ = "token_purchases"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Package details
    package_name = Column(String(100), nullable=False)  # 'starter', 'pro', 'unlimited'
    tokens_purchased = Column(Integer, nullable=False)

    # Pricing
    amount_paid = Column(Integer, nullable=False)  # In paise/cents
    currency = Column(String(10), default="INR")

    # Payment
    payment_id = Column(String(255), nullable=True)  # Razorpay payment ID
    payment_status = Column(String(50), default="pending")  # pending, success, failed

    # Validity
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=True)  # Null for lifetime
    is_expired = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TokenPurchase {self.package_name} tokens={self.tokens_purchased}>"
