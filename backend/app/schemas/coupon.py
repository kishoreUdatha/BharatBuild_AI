"""
Coupon and Wallet Schemas - Request/Response models for coupon system
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============== Enums ==============

class CouponCategoryEnum(str, Enum):
    STUDENT = "student"
    FACULTY = "faculty"
    COLLEGE = "college"
    MEDIA = "media"


class CouponStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"


class WalletTransactionTypeEnum(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    WITHDRAWAL = "withdrawal"
    REFUND = "refund"


# ============== Coupon Schemas ==============

class CouponCreate(BaseModel):
    """Schema for creating a new coupon (Admin only)"""
    code: str = Field(..., min_length=3, max_length=50, description="Unique coupon code")
    owner_name: str = Field(..., min_length=1, max_length=100, description="Name of the coupon owner")
    owner_email: str = Field(..., max_length=255, description="Email of the coupon owner")
    owner_phone: str = Field(..., min_length=10, max_length=15, description="Phone number of the coupon owner")
    category: CouponCategoryEnum = Field(..., description="Category: student, faculty, college, media")
    name: Optional[str] = Field(None, max_length=100, description="Display name for the coupon")
    description: Optional[str] = Field(None, description="Description of the coupon")
    discount_amount: int = Field(default=10000, ge=0, description="Discount for applier in paise (10000 = ₹100)")
    reward_amount: int = Field(default=10000, ge=0, description="Reward for owner in paise (10000 = ₹100)")
    valid_from: Optional[datetime] = Field(None, description="Start date (defaults to now)")
    valid_until: Optional[datetime] = Field(None, description="Expiry date (null = no expiry)")

    @field_validator('code')
    @classmethod
    def uppercase_code(cls, v):
        return v.upper().strip()


class CouponUpdate(BaseModel):
    """Schema for updating a coupon (Admin only)"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    owner_name: Optional[str] = Field(None, max_length=100)
    owner_email: Optional[str] = Field(None, max_length=255)
    owner_phone: Optional[str] = Field(None, max_length=15)
    category: Optional[CouponCategoryEnum] = None
    discount_amount: Optional[int] = Field(None, ge=0)
    reward_amount: Optional[int] = Field(None, ge=0)
    status: Optional[CouponStatusEnum] = None
    is_active: Optional[bool] = None
    valid_until: Optional[datetime] = None


class CouponResponse(BaseModel):
    """Schema for coupon response"""
    id: str
    code: str
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    owner_phone: Optional[str] = None
    category: CouponCategoryEnum
    name: Optional[str] = None
    description: Optional[str] = None
    discount_amount: int  # in paise
    discount_amount_inr: float  # in rupees
    reward_amount: int  # in paise
    reward_amount_inr: float  # in rupees
    total_uses: int
    total_discount_given: int
    total_reward_earned: int
    status: CouponStatusEnum
    is_active: bool
    valid_from: datetime
    valid_until: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CouponListResponse(BaseModel):
    """Paginated list of coupons"""
    coupons: List[CouponResponse]
    total: int
    page: int
    page_size: int


class CouponValidateRequest(BaseModel):
    """Request to validate a coupon code"""
    code: str = Field(..., description="Coupon code to validate")
    amount: int = Field(..., ge=0, description="Order amount in paise")

    @field_validator('code')
    @classmethod
    def uppercase_code(cls, v):
        return v.upper().strip()


class CouponValidateResponse(BaseModel):
    """Response after validating a coupon"""
    valid: bool
    code: str
    message: str
    discount_amount: Optional[int] = None  # in paise
    discount_amount_inr: Optional[float] = None  # in rupees
    final_amount: Optional[int] = None  # in paise
    final_amount_inr: Optional[float] = None  # in rupees
    coupon_id: Optional[str] = None
    owner_name: Optional[str] = None


class CouponApplyRequest(BaseModel):
    """Request to apply a coupon after successful payment"""
    code: str = Field(..., description="Coupon code that was applied")
    order_id: str = Field(..., description="Razorpay order ID")
    original_amount: int = Field(..., ge=0, description="Original amount in paise")
    discount_amount: int = Field(..., ge=0, description="Discount given in paise")
    final_amount: int = Field(..., ge=0, description="Final amount paid in paise")
    transaction_id: Optional[str] = Field(None, description="Transaction ID from database")

    @field_validator('code')
    @classmethod
    def uppercase_code(cls, v):
        return v.upper().strip()


class CouponApplyResponse(BaseModel):
    """Response after applying a coupon"""
    success: bool
    message: str
    coupon_usage_id: Optional[str] = None
    discount_given: Optional[int] = None
    reward_credited: Optional[int] = None
    owner_wallet_balance: Optional[int] = None


# ============== Coupon Usage Schemas ==============

class CouponUsageResponse(BaseModel):
    """Schema for coupon usage record"""
    id: str
    coupon_id: str
    coupon_code: str
    applied_by_id: str
    applied_by_name: Optional[str] = None
    applied_by_email: Optional[str] = None
    owner_id: str
    owner_name: Optional[str] = None
    order_id: Optional[str] = None
    original_amount: int
    discount_given: int
    final_amount: int
    reward_given: int
    applied_at: datetime

    class Config:
        from_attributes = True


class CouponUsageListResponse(BaseModel):
    """Paginated list of coupon usages"""
    usages: List[CouponUsageResponse]
    total: int
    page: int
    page_size: int


# ============== Wallet Schemas ==============

class WalletResponse(BaseModel):
    """Schema for wallet response"""
    id: str
    user_id: str
    balance: int  # in paise
    balance_inr: float  # in rupees
    total_earned: int
    total_used: int
    total_withdrawn: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WalletTransactionResponse(BaseModel):
    """Schema for wallet transaction"""
    id: str
    wallet_id: str
    user_id: str
    transaction_type: WalletTransactionTypeEnum
    source: str
    amount: int  # in paise
    amount_inr: float  # in rupees
    balance_after: int
    description: Optional[str] = None
    reference_id: Optional[str] = None
    reference_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class WalletTransactionListResponse(BaseModel):
    """Paginated list of wallet transactions"""
    transactions: List[WalletTransactionResponse]
    total: int
    page: int
    page_size: int
    current_balance: int
    current_balance_inr: float


class WalletWithdrawRequest(BaseModel):
    """Request to withdraw from wallet (future feature)"""
    amount: int = Field(..., gt=0, description="Amount to withdraw in paise")
    bank_account_id: Optional[str] = Field(None, description="Bank account for transfer")


# ============== User's Coupon Dashboard ==============

class MyCouponResponse(BaseModel):
    """Schema for user's own coupon details"""
    coupon: Optional[CouponResponse] = None
    has_coupon: bool
    wallet_balance: int
    wallet_balance_inr: float
    total_earnings: int
    total_earnings_inr: float
    total_uses: int
    recent_usages: List[CouponUsageResponse] = []


# ============== Admin Analytics ==============

class CouponAnalytics(BaseModel):
    """Analytics for admin dashboard"""
    total_coupons: int
    active_coupons: int
    total_uses: int
    total_discount_given: int  # in paise
    total_discount_given_inr: float
    total_rewards_paid: int  # in paise
    total_rewards_paid_inr: float
    coupons_by_category: dict  # {category: count}
    top_coupons: List[CouponResponse]


class CouponStatsResponse(BaseModel):
    """Stats for a specific coupon"""
    coupon: CouponResponse
    usage_count: int
    total_discount: int
    total_reward: int
    recent_usages: List[CouponUsageResponse]
    daily_usage: List[dict]  # [{date: "2024-01-01", count: 5}, ...]
