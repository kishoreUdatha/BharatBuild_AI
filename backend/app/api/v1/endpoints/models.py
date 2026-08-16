"""
Model Selection API Endpoint

Provides:
- GET /api/v1/models — List available models for the user's plan
- POST /api/v1/models/preference — Set user's model preference
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.core.logging_config import logger
from app.config.model_registry import model_registry

router = APIRouter(prefix="/models", tags=["models"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    tier: str
    description: str
    accessible: bool
    min_plan: str
    speed_rating: int
    quality_rating: int
    supports_streaming: bool


class ModelsListResponse(BaseModel):
    models: List[ModelInfo]
    current_preference: str = "auto"
    current_plan: str = "free"


class SetPreferenceRequest(BaseModel):
    preference: str = Field(
        ...,
        description="Model preference: 'auto', 'fast', 'balanced', 'smart', or specific model ID"
    )


class SetPreferenceResponse(BaseModel):
    success: bool
    preference: str
    resolved_model: str
    message: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("", response_model=ModelsListResponse)
async def list_models(
    # TODO: Add auth dependency to get actual user plan
    # current_user: User = Depends(get_current_user),
):
    """
    List all available AI models.
    Models are filtered by user's subscription plan.
    """
    # TODO: Get actual user plan from auth
    user_plan = "free"  # Replace with: current_user.plan

    models_list = model_registry.to_frontend_list(user_plan)

    return ModelsListResponse(
        models=[ModelInfo(**m) for m in models_list],
        current_preference="auto",  # TODO: Load from user settings
        current_plan=user_plan,
    )


@router.post("/preference", response_model=SetPreferenceResponse)
async def set_model_preference(
    request: SetPreferenceRequest,
    # TODO: Add auth dependency
    # current_user: User = Depends(get_current_user),
):
    """
    Set user's model preference.
    
    Options:
    - "auto": System picks best model per task (default)
    - "fast": Always use fastest model (Haiku)
    - "balanced": Use balanced model (Sonnet)
    - "smart": Use best quality model (Opus/Sonnet)
    - Specific model ID: "haiku", "sonnet", "opus", "gpt4o", "gemini"
    """
    user_plan = "free"  # TODO: Replace with actual user plan
    preference = request.preference.lower().strip()

    # Validate preference
    valid_preferences = ["auto", "fast", "balanced", "smart"] + list(model_registry.models.keys())
    if preference not in valid_preferences:
        return SetPreferenceResponse(
            success=False,
            preference=preference,
            resolved_model="haiku",
            message=f"Invalid preference. Valid options: {', '.join(valid_preferences)}",
        )

    # Resolve what model this would give for a typical agent (planner)
    resolved = model_registry.resolve_model(
        agent_type="planner",
        user_plan=user_plan,
        user_preference=preference,
    )

    # TODO: Save preference to user settings in database
    # await update_user_setting(current_user.id, "model_preference", preference)

    logger.info(f"[Models] User set preference to '{preference}' → resolves to '{resolved}'")

    return SetPreferenceResponse(
        success=True,
        preference=preference,
        resolved_model=resolved,
        message=f"Model preference set to '{preference}'. Using {resolved} for code generation.",
    )
