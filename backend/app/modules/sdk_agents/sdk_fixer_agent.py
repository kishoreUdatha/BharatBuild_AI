"""
SDK-based Fixer Agent

Uses Claude's official tool use API for automatic error fixing.
This is a production-ready implementation that:
- Automatically retries on failures
- Manages context efficiently
- Uses built-in tool handling
"""

import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
import json
import re
import os

from anthropic import AsyncAnthropic

from app.core.logging_config import logger
from app.core.config import settings
from app.modules.sdk_agents.sdk_tools import SDKToolManager, SDK_FIXER_SYSTEM_PROMPT
from app.services.unified_storage import unified_storage as storage
from app.services.smart_project_analyzer import smart_analyzer, Technology, ProjectStructure


@dataclass
class FixResult:
    """Result of a fix attempt"""
    success: bool
    files_modified: List[str]
    error_fixed: bool
    message: str
    attempts: int
    final_error: Optional[str] = None


class SDKFixerAgent:
    """
    Claude Agent SDK-style Fixer Agent.

    Uses the official Anthropic tool use API for:
    - Automatic tool execution loop
    - Built-in error handling
    - Context management
    - Retry logic
    - SMART PROJECT ANALYSIS for technology-aware fixing

    This replaces the manual implementation in fixer_agent.py with
    a cleaner, SDK-based approach that supports ALL technologies:
    - React, Vue, Angular, Svelte, Next.js
    - Python (FastAPI, Django, Flask)
    - Java (Spring Boot)
    - Go, Rust
    - Fullstack monorepos
    """

    MAX_ATTEMPTS = 5
    MAX_TOOL_ITERATIONS = 40  # Increased from 20 for complex fullstack projects

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8192
    ):
        """Initialize the SDK Fixer Agent"""
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = model
        self.max_tokens = max_tokens
        self.tools = SDKToolManager.get_fixer_tools()
        self.system_prompt = SDK_FIXER_SYSTEM_PROMPT
        # Cache for project structures
        self._project_cache: Dict[str, ProjectStructure] = {}

    async def _get_project_structure(
        self,
        project_id: str,
        user_id: str
    ) -> Optional[ProjectStructure]:
        """
        Get project structure from cache or analyze.

        This enables technology-aware fixing with proper working directories.
        """
        cache_key = f"{project_id}:{user_id}"

        if cache_key not in self._project_cache:
            try:
                structure = await smart_analyzer.analyze_project(
                    project_id=project_id,
                    user_id=user_id
                )
                self._project_cache[cache_key] = structure
                logger.info(f"[SDKFixerAgent:{project_id}] Analyzed project: {structure.technology.value}")
            except Exception as e:
                logger.warning(f"[SDKFixerAgent:{project_id}] Failed to analyze project: {e}")
                return None

        return self._project_cache.get(cache_key)

    async def fix_error(
        self,
        project_id: str,
        user_id: str,
        error_message: str,
        stack_trace: str = "",
        command: str = "",
        context_files: Optional[Dict[str, str]] = None
    ) -> FixResult:
        """
        Fix an error using the SDK tool loop with technology awareness.

        Args:
            project_id: Project identifier
            user_id: User identifier
            error_message: The error to fix
            stack_trace: Stack trace if available
            command: Command that caused the error
            context_files: Dict of file paths to contents for context

        Returns:
            FixResult with success status and details
        """
        logger.info(f"[SDKFixerAgent:{project_id}] Starting fix for: {error_message[:100]}...")

        # Get project structure for technology-aware fixing
        project_structure = await self._get_project_structure(project_id, user_id)

        # Build initial message with error context AND technology info
        user_message = self._build_error_prompt(
            error_message=error_message,
            stack_trace=stack_trace,
            command=command,
            context_files=context_files,
            project_structure=project_structure
        )

        # Initialize conversation
        messages = [{"role": "user", "content": user_message}]
        files_modified = []
        attempts = 0

        try:
            # Run the agent loop
            while attempts < self.MAX_TOOL_ITERATIONS:
                attempts += 1

                # Call Claude with tools
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=self.system_prompt,
                    tools=self.tools,
                    messages=messages
                )

                logger.info(f"[SDKFixerAgent:{project_id}] Iteration {attempts}, stop_reason: {response.stop_reason}")

                # Check if we're done
                if response.stop_reason == "end_turn":
                    # Extract final message
                    final_text = self._extract_text(response.content)
                    return FixResult(
                        success=True,
                        files_modified=files_modified,
                        error_fixed=True,
                        message=final_text,
                        attempts=attempts
                    )

                # Process tool uses
                if response.stop_reason == "tool_use":
                    # Add assistant's response to messages
                    messages.append({
                        "role": "assistant",
                        "content": response.content
                    })

                    # Execute tools and collect results
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            result = await self._execute_tool(
                                project_id=project_id,
                                user_id=user_id,
                                tool_name=block.name,
                                tool_input=block.input
                            )

                            # Track modified files
                            if block.name in ["str_replace", "str_replace_all", "create_file", "insert_lines"]:
                                file_path = block.input.get("path", "")
                                if file_path and file_path not in files_modified:
                                    files_modified.append(file_path)

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result
                            })

                    # Add tool results to messages
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })
                else:
                    # Unexpected stop reason
                    logger.warning(f"[SDKFixerAgent:{project_id}] Unexpected stop_reason: {response.stop_reason}")
                    break

            # Max iterations reached
            return FixResult(
                success=False,
                files_modified=files_modified,
                error_fixed=False,
                message="Max iterations reached without completing fix",
                attempts=attempts
            )

        except Exception as e:
            logger.error(f"[SDKFixerAgent:{project_id}] Error during fix: {e}")
            return FixResult(
                success=False,
                files_modified=files_modified,
                error_fixed=False,
                message=str(e),
                attempts=attempts,
                final_error=str(e)
            )

    async def fix_with_retry(
        self,
        project_id: str,
        user_id: str,
        error_message: str,
        stack_trace: str = "",
        command: str = "",
        build_command: str = "npm run build",
        max_retries: int = 3
    ) -> FixResult:
        """
        Fix error with automatic retry and verification.

        After each fix attempt, runs the build command to verify.
        Continues until fixed or max retries reached.

        Args:
            project_id: Project identifier
            user_id: User identifier
            error_message: Initial error message
            stack_trace: Stack trace if available
            command: Command that caused the error
            build_command: Command to run for verification
            max_retries: Maximum number of fix attempts

        Returns:
            FixResult with final status
        """
        current_error = error_message
        current_stack = stack_trace
        all_files_modified = []
        total_attempts = 0

        for retry in range(max_retries):
            logger.info(f"[SDKFixerAgent:{project_id}] Fix attempt {retry + 1}/{max_retries}")

            # Attempt fix
            result = await self.fix_error(
                project_id=project_id,
                user_id=user_id,
                error_message=current_error,
                stack_trace=current_stack,
                command=command
            )

            total_attempts += result.attempts
            all_files_modified.extend(result.files_modified)

            if not result.success:
                continue

            # Verify by running build
            verify_result = await self._execute_tool(
                project_id=project_id,
                user_id=user_id,
                tool_name="bash",
                tool_input={"command": build_command, "timeout": 60}
            )

            # Check if build succeeded
            if "error" not in verify_result.lower() and "failed" not in verify_result.lower():
                logger.info(f"[SDKFixerAgent:{project_id}] Fix verified successfully!")
                return FixResult(
                    success=True,
                    files_modified=list(set(all_files_modified)),
                    error_fixed=True,
                    message=f"Fixed after {retry + 1} attempts",
                    attempts=total_attempts
                )

            # Extract new error for next attempt
            current_error = verify_result
            current_stack = ""
            logger.warning(f"[SDKFixerAgent:{project_id}] Build still failing, retrying...")

        # Max retries exhausted
        return FixResult(
            success=False,
            files_modified=list(set(all_files_modified)),
            error_fixed=False,
            message=f"Failed to fix after {max_retries} attempts",
            attempts=total_attempts,
            final_error=current_error
        )

    def _build_error_prompt(
        self,
        error_message: str,
        stack_trace: str = "",
        command: str = "",
        context_files: Optional[Dict[str, str]] = None,
        project_structure: Optional[ProjectStructure] = None
    ) -> str:
        """Build the initial prompt with error context and technology info"""
        parts = []

        # Add technology context if available
        if project_structure:
            parts.append("## Project Context\n")
            parts.append(f"**Technology:** {project_structure.technology.value}\n")
            parts.append(f"**Working Directory:** {project_structure.working_directory.name}/\n")
            parts.append(f"**Install Command:** `{project_structure.install_command}`\n")
            parts.append(f"**Run Command:** `{project_structure.run_command}`\n")
            if project_structure.entry_points:
                parts.append(f"**Entry Points:** {', '.join(project_structure.entry_points)}\n")
            parts.append("\n")

        parts.extend([
            "## Error to Fix\n",
            f"**Command:** `{command}`\n" if command else "",
            f"**Error Message:**\n```\n{error_message}\n```\n",
        ])

        if stack_trace:
            parts.append(f"**Stack Trace:**\n```\n{stack_trace[:2000]}\n```\n")

        if context_files:
            parts.append("\n## Related Files (READ THESE FIRST)\n")
            # Prioritize build config files
            build_configs = ["pom.xml", "build.gradle", "package.json", "requirements.txt", "go.mod", "Cargo.toml"]
            sorted_files = sorted(
                context_files.items(),
                key=lambda x: (0 if any(cfg in x[0] for cfg in build_configs) else 1, x[0])
            )
            # Include more context files - up to 15
            for path, content in sorted_files[:15]:
                # Truncate based on file type - build configs get more space
                is_build_config = any(cfg in path for cfg in build_configs)
                max_size = 3000 if is_build_config else 2000
                truncated = content[:max_size] if len(content) > max_size else content
                # Identify file type for syntax highlighting
                ext = path.split('.')[-1] if '.' in path else ''
                lang = {'java': 'java', 'py': 'python', 'ts': 'typescript', 'tsx': 'tsx',
                        'js': 'javascript', 'json': 'json', 'xml': 'xml', 'properties': 'properties',
                        'go': 'go', 'rs': 'rust', 'toml': 'toml', 'gradle': 'groovy'}.get(ext, '')
                parts.append(f"### {path}\n```{lang}\n{truncated}\n```\n")

        # Technology-specific fix guidance
        tech_guidance = ""
        if project_structure:
            tech = project_structure.technology
            if tech in [Technology.REACT_VITE, Technology.VUE_VITE]:
                tech_guidance = """
**React/Vite Specific:**
- For import errors, check if the package exists in package.json
- For "Failed to resolve import", the file might be missing - create it
- For TypeScript errors, check tsconfig.json settings
- Working directory is where package.json is located
"""
            elif tech in [Technology.FASTAPI, Technology.FLASK, Technology.DJANGO]:
                tech_guidance = """
**Python Specific:**
- For import errors, check if the package is in requirements.txt
- For module not found, check the file path and __init__.py files
- For FastAPI, check Pydantic model definitions
- Run pip install -r requirements.txt if dependencies are missing
"""
            elif tech in [Technology.SPRING_BOOT_MAVEN, Technology.SPRING_BOOT_GRADLE]:
                tech_guidance = """
**Java/Spring Boot Specific:**
- **CRITICAL**: Spring Boot 3+ uses `jakarta.*` instead of `javax.*` - replace ALL occurrences
  - `javax.validation.*` → `jakarta.validation.*`
  - `javax.persistence.*` → `jakarta.persistence.*`
  - `javax.servlet.*` → `jakarta.servlet.*`
- Use `str_replace_all` to fix all javax imports in a file at once
- For "cannot find symbol" on getters/setters: Check if Entity class has Lombok @Data or explicit getters
- For "package does not exist": Add the correct dependency to pom.xml
- Build command: `mvn clean compile` (not install, just compile to test)
- Check pom.xml for Spring Boot version - if 3.x, ALL javax must be jakarta
"""
            elif tech in [Technology.GO]:
                tech_guidance = """
**Go Specific:**
- For import errors, check go.mod and run go mod tidy
- For undefined errors, check function/type visibility (capitalization)
- For struct errors, check field names and types
"""
            elif tech in [Technology.RUST]:
                tech_guidance = """
**Rust Specific:**
- For borrow checker errors, consider using references or cloning
- For missing trait implementations, add #[derive] or impl blocks
- For type mismatches, check ownership and lifetimes
- Run cargo build after changes
"""

        parts.append(f"""
## Your Task

1. **Analyze** the error message and identify the root cause
2. **Read the build config** (pom.xml, package.json, etc.) to understand dependencies
3. **Read the error file** using `view_file` to see the exact code
4. **Fix the issue**:
   - Use `str_replace` for single fixes
   - Use `str_replace_all` for fixing ALL occurrences (e.g., javax→jakarta)
   - Use `create_file` for missing files
5. **Verify** by running the build command with `bash`
6. **Repeat** if there are more errors
{tech_guidance}
**IMPORTANT:**
- Working directory: {project_structure.working_directory.name if project_structure else 'project root'}
- Read files BEFORE modifying them
- Fix ALL related errors, not just the first one
- Run the build after each major fix to see remaining errors

Start by analyzing the error and reading the relevant build config file.
""")

        return "".join(parts)

    def _extract_text(self, content: List[Any]) -> str:
        """Extract text from response content blocks"""
        text_parts = []
        for block in content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "\n".join(text_parts)

    async def _execute_tool(
        self,
        project_id: str,
        user_id: str,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """
        Execute a tool and return the result.

        This connects SDK tools to BharatBuild's sandbox environment.
        """
        logger.info(f"[SDKFixerAgent:{project_id}] Executing tool: {tool_name}")

        try:
            if tool_name == "bash":
                return await self._execute_bash(project_id, user_id, tool_input)
            elif tool_name == "view_file":
                return await self._execute_view_file(project_id, user_id, tool_input)
            elif tool_name == "str_replace":
                return await self._execute_str_replace(project_id, user_id, tool_input)
            elif tool_name == "str_replace_all":
                return await self._execute_str_replace_all(project_id, user_id, tool_input)
            elif tool_name == "create_file":
                return await self._execute_create_file(project_id, user_id, tool_input)
            elif tool_name == "insert_lines":
                return await self._execute_insert_lines(project_id, user_id, tool_input)
            elif tool_name == "glob":
                return await self._execute_glob(project_id, user_id, tool_input)
            elif tool_name == "grep":
                return await self._execute_grep(project_id, user_id, tool_input)
            elif tool_name == "list_directory":
                return await self._execute_list_dir(project_id, user_id, tool_input)
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            logger.error(f"[SDKFixerAgent:{project_id}] Tool error: {e}")
            return f"Error executing {tool_name}: {str(e)}"

    async def _execute_bash(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Execute a bash command in the sandbox with smart working directory"""
        command = tool_input.get("command", "")
        timeout = tool_input.get("timeout", 120)

        if not command:
            return "Error: No command provided"

        try:
            # Get sandbox path
            sandbox_path = storage.get_sandbox_path(project_id, user_id)

            # Use smart working directory from cached project structure
            cache_key = f"{project_id}:{user_id}"
            working_dir = sandbox_path

            if cache_key in self._project_cache:
                project_structure = self._project_cache[cache_key]
                # Use the smart analyzer's detected working directory
                working_dir = str(project_structure.working_directory)
                logger.info(f"[SDKFixerAgent:{project_id}] Using smart working dir: {working_dir}")
            else:
                # Try to get working directory from smart analyzer
                try:
                    project_structure = await smart_analyzer.analyze_project(
                        project_id=project_id,
                        user_id=user_id
                    )
                    working_dir = str(project_structure.working_directory)
                    self._project_cache[cache_key] = project_structure
                    logger.info(f"[SDKFixerAgent:{project_id}] Analyzed and using working dir: {working_dir}")
                except Exception as e:
                    logger.warning(f"[SDKFixerAgent:{project_id}] Could not analyze, using sandbox root: {e}")

            # Execute command in the correct working directory (non-blocking)
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return f"Error: Command timed out after {timeout} seconds"

            output = ""
            if stdout:
                output += f"STDOUT:\n{stdout.decode('utf-8', errors='replace')}\n"
            if stderr:
                output += f"STDERR:\n{stderr.decode('utf-8', errors='replace')}\n"
            output += f"Exit Code: {process.returncode}"

            return output if output else "Command completed with no output"

        except asyncio.TimeoutError:
            return f"Error: Command timed out after {timeout} seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"

    async def _execute_view_file(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Read a file from the sandbox"""
        path = tool_input.get("path", "")
        start_line = tool_input.get("start_line")
        end_line = tool_input.get("end_line")

        if not path:
            return "Error: No path provided"

        try:
            content = await storage.read_from_sandbox(project_id, path, user_id)

            if content is None:
                return f"Error: File not found: {path}"

            # Apply line range if specified
            if start_line or end_line:
                lines = content.split("\n")
                start = (start_line - 1) if start_line else 0
                end = end_line if end_line else len(lines)
                lines = lines[start:end]
                # Add line numbers
                numbered = [f"{i + start + 1}: {line}" for i, line in enumerate(lines)]
                return "\n".join(numbered)

            # Add line numbers
            lines = content.split("\n")
            numbered = [f"{i + 1}: {line}" for i, line in enumerate(lines)]
            return "\n".join(numbered)

        except Exception as e:
            return f"Error reading file: {str(e)}"

    async def _execute_str_replace(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Replace string in a file"""
        path = tool_input.get("path", "")
        old_str = tool_input.get("old_str", "")
        new_str = tool_input.get("new_str", "")

        if not path or not old_str:
            return "Error: path and old_str are required"

        try:
            # Read current content
            content = await storage.read_from_sandbox(project_id, path, user_id)

            if content is None:
                return f"Error: File not found: {path}"

            # Check if old_str exists
            if old_str not in content:
                return f"Error: Could not find the exact string to replace in {path}. Make sure old_str matches exactly (including whitespace)."

            # Replace (single occurrence)
            new_content = content.replace(old_str, new_str, 1)

            # Write back
            await storage.write_to_sandbox(project_id, path, new_content, user_id)

            return f"Successfully replaced text in {path}"

        except Exception as e:
            return f"Error replacing text: {str(e)}"

    async def _execute_str_replace_all(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Replace ALL occurrences of a string in a file"""
        path = tool_input.get("path", "")
        old_str = tool_input.get("old_str", "")
        new_str = tool_input.get("new_str", "")

        if not path or not old_str:
            return "Error: path and old_str are required"

        try:
            # Read current content
            content = await storage.read_from_sandbox(project_id, path, user_id)

            if content is None:
                return f"Error: File not found: {path}"

            # Check if old_str exists
            if old_str not in content:
                return f"Error: Could not find the string '{old_str}' in {path}"

            # Count occurrences
            count = content.count(old_str)

            # Replace ALL occurrences
            new_content = content.replace(old_str, new_str)

            # Write back
            await storage.write_to_sandbox(project_id, path, new_content, user_id)

            return f"Successfully replaced {count} occurrence(s) of '{old_str}' with '{new_str}' in {path}"

        except Exception as e:
            return f"Error replacing text: {str(e)}"

    async def _execute_create_file(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Create a new file"""
        path = tool_input.get("path", "")
        content = tool_input.get("content", "")

        if not path:
            return "Error: path is required"

        try:
            await storage.write_to_sandbox(project_id, path, content, user_id)
            return f"Successfully created {path}"
        except Exception as e:
            return f"Error creating file: {str(e)}"

    async def _execute_insert_lines(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Insert lines at a position"""
        path = tool_input.get("path", "")
        line = tool_input.get("line", 0)
        content = tool_input.get("content", "")

        if not path:
            return "Error: path is required"

        try:
            # Read current content
            current = await storage.read_from_sandbox(project_id, path, user_id)

            if current is None:
                return f"Error: File not found: {path}"

            # Split and insert
            lines = current.split("\n")
            insert_lines = content.split("\n")
            lines[line:line] = insert_lines

            # Write back
            new_content = "\n".join(lines)
            await storage.write_to_sandbox(project_id, path, new_content, user_id)

            return f"Successfully inserted {len(insert_lines)} lines at line {line} in {path}"

        except Exception as e:
            return f"Error inserting lines: {str(e)}"

    async def _execute_glob(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Find files matching a pattern"""
        pattern = tool_input.get("pattern", "")

        if not pattern:
            return "Error: pattern is required"

        try:
            import glob as glob_module

            sandbox_path = storage.get_sandbox_path(project_id, user_id)
            full_pattern = os.path.join(sandbox_path, pattern)

            matches = glob_module.glob(full_pattern, recursive=True)

            # Convert to relative paths
            relative = [os.path.relpath(m, sandbox_path) for m in matches]

            if not relative:
                return f"No files found matching: {pattern}"

            return "Matching files:\n" + "\n".join(relative[:50])

        except Exception as e:
            return f"Error searching files: {str(e)}"

    async def _execute_grep(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Search for pattern in files"""
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", ".")
        include = tool_input.get("include", "")

        if not pattern:
            return "Error: pattern is required"

        try:
            sandbox_path = storage.get_sandbox_path(project_id, user_id)
            search_path = os.path.join(sandbox_path, path)

            # Build grep command
            cmd = f'grep -rn "{pattern}" "{search_path}"'
            if include:
                cmd = f'grep -rn --include="{include}" "{pattern}" "{search_path}"'

            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=30
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return f"Error: Grep command timed out after 30 seconds"

            output = stdout.decode('utf-8', errors='replace') or stderr.decode('utf-8', errors='replace')
            if not output:
                return f"No matches found for: {pattern}"

            # Limit output
            lines = output.split("\n")[:30]
            return "\n".join(lines)

        except asyncio.TimeoutError:
            return f"Error: Grep command timed out after 30 seconds"
        except Exception as e:
            return f"Error searching: {str(e)}"

    async def _execute_list_dir(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """List directory contents"""
        path = tool_input.get("path", ".")
        recursive = tool_input.get("recursive", False)

        try:
            sandbox_path = storage.get_sandbox_path(project_id, user_id)
            full_path = os.path.join(sandbox_path, path)

            if not os.path.exists(full_path):
                return f"Error: Directory not found: {path}"

            if recursive:
                items = []
                for root, dirs, files in os.walk(full_path):
                    rel_root = os.path.relpath(root, sandbox_path)
                    for f in files:
                        items.append(os.path.join(rel_root, f))
                return "\n".join(items[:100])
            else:
                items = os.listdir(full_path)
                result = []
                for item in sorted(items):
                    item_path = os.path.join(full_path, item)
                    prefix = "[DIR]" if os.path.isdir(item_path) else "[FILE]"
                    result.append(f"{prefix} {item}")
                return "\n".join(result)

        except Exception as e:
            return f"Error listing directory: {str(e)}"


# Singleton instance
sdk_fixer_agent = SDKFixerAgent()
