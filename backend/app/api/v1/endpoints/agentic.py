"""
BharatBuild Agentic API Endpoint - Claude Code Style

This endpoint provides Claude Code-style agentic conversations with tool use.
The backend handles Claude API calls, while the CLI executes tools locally.

Flow:
1. CLI sends user message + tool results (if any)
2. Backend calls Claude with tools defined
3. Backend returns Claude's response (text + tool calls)
4. CLI executes tools locally and sends results back
5. Repeat until Claude stops calling tools
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import asyncio
import json
import logging

from app.utils.claude_client import claude_client
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agentic", tags=["agentic"])


# =============================================================================
# Tool Definitions (same as Claude Code)
# =============================================================================

AGENTIC_TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file. Use this to understand existing code before making changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to read (relative to working directory)"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Create a new file or completely overwrite an existing file. Use for creating new files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to write to"
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "edit_file",
        "description": "Edit a file by replacing a specific string. Always read the file first to get exact content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to edit"
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact string to find and replace"
                },
                "new_string": {
                    "type": "string",
                    "description": "The string to replace it with"
                }
            },
            "required": ["path", "old_string", "new_string"]
        }
    },
    {
        "name": "bash",
        "description": "Execute a bash/shell command. Use for running builds, tests, git commands, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 60)",
                    "default": 60
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "glob",
        "description": "Find files matching a glob pattern. Use to discover project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern like '**/*.py' or 'src/**/*.ts'"
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "grep",
        "description": "Search for text/regex in files. Use to find code references.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The text or regex pattern to search for"
                },
                "path": {
                    "type": "string",
                    "description": "Directory or file to search in (default: current directory)",
                    "default": "."
                },
                "include": {
                    "type": "string",
                    "description": "File pattern to include (e.g., '*.py')",
                    "default": "*"
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "list_directory",
        "description": "List contents of a directory with details.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list (default: current directory)",
                    "default": "."
                }
            },
            "required": []
        }
    }
]


# System prompt for agentic mode
AGENTIC_SYSTEM_PROMPT = """You are BharatBuild AI, an expert AI coding assistant. You help developers build, debug, and improve code.

You have access to tools to read files, write files, edit files, and execute commands. Use them to accomplish tasks.

## Important Guidelines:

1. **Always read before editing** - Before modifying a file, read it first to understand its current content.

2. **Make minimal changes** - Only change what's necessary. Don't refactor unrelated code.

3. **Explain your actions** - Briefly describe what you're doing and why.

4. **Verify your work** - After making changes, run tests or builds to verify correctness.

5. **Handle errors gracefully** - If something fails, explain what went wrong and try to fix it.

## Working Directory: {working_dir}

When the user asks you to do something:
1. First explore the codebase to understand the structure
2. Read relevant files to understand the current implementation
3. Make the necessary changes
4. Verify the changes work (run tests, builds, etc.)

Be proactive but careful. Show your tool calls clearly so the user can follow along."""


# =============================================================================
# Request/Response Models
# =============================================================================

class ToolResult(BaseModel):
    """Result of a tool execution from CLI"""
    tool_use_id: str = Field(..., description="ID of the tool call")
    content: str = Field(..., description="Result content or error message")
    is_error: bool = Field(default=False, description="Whether the result is an error")


class AgenticMessage(BaseModel):
    """A message in the agentic conversation"""
    role: str = Field(..., description="Message role: user or assistant")
    content: Any = Field(..., description="Message content")


class AgenticRequest(BaseModel):
    """Request for agentic conversation"""
    messages: List[AgenticMessage] = Field(..., description="Conversation messages")
    tool_results: Optional[List[ToolResult]] = Field(default=None, description="Results from tool executions")
    working_dir: str = Field(default=".", description="CLI working directory")
    model: str = Field(default="sonnet", description="Model to use: haiku or sonnet")
    max_tokens: int = Field(default=8192, description="Max tokens for response")


class ToolCall(BaseModel):
    """A tool call from Claude"""
    id: str
    name: str
    input: Dict[str, Any]


class AgenticResponse(BaseModel):
    """Response from agentic conversation"""
    text: Optional[str] = Field(default=None, description="Text response from Claude")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tool calls to execute")
    stop_reason: str = Field(..., description="Reason for stopping: end_turn or tool_use")
    usage: Dict[str, int] = Field(..., description="Token usage")


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/chat", response_model=AgenticResponse)
async def agentic_chat(
    request: AgenticRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Handle an agentic conversation turn.

    The CLI sends messages and any tool results from the previous turn.
    The backend calls Claude and returns text + tool calls.
    The CLI executes tools locally and calls this again with results.

    This continues until Claude stops calling tools (stop_reason = end_turn).
    """
    try:
        logger.info(f"[Agentic] User {current_user.id} - Processing agentic request")

        # Build messages for Claude API
        claude_messages = []

        for msg in request.messages:
            claude_messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # If we have tool results, add them as a user message
        if request.tool_results:
            tool_result_content = []
            for result in request.tool_results:
                tool_result_content.append({
                    "type": "tool_result",
                    "tool_use_id": result.tool_use_id,
                    "content": result.content,
                    "is_error": result.is_error
                })
            claude_messages.append({
                "role": "user",
                "content": tool_result_content
            })

        # Get system prompt with working directory
        system_prompt = AGENTIC_SYSTEM_PROMPT.format(working_dir=request.working_dir)

        # Select model
        model_name = claude_client.sonnet_model if request.model == "sonnet" else claude_client.haiku_model

        logger.info(f"[Agentic] Calling Claude API with model: {model_name}")

        # Call Claude API with tools
        response = await claude_client.async_client.messages.create(
            model=model_name,
            max_tokens=request.max_tokens,
            system=system_prompt,
            tools=AGENTIC_TOOLS,
            messages=claude_messages
        )

        # Parse response
        text_content = None
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_content = block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    input=block.input
                ))

        logger.info(f"[Agentic] Claude response: {len(tool_calls)} tool calls, stop_reason: {response.stop_reason}")

        return AgenticResponse(
            text=text_content,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
        )

    except Exception as e:
        logger.error(f"[Agentic] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def agentic_chat_stream(
    request: AgenticRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Stream an agentic conversation turn.

    Returns Server-Sent Events with:
    - text_delta: Streaming text chunks
    - tool_use: Tool call information
    - done: Final message with usage stats
    """
    try:
        logger.info(f"[Agentic Stream] User {current_user.id} - Processing streaming request")

        # Build messages for Claude API
        claude_messages = []

        for msg in request.messages:
            claude_messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # If we have tool results, add them as a user message
        if request.tool_results:
            tool_result_content = []
            for result in request.tool_results:
                tool_result_content.append({
                    "type": "tool_result",
                    "tool_use_id": result.tool_use_id,
                    "content": result.content,
                    "is_error": result.is_error
                })
            claude_messages.append({
                "role": "user",
                "content": tool_result_content
            })

        # Get system prompt with working directory
        system_prompt = AGENTIC_SYSTEM_PROMPT.format(working_dir=request.working_dir)

        # Select model
        model_name = claude_client.sonnet_model if request.model == "sonnet" else claude_client.haiku_model

        async def event_generator():
            try:
                async with claude_client.async_client.messages.stream(
                    model=model_name,
                    max_tokens=request.max_tokens,
                    system=system_prompt,
                    tools=AGENTIC_TOOLS,
                    messages=claude_messages
                ) as stream:
                    # Track tool calls
                    current_tool = None
                    tool_calls = []

                    async for event in stream:
                        if event.type == "content_block_start":
                            if hasattr(event.content_block, 'type'):
                                if event.content_block.type == "tool_use":
                                    current_tool = {
                                        "id": event.content_block.id,
                                        "name": event.content_block.name,
                                        "input": ""
                                    }

                        elif event.type == "content_block_delta":
                            if hasattr(event.delta, 'text'):
                                # Text delta
                                yield f"data: {json.dumps({'type': 'text_delta', 'text': event.delta.text})}\n\n"
                            elif hasattr(event.delta, 'partial_json'):
                                # Tool input delta
                                if current_tool:
                                    current_tool["input"] += event.delta.partial_json

                        elif event.type == "content_block_stop":
                            if current_tool:
                                # Parse tool input JSON
                                try:
                                    current_tool["input"] = json.loads(current_tool["input"])
                                except:
                                    current_tool["input"] = {}

                                tool_calls.append(current_tool)
                                yield f"data: {json.dumps({'type': 'tool_use', 'tool': current_tool})}\n\n"
                                current_tool = None

                        await asyncio.sleep(0)

                    # Get final message
                    final_message = await stream.get_final_message()

                    # Send done event
                    done_data = {
                        "type": "done",
                        "stop_reason": final_message.stop_reason,
                        "tool_calls": tool_calls,
                        "usage": {
                            "input_tokens": final_message.usage.input_tokens,
                            "output_tokens": final_message.usage.output_tokens,
                            "total_tokens": final_message.usage.input_tokens + final_message.usage.output_tokens
                        }
                    }
                    yield f"data: {json.dumps(done_data)}\n\n"

            except Exception as e:
                logger.error(f"[Agentic Stream] Error: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        logger.error(f"[Agentic Stream] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def list_tools():
    """List all available tools for agentic mode"""
    return {
        "tools": [
            {
                "name": tool["name"],
                "description": tool["description"]
            }
            for tool in AGENTIC_TOOLS
        ]
    }
