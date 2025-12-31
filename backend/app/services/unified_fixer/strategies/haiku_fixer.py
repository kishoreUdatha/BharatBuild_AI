"""
Haiku Fix Strategy (Tier 2)

Fast AI - $0.001 per fix - ~2s response time
Handles simple errors that need AI reasoning:
- Import errors
- Syntax errors
- Type errors
"""

import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from app.core.logging_config import logger
from app.services.unified_fixer.classifier import ClassifiedError, ErrorCategory
from app.services.unified_fixer.strategies.deterministic import FixResult


# Haiku-optimized prompts (concise for speed)
HAIKU_SYSTEM_PROMPT = """You are a code fixer. Output JSON only.

Output format:
{
  "fix_type": "file_edit" | "file_create" | "command",
  "file_path": "path/to/file",
  "search": "exact text to find",
  "replace": "replacement text",
  "explanation": "1 sentence"
}

Rules:
- search/replace must be EXACT strings from the file
- Keep changes minimal
- Never add comments or logs
"""


class HaikuStrategy:
    """
    Tier 2: Haiku AI fix strategy.

    Handles:
    - Import errors (missing imports, wrong paths)
    - Syntax errors (typos, missing brackets)
    - Type errors (simple type mismatches)

    Fast AI - $0.001 - ~2s
    """

    COST_PER_FIX = 0.001  # Approximate cost

    def __init__(self, file_manager=None, anthropic_client=None):
        """
        Args:
            file_manager: UnifiedFileManager instance
            anthropic_client: Anthropic client for API calls
        """
        self.file_manager = file_manager
        self.client = anthropic_client

    async def fix(
        self,
        classified_error: ClassifiedError,
        project_path: str,
        project_id: str,
        user_id: str,
        file_content: str = None
    ) -> FixResult:
        """
        Apply Haiku AI fix for simple errors.

        Args:
            classified_error: Classified error from ErrorClassifier
            project_path: Path to project
            project_id: Project ID
            user_id: User ID
            file_content: Content of the file with error (optional)

        Returns:
            FixResult with success status and details
        """
        start_time = time.time()

        try:
            # Read file if not provided
            if not file_content and classified_error.file_path:
                file_content = await self._read_file(
                    project_path, project_id, user_id,
                    classified_error.file_path
                )

            if not file_content:
                return FixResult(
                    success=False,
                    fix_type="haiku",
                    files_modified=[],
                    error="Could not read file content",
                    time_ms=int((time.time() - start_time) * 1000),
                    cost=0.0
                )

            # Generate fix with Haiku
            fix_response = await self._call_haiku(
                classified_error,
                file_content
            )

            if not fix_response:
                return FixResult(
                    success=False,
                    fix_type="haiku",
                    files_modified=[],
                    error="Haiku did not return a valid fix",
                    time_ms=int((time.time() - start_time) * 1000),
                    cost=self.COST_PER_FIX
                )

            # Apply the fix
            result = await self._apply_fix(
                fix_response,
                project_path,
                project_id,
                user_id,
                file_content,
                classified_error.file_path
            )

            result.time_ms = int((time.time() - start_time) * 1000)
            result.cost = self.COST_PER_FIX

            return result

        except Exception as e:
            logger.error(f"[HaikuStrategy] Fix failed: {e}")
            return FixResult(
                success=False,
                fix_type="haiku",
                files_modified=[],
                error=str(e),
                time_ms=int((time.time() - start_time) * 1000),
                cost=self.COST_PER_FIX
            )

    async def _read_file(
        self,
        project_path: str,
        project_id: str,
        user_id: str,
        file_path: str
    ) -> Optional[str]:
        """Read file content"""
        try:
            if self.file_manager:
                content = await self.file_manager.read_file(
                    project_id, user_id, file_path
                )
                return content
            else:
                # Fallback to direct read
                import os
                full_path = os.path.join(project_path, file_path)
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        return f.read()
        except Exception as e:
            logger.warning(f"[HaikuStrategy] Could not read file: {e}")
        return None

    async def _call_haiku(
        self,
        error: ClassifiedError,
        file_content: str
    ) -> Optional[Dict]:
        """Call Haiku API for fix"""
        if not self.client:
            # Try to get client
            try:
                from anthropic import AsyncAnthropic
                import os
                self.client = AsyncAnthropic(
                    api_key=os.environ.get("ANTHROPIC_API_KEY")
                )
            except Exception as e:
                logger.error(f"[HaikuStrategy] Could not create Anthropic client: {e}")
                return None

        # Prepare prompt
        user_prompt = self._build_prompt(error, file_content)

        try:
            response = await self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                system=HAIKU_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Parse JSON response
            content = response.content[0].text

            # Extract JSON from response
            fix_data = self._extract_json(content)

            if fix_data:
                logger.info(f"[HaikuStrategy] Got fix: {fix_data.get('fix_type')}")
                return fix_data
            else:
                logger.warning(f"[HaikuStrategy] Could not parse response: {content[:200]}")
                return None

        except Exception as e:
            logger.error(f"[HaikuStrategy] API call failed: {e}")
            return None

    def _build_prompt(self, error: ClassifiedError, file_content: str) -> str:
        """Build concise prompt for Haiku"""
        # Truncate file content if too long
        max_lines = 100
        lines = file_content.split('\n')

        if len(lines) > max_lines:
            # Focus around error line if known
            if error.line_number:
                start = max(0, error.line_number - 30)
                end = min(len(lines), error.line_number + 30)
                lines = lines[start:end]
                file_content = '\n'.join(lines)
            else:
                file_content = '\n'.join(lines[:max_lines])

        prompt = f"""Error: {error.original_error[:500]}

File: {error.file_path or 'unknown'}
{f'Line: {error.line_number}' if error.line_number else ''}

```
{file_content}
```

Fix the error. Output JSON only."""

        return prompt

    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from response text"""
        # Try direct parse
        try:
            return json.loads(text)
        except:
            pass

        # Try to find JSON block
        import re

        # Look for ```json ... ``` block
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass

        # Look for { ... } anywhere
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass

        return None

    async def _apply_fix(
        self,
        fix_data: Dict,
        project_path: str,
        project_id: str,
        user_id: str,
        original_content: str,
        file_path: str
    ) -> FixResult:
        """Apply the fix from Haiku"""
        fix_type = fix_data.get("fix_type", "file_edit")
        target_path = fix_data.get("file_path", file_path)

        if fix_type == "file_edit":
            search = fix_data.get("search", "")
            replace = fix_data.get("replace", "")

            if not search:
                return FixResult(
                    success=False,
                    fix_type="haiku",
                    files_modified=[],
                    error="No search string provided"
                )

            # Apply search/replace
            if search in original_content:
                new_content = original_content.replace(search, replace, 1)

                # Write file
                success = await self._write_file(
                    project_path, project_id, user_id,
                    target_path, new_content
                )

                if success:
                    return FixResult(
                        success=True,
                        fix_type="file_edit",
                        files_modified=[target_path]
                    )
                else:
                    return FixResult(
                        success=False,
                        fix_type="file_edit",
                        files_modified=[],
                        error="Failed to write file"
                    )
            else:
                return FixResult(
                    success=False,
                    fix_type="file_edit",
                    files_modified=[],
                    error=f"Search string not found in file"
                )

        elif fix_type == "file_create":
            content = fix_data.get("replace", fix_data.get("content", ""))

            success = await self._write_file(
                project_path, project_id, user_id,
                target_path, content
            )

            if success:
                return FixResult(
                    success=True,
                    fix_type="file_create",
                    files_modified=[target_path]
                )
            else:
                return FixResult(
                    success=False,
                    fix_type="file_create",
                    files_modified=[],
                    error="Failed to create file"
                )

        elif fix_type == "command":
            command = fix_data.get("command", "")

            if command:
                import asyncio

                process = await asyncio.create_subprocess_shell(
                    command,
                    cwd=project_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=60
                )

                if process.returncode == 0:
                    return FixResult(
                        success=True,
                        fix_type="command",
                        files_modified=[],
                        command_run=command
                    )
                else:
                    return FixResult(
                        success=False,
                        fix_type="command",
                        files_modified=[],
                        command_run=command,
                        error=stderr.decode()[:500] if stderr else "Command failed"
                    )
            else:
                return FixResult(
                    success=False,
                    fix_type="command",
                    files_modified=[],
                    error="No command provided"
                )

        return FixResult(
            success=False,
            fix_type="haiku",
            files_modified=[],
            error=f"Unknown fix type: {fix_type}"
        )

    async def _write_file(
        self,
        project_path: str,
        project_id: str,
        user_id: str,
        file_path: str,
        content: str
    ) -> bool:
        """Write file content"""
        try:
            if self.file_manager:
                return await self.file_manager.write_file(
                    project_id, user_id, file_path, content
                )
            else:
                # Fallback to direct write
                import os
                full_path = os.path.join(project_path, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
        except Exception as e:
            logger.error(f"[HaikuStrategy] Failed to write file: {e}")
            return False

    def can_handle(self, error: ClassifiedError) -> bool:
        """Check if this strategy can handle the error"""
        return error.category in [
            ErrorCategory.IMPORT,
            ErrorCategory.SYNTAX,
            ErrorCategory.TYPE
        ]
