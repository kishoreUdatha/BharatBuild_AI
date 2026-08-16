"""
Incremental Generation API Endpoint

Provides SSE (Server-Sent Events) streaming for Kiro-style
file-by-file project generation with real-time progress.

Usage:
    POST /api/v1/projects/generate/incremental
    
    Body: {
        "prompt": "Build a todo app with React and FastAPI",
        "project_id": "optional-existing-id"
    }
    
    Response: SSE stream of events:
        data: {"type": "plan_complete", "data": {"total_files": 15, ...}}
        data: {"type": "file_start", "data": {"file": "src/App.tsx", "index": 1}}
        data: {"type": "file_complete", "data": {"file": "src/App.tsx", "progress_pct": 7}}
        data: {"type": "fix_start", "data": {"file": "src/api.ts", "errors": [...]}}
        data: {"type": "fix_complete", "data": {"file": "src/api.ts"}}
        data: {"type": "done", "data": {"total_files": 15, "errors_fixed": 3}}
"""

import json
import asyncio
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.logging_config import logger
from app.modules.agents.base_agent import AgentContext
from app.modules.agents.incremental_orchestrator import (
    IncrementalOrchestrator,
    StreamEvent,
    incremental_orchestrator,
)


router = APIRouter(prefix="/projects", tags=["incremental-generation"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class IncrementalGenerateRequest(BaseModel):
    """Request body for incremental generation."""
    prompt: str = Field(..., min_length=3, max_length=5000, description="Project description")
    project_id: Optional[str] = Field(None, description="Existing project ID (for modifications)")
    user_id: Optional[str] = Field(None, description="User ID")
    # Optional overrides
    max_files: Optional[int] = Field(None, ge=1, le=100, description="Max files to generate")


# =============================================================================
# SSE STREAMING ENDPOINT
# =============================================================================

@router.post("/generate/incremental")
async def generate_incremental(
    request: IncrementalGenerateRequest,
    http_request: Request,
):
    """
    Generate a project incrementally using Kiro-style file-by-file approach.
    
    Returns an SSE stream with real-time progress events:
    - plan_start / plan_complete: Planning phase
    - file_start / file_complete: Each file being generated
    - fix_start / fix_complete: Inline error fixes
    - done: Generation complete
    - error: Fatal error
    
    Frontend should listen to this stream and update UI in real-time.
    """
    # Create project ID if not provided
    import shortuuid
    project_id = request.project_id or f"proj_{shortuuid.uuid()[:12]}"

    logger.info(f"[IncrementalAPI] Starting incremental generation: {project_id}")
    logger.info(f"[IncrementalAPI] Prompt: {request.prompt[:100]}...")

    # Build agent context
    context = AgentContext(
        user_request=request.prompt,
        project_id=project_id,
        user_id=request.user_id,
        metadata={
            "generation_mode": "incremental",
            "max_files": request.max_files,
        },
    )

    async def event_stream():
        """SSE event generator."""
        try:
            async for event in incremental_orchestrator.generate(context):
                # Check if client disconnected
                if await http_request.is_disconnected():
                    logger.info(f"[IncrementalAPI] Client disconnected: {project_id}")
                    break

                # Format as SSE
                event_data = json.dumps(event.to_dict(), ensure_ascii=False)
                yield f"data: {event_data}\n\n"

                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            logger.info(f"[IncrementalAPI] Stream cancelled: {project_id}")
        except Exception as e:
            logger.error(f"[IncrementalAPI] Stream error: {e}", exc_info=True)
            error_event = StreamEvent(type="error", data={"message": str(e)})
            yield f"data: {json.dumps(error_event.to_dict())}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/generate/incremental/{project_id}/status")
async def get_generation_status(project_id: str):
    """
    Get current generation status for a project.
    Useful for reconnection after client disconnect.
    """
    # TODO: Store progress in Redis for persistence across reconnects
    return {
        "project_id": project_id,
        "status": "unknown",
        "message": "Real-time status available via SSE stream only",
    }
