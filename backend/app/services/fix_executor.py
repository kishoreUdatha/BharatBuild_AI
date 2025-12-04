"""
Fix Executor Service - Executes fixes via Fixer Agent (Bolt.new style)

This is the callback that AutoFixer uses to actually fix errors.
It calls the Fixer Agent, parses patches, applies them, and restarts the project.

Full flow:
1. Build fixer payload (logs + files + tech stack)
2. Call Fixer Agent (Claude)
3. Parse <patch> blocks
4. Apply patches to files
5. Restart Docker/Preview
6. Notify clients
"""

import re
from typing import Dict, Any, List, Optional

from app.core.logging_config import logger
from app.modules.agents.fixer_agent import FixerAgent
from app.services.unified_storage import UnifiedStorageService as UnifiedStorageManager
from app.services.restart_manager import restart_project


async def execute_fix(project_id: str, log_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute fix using Fixer Agent.

    This is the callback function for AutoFixer.
    Called automatically when errors are detected!

    Args:
        project_id: Project ID
        log_payload: LogBus payload containing all errors

    Returns:
        Result dict with success status and applied patches
    """
    logger.info(f"[FixExecutor:{project_id}] Starting automatic fix")

    try:
        # Get storage manager
        storage = UnifiedStorageManager()

        # Get project files for context
        project_files = {}
        try:
            file_list = await storage.list_sandbox_files(project_id)
            error_files = log_payload.get("error_files", [])

            # Read files mentioned in errors + key files
            key_patterns = ["*.jsx", "*.tsx", "*.js", "*.ts", "*.py", "*.css"]
            files_to_read = set(error_files)

            for pattern in key_patterns:
                matching = [f for f in file_list if f.endswith(pattern.replace("*", ""))]
                files_to_read.update(matching[:10])  # Limit per pattern

            for file_path in list(files_to_read)[:20]:  # Max 20 files
                try:
                    content = await storage.read_from_sandbox(project_id, file_path)
                    if content:
                        project_files[file_path] = content
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"[FixExecutor:{project_id}] Failed to read files: {e}")

        # Build error description from log payload
        error_description = build_error_description(log_payload)

        if not error_description:
            return {
                "success": False,
                "error": "No errors to fix",
                "patches_applied": 0,
                "files_modified": []
            }

        # Initialize Fixer Agent
        fixer = FixerAgent()

        # Build context for fixer
        file_context = {
            "files": project_files,
            "file_tree": list(project_files.keys()),
            "tech_stack": detect_tech_stack(project_files),
            "log_payload": log_payload
        }

        # Call Fixer Agent
        logger.info(f"[FixExecutor:{project_id}] Calling Fixer Agent with {len(project_files)} files")

        result = await fixer.fix_error(
            error={"description": error_description, "source": "auto-fix"},
            project_id=project_id,
            file_context=file_context
        )

        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "Fixer Agent failed"),
                "patches_applied": 0,
                "files_modified": []
            }

        # Parse and apply patches
        patches = result.get("patches", [])
        if not patches:
            # Try to extract patches from response
            response_text = result.get("response", "")
            patches = parse_patches(response_text)

        if not patches:
            return {
                "success": False,
                "error": "No patches generated",
                "patches_applied": 0,
                "files_modified": []
            }

        # Apply patches
        files_modified = []
        patches_applied = 0

        for patch in patches:
            file_path = patch.get("file")
            patch_content = patch.get("content")

            if not file_path or not patch_content:
                continue

            try:
                # Read current file content
                current_content = project_files.get(file_path)
                if current_content is None:
                    try:
                        current_content = await storage.read_from_sandbox(project_id, file_path)
                    except Exception:
                        current_content = ""

                # Apply patch
                new_content = apply_unified_patch(current_content or "", patch_content)

                if new_content and new_content != current_content:
                    # Save patched file
                    await storage.save_to_sandbox(project_id, file_path, new_content)
                    files_modified.append(file_path)
                    patches_applied += 1
                    logger.info(f"[FixExecutor:{project_id}] Applied patch to {file_path}")

            except Exception as e:
                logger.error(f"[FixExecutor:{project_id}] Failed to apply patch to {file_path}: {e}")

        # ========== STEP 5: RESTART PROJECT (Bolt.new style) ==========
        # After patches are applied, restart Docker/Preview so changes take effect
        if patches_applied > 0:
            logger.info(f"[FixExecutor:{project_id}] Restarting project after {patches_applied} patches")
            try:
                restart_result = await restart_project(
                    project_id,
                    restart_docker=True,
                    restart_preview=True,
                    notify_clients=True
                )
                logger.info(f"[FixExecutor:{project_id}] Restart result: {restart_result}")
            except Exception as e:
                logger.warning(f"[FixExecutor:{project_id}] Restart failed (patches still applied): {e}")

        return {
            "success": patches_applied > 0,
            "patches_applied": patches_applied,
            "files_modified": files_modified,
            "error": None if patches_applied > 0 else "No patches could be applied"
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
    """Build error description from LogBus payload"""
    parts = []

    # Browser errors
    for error in log_payload.get("browser_errors", [])[:5]:
        msg = error.get("message", "")
        file = error.get("file", "")
        line = error.get("line", "")
        parts.append(f"Browser Error: {msg}")
        if file:
            parts.append(f"  Location: {file}:{line}")
        if error.get("stack"):
            parts.append(f"  Stack: {error['stack'][:300]}")

    # Build errors
    for error in log_payload.get("build_errors", [])[:5]:
        msg = error.get("message", "")
        parts.append(f"Build Error: {msg}")

    # Backend errors
    for error in log_payload.get("backend_errors", [])[:3]:
        msg = error.get("message", "")
        parts.append(f"Backend Error: {msg}")

    # Docker errors
    for error in log_payload.get("docker_errors", [])[:2]:
        msg = error.get("message", "")
        parts.append(f"Docker Error: {msg}")

    # Network errors (less common to fix)
    for error in log_payload.get("network_errors", [])[:2]:
        msg = error.get("message", "")
        url = error.get("url", "")
        parts.append(f"Network Error: {msg} (URL: {url})")

    return "\n".join(parts)


def detect_tech_stack(files: Dict[str, str]) -> str:
    """Detect tech stack from file contents"""
    stack_parts = []

    file_names = list(files.keys())
    all_content = "\n".join(files.values())

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


def apply_unified_patch(original: str, patch: str) -> Optional[str]:
    """
    Apply unified diff patch to original content.

    Returns patched content or None if patch failed.
    """
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
