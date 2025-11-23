from fastapi import APIRouter
from app.api.v1.endpoints import auth, projects, api_keys, billing, tokens, streaming, bolt, automation, orchestrator

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["API Keys"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
api_router.include_router(tokens.router, prefix="/tokens", tags=["Token Management"])
api_router.include_router(streaming.router, prefix="/streaming", tags=["Streaming"])
api_router.include_router(bolt.router, tags=["Bolt AI Editor"])
api_router.include_router(automation.router, tags=["Automation Engine"])
api_router.include_router(orchestrator.router, tags=["Dynamic Orchestrator"])
