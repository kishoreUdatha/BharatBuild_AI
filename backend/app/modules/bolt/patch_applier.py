"""
Unified Diff Patch Applier
Applies Git-style patches to files (Python backend version)
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DiffHunk:
    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    changes: List[Dict[str, str]]


@dataclass
class ParsedDiff:
    old_file: str
    new_file: str
    hunks: List[DiffHunk]


def parse_unified_diff(patch: str) -> ParsedDiff:
    """Parse a unified diff patch"""
    lines = patch.strip().split('\n')

    diff = ParsedDiff(old_file="", new_file="", hunks=[])

    current_hunk = None
    i = 0

    while i < len(lines):
        line = lines[i]

        # Parse file headers
        if line.startswith('--- '):
            diff.old_file = line[4:].strip().replace('a/', '')
        elif line.startswith('+++ '):
            diff.new_file = line[4:].strip().replace('b/', '')

        # Parse hunk header
        elif line.startswith('@@'):
            # @@ -10,3 +10,7 @@
            match = re.search(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
            if match:
                old_start = int(match.group(1))
                old_lines = int(match.group(2)) if match.group(2) else 1
                new_start = int(match.group(3))
                new_lines = int(match.group(4)) if match.group(4) else 1

                if current_hunk:
                    diff.hunks.append(current_hunk)

                current_hunk = DiffHunk(
                    old_start=old_start,
                    old_lines=old_lines,
                    new_start=new_start,
                    new_lines=new_lines,
                    changes=[]
                )

        # Parse changes
        elif current_hunk is not None:
            if line.startswith('+') and not line.startswith('+++'):
                current_hunk.changes.append({
                    'type': 'add',
                    'content': line[1:]
                })
            elif line.startswith('-') and not line.startswith('---'):
                current_hunk.changes.append({
                    'type': 'remove',
                    'content': line[1:]
                })
            elif line.startswith(' '):
                current_hunk.changes.append({
                    'type': 'context',
                    'content': line[1:]
                })

        i += 1

    # Add last hunk
    if current_hunk:
        diff.hunks.append(current_hunk)

    return diff


def apply_unified_patch(
    original_content: str,
    patch: str
) -> Dict:
    """
    Apply a unified diff patch to original content

    Args:
        original_content: Original file content
        patch: Unified diff patch

    Returns:
        Dict with success, new_content, error, conflicts
    """
    try:
        diff = parse_unified_diff(patch)
        lines = original_content.split('\n')

        # Apply each hunk
        for hunk in diff.hunks:
            result = _apply_hunk(lines, hunk)
            if not result['success']:
                return result

        return {
            'success': True,
            'new_content': '\n'.join(lines),
            'error': None,
            'conflicts': None
        }

    except Exception as e:
        return {
            'success': False,
            'new_content': None,
            'error': f"Failed to apply patch: {str(e)}",
            'conflicts': None
        }


def _apply_hunk(lines: List[str], hunk: DiffHunk) -> Dict:
    """Apply a single hunk to the lines array"""
    # Convert to 0-based index
    current_line = hunk.old_start - 1
    original_lines = lines.copy()

    try:
        for change in hunk.changes:
            change_type = change['type']
            content = change['content']

            if change_type == 'context':
                # Verify context line matches
                if current_line >= len(lines):
                    return {
                        'success': False,
                        'error': f"Context mismatch at line {current_line + 1}: exceeded file length",
                        'conflicts': [
                            f"Line {current_line + 1}",
                            "File is shorter than expected"
                        ]
                    }

                if lines[current_line] != content:
                    return {
                        'success': False,
                        'error': f"Context mismatch at line {current_line + 1}. Expected: \"{content}\", Got: \"{lines[current_line]}\"",
                        'conflicts': [
                            f"Line {current_line + 1}",
                            f"Expected: {content}",
                            f"Got: {lines[current_line]}"
                        ]
                    }
                current_line += 1

            elif change_type == 'remove':
                # Verify line to remove matches
                if current_line >= len(lines):
                    return {
                        'success': False,
                        'error': f"Cannot remove line {current_line + 1}: exceeded file length",
                        'conflicts': [
                            f"Line {current_line + 1}",
                            "File is shorter than expected"
                        ]
                    }

                if lines[current_line] != content:
                    return {
                        'success': False,
                        'error': f"Cannot remove line {current_line + 1}. Content mismatch.",
                        'conflicts': [
                            f"Line {current_line + 1}",
                            f"Expected to remove: {content}",
                            f"Got: {lines[current_line]}"
                        ]
                    }
                # Remove the line
                lines.pop(current_line)

            elif change_type == 'add':
                # Insert new line
                lines.insert(current_line, content)
                current_line += 1

        return {'success': True}

    except Exception as e:
        # Restore original lines on error
        lines.clear()
        lines.extend(original_lines)

        return {
            'success': False,
            'error': f"Hunk application failed: {str(e)}"
        }


def apply_patch_fuzzy(
    original_content: str,
    patch: str,
    fuzziness: int = 2
) -> Dict:
    """
    Apply patch with fuzzy matching

    Args:
        original_content: Original file content
        patch: Unified diff patch
        fuzziness: Number of lines to search around the specified location

    Returns:
        Dict with success, new_content, error, conflicts
    """
    # Try exact match first
    result = apply_unified_patch(original_content, patch)
    if result['success']:
        return result

    # Try fuzzy matching
    try:
        diff = parse_unified_diff(patch)
        lines = original_content.split('\n')

        for hunk in diff.hunks:
            # Try exact match
            result = _apply_hunk(lines.copy(), hunk)

            if not result['success']:
                # Try fuzzy matching with offset
                found = False
                for offset in range(-fuzziness, fuzziness + 1):
                    if offset == 0:
                        continue

                    modified_hunk = DiffHunk(
                        old_start=hunk.old_start + offset,
                        old_lines=hunk.old_lines,
                        new_start=hunk.new_start + offset,
                        new_lines=hunk.new_lines,
                        changes=hunk.changes
                    )

                    result = _apply_hunk(lines.copy(), modified_hunk)
                    if result['success']:
                        _apply_hunk(lines, modified_hunk)
                        found = True
                        break

                if not found:
                    return {
                        'success': False,
                        'error': f"Could not find matching context for hunk (tried fuzziness: {fuzziness})",
                        'new_content': None,
                        'conflicts': None
                    }

        return {
            'success': True,
            'new_content': '\n'.join(lines),
            'error': None,
            'conflicts': None
        }

    except Exception as e:
        return {
            'success': False,
            'new_content': None,
            'error': f"Fuzzy patch failed: {str(e)}",
            'conflicts': None
        }


def reverse_patch(patch: str) -> str:
    """Create a reverse patch for undo operations"""
    lines = patch.strip().split('\n')
    reversed_lines = []

    for line in lines:
        if line.startswith('+++'):
            # Swap +++ and ---
            reversed_lines.append(line.replace('+++', '---', 1))
        elif line.startswith('---'):
            reversed_lines.append(line.replace('---', '+++', 1))
        elif line.startswith('+') and not line.startswith('+++'):
            # + becomes -
            reversed_lines.append('-' + line[1:])
        elif line.startswith('-') and not line.startswith('---'):
            # - becomes +
            reversed_lines.append('+' + line[1:])
        else:
            # Context lines and headers remain the same
            reversed_lines.append(line)

    return '\n'.join(reversed_lines)


def preview_patch(original_content: str, patch: str) -> Dict:
    """
    Preview patch changes without applying

    Returns:
        Dict with additions, deletions, changes
    """
    try:
        diff = parse_unified_diff(patch)

        additions = 0
        deletions = 0
        changes = []

        for hunk in diff.hunks:
            line_num = hunk.new_start

            for change in hunk.changes:
                if change['type'] == 'add':
                    additions += 1
                    changes.append({
                        'line': line_num,
                        'type': 'add',
                        'content': change['content']
                    })
                    line_num += 1
                elif change['type'] == 'remove':
                    deletions += 1
                    changes.append({
                        'line': line_num,
                        'type': 'remove',
                        'content': change['content']
                    })
                else:
                    line_num += 1

        return {
            'additions': additions,
            'deletions': deletions,
            'changes': changes
        }

    except Exception as e:
        return {
            'additions': 0,
            'deletions': 0,
            'changes': [],
            'error': str(e)
        }
