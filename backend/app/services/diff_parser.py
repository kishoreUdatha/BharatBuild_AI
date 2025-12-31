"""
Diff Parser - Parses and applies unified diffs WITHOUT external tools

No git, no patch command - pure Python implementation.
This runs in the backend, not in the sandbox.

Flow:
1. Claude returns unified diff
2. DiffParser.parse() extracts operations
3. DiffParser.apply() applies to file content
4. Backend writes new content to sandbox
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.core.logging_config import logger


class LineOperation(Enum):
    """Type of operation for a line"""
    ADD = "add"
    DELETE = "delete"
    CONTEXT = "context"


@dataclass
class DiffLine:
    """A single line in a diff hunk"""
    operation: LineOperation
    content: str
    old_line_num: Optional[int] = None
    new_line_num: Optional[int] = None


@dataclass
class DiffHunk:
    """A hunk in a diff (one @@ section)"""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[DiffLine] = field(default_factory=list)


@dataclass
class ParsedDiff:
    """Result of parsing a unified diff"""
    old_file: str
    new_file: str
    hunks: List[DiffHunk] = field(default_factory=list)
    is_valid: bool = True
    error: Optional[str] = None


@dataclass
class ApplyResult:
    """Result of applying a diff"""
    success: bool
    new_content: str
    error: Optional[str] = None
    lines_added: int = 0
    lines_deleted: int = 0


class DiffParser:
    """
    Parses and applies unified diffs.

    Unified diff format:
    ```
    --- a/path/to/file
    +++ b/path/to/file
    @@ -start,count +start,count @@
     context line (space prefix)
    -deleted line (minus prefix)
    +added line (plus prefix)
    ```
    """

    # Regex patterns
    OLD_FILE_PATTERN = re.compile(r'^---\s+(?:a/)?(.+?)(?:\t.*)?$')
    NEW_FILE_PATTERN = re.compile(r'^\+\+\+\s+(?:b/)?(.+?)(?:\t.*)?$')
    HUNK_PATTERN = re.compile(r'^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@')

    @classmethod
    def parse(cls, diff_text: str) -> ParsedDiff:
        """
        Parse a unified diff into structured format.

        Args:
            diff_text: The unified diff string

        Returns:
            ParsedDiff with hunks and operations
        """
        lines = diff_text.strip().split('\n')

        if not lines:
            return ParsedDiff(
                old_file="", new_file="",
                is_valid=False, error="Empty diff"
            )

        result = ParsedDiff(old_file="", new_file="")
        current_hunk: Optional[DiffHunk] = None
        old_line = 0
        new_line = 0

        for i, line in enumerate(lines):
            # Parse old file header
            old_match = cls.OLD_FILE_PATTERN.match(line)
            if old_match:
                result.old_file = old_match.group(1).strip()
                continue

            # Parse new file header
            new_match = cls.NEW_FILE_PATTERN.match(line)
            if new_match:
                result.new_file = new_match.group(1).strip()
                continue

            # Parse hunk header
            hunk_match = cls.HUNK_PATTERN.match(line)
            if hunk_match:
                # Save previous hunk
                if current_hunk:
                    result.hunks.append(current_hunk)

                old_start = int(hunk_match.group(1))
                old_count = int(hunk_match.group(2)) if hunk_match.group(2) else 1
                new_start = int(hunk_match.group(3))
                new_count = int(hunk_match.group(4)) if hunk_match.group(4) else 1

                current_hunk = DiffHunk(
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count
                )
                old_line = old_start
                new_line = new_start
                continue

            # Parse diff lines (only if we're in a hunk)
            if current_hunk is not None:
                if line.startswith('+'):
                    # Added line
                    current_hunk.lines.append(DiffLine(
                        operation=LineOperation.ADD,
                        content=line[1:],  # Remove the + prefix
                        new_line_num=new_line
                    ))
                    new_line += 1

                elif line.startswith('-'):
                    # Deleted line
                    current_hunk.lines.append(DiffLine(
                        operation=LineOperation.DELETE,
                        content=line[1:],  # Remove the - prefix
                        old_line_num=old_line
                    ))
                    old_line += 1

                elif line.startswith(' ') or line == '':
                    # Context line (unchanged)
                    content = line[1:] if line.startswith(' ') else ''
                    current_hunk.lines.append(DiffLine(
                        operation=LineOperation.CONTEXT,
                        content=content,
                        old_line_num=old_line,
                        new_line_num=new_line
                    ))
                    old_line += 1
                    new_line += 1

                elif line.startswith('\\'):
                    # "\ No newline at end of file" - skip
                    continue

        # Don't forget the last hunk
        if current_hunk:
            result.hunks.append(current_hunk)

        # Validate
        if not result.hunks:
            result.is_valid = False
            result.error = "No hunks found in diff"
        elif not result.new_file:
            result.is_valid = False
            result.error = "No file path found in diff"

        return result

    @classmethod
    def apply(cls, original_content: str, parsed_diff: ParsedDiff) -> ApplyResult:
        """
        Apply a parsed diff to original file content.

        Args:
            original_content: The original file content
            parsed_diff: The parsed diff to apply

        Returns:
            ApplyResult with new content or error
        """
        if not parsed_diff.is_valid:
            return ApplyResult(
                success=False,
                new_content=original_content,
                error=parsed_diff.error
            )

        # Split original into lines
        original_lines = original_content.split('\n')

        # Track changes
        lines_added = 0
        lines_deleted = 0

        # Apply hunks in reverse order to preserve line numbers
        for hunk in reversed(parsed_diff.hunks):
            try:
                # Calculate the index (0-based)
                start_idx = hunk.old_start - 1

                # Verify context matches (optional but recommended)
                if not cls._verify_context(original_lines, hunk, start_idx):
                    logger.warning(f"[DiffParser] Context mismatch at line {hunk.old_start}, attempting fuzzy match")
                    start_idx = cls._fuzzy_find_context(original_lines, hunk)
                    if start_idx < 0:
                        return ApplyResult(
                            success=False,
                            new_content=original_content,
                            error=f"Could not find matching context for hunk at line {hunk.old_start}"
                        )

                # Build new lines for this section
                new_section = []
                old_idx = start_idx

                for diff_line in hunk.lines:
                    if diff_line.operation == LineOperation.CONTEXT:
                        # Keep the original line
                        if old_idx < len(original_lines):
                            new_section.append(original_lines[old_idx])
                            old_idx += 1
                    elif diff_line.operation == LineOperation.DELETE:
                        # Skip this line (delete it)
                        old_idx += 1
                        lines_deleted += 1
                    elif diff_line.operation == LineOperation.ADD:
                        # Add new line
                        new_section.append(diff_line.content)
                        lines_added += 1

                # Replace the section in original
                end_idx = start_idx + hunk.old_count
                original_lines[start_idx:end_idx] = new_section

            except Exception as e:
                logger.error(f"[DiffParser] Error applying hunk: {e}")
                return ApplyResult(
                    success=False,
                    new_content=original_content,
                    error=f"Error applying hunk: {str(e)}"
                )

        # Join lines back
        new_content = '\n'.join(original_lines)

        logger.info(f"[DiffParser] Applied diff: +{lines_added} -{lines_deleted} lines")

        return ApplyResult(
            success=True,
            new_content=new_content,
            lines_added=lines_added,
            lines_deleted=lines_deleted
        )

    @classmethod
    def apply_diff(cls, original_content: str, diff_text: str) -> ApplyResult:
        """
        Convenience method: parse and apply in one call.

        Args:
            original_content: The original file content
            diff_text: The unified diff string

        Returns:
            ApplyResult with new content or error
        """
        parsed = cls.parse(diff_text)
        if not parsed.is_valid:
            return ApplyResult(
                success=False,
                new_content=original_content,
                error=parsed.error
            )
        return cls.apply(original_content, parsed)

    @classmethod
    def _verify_context(cls, lines: List[str], hunk: DiffHunk, start_idx: int) -> bool:
        """
        Verify that context lines match the original file.
        """
        idx = start_idx
        for diff_line in hunk.lines:
            if diff_line.operation == LineOperation.CONTEXT:
                if idx >= len(lines):
                    return False
                # Fuzzy match - ignore trailing whitespace
                if lines[idx].rstrip() != diff_line.content.rstrip():
                    return False
                idx += 1
            elif diff_line.operation == LineOperation.DELETE:
                if idx >= len(lines):
                    return False
                # The line to delete should match
                if lines[idx].rstrip() != diff_line.content.rstrip():
                    return False
                idx += 1
        return True

    @classmethod
    def _fuzzy_find_context(cls, lines: List[str], hunk: DiffHunk) -> int:
        """
        Try to find the hunk context with some tolerance for line number drift.

        Searches +/- 10 lines from expected position.
        """
        expected_start = hunk.old_start - 1
        search_range = 10

        # Get first non-empty context or delete line to search for
        search_content = None
        for diff_line in hunk.lines:
            if diff_line.operation in (LineOperation.CONTEXT, LineOperation.DELETE):
                if diff_line.content.strip():
                    search_content = diff_line.content.rstrip()
                    break

        if not search_content:
            return expected_start  # No context to search for

        # Search around expected position
        for offset in range(search_range + 1):
            for direction in [0, -1, 1]:
                if direction == 0 and offset != 0:
                    continue

                idx = expected_start + (offset * direction)
                if 0 <= idx < len(lines):
                    if lines[idx].rstrip() == search_content:
                        # Verify more context matches
                        if cls._verify_context(lines, hunk, idx):
                            logger.info(f"[DiffParser] Fuzzy matched at line {idx + 1} (expected {hunk.old_start})")
                            return idx

        return -1  # Not found

    @classmethod
    def extract_file_path(cls, diff_text: str) -> Optional[str]:
        """
        Extract the file path from a diff without full parsing.
        """
        for line in diff_text.split('\n'):
            match = cls.NEW_FILE_PATTERN.match(line)
            if match:
                return match.group(1).strip()
            # Also try old file if new not found
            match = cls.OLD_FILE_PATTERN.match(line)
            if match:
                return match.group(1).strip()
        return None


# Convenience functions
def parse_diff(diff_text: str) -> ParsedDiff:
    """Parse a unified diff string."""
    return DiffParser.parse(diff_text)


def apply_diff(original_content: str, diff_text: str) -> ApplyResult:
    """Parse and apply a unified diff to content."""
    return DiffParser.apply_diff(original_content, diff_text)
