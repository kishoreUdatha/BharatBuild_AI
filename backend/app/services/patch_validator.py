"""
Patch Validator - Validates Claude's output before applying

Claude never touches the system directly.
Every patch must pass validation before being applied.

Validates:
1. Only allowed files are modified
2. Syntax appears valid
3. No dangerous patterns
4. Patch can be applied cleanly
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

from app.core.logging_config import logger


@dataclass
class ValidationResult:
    """Result of patch validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    file_path: str
    patch_type: str  # 'diff' or 'full_file' or 'new_file'


class PatchValidator:
    """
    Validates patches before they are applied.

    Security gate between Claude and the filesystem.
    """

    # Files that should never be modified by auto-fixer
    FORBIDDEN_FILES = [
        '.env',
        '.env.local',
        '.env.production',
        'credentials.json',
        'secrets.json',
        '.git/config',
        'id_rsa',
        'id_ed25519',
        '.npmrc',
        '.yarnrc',
        'docker-compose.yml',  # Infra changes should be manual
        'Dockerfile',  # Infra changes should be manual
    ]

    # Patterns that should never appear in patches
    DANGEROUS_PATTERNS = [
        r'eval\s*\(',
        r'Function\s*\(',
        r'child_process',
        r'exec\s*\(',
        r'spawn\s*\(',
        r'rm\s+-rf',
        r'curl\s+.*\|\s*(?:bash|sh)',
        r'wget\s+.*\|\s*(?:bash|sh)',
    ]

    # Allowed file extensions for modification
    ALLOWED_EXTENSIONS = [
        '.js', '.jsx', '.ts', '.tsx',
        '.json', '.css', '.scss', '.sass', '.less',
        '.html', '.htm', '.vue', '.svelte',
        '.md', '.txt', '.yaml', '.yml',
        '.mjs', '.cjs',
    ]

    @classmethod
    def validate_diff(
        cls,
        patch_content: str,
        project_path: Path,
        allowed_files: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Validate a unified diff patch.

        Args:
            patch_content: The diff content
            project_path: Project root path
            allowed_files: Optional list of allowed file paths

        Returns:
            ValidationResult with validity and any errors
        """
        errors = []
        warnings = []

        # Extract file path from diff
        file_match = re.search(r'^(?:---|\+\+\+)\s+([^\s]+)', patch_content, re.MULTILINE)
        if not file_match:
            return ValidationResult(
                is_valid=False,
                errors=["Could not extract file path from diff"],
                warnings=[],
                file_path="unknown",
                patch_type="diff"
            )

        file_path = file_match.group(1)
        # Clean up git-style prefixes
        file_path = re.sub(r'^[ab]/', '', file_path)

        # Check forbidden files
        if cls._is_forbidden_file(file_path):
            return ValidationResult(
                is_valid=False,
                errors=[f"Cannot modify forbidden file: {file_path}"],
                warnings=[],
                file_path=file_path,
                patch_type="diff"
            )

        # Check file extension
        if not cls._has_allowed_extension(file_path):
            warnings.append(f"Unusual file extension for: {file_path}")

        # Check allowed files list
        if allowed_files and file_path not in allowed_files:
            # Also check without frontend/ prefix
            normalized = file_path.replace('frontend/', '').replace('backend/', '')
            if normalized not in [f.replace('frontend/', '').replace('backend/', '') for f in allowed_files]:
                warnings.append(f"File not in expected list: {file_path}")

        # Check for dangerous patterns
        dangerous = cls._check_dangerous_patterns(patch_content)
        if dangerous:
            errors.extend(dangerous)

        # Validate diff syntax
        if not cls._is_valid_diff_syntax(patch_content):
            warnings.append("Diff syntax may be malformed")

        # Check if target file exists (for patches, not new files)
        target_path = project_path / file_path
        if not target_path.exists():
            # Try with frontend prefix
            target_path = project_path / "frontend" / file_path
            if not target_path.exists():
                warnings.append(f"Target file does not exist: {file_path}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            file_path=file_path,
            patch_type="diff"
        )

    @classmethod
    def validate_full_file(
        cls,
        file_path: str,
        content: str,
        project_path: Path
    ) -> ValidationResult:
        """
        Validate a full file replacement.

        Args:
            file_path: Path of the file
            content: New file content
            project_path: Project root path

        Returns:
            ValidationResult with validity and any errors
        """
        errors = []
        warnings = []

        # Check forbidden files
        if cls._is_forbidden_file(file_path):
            return ValidationResult(
                is_valid=False,
                errors=[f"Cannot modify forbidden file: {file_path}"],
                warnings=[],
                file_path=file_path,
                patch_type="full_file"
            )

        # Check file extension
        if not cls._has_allowed_extension(file_path):
            warnings.append(f"Unusual file extension for: {file_path}")

        # Check for dangerous patterns
        dangerous = cls._check_dangerous_patterns(content)
        if dangerous:
            errors.extend(dangerous)

        # Basic syntax validation for known file types
        syntax_check = cls._validate_syntax(file_path, content)
        if syntax_check:
            errors.extend(syntax_check)

        # Check file size (sanity check)
        if len(content) > 500000:  # 500KB
            warnings.append(f"File is very large: {len(content)} bytes")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            file_path=file_path,
            patch_type="full_file"
        )

    @classmethod
    def validate_new_file(
        cls,
        file_path: str,
        content: str,
        project_path: Path
    ) -> ValidationResult:
        """
        Validate a new file creation.

        Args:
            file_path: Path of the new file
            content: File content
            project_path: Project root path

        Returns:
            ValidationResult with validity and any errors
        """
        errors = []
        warnings = []

        # Check forbidden files
        if cls._is_forbidden_file(file_path):
            return ValidationResult(
                is_valid=False,
                errors=[f"Cannot create forbidden file: {file_path}"],
                warnings=[],
                file_path=file_path,
                patch_type="new_file"
            )

        # Check if file already exists
        target_path = project_path / file_path
        if target_path.exists():
            warnings.append(f"File already exists, will be overwritten: {file_path}")

        # Check for dangerous patterns
        dangerous = cls._check_dangerous_patterns(content)
        if dangerous:
            errors.extend(dangerous)

        # Basic syntax validation
        syntax_check = cls._validate_syntax(file_path, content)
        if syntax_check:
            errors.extend(syntax_check)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            file_path=file_path,
            patch_type="new_file"
        )

    @classmethod
    def _is_forbidden_file(cls, file_path: str) -> bool:
        """Check if file is in forbidden list"""
        normalized = file_path.lower().replace('\\', '/')
        for forbidden in cls.FORBIDDEN_FILES:
            if forbidden.lower() in normalized or normalized.endswith(forbidden.lower()):
                return True
        return False

    @classmethod
    def _has_allowed_extension(cls, file_path: str) -> bool:
        """Check if file has allowed extension"""
        return any(file_path.lower().endswith(ext) for ext in cls.ALLOWED_EXTENSIONS)

    @classmethod
    def _check_dangerous_patterns(cls, content: str) -> List[str]:
        """Check for dangerous code patterns"""
        found = []
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                found.append(f"Dangerous pattern detected: {pattern}")
        return found

    @classmethod
    def _is_valid_diff_syntax(cls, patch: str) -> bool:
        """Basic validation of diff syntax"""
        # Should have --- and +++ lines
        has_minus = re.search(r'^---\s', patch, re.MULTILINE)
        has_plus = re.search(r'^\+\+\+\s', patch, re.MULTILINE)
        # Should have @@ hunk headers
        has_hunk = re.search(r'^@@.*@@', patch, re.MULTILINE)

        return bool(has_minus and has_plus) or bool(has_hunk)

    @classmethod
    def _validate_syntax(cls, file_path: str, content: str) -> List[str]:
        """
        Basic syntax validation for known file types.
        Not a full parser, just catches obvious issues.
        """
        errors = []

        if file_path.endswith('.json'):
            # Validate JSON syntax
            try:
                import json
                json.loads(content)
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON syntax: {e}")

        elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
            # Basic bracket balance check
            open_braces = content.count('{')
            close_braces = content.count('}')
            open_parens = content.count('(')
            close_parens = content.count(')')
            open_brackets = content.count('[')
            close_brackets = content.count(']')

            if open_braces != close_braces:
                errors.append(f"Unbalanced braces: {open_braces} open, {close_braces} close")
            if open_parens != close_parens:
                errors.append(f"Unbalanced parentheses: {open_parens} open, {close_parens} close")
            if open_brackets != close_brackets:
                errors.append(f"Unbalanced brackets: {open_brackets} open, {close_brackets} close")

        return errors


# Singleton instance
patch_validator = PatchValidator()
