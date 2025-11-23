"""
AGENT 3 - Fixer Agent (Auto Debugger)
Fixes errors during generation, build, runtime, or compilation
"""

from typing import Dict, List, Optional, Any
import json
import re
from datetime import datetime

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext


class FixerAgent(BaseAgent):
    """
    Fixer Agent - Auto Debugger

    Responsibilities:
    - Fix errors during generation
    - Fix errors during build
    - Fix user-provided errors (student pastes error while running locally)
    - Fix runtime crashes
    - Fix compilation failures
    - Locate the file responsible using context + file patterns + stack trace
    - Generate corrected FULL file(s)
    """

    SYSTEM_PROMPT = """You are the FIXER AGENT (AGENT 3 - Auto Debugger).

YOUR JOB:
1. Fix errors based on logs, stack traces, build errors, or user-provided errors.
2. Locate the file responsible using context + file patterns + stack trace.
3. Generate corrected FULL file(s) using <file> blocks.
4. Do NOT change architecture unless needed.
5. Fix ONLY the real cause.

OUTPUT:
<file path="...">...</file>

RULES:
- Only update files affected by the error.
- If additional installs or commands are needed, output:
  <instructions>npm install ...</instructions>

EXAMPLE INPUT:
Error: ModuleNotFoundError: No module named 'fastapi'
Stack trace:
  File "backend/app/main.py", line 1, in <module>
    from fastapi import FastAPI

EXAMPLE OUTPUT:
<instructions>
cd backend && pip install fastapi uvicorn
</instructions>

EXAMPLE INPUT:
Error: TypeError: 'NoneType' object is not subscriptable
Stack trace:
  File "backend/app/api/todos.py", line 45, in get_todos
    user_id = request.user['id']

Context:
- FastAPI backend
- JWT authentication
- User should be injected via dependency

EXAMPLE OUTPUT:
<file path="backend/app/api/todos.py">
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.auth import get_current_user
from app.models.user import User
from app.models.todo import Todo
from app.core.database import get_db

router = APIRouter()

@router.get("/todos")
async def get_todos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Fixed: Access user.id directly instead of request.user['id']
    todos = db.query(Todo).filter(Todo.user_id == current_user.id).all()
    return {"todos": todos}
</file>

CRITICAL RULES:
1. Analyze the FULL error message and stack trace
2. Identify the ROOT CAUSE, not just symptoms
3. Fix the SPECIFIC file(s) causing the error
4. Output COMPLETE corrected files
5. If missing dependencies, use <instructions> tag
6. Do NOT refactor unrelated code
7. Maintain existing architecture
8. Fix ONLY what's broken
"""

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="FixerAgent",
            role="Auto Debugger and Error Fixer",
            capabilities=[
                "error_analysis",
                "bug_fixing",
                "build_error_resolution",
                "runtime_error_fixing",
                "compilation_error_fixing",
                "dependency_resolution"
            ],
            model=model  # Use sonnet for better debugging
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Fix errors based on provided error messages and context

        Args:
            context: AgentContext with error details

        Returns:
            Fixed files and instructions
        """
        metadata = context.metadata or {}
        error_message = metadata.get("error_message", "")
        stack_trace = metadata.get("stack_trace", "")
        affected_files = metadata.get("affected_files", [])
        project_context = metadata.get("project_context", {})

        prompt = f"""
Fix the following error:

USER REQUEST: {context.user_request}

ERROR MESSAGE:
{error_message}

STACK TRACE:
{stack_trace}

AFFECTED FILES:
{json.dumps(affected_files, indent=2)}

PROJECT CONTEXT:
{json.dumps(project_context, indent=2)}

Analyze the error, locate the responsible file(s), and provide complete corrected file(s) using <file path="...">...</file> tags.
If additional commands are needed (npm install, pip install, etc.), use <instructions>...</instructions> tag.
"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=4096,
            temperature=0.2  # Lower temperature for precise fixes
        )

        # Parse the response for file blocks and instructions
        fixed_files = self._parse_file_blocks(response)
        instructions = self._parse_instructions(response)

        return {
            "success": True,
            "fixed_files": fixed_files,
            "instructions": instructions,
            "raw_response": response
        }

    def _parse_file_blocks(self, response: str) -> List[Dict[str, str]]:
        """
        Parse <file path="...">...</file> blocks from response

        Args:
            response: Raw response from Claude

        Returns:
            List of file dictionaries with path and content
        """
        files = []
        file_pattern = r'<file\s+path="([^"]+)">(.*?)</file>'
        matches = re.findall(file_pattern, response, re.DOTALL)

        for path, content in matches:
            files.append({
                "path": path.strip(),
                "content": content.strip()
            })

        logger.info(f"Parsed {len(files)} file blocks from fixer response")
        return files

    def _parse_instructions(self, response: str) -> Optional[str]:
        """
        Parse <instructions>...</instructions> block from response

        Args:
            response: Raw response from Claude

        Returns:
            Instructions string or None
        """
        instructions_pattern = r'<instructions>(.*?)</instructions>'
        match = re.search(instructions_pattern, response, re.DOTALL)

        if match:
            instructions = match.group(1).strip()
            logger.info(f"Parsed instructions: {instructions}")
            return instructions

        return None
