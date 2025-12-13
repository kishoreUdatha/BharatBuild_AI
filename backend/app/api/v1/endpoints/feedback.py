"""
Feedback API endpoints for collecting user feedback
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

from app.modules.auth.dependencies import get_optional_current_user
from app.models.user import User
from app.core.logging_config import logger

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    """Schema for creating feedback"""
    type: str  # general, bug, feature, praise
    rating: Optional[int] = None  # 1-5
    message: str
    email: Optional[EmailStr] = None
    page_url: Optional[str] = None
    user_agent: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Response after submitting feedback"""
    success: bool
    message: str
    feedback_id: Optional[str] = None


# In-memory storage for feedback (in production, use database)
feedback_storage: list = []


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackCreate,
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Submit user feedback.

    Accepts feedback from both authenticated and anonymous users.
    """
    try:
        # Validate feedback type
        valid_types = ['general', 'bug', 'feature', 'praise']
        if feedback.type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid feedback type. Must be one of: {', '.join(valid_types)}"
            )

        # Validate rating if provided
        if feedback.rating is not None and (feedback.rating < 1 or feedback.rating > 5):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rating must be between 1 and 5"
            )

        # Validate message length
        if len(feedback.message.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Feedback message must be at least 10 characters"
            )

        if len(feedback.message) > 5000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Feedback message must be less than 5000 characters"
            )

        # Create feedback record
        feedback_id = f"fb_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{len(feedback_storage)}"

        feedback_record = {
            "id": feedback_id,
            "type": feedback.type,
            "rating": feedback.rating,
            "message": feedback.message.strip(),
            "email": feedback.email,
            "page_url": feedback.page_url,
            "user_agent": feedback.user_agent,
            "user_id": str(current_user.id) if current_user else None,
            "user_email": current_user.email if current_user else None,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store feedback (in production, save to database)
        feedback_storage.append(feedback_record)

        # Log feedback for now (in production, send to Slack/Discord/Email)
        logger.info(f"New feedback received: type={feedback.type}, rating={feedback.rating}, "
                   f"user={'authenticated' if current_user else 'anonymous'}, "
                   f"message_preview={feedback.message[:50]}...")

        return FeedbackResponse(
            success=True,
            message="Thank you for your feedback!",
            feedback_id=feedback_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback. Please try again."
        )


@router.get("/stats")
async def get_feedback_stats(
    current_user: User = Depends(get_optional_current_user)
):
    """
    Get feedback statistics (admin only in production).
    For development, returns basic stats.
    """
    try:
        total = len(feedback_storage)
        by_type = {}
        avg_rating = 0
        rated_count = 0

        for fb in feedback_storage:
            fb_type = fb.get("type", "general")
            by_type[fb_type] = by_type.get(fb_type, 0) + 1
            if fb.get("rating"):
                avg_rating += fb["rating"]
                rated_count += 1

        return {
            "total": total,
            "by_type": by_type,
            "average_rating": round(avg_rating / rated_count, 2) if rated_count > 0 else None,
            "rated_count": rated_count
        }
    except Exception as e:
        logger.error(f"Error getting feedback stats: {str(e)}")
        return {"total": 0, "by_type": {}, "average_rating": None, "rated_count": 0}
