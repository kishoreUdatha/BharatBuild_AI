"""
Admin API endpoints for BharatBuild AI Admin Dashboard.
All endpoints require admin or superuser privileges.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.admin import dashboard, users, projects, billing, analytics, plans, api_keys, audit_logs, settings, feedback, websocket, sandboxes, documents

admin_router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])

# Include all admin sub-routers
admin_router.include_router(dashboard.router, prefix="/dashboard", tags=["Admin Dashboard"])
admin_router.include_router(users.router, prefix="/users", tags=["Admin Users"])
admin_router.include_router(projects.router, prefix="/projects", tags=["Admin Projects"])
admin_router.include_router(billing.router, prefix="/billing", tags=["Admin Billing"])
admin_router.include_router(analytics.router, prefix="/analytics", tags=["Admin Analytics"])
admin_router.include_router(plans.router, prefix="/plans", tags=["Admin Plans"])
admin_router.include_router(api_keys.router, prefix="/api-keys", tags=["Admin API Keys"])
admin_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Admin Audit Logs"])
admin_router.include_router(settings.router, prefix="/settings", tags=["Admin Settings"])
admin_router.include_router(feedback.router, prefix="/feedback", tags=["Admin Feedback"])
admin_router.include_router(websocket.router, tags=["Admin WebSocket"])
admin_router.include_router(sandboxes.router, prefix="/sandboxes", tags=["Admin Sandboxes"])
admin_router.include_router(documents.router, prefix="/documents", tags=["Admin Documents"])
