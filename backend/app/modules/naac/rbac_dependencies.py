"""
NAAC RBAC Dependencies
Provides FastAPI dependencies for role-based access control in NAAC endpoints.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional, Callable
from datetime import datetime

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.models.user import User
from app.models.naac_rbac import (
    NAACRole,
    UserNAACRole,
    NAACPermission,
    RolePermission,
    NAACRoleType,
    NAACPermissionType,
)


async def get_current_naac_roles(
    db: AsyncSession,
    user: User,
    criterion: Optional[int] = None,
    department: Optional[str] = None,
    include_inactive: bool = False
) -> List[UserNAACRole]:
    """
    Get all NAAC roles for a user, optionally filtered by criterion/department.

    Args:
        db: Database session
        user: Current user
        criterion: Optional criterion number to filter by
        department: Optional department to filter by
        include_inactive: Include inactive role assignments

    Returns:
        List of UserNAACRole assignments
    """
    query = (
        select(UserNAACRole)
        .options(selectinload(UserNAACRole.role))
        .where(UserNAACRole.user_id == str(user.id))
    )

    if not include_inactive:
        query = query.where(UserNAACRole.is_active == True)
        query = query.where(
            (UserNAACRole.valid_until == None) |
            (UserNAACRole.valid_until > datetime.utcnow())
        )

    result = await db.execute(query)
    roles = result.scalars().all()

    # Filter by scope if specified
    if criterion is not None or department is not None:
        filtered_roles = []
        for ur in roles:
            role = ur.role

            # Check criterion access
            if criterion is not None:
                if not role.can_access_all_criteria:
                    if ur.criterion_number is not None and ur.criterion_number != criterion:
                        continue
                    if role.allowed_criteria and criterion not in role.allowed_criteria:
                        continue

            # Check department access
            if department is not None:
                if not role.can_access_all_departments:
                    if ur.department is not None and ur.department != department:
                        continue

            filtered_roles.append(ur)
        return filtered_roles

    return list(roles)


class NAACPermissionChecker:
    """
    Permission checker for NAAC resources.
    Checks if user has required permissions based on their roles.
    """

    def __init__(
        self,
        db: AsyncSession,
        user: User,
        user_roles: List[UserNAACRole]
    ):
        self.db = db
        self.user = user
        self.user_roles = user_roles
        self._permissions_cache: dict = {}
        self._roles_loaded = False

    async def _load_permissions(self):
        """Load all permissions for user's roles"""
        if self._roles_loaded:
            return

        role_ids = [str(ur.role_id) for ur in self.user_roles]
        if not role_ids:
            self._roles_loaded = True
            return

        # Get all role permissions
        query = (
            select(RolePermission)
            .options(selectinload(RolePermission.permission))
            .where(RolePermission.role_id.in_(role_ids))
        )
        result = await self.db.execute(query)
        role_perms = result.scalars().all()

        for rp in role_perms:
            key = f"{rp.permission.resource}:{rp.permission.action.value}"
            if key not in self._permissions_cache:
                self._permissions_cache[key] = []
            self._permissions_cache[key].append({
                'role_id': str(rp.role_id),
                'criterion_scope': rp.criterion_scope,
                'department_scope': rp.department_scope
            })

        self._roles_loaded = True

    async def has_permission(
        self,
        resource: str,
        action: str,
        criterion: Optional[int] = None,
        department: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission for resource:action within scope.

        Args:
            resource: Resource name (e.g., 'criterion1', 'evidence', 'task')
            action: Action name (e.g., 'view', 'edit', 'approve')
            criterion: Optional criterion number for scope check
            department: Optional department for scope check

        Returns:
            True if user has permission
        """
        # Admin/superuser bypass
        if self.user.is_superuser or self.user.role.value == 'admin':
            return True

        await self._load_permissions()

        key = f"{resource}:{action}"
        if key not in self._permissions_cache:
            # Check for wildcard permissions
            wildcard_key = f"*:{action}"
            if wildcard_key not in self._permissions_cache:
                return False
            key = wildcard_key

        perms = self._permissions_cache[key]

        for perm in perms:
            # Find the user role for this permission's role
            user_role = next(
                (ur for ur in self.user_roles if str(ur.role_id) == perm['role_id']),
                None
            )
            if not user_role:
                continue

            # Check scope restrictions
            if criterion is not None:
                # Check permission-level scope
                if perm['criterion_scope'] and criterion not in perm['criterion_scope']:
                    continue

                # Check user role scope
                if not user_role.role.can_access_all_criteria:
                    if user_role.criterion_number is not None and user_role.criterion_number != criterion:
                        continue
                    if user_role.role.allowed_criteria and criterion not in user_role.role.allowed_criteria:
                        continue

            if department is not None:
                # Check permission-level scope
                if perm['department_scope'] and department not in perm['department_scope']:
                    continue

                # Check user role scope
                if not user_role.role.can_access_all_departments:
                    if user_role.department is not None and user_role.department != department:
                        continue

            return True

        return False

    async def get_accessible_criteria(self) -> List[int]:
        """Get list of criteria the user can access"""
        criteria = set()

        for ur in self.user_roles:
            if ur.role.can_access_all_criteria:
                return list(range(1, 8))  # All 7 criteria

            if ur.criterion_number is not None:
                criteria.add(ur.criterion_number)

            if ur.role.allowed_criteria:
                criteria.update(ur.role.allowed_criteria)

        return sorted(list(criteria))

    async def get_accessible_departments(self) -> List[str]:
        """Get list of departments the user can access"""
        departments = set()

        for ur in self.user_roles:
            if ur.role.can_access_all_departments:
                return ["*"]  # All departments

            if ur.department is not None:
                departments.add(ur.department)

        return sorted(list(departments))

    def has_role(self, role_type: NAACRoleType) -> bool:
        """Check if user has a specific role type"""
        return any(ur.role.role_type == role_type for ur in self.user_roles)

    def get_highest_role(self) -> Optional[UserNAACRole]:
        """Get the user's highest-level role (lowest hierarchy number)"""
        if not self.user_roles:
            return None
        return min(self.user_roles, key=lambda ur: ur.role.hierarchy_level)

    def can_approve(self, level: str) -> bool:
        """
        Check if user can approve at a specific level.

        Args:
            level: 'department' (1), 'criterion' (2), 'iqac' (3), or 'head' (4)
        """
        level_map = {
            'department': 1,
            'criterion': 2,
            'iqac': 3,
            'head': 4
        }
        required_level = level_map.get(level, 0)

        for ur in self.user_roles:
            if ur.role.can_approve_level and ur.role.can_approve_level >= required_level:
                return True

        return False


async def get_naac_permission_checker(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> NAACPermissionChecker:
    """
    FastAPI dependency to get NAACPermissionChecker instance.
    """
    user_roles = await get_current_naac_roles(db, current_user)
    return NAACPermissionChecker(db, current_user, user_roles)


def require_naac_permission(resource: str, action: str):
    """
    Dependency factory for requiring specific NAAC permission.

    Usage:
        @router.get("/data")
        async def get_data(
            _: None = Depends(require_naac_permission("criterion1", "view"))
        ):
            ...
    """
    async def permission_dependency(
        checker: NAACPermissionChecker = Depends(get_naac_permission_checker)
    ):
        if not await checker.has_permission(resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {resource}:{action}"
            )
        return checker

    return permission_dependency


def require_naac_role(role_types: List[NAACRoleType]):
    """
    Dependency factory for requiring specific NAAC roles.

    Usage:
        @router.post("/approve")
        async def approve(
            _: None = Depends(require_naac_role([NAACRoleType.IQAC_COORDINATOR]))
        ):
            ...
    """
    async def role_dependency(
        checker: NAACPermissionChecker = Depends(get_naac_permission_checker)
    ):
        for role_type in role_types:
            if checker.has_role(role_type):
                return checker

        role_names = [rt.value for rt in role_types]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Required role: {' or '.join(role_names)}"
        )

    return role_dependency


def require_criterion_access(criterion: int):
    """
    Dependency factory for requiring access to a specific criterion.

    Usage:
        @router.get("/criterion/1/data")
        async def get_c1_data(
            _: None = Depends(require_criterion_access(1))
        ):
            ...
    """
    async def criterion_dependency(
        checker: NAACPermissionChecker = Depends(get_naac_permission_checker)
    ):
        accessible = await checker.get_accessible_criteria()
        if criterion not in accessible:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to Criterion {criterion}"
            )
        return checker

    return criterion_dependency


def require_approval_level(level: str):
    """
    Dependency factory for requiring approval capability at a level.

    Usage:
        @router.post("/approve")
        async def approve(
            _: None = Depends(require_approval_level("iqac"))
        ):
            ...
    """
    async def approval_dependency(
        checker: NAACPermissionChecker = Depends(get_naac_permission_checker)
    ):
        if not checker.can_approve(level):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot approve at {level} level"
            )
        return checker

    return approval_dependency
