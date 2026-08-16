"""
Model Registry — Dynamic Model Selection for BharatBuild AI

Supports 19+ models across 6 providers with credit-based pricing.
Similar to Kiro Web's model selection system.

Credit System:
- 1x = base cost (reference: GPT 5.6 Terra / Auto)
- 0.05x = cheapest (Qwen3 Coder)
- 2.4x = most expensive (GPT 5.6 Sol)

Usage:
    from app.config.model_registry import model_registry

    # Get available models for user
    models = model_registry.get_available_models("premium")

    # Resolve best model for a task
    model_id = model_registry.resolve_model(
        agent_type="planner",
        user_plan="premium",
        user_preference="auto"
    )

    # Calculate credit cost
    credits = model_registry.calculate_credits(model_id, input_tokens=5000, output_tokens=3000)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from app.core.logging_config import logger


# =============================================================================
# ENUMS
# =============================================================================

class ModelTier(str, Enum):
    ULTRA = "ultra"       # Best quality, slowest (Opus 5)
    SMART = "smart"       # High quality (Opus 4.x, GPT Sol)
    BALANCED = "balanced" # Good balance (Sonnet, GPT Terra)
    FAST = "fast"         # Quick responses (Haiku, GPT Luna)
    BUDGET = "budget"     # Cheapest (DeepSeek, Qwen, MiniMax)
    AUTO = "auto"         # System picks per task


class ModelProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    MINIMAX = "minimax"
    ZHIPU = "zhipu"       # GLM
    ALIBABA = "alibaba"   # Qwen


class PlanType(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


# =============================================================================
# MODEL CONFIG
# =============================================================================

@dataclass
class ModelConfig:
    """Configuration for a single AI model."""
    id: str
    name: str
    provider: ModelProvider
    model_name: str              # Actual API model identifier
    tier: ModelTier
    description: str
    credit_multiplier: float     # Cost multiplier (1x = base)

    # Capabilities
    max_output_tokens: int = 8192
    supports_streaming: bool = True
    supports_vision: bool = False
    context_window: int = 200000

    # Access control
    min_plan: PlanType = PlanType.FREE

    # Performance (1-10)
    speed_rating: int = 5
    quality_rating: int = 5
    coding_rating: int = 5       # How good at code generation

    # Agent suitability
    best_for: List[str] = field(default_factory=list)

    # Status
    experimental: bool = False
    enabled: bool = True


# =============================================================================
# ALL AVAILABLE MODELS (19 models, 6 providers)
# =============================================================================

AVAILABLE_MODELS: Dict[str, ModelConfig] = {

    # =========================================================================
    # ANTHROPIC (Claude)
    # =========================================================================

    "claude-opus-5": ModelConfig(
        id="claude-opus-5",
        name="Claude Opus 5",
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-opus-5",
        tier=ModelTier.ULTRA,
        description="Most capable model with 1M context window",
        credit_multiplier=2.2,
        max_output_tokens=16384,
        context_window=1000000,
        min_plan=PlanType.PREMIUM,
        speed_rating=3,
        quality_rating=10,
        coding_rating=10,
        best_for=["planner", "architect", "production_fixer"],
        experimental=True,
    ),
    "claude-sonnet-5": ModelConfig(
        id="claude-sonnet-5",
        name="Claude Sonnet 5",
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-sonnet-5",
        tier=ModelTier.BALANCED,
        description="Claude Sonnet 5 model with 1M context window",
        credit_multiplier=1.3,
        max_output_tokens=16384,
        context_window=1000000,
        min_plan=PlanType.FREE,
        speed_rating=6,
        quality_rating=9,
        coding_rating=9,
        best_for=["planner", "writer", "fixer", "coder", "documenter"],
    ),
    "claude-opus-4.8": ModelConfig(
        id="claude-opus-4.8",
        name="Claude Opus 4.8",
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-opus-4-8",
        tier=ModelTier.SMART,
        description="Claude Opus 4.8 model with 1M context window",
        credit_multiplier=2.2,
        max_output_tokens=16384,
        context_window=1000000,
        min_plan=PlanType.PREMIUM,
        speed_rating=4,
        quality_rating=9,
        coding_rating=9,
        best_for=["planner", "architect", "production_fixer"],
    ),
    "claude-opus-4.7": ModelConfig(
        id="claude-opus-4.7",
        name="Claude Opus 4.7",
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-opus-4-7",
        tier=ModelTier.SMART,
        description="Claude Opus 4.7 model with 1M context window",
        credit_multiplier=2.2,
        max_output_tokens=16384,
        context_window=1000000,
        min_plan=PlanType.PREMIUM,
        speed_rating=4,
        quality_rating=9,
        coding_rating=9,
        best_for=["planner", "architect"],
    ),
    "claude-opus-4.6": ModelConfig(
        id="claude-opus-4.6",
        name="Claude Opus 4.6",
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-opus-4-6",
        tier=ModelTier.SMART,
        description="Claude Opus 4.6 model with 1M context window",
        credit_multiplier=2.2,
        max_output_tokens=8192,
        context_window=1000000,
        min_plan=PlanType.PREMIUM,
        speed_rating=4,
        quality_rating=9,
        coding_rating=9,
        best_for=["planner", "architect"],
    ),
    "claude-opus-4.5": ModelConfig(
        id="claude-opus-4.5",
        name="Claude Opus 4.5",
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-opus-4-5",
        tier=ModelTier.SMART,
        description="Claude Opus 4.5 model",
        credit_multiplier=2.2,
        max_output_tokens=8192,
        context_window=200000,
        min_plan=PlanType.PREMIUM,
        speed_rating=3,
        quality_rating=9,
        coding_rating=9,
        best_for=["planner", "architect"],
    ),
    "claude-sonnet-4.6": ModelConfig(
        id="claude-sonnet-4.6",
        name="Claude Sonnet 4.6",
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-sonnet-4-6",
        tier=ModelTier.BALANCED,
        description="Hybrid reasoning and coding for regular use",
        credit_multiplier=1.3,
        max_output_tokens=16384,
        context_window=1000000,
        min_plan=PlanType.FREE,
        speed_rating=6,
        quality_rating=8,
        coding_rating=9,
        best_for=["planner", "writer", "fixer", "coder", "documenter"],
    ),
    "claude-sonnet-4.5": ModelConfig(
        id="claude-sonnet-4.5",
        name="Claude Sonnet 4.5",
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-sonnet-4-5",
        tier=ModelTier.BALANCED,
        description="Claude Sonnet 4.5 model",
        credit_multiplier=1.3,
        max_output_tokens=8192,
        context_window=200000,
        min_plan=PlanType.FREE,
        speed_rating=6,
        quality_rating=8,
        coding_rating=8,
        best_for=["writer", "fixer", "coder"],
    ),
    "claude-sonnet-4": ModelConfig(
        id="claude-sonnet-4",
        name="Claude Sonnet 4",
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-sonnet-4-20250514",
        tier=ModelTier.BALANCED,
        description="RETIRED 2026-06-15 by Anthropic - the API returns 404. Kept "
                    "only so stored user preferences resolve instead of raising; "
                    "disabled so it is never served. Use claude-sonnet-5.",
        credit_multiplier=1.3,
        max_output_tokens=16384,
        context_window=200000,
        min_plan=PlanType.FREE,
        speed_rating=6,
        quality_rating=8,
        coding_rating=9,
        best_for=["writer", "fixer", "coder"],
        enabled=False,
    ),
    "claude-haiku-4.5": ModelConfig(
        id="claude-haiku-4.5",
        name="Claude Haiku 4.5",
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-haiku-4-5",
        tier=ModelTier.FAST,
        description="The latest Claude Haiku model",
        credit_multiplier=0.4,
        max_output_tokens=4096,
        context_window=200000,
        min_plan=PlanType.FREE,
        speed_rating=9,
        quality_rating=6,
        coding_rating=6,
        best_for=["classifier", "debugger", "runner", "verifier", "summarizer"],
    ),

    # =========================================================================
    # OPENAI (GPT)
    # =========================================================================

    "gpt-5.6-sol": ModelConfig(
        id="gpt-5.6-sol",
        name="GPT 5.6 Sol",
        provider=ModelProvider.OPENAI,
        model_name="gpt-5.6-sol",
        tier=ModelTier.ULTRA,
        description="Experimental preview of OpenAI GPT 5.6 Sol",
        credit_multiplier=2.4,
        max_output_tokens=16384,
        supports_vision=True,
        context_window=256000,
        min_plan=PlanType.PREMIUM,
        speed_rating=4,
        quality_rating=10,
        coding_rating=9,
        best_for=["planner", "architect"],
        experimental=True,
    ),
    "gpt-5.6-terra": ModelConfig(
        id="gpt-5.6-terra",
        name="GPT 5.6 Terra",
        provider=ModelProvider.OPENAI,
        model_name="gpt-5.6-terra",
        tier=ModelTier.BALANCED,
        description="Experimental preview of OpenAI GPT 5.6 Terra with 272k context",
        credit_multiplier=1.0,
        max_output_tokens=16384,
        supports_vision=True,
        context_window=272000,
        min_plan=PlanType.STARTER,
        speed_rating=7,
        quality_rating=8,
        coding_rating=8,
        best_for=["writer", "coder", "explainer"],
        experimental=True,
    ),
    "gpt-5.6-luna": ModelConfig(
        id="gpt-5.6-luna",
        name="GPT 5.6 Luna",
        provider=ModelProvider.OPENAI,
        model_name="gpt-5.6-luna",
        tier=ModelTier.FAST,
        description="Experimental preview of OpenAI GPT 5.6 Luna with 272k context",
        credit_multiplier=0.1,
        max_output_tokens=8192,
        supports_vision=True,
        context_window=272000,
        min_plan=PlanType.FREE,
        speed_rating=9,
        quality_rating=6,
        coding_rating=6,
        best_for=["classifier", "summarizer", "runner"],
        experimental=True,
    ),

    # =========================================================================
    # DEEPSEEK
    # =========================================================================

    "deepseek-v3.2": ModelConfig(
        id="deepseek-v3.2",
        name="Deepseek v3.2",
        provider=ModelProvider.DEEPSEEK,
        model_name="deepseek-chat",
        tier=ModelTier.BUDGET,
        description="Experimental preview of DeepSeek V3.2",
        credit_multiplier=0.25,
        max_output_tokens=8192,
        context_window=128000,
        min_plan=PlanType.FREE,
        speed_rating=7,
        quality_rating=7,
        coding_rating=8,
        best_for=["writer", "coder", "fixer", "debugger"],
        experimental=True,
    ),

    # =========================================================================
    # MINIMAX
    # =========================================================================

    "minimax-m2.5": ModelConfig(
        id="minimax-m2.5",
        name="MiniMax M2.5",
        provider=ModelProvider.MINIMAX,
        model_name="minimax-m2.5",
        tier=ModelTier.BUDGET,
        description="MiniMax M2.5 model",
        credit_multiplier=0.25,
        max_output_tokens=8192,
        context_window=128000,
        min_plan=PlanType.FREE,
        speed_rating=7,
        quality_rating=6,
        coding_rating=6,
        best_for=["summarizer", "explainer"],
        experimental=True,
    ),
    "minimax-m2.1": ModelConfig(
        id="minimax-m2.1",
        name="MiniMax M2.1",
        provider=ModelProvider.MINIMAX,
        model_name="minimax-m2.1",
        tier=ModelTier.BUDGET,
        description="Experimental preview of MiniMax M2.1",
        credit_multiplier=0.15,
        max_output_tokens=4096,
        context_window=64000,
        min_plan=PlanType.FREE,
        speed_rating=8,
        quality_rating=5,
        coding_rating=5,
        best_for=["classifier", "summarizer"],
        experimental=True,
    ),

    # =========================================================================
    # ZHIPU AI (GLM)
    # =========================================================================

    "glm-5": ModelConfig(
        id="glm-5",
        name="GLM 5",
        provider=ModelProvider.ZHIPU,
        model_name="glm-5",
        tier=ModelTier.BUDGET,
        description="GLM-5 model",
        credit_multiplier=0.5,
        max_output_tokens=8192,
        context_window=128000,
        min_plan=PlanType.FREE,
        speed_rating=7,
        quality_rating=7,
        coding_rating=7,
        best_for=["writer", "coder", "explainer"],
        experimental=True,
    ),

    # =========================================================================
    # ALIBABA (Qwen)
    # =========================================================================

    "qwen3-coder-next": ModelConfig(
        id="qwen3-coder-next",
        name="Qwen3 Coder Next",
        provider=ModelProvider.ALIBABA,
        model_name="qwen3-coder-next",
        tier=ModelTier.BUDGET,
        description="Experimental preview of Qwen3 Coder Next",
        credit_multiplier=0.05,
        max_output_tokens=8192,
        context_window=128000,
        min_plan=PlanType.FREE,
        speed_rating=8,
        quality_rating=6,
        coding_rating=7,
        best_for=["coder", "fixer", "debugger"],
        experimental=True,
    ),

    # =========================================================================
    # GOOGLE (Gemini)
    # =========================================================================

    "gemini-2.0-flash": ModelConfig(
        id="gemini-2.0-flash",
        name="Gemini 2.0 Flash",
        provider=ModelProvider.GOOGLE,
        model_name="gemini-2.0-flash",
        tier=ModelTier.FAST,
        description="Google's fast model with 1M context",
        credit_multiplier=0.3,
        max_output_tokens=8192,
        supports_vision=True,
        context_window=1000000,
        min_plan=PlanType.FREE,
        speed_rating=9,
        quality_rating=7,
        coding_rating=7,
        best_for=["classifier", "summarizer", "explainer"],
    ),
}


# =============================================================================
# AUTO MODE — What model each agent uses by default
# =============================================================================

# Keys must name an enabled entry in AVAILABLE_MODELS - resolve_model falls back
# here last, so a default pointing at a retired model 404s every agent that uses it.
AGENT_DEFAULT_MODELS: Dict[str, str] = {
    "planner": "claude-sonnet-5",
    "writer": "claude-sonnet-5",
    "coder": "claude-sonnet-5",
    "fixer": "claude-sonnet-5",
    "production_fixer": "claude-sonnet-5",
    "documenter": "claude-sonnet-5",
    "architect": "claude-sonnet-5",
    "debugger": "claude-haiku-4.5",
    "runner": "claude-haiku-4.5",
    "verifier": "claude-haiku-4.5",
    "summarizer": "claude-haiku-4.5",
    "classifier": "claude-haiku-4.5",
    "memory": "claude-haiku-4.5",
    "explainer": "claude-sonnet-5",
    "tester": "claude-sonnet-5",
    "enhancer": "claude-sonnet-5",
}


# =============================================================================
# MODEL REGISTRY
# =============================================================================

class ModelRegistry:
    """
    Central registry for model selection with credit-based pricing.
    """

    def __init__(self):
        self.models = AVAILABLE_MODELS
        self.agent_defaults = AGENT_DEFAULT_MODELS

    def get_all_models(self) -> List[ModelConfig]:
        """Get all registered models."""
        return list(self.models.values())

    def get_available_models(self, user_plan: str = "free") -> List[ModelConfig]:
        """Get models available to a user based on their plan."""
        plan_hierarchy = {"free": 0, "starter": 1, "premium": 2, "enterprise": 3}
        user_level = plan_hierarchy.get(user_plan.lower(), 0)

        return [
            model for model in self.models.values()
            if model.enabled and plan_hierarchy.get(model.min_plan.value, 0) <= user_level
        ]

    def get_models_by_provider(self, provider: str) -> List[ModelConfig]:
        """Get models from a specific provider."""
        return [m for m in self.models.values() if m.provider.value == provider]

    def get_models_by_tier(self, tier: str) -> List[ModelConfig]:
        """Get models in a specific tier."""
        return [m for m in self.models.values() if m.tier.value == tier]

    def resolve_model(
        self,
        agent_type: str,
        user_plan: str = "free",
        user_preference: str = "auto",
    ) -> str:
        """
        Resolve which model ID to use.

        Priority:
        1. User explicit model choice (by ID)
        2. User tier preference ("fast", "balanced", "smart", "budget", "ultra")
        3. Agent default (auto mode)
        """
        # 1. Specific model by ID
        if user_preference and user_preference not in ("auto", "fast", "balanced", "smart", "budget", "ultra"):
            if user_preference in self.models:
                model = self.models[user_preference]
                if not model.enabled:
                    logger.warning(
                        f"[ModelRegistry] User requested '{user_preference}' but it is retired/disabled. "
                        f"Falling back."
                    )
                elif self._can_access(model, user_plan):
                    return user_preference
                else:
                    logger.warning(
                        f"[ModelRegistry] User requested '{user_preference}' but plan '{user_plan}' "
                        f"doesn't have access. Falling back."
                    )

        # 2. Tier preference
        if user_preference in ("fast", "balanced", "smart", "budget", "ultra"):
            tier_map = {
                "budget": ModelTier.BUDGET,
                "fast": ModelTier.FAST,
                "balanced": ModelTier.BALANCED,
                "smart": ModelTier.SMART,
                "ultra": ModelTier.ULTRA,
            }
            target_tier = tier_map[user_preference]

            # Find best model in that tier for this agent
            candidates = [
                m for m in self.models.values()
                if m.tier == target_tier
                and m.enabled
                and self._can_access(m, user_plan)
                and (agent_type in m.best_for or not m.best_for)
            ]
            if candidates:
                # Pick the one with best coding rating
                candidates.sort(key=lambda m: m.coding_rating, reverse=True)
                return candidates[0].id

            # Fallback: any model in that tier
            any_in_tier = [
                m for m in self.models.values()
                if m.tier == target_tier and m.enabled and self._can_access(m, user_plan)
            ]
            if any_in_tier:
                return any_in_tier[0].id

        # 3. Agent default (auto mode)
        default_id = self.agent_defaults.get(agent_type, "claude-haiku-4.5")
        if (
            default_id in self.models
            and self.models[default_id].enabled
            and self._can_access(self.models[default_id], user_plan)
        ):
            return default_id

        # 4. Ultimate fallback
        return "claude-haiku-4.5"

    def get_model_config(self, model_id: str) -> Optional[ModelConfig]:
        """Get full config for a model ID."""
        return self.models.get(model_id)

    def get_model_name(self, model_id: str) -> str:
        """Get the actual API model name from an internal ID."""
        model = self.models.get(model_id)
        return model.model_name if model else "claude-3-5-haiku-20241022"

    def get_provider(self, model_id: str) -> str:
        """Get the provider for a model."""
        model = self.models.get(model_id)
        return model.provider.value if model else "anthropic"

    def calculate_credits(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate credit cost for a model call.

        Credits = (tokens / 1000) * credit_multiplier
        Base rate: 1 credit per 1000 tokens at 1x multiplier

        Returns:
            Credits consumed (float)
        """
        model = self.models.get(model_id)
        if not model:
            return 0.0

        total_tokens = input_tokens + output_tokens
        return (total_tokens / 1000) * model.credit_multiplier

    def _can_access(self, model: ModelConfig, user_plan: str) -> bool:
        """Check if user's plan can access a model."""
        plan_hierarchy = {"free": 0, "starter": 1, "premium": 2, "enterprise": 3}
        return plan_hierarchy.get(user_plan.lower(), 0) >= plan_hierarchy.get(model.min_plan.value, 0)

    def to_frontend_list(self, user_plan: str = "free") -> List[Dict[str, Any]]:
        """Get model list formatted for frontend display."""
        plan_hierarchy = {"free": 0, "starter": 1, "premium": 2, "enterprise": 3}
        user_level = plan_hierarchy.get(user_plan.lower(), 0)

        result = []

        # Add "Auto" option first
        result.append({
            "id": "auto",
            "name": "Auto",
            "provider": "system",
            "tier": "auto",
            "description": "Models chosen by task for optimal usage and consistent quality",
            "credit_multiplier": 1.0,
            "accessible": True,
            "min_plan": "free",
            "speed_rating": 7,
            "quality_rating": 8,
            "coding_rating": 8,
            "experimental": False,
            "context_window": 200000,
            # Required by the ModelInfo response schema; omitting it 500s /api/v1/models.
            "supports_streaming": True,
        })

        # Add all models sorted by credit cost (expensive first, like Kiro)
        sorted_models = sorted(self.models.values(), key=lambda m: m.credit_multiplier, reverse=True)

        for model in sorted_models:
            if not model.enabled:
                continue

            model_level = plan_hierarchy.get(model.min_plan.value, 0)
            result.append({
                "id": model.id,
                "name": model.name,
                "provider": model.provider.value,
                "tier": model.tier.value,
                "description": model.description,
                "credit_multiplier": model.credit_multiplier,
                "accessible": user_level >= model_level,
                "min_plan": model.min_plan.value,
                "speed_rating": model.speed_rating,
                "quality_rating": model.quality_rating,
                "coding_rating": model.coding_rating,
                "experimental": model.experimental,
                "context_window": model.context_window,
                "supports_streaming": model.supports_streaming,
            })

        return result


# =============================================================================
# SINGLETON
# =============================================================================

model_registry = ModelRegistry()
