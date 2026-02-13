"""
Team Code Merger Service

Handles merging code from team member workspaces into the main project.
Implements 3-way merge algorithm:
- Base: Original state when member branched
- Member: Member's current changes
- Main: Current main project state

Features:
- Auto-merge for non-conflicting changes
- Conflict detection with markers
- AI-assisted conflict resolution
- Merge history tracking
"""

import difflib
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.core.logging_config import logger
from app.models.team import Team, TeamMember
from app.schemas.team import (
    MergeResponse, MergeResolveResponse, FileConflict, ConflictResolution
)


# Store merge state for multi-step conflict resolution
_pending_merges: Dict[str, Dict[str, Any]] = {}


def _compute_hash(content: str) -> str:
    """Compute hash of file content"""
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def _split_lines(content: str) -> List[str]:
    """Split content into lines, preserving line endings"""
    if not content:
        return []
    lines = content.splitlines(keepends=True)
    # Ensure last line has newline for consistency
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'
    return lines


def _three_way_merge(
    base: str,
    member: str,
    main: str
) -> Tuple[str, List[Tuple[int, str, str, str]]]:
    """
    Perform 3-way merge of content.

    Args:
        base: Original content when member started
        member: Member's current content
        main: Current main branch content

    Returns:
        Tuple of (merged_content, conflicts)
        where conflicts is list of (line_num, base_chunk, member_chunk, main_chunk)
    """
    base_lines = _split_lines(base)
    member_lines = _split_lines(member)
    main_lines = _split_lines(main)

    # If member didn't change from base, use main
    if base_lines == member_lines:
        return main, []

    # If main didn't change from base, use member
    if base_lines == main_lines:
        return member, []

    # Both changed - need to merge
    # Use difflib to find changes
    base_to_member = list(difflib.ndiff(base_lines, member_lines))
    base_to_main = list(difflib.ndiff(base_lines, main_lines))

    # Simple merge strategy: try to combine changes
    merged_lines = []
    conflicts = []

    # Get unified diff for member and main
    member_changes = set()
    main_changes = set()

    # Track which lines each branch modified
    line_idx = 0
    for diff in difflib.ndiff(base_lines, member_lines):
        if diff.startswith('  '):
            line_idx += 1
        elif diff.startswith('- '):
            member_changes.add(line_idx)
            line_idx += 1
        elif diff.startswith('+ '):
            member_changes.add(line_idx)

    line_idx = 0
    for diff in difflib.ndiff(base_lines, main_lines):
        if diff.startswith('  '):
            line_idx += 1
        elif diff.startswith('- '):
            main_changes.add(line_idx)
            line_idx += 1
        elif diff.startswith('+ '):
            main_changes.add(line_idx)

    # Check for overlapping changes
    overlap = member_changes & main_changes

    if not overlap:
        # No overlapping changes - can auto-merge
        # Apply member changes to main
        # Use a sequence matcher for better merging
        matcher = difflib.SequenceMatcher(None, base_lines, member_lines)
        result_lines = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Check if main modified these lines
                for idx in range(i1, i2):
                    if idx < len(main_lines) and main_lines[idx] != base_lines[idx]:
                        result_lines.append(main_lines[idx])
                    else:
                        result_lines.append(base_lines[idx])
            elif tag == 'replace' or tag == 'insert':
                # Member's changes
                result_lines.extend(member_lines[j1:j2])
            # 'delete' - lines removed by member, don't include

        return ''.join(result_lines), []

    else:
        # Overlapping changes - has conflicts
        # Create conflict markers
        conflict_regions = []

        # Use SequenceMatcher on all three versions
        # For now, use a simpler approach: if there's overlap, the whole file is a conflict
        conflict_content = []
        conflict_content.append("<<<<<<< MAIN\n")
        conflict_content.extend(main_lines)
        conflict_content.append("=======\n")
        conflict_content.extend(member_lines)
        conflict_content.append(">>>>>>> MEMBER\n")

        conflicts.append((1, base, member, main))

        return ''.join(conflict_content), conflicts


async def get_member_files(
    team: Team,
    member: TeamMember,
    file_paths: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Get files from a member's workspace.

    In a full implementation, this would read from the member's
    isolated sandbox/branch. For now, we use a simplified approach.
    """
    # Import storage service
    from app.services.unified_storage import unified_storage

    member_files = {}

    # Get all files from member's workspace
    project_id = str(team.project_id)
    user_id = str(member.user_id)

    # If specific paths requested, only get those
    if file_paths:
        for path in file_paths:
            content = await unified_storage.read_from_sandbox(
                project_id=project_id,
                file_path=path,
                user_id=user_id
            )
            if content:
                member_files[path] = content
    else:
        # Get all files - would need to list files in sandbox
        # For now, this is a placeholder
        pass

    return member_files


async def get_main_files(
    team: Team,
    file_paths: List[str]
) -> Dict[str, str]:
    """Get files from the main project"""
    from app.services.unified_storage import unified_storage

    main_files = {}
    project_id = str(team.project_id)

    for path in file_paths:
        content = await unified_storage.read_from_sandbox(
            project_id=project_id,
            file_path=path,
            user_id=str(team.created_by)  # Leader's workspace is main
        )
        if content:
            main_files[path] = content

    return main_files


async def get_base_files(
    team: Team,
    member: TeamMember,
    file_paths: List[str]
) -> Dict[str, str]:
    """
    Get base version of files (when member started).

    In a full implementation, this would use git or snapshots.
    For now, we'll use a simplified approach where base = main.
    """
    # For MVP, assume base is the same as main
    # A full implementation would track snapshots per member
    return await get_main_files(team, file_paths)


async def merge_member_changes(
    team: Team,
    member: TeamMember,
    file_paths: Optional[List[str]] = None,
    commit_message: Optional[str] = None
) -> MergeResponse:
    """
    Merge a member's changes into the main project.

    Args:
        team: The team
        member: Team member whose changes to merge
        file_paths: Specific files to merge (None = all changed files)
        commit_message: Optional commit message

    Returns:
        MergeResponse with merge results
    """
    from app.services.unified_storage import unified_storage

    project_id = str(team.project_id)
    leader_id = str(team.created_by)

    try:
        # Get member's files
        member_files = await get_member_files(team, member, file_paths)

        if not member_files:
            return MergeResponse(
                success=False,
                merged_files=[],
                conflicts=[],
                auto_resolved=[],
                message="No files found in member's workspace"
            )

        # Get main and base files
        file_list = list(member_files.keys())
        main_files = await get_main_files(team, file_list)
        base_files = await get_base_files(team, member, file_list)

        merged_files = []
        conflicts = []
        auto_resolved = []

        for path in file_list:
            member_content = member_files.get(path, "")
            main_content = main_files.get(path, "")
            base_content = base_files.get(path, "")

            # Check if file is new (not in main)
            if not main_content and member_content:
                # New file - just add it
                await unified_storage.write_to_sandbox(
                    project_id=project_id,
                    file_path=path,
                    content=member_content,
                    user_id=leader_id
                )
                merged_files.append(path)
                continue

            # Check if file was deleted by member
            if main_content and not member_content:
                # For now, skip deleted files - could add as conflict
                continue

            # Both have the file - merge
            if member_content == main_content:
                # No changes needed
                continue

            # Perform 3-way merge
            merged_content, file_conflicts = _three_way_merge(
                base_content,
                member_content,
                main_content
            )

            if file_conflicts:
                # Has conflicts
                conflicts.append(FileConflict(
                    file_path=path,
                    conflict_type="content",
                    base_content=base_content,
                    member_content=member_content,
                    main_content=main_content,
                    conflict_markers=merged_content
                ))
            else:
                # Auto-merged successfully
                await unified_storage.write_to_sandbox(
                    project_id=project_id,
                    file_path=path,
                    content=merged_content,
                    user_id=leader_id
                )
                auto_resolved.append(path)
                merged_files.append(path)

        # Store pending merge state if there are conflicts
        if conflicts:
            merge_id = f"{team.id}-{member.id}-{datetime.utcnow().timestamp()}"
            _pending_merges[merge_id] = {
                "team_id": str(team.id),
                "member_id": str(member.id),
                "conflicts": conflicts,
                "commit_message": commit_message
            }

        success = len(conflicts) == 0
        message = "Merge completed successfully" if success else f"{len(conflicts)} file(s) have conflicts"

        logger.info(f"Merge for team {team.id}: {len(merged_files)} merged, "
                   f"{len(auto_resolved)} auto-resolved, {len(conflicts)} conflicts")

        return MergeResponse(
            success=success,
            merged_files=merged_files,
            conflicts=conflicts,
            auto_resolved=auto_resolved,
            message=message
        )

    except Exception as e:
        logger.error(f"Error merging member changes: {e}", exc_info=True)
        return MergeResponse(
            success=False,
            merged_files=[],
            conflicts=[],
            auto_resolved=[],
            message=f"Merge failed: {str(e)}"
        )


async def resolve_conflicts(
    team: Team,
    resolutions: List[ConflictResolution]
) -> MergeResolveResponse:
    """
    Resolve merge conflicts using provided resolutions.

    Args:
        team: The team
        resolutions: List of conflict resolutions

    Returns:
        MergeResolveResponse with resolution results
    """
    from app.services.unified_storage import unified_storage

    project_id = str(team.project_id)
    leader_id = str(team.created_by)

    resolved_files = []
    remaining_conflicts = []

    try:
        for resolution in resolutions:
            path = resolution.file_path

            if resolution.resolution == "keep_main":
                # Keep main version - nothing to do, it's already there
                resolved_files.append(path)

            elif resolution.resolution == "keep_member":
                # Use member's version - need to get it from pending merge state
                # For now, we'll need the member content passed in
                # This is a limitation - in production, store conflict state
                if resolution.merged_content:
                    # Assume merged_content contains member version
                    await unified_storage.write_to_sandbox(
                        project_id=project_id,
                        file_path=path,
                        content=resolution.merged_content,
                        user_id=leader_id
                    )
                    resolved_files.append(path)
                else:
                    remaining_conflicts.append(path)

            elif resolution.resolution == "merged_content":
                if resolution.merged_content:
                    await unified_storage.write_to_sandbox(
                        project_id=project_id,
                        file_path=path,
                        content=resolution.merged_content,
                        user_id=leader_id
                    )
                    resolved_files.append(path)
                else:
                    remaining_conflicts.append(path)

            else:
                remaining_conflicts.append(path)

        success = len(remaining_conflicts) == 0
        message = "All conflicts resolved" if success else f"{len(remaining_conflicts)} conflicts remaining"

        logger.info(f"Resolved {len(resolved_files)} conflicts for team {team.id}")

        return MergeResolveResponse(
            success=success,
            resolved_files=resolved_files,
            remaining_conflicts=remaining_conflicts,
            message=message
        )

    except Exception as e:
        logger.error(f"Error resolving conflicts: {e}", exc_info=True)
        return MergeResolveResponse(
            success=False,
            resolved_files=[],
            remaining_conflicts=[r.file_path for r in resolutions],
            message=f"Resolution failed: {str(e)}"
        )


async def ai_resolve_conflict(
    base_content: str,
    member_content: str,
    main_content: str,
    file_path: str
) -> Optional[str]:
    """
    Use AI to intelligently resolve a merge conflict.

    Analyzes both versions and attempts to create a merged version
    that preserves the intent of both changes.
    """
    from anthropic import AsyncAnthropic
    from app.core.config import settings

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = f"""You are a code merging assistant. Two developers made changes to the same file and there's a conflict.

FILE: {file_path}

BASE VERSION (original):
```
{base_content}
```

MEMBER VERSION (their changes):
```
{member_content}
```

MAIN VERSION (current):
```
{main_content}
```

Please analyze both sets of changes and create a merged version that:
1. Preserves the intent of both changes
2. Resolves any conflicts intelligently
3. Maintains code correctness
4. Keeps consistent style

Return ONLY the merged code, no explanations. If you cannot merge cleanly, return the main version with a TODO comment noting the conflict."""

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        merged = response.content[0].text

        # Strip any markdown code blocks
        if "```" in merged:
            # Extract content between code blocks
            parts = merged.split("```")
            if len(parts) >= 3:
                # Skip language identifier if present
                code_part = parts[1]
                if code_part.startswith(("python", "javascript", "typescript", "java", "go", "rust")):
                    code_part = "\n".join(code_part.split("\n")[1:])
                merged = code_part.strip()

        return merged

    except Exception as e:
        logger.error(f"AI conflict resolution failed: {e}")
        return None
