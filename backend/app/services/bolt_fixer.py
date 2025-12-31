"""
Bolt Fixer - Unified fixer using Bolt.new architecture

This replaces SimpleFixer with the proper Bolt.new pattern:
1. Error Classifier (rule-based, NO AI)
2. Decision Gate (should Claude be called?)
3. Retry Limiter (max attempts)
4. Claude API (strict prompt, diff only)
5. Patch Validator (validate before apply)
6. Diff Parser (pure Python, no git)
7. Patch Applier (atomic with rollback)

Claude is a tool, not a controller.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

from app.core.logging_config import logger
from app.services.error_classifier import ErrorClassifier, ErrorType, ClassifiedError
from app.services.patch_validator import PatchValidator
from app.services.retry_limiter import retry_limiter
from app.services.diff_parser import DiffParser
from app.services.patch_applier import PatchApplier
from app.services.storage_service import storage_service


@dataclass
class BoltFixResult:
    """Result from BoltFixer - compatible with SimpleFixResult"""
    success: bool
    files_modified: List[str]
    message: str
    patches_applied: int = 0
    error_type: Optional[str] = None
    fix_strategy: Optional[str] = None


class BoltFixer:
    """
    Bolt.new style fixer with rule-based classification and atomic patches.

    Flow:
    1. Classify error (rule-based)
    2. Check if Claude-fixable
    3. Check retry limits
    4. Call Claude (strict prompt)
    5. Validate patch
    6. Apply atomically
    """

    # Strict system prompt - Claude returns ONLY diffs
    SYSTEM_PROMPT = """You are an automated code-fix agent.

STRICT RULES:
- Return ONLY a unified diff or file block
- Do NOT explain
- Do NOT invent files
- Do NOT modify unrelated code

OUTPUT FORMAT:

For patching existing files:
<patch>
--- path/to/file
+++ path/to/file
@@ -line,count +line,count @@
- old line
+ new line
</patch>

For creating missing files:
<newfile path="path/to/file">
file content
</newfile>

For full file replacement (syntax errors):
<file path="path/to/file">
complete file content
</file>

If no fix possible: <patch></patch>

No text outside blocks. No markdown. No commentary."""

    SYNTAX_FIX_PROMPT = """You are fixing a SYNTAX ERROR.

Return the COMPLETE fixed file using:
<file path="filepath">complete content</file>

Rules:
- Return ENTIRE file, not a patch
- Fix all bracket mismatches
- Remove duplicate code blocks
- Maintain proper structure

No explanations. Only the <file> block."""

    def __init__(self):
        self._claude_client = None

    async def fix_from_backend(
        self,
        project_id: str,
        project_path: Path,
        payload: Dict[str, Any]
    ) -> BoltFixResult:
        """
        BOLT.NEW STYLE: Fix errors from backend execution.

        Same interface as SimpleFixer.fix_from_backend for drop-in replacement.

        Args:
            project_id: Project ID
            project_path: Path to project files
            payload: Error payload from ExecutionContext

        Returns:
            BoltFixResult with success status and modified files
        """
        # Extract payload
        stderr = payload.get("stderr", "")
        stdout = payload.get("stdout", "")
        exit_code = payload.get("exit_code", 1)
        error_file = payload.get("error_file")
        error_line = payload.get("error_line")
        primary_error_type = payload.get("primary_error_type")

        # Combine stdout and stderr for classification
        # Vite/esbuild errors often go to stdout, not stderr
        combined_output = f"{stderr}\n{stdout}".strip() if stderr or stdout else ""

        logger.info(
            f"[BoltFixer:{project_id}] fix_from_backend: "
            f"exit_code={exit_code}, stderr_len={len(stderr)}, stdout_len={len(stdout)}"
        )

        # =================================================================
        # STEP 1: CLASSIFY ERROR (Rule-based, NO AI)
        # =================================================================
        classified = ErrorClassifier.classify(
            error_message=combined_output[:2000],
            stderr=combined_output,
            exit_code=exit_code
        )

        logger.info(
            f"[BoltFixer:{project_id}] Classified: {classified.error_type.value}, "
            f"fixable={classified.is_claude_fixable}, confidence={classified.confidence}"
        )

        # =================================================================
        # STEP 2: DECISION GATE - Should Claude be called?
        # =================================================================
        should_call, reason = ErrorClassifier.should_call_claude(classified)
        if not should_call:
            logger.info(f"[BoltFixer:{project_id}] NOT calling Claude: {reason}")
            return BoltFixResult(
                success=False,
                files_modified=[],
                message=reason,
                error_type=classified.error_type.value,
                fix_strategy="skipped"
            )

        # =================================================================
        # STEP 3: CHECK RETRY LIMITS
        # =================================================================
        error_hash = retry_limiter.hash_error(combined_output[:500])
        can_retry, retry_reason = retry_limiter.can_retry(project_id, error_hash)
        if not can_retry:
            logger.warning(f"[BoltFixer:{project_id}] Retry limit: {retry_reason}")
            return BoltFixResult(
                success=False,
                files_modified=[],
                message=retry_reason,
                error_type=classified.error_type.value,
                fix_strategy="retry_blocked"
            )

        # =================================================================
        # STEP 4: GATHER CONTEXT (file content for Claude)
        # =================================================================
        file_content = ""
        target_file = classified.file_path or error_file

        if target_file and project_path:
            file_path = project_path / target_file
            if not file_path.exists():
                file_path = project_path / "frontend" / target_file
            if file_path.exists():
                try:
                    file_content = file_path.read_text(encoding='utf-8')
                    logger.info(f"[BoltFixer:{project_id}] Read file: {target_file} ({len(file_content)} chars)")
                except Exception as e:
                    logger.warning(f"[BoltFixer:{project_id}] Could not read {target_file}: {e}")

        # =================================================================
        # STEP 5: CALL CLAUDE (strict prompt)
        # =================================================================
        # Choose prompt based on error type
        if classified.error_type == ErrorType.SYNTAX_ERROR:
            system_prompt = self.SYNTAX_FIX_PROMPT
            max_tokens = 16384
        else:
            system_prompt = self.SYSTEM_PROMPT
            max_tokens = 4096

        # Build user prompt
        error_type_template = ErrorClassifier.get_claude_prompt_template(classified.error_type)
        user_prompt = f"""{error_type_template}

ERROR: {combined_output[:2000]}
FILE: {target_file or 'unknown'}
LINE: {classified.line_number or error_line or 0}

FILE CONTENT:
```
{file_content[:10000] if file_content else 'No file content available'}
```

BUILD LOG:
{combined_output[-2000:]}
"""

        logger.info(f"[BoltFixer:{project_id}] Calling Claude for {classified.error_type.value}")

        try:
            response = await self._call_claude(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens
            )
        except Exception as e:
            logger.error(f"[BoltFixer:{project_id}] Claude call failed: {e}")
            retry_limiter.record_attempt(project_id, error_hash, tokens_used=0, fixed=False)
            return BoltFixResult(
                success=False,
                files_modified=[],
                message=f"Claude API error: {str(e)}",
                error_type=classified.error_type.value,
                fix_strategy="claude_error"
            )

        # Estimate tokens
        tokens_used = len(user_prompt.split()) + len(response.split())

        # =================================================================
        # STEP 6: PARSE RESPONSE
        # =================================================================
        patches = self._parse_patch_blocks(response)
        full_files = self._parse_file_blocks(response)
        new_files = self._parse_newfile_blocks(response)

        logger.info(
            f"[BoltFixer:{project_id}] Claude returned: "
            f"{len(patches)} patches, {len(full_files)} files, {len(new_files)} new files"
        )

        if not patches and not full_files and not new_files:
            logger.warning(f"[BoltFixer:{project_id}] No fixes in Claude response")
            retry_limiter.record_attempt(project_id, error_hash, tokens_used=tokens_used, fixed=False)
            return BoltFixResult(
                success=False,
                files_modified=[],
                message="Claude returned no fixes",
                error_type=classified.error_type.value,
                fix_strategy="no_fix"
            )

        # =================================================================
        # STEP 7: VALIDATE AND APPLY
        # =================================================================
        files_modified = []
        applier = PatchApplier(project_path)

        # Apply patches using DiffParser
        for patch in patches:
            patch_content = patch.get("patch", "")
            file_path = patch.get("path", "")

            # Validate
            result = PatchValidator.validate_diff(patch_content, project_path)
            if not result.is_valid:
                logger.warning(f"[BoltFixer:{project_id}] Invalid patch: {result.errors}")
                continue

            # Find target file
            parsed = DiffParser.parse(patch_content)
            actual_file = parsed.new_file or parsed.old_file or file_path
            target_path = project_path / actual_file
            if not target_path.exists():
                target_path = project_path / "frontend" / actual_file

            if target_path.exists():
                try:
                    original = target_path.read_text(encoding='utf-8')
                    apply_result = DiffParser.apply(original, parsed)

                    if apply_result.success:
                        # Write atomically
                        temp_path = target_path.with_suffix(target_path.suffix + '.tmp')
                        temp_path.write_text(apply_result.new_content, encoding='utf-8')
                        temp_path.replace(target_path)
                        files_modified.append(actual_file)
                        logger.info(f"[BoltFixer:{project_id}] Applied patch to {actual_file}")
                except Exception as e:
                    logger.error(f"[BoltFixer:{project_id}] Error applying patch: {e}")

        # Apply full file replacements
        for file_info in full_files:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")

            # Validate
            result = PatchValidator.validate_full_file(file_path, content, project_path)
            if not result.is_valid:
                logger.warning(f"[BoltFixer:{project_id}] Invalid file: {result.errors}")
                continue

            target_path = project_path / file_path
            if not target_path.exists():
                target_path = project_path / "frontend" / file_path

            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path = target_path.with_suffix(target_path.suffix + '.tmp')
                temp_path.write_text(content, encoding='utf-8')
                temp_path.replace(target_path)
                files_modified.append(file_path)
                logger.info(f"[BoltFixer:{project_id}] Wrote file {file_path}")
            except Exception as e:
                logger.error(f"[BoltFixer:{project_id}] Error writing file: {e}")

        # Create new files
        for file_info in new_files:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")

            # Validate
            result = PatchValidator.validate_new_file(file_path, content, project_path)
            if not result.is_valid:
                logger.warning(f"[BoltFixer:{project_id}] Invalid new file: {result.errors}")
                continue

            target_path = project_path / file_path
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding='utf-8')
                files_modified.append(file_path)
                logger.info(f"[BoltFixer:{project_id}] Created {file_path}")
            except Exception as e:
                logger.error(f"[BoltFixer:{project_id}] Error creating file: {e}")

        # =================================================================
        # STEP 8: SYNC TO S3 (persist fixes)
        # =================================================================
        if files_modified:
            await self._sync_to_s3(project_id, project_path, files_modified)

        # =================================================================
        # STEP 9: RECORD ATTEMPT AND RETURN
        # =================================================================
        success = len(files_modified) > 0
        retry_limiter.record_attempt(project_id, error_hash, tokens_used=tokens_used, fixed=success)

        return BoltFixResult(
            success=success,
            files_modified=files_modified,
            message=f"Fixed {len(files_modified)} file(s)" if success else "No files fixed",
            patches_applied=len(files_modified),
            error_type=classified.error_type.value,
            fix_strategy="bolt_fixer"
        )

    async def _call_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096
    ) -> str:
        """Call Claude API with strict prompts."""
        import anthropic

        if self._claude_client is None:
            from app.core.config import settings
            self._claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = self._claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            temperature=0.1,  # Very low for precise fixes
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        return response.content[0].text if response.content else ""

    def _parse_patch_blocks(self, response: str) -> List[Dict[str, str]]:
        """Parse <patch>...</patch> blocks."""
        import re
        patches = []
        pattern = r'<patch>(.*?)</patch>'

        for match in re.findall(pattern, response, re.DOTALL):
            content = match.strip()
            if not content:
                continue

            # Extract file path
            path_match = re.search(r'^(?:---|\+\+\+)\s+(?:[ab]/)?([^\s]+)', content, re.MULTILINE)
            file_path = path_match.group(1) if path_match else "unknown"

            patches.append({"path": file_path, "patch": content})

        return patches

    def _parse_file_blocks(self, response: str) -> List[Dict[str, str]]:
        """Parse <file path="...">...</file> blocks."""
        import re
        files = []
        pattern = r'<file\s+path="([^"]+)">(.*?)</file>'

        for path, content in re.findall(pattern, response, re.DOTALL):
            files.append({"path": path.strip(), "content": content.strip()})

        return files

    def _parse_newfile_blocks(self, response: str) -> List[Dict[str, str]]:
        """Parse <newfile path="...">...</newfile> blocks."""
        import re
        files = []
        pattern = r'<newfile\s+path="([^"]+)">(.*?)</newfile>'

        for path, content in re.findall(pattern, response, re.DOTALL):
            # Clean markdown if present
            content = content.strip()
            if content.startswith('```'):
                lines = content.split('\n')[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                content = '\n'.join(lines)

            files.append({"path": path.strip(), "content": content.strip()})

        return files

    async def _sync_to_s3(
        self,
        project_id: str,
        project_path: Path,
        files_modified: List[str]
    ) -> None:
        """
        Sync fixed files to S3 for persistence.

        This ensures fixes survive container restarts.
        Database stores metadata only, S3 stores content.
        """
        for file_path in files_modified:
            try:
                # Read the fixed content from sandbox
                full_path = project_path / file_path
                if not full_path.exists():
                    full_path = project_path / "frontend" / file_path

                if not full_path.exists():
                    logger.warning(f"[BoltFixer:{project_id}] File not found for S3 sync: {file_path}")
                    continue

                content = full_path.read_text(encoding='utf-8')

                # Upload to S3
                await storage_service.upload_file(
                    project_id=project_id,
                    file_path=file_path,
                    content=content.encode('utf-8'),
                    content_type="text/plain"
                )

                logger.info(f"[BoltFixer:{project_id}] ✓ Synced to S3: {file_path}")

            except Exception as e:
                logger.error(f"[BoltFixer:{project_id}] ✗ S3 sync failed for {file_path}: {e}")


# Singleton instance
bolt_fixer = BoltFixer()
