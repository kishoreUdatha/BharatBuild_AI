"""
Unified BharatBuild Agent — Kiro-style Single Agent with Tools

Instead of separate Planner → Writer → Fixer pipeline,
this is ONE agent that:
1. Reads the user's message
2. Thinks about what to do (visible reasoning)
3. Uses tools (read_file, write_file, run_command, search)
4. Responds with what it did
5. All in ONE continuous conversation

Similar to how Kiro CLI works — one AI that can do everything.

Usage:
    agent = UnifiedAgent()
    async for event in agent.execute(context):
        # Events: thinking, tool_use, file_created, file_modified, command_run, done
        send_to_frontend(event)
"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.core.logging_config import logger
from app.core.config import settings
from app.modules.agents.base_agent import BaseAgent, AgentContext
from app.utils.security import sanitize_file_content_for_prompt, validate_file_path
from app.utils.output_parser import OutputParser


# =============================================================================
# EVENT TYPES
# =============================================================================

class EventType(str, Enum):
    THINKING = "thinking"           # Agent reasoning (visible to user)
    TOOL_CALL = "tool_call"         # Agent calling a tool
    TOOL_RESULT = "tool_result"     # Tool returned result
    FILE_CREATED = "file_created"   # New file created
    FILE_MODIFIED = "file_modified" # Existing file modified
    FILE_READ = "file_read"         # File was read for context
    COMMAND_RUN = "command_run"     # Shell command executed
    COMMAND_OUTPUT = "command_output"  # Command output
    MESSAGE = "message"             # Text response to user
    ERROR = "error"                 # Error occurred
    DONE = "done"                   # Task complete


@dataclass
class AgentEvent:
    """Event streamed from the unified agent."""
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type.value, "data": self.data, "timestamp": self.timestamp}


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file from the project",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to project root"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Create a new file or overwrite an existing file",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to project root"},
                "content": {"type": "string", "description": "Complete file content"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "edit_file",
        "description": "Edit part of an existing file by replacing old content with new content",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to edit"},
                "old_content": {"type": "string", "description": "Exact text to find and replace"},
                "new_content": {"type": "string", "description": "New text to replace with"}
            },
            "required": ["path", "old_content", "new_content"]
        }
    },
    {
        "name": "list_files",
        "description": "List all files in the project or a specific directory",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path (default: project root)", "default": "."}
            }
        }
    },
    {
        "name": "search_files",
        "description": "Search for text/pattern across project files",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Text or regex pattern to search"},
                "path": {"type": "string", "description": "Directory to search in", "default": "."}
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "run_command",
        "description": "Execute a shell command in the project directory (npm install, build, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 60}
            },
            "required": ["command"]
        }
    },
    {
        "name": "delete_file",
        "description": "Delete a file from the project",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to delete"}
            },
            "required": ["path"]
        }
    },
]

# System prompt for the unified agent
UNIFIED_AGENT_SYSTEM_PROMPT = """You are BharatBuild AI Agent — a powerful AI coding assistant that can read, write, and execute code in the user's project.

You work like a senior developer: you think through problems, read relevant code, make precise changes, and verify they work.

## Your Tools

You have these tools available:
- **read_file**: Read a file to understand existing code
- **write_file**: Create a new file with complete content
- **edit_file**: Edit part of an existing file (find and replace)
- **list_files**: See what files exist in the project
- **search_files**: Search for text/patterns across files
- **run_command**: Execute shell commands (install deps, build, test)
- **delete_file**: Remove a file

## How to Work

1. **Understand first** — Read relevant files before making changes
2. **Plan your approach** — Think about what needs to change
3. **Make precise edits** — Use edit_file for small changes, write_file for new files
4. **Verify** — Run build/test commands to check your changes
5. **Explain** — Tell the user what you did and why

## Rules

- ALWAYS read a file before editing it (to get current content)
- Use edit_file for modifications (NOT write_file to overwrite)
- Use write_file ONLY for new files
- When editing, use enough context in old_content to be unique (3-5 lines)
- Run `npm install` or `pip install` after adding dependencies
- After multiple file changes, run the build command to verify
- Keep changes minimal — don't rewrite files unnecessarily
- If something fails, read the error and fix it

## Response Format

Think step by step, then use tools. After completing the task, summarize what you did.
"""


# =============================================================================
# UNIFIED AGENT
# =============================================================================

class UnifiedAgent(BaseAgent):
    """
    Kiro-style unified agent that uses tools to accomplish any task.
    
    Instead of routing to separate agents, this one agent:
    - Understands the request
    - Plans an approach
    - Uses tools (read/write/edit/run) to make changes
    - Verifies the result
    - Reports back to the user
    """

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="BharatBuild Agent",
            role="unified_agent",
            capabilities=[
                "code_generation", "code_editing", "debugging",
                "file_management", "command_execution", "explanation"
            ],
            model=model
        )
        self.max_tool_calls = 25  # Max tool uses per request
        self.max_iterations = 10  # Max think-act cycles

    async def execute(
        self,
        context: AgentContext,
        project_files: Optional[Dict[str, str]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Execute user request using tools, yielding events in real-time.
        
        Args:
            context: Agent context with user request
            project_files: Dict of existing project files {path: content}
            conversation_history: Previous messages for context
            
        Yields:
            AgentEvent for each action taken
        """
        project_files = project_files or {}
        conversation_history = conversation_history or []
        tool_calls_made = 0
        files_created = []
        files_modified = []
        commands_run = []

        # Build initial messages
        messages = self._build_messages(context, project_files, conversation_history)

        yield AgentEvent(type=EventType.THINKING, data={
            "message": "Understanding your request...",
            "step": "analyzing"
        })

        try:
            for iteration in range(self.max_iterations):
                # Call Claude with tools
                response = await self._call_with_tools(
                    messages=messages,
                    context=context,
                )

                if response is None:
                    yield AgentEvent(type=EventType.ERROR, data={
                        "message": "Failed to get AI response"
                    })
                    return

                # Process response
                stop_reason = response.get("stop_reason", "end_turn")
                content_blocks = response.get("content", [])

                # Handle text blocks (thinking/response)
                for block in content_blocks:
                    if block.get("type") == "text":
                        text = block.get("text", "")
                        if text.strip():
                            yield AgentEvent(type=EventType.MESSAGE, data={
                                "content": text,
                                "iteration": iteration + 1,
                            })

                    elif block.get("type") == "tool_use":
                        tool_name = block.get("name", "")
                        tool_input = block.get("input", {})
                        tool_id = block.get("id", "")

                        tool_calls_made += 1
                        if tool_calls_made > self.max_tool_calls:
                            yield AgentEvent(type=EventType.ERROR, data={
                                "message": f"Tool call limit reached ({self.max_tool_calls})"
                            })
                            break

                        # Emit tool call event
                        yield AgentEvent(type=EventType.TOOL_CALL, data={
                            "tool": tool_name,
                            "input": tool_input,
                        })

                        # Execute the tool
                        tool_result = await self._execute_tool(
                            tool_name, tool_input, context, project_files
                        )

                        # Track what happened
                        if tool_name == "write_file" and tool_result.get("success"):
                            files_created.append(tool_input.get("path"))
                            yield AgentEvent(type=EventType.FILE_CREATED, data={
                                "path": tool_input.get("path"),
                                "size": len(tool_input.get("content", "")),
                            })
                        elif tool_name == "edit_file" and tool_result.get("success"):
                            files_modified.append(tool_input.get("path"))
                            yield AgentEvent(type=EventType.FILE_MODIFIED, data={
                                "path": tool_input.get("path"),
                            })
                        elif tool_name == "read_file":
                            yield AgentEvent(type=EventType.FILE_READ, data={
                                "path": tool_input.get("path"),
                                "found": tool_result.get("success", False),
                            })
                        elif tool_name == "run_command":
                            commands_run.append(tool_input.get("command"))
                            yield AgentEvent(type=EventType.COMMAND_RUN, data={
                                "command": tool_input.get("command"),
                                "exit_code": tool_result.get("exit_code", -1),
                            })
                            if tool_result.get("output"):
                                yield AgentEvent(type=EventType.COMMAND_OUTPUT, data={
                                    "output": tool_result["output"][:2000],
                                })

                        # Emit tool result
                        yield AgentEvent(type=EventType.TOOL_RESULT, data={
                            "tool": tool_name,
                            "success": tool_result.get("success", False),
                            "summary": tool_result.get("summary", ""),
                        })

                        # Add tool result to messages for next iteration
                        messages.append({
                            "role": "assistant",
                            "content": content_blocks,
                        })
                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": json.dumps(tool_result),
                            }],
                        })

                # If no more tool calls needed, we're done
                if stop_reason == "end_turn":
                    break

            # Done!
            yield AgentEvent(type=EventType.DONE, data={
                "files_created": files_created,
                "files_modified": files_modified,
                "commands_run": commands_run,
                "tool_calls": tool_calls_made,
                "iterations": iteration + 1,
            })

        except Exception as e:
            logger.error(f"[UnifiedAgent] Error: {e}", exc_info=True)
            yield AgentEvent(type=EventType.ERROR, data={
                "message": str(e),
            })

    async def process(self, context: AgentContext, **kwargs) -> Dict[str, Any]:
        """BaseAgent interface — collects all events and returns final result."""
        events = []
        async for event in self.execute(context, **kwargs):
            events.append(event.to_dict())

        return {
            "success": not any(e["type"] == "error" for e in events),
            "events": events,
            "agent": self.name,
        }

    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================

    def _build_messages(
        self,
        context: AgentContext,
        project_files: Dict[str, str],
        conversation_history: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """Build the initial messages for Claude."""
        messages = []

        # Add conversation history
        for msg in conversation_history[-10:]:  # Last 10 messages
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        # Build user message with project context
        user_content = context.user_request

        # Add file list context if project has files
        if project_files:
            file_list = "\n".join(f"  - {path}" for path in sorted(project_files.keys())[:50])
            user_content = f"""PROJECT FILES ({len(project_files)} files):
{file_list}

USER REQUEST:
{context.user_request}"""

        messages.append({"role": "user", "content": user_content})
        return messages

    async def _call_with_tools(
        self,
        messages: List[Dict[str, Any]],
        context: AgentContext,
    ) -> Optional[Dict[str, Any]]:
        """Call Claude with tool definitions."""
        try:
            active_model = self.resolve_model(context)

            response = await self.claude.async_client.messages.create(
                model=self.claude.sonnet_model if active_model == "sonnet" else self.claude.haiku_model,
                max_tokens=8192,
                temperature=0.3,
                system=UNIFIED_AGENT_SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            # Track tokens
            self._total_input_tokens += response.usage.input_tokens
            self._total_output_tokens += response.usage.output_tokens
            self._call_count += 1

            # Convert to dict
            content_blocks = []
            for block in response.content:
                if block.type == "text":
                    content_blocks.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    content_blocks.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            return {
                "content": content_blocks,
                "stop_reason": response.stop_reason,
            }

        except Exception as e:
            logger.error(f"[UnifiedAgent] Claude API error: {e}", exc_info=True)
            return None

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: AgentContext,
        project_files: Dict[str, str],
    ) -> Dict[str, Any]:
        """Execute a tool and return the result."""

        try:
            if tool_name == "read_file":
                return await self._tool_read_file(tool_input, context, project_files)
            elif tool_name == "write_file":
                return await self._tool_write_file(tool_input, context, project_files)
            elif tool_name == "edit_file":
                return await self._tool_edit_file(tool_input, context, project_files)
            elif tool_name == "list_files":
                return self._tool_list_files(tool_input, project_files)
            elif tool_name == "search_files":
                return self._tool_search_files(tool_input, project_files)
            elif tool_name == "run_command":
                return await self._tool_run_command(tool_input, context)
            elif tool_name == "delete_file":
                return self._tool_delete_file(tool_input, context, project_files)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _tool_read_file(
        self, input: Dict, context: AgentContext, project_files: Dict[str, str]
    ) -> Dict[str, Any]:
        """Read a file from the project."""
        path = input.get("path", "")
        
        # Validate path
        is_valid, err = validate_file_path(path)
        if not is_valid:
            return {"success": False, "error": f"Invalid path: {err}"}

        # Check in-memory files first
        if path in project_files:
            content = project_files[path]
            return {
                "success": True,
                "content": content[:15000],  # Limit size
                "size": len(content),
                "summary": f"Read {path} ({len(content)} chars)",
            }

        # Try loading from file manager
        try:
            from app.modules.automation import file_manager
            content = await file_manager.read_file(context.project_id, path)
            if content:
                project_files[path] = content  # Cache it
                return {
                    "success": True,
                    "content": content[:15000],
                    "size": len(content),
                    "summary": f"Read {path} ({len(content)} chars)",
                }
        except Exception:
            pass

        return {"success": False, "error": f"File not found: {path}"}

    async def _tool_write_file(
        self, input: Dict, context: AgentContext, project_files: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create or overwrite a file."""
        path = input.get("path", "")
        content = input.get("content", "")

        is_valid, err = validate_file_path(path)
        if not is_valid:
            return {"success": False, "error": f"Invalid path: {err}"}

        # Save to in-memory store
        project_files[path] = content

        # Save to file system
        try:
            from app.modules.automation import file_manager
            await file_manager.create_file(
                project_id=context.project_id,
                file_path=path,
                content=content
            )
        except Exception as e:
            logger.warning(f"[UnifiedAgent] File save to disk failed: {e}")

        return {
            "success": True,
            "summary": f"Created {path} ({len(content)} chars)",
        }

    async def _tool_edit_file(
        self, input: Dict, context: AgentContext, project_files: Dict[str, str]
    ) -> Dict[str, Any]:
        """Edit part of an existing file."""
        path = input.get("path", "")
        old_content = input.get("old_content", "")
        new_content = input.get("new_content", "")

        if not old_content:
            return {"success": False, "error": "old_content is required"}

        # Get current file content
        current = project_files.get(path)
        if current is None:
            return {"success": False, "error": f"File not found: {path}. Read it first."}

        # Find and replace (first occurrence only)
        if old_content not in current:
            # Try fuzzy match (strip whitespace)
            if old_content.strip() in current:
                current = current.replace(old_content.strip(), new_content.strip(), 1)
            else:
                return {
                    "success": False,
                    "error": "old_content not found in file. Make sure it matches exactly.",
                }
        else:
            current = current.replace(old_content, new_content, 1)

        # Save
        project_files[path] = current
        try:
            from app.modules.automation import file_manager
            await file_manager.update_file(
                project_id=context.project_id,
                file_path=path,
                content=current
            )
        except Exception as e:
            logger.warning(f"[UnifiedAgent] File update to disk failed: {e}")

        return {
            "success": True,
            "summary": f"Edited {path}",
        }

    def _tool_list_files(
        self, input: Dict, project_files: Dict[str, str]
    ) -> Dict[str, Any]:
        """List project files."""
        path = input.get("path", ".")
        
        if path == "." or path == "":
            files = sorted(project_files.keys())
        else:
            # Filter by directory
            prefix = path.rstrip("/") + "/"
            files = sorted(f for f in project_files.keys() if f.startswith(prefix))

        return {
            "success": True,
            "files": files[:100],
            "count": len(files),
            "summary": f"Found {len(files)} files",
        }

    def _tool_search_files(
        self, input: Dict, project_files: Dict[str, str]
    ) -> Dict[str, Any]:
        """Search across files."""
        pattern = input.get("pattern", "")
        search_path = input.get("path", ".")

        if not pattern:
            return {"success": False, "error": "pattern is required"}

        results = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            # Fallback to literal search
            regex = None

        for file_path, content in project_files.items():
            if search_path != "." and not file_path.startswith(search_path):
                continue

            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                matched = (regex.search(line) if regex else pattern.lower() in line.lower())
                if matched:
                    results.append({
                        "file": file_path,
                        "line": i,
                        "content": line.strip()[:100],
                    })
                    if len(results) >= 20:
                        break
            if len(results) >= 20:
                break

        return {
            "success": True,
            "results": results,
            "count": len(results),
            "summary": f"Found {len(results)} matches for '{pattern}'",
        }

    async def _tool_run_command(
        self, input: Dict, context: AgentContext
    ) -> Dict[str, Any]:
        """Execute a shell command."""
        command = input.get("command", "")
        timeout = min(input.get("timeout", 60), 120)

        if not command:
            return {"success": False, "error": "command is required"}

        # Block dangerous commands
        dangerous = ["rm -rf /", "sudo", "chmod 777", "> /dev/", "mkfs", "dd if="]
        if any(d in command for d in dangerous):
            return {"success": False, "error": "Command blocked for safety"}

        try:
            from app.modules.automation import file_manager
            result = await file_manager.run_command(
                project_id=context.project_id,
                command=command,
                timeout=timeout
            )
            return {
                "success": result.get("exit_code", 1) == 0,
                "exit_code": result.get("exit_code", -1),
                "output": result.get("output", "")[:5000],
                "summary": f"Ran: {command} (exit {result.get('exit_code', -1)})",
            }
        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "output": str(e),
                "summary": f"Command failed: {e}",
            }

    def _tool_delete_file(
        self, input: Dict, context: AgentContext, project_files: Dict[str, str]
    ) -> Dict[str, Any]:
        """Delete a file."""
        path = input.get("path", "")

        if path in project_files:
            del project_files[path]
            return {"success": True, "summary": f"Deleted {path}"}

        return {"success": False, "error": f"File not found: {path}"}


# =============================================================================
# SINGLETON
# =============================================================================

unified_agent = UnifiedAgent()
