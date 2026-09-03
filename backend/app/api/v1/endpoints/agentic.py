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

from app.utils.claude_client import claude_client
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.core.logging_config import logger
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.auth.feature_flags import require_agentic_mode
from app.api.v1.endpoints.agentic_credits import (
    check_credits_or_402,
    deduct_and_report,
    usage_from_message,
)

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
    # The client is the process that actually executes tools, so it is the
    # authority on which ones exist. Both fields were missing from this model,
    # so pydantic dropped them from the body and every request fell back to the
    # hardcoded AGENTIC_TOOLS. The model then called tools the CLI had never
    # registered (edit_file, list_directory) — which came back to the user as
    # "Unknown tool" — while the CLI's own tools were never offered at all.
    tools: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Tool definitions from the client. Server defaults are used when omitted.",
    )
    system: Optional[str] = Field(
        default=None,
        description="System prompt from the client. Server default is used when omitted.",
    )


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
    # The CLI has read these three since the proxy client was written
    # (proxy-model.ts) but the server never sent them, so the status bar showed
    # a local estimate as though it were an authoritative balance.
    credits_deducted: float = Field(default=0.0, description="Credits charged for this turn")
    credits_remaining: float = Field(default=-1, description="Balance after the charge; -1 when unknown")
    model_used: Optional[str] = Field(default=None, description="Model that served the turn")


# =============================================================================
# Request resolution
# =============================================================================

# A client is free to define its own toolset, but the array is forwarded
# straight to the model provider, so it has to be well-formed and bounded.
MAX_CLIENT_TOOLS = 128
MAX_CLIENT_SYSTEM_CHARS = 100_000


def resolve_tools(request: AgenticRequest) -> List[Dict[str, Any]]:
    """
    Tool definitions to send to the model.

    Prefers the client's, because the client is what executes them. Falls back
    to the server defaults for callers that send none (the web UI), which keeps
    this backwards compatible.
    """
    tools = request.tools
    if not tools:
        return AGENTIC_TOOLS

    if len(tools) > MAX_CLIENT_TOOLS:
        raise HTTPException(
            status_code=400,
            detail=f"Too many tools: {len(tools)} (max {MAX_CLIENT_TOOLS})",
        )

    seen = set()
    for index, tool in enumerate(tools):
        if not isinstance(tool, dict):
            raise HTTPException(status_code=400, detail=f"tools[{index}] must be an object")

        name = tool.get("name")
        if not isinstance(name, str) or not name:
            raise HTTPException(status_code=400, detail=f"tools[{index}] is missing a name")

        # Providers reject a tools array containing repeated names, and the
        # error they return does not say which one, so catch it here.
        if name in seen:
            raise HTTPException(status_code=400, detail=f"Duplicate tool name: {name}")
        seen.add(name)

        if not isinstance(tool.get("input_schema"), dict):
            raise HTTPException(
                status_code=400,
                detail=f"Tool '{name}' is missing an input_schema object",
            )

    return tools


def resolve_system_prompt(request: AgenticRequest) -> str:
    """
    System prompt to use. The client's own prompt describes the tools it
    actually has, so it must win when both are present.
    """
    system = request.system
    if not system:
        return AGENTIC_SYSTEM_PROMPT.format(working_dir=request.working_dir)

    if len(system) > MAX_CLIENT_SYSTEM_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"System prompt too large: {len(system)} chars (max {MAX_CLIENT_SYSTEM_CHARS})",
        )
    return system


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/chat", response_model=AgenticResponse)
async def agentic_chat(
    request: AgenticRequest,
    current_user: User = Depends(get_current_user),
    # get_db was imported but never requested, so neither endpoint had a
    # session — which is part of why credit metering was never wired here.
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_agentic_mode)
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
        system_prompt = resolve_system_prompt(request)
        active_tools = resolve_tools(request)

        # Select model
        model_name = claude_client.sonnet_model if request.model == "sonnet" else claude_client.haiku_model

        # Refuse the turn before spending anything when the account is empty.
        # This endpoint had no credit gate: the system was wired into the
        # orchestrator path only, so every CLI turn ran unmetered.
        await check_credits_or_402(current_user, db)

        logger.info(f"[Agentic] Calling Claude API with model: {model_name}")

        # Call Claude API with tools
        response = await claude_client.async_client.messages.create(
            model=model_name,
            max_tokens=request.max_tokens,
            system=system_prompt,
            tools=active_tools,
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

        # Charge for what was actually used, not what was estimated up front.
        in_tok, out_tok = usage_from_message(response)
        billing = await deduct_and_report(current_user.id, model_name, in_tok, out_tok)

        return AgenticResponse(
            text=text_content,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            **billing
        )

    # A deliberate 4xx (bad tools array, oversized system prompt) must keep its
    # status and message; the blanket handler below turned them into an opaque
    # 500 that read like a server fault rather than a malformed request.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Agentic] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def agentic_chat_stream(
    request: AgenticRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_agentic_mode)
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
        system_prompt = resolve_system_prompt(request)
        active_tools = resolve_tools(request)

        # Select model
        model_name = claude_client.sonnet_model if request.model == "sonnet" else claude_client.haiku_model

        # Gate before the stream opens, while `db` is still live and while a 402
        # can still be a clean HTTP status. Once StreamingResponse is returned
        # the status line is already sent and a refusal could only be an
        # in-band error event.
        await check_credits_or_402(current_user, db)

        # The request-scoped session is closed by the time the generator runs,
        # so deduction below opens its own. Capture the id now — touching
        # `current_user` later would hit a detached instance.
        billing_user_id = str(current_user.id)

        async def event_generator():
            try:
                async with claude_client.async_client.messages.stream(
                    model=model_name,
                    max_tokens=request.max_tokens,
                    system=system_prompt,
                    tools=active_tools,
                    messages=claude_messages
                ) as stream:
                    # Track tool calls
                    current_tool = None
                    tool_calls = []

                    # Bytes of tool input announced so far, so progress is
                    # reported at a readable rate rather than per token.
                    announced_bytes = 0

                    async for event in stream:
                        if event.type == "content_block_start":
                            if hasattr(event.content_block, 'type'):
                                if event.content_block.type == "tool_use":
                                    current_tool = {
                                        "id": event.content_block.id,
                                        "name": event.content_block.name,
                                        "input": ""
                                    }
                                    announced_bytes = 0
                                    # Say which tool is coming as soon as the
                                    # model commits to it. Nothing was emitted
                                    # until the block finished, so generating a
                                    # large file looked like the CLI had hung —
                                    # 15s of silence with no indication that a
                                    # write was even in progress.
                                    yield (
                                        "data: "
                                        + json.dumps({
                                            "type": "tool_use_start",
                                            "tool_use_id": current_tool["id"],
                                            "name": current_tool["name"],
                                        })
                                        + "\n\n"
                                    )

                        elif event.type == "content_block_delta":
                            if hasattr(event.delta, 'text'):
                                # Text delta
                                yield f"data: {json.dumps({'type': 'text_delta', 'text': event.delta.text})}\n\n"
                            elif hasattr(event.delta, 'partial_json'):
                                # Tool input delta
                                if current_tool:
                                    current_tool["input"] += event.delta.partial_json
                                    # Progress, not content: the full input is
                                    # already sent once when the block closes,
                                    # and echoing every fragment would double
                                    # the payload for a large file. A byte count
                                    # every 512 bytes is enough to drive a
                                    # live indicator.
                                    size = len(current_tool["input"])
                                    if size - announced_bytes >= 512:
                                        announced_bytes = size
                                        yield (
                                            "data: "
                                            + json.dumps({
                                                "type": "tool_use_progress",
                                                "tool_use_id": current_tool["id"],
                                                "name": current_tool["name"],
                                                "bytes": size,
                                            })
                                            + "\n\n"
                                        )

                        elif event.type == "content_block_stop":
                            if current_tool:
                                # Parse tool input JSON
                                try:
                                    current_tool["input"] = json.loads(current_tool["input"])
                                except (json.JSONDecodeError, TypeError) as e:
                                    logger.debug(f"Could not parse tool input JSON: {e}")
                                    current_tool["input"] = {}

                                tool_calls.append(current_tool)
                                yield f"data: {json.dumps({'type': 'tool_use', 'tool': current_tool})}\n\n"
                                current_tool = None

                        await asyncio.sleep(0)

                    # Get final message
                    final_message = await stream.get_final_message()

                    # Charge for actual usage. Failures here are logged and
                    # swallowed inside deduct_and_report — the answer has
                    # already been streamed to the user and must not be
                    # retracted because a ledger write failed.
                    in_tok, out_tok = usage_from_message(final_message)
                    billing = await deduct_and_report(billing_user_id, model_name, in_tok, out_tok)

                    # Send done event
                    done_data = {
                        "type": "done",
                        "stop_reason": final_message.stop_reason,
                        "tool_calls": tool_calls,
                        **billing,
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

    except HTTPException:
        raise
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
