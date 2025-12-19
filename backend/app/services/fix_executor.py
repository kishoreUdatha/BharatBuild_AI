"""
Fix Executor Service - Executes fixes via Fixer Agent (Bolt.new style)

This is the callback that AutoFixer uses to actually fix errors.
It calls the Fixer Agent, parses patches, applies them, and restarts the project.

Full flow:
1. Build fixer payload (logs + files + tech stack) using ContextEngine
2. Call Fixer Agent (Claude) with full context
3. Parse <file> blocks (can create NEW files!)
4. Apply patches/create files
5. Restart Docker/Preview
6. Notify clients

BOLT.NEW STYLE IMPROVEMENTS:
- Uses ContextEngine to scan ALL project files
- Detects MISSING modules (files that need to be CREATED)
- Includes SIBLING files for pattern matching
- Creates NEW files, not just patches existing ones
"""

import re
import time
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.core.logging_config import logger
from app.core.config import settings

# ========== FIX RATE LIMITER ==========
# Prevents infinite fix loops by enforcing cooldowns between fix attempts
_fix_timestamps: Dict[str, List[float]] = {}  # project_id -> list of timestamps
_FIX_COOLDOWN_SECONDS = settings.AUTOFIXER_FIX_COOLDOWN_SECONDS
_MAX_FIXES_PER_WINDOW = 5  # Max fix attempts per window
_FIX_WINDOW_SECONDS = settings.AUTOFIXER_FIX_WINDOW_SECONDS


def _can_attempt_fix(project_id: str) -> tuple[bool, str]:
    """
    Check if we can attempt a fix for this project (rate limiting).
    Returns (allowed, reason) tuple.
    """
    now = time.time()

    # Initialize if needed
    if project_id not in _fix_timestamps:
        _fix_timestamps[project_id] = []

    timestamps = _fix_timestamps[project_id]

    # Clean old timestamps outside the window
    timestamps[:] = [t for t in timestamps if now - t < _FIX_WINDOW_SECONDS]

    # Check cooldown from last fix
    if timestamps and now - timestamps[-1] < _FIX_COOLDOWN_SECONDS:
        remaining = _FIX_COOLDOWN_SECONDS - (now - timestamps[-1])
        return False, f"Cooldown active ({remaining:.1f}s remaining)"

    # Check max attempts in window
    if len(timestamps) >= _MAX_FIXES_PER_WINDOW:
        oldest = timestamps[0]
        reset_in = _FIX_WINDOW_SECONDS - (now - oldest)
        return False, f"Max attempts ({_MAX_FIXES_PER_WINDOW}) reached. Resets in {reset_in:.0f}s"

    return True, "OK"


def _record_fix_attempt(project_id: str):
    """Record a fix attempt timestamp"""
    now = time.time()
    if project_id not in _fix_timestamps:
        _fix_timestamps[project_id] = []
    _fix_timestamps[project_id].append(now)


from app.modules.agents.production_fixer_agent import production_fixer_agent
from app.modules.agents.base_agent import AgentContext
from app.modules.automation.context_engine import ContextEngine
from app.services.unified_storage import UnifiedStorageService as UnifiedStorageManager
from app.services.restart_manager import restart_project
from app.core.config import settings


class FixExecutor:
    """
    Fix Executor class - Wrapper for executing fixes via Fixer Agent.

    Usage:
        fix_executor = FixExecutor(project_id)
        result = await fix_executor.execute_fix(
            error_message="...",
            stack_trace="...",
            command="npm run dev",
            context={"file_tree": [...], "recently_modified": [...]}
        )
    """

    def __init__(self, project_id: str):
        self.project_id = project_id

    async def execute_fix(
        self,
        error_message: str,
        stack_trace: str = "",
        command: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute fix with the new interface that accepts error_message, stack_trace, command, context.

        This wraps the module-level execute_fix function, converting the new interface
        to the old log_payload format.
        """
        # Build log_payload format from the new parameters
        log_payload = {
            "browser_errors": [{
                "message": error_message,
                "stack": stack_trace,
                "file": "",
                "line": None
            }] if error_message else [],
            "build_errors": [],
            "backend_errors": [],
            "docker_errors": [],
            "network_errors": [],
            # Include Bolt.new-style context
            "context": context or {}
        }

        # If we have recently_modified files in context, prioritize those in the fixer
        if context and context.get("recently_modified"):
            logger.info(f"[FixExecutor:{self.project_id}] Using {len(context['recently_modified'])} recently modified files as hints")

        if context and context.get("file_tree"):
            logger.info(f"[FixExecutor:{self.project_id}] File tree has {len(context['file_tree'])} files")

        return await execute_fix_internal(self.project_id, log_payload)


async def execute_fix_internal(project_id: str, log_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute fix using Fixer Agent with FULL CONTEXT (Bolt.new style).

    This is the callback function for AutoFixer.
    Called automatically when errors are detected!

    Args:
        project_id: Project ID
        log_payload: LogBus payload containing all errors

    Returns:
        Result dict with success status and applied patches
    """
    logger.info(f"[FixExecutor:{project_id}] Starting automatic fix")

    # ========== RATE LIMIT CHECK ==========
    # Prevent infinite fix loops
    can_fix, reason = _can_attempt_fix(project_id)
    if not can_fix:
        logger.warning(f"[FixExecutor:{project_id}] Rate limited: {reason}")
        return {
            "success": False,
            "error": f"Fix rate limited: {reason}",
            "rate_limited": True,
            "files_created": 0,
            "patches_applied": 0,
            "files_modified": []
        }

    # Record this attempt
    _record_fix_attempt(project_id)

    try:
        # Get storage manager
        storage = UnifiedStorageManager()

        # ========== BOLT.NEW STYLE: USE CONTEXT ENGINE ==========
        # Get project path for ContextEngine
        project_path = Path(settings.USER_PROJECTS_PATH) / project_id
        user_id = None  # Will be extracted from path

        if not project_path.exists():
            # Try sandbox path
            sandbox_base = Path(settings.SANDBOX_PATH) if hasattr(settings, 'SANDBOX_PATH') else Path("C:/tmp/sandbox/workspace")
            # Find the project directory (could be nested under user_id)
            for user_dir in sandbox_base.iterdir():
                if user_dir.is_dir():
                    potential_path = user_dir / project_id
                    if potential_path.exists():
                        project_path = potential_path
                        user_id = user_dir.name  # Extract user_id from path!
                        break

        logger.info(f"[FixExecutor:{project_id}] Using project path: {project_path}, user_id: {user_id}")

        # Initialize ContextEngine
        context_engine = ContextEngine(str(project_path))

        # Scan ALL project files (Bolt.new style!)
        # scan_project_files() returns List[Dict] with {'path': str, 'content': str, 'size': int}
        all_files_list = context_engine.scan_project_files()
        logger.info(f"[FixExecutor:{project_id}] Scanned {len(all_files_list)} project files")

        # Convert to Dict[str, str] format for detect_tech_stack_from_files and other uses
        # Robust null handling: skip invalid entries, convert None content to empty string
        all_files: Dict[str, str] = {}
        for f in all_files_list:
            if f is None or not isinstance(f, dict):
                continue
            path = f.get('path')
            if not path or not isinstance(path, str):
                continue
            content = f.get('content')
            # Convert None, non-string, or any falsy content to empty string
            all_files[path] = content if isinstance(content, str) else ''

        # Build errors list from log_payload (convert to ContextEngine format)
        # SAFETY: Use `or ""` to convert None values to empty strings
        errors = []
        for error in log_payload.get("browser_errors") or []:
            if error is None or not isinstance(error, dict):
                continue
            errors.append({
                "message": error.get("message") or "",
                "file": error.get("file") or "",
                "line": error.get("line"),
                "stack": error.get("stack") or "",
                "source": "browser"
            })
        for error in log_payload.get("build_errors") or []:
            if error is None or not isinstance(error, dict):
                continue
            errors.append({
                "message": error.get("message") or "",
                "file": error.get("file") or "",
                "stack": error.get("stack") or "",
                "source": "build"
            })
        for error in log_payload.get("backend_errors") or []:
            if error is None or not isinstance(error, dict):
                continue
            errors.append({
                "message": error.get("message") or "",
                "file": error.get("file") or "",
                "stack": error.get("stack") or "",
                "source": "backend"
            })
        for error in log_payload.get("docker_errors") or []:
            if error is None:
                continue
            errors.append({
                "message": (error.get("message") or "") if isinstance(error, dict) else str(error),
                "source": "docker"
            })

        # Build context using ContextEngine (extracts missing modules, sibling files, etc.)
        # NOTE: build_context expects List[Dict] format, so use all_files_list
        # detect_tech_stack_from_files expects Dict[str, str] format, so use all_files
        # IMPORTANT: tech_stack expects List[str], convert comma-separated string to list
        detected_stack = detect_tech_stack_from_files(all_files)
        tech_stack_list = [s.strip() for s in detected_stack.split(",")] if detected_stack and detected_stack != "Unknown" else None

        context_payload = context_engine.build_context(
            user_message=build_error_description(log_payload),
            errors=errors,
            terminal_logs=[],  # Could add terminal logs if available
            all_files=all_files_list,  # Pass list format to build_context
            tech_stack=tech_stack_list  # Pass list format for tech_stack
        )

        logger.info(f"[FixExecutor:{project_id}] Context: {len(context_payload.relevant_files)} files, {len(context_payload.missing_modules)} missing modules")

        # Build error description from log payload
        error_description = build_error_description(log_payload)

        if not error_description:
            return {
                "success": False,
                "error": "No errors to fix",
                "patches_applied": 0,
                "files_modified": []
            }

        # ========== BUILD FILE CONTEXT FROM CONTEXT ENGINE ==========
        # Convert ContextEngine output to file dict for Fixer Agent
        # NOTE: context_payload.relevant_files is already Dict[str, str] (path -> content)
        project_files: Dict[str, str] = dict(context_payload.relevant_files)

        # Also add any files from all_files dict that might be needed
        for file_path, content in all_files.items():
            if file_path not in project_files:
                project_files[file_path] = content

        logger.info(f"[FixExecutor:{project_id}] Built file context with {len(project_files)} files")

        # Build context for ProductionFixerAgent (using AgentContext)
        # Derive sibling files from missing_modules (files in same directory as suggested paths)
        sibling_files = []
        for missing in context_payload.missing_modules:
            suggested_path = missing.get('suggested_path', '')
            if suggested_path:
                suggested_dir = str(Path(suggested_path).parent)
                # Find project files in the same directory
                for file_path in project_files.keys():
                    file_dir = str(Path(file_path).parent)
                    if file_dir == suggested_dir and file_path not in sibling_files:
                        sibling_files.append(file_path)

        # Extract Bolt.new-style context (file_tree, recently_modified) from log_payload
        bolt_context = log_payload.get("context", {}) or {}
        frontend_file_tree = bolt_context.get("file_tree", []) or []
        recently_modified = bolt_context.get("recently_modified", []) or []

        logger.info(f"[FixExecutor:{project_id}] Bolt.new context: {len(frontend_file_tree)} files in tree, {len(recently_modified)} recently modified")

        # Create AgentContext for ProductionFixerAgent
        agent_context = AgentContext(
            project_id=project_id,
            user_request=f"Fix error: {error_description}",
            metadata={
                "error_message": error_description,
                "stack_trace": "\n".join([e.get("stack", "") for e in errors if e.get("stack")]),
                "project_files": list(project_files.keys()),
                "file_contents": project_files,
                "tech_stack": context_payload.tech_stack,
                "missing_modules": context_payload.missing_modules,
                "sibling_files": sibling_files,
                # Bolt.new-style context for Claude
                "file_tree": frontend_file_tree if frontend_file_tree else list(all_files.keys()),
                "recently_modified": recently_modified,
                "environment": {
                    "framework": context_payload.tech_stack,
                    "project_type": "auto-detected",
                }
            }
        )

        # Call ProductionFixerAgent (singleton instance)
        logger.info(f"[FixExecutor:{project_id}] Calling ProductionFixerAgent with {len(project_files)} files, {len(context_payload.missing_modules)} missing modules")

        result = await production_fixer_agent.process(agent_context)

        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "Fixer Agent failed"),
                "patches_applied": 0,
                "files_modified": []
            }

        # ========== GET FIXES FROM PRODUCTIONFIXTRAGENT (HYBRID) ==========
        # ProductionFixerAgent now returns:
        # - fixed_files: Full content for new/missing files
        # - patches: Unified diff for existing files
        file_blocks = result.get("fixed_files", [])
        patches = result.get("patches", [])

        # Also check for new_files_created (missing config files)
        new_files_created = result.get("new_files_created", [])
        if new_files_created:
            # Add new files to file_blocks if not already there
            for new_file in new_files_created:
                if new_file not in file_blocks:
                    file_blocks.append(new_file)

        # Get runCommand (instructions) from fixer agent
        run_command = result.get("instructions")

        logger.info(f"[FixExecutor:{project_id}] Got {len(patches)} patches + {len(file_blocks)} full files + runCommand: {run_command}")

        if not file_blocks and not patches and not run_command:
            return {
                "success": False,
                "error": "No patches, file blocks, or commands generated",
                "patches_applied": 0,
                "files_modified": []
            }

        # ========== EXECUTE RUN COMMAND (npm install, pip install, etc.) ==========
        command_executed = False
        if run_command:
            command_executed = await execute_install_command(project_path, run_command)
            if command_executed:
                logger.info(f"[FixExecutor:{project_id}] Successfully executed: {run_command}")

        # ========== APPLY FILE BLOCKS (CREATE NEW FILES - Bolt.new style!) ==========
        files_modified = []
        files_created = 0

        for file_block in file_blocks:
            file_path = file_block.get("path")
            file_content = file_block.get("content")

            if not file_path or file_content is None:
                continue

            # Skip node_modules and other system directories (locked files on Windows)
            if 'node_modules' in file_path or '.git' in file_path:
                logger.warning(f"[FixExecutor:{project_id}] Skipping system file: {file_path}")
                continue

            try:
                # Create new file (or overwrite if exists)
                # Use write_to_sandbox with user_id for correct path
                await storage.write_to_sandbox(project_id, file_path, file_content, user_id)
                files_modified.append(file_path)
                files_created += 1
                logger.info(f"[FixExecutor:{project_id}] Created/updated file: {file_path}")

            except Exception as e:
                logger.error(f"[FixExecutor:{project_id}] Failed to create file {file_path}: {e}")

        # ========== APPLY UNIFIED DIFF PATCHES (MODIFY EXISTING FILES) ==========
        patches_applied = 0

        for patch_info in patches:
            file_path = patch_info.get("path")
            patch_content = patch_info.get("patch")

            if not file_path or not patch_content:
                continue

            # Skip node_modules and other system directories (locked files on Windows)
            if 'node_modules' in file_path or '.git' in file_path:
                logger.warning(f"[FixExecutor:{project_id}] Skipping system file patch: {file_path}")
                continue

            try:
                # Read current file content
                current_content = project_files.get(file_path)
                if current_content is None:
                    try:
                        current_content = await storage.read_from_sandbox(project_id, file_path, user_id)
                    except Exception:
                        current_content = ""

                # Apply unified diff patch
                new_content = apply_unified_patch(current_content or "", patch_content)

                if new_content is None:
                    # Patch parsing failed - log with details for debugging
                    logger.error(f"[FixExecutor:{project_id}] ❌ Patch parsing FAILED for {file_path}. "
                                f"Patch content (first 200 chars): {patch_content[:200]}...")
                    # Try to recover by applying as full file replacement if patch looks like complete file
                    if not patch_content.startswith('---') and not patch_content.startswith('@@'):
                        logger.info(f"[FixExecutor:{project_id}] Attempting full file replacement for {file_path}")
                        await storage.write_to_sandbox(project_id, file_path, patch_content, user_id)
                        if file_path not in files_modified:
                            files_modified.append(file_path)
                        patches_applied += 1
                elif new_content != current_content:
                    # Save patched file (use write_to_sandbox with user_id)
                    await storage.write_to_sandbox(project_id, file_path, new_content, user_id)
                    if file_path not in files_modified:
                        files_modified.append(file_path)
                    patches_applied += 1
                    logger.info(f"[FixExecutor:{project_id}] ✅ Applied unified diff patch to {file_path}")
                else:
                    logger.warning(f"[FixExecutor:{project_id}] ⚠️ Patch produced no changes for {file_path}")

            except Exception as e:
                logger.error(f"[FixExecutor:{project_id}] ❌ Failed to apply patch to {file_path}: {e}")

        # ========== STEP 5: RESTART PROJECT (Bolt.new style) ==========
        # After patches/files are applied, restart Docker/Preview so changes take effect
        total_changes = patches_applied + files_created + (1 if command_executed else 0)
        if total_changes > 0:
            logger.info(f"[FixExecutor:{project_id}] Restarting project after {files_created} files created, {patches_applied} patches, command_executed={command_executed}")
            try:
                restart_result = await restart_project(
                    project_id,
                    restart_docker=True,
                    restart_preview=True,
                    notify_clients=True
                )
                logger.info(f"[FixExecutor:{project_id}] Restart result: {restart_result}")
            except Exception as e:
                logger.warning(f"[FixExecutor:{project_id}] Restart failed (changes still applied): {e}")

        return {
            "success": total_changes > 0,
            "patches_applied": patches_applied,
            "files_created": files_created,
            "files_modified": files_modified,
            "command_executed": run_command if command_executed else None,
            "error": None if total_changes > 0 else "No changes could be applied"
        }

    except Exception as e:
        logger.error(f"[FixExecutor:{project_id}] Fix execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "patches_applied": 0,
            "files_modified": []
        }


def build_error_description(log_payload: Dict[str, Any]) -> str:
    """Build error description from LogBus payload with robust null handling"""
    if log_payload is None:
        return ""

    parts = []

    def safe_get(d: Any, key: str, default: str = "") -> str:
        """Safely get a string value from a dict, handling None and non-dict inputs"""
        if d is None or not isinstance(d, dict):
            return default
        val = d.get(key, default)
        return str(val) if val is not None else default

    # Browser errors
    browser_errors = log_payload.get("browser_errors") or []
    for error in browser_errors[:5]:
        if error is None or not isinstance(error, dict):
            continue
        msg = safe_get(error, "message")
        file = safe_get(error, "file")
        line = safe_get(error, "line")
        if msg:
            parts.append(f"Browser Error: {msg}")
        if file:
            parts.append(f"  Location: {file}:{line}")
        stack = safe_get(error, "stack")
        if stack:
            parts.append(f"  Stack: {stack[:300]}")

    # Build errors
    build_errors = log_payload.get("build_errors") or []
    for error in build_errors[:5]:
        if error is None or not isinstance(error, dict):
            continue
        msg = safe_get(error, "message")
        if msg:
            parts.append(f"Build Error: {msg}")

    # Backend errors
    backend_errors = log_payload.get("backend_errors") or []
    for error in backend_errors[:3]:
        if error is None or not isinstance(error, dict):
            continue
        msg = safe_get(error, "message")
        if msg:
            parts.append(f"Backend Error: {msg}")

    # Docker errors
    docker_errors = log_payload.get("docker_errors") or []
    for error in docker_errors[:2]:
        if error is None:
            continue
        if isinstance(error, dict):
            msg = safe_get(error, "message")
        else:
            msg = str(error)
        if msg:
            parts.append(f"Docker Error: {msg}")

    # Network errors (less common to fix)
    network_errors = log_payload.get("network_errors") or []
    for error in network_errors[:2]:
        if error is None or not isinstance(error, dict):
            continue
        msg = safe_get(error, "message")
        url = safe_get(error, "url")
        if msg:
            parts.append(f"Network Error: {msg} (URL: {url})")

    return "\n".join(parts)


def detect_tech_stack(files: Dict[str, str]) -> str:
    """Detect tech stack from file contents"""
    stack_parts = []

    file_names = list(files.keys())
    # Handle None values in files dict - convert None to empty string
    all_content = "\n".join(v or '' for v in files.values())

    # React
    if any(".jsx" in f or ".tsx" in f for f in file_names) or "import React" in all_content:
        stack_parts.append("React")

    # Next.js
    if "next.config" in str(file_names) or "from 'next" in all_content:
        stack_parts.append("Next.js")

    # Vue
    if any(".vue" in f for f in file_names):
        stack_parts.append("Vue")

    # TypeScript
    if any(".ts" in f or ".tsx" in f for f in file_names):
        stack_parts.append("TypeScript")

    # Python/FastAPI
    if any(".py" in f for f in file_names):
        stack_parts.append("Python")
        if "fastapi" in all_content.lower():
            stack_parts.append("FastAPI")

    # Node.js
    if "package.json" in file_names:
        stack_parts.append("Node.js")

    # Tailwind
    if "tailwind" in all_content.lower():
        stack_parts.append("Tailwind CSS")

    return ", ".join(stack_parts) if stack_parts else "Unknown"


def parse_patches(response: str) -> List[Dict[str, str]]:
    """Parse <patch> blocks from Fixer Agent response"""
    patches = []

    # SAFETY: Handle None or empty response
    if response is None or not isinstance(response, str):
        logger.warning("[FixExecutor] parse_patches received None or non-string response")
        return patches

    # Pattern to match <patch> blocks
    patch_pattern = r'<patch>\s*(.*?)\s*</patch>'
    matches = re.findall(patch_pattern, response, re.DOTALL)

    for patch_content in matches:
        # Extract file path from --- line
        file_match = re.search(r'^---\s+(\S+)', patch_content, re.MULTILINE)
        if file_match:
            file_path = file_match.group(1)
            # Clean up path (remove a/ prefix if present)
            file_path = re.sub(r'^[ab]/', '', file_path)
            patches.append({
                "file": file_path,
                "content": patch_content.strip()
            })

    return patches


def parse_file_blocks(response: str) -> List[Dict[str, str]]:
    """
    Parse <file> blocks from Fixer Agent response (Bolt.new style).

    This allows the fixer to CREATE NEW FILES, not just patch existing ones!

    Format:
    <file path="src/components/Header.tsx">
    import React from 'react';
    ...
    </file>
    """
    file_blocks = []

    # SAFETY: Handle None or empty response
    if response is None or not isinstance(response, str):
        logger.warning("[FixExecutor] parse_file_blocks received None or non-string response")
        return file_blocks

    # Pattern 1: <file path="...">content</file>
    pattern1 = r'<file\s+path=["\']([^"\']+)["\']>(.*?)</file>'
    for match in re.finditer(pattern1, response, re.DOTALL):
        file_path = match.group(1).strip()
        content = match.group(2).strip()
        file_blocks.append({
            "path": file_path,
            "content": content
        })

    # Pattern 2: <file>path\ncontent</file> (simpler format)
    pattern2 = r'<file>\s*([^\n]+)\n(.*?)</file>'
    for match in re.finditer(pattern2, response, re.DOTALL):
        file_path = match.group(1).strip()
        content = match.group(2).strip()
        # Avoid duplicates
        if not any(fb["path"] == file_path for fb in file_blocks):
            file_blocks.append({
                "path": file_path,
                "content": content
            })

    # Pattern 3: ```tsx filepath="..." or ```typescript filepath="..."
    pattern3 = r'```(?:tsx?|jsx?|typescript|javascript)\s+filepath=["\']([^"\']+)["\']\n(.*?)```'
    for match in re.finditer(pattern3, response, re.DOTALL):
        file_path = match.group(1).strip()
        content = match.group(2).strip()
        if not any(fb["path"] == file_path for fb in file_blocks):
            file_blocks.append({
                "path": file_path,
                "content": content
            })

    logger.info(f"[FixExecutor] Parsed {len(file_blocks)} file blocks from response")
    return file_blocks


def parse_newfile_blocks(response: str) -> List[Dict[str, str]]:
    """
    Parse <newfile> blocks from Fixer Agent response.

    This is for creating missing config files like tsconfig.node.json, postcss.config.js.

    Format:
    <newfile path="tsconfig.node.json">
    {
      "compilerOptions": { ... }
    }
    </newfile>
    """
    newfile_blocks = []

    # SAFETY: Handle None or empty response
    if response is None or not isinstance(response, str):
        logger.warning("[FixExecutor] parse_newfile_blocks received None or non-string response")
        return newfile_blocks

    # Pattern: <newfile path="...">content</newfile>
    pattern = r'<newfile\s+path=["\']([^"\']+)["\']>(.*?)</newfile>'
    for match in re.finditer(pattern, response, re.DOTALL):
        file_path = match.group(1).strip()
        content = match.group(2).strip()

        # Remove markdown code blocks if present
        if content.startswith('```'):
            lines = content.split('\n')
            if lines:
                lines = lines[1:]  # Remove first line (```json etc)
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]  # Remove last line
            content = '\n'.join(lines)

        newfile_blocks.append({
            "path": file_path,
            "content": content.strip()
        })

    if newfile_blocks:
        logger.info(f"[FixExecutor] Parsed {len(newfile_blocks)} newfile blocks: {[f['path'] for f in newfile_blocks]}")

    return newfile_blocks


def detect_tech_stack_from_files(all_files: Dict[str, str]) -> str:
    """
    Detect tech stack from scanned project files.
    Supports ALL major programming languages and frameworks.

    Args:
        all_files: Dict of file_path -> content from ContextEngine.scan_project_files()

    Returns:
        Comma-separated tech stack string
    """
    stack_parts = []

    file_names = list(all_files.keys())
    file_names_lower = [f.lower() for f in file_names]
    # Only check a sample of content to avoid performance issues
    # Handle None values in files dict - convert None to empty string
    sample_content = "\n".join((v or '') for v in list(all_files.values())[:30])
    sample_content_lower = sample_content.lower()

    # ============= JAVASCRIPT/TYPESCRIPT =============
    # React
    if any(".jsx" in f or ".tsx" in f for f in file_names) or "import React" in sample_content:
        stack_parts.append("React")

    # Next.js
    if any("next.config" in f for f in file_names) or "from 'next" in sample_content:
        stack_parts.append("Next.js")

    # Vite
    if any("vite.config" in f for f in file_names):
        stack_parts.append("Vite")

    # Vue
    if any(".vue" in f for f in file_names):
        stack_parts.append("Vue")
        if "nuxt.config" in str(file_names_lower):
            stack_parts.append("Nuxt.js")

    # Svelte
    if any(".svelte" in f for f in file_names):
        stack_parts.append("Svelte")
        if "svelte.config" in str(file_names_lower):
            stack_parts.append("SvelteKit")

    # Angular
    if any("angular.json" in f for f in file_names) or "@angular" in sample_content:
        stack_parts.append("Angular")

    # TypeScript
    if any(".ts" in f or ".tsx" in f for f in file_names) or any("tsconfig" in f for f in file_names):
        stack_parts.append("TypeScript")

    # Node.js/Express
    if any("package.json" in f for f in file_names):
        stack_parts.append("Node.js")
        if "express" in sample_content_lower:
            stack_parts.append("Express")
        if "nestjs" in sample_content_lower or "@nestjs" in sample_content:
            stack_parts.append("NestJS")

    # ============= PYTHON =============
    if any(".py" in f for f in file_names):
        stack_parts.append("Python")
        if "fastapi" in sample_content_lower:
            stack_parts.append("FastAPI")
        if "django" in sample_content_lower:
            stack_parts.append("Django")
        if "flask" in sample_content_lower:
            stack_parts.append("Flask")
        if "streamlit" in sample_content_lower:
            stack_parts.append("Streamlit")
        if "pandas" in sample_content_lower:
            stack_parts.append("Pandas")
        if "pytorch" in sample_content_lower or "torch" in sample_content_lower:
            stack_parts.append("PyTorch")
        if "tensorflow" in sample_content_lower:
            stack_parts.append("TensorFlow")

    # ============= GO =============
    if any(".go" in f for f in file_names) or any("go.mod" in f for f in file_names):
        stack_parts.append("Go")
        if "gin-gonic" in sample_content_lower or "gin." in sample_content_lower:
            stack_parts.append("Gin")
        if "fiber" in sample_content_lower:
            stack_parts.append("Fiber")
        if "echo" in sample_content_lower:
            stack_parts.append("Echo")

    # ============= RUST =============
    if any(".rs" in f for f in file_names) or any("cargo.toml" in f.lower() for f in file_names):
        stack_parts.append("Rust")
        if "actix" in sample_content_lower:
            stack_parts.append("Actix")
        if "rocket" in sample_content_lower:
            stack_parts.append("Rocket")
        if "tokio" in sample_content_lower:
            stack_parts.append("Tokio")

    # ============= JAVA/KOTLIN =============
    if any(".java" in f for f in file_names):
        stack_parts.append("Java")
        if "spring" in sample_content_lower:
            stack_parts.append("Spring Boot")
        if "quarkus" in sample_content_lower:
            stack_parts.append("Quarkus")

    if any(".kt" in f for f in file_names):
        stack_parts.append("Kotlin")
        if "ktor" in sample_content_lower:
            stack_parts.append("Ktor")

    # ============= C#/.NET =============
    if any(".cs" in f for f in file_names) or any(".csproj" in f for f in file_names):
        stack_parts.append("C#")
        if "aspnetcore" in sample_content_lower or "microsoft.aspnetcore" in sample_content_lower:
            stack_parts.append("ASP.NET Core")
        if "blazor" in sample_content_lower:
            stack_parts.append("Blazor")

    # ============= RUBY =============
    if any(".rb" in f for f in file_names) or any("gemfile" in f.lower() for f in file_names):
        stack_parts.append("Ruby")
        if "rails" in sample_content_lower or any("config/routes.rb" in f for f in file_names):
            stack_parts.append("Rails")
        if "sinatra" in sample_content_lower:
            stack_parts.append("Sinatra")

    # ============= PHP =============
    if any(".php" in f for f in file_names):
        stack_parts.append("PHP")
        if "laravel" in sample_content_lower or any("artisan" in f for f in file_names):
            stack_parts.append("Laravel")
        if "symfony" in sample_content_lower:
            stack_parts.append("Symfony")

    # ============= ELIXIR =============
    if any(".ex" in f or ".exs" in f for f in file_names):
        stack_parts.append("Elixir")
        if "phoenix" in sample_content_lower:
            stack_parts.append("Phoenix")

    # ============= SWIFT =============
    if any(".swift" in f for f in file_names):
        stack_parts.append("Swift")
        if "swiftui" in sample_content_lower:
            stack_parts.append("SwiftUI")
        if "vapor" in sample_content_lower:
            stack_parts.append("Vapor")

    # ============= CSS FRAMEWORKS =============
    if "tailwind" in sample_content_lower or any("tailwind.config" in f for f in file_names):
        stack_parts.append("Tailwind CSS")
    if "bootstrap" in sample_content_lower:
        stack_parts.append("Bootstrap")
    if "sass" in sample_content_lower or any(".scss" in f for f in file_names):
        stack_parts.append("Sass")

    # ============= DATABASES =============
    if "postgresql" in sample_content_lower or "psycopg" in sample_content_lower:
        stack_parts.append("PostgreSQL")
    if "mongodb" in sample_content_lower or "mongoose" in sample_content_lower:
        stack_parts.append("MongoDB")
    if "mysql" in sample_content_lower:
        stack_parts.append("MySQL")
    if "redis" in sample_content_lower:
        stack_parts.append("Redis")
    if "prisma" in sample_content_lower:
        stack_parts.append("Prisma")
    if "sqlalchemy" in sample_content_lower:
        stack_parts.append("SQLAlchemy")

    # ============= DOCKER/INFRASTRUCTURE =============
    if any("dockerfile" in f.lower() for f in file_names) or any("docker-compose" in f.lower() for f in file_names):
        stack_parts.append("Docker")
    if any("kubernetes" in f.lower() or "k8s" in f.lower() for f in file_names):
        stack_parts.append("Kubernetes")

    return ", ".join(stack_parts) if stack_parts else "Unknown"


def apply_unified_patch(original: str, patch: str) -> Optional[str]:
    """
    Apply unified diff patch to original content.

    Returns patched content or None if patch failed.
    """
    # SAFETY: Handle None or empty inputs
    if original is None:
        original = ""
    if patch is None or not isinstance(patch, str):
        logger.warning("[FixExecutor] apply_unified_patch received None or non-string patch")
        return None

    try:
        lines = original.split('\n')
        result_lines = lines.copy()

        # Parse hunks from patch
        hunk_pattern = r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@'

        current_pos = 0
        offset = 0  # Track line number offset from previous hunks

        for hunk_match in re.finditer(hunk_pattern, patch):
            old_start = int(hunk_match.group(1))
            old_count = int(hunk_match.group(2) or 1)
            new_start = int(hunk_match.group(3))
            new_count = int(hunk_match.group(4) or 1)

            # Get hunk content (lines after @@ until next @@ or end)
            hunk_start = hunk_match.end()
            next_hunk = re.search(hunk_pattern, patch[hunk_start:])
            if next_hunk:
                hunk_end = hunk_start + next_hunk.start()
            else:
                hunk_end = len(patch)

            hunk_content = patch[hunk_start:hunk_end].strip()
            hunk_lines = hunk_content.split('\n')

            # Apply hunk
            new_lines = []
            old_line_idx = old_start - 1 + offset

            for line in hunk_lines:
                if not line:
                    continue
                prefix = line[0] if line else ' '
                content = line[1:] if len(line) > 1 else ''

                if prefix == ' ':
                    # Context line - keep
                    new_lines.append(content)
                elif prefix == '-':
                    # Remove line - skip
                    pass
                elif prefix == '+':
                    # Add line
                    new_lines.append(content)

            # Replace old lines with new lines
            actual_start = old_start - 1 + offset
            actual_end = actual_start + old_count

            # Ensure indices are valid
            actual_start = max(0, min(actual_start, len(result_lines)))
            actual_end = max(actual_start, min(actual_end, len(result_lines)))

            result_lines = result_lines[:actual_start] + new_lines + result_lines[actual_end:]

            # Update offset for next hunk
            offset += len(new_lines) - old_count

        return '\n'.join(result_lines)

    except Exception as e:
        logger.error(f"[FixExecutor] Patch application failed: {e}")
        return None


# ============= EXECUTE INSTALL COMMANDS =============
# Allowed commands for security (only npm/pip install)
ALLOWED_INSTALL_COMMANDS = [
    "npm install",
    "npm i",
    "pip install",
    "pip3 install",
    "yarn add",
    "pnpm add",
]


async def execute_install_command(project_path: Path, command: str) -> bool:
    """
    Execute install commands (npm install, pip install) in the project directory.

    Security: Only allows whitelisted install commands to prevent arbitrary code execution.

    Args:
        project_path: Path to the project directory
        command: Command to execute (e.g., "npm install @tailwindcss/forms")

    Returns:
        True if command executed successfully, False otherwise
    """
    if not command or not isinstance(command, str):
        return False

    command = command.strip()

    # Security: Only allow whitelisted install commands
    is_allowed = False
    for allowed_cmd in ALLOWED_INSTALL_COMMANDS:
        if command.startswith(allowed_cmd):
            is_allowed = True
            break

    if not is_allowed:
        logger.warning(f"[FixExecutor] Blocked unsafe command: {command}")
        return False

    # Determine the correct working directory
    # For monorepo projects, install in the appropriate subfolder
    work_dir = project_path

    # Check if command is for frontend dependencies (common patterns)
    if any(pkg in command for pkg in ["@tailwindcss", "react", "vite", "tailwind", "postcss", "autoprefixer"]):
        frontend_path = project_path / "frontend"
        if frontend_path.exists() and (frontend_path / "package.json").exists():
            work_dir = frontend_path
            logger.info(f"[FixExecutor] Running npm install in frontend/ folder")

    # For backend dependencies
    if any(pkg in command for pkg in ["fastapi", "uvicorn", "sqlalchemy", "pydantic"]):
        backend_path = project_path / "backend"
        if backend_path.exists() and (backend_path / "requirements.txt").exists():
            work_dir = backend_path

    logger.info(f"[FixExecutor] Executing command: {command} in {work_dir}")

    try:
        # Run the command asynchronously
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=str(work_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)

        if process.returncode == 0:
            logger.info(f"[FixExecutor] ✅ Command succeeded: {command}")
            if stdout:
                logger.debug(f"[FixExecutor] stdout: {stdout.decode()[:500]}")
            return True
        else:
            logger.error(f"[FixExecutor] ❌ Command failed (exit {process.returncode}): {command}")
            if stderr:
                logger.error(f"[FixExecutor] stderr: {stderr.decode()[:500]}")
            return False

    except asyncio.TimeoutError:
        logger.error(f"[FixExecutor] ⏱️ Command timed out after 120s: {command}")
        return False
    except Exception as e:
        logger.error(f"[FixExecutor] ❌ Command execution failed: {e}")
        return False


# ============= MODULE-LEVEL ALIAS =============
# This alias is used by main.py to register the auto-fix callback
# AutoFixer calls: fix_callback(project_id, log_payload)
execute_fix = execute_fix_internal
