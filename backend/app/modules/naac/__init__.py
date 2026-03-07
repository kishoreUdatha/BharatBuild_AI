"""
NAAC Module
Contains RBAC dependencies and workflow services for NAAC accreditation.
"""

from app.modules.naac.rbac_dependencies import (
    get_current_naac_roles,
    NAACPermissionChecker,
    require_naac_permission,
    require_naac_role,
    require_criterion_access,
    get_naac_permission_checker,
)

__all__ = [
    "get_current_naac_roles",
    "NAACPermissionChecker",
    "require_naac_permission",
    "require_naac_role",
    "require_criterion_access",
    "get_naac_permission_checker",
]
