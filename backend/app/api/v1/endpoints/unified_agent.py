"""
Unified Agent API Endpoint

Single endpoint for Kiro-style AI interaction.
Streams real-time events as the agent thinks, reads, writes, and executes.

POST /api/v1/agent/execute
  → SSE stream of agent events (thinking, tool_call, file_created, etc.)
"""

import json
import asyncio
from typing import Optional, List, Dict
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.logging_config import logger
from app.modules.agents.base_agent import AgentContext
from app.modules.agents.unified_agent import UnifiedAgent, unified_agent


router = APIRouter(prefix="/agent", tags=["unified-agent"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class AgentExecuteRequest(BaseModel):
    """Request to execute the unified agent."""
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    project_id: str = Field(..., description="Project ID")
    user_id: Optional[str] = Field(None, description="User ID")
    # Context
    project_files: Optional[Dict[str, str]] = Field(None, description="Current project files {path: content}")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="Previous messages")
    # Model preference
    model_preference: str = Field("auto", description="Model preference: auto, fast, balanced, smart, or model ID")
    user_plan: str = Field("free", description="User subscription plan")


# =============================================================================
# ENDPOINT
# =============================================================================

@router.post("/execute")
async def execute_agent(
    request: AgentExecuteRequest,
    http_request: Request,
):
    """
    Execute the unified BharatBuild agent.
    
    Returns SSE stream with real-time events:
    - thinking: Agent reasoning
    - tool_call: Agent using a tool (read_file, write_file, etc.)
    - tool_result: Tool execution result
    - file_created: New file created
    - file_modified: File was edited
    - file_read: File was read for context
    - command_run: Shell command executed
    - command_output: Command stdout/stderr
    - message: Text response to user
    - error: Something went wrong
    - done: Task complete (includes summary)
    
    Example frontend consumption:
    ```javascript
    const response = await fetch('/api/v1/agent/execute', {
      method: 'POST',
      body: JSON.stringify({ message: "Add dark mode", project_id: "abc" })
    });
    
    const reader = response.body.getReader();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const events = new TextDecoder().decode(value).split('\\n\\n');
      for (const event of events) {
        if (event.startsWith('data: ')) {
          const data = JSON.parse(event.slice(6));
          handleAgentEvent(data);
        }
      }
    }
    ```
    """
    logger.info(f"[AgentAPI] Execute: project={request.project_id}, message={request.message[:80]}...")

    # Build context
    context = AgentContext(
        user_request=request.message,
        project_id=request.project_id,
        user_id=request.user_id,
        model_preference=request.model_preference,
        user_plan=request.user_plan,
    )

    async def event_stream():
        """SSE event generator."""
        try:
            async for event in unified_agent.execute(
                context=context,
                project_files=request.project_files or {},
                conversation_history=request.conversation_history or [],
            ):
                # Check if client disconnected
                if await http_request.is_disconnected():
                    logger.info(f"[AgentAPI] Client disconnected: {request.project_id}")
                    break

                # Format as SSE
                event_data = json.dumps(event.to_dict(), ensure_ascii=False)
                yield f"data: {event_data}\n\n"

                # Small delay for smooth streaming
                await asyncio.sleep(0.01)

            # Send done signal
            yield "data: [DONE]\n\n"

        except asyncio.CancelledError:
            logger.info(f"[AgentAPI] Stream cancelled: {request.project_id}")
        except Exception as e:
            logger.error(f"[AgentAPI] Stream error: {e}", exc_info=True)
            error_data = json.dumps({"type": "error", "data": {"message": str(e)}})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/tools")
async def list_agent_tools():
    """List all tools available to the unified agent."""
    from app.modules.agents.unified_agent import TOOLS
    return {"tools": TOOLS, "count": len(TOOLS)}
