"""
Usage API Endpoint

Shows AI usage statistics to users:
- Tokens used (today, this month, total)
- Cost breakdown by model
- Remaining balance
- Per-project usage
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional

from app.llm.usage_tracker import usage_tracker

router = APIRouter(prefix="/usage", tags=["Usage"])


class UsageSummary(BaseModel):
    total_tokens: int
    total_cost_usd: float
    total_credits: float
    total_calls: int
    models_used: List[str]
    remaining_credits: Optional[float] = None


class ModelUsage(BaseModel):
    model: str
    provider: str
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


@router.get("/session", response_model=UsageSummary)
async def get_session_usage():
    """Get usage for the current server session"""
    summary = usage_tracker.get_session_summary()
    return UsageSummary(**summary)


@router.get("/estimate")
async def estimate_cost(model: str, input_tokens: int = 1000, output_tokens: int = 500):
    """Estimate cost and credits for a specific request"""
    total_tokens = input_tokens + output_tokens
    cost = usage_tracker.get_request_cost(model, input_tokens, output_tokens)
    credits = usage_tracker.get_request_credits(model, total_tokens)
    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": cost,
        "estimated_credits": credits,
        "formatted_cost": f"${cost:.4f}",
        "formatted_credits": f"{credits:.2f} credits"
    }


@router.get("/pricing")
async def get_pricing():
    """Get pricing for all supported models"""
    from app.llm.usage_tracker import MODEL_PRICING
    
    pricing = []
    for model, (input_price, output_price) in MODEL_PRICING.items():
        pricing.append({
            "model": model,
            "input_per_million": input_price,
            "output_per_million": output_price,
            "input_per_1k": round(input_price / 1000, 4),
            "output_per_1k": round(output_price / 1000, 4),
        })
    
    return {"models": pricing}
