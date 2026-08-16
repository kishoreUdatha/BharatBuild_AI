"""
Kiro-style Patch Applier - Surgical strReplace operations

Instead of replacing entire files, this applies precise text replacements.
Each patch specifies: file_path, old_str (to find), new_str (to replace with).

Benefits:
- Less tokens (only changed lines, not entire file)
- More precise (won't break working code)
- Faster (smaller AI response)
- Verifiable (can check if old_str exists before applying)
"""

from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PatchResult:
    """Result of applying a single patch"""
    def __init__(self, path: str, success: bool, error: str = ""):
        self.path = path
        self.success = success
        self.error = error


def apply_str_replace(
    file_content: str,
    old_str: str,
    new_str: str
) -> Tuple[bool, str, str]:
    """
    Apply a single strReplace operation on file content.
    
    Args:
        file_content: Current file content
        old_str: Text to find (must match exactly)
        new_str: Text to replace with
    
    Returns:
        (success, new_content, error_message)
    """
    if not old_str:
        return False, file_content, "old_str is empty"
    
    # Check if old_str exists in the file
    if old_str not in file_content:
        # Try with normalized whitespace (common AI issue: extra spaces/tabs)
        normalized_content = ' '.join(file_content.split())
        normalized_old = ' '.join(old_str.split())
        
        if normalized_old in normalized_content:
            # Find the actual text by matching line by line
            old_lines = old_str.strip().split('\n')
            content_lines = file_content.split('\n')
            
            # Try to find a fuzzy match
            for i in range(len(content_lines) - len(old_lines) + 1):
                chunk = '\n'.join(content_lines[i:i + len(old_lines)])
                if chunk.strip() == old_str.strip():
                    # Found it with whitespace differences
                    file_content = file_content.replace(chunk, new_str)
                    return True, file_content, ""
        
        return False, file_content, f"old_str not found in file (first 50 chars: '{old_str[:50]}...')"
    
    # Count occurrences
    count = file_content.count(old_str)
    if count > 1:
        logger.warning(f"[PatchApplier] old_str found {count} times - replacing first occurrence only")
    
    # Apply replacement (first occurrence only)
    new_content = file_content.replace(old_str, new_str, 1)
    
    return True, new_content, ""


def apply_patches(
    patches: List[Dict],
    read_file_fn,
    write_file_fn
) -> List[PatchResult]:
    """
    Apply a list of strReplace patches.
    
    Args:
        patches: List of {path, old_str, new_str} dicts
        read_file_fn: async function(path) -> content
        write_file_fn: async function(path, content) -> bool
    
    Returns:
        List of PatchResult
    """
    results = []
    
    for patch in patches:
        path = patch.get("path", "")
        old_str = patch.get("old_str", "")
        new_str = patch.get("new_str", "")
        
        if not path:
            results.append(PatchResult(path, False, "Missing file path"))
            continue
        
        if not old_str:
            results.append(PatchResult(path, False, "Missing old_str"))
            continue
        
        results.append(PatchResult(path, True))  # Will be updated below
    
    return results


async def apply_patches_async(
    patches: List[Dict],
    project_id: str,
    user_id: str,
    storage
) -> List[PatchResult]:
    """
    Apply strReplace patches using unified storage.
    
    Args:
        patches: List of {path, old_str, new_str} dicts
        project_id: Project ID
        user_id: User ID
        storage: UnifiedStorageService instance
    
    Returns:
        List of PatchResult
    """
    results = []
    
    for patch in patches:
        path = patch.get("path", "")
        old_str = patch.get("old_str", "")
        new_str = patch.get("new_str", "")
        
        if not path or not old_str:
            results.append(PatchResult(path, False, "Missing path or old_str"))
            continue
        
        try:
            # Read current file content
            content = await storage.read_from_sandbox(project_id, path, user_id)
            
            if content is None:
                results.append(PatchResult(path, False, f"File not found: {path}"))
                continue
            
            # Apply the replacement
            success, new_content, error = apply_str_replace(content, old_str, new_str)
            
            if success:
                # Write back
                await storage.write_to_sandbox(project_id, path, new_content, user_id)
                logger.info(f"[PatchApplier] Applied patch to {path}")
                results.append(PatchResult(path, True))
            else:
                logger.warning(f"[PatchApplier] Failed to apply patch to {path}: {error}")
                results.append(PatchResult(path, False, error))
                
        except Exception as e:
            logger.error(f"[PatchApplier] Error applying patch to {path}: {e}")
            results.append(PatchResult(path, False, str(e)))
    
    return results


def parse_str_replace_response(response: str) -> List[Dict]:
    """
    Parse AI response containing strReplace patches.
    
    Expected format:
    <str_replace path="src/App.tsx">
    <old_str>
    import Home from './pages/Home'
    </old_str>
    <new_str>
    import HomePage from './pages/HomePage'
    </new_str>
    </str_replace>
    
    Returns:
        List of {path, old_str, new_str} dicts
    """
    import re
    
    patches = []
    
    # Pattern: <str_replace path="...">...<old_str>...</old_str><new_str>...</new_str></str_replace>
    pattern = r'<str_replace\s+path=["\']([^"\']+)["\']>\s*<old_str>(.*?)</old_str>\s*<new_str>(.*?)</new_str>\s*</str_replace>'
    
    matches = re.findall(pattern, response, re.DOTALL)
    
    for match in matches:
        path, old_str, new_str = match
        # Strip leading/trailing newlines but preserve internal formatting
        old_str = old_str.strip('\n')
        new_str = new_str.strip('\n')
        
        if path and old_str:
            patches.append({
                "path": path.strip(),
                "old_str": old_str,
                "new_str": new_str
            })
    
    if not patches:
        # Try JSON format as fallback
        try:
            import json
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group(0))
                if "patches" in data:
                    for p in data["patches"]:
                        if p.get("path") and p.get("old_str"):
                            patches.append({
                                "path": p["path"],
                                "old_str": p["old_str"],
                                "new_str": p.get("new_str", "")
                            })
        except (json.JSONDecodeError, Exception):
            pass
    
    logger.info(f"[PatchApplier] Parsed {len(patches)} strReplace patches from response")
    return patches
