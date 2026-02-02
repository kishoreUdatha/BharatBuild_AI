"""
Coupon and Wallet Models - Referral discount system with dual rewards

When a coupon is applied:
- Applier gets discount (e.g., ₹100 off)
- Coupon owner gets reward (e.g., ₹100 to wallet)
"""

from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey, Enum as SQLEnum, Text, Index, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class CouponCategory(str, enum.Enum):
    """Category of coupon owner"""
    STUDENT = "student"
    FACULTY = "faculty"
    COLLEGE = "college"
    MEDIA = "media"


class CouponStatus(str, enum.Enum):
    """Coupon status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"


class WalletTransactionType(str, enum.Enum):
    """Type of wallet transaction"""
    CREDIT = "credit"           # Money added (reward)
    DEBIT = "debit"             # Money used (purchase)
    WITHDRAWAL = "withdrawal"   # Withdrawn to bank
    REFUND = "refund"           # Refunded amount


class WalletTransactionSource(str, enum.Enum):
    """Source of wallet transaction"""
    COUPON_REWARD = "coupon_reward"     # Earned from coupon usage
    PURCHASE = "purchase"               # Used for purchase
    WITHDRAWAL = "withdrawal"           # Withdrawn to bank
    ADMIN_CREDIT = "admin_credit"       # Admin manually added
    ADMIN_DEBIT = "admin_debit"         # Admin manually deducted
    REFUND = "refund"                   # Refund from failed transaction


class Coupon(Base):
    """
    Coupon/Referral code model

    When someone applies this coupon:
    - They get `discount_amount` off their purchase
    - The owner gets `reward_amount` added to their wallet
    """
    __tablename__ = "coupons"

    __table_args__ = (
        Index('ix_coupons_code', 'code'),
        Index('ix_coupons_owner', 'owner_id'),
        Index('ix_coupons_status', 'status'),
        Index('ix_coupons_category', 'category'),
    )

    # Primary Key
    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Coupon Code (unique identifier shown to users)
    # Note: index is defined in __table_args__ as ix_coupons_code
    code = Column(String(50), unique=True, nullable=False)

    # Owner info - stored directly for flexibility (no user account required)
    owner_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # Optional link to user
    owner_name = Column(String(100), nullable=False)  # Required - display name
    owner_email = Column(String(255), nullable=False)  # Required - contact email
    owner_phone = Column(String(15), nullable=False)  # Required - contact phone

    # Category of coupon
    category = Column(SQLEnum(CouponCategory), nullable=False)

    # Display name and description
    name = Column(String(100), nullable=True)  # e.g., "Ravi's Referral Code"
    description = Column(Text, nullable=True)

    # Discount for the person applying the coupon (in paise, e.g., 10000 = ₹100)
    discount_amount = Column(Integer, nullable=False, default=10000)  # Default ₹100

    # Reward for the coupon owner (in paise, e.g., 10000 = ₹100)
    reward_amount = Column(Integer, nullable=False, default=10000)  # Default ₹100

    # Usage tracking
    total_uses = Column(Integer, default=0, nullable=False)
    total_discount_given = Column(Integer, default=0, nullable=False)  # in paise
    total_reward_earned = Column(Integer, default=0, nullable=False)   # in paise

    # Status
    status = Column(SQLEnum(CouponStatus), default=CouponStatus.ACTIVE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Validity period (optional)
    valid_from = Column(DateTime, default=datetime.utcnow, nullable=False)
    valid_until = Column(DateTime, nullable=True)  # NULL means no expiry

    # Admin who created this coupon
    created_by = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], backref="owned_coupons")
    creator = relationship("User", foreign_keys=[created_by])
    usages = relationship("CouponUsage", back_populates="coupon", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Coupon {self.code} (Owner: {self.owner_id})>"

    @property
    def discount_amount_inr(self) -> float:
        """Discount amount in INR (rupees)"""
        return self.discount_amount / 100

    @property
    def reward_amount_inr(self) -> float:
        """Reward amount in INR (rupees)"""
        return self.reward_amount / 100


class CouponUsage(Base):
    """
    Track each coupon usage

    Records who applied the coupon, how much discount they got,
    and how much reward the owner received.
    """
    __tablename__ = "coupon_usages"

    __table_args__ = (
        Index('ix_coupon_usages_coupon', 'coupon_id'),
        Index('ix_coupon_usages_user', 'applied_by_id'),
        Index('ix_coupon_usages_owner', 'owner_id'),
        Index('ix_coupon_usages_order', 'order_id'),
    )

    # Primary Key
    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Which coupon was used
    coupon_id = Column(GUID, ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False)

    # Who applied the coupon (the buyer)
    applied_by_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Who owns the coupon (gets the reward)
    owner_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Payment/Order reference
    order_id = Column(String(100), nullable=True)  # Razorpay order ID
    transaction_id = Column(GUID, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)

    # Amounts (all in paise)
    original_amount = Column(Integer, nullable=False)    # Price before discount
    discount_given = Column(Integer, nullable=False)     # Discount amount
    final_amount = Column(Integer, nullable=False)       # Price after discount
    reward_given = Column(Integer, nullable=False)       # Amount credited to owner

    # Wallet transaction reference (for the reward)
    wallet_transaction_id = Column(GUID, ForeignKey("wallet_transactions.id", ondelete="SET NULL"), nullable=True)

    # Timestamp
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    coupon = relationship("Coupon", back_populates="usages")
    applied_by = relationship("User", foreign_keys=[applied_by_id])
    owner = relationship("User", foreign_keys=[owner_id])
    transaction = relationship("Transaction")
    wallet_transaction = relationship("WalletTransaction")

    def __repr__(self):
        return f"<CouponUsage {self.coupon_id} by {self.applied_by_id}>"


class Wallet(Base):
    """
    User wallet for storing earned rewards

    Users earn money in their wallet when their coupon codes are used.
    They can use wallet balance for purchases or withdraw to bank.
    """
    __tablename__ = "wallets"

    __table_args__ = (
        Index('ix_wallets_user', 'user_id'),
    )

    # Primary Key
    id = Column(GUID, primary_key=True, default=generate_uuid)

    # One wallet per user
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Balance in paise (e.g., 10000 = ₹100)
    balance = Column(Integer, default=0, nullable=False)

    # Lifetime stats (all in paise)
    total_earned = Column(Integer, default=0, nullable=False)      # Total credits
    total_used = Column(Integer, default=0, nullable=False)        # Total debits for purchases
    total_withdrawn = Column(Integer, default=0, nullable=False)   # Total withdrawn to bank

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="wallet")
    transactions = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Wallet {self.user_id}: ₹{self.balance/100:.2f}>"

    @property
    def balance_inr(self) -> float:
        """Balance in INR (rupees)"""
        return self.balance / 100


class WalletTransaction(Base):
    """
    Individual wallet transaction record

    Tracks every credit/debit to the wallet for audit trail.
    """
    __tablename__ = "wallet_transactions"

    __table_args__ = (
        Index('ix_wallet_transactions_wallet', 'wallet_id'),
        Index('ix_wallet_transactions_user', 'user_id'),
        Index('ix_wallet_transactions_type', 'transaction_type'),
        Index('ix_wallet_transactions_source', 'source'),
    )

    # Primary Key
    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Which wallet
    wallet_id = Column(GUID, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Transaction details
    transaction_type = Column(SQLEnum(WalletTransactionType), nullable=False)
    source = Column(SQLEnum(WalletTransactionSource), nullable=False)

    # Amount in paise (always positive, type determines direction)
    amount = Column(Integer, nullable=False)

    # Balance after this transaction
    balance_after = Column(Integer, nullable=False)

    # Description for display
    description = Column(String(500), nullable=True)

    # Reference to related records
    reference_id = Column(String(100), nullable=True)  # Could be coupon_usage_id, order_id, etc.
    reference_type = Column(String(50), nullable=True)  # "coupon_usage", "order", "withdrawal"

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    wallet = relationship("Wallet", back_populates="transactions")
    user = relationship("User")

    def __repr__(self):
        return f"<WalletTransaction {self.transaction_type}: ₹{self.amount/100:.2f}>"

    @property
    def amount_inr(self) -> float:
        """Amount in INR (rupees)"""
        return self.amount / 100
