"""
Chatbot API Endpoints
=====================
Handles AI chatbot interactions for user support.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.chatbot_service import chatbot_service
from app.core.logging_config import logger

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


class ChatMessage(BaseModel):
    """Single chat message"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request to send a message to chatbot"""
    message: str = Field(..., min_length=1, max_length=1000, description="User's message")
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Previous messages in conversation"
    )
    user_context: Optional[Dict] = Field(
        default=None,
        description="Context about the user (logged in, plan, etc.)"
    )


class ChatResponse(BaseModel):
    """Chatbot response"""
    response: str = Field(..., description="AI response")
    quick_replies: List[Dict] = Field(
        default=[],
        description="Suggested follow-up questions"
    )


class QuickRepliesResponse(BaseModel):
    """Quick replies response"""
    quick_replies: List[Dict]


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    req: Request
):
    """
    Send a message to the AI chatbot and get a response.

    This endpoint is public (no auth required) to allow pre-login support.
    Rate limited to prevent abuse.
    """
    try:
        # Convert conversation history to dict format
        history = None
        if request.conversation_history:
            history = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]

        # Get AI response
        response = await chatbot_service.get_response(
            user_message=request.message,
            conversation_history=history,
            user_context=request.user_context
        )

        # Get quick reply suggestions
        quick_replies = await chatbot_service.get_quick_replies()

        logger.info(f"[Chatbot] Responded to query: {request.message[:50]}...")

        return ChatResponse(
            response=response,
            quick_replies=quick_replies
        )

    except Exception as e:
        logger.error(f"[Chatbot] Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process your message. Please try again."
        )


@router.get("/quick-replies", response_model=QuickRepliesResponse)
async def get_quick_replies(
    category: Optional[str] = None
):
    """
    Get suggested quick reply buttons.

    Categories: general, pricing, technical, payment, support
    """
    quick_replies = await chatbot_service.get_quick_replies(category)
    return QuickRepliesResponse(quick_replies=quick_replies)


@router.get("/health")
async def chatbot_health():
    """Check if chatbot service is healthy"""
    return {"status": "ok", "service": "chatbot"}
