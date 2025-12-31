"""
Sonnet Fix Strategy (Tier 3)

Smart AI - $0.01 per fix - ~5-10s response time
Handles complex errors that need deep reasoning:
- Runtime errors
- Build errors
- Multi-file issues
- Unknown errors
"""

import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from app.core.logging_config import logger
from app.services.unified_fixer.classifier import ClassifiedError, ErrorCategory
from app.services.unified_fixer.strategies.deterministic import FixResult


# Sonnet-optimized system prompt (detailed for complex fixes)
SONNET_SYSTEM_PROMPT = """You are an expert code fixer. Analyze errors deeply and provide precise fixes.

Output JSON with this structure:
{
  "analysis": "Brief analysis of the root cause",
  "fixes": [
    {
      "fix_type": "file_edit" | "file_create" | "command",
      "file_path": "path/to/file",
      "search": "exact text to find (for file_edit)",
      "replace": "replacement text",
      "priority": 1
    }
  ],
  "explanation": "What was wrong and how this fixes it"
}

Rules:
- search/replace strings must be EXACT matches from the file
- Order fixes by priority (1 = highest)
- For multi-file fixes, include all files in the fixes array
- Keep changes minimal and focused
- Never add unnecessary comments, logs, or changes
- Consider side effects and imports
"""


class SonnetStrategy:
    """
    Tier 3: Sonnet AI fix strategy.

    Handles:
    - Runtime errors (complex logic bugs)
    - Build errors (configuration issues)
    - Multi-file issues
    - Unknown/complex errors

    Smart AI - $0.01 - ~5-10s
    """

    COST_PER_FIX = 0.01  # Approximate cost

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
        file_contents: Dict[str, str] = None,
        project_context: str = None
    ) -> FixResult:
        """
        Apply Sonnet AI fix for complex errors.

        Args:
            classified_error: Classified error from ErrorClassifier
            project_path: Path to project
            project_id: Project ID
            user_id: User ID
            file_contents: Dict of file_path -> content (optional)
            project_context: Additional project context (optional)

        Returns:
            FixResult with success status and details
        """
        start_time = time.time()

        try:
            # Gather file contents if not provided
            if not file_contents:
                file_contents = await self._gather_context(
                    project_path, project_id, user_id,
                    classified_error
                )

            if not file_contents:
                return FixResult(
                    success=False,
                    fix_type="sonnet",
                    files_modified=[],
                    error="Could not gather file context",
                    time_ms=int((time.time() - start_time) * 1000),
                    cost=0.0
                )

            # Generate fix with Sonnet
            fix_response = await self._call_sonnet(
                classified_error,
                file_contents,
                project_context
            )

            if not fix_response:
                return FixResult(
                    success=False,
                    fix_type="sonnet",
                    files_modified=[],
                    error="Sonnet did not return a valid fix",
                    time_ms=int((time.time() - start_time) * 1000),
                    cost=self.COST_PER_FIX
                )

            # Apply all fixes
            result = await self._apply_fixes(
                fix_response,
                project_path,
                project_id,
                user_id,
                file_contents
            )

            result.time_ms = int((time.time() - start_time) * 1000)
            result.cost = self.COST_PER_FIX

            return result

        except Exception as e:
            logger.error(f"[SonnetStrategy] Fix failed: {e}")
            return FixResult(
                success=False,
                fix_type="sonnet",
                files_modified=[],
                error=str(e),
                time_ms=int((time.time() - start_time) * 1000),
                cost=self.COST_PER_FIX
            )

    async def _gather_context(
        self,
        project_path: str,
        project_id: str,
        user_id: str,
        error: ClassifiedError
    ) -> Dict[str, str]:
        """Gather relevant file contents for context"""
        file_contents = {}

        # Primary error file
        if error.file_path:
            content = await self._read_file(
                project_path, project_id, user_id,
                error.file_path
            )
            if content:
                file_contents[error.file_path] = content

        # Try to find related files from error message
        related_files = self._extract_related_files(error.original_error)
        for file_path in related_files[:5]:  # Limit to 5 related files
            if file_path not in file_contents:
                content = await self._read_file(
                    project_path, project_id, user_id,
                    file_path
                )
                if content:
                    file_contents[file_path] = content

        # If no files found, try to get main entry files
        if not file_contents:
            common_entries = [
                "src/App.tsx", "src/App.jsx", "src/App.js",
                "src/index.tsx", "src/index.jsx", "src/index.js",
                "src/main.tsx", "src/main.jsx", "src/main.js",
                "app/main.py", "main.py", "app.py",
                "index.js", "index.ts"
            ]
            for entry in common_entries:
                content = await self._read_file(
                    project_path, project_id, user_id,
                    entry
                )
                if content:
                    file_contents[entry] = content
                    break

        return file_contents

    def _extract_related_files(self, error: str) -> List[str]:
        """Extract file paths mentioned in error"""
        import re

        files = []
        patterns = [
            r'(?:at |in |File )["\']?([^"\':\s]+\.[a-zA-Z]+)',
            r'([a-zA-Z0-9_\-./]+\.[tj]sx?):?\d*',
            r'([a-zA-Z0-9_\-./]+\.py):?\d*',
            r'([a-zA-Z0-9_\-./]+\.vue):?\d*',
            r'([a-zA-Z0-9_\-./]+\.svelte):?\d*',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, error)
            files.extend(matches)

        # Deduplicate and clean
        seen = set()
        clean_files = []
        for f in files:
            f = f.strip().lstrip('./')
            if f not in seen and not f.startswith('node_modules'):
                seen.add(f)
                clean_files.append(f)

        return clean_files

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
                import os
                full_path = os.path.join(project_path, file_path)
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        return f.read()
        except Exception as e:
            logger.debug(f"[SonnetStrategy] Could not read file {file_path}: {e}")
        return None

    async def _call_sonnet(
        self,
        error: ClassifiedError,
        file_contents: Dict[str, str],
        project_context: str = None
    ) -> Optional[Dict]:
        """Call Sonnet API for fix"""
        if not self.client:
            try:
                from anthropic import AsyncAnthropic
                import os
                self.client = AsyncAnthropic(
                    api_key=os.environ.get("ANTHROPIC_API_KEY")
                )
            except Exception as e:
                logger.error(f"[SonnetStrategy] Could not create Anthropic client: {e}")
                return None

        # Build comprehensive prompt
        user_prompt = self._build_prompt(error, file_contents, project_context)

        try:
            response = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                system=SONNET_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            content = response.content[0].text
            fix_data = self._extract_json(content)

            if fix_data:
                logger.info(f"[SonnetStrategy] Got fix with {len(fix_data.get('fixes', []))} changes")
                return fix_data
            else:
                logger.warning(f"[SonnetStrategy] Could not parse response")
                return None

        except Exception as e:
            logger.error(f"[SonnetStrategy] API call failed: {e}")
            return None

    def _build_prompt(
        self,
        error: ClassifiedError,
        file_contents: Dict[str, str],
        project_context: str = None
    ) -> str:
        """Build detailed prompt for Sonnet"""
        prompt_parts = [
            f"## Error\n```\n{error.original_error[:2000]}\n```\n"
        ]

        if error.file_path:
            prompt_parts.append(f"Primary file: {error.file_path}")
        if error.line_number:
            prompt_parts.append(f"Line: {error.line_number}")
        prompt_parts.append(f"Category: {error.category.value}")

        if project_context:
            prompt_parts.append(f"\n## Project Context\n{project_context}\n")

        prompt_parts.append("\n## Files\n")

        # Include file contents with truncation
        for file_path, content in file_contents.items():
            lines = content.split('\n')
            # Truncate very long files
            if len(lines) > 200:
                # Focus around error line if this is the primary file
                if file_path == error.file_path and error.line_number:
                    start = max(0, error.line_number - 50)
                    end = min(len(lines), error.line_number + 50)
                    content = '\n'.join(lines[start:end])
                    prompt_parts.append(
                        f"### {file_path} (lines {start+1}-{end})\n```\n{content}\n```\n"
                    )
                else:
                    content = '\n'.join(lines[:200])
                    prompt_parts.append(
                        f"### {file_path} (truncated)\n```\n{content}\n```\n"
                    )
            else:
                prompt_parts.append(
                    f"### {file_path}\n```\n{content}\n```\n"
                )

        prompt_parts.append(
            "\nAnalyze the error and provide fixes. Output JSON only."
        )

        return '\n'.join(prompt_parts)

    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from response text"""
        import re

        # Try direct parse
        try:
            return json.loads(text)
        except:
            pass

        # Look for ```json ... ``` block
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass

        # Look for { ... } with nested braces
        brace_count = 0
        start_idx = None
        for i, char in enumerate(text):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx is not None:
                    try:
                        return json.loads(text[start_idx:i+1])
                    except:
                        start_idx = None

        return None

    async def _apply_fixes(
        self,
        fix_response: Dict,
        project_path: str,
        project_id: str,
        user_id: str,
        original_contents: Dict[str, str]
    ) -> FixResult:
        """Apply all fixes from Sonnet response"""
        fixes = fix_response.get("fixes", [])

        if not fixes:
            # Check for single fix format
            if "fix_type" in fix_response:
                fixes = [fix_response]
            else:
                return FixResult(
                    success=False,
                    fix_type="sonnet",
                    files_modified=[],
                    error="No fixes provided"
                )

        # Sort by priority
        fixes.sort(key=lambda x: x.get("priority", 999))

        files_modified = []
        errors = []
        modified_contents = dict(original_contents)

        for fix in fixes:
            fix_type = fix.get("fix_type", "file_edit")
            file_path = fix.get("file_path", "")

            if fix_type == "file_edit":
                search = fix.get("search", "")
                replace = fix.get("replace", "")

                if not search or not file_path:
                    errors.append(f"Missing search or file_path for edit")
                    continue

                # Get current content (may have been modified by previous fix)
                content = modified_contents.get(file_path)
                if not content:
                    content = await self._read_file(
                        project_path, project_id, user_id, file_path
                    )

                if not content:
                    errors.append(f"Could not read {file_path}")
                    continue

                if search in content:
                    new_content = content.replace(search, replace, 1)
                    modified_contents[file_path] = new_content

                    success = await self._write_file(
                        project_path, project_id, user_id,
                        file_path, new_content
                    )

                    if success:
                        if file_path not in files_modified:
                            files_modified.append(file_path)
                        logger.info(f"[SonnetStrategy] Applied edit to {file_path}")
                    else:
                        errors.append(f"Failed to write {file_path}")
                else:
                    errors.append(f"Search string not found in {file_path}")

            elif fix_type == "file_create":
                content = fix.get("replace", fix.get("content", ""))

                if not file_path or not content:
                    errors.append("Missing file_path or content for create")
                    continue

                success = await self._write_file(
                    project_path, project_id, user_id,
                    file_path, content
                )

                if success:
                    files_modified.append(file_path)
                    logger.info(f"[SonnetStrategy] Created {file_path}")
                else:
                    errors.append(f"Failed to create {file_path}")

            elif fix_type == "command":
                command = fix.get("command", "")

                if command:
                    import asyncio

                    try:
                        process = await asyncio.create_subprocess_shell(
                            command,
                            cwd=project_path,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )

                        stdout, stderr = await asyncio.wait_for(
                            process.communicate(),
                            timeout=120
                        )

                        if process.returncode == 0:
                            logger.info(f"[SonnetStrategy] Ran command: {command}")
                        else:
                            errors.append(
                                f"Command failed: {stderr.decode()[:200]}"
                            )
                    except asyncio.TimeoutError:
                        errors.append(f"Command timed out: {command}")
                    except Exception as e:
                        errors.append(f"Command error: {e}")

        # Return result
        if files_modified:
            return FixResult(
                success=True,
                fix_type="multi_edit" if len(files_modified) > 1 else "file_edit",
                files_modified=files_modified,
                error="; ".join(errors) if errors else None
            )
        else:
            return FixResult(
                success=False,
                fix_type="sonnet",
                files_modified=[],
                error="; ".join(errors) if errors else "No changes applied"
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
                import os
                full_path = os.path.join(project_path, file_path)
                os.makedirs(os.path.dirname(full_path) if os.path.dirname(full_path) else '.', exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
        except Exception as e:
            logger.error(f"[SonnetStrategy] Failed to write file: {e}")
            return False

    def can_handle(self, error: ClassifiedError) -> bool:
        """Check if this strategy can handle the error"""
        return error.category in [
            ErrorCategory.RUNTIME,
            ErrorCategory.BUILD,
            ErrorCategory.UNKNOWN
        ]
