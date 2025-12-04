"""
AGENT 4 - Runner Agent (Terminal Emulator / Command Executor)
Simulates command execution and detects errors for Fixer Agent
"""

from typing import Dict, List, Optional, Any
import asyncio
import subprocess
import json
from datetime import datetime

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext


class RunnerAgent(BaseAgent):
    """
    Runner Agent - Terminal Emulator / Command Executor

    Responsibilities:
    - Execute shell/terminal commands virtually or actually
    - Simulate build processes
    - Run install commands (npm install, pip install, etc.)
    - Run unit tests
    - Run database migrations
    - Detect errors, warnings, and dependency issues
    - Produce terminal-like output for success or error states
    - Pass detected errors to Fixer Agent
    """

    SYSTEM_PROMPT = """You are the RUNNER AGENT (AGENT 4 - Terminal Emulator / Command Executor).

YOUR JOB:
- Execute shell/terminal commands virtually.
- Produce output similar to a real terminal (success or error).
- Identify warnings, errors, dependency issues.
- NEVER fix errors.
- Only simulate execution results.

OUTPUT:
<terminal>
... logs ...
</terminal>

EXAMPLE INPUT:
Command: npm install
Project: Next.js 14 + TypeScript
Context: package.json exists with react, next dependencies

EXAMPLE OUTPUT:
<terminal>
$ npm install

npm WARN deprecated @babel/plugin-proposal-class-properties@7.18.6: This proposal has been merged to the ECMAScript standard and thus this plugin is no longer maintained.

added 524 packages, and audited 525 packages in 12s

142 packages are looking for funding
  run `npm fund` for details

found 0 vulnerabilities

[OK] Installation complete
</terminal>

EXAMPLE INPUT:
Command: npm run build
Project: Next.js frontend
Context: TypeScript errors in components

EXAMPLE OUTPUT:
<terminal>
$ npm run build

> next build

info  - Checking validity of types...
Failed to compile.

Type error: Property 'user' does not exist on type '{}'.

  32 |   return (
  33 |     <div>
> 34 |       <h1>Welcome {props.user.name}</h1>
     |                          ^
  35 |     </div>
  36 |   )
  37 | }

Error: Command failed with exit code 1
</terminal>

EXAMPLE INPUT:
Command: python manage.py migrate
Project: Django backend
Context: Database not created yet

EXAMPLE OUTPUT:
<terminal>
$ python manage.py migrate

Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions, api
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying admin.0001_initial... OK
  Applying admin.0002_logentry_remove_auto_add... OK
  Applying contenttypes.0002_remove_content_type_name... OK
  Applying auth.0002_alter_permission_name_max_length... OK
  Applying auth.0003_alter_user_email_max_length... OK
  Applying sessions.0001_initial... OK
  Applying api.0001_initial... OK

[OK] Migrations applied successfully
</terminal>

EXAMPLE INPUT:
Command: pytest tests/
Project: FastAPI backend
Context: Some tests failing

EXAMPLE OUTPUT:
<terminal>
$ pytest tests/

============================= test session starts ==============================
platform linux -- Python 3.10.12, pytest-7.4.3, pluggy-1.3.0
rootdir: /app/backend
collected 15 items

tests/test_auth.py::test_register PASSED                                [ 6%]
tests/test_auth.py::test_login PASSED                                   [13%]
tests/test_auth.py::test_invalid_credentials PASSED                     [20%]
tests/test_todos.py::test_create_todo PASSED                            [26%]
tests/test_todos.py::test_get_todos FAILED                              [33%]
tests/test_todos.py::test_update_todo PASSED                            [40%]
tests/test_todos.py::test_delete_todo PASSED                            [46%]

=================================== FAILURES ===================================
___________________________ test_get_todos ____________________________________

    def test_get_todos():
        response = client.get("/api/todos")
>       assert response.status_code == 200
E       AssertionError: assert 401 == 200
E        +  where 401 = <Response [401]>.status_code

tests/test_todos.py:45: AssertionError
========================= short test summary info ==============================
FAILED tests/test_todos.py::test_get_todos - AssertionError: assert 401 == 200
======================== 13 passed, 2 failed in 1.23s ==========================

Error: Tests failed
</terminal>

CRITICAL RULES:
1. Simulate realistic terminal output
2. Include version numbers, package counts, timing info
3. Show progress indicators (OK, PASSED, FAILED, etc.)
4. Detect and highlight errors, warnings, deprecations
5. NEVER fix errors - only report them
6. Output in <terminal> tags only
7. Be consistent with real command-line tools
8. Include exit codes for failures
"""

    def __init__(self, model: str = "haiku"):
        super().__init__(
            name="RunnerAgent",
            role="Terminal Emulator and Command Executor",
            capabilities=[
                "command_execution",
                "build_simulation",
                "test_execution",
                "dependency_installation",
                "migration_execution",
                "error_detection"
            ],
            model=model  # Use haiku for fast simulation
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Execute or simulate command execution

        Args:
            context: AgentContext with command to execute

        Returns:
            Terminal output with success/error status
        """
        metadata = context.metadata or {}
        command = context.user_request
        project_context = metadata.get("project_context", {})
        execution_mode = metadata.get("execution_mode", "simulate")  # "simulate" or "actual"

        if execution_mode == "actual":
            # Actually execute the command
            result = await self._execute_actual_command(command, project_context)
        else:
            # Simulate command execution using Claude
            result = await self._simulate_command_execution(command, project_context)

        return result

    async def _simulate_command_execution(
        self,
        command: str,
        project_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate command execution using Claude

        Args:
            command: Shell command to simulate
            project_context: Project context (tech stack, files, etc.)

        Returns:
            Simulated terminal output
        """
        prompt = f"""
Simulate the execution of this command:

COMMAND: {command}

PROJECT CONTEXT:
{json.dumps(project_context, indent=2)}

Produce realistic terminal output including:
- Command being executed
- Progress indicators
- Success/error messages
- Version numbers and package counts
- Warnings or deprecations
- Exit codes for failures

Output ONLY in <terminal>...</terminal> tags.
Make it look like real terminal output from the actual tool (npm, pip, pytest, docker, etc.).
"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=2048,
            temperature=0.3  # Lower temperature for consistent output
        )

        terminal_output = self._parse_terminal_output(response)
        has_errors = self._detect_errors(terminal_output)

        return {
            "success": not has_errors,
            "command": command,
            "terminal_output": terminal_output,
            "has_errors": has_errors,
            "raw_response": response
        }

    async def _execute_actual_command(
        self,
        command: str,
        project_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Actually execute a shell command

        Args:
            command: Shell command to execute
            project_context: Project context (working directory, etc.)

        Returns:
            Actual terminal output
        """
        working_dir = project_context.get("working_directory", ".")
        timeout = project_context.get("timeout", 300)  # 5 minutes default

        try:
            logger.info(f"Executing command: {command} in {working_dir}")

            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "command": command,
                    "terminal_output": f"<terminal>\nError: Command timed out after {timeout} seconds\n</terminal>",
                    "has_errors": True,
                    "error": "timeout"
                }

            # Combine stdout and stderr
            output = ""
            if stdout:
                output += stdout.decode('utf-8', errors='replace')
            if stderr:
                output += stderr.decode('utf-8', errors='replace')

            terminal_output = f"<terminal>\n$ {command}\n\n{output}\n</terminal>"
            has_errors = process.returncode != 0

            return {
                "success": not has_errors,
                "command": command,
                "terminal_output": terminal_output,
                "has_errors": has_errors,
                "exit_code": process.returncode
            }

        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return {
                "success": False,
                "command": command,
                "terminal_output": f"<terminal>\nError executing command: {str(e)}\n</terminal>",
                "has_errors": True,
                "error": str(e)
            }

    def _parse_terminal_output(self, response: str) -> str:
        """
        Parse <terminal>...</terminal> block from response

        Args:
            response: Raw response from Claude

        Returns:
            Terminal output string
        """
        import re
        terminal_pattern = r'<terminal>(.*?)</terminal>'
        match = re.search(terminal_pattern, response, re.DOTALL)

        if match:
            return match.group(0)  # Return with tags

        # If no tags found, wrap the response
        return f"<terminal>\n{response}\n</terminal>"

    def _detect_errors(self, terminal_output: str) -> bool:
        """
        Detect if terminal output contains errors

        Args:
            terminal_output: Terminal output string

        Returns:
            True if errors detected, False otherwise
        """
        error_indicators = [
            "Error:",
            "ERROR:",
            "FAILED",
            "failed",
            "Exception:",
            "Traceback",
            "exit code 1",
            "Command failed",
            "Build failed",
            "Test failed",
            "npm ERR!",
            "pip error",
            "fatal:",
            "ENOENT",
            "SyntaxError",
            "TypeError",
            "ModuleNotFoundError"
        ]

        for indicator in error_indicators:
            if indicator in terminal_output:
                return True

        return False
