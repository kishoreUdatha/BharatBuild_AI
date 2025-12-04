"""
Prompt Classification Endpoint

This endpoint uses the AI-powered PromptClassifierAgent to intelligently
classify user prompts before routing them to the appropriate handler.

Similar to how Bolt.new, Cursor, and Replit Agent classify prompts.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.modules.agents.prompt_classifier_agent import prompt_classifier_agent
from app.core.logging_config import logger

router = APIRouter()


class ClassifyRequest(BaseModel):
    prompt: str
    has_existing_project: bool = False
    current_files: Optional[List[str]] = None
    conversation_history: Optional[List[Dict[str, str]]] = None


class ClassifyResponse(BaseModel):
    intent: str  # CHAT, GENERATE, MODIFY, EXPLAIN, DEBUG, DOCUMENT, REFACTOR
    confidence: float
    reasoning: Optional[str] = None
    requires_generation: bool
    suggested_workflow: str  # bolt_standard, bolt_instant, chat_only
    entities: dict
    chat_response: Optional[str] = None


@router.post("/classify", response_model=ClassifyResponse)
async def classify_user_prompt(request: ClassifyRequest):
    """
    Classify a user prompt using the AI-powered PromptClassifierAgent.

    This is the first layer in the request pipeline - it determines the user's
    intent before routing to the appropriate handler.

    Returns:
        - intent: The classified intent (CHAT, GENERATE, MODIFY, etc.)
        - confidence: How confident the classification is (0-1)
        - reasoning: AI's reasoning for the classification
        - requires_generation: Whether this needs code generation
        - suggested_workflow: Which workflow to use
        - entities: Extracted entities (technologies, project type, etc.)
        - chat_response: For CHAT intent, the response to send back
    """
    try:
        logger.info(f"[Classify API] Received prompt: '{request.prompt[:100]}...'")

        result = await prompt_classifier_agent.classify(
            prompt=request.prompt,
            has_existing_project=request.has_existing_project,
            current_files=request.current_files,
            conversation_history=request.conversation_history
        )

        logger.info(
            f"[Classify API] Result: intent={result['intent']}, "
            f"confidence={result['confidence']:.2f}, "
            f"workflow={result['suggestedWorkflow']}"
        )

        return ClassifyResponse(
            intent=result["intent"],
            confidence=result["confidence"],
            reasoning=result.get("reasoning"),
            requires_generation=result["requiresGeneration"],
            suggested_workflow=result["suggestedWorkflow"],
            entities=result.get("entities", {}),
            chat_response=result.get("chatResponse")
        )
    except Exception as e:
        logger.error(f"[Classify API] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def classifier_health():
    """Health check for the classifier service."""
    return {"status": "healthy", "service": "prompt_classifier_agent"}
