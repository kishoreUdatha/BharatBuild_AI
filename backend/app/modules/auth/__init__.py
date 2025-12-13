# Authentication module

from app.modules.auth.dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_admin,
    get_current_faculty,
    get_optional_user,
    get_user_project,
    get_user_project_with_db,
    require_admin
)

from app.modules.auth.usage_limits import (
    # Core limit checks
    check_token_limit,
    check_project_limit,
    check_api_rate_limit,
    require_feature,
    check_all_limits,
    # Feature-specific limit checks
    check_document_generation_limit,
    check_document_type,
    check_bug_fixing_limit,
    check_code_generation_limit,
    check_model_access,
    # Token management
    deduct_tokens,
    log_api_usage,
    get_user_limits,
    # Data classes
    UsageLimitCheck,
    UserLimits
)

__all__ = [
    # User authentication
    "get_current_user",
    "get_current_active_user",
    "get_current_admin",
    "get_current_faculty",
    "get_optional_user",
    "get_user_project",
    "get_user_project_with_db",
    "require_admin",
    # Core usage limits
    "check_token_limit",
    "check_project_limit",
    "check_api_rate_limit",
    "require_feature",
    "check_all_limits",
    # Feature-specific limits
    "check_document_generation_limit",
    "check_document_type",
    "check_bug_fixing_limit",
    "check_code_generation_limit",
    "check_model_access",
    # Token management
    "deduct_tokens",
    "log_api_usage",
    "get_user_limits",
    # Data classes
    "UsageLimitCheck",
    "UserLimits"
]
