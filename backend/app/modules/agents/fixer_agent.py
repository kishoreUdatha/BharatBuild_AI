"""
AGENT 3 - Fixer Agent (Auto Debugger)
Fixes errors during generation, build, runtime, or compilation

Architecture follows Bolt.new pattern:
1. Error Classifier (rule-based) - Classifies errors BEFORE Claude
2. Decision Gate - Determines if Claude should be called
3. Strict Prompt - Claude returns diff only, no explanations
4. Patch Validator - Validates output before applying
5. Retry Limiter - Caps retries to prevent runaway costs

Claude is never called blindly. Claude is a tool, not a controller.
"""

from typing import Dict, List, Optional, Any, Tuple
import json
import re
from datetime import datetime
from pathlib import Path

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext
from app.services.error_classifier import ErrorClassifier, ErrorType, ClassifiedError
from app.services.patch_validator import PatchValidator, ValidationResult
from app.services.retry_limiter import RetryLimiter, retry_limiter


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

    # STRICT system prompt - Claude only returns diffs, no explanations
    SYSTEM_PROMPT = """You are an automated code-fix agent.

STRICT RULES:
- You may ONLY return a unified diff or file block.
- Do NOT explain.
- Do NOT invent files.
- Do NOT modify unrelated code.
- Do NOT output anything outside <patch> or <newfile> or <file> blocks.

JAVA CONSISTENCY (MULTI-FILE):
When fixing Java "cannot find symbol" errors:
1. Check ALL related files provided (Entity, DTO, Service, Controller)
2. Ensure field/method names match EXACTLY across related files
3. If DTO missing getter/setter - add it to the DTO
4. If Service interface missing method - add to BOTH interface AND implementation
5. Output MULTIPLE <file> blocks if multiple files need changes

OUTPUT FORMAT:

For PATCHING existing files:
<patch>
--- path/to/file
+++ path/to/file
@@ -line,count +line,count @@
- old line
+ new line
</patch>

For CREATING missing files:
<newfile path="path/to/file">
file content here
</newfile>

For FULL FILE REPLACEMENT (syntax errors only):
<file path="path/to/file">
complete file content
</file>

If no fix is possible: <patch></patch>

No text outside blocks. No markdown. No commentary."""

    # Extended system prompt for syntax errors (full file replacement)
    SYNTAX_FIX_PROMPT = """You are fixing a SYNTAX ERROR.

The file has malformed code (mismatched brackets, tokens, etc).
You MUST return the COMPLETE fixed file.

Use: <file path="filepath">complete content</file>

Rules:
- Return the ENTIRE file, not a patch
- Fix all bracket mismatches {{ }} ( ) [ ]
- Remove duplicate code blocks
- Remove orphaned/unreachable code
- Maintain proper component structure

No explanations. Only the <file> block."""

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
        if context is None:
            logger.error("[FixerAgent] Received None context")
            return {
                "success": False,
                "error": "Invalid context: context is None",
                "fixed_files": [],
                "instructions": None
            }

        # Ensure metadata is never None
        metadata = context.metadata if context.metadata is not None else {}
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

    def _parse_patch_blocks(self, response: str) -> List[Dict[str, str]]:
        """
        Parse <patch>...</patch> blocks from response (unified diff format)

        Args:
            response: Raw response from Claude

        Returns:
            List of patch dictionaries with path and patch content
        """
        patches = []
        patch_pattern = r'<patch>(.*?)</patch>'
        matches = re.findall(patch_pattern, response, re.DOTALL)

        for patch_content in matches:
            patch_content = patch_content.strip()

            # Extract file path from diff header (--- path or +++ path)
            path_match = re.search(r'^(?:---|\+\+\+)\s+([^\s]+)', patch_content, re.MULTILINE)
            if path_match:
                file_path = path_match.group(1)
                # Clean up path (remove a/ or b/ prefix from git diff)
                file_path = re.sub(r'^[ab]/', '', file_path)

                patches.append({
                    "path": file_path.strip(),
                    "patch": patch_content
                })
            else:
                logger.warning(f"Could not extract file path from patch block")

        logger.info(f"Parsed {len(patches)} patch blocks from fixer response")
        return patches

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

    def _parse_request_files(self, response: str) -> List[str]:
        """
        Parse <request_file>...</request_file> blocks from response

        When the fixer needs more context, it can request additional files.

        Args:
            response: Raw response from Claude

        Returns:
            List of file paths requested
        """
        request_pattern = r'<request_file>(.*?)</request_file>'
        matches = re.findall(request_pattern, response, re.DOTALL)

        requested = [m.strip() for m in matches if m.strip()]
        if requested:
            logger.info(f"Fixer requested {len(requested)} additional files: {requested}")

        return requested

    def _parse_newfile_blocks(self, response: str) -> List[Dict[str, str]]:
        """
        Parse <newfile path="...">...</newfile> blocks from response.

        These are for creating new files that don't exist (missing config files).

        Args:
            response: Raw response from Claude

        Returns:
            List of new file dictionaries with path and content
        """
        new_files = []
        newfile_pattern = r'<newfile\s+path="([^"]+)">(.*?)</newfile>'
        matches = re.findall(newfile_pattern, response, re.DOTALL)

        for path, content in matches:
            # Clean up content - remove markdown code blocks if present
            content = content.strip()
            if content.startswith('```'):
                lines = content.split('\n')
                # Remove first line (```json or ```javascript etc)
                if lines:
                    lines = lines[1:]
                # Remove last line if it's just ```
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                content = '\n'.join(lines)

            new_files.append({
                "path": path.strip(),
                "content": content.strip()
            })

        if new_files:
            logger.info(f"Parsed {len(new_files)} new files to create: {[f['path'] for f in new_files]}")

        return new_files

    async def _try_deterministic_export_fix(
        self,
        project_id: str,
        error_message: str,
        project_path: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Deterministically fix export/import mismatches (no AI needed).

        This fixes the common error:
        - "No matching export in 'X.tsx' for import 'default'"

        When components use named exports (export const X = ...) but
        imports expect default exports (import X from ...).

        The fix: Add 'export default ComponentName;' at the end of the file.

        Returns:
            Dict with response and files_modified if fixed, None otherwise
        """
        # Pattern: No matching export in "path" for import "default"
        export_error_pattern = r'No matching export in ["\']([^"\']+)["\'] for import ["\']default["\']'
        matches = re.findall(export_error_pattern, error_message)

        if not matches:
            return None

        logger.info(f"[FixerAgent:{project_id}] Found {len(matches)} export mismatch errors - using deterministic fix")

        # Get project path if not provided
        if project_path is None:
            try:
                from app.modules.automation.file_manager import FileManager
                fm = FileManager()
                project_path = fm.get_project_path(project_id)
            except Exception as e:
                logger.warning(f"[FixerAgent:{project_id}] Could not get project path: {e}")
                return None

        files_modified = []
        patches = []
        unique_files = set(matches)

        for rel_path in unique_files:
            try:
                # Handle paths like src/components/UI/Button.tsx
                file_path = project_path / rel_path

                # Also try with frontend/ prefix for full-stack projects
                if not file_path.exists():
                    file_path = project_path / "frontend" / rel_path
                if not file_path.exists():
                    logger.warning(f"[FixerAgent:{project_id}] File not found: {rel_path}")
                    continue

                content = file_path.read_text(encoding='utf-8')

                # Check if file already has a default export
                if re.search(r'export\s+default\s+', content):
                    logger.info(f"[FixerAgent:{project_id}] File already has default export: {rel_path}")
                    continue

                # Find the component name from named exports
                # Pattern: export const ComponentName = ...
                # or: export function ComponentName(...
                # or: export const ComponentName: React.FC = ...
                component_match = re.search(
                    r'export\s+(?:const|function|class)\s+([A-Z][a-zA-Z0-9]*)',
                    content
                )

                if not component_match:
                    logger.warning(f"[FixerAgent:{project_id}] Could not find component name in {rel_path}")
                    continue

                component_name = component_match.group(1)
                logger.info(f"[FixerAgent:{project_id}] Found component '{component_name}' in {rel_path}")

                # Add default export at the end of the file
                if content.endswith('\n'):
                    new_content = content + f"\nexport default {component_name};\n"
                else:
                    new_content = content + f"\n\nexport default {component_name};\n"

                # Write fixed content
                file_path.write_text(new_content, encoding='utf-8')

                # Determine the correct relative path
                try:
                    final_rel_path = str(file_path.relative_to(project_path))
                except ValueError:
                    final_rel_path = rel_path

                files_modified.append(final_rel_path)
                logger.info(f"[FixerAgent:{project_id}] Added 'export default {component_name}' to {final_rel_path}")

                # Create a patch for the response
                patches.append(f"""<patch>
--- {final_rel_path}
+++ {final_rel_path}
@@ -end of file @@
+export default {component_name};
</patch>""")

                # Sync to S3 for persistence
                try:
                    from app.services.unified_storage import unified_storage
                    await unified_storage.save_to_database(
                        project_id=project_id,
                        file_path=final_rel_path,
                        content=new_content
                    )
                    logger.info(f"[FixerAgent:{project_id}] Persisted fix to S3+DB: {final_rel_path}")
                except Exception as sync_err:
                    logger.warning(f"[FixerAgent:{project_id}] Failed to persist fix: {sync_err}")

            except Exception as e:
                logger.warning(f"[FixerAgent:{project_id}] Error fixing {rel_path}: {e}")
                continue

        if files_modified:
            return {
                "response": "\n".join(patches),
                "files_modified": files_modified,
                "message": f"Deterministic fix: Added default exports to {len(files_modified)} component(s)",
                "deterministic": True
            }

        return None

    async def fix_error(
        self,
        error: Dict[str, Any],
        project_id: str,
        file_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fix a specific error - called by orchestrator

        Follows Bolt.new architecture:
        1. Classify error (rule-based, no AI)
        2. Check if Claude should be called
        3. Check retry limits
        4. Call Claude with strict prompt
        5. Validate output
        6. Apply fix

        Args:
            error: Error dictionary with message, file, line, etc.
            project_id: Project ID
            file_context: Context about project files and tech stack

        Returns:
            Dict with response containing fixed files
        """
        # Build error message
        error_message = error.get("message", "Unknown error")
        error_file = error.get("file", "unknown")
        error_line = error.get("line", 0)
        stderr = error.get("stderr", "")

        # =================================================================
        # STEP 1: CLASSIFY ERROR (Rule-based, NO AI)
        # =================================================================
        classified = ErrorClassifier.classify(
            error_message=error_message,
            stderr=stderr,
            exit_code=error.get("exit_code", 1)
        )
        logger.info(
            f"[FixerAgent:{project_id}] Classified error: {classified.error_type.value}, "
            f"fixable={classified.is_claude_fixable}, confidence={classified.confidence}"
        )

        # =================================================================
        # STEP 2: DECISION GATE - Should Claude be called?
        # =================================================================
        should_call, reason = ErrorClassifier.should_call_claude(classified)
        if not should_call:
            logger.info(f"[FixerAgent:{project_id}] NOT calling Claude: {reason}")
            return {
                "success": False,
                "error": reason,
                "error_type": classified.error_type.value,
                "suggested_action": classified.suggested_action,
                "skip_claude": True
            }

        # =================================================================
        # STEP 3: CHECK RETRY LIMITS
        # =================================================================
        error_hash = retry_limiter.hash_error(error_message)
        can_retry, retry_reason = retry_limiter.can_retry(project_id, error_hash)
        if not can_retry:
            logger.warning(f"[FixerAgent:{project_id}] Retry limit reached: {retry_reason}")
            return {
                "success": False,
                "error": retry_reason,
                "error_type": classified.error_type.value,
                "retry_blocked": True,
                "stats": retry_limiter.get_stats(project_id)
            }

        # =================================================================
        # STEP 4: Try deterministic fixes FIRST (fast, free, no AI cost)
        # =================================================================
        deterministic_result = await self._try_deterministic_export_fix(
            project_id=project_id,
            error_message=error_message
        )
        if deterministic_result:
            logger.info(f"[FixerAgent:{project_id}] Deterministic fix applied - skipping AI")
            retry_limiter.record_attempt(project_id, error_hash, tokens_used=0, fixed=True)
            return deterministic_result

        # Get file contents for context
        files_created = file_context.get("files_created", [])
        tech_stack = file_context.get("tech_stack", {})
        terminal_logs = file_context.get("terminal_logs", [])
        additional_files = file_context.get("additional_files", {})  # From retry with requested files

        # Get complete log payload from LogBus (all 5 collectors)
        log_payload = {}
        try:
            from app.services.log_bus import get_log_bus
            log_bus = get_log_bus(project_id)
            log_payload = log_bus.get_fixer_payload()
            logger.info(f"[FixerAgent] LogBus payload: {len(log_payload.get('browser_errors', []))} browser, "
                       f"{len(log_payload.get('build_errors', []))} build, "
                       f"{len(log_payload.get('backend_errors', []))} backend, "
                       f"{len(log_payload.get('network_errors', []))} network, "
                       f"{len(log_payload.get('docker_errors', []))} docker errors")
        except Exception as e:
            logger.warning(f"[FixerAgent] Could not get LogBus payload: {e}")

        # Use Context Engine to get relevant files with FULL content
        try:
            from app.modules.automation.file_manager import FileManager
            from app.modules.automation.context_engine import build_fixer_context

            fm = FileManager()
            project_path = str(fm.get_project_path(project_id))

            # Build context using the Context Engine
            context_payload = build_fixer_context(
                project_path=project_path,
                user_message=f"Fix error: {error_message}",
                errors=[error],
                terminal_logs=terminal_logs,
                all_files=files_created,
                active_file=error_file if error_file != "unknown" else None,
                tech_stack=list(tech_stack.keys()) if isinstance(tech_stack, dict) else tech_stack
            )

            # Build relevant files section with FULL content
            relevant_files_content = ""
            for path, content in context_payload.relevant_files.items():
                relevant_files_content += f"\n--- {path} ---\n```\n{content}\n```\n"

            # Add any additional files requested by fixer in previous attempt
            for path, content in additional_files.items():
                if path not in context_payload.relevant_files:
                    relevant_files_content += f"\n--- {path} (requested) ---\n```\n{content}\n```\n"

            total_files = len(context_payload.relevant_files) + len(additional_files)
            logger.info(f"[FixerAgent] Context Engine selected {len(context_payload.relevant_files)} files + {len(additional_files)} requested files")

        except Exception as e:
            logger.warning(f"[FixerAgent] Context Engine failed, falling back to basic: {e}")
            # Fallback to basic file reading
            relevant_files_content = ""
            if error_file and error_file != "unknown":
                try:
                    from app.modules.automation.file_manager import FileManager
                    fm = FileManager()
                    project_path = fm.get_project_path(project_id)
                    file_path = project_path / error_file
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            relevant_files_content = f"\n--- {error_file} ---\n```\n{content}\n```\n"
                except Exception as read_err:
                    logger.warning(f"Could not read affected file: {read_err}")

            # Add any additional files requested by fixer in previous attempt
            for path, content in additional_files.items():
                relevant_files_content += f"\n--- {path} (requested) ---\n```\n{content}\n```\n"

            context_payload = None

        # Build comprehensive logs section from LogBus (all 5 collectors)
        logs_section = ""
        if log_payload:
            # Browser Console Errors
            browser_errors = log_payload.get("browser_errors", [])
            if browser_errors:
                logs_section += "\n--- BROWSER CONSOLE ERRORS ---\n"
                for err in browser_errors[:10]:
                    logs_section += f"• {err.get('message', '')}"
                    if err.get('file'):
                        logs_section += f" ({err['file']}:{err.get('line', '?')})"
                    logs_section += "\n"

            # Build Errors (Vite/Webpack/tsc)
            build_errors = log_payload.get("build_errors", [])
            if build_errors:
                logs_section += "\n--- BUILD ERRORS ---\n"
                for err in build_errors[:10]:
                    logs_section += f"• {err.get('message', '')}\n"

            # Backend Runtime Errors
            backend_errors = log_payload.get("backend_errors", [])
            if backend_errors:
                logs_section += "\n--- BACKEND ERRORS ---\n"
                for err in backend_errors[:10]:
                    logs_section += f"• {err.get('message', '')}\n"

            # Network Errors (fetch/XHR)
            network_errors = log_payload.get("network_errors", [])
            if network_errors:
                logs_section += "\n--- NETWORK ERRORS ---\n"
                for err in network_errors[:10]:
                    logs_section += f"• {err.get('method', 'GET')} {err.get('url', '')} - {err.get('status', '?')} {err.get('message', '')}\n"

            # Docker Errors
            docker_errors = log_payload.get("docker_errors", [])
            if docker_errors:
                logs_section += "\n--- DOCKER ERRORS ---\n"
                for err in docker_errors[:10]:
                    logs_section += f"• {err.get('message', '')}\n"

            # Stack Traces
            stack_traces = log_payload.get("stack_traces", [])
            if stack_traces:
                logs_section += "\n--- STACK TRACES ---\n"
                for trace in stack_traces[:3]:
                    logs_section += f"• {trace.get('message', '')}\n"
                    for frame in trace.get('frames', [])[:5]:
                        logs_section += f"    at {frame.get('function', '?')} ({frame.get('file', '?')}:{frame.get('line', '?')})\n"

        # =================================================================
        # STEP 5: BUILD STRICT PROMPT (based on error type)
        # =================================================================
        # Get the error-type specific prompt template
        error_type_prompt = ErrorClassifier.get_claude_prompt_template(classified.error_type)

        # Choose system prompt based on error type
        if classified.error_type == ErrorType.SYNTAX_ERROR:
            system_prompt = self.SYNTAX_FIX_PROMPT
            max_tokens = 16384  # Need more tokens for full file
        else:
            system_prompt = self.SYSTEM_PROMPT
            max_tokens = 4096  # Smaller for diffs

        # Build the strict user prompt
        prompt = f"""{error_type_prompt}

ERROR: {error_message}
FILE: {classified.file_path or error_file}
LINE: {classified.line_number or error_line}

CONTEXT:
{json.dumps(classified.extracted_context, indent=2) if classified.extracted_context else "None"}

FILE CONTENT:
{relevant_files_content if relevant_files_content else "No file content available"}

BUILD LOG (last 20 lines):
{logs_section[-2000:] if logs_section else "No logs"}
"""

        # =================================================================
        # STEP 6: CALL CLAUDE (strict prompt, limited tokens)
        # =================================================================
        logger.info(f"[FixerAgent:{project_id}] Calling Claude for {classified.error_type.value} fix")
        response = await self._call_claude(
            system_prompt=system_prompt,
            user_prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.1  # Very low for precise fixes
        )

        # Estimate tokens used (rough estimate)
        tokens_used = len(prompt.split()) + len(response.split())

        # =================================================================
        # STEP 7: PARSE RESPONSE
        # =================================================================
        patches = self._parse_patch_blocks(response)
        fixed_files = self._parse_file_blocks(response)
        new_files = self._parse_newfile_blocks(response)
        requested_files = self._parse_request_files(response)

        logger.info(
            f"[FixerAgent:{project_id}] Claude returned: "
            f"{len(patches)} patches, {len(fixed_files)} files, {len(new_files)} new files"
        )

        # =================================================================
        # STEP 8: VALIDATE PATCHES (before applying)
        # =================================================================
        try:
            from app.modules.automation.file_manager import FileManager
            fm = FileManager()
            project_path = fm.get_project_path(project_id)
        except:
            project_path = Path("/tmp")

        validation_errors = []
        validated_patches = []
        validated_files = []
        validated_new_files = []

        # Validate patches
        for patch in patches:
            result = PatchValidator.validate_diff(
                patch_content=patch.get("patch", ""),
                project_path=project_path
            )
            if result.is_valid:
                validated_patches.append(patch)
            else:
                validation_errors.extend(result.errors)
                logger.warning(f"[FixerAgent:{project_id}] Invalid patch for {result.file_path}: {result.errors}")

        # Validate full file replacements
        for file_info in fixed_files:
            result = PatchValidator.validate_full_file(
                file_path=file_info.get("path", ""),
                content=file_info.get("content", ""),
                project_path=project_path
            )
            if result.is_valid:
                validated_files.append(file_info)
            else:
                validation_errors.extend(result.errors)
                logger.warning(f"[FixerAgent:{project_id}] Invalid file {result.file_path}: {result.errors}")

        # Validate new files
        for file_info in new_files:
            result = PatchValidator.validate_new_file(
                file_path=file_info.get("path", ""),
                content=file_info.get("content", ""),
                project_path=project_path
            )
            if result.is_valid:
                validated_new_files.append(file_info)
            else:
                validation_errors.extend(result.errors)
                logger.warning(f"[FixerAgent:{project_id}] Invalid new file {result.file_path}: {result.errors}")

        # =================================================================
        # STEP 9: RECORD ATTEMPT
        # =================================================================
        has_valid_fix = (len(validated_patches) > 0 or
                        len(validated_files) > 0 or
                        len(validated_new_files) > 0)

        retry_limiter.record_attempt(
            project_id=project_id,
            error_hash=error_hash,
            tokens_used=tokens_used,
            fixed=has_valid_fix
        )

        # =================================================================
        # STEP 10: RETURN RESULT
        # =================================================================
        if validation_errors and not has_valid_fix:
            logger.error(f"[FixerAgent:{project_id}] All patches failed validation: {validation_errors}")
            return {
                "success": False,
                "error": f"Patches failed validation: {validation_errors[0]}",
                "validation_errors": validation_errors,
                "error_type": classified.error_type.value,
                "response": response
            }

        return {
            "success": has_valid_fix,
            "response": response,
            "patches": validated_patches,
            "fixed_files": validated_files,
            "new_files": validated_new_files,
            "requested_files": requested_files,
            "error_fixed": error_message,
            "error_type": classified.error_type.value,
            "validation_warnings": validation_errors if not has_valid_fix else [],
            "tokens_used": tokens_used,
            "retry_stats": retry_limiter.get_stats(project_id)
        }
