from fastapi import APIRouter
from app.api.v1.endpoints import auth, projects, api_keys, billing, tokens, streaming, bolt, automation, orchestrator, logs, execution, documents, adventure, resume, download, containers, preview, preview_proxy, jobs, agentic, classify, sync, payments, import_project, paper, feedback, sandbox, workspace, log_stream, retrieval, users, sdk_agents, errors, autofixer_metrics, health, workshop, campus_drive, coupons, chatbot, faculty, student, trainer, git_webhooks, stories
from app.api.v1.endpoints import unified_agent, models
from app.api.v1.endpoints.admin import admin_router

api_router = APIRouter()

# Include deep health check endpoints (use /health/ready for ALB)
api_router.include_router(health.router)

# Simple health check endpoint for ALB (backward compatible)
# NOTE: For better reliability, configure ALB to use /api/v1/health/ready instead
@api_router.get("/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint for load balancer (backward compatible)"""
    return {"status": "healthy", "service": "bharatbuild-backend"}

# SECURITY NOTE: The unauthenticated /fix-db, /check-projects and /create-tables
# endpoints that used to live here have been removed. They allowed any caller to
# DROP SCHEMA public CASCADE and to dump user emails over a plain GET request.
#
# Schema management now belongs to:
#   - alembic (`alembic upgrade head`, run by scripts/entrypoint.sh at startup)
#   - scripts/init_db.py for a deliberate local bootstrap
# Read-only database introspection belongs to the authenticated admin router
# (`/api/v1/admin/...`), which enforces admin privileges.


api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(classify.router, prefix="/classify", tags=["Prompt Classification"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["API Keys"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
api_router.include_router(tokens.router, prefix="/tokens", tags=["Token Management"])
api_router.include_router(streaming.router, prefix="/streaming", tags=["Streaming"])
api_router.include_router(bolt.router, tags=["Bolt AI Editor"])
api_router.include_router(automation.router, tags=["Automation Engine"])
api_router.include_router(orchestrator.router, tags=["Dynamic Orchestrator"])
api_router.include_router(logs.router, tags=["Logs"])
api_router.include_router(execution.router, prefix="/execution", tags=["Project Execution"])
api_router.include_router(documents.router, prefix="/documents", tags=["Document Generation"])
api_router.include_router(adventure.router, tags=["Project Adventure"])
api_router.include_router(resume.router, prefix="/resume", tags=["Resume & Recovery"])
api_router.include_router(download.router, prefix="/download", tags=["Download & Temp Storage"])
api_router.include_router(containers.router, tags=["Container Execution"])
# NOTE: Old preview.py removed - replaced by preview_proxy.py (Bolt.new-style reverse proxy w/ Docker internal IP)
api_router.include_router(preview_proxy.router, tags=["Preview Reverse Proxy"])
api_router.include_router(jobs.router, tags=["Job Storage"])
api_router.include_router(agentic.router, tags=["Agentic CLI"])
api_router.include_router(sync.router, tags=["File Sync"])
api_router.include_router(import_project.router, prefix="/import", tags=["Project Import & Analysis"])
api_router.include_router(paper.router, prefix="/paper", tags=["IEEE Paper Analysis"])
api_router.include_router(feedback.router, tags=["User Feedback"])
api_router.include_router(sandbox.router, prefix="/sandbox", tags=["Sandbox Management"])
api_router.include_router(workspace.router, prefix="/workspace", tags=["Workspace Management"])
api_router.include_router(log_stream.router, prefix="/log-stream", tags=["Log Stream WebSocket"])
api_router.include_router(retrieval.router, tags=["Project Retrieval"])
api_router.include_router(users.router, prefix="/users", tags=["User Management"])
api_router.include_router(workshop.router, tags=["Workshop Enrollment"])
api_router.include_router(campus_drive.router, tags=["Campus Drive"])
api_router.include_router(faculty.router, tags=["Faculty Portal"])
api_router.include_router(student.router, tags=["Student Portal"])
api_router.include_router(trainer.router, tags=["Trainer Portal"])
api_router.include_router(git_webhooks.router, tags=["Git Webhooks"])
# One story, one address, for every portal - see endpoints/stories.py
api_router.include_router(stories.router, tags=["User Stories"])
api_router.include_router(sdk_agents.router, tags=["SDK Agents"])
api_router.include_router(errors.router, prefix="/errors", tags=["Unified Error Handler"])
api_router.include_router(autofixer_metrics.router, prefix="/autofixer", tags=["Auto-Fixer Metrics"])
api_router.include_router(coupons.router, tags=["Coupons"])
api_router.include_router(chatbot.router, tags=["Chatbot"])
api_router.include_router(unified_agent.router, tags=["Unified Agent (Kiro-style)"])
api_router.include_router(models.router, tags=["Model Selection"])
api_router.include_router(admin_router)

# MCP Deploy integration (GitHub + Vercel)
from app.mcp.deploy_endpoint import router as deploy_router
api_router.include_router(deploy_router, tags=["Deploy (MCP)"])

# Usage tracking
from app.llm.usage_endpoint import router as usage_router
api_router.include_router(usage_router, tags=["Usage Tracking"])

