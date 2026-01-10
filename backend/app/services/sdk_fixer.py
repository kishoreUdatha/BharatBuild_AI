"""
Claude SDK Agent-based Fixer

A simple, robust fixer that uses Claude SDK with tools.
Claude decides which files to read/write - no complex logic needed.

Usage:
    fixer = SDKFixer(sandbox_reader, sandbox_writer)
    result = await fixer.fix(project_path, build_errors)
"""

import logging
import asyncio
from typing import Optional, Callable, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass
from anthropic import AsyncAnthropic

logger = logging.getLogger("bharatbuild")


@dataclass
class SDKFixResult:
    """Result from SDK fixer"""
    success: bool
    files_modified: List[str]
    files_created: List[str]
    message: str
    tool_calls: int
    tokens_used: int


class SDKFixer:
    """
    Claude SDK Agent-based fixer.

    Much simpler than BoltFixer:
    - Claude reads files it needs via tools
    - Claude writes fixes via tools
    - No complex prompt engineering
    - No truncation issues
    """

    SYSTEM_PROMPT = """You are an expert code fixer. Fix build/compilation errors.

RULES:
1. First, use list_files to see project structure
2. Use read_file to read files that have errors or need fixing
3. Use write_file to write the fixed content

JAVA RULES (CRITICAL):
- NO LOMBOK: Remove @Data, @Getter, @Setter, @Builder, @NoArgsConstructor, @AllArgsConstructor
- Remove: import lombok.*;
- Add explicit getter for EVERY field: public Type getField() { return field; }
- Add explicit setter for EVERY field: public void setField(Type val) { this.field = val; }
- Add no-arg constructor and all-args constructor
- Use constructor injection for services (not @RequiredArgsConstructor)

FIX ROOT CAUSE:
- If error says "cannot find symbol: method getX() in class Order"
  → Read Order.java and add the missing getter
- If error says "location: class Product"
  → Fix Product.java, not the file that uses it

OUTPUT:
- Fix ALL files that need fixing
- Write complete, working files
- No placeholders or TODOs
"""

    TOOLS = [
        {
            "name": "list_files",
            "description": "List files in a directory. Use pattern like '**/*.java' or 'src/**/*'",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern like '**/*.java' or 'backend/src/**/*.java'"
                    }
                },
                "required": ["pattern"]
            }
        },
        {
            "name": "read_file",
            "description": "Read a file's content",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to project root"
                    }
                },
                "required": ["path"]
            }
        },
        {
            "name": "write_file",
            "description": "Write content to a file (creates or overwrites)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to project root"
                    },
                    "content": {
                        "type": "string",
                        "description": "Complete file content to write"
                    }
                },
                "required": ["path", "content"]
            }
        }
    ]

    def __init__(
        self,
        sandbox_reader: Optional[Callable[[str], Optional[str]]] = None,
        sandbox_writer: Optional[Callable[[str, str], bool]] = None,
        sandbox_lister: Optional[Callable[[str, str], List[str]]] = None
    ):
        """
        Initialize SDK Fixer.

        Args:
            sandbox_reader: Callback to read files from sandbox
            sandbox_writer: Callback to write files to sandbox
            sandbox_lister: Callback to list files in sandbox
        """
        self._client = AsyncAnthropic()
        self._sandbox_reader = sandbox_reader
        self._sandbox_writer = sandbox_writer
        self._sandbox_lister = sandbox_lister
        self._project_path: Optional[Path] = None
        self._files_modified: List[str] = []
        self._files_created: List[str] = []

    async def fix(
        self,
        project_path: Path,
        build_errors: str,
        max_iterations: int = 10
    ) -> SDKFixResult:
        """
        Fix build errors using Claude SDK agent.

        Args:
            project_path: Root path of the project
            build_errors: Build/compilation error output
            max_iterations: Max tool use iterations

        Returns:
            SDKFixResult with success status and modified files
        """
        self._project_path = project_path
        self._files_modified = []
        self._files_created = []
        tool_calls = 0
        total_tokens = 0

        # Initial message with build errors
        messages = [{
            "role": "user",
            "content": f"""Fix these build errors:

```
{build_errors[:8000]}
```

Project path: {project_path}

Steps:
1. List Java files to understand structure
2. Read files that have errors (check "location:" in errors)
3. Fix each file - remove Lombok, add explicit getters/setters
4. Write the fixed files
"""
        }]

        try:
            for iteration in range(max_iterations):
                logger.info(f"[SDKFixer] Iteration {iteration + 1}/{max_iterations}")

                # Call Claude
                response = await self._client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=16384,
                    system=self.SYSTEM_PROMPT,
                    tools=self.TOOLS,
                    messages=messages
                )

                total_tokens += response.usage.input_tokens + response.usage.output_tokens

                # Check if done
                if response.stop_reason == "end_turn":
                    logger.info(f"[SDKFixer] Completed after {iteration + 1} iterations")
                    break

                # Process tool uses
                if response.stop_reason == "tool_use":
                    # Add assistant message
                    messages.append({
                        "role": "assistant",
                        "content": response.content
                    })

                    # Execute tools and collect results
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            tool_calls += 1
                            result = await self._execute_tool(
                                block.name,
                                block.input,
                                block.id
                            )
                            tool_results.append(result)

                    # Add tool results
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })
                else:
                    # Unexpected stop reason
                    logger.warning(f"[SDKFixer] Unexpected stop: {response.stop_reason}")
                    break

            return SDKFixResult(
                success=len(self._files_modified) > 0 or len(self._files_created) > 0,
                files_modified=self._files_modified,
                files_created=self._files_created,
                message=f"Fixed {len(self._files_modified)} files, created {len(self._files_created)} files",
                tool_calls=tool_calls,
                tokens_used=total_tokens
            )

        except Exception as e:
            logger.error(f"[SDKFixer] Error: {e}")
            return SDKFixResult(
                success=False,
                files_modified=[],
                files_created=[],
                message=f"Error: {str(e)}",
                tool_calls=tool_calls,
                tokens_used=total_tokens
            )

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_use_id: str
    ) -> Dict[str, Any]:
        """Execute a tool and return the result."""
        try:
            if tool_name == "list_files":
                result = await self._list_files(tool_input.get("pattern", "**/*"))
            elif tool_name == "read_file":
                result = await self._read_file(tool_input.get("path", ""))
            elif tool_name == "write_file":
                result = await self._write_file(
                    tool_input.get("path", ""),
                    tool_input.get("content", "")
                )
            else:
                result = f"Unknown tool: {tool_name}"

            logger.info(f"[SDKFixer] Tool {tool_name}: {tool_input.get('path', tool_input.get('pattern', ''))[:50]}")

            return {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": result
            }

        except Exception as e:
            logger.error(f"[SDKFixer] Tool error {tool_name}: {e}")
            return {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": f"Error: {str(e)}",
                "is_error": True
            }

    async def _list_files(self, pattern: str) -> str:
        """List files matching pattern."""
        import glob

        if self._sandbox_lister and self._project_path:
            # Use sandbox lister for remote mode
            files = self._sandbox_lister(str(self._project_path), pattern)
        else:
            # Local mode
            full_pattern = str(self._project_path / pattern)
            files = glob.glob(full_pattern, recursive=True)
            # Make paths relative
            files = [str(Path(f).relative_to(self._project_path)) for f in files]

        # Limit to 100 files
        if len(files) > 100:
            files = files[:100]
            return f"Found {len(files)}+ files (showing first 100):\n" + "\n".join(files)

        return f"Found {len(files)} files:\n" + "\n".join(files)

    async def _read_file(self, path: str) -> str:
        """Read a file's content."""
        # Normalize path
        path = path.replace("\\", "/")
        if path.startswith("/"):
            path = path[1:]

        full_path = self._project_path / path

        if self._sandbox_reader:
            # Use sandbox reader for remote mode
            content = self._sandbox_reader(str(full_path).replace("\\", "/"))
            if content:
                return content
            return f"File not found: {path}"
        else:
            # Local mode
            if full_path.exists():
                return full_path.read_text(encoding="utf-8")
            return f"File not found: {path}"

    async def _write_file(self, path: str, content: str) -> str:
        """Write content to a file."""
        # Normalize path
        path = path.replace("\\", "/")
        if path.startswith("/"):
            path = path[1:]

        full_path = self._project_path / path

        # Check if file exists (for tracking modified vs created)
        file_exists = False
        if self._sandbox_reader:
            file_exists = self._sandbox_reader(str(full_path).replace("\\", "/")) is not None
        else:
            file_exists = full_path.exists()

        # Write file
        if self._sandbox_writer:
            # Use sandbox writer for remote mode
            success = self._sandbox_writer(str(full_path).replace("\\", "/"), content)
            if not success:
                return f"Failed to write: {path}"
        else:
            # Local mode
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

        # Track modified/created files
        if file_exists:
            if path not in self._files_modified:
                self._files_modified.append(path)
            return f"Updated: {path} ({len(content)} chars)"
        else:
            if path not in self._files_created:
                self._files_created.append(path)
            return f"Created: {path} ({len(content)} chars)"


# Convenience function for integration
async def sdk_fix_errors(
    project_path: Path,
    build_errors: str,
    sandbox_reader: Optional[Callable] = None,
    sandbox_writer: Optional[Callable] = None,
    sandbox_lister: Optional[Callable] = None
) -> SDKFixResult:
    """
    Convenience function to fix errors using SDK agent.

    Usage:
        result = await sdk_fix_errors(
            project_path=Path("/path/to/project"),
            build_errors="[ERROR] cannot find symbol...",
            sandbox_reader=my_reader,
            sandbox_writer=my_writer
        )
    """
    fixer = SDKFixer(
        sandbox_reader=sandbox_reader,
        sandbox_writer=sandbox_writer,
        sandbox_lister=sandbox_lister
    )
    return await fixer.fix(project_path, build_errors)
