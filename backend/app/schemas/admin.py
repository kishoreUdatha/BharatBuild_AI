from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== Dashboard Schemas ====================

class DashboardStats(BaseModel):
    """Dashboard KPI statistics"""
    total_users: int
    active_users: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int

    total_projects: int
    active_projects: int

    total_revenue: float
    revenue_this_month: float

    total_subscriptions: int
    active_subscriptions: int

    total_tokens_used: int
    tokens_used_today: int

    total_api_calls: int
    api_calls_today: int

    # Additional analytics
    conversion_rate: float = 0.0  # % of users who converted to paid
    verification_rate: float = 0.0  # % of users who verified email
    avg_revenue_per_user: float = 0.0  # ARPU in INR


class ActivityItem(BaseModel):
    """Single activity item for activity feed"""
    id: str
    type: str  # 'user_signup', 'project_created', 'subscription', 'payment', etc.
    title: str
    description: str
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class ActivityFeedResponse(BaseModel):
    """Activity feed response"""
    items: List[ActivityItem]
    total: int


# ==================== User Management Schemas ====================

class AdminUserResponse(BaseModel):
    """Enhanced user response for admin"""
    id: str
    email: str
    full_name: Optional[str]
    username: Optional[str]
    role: str
    organization: Optional[str]
    is_active: bool
    is_verified: bool
    is_superuser: bool
    oauth_provider: Optional[str]
    avatar_url: Optional[str]
    created_at: datetime
    last_login: Optional[datetime]

    # Usage stats
    projects_count: int = 0
    tokens_used: int = 0
    subscription_plan: Optional[str] = None


class AdminUserUpdate(BaseModel):
    """Update user by admin"""
    full_name: Optional[str] = None
    role: Optional[str] = None
    organization: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_superuser: Optional[bool] = None


class BulkActionType(str, Enum):
    SUSPEND = "suspend"
    ACTIVATE = "activate"
    DELETE = "delete"
    CHANGE_ROLE = "change_role"


class BulkUserAction(BaseModel):
    """Bulk action on users"""
    user_ids: List[str]
    action: BulkActionType
    role: Optional[str] = None  # Required if action is CHANGE_ROLE


class AdminUsersResponse(BaseModel):
    """Paginated users response for admin"""
    items: List[AdminUserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Project Management Schemas ====================

class AdminProjectResponse(BaseModel):
    """Project response for admin"""
    id: str
    title: str
    description: Optional[str]
    status: str
    mode: str
    user_id: str
    user_email: str
    user_name: Optional[str]
    files_count: int = 0
    storage_size_mb: float = 0.0
    created_at: datetime
    updated_at: Optional[datetime]
    last_activity: Optional[datetime]


class AdminProjectsResponse(BaseModel):
    """Paginated projects response"""
    items: List[AdminProjectResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class StorageStats(BaseModel):
    """Storage statistics"""
    total_storage_gb: float
    used_storage_gb: float
    storage_by_user: List[Dict[str, Any]]
    storage_by_project: List[Dict[str, Any]]


# ==================== Billing Schemas ====================

class RevenueData(BaseModel):
    """Revenue data point"""
    date: str
    amount: float
    currency: str = "INR"
    transactions_count: int


class RevenueResponse(BaseModel):
    """Revenue analytics response"""
    total_revenue: float
    revenue_this_month: float
    revenue_last_month: float
    growth_percentage: float
    daily_revenue: List[RevenueData]
    monthly_revenue: List[RevenueData]


class AdminTransactionResponse(BaseModel):
    """Transaction response for admin"""
    id: str
    user_id: str
    user_email: str
    user_name: Optional[str]
    amount: int  # in paise
    currency: str
    status: str
    description: Optional[str]
    razorpay_payment_id: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


class AdminTransactionsResponse(BaseModel):
    """Paginated transactions response"""
    items: List[AdminTransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminSubscriptionResponse(BaseModel):
    """Subscription response for admin"""
    id: str
    user_id: str
    user_email: str
    user_name: Optional[str]
    plan_name: str
    plan_type: str
    status: str
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    created_at: datetime


class AdminSubscriptionsResponse(BaseModel):
    """Paginated subscriptions response"""
    items: List[AdminSubscriptionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Analytics Schemas ====================

class TimeSeriesDataPoint(BaseModel):
    """Time series data point"""
    date: str
    value: float
    label: Optional[str] = None


class UserGrowthResponse(BaseModel):
    """User growth analytics"""
    data: List[TimeSeriesDataPoint]
    total_users: int
    growth_rate: float  # percentage


class TokenUsageResponse(BaseModel):
    """Token usage analytics"""
    total_tokens: int
    tokens_by_model: Dict[str, int]
    daily_usage: List[TimeSeriesDataPoint]
    top_users: List[Dict[str, Any]]


class ApiCallsResponse(BaseModel):
    """API calls analytics"""
    total_calls: int
    calls_by_endpoint: Dict[str, int]
    daily_calls: List[TimeSeriesDataPoint]
    average_response_time: float


# ==================== Plan Management Schemas ====================

class AdminPlanCreate(BaseModel):
    """Create a new plan"""
    name: str
    slug: str
    plan_type: str  # 'free', 'student', 'basic', 'pro', 'enterprise'
    price: int  # in paise
    currency: str = "INR"
    billing_period: str = "monthly"

    # Limits
    token_limit: Optional[int] = None
    project_limit: Optional[int] = None
    api_calls_limit: Optional[int] = None
    code_generations_per_day: Optional[int] = None
    auto_fixes_per_day: Optional[int] = None
    documents_per_month: Optional[int] = None

    # Execution
    concurrent_executions: int = 1
    execution_timeout_minutes: int = 10

    # Features
    allowed_models: List[str] = ["haiku"]
    feature_flags: Dict[str, bool] = {}

    is_active: bool = True


class AdminPlanUpdate(BaseModel):
    """Update an existing plan"""
    name: Optional[str] = None
    price: Optional[int] = None
    token_limit: Optional[int] = None
    project_limit: Optional[int] = None
    feature_flags: Optional[Dict[str, bool]] = None
    is_active: Optional[bool] = None


class AdminPlanResponse(BaseModel):
    """Plan response for admin"""
    id: str
    name: str
    slug: str
    plan_type: str
    price: int
    currency: str
    billing_period: str
    token_limit: Optional[int]
    project_limit: Optional[int]
    feature_flags: Dict[str, bool] = {}
    allowed_models: List[str] = []
    subscribers_count: int = 0
    is_active: bool
    created_at: datetime


# ==================== API Keys Schemas ====================

class AdminApiKeyResponse(BaseModel):
    """API key response for admin"""
    id: str
    user_id: str
    user_email: str
    name: str
    key_prefix: str  # First 8 chars
    status: str
    rate_limit_per_minute: Optional[int]
    rate_limit_per_hour: Optional[int]
    rate_limit_per_day: Optional[int]
    token_limit: Optional[int]
    tokens_used: int = 0
    requests_count: int = 0
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime


class AdminApiKeysResponse(BaseModel):
    """Paginated API keys response"""
    items: List[AdminApiKeyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Audit Log Schemas ====================

class AuditLogResponse(BaseModel):
    """Audit log entry response"""
    id: str
    admin_id: str
    admin_email: str
    admin_name: Optional[str]
    action: str
    target_type: str
    target_id: Optional[str]
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    created_at: datetime


class AuditLogsResponse(BaseModel):
    """Paginated audit logs response"""
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Settings Schemas ====================

class SystemSettingResponse(BaseModel):
    """System setting response"""
    id: str
    key: str
    value: Any
    description: Optional[str]
    category: Optional[str]
    updated_at: datetime


class SystemSettingUpdate(BaseModel):
    """Update system setting"""
    value: Any
    description: Optional[str] = None


class FeatureFlagsResponse(BaseModel):
    """Feature flags response"""
    flags: Dict[str, bool]
    updated_at: datetime


class FeatureFlagsUpdate(BaseModel):
    """Update feature flags"""
    flags: Dict[str, bool]


# ==================== Feedback Schemas ====================

class AdminFeedbackResponse(BaseModel):
    """Feedback response for admin"""
    id: str
    user_id: str
    user_email: str
    user_name: Optional[str]
    type: str  # 'bug', 'feature', 'general', 'praise'
    rating: Optional[int]
    message: str
    status: str  # 'pending', 'reviewed', 'resolved', 'dismissed'
    admin_response: Optional[str]
    responded_at: Optional[datetime]
    created_at: datetime


class AdminFeedbacksResponse(BaseModel):
    """Paginated feedback response"""
    items: List[AdminFeedbackResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class FeedbackStatusUpdate(BaseModel):
    """Update feedback status"""
    status: str  # 'reviewed', 'resolved', 'dismissed'


class FeedbackResponseCreate(BaseModel):
    """Admin response to feedback"""
    response: str
