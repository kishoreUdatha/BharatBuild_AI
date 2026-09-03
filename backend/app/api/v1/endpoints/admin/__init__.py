"""
Admin API endpoints for BharatBuild AI Admin Dashboard.
All endpoints require admin or superuser privileges.
"""
from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import (get_platform_admin,
                                           get_platform_staff)

from app.api.v1.endpoints.admin import dashboard, users, projects, billing, analytics, plans, api_keys, audit_logs, settings, feedback, websocket, sandboxes, documents, campus_drive, coupons, colleges, staff, trainer_assignments

admin_router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])

# Include all admin sub-routers. The routers carrying revenue, plans,
# API keys and cross-tenant analytics are the platform operator's,
# so they are guarded beyond plain admin.
admin_router.include_router(dashboard.router, prefix="/dashboard", tags=["Admin Dashboard"])
admin_router.include_router(users.router, prefix="/users", tags=["Admin Users"])
# Onboarding a college is a platform-level act, not a college admin one:
# it decides which tenant new signups land in.
admin_router.include_router(colleges.router, tags=["Admin Colleges"],
                            dependencies=[Depends(get_platform_staff)])
# Not platform-only: a college's own administrator creates their guides and
# trainers here too. The service decides which college an account lands in.
admin_router.include_router(staff.router, tags=["Admin Staff"])
# Who teaches where is the platform operator's call: a college must not be
# able to grant itself somebody else's trainer.
admin_router.include_router(trainer_assignments.router,
                            tags=["Admin Trainer Assignments"],
                            dependencies=[Depends(get_platform_staff)])
admin_router.include_router(projects.router, prefix="/projects", tags=["Admin Projects"])
admin_router.include_router(billing.router, prefix="/billing", tags=["Admin Billing"], dependencies=[Depends(get_platform_admin)])
admin_router.include_router(analytics.router, prefix="/analytics", tags=["Admin Analytics"], dependencies=[Depends(get_platform_admin)])
admin_router.include_router(plans.router, prefix="/plans", tags=["Admin Plans"], dependencies=[Depends(get_platform_admin)])
admin_router.include_router(api_keys.router, prefix="/api-keys", tags=["Admin API Keys"], dependencies=[Depends(get_platform_admin)])
admin_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Admin Audit Logs"])
admin_router.include_router(settings.router, prefix="/settings", tags=["Admin Settings"])
admin_router.include_router(feedback.router, prefix="/feedback", tags=["Admin Feedback"])
admin_router.include_router(websocket.router, tags=["Admin WebSocket"])
admin_router.include_router(sandboxes.router, prefix="/sandboxes", tags=["Admin Sandboxes"])
admin_router.include_router(documents.router, prefix="/documents", tags=["Admin Documents"])
admin_router.include_router(campus_drive.router, prefix="/campus-drive", tags=["Admin Campus Drive"])
admin_router.include_router(coupons.router, tags=["Admin Coupons"], dependencies=[Depends(get_platform_admin)])
