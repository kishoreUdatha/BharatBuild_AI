from fastapi import APIRouter, Depends
from app.models.user import User
from app.modules.auth.dependencies import get_current_user

router = APIRouter()


@router.get("/plans")
async def get_plans():
    """Get available subscription plans"""
    return {
        "plans": [
            {
                "name": "Free",
                "price": 0,
                "features": ["1000 tokens/month", "Basic support"]
            },
            {
                "name": "Pro",
                "price": 999,
                "features": ["100K tokens/month", "Priority support", "All modes"]
            }
        ]
    }


@router.get("/usage")
async def get_usage(current_user: User = Depends(get_current_user)):
    """Get user's usage statistics"""
    return {
        "user_id": str(current_user.id),
        "tokens_used": 0,
        "tokens_remaining": 1000
    }
