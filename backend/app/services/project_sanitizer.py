"""
Project Sanitizer - Auto-fix common issues in generated project files

Makes project builds error-proof in Docker/EC2 sandbox environments by:
1. Sanitizing file paths (remove invalid characters)
2. Fixing line endings (CRLF -> LF for Unix)
3. Validating and fixing JSON files (package.json, tsconfig.json)
4. Validating and fixing YAML files (docker-compose.yml)
5. Fixing common JavaScript/TypeScript issues
6. Adding BOM removal for UTF-8 files
7. Validating Dockerfile syntax
8. Fixing common Python issues
"""

import re
import json
import os
from typing import Tuple, Optional, Dict, Any, List
from pathlib import Path

from app.core.logging_config import logger


class ProjectSanitizer:
    """Auto-sanitize project files for error-proof builds."""

    # File extensions that should be sanitized
    TEXT_EXTENSIONS = {
        '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
        '.json', '.yaml', '.yml',
        '.py', '.pyx',
        '.java', '.kt', '.scala',
        '.go', '.rs',
        '.html', '.htm', '.css', '.scss', '.sass', '.less',
        '.md', '.txt', '.csv',
        '.sh', '.bash', '.zsh',
        '.xml', '.svg',
        '.env', '.env.example', '.env.local',
        '.gitignore', '.dockerignore', '.eslintrc', '.prettierrc',
        '.sql', '.graphql', '.gql',
    }

    # Files that need special handling
    SPECIAL_FILES = {
        'package.json', 'tsconfig.json', 'jsconfig.json',
        'docker-compose.yml', 'docker-compose.yaml',
        'Dockerfile', '.dockerignore',
        'requirements.txt', 'pyproject.toml', 'setup.py',
        'pom.xml', 'build.gradle', 'settings.gradle',
        'go.mod', 'go.sum',
        'Cargo.toml',
    }

    def __init__(self):
        self.fixes_applied: List[str] = []

    def sanitize_file(self, file_path: str, content: str) -> Tuple[str, str, List[str]]:
        """
        Sanitize a file's path and content.

        Args:
            file_path: Relative file path
            content: File content

        Returns:
            Tuple of (sanitized_path, sanitized_content, list_of_fixes_applied)
        """
        self.fixes_applied = []

        # 1. Sanitize file path
        sanitized_path = self._sanitize_path(file_path)

        # 2. Skip binary files
        if self._is_binary_file(file_path):
            return sanitized_path, content, self.fixes_applied

        # 3. Apply general sanitization
        sanitized_content = self._sanitize_content(content, file_path)

        # 4. Apply file-specific sanitization
        file_name = os.path.basename(file_path).lower()
        ext = os.path.splitext(file_path)[1].lower()

        if file_name == 'package.json':
            sanitized_content = self._sanitize_package_json(sanitized_content)
        elif file_name in ('tsconfig.json', 'jsconfig.json'):
            sanitized_content = self._sanitize_tsconfig(sanitized_content)
        elif file_name in ('docker-compose.yml', 'docker-compose.yaml') or ext in ('.yml', '.yaml'):
            sanitized_content = self._sanitize_yaml(sanitized_content)
        elif file_name == 'dockerfile' or file_path.lower().endswith('dockerfile'):
            sanitized_content = self._sanitize_dockerfile(sanitized_content)
        elif ext in ('.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'):
            sanitized_content = self._sanitize_javascript(sanitized_content)
        elif ext == '.py':
            sanitized_content = self._sanitize_python(sanitized_content)
        elif ext in ('.sh', '.bash'):
            sanitized_content = self._sanitize_shell_script(sanitized_content)
        elif ext == '.json':
            sanitized_content = self._sanitize_json(sanitized_content)
        elif file_name == '.env' or file_name.startswith('.env'):
            sanitized_content = self._sanitize_env_file(sanitized_content)

        return sanitized_path, sanitized_content, self.fixes_applied

    def _sanitize_path(self, file_path: str) -> str:
        """Sanitize file path for cross-platform compatibility."""
        original = file_path

        # Normalize path separators
        sanitized = file_path.replace('\\', '/')

        # Remove leading/trailing whitespace from path components
        parts = [p.strip() for p in sanitized.split('/') if p.strip()]
        sanitized = '/'.join(parts)

        # Remove invalid characters (keep alphanumeric, dots, dashes, underscores, slashes)
        # But preserve common special chars in filenames
        sanitized = re.sub(r'[<>:"|?*\x00-\x1f]', '', sanitized)

        # Prevent directory traversal
        sanitized = sanitized.replace('../', '').replace('..\\', '')

        # Remove duplicate slashes
        sanitized = re.sub(r'/+', '/', sanitized)

        # Remove leading slash (should be relative path)
        sanitized = sanitized.lstrip('/')

        if sanitized != original:
            self.fixes_applied.append(f"Path sanitized: {original} -> {sanitized}")

        return sanitized

    def _is_binary_file(self, file_path: str) -> bool:
        """Check if file is binary based on extension."""
        binary_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp', '.bmp',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx',
            '.zip', '.tar', '.gz', '.rar', '.7z',
            '.exe', '.dll', '.so', '.dylib',
            '.woff', '.woff2', '.ttf', '.eot', '.otf',
            '.mp3', '.mp4', '.avi', '.mov', '.webm',
            '.pyc', '.pyo', '.class', '.o',
        }
        ext = os.path.splitext(file_path)[1].lower()
        return ext in binary_extensions

    def _sanitize_content(self, content: str, file_path: str) -> str:
        """Apply general content sanitization."""
        original_len = len(content)

        # Remove BOM (Byte Order Mark)
        if content.startswith('\ufeff'):
            content = content[1:]
            self.fixes_applied.append("Removed UTF-8 BOM")

        # Normalize line endings to LF (Unix style) for Docker/Linux compatibility
        if '\r\n' in content:
            content = content.replace('\r\n', '\n')
            self.fixes_applied.append("Converted CRLF to LF")

        if '\r' in content:
            content = content.replace('\r', '\n')
            self.fixes_applied.append("Converted CR to LF")

        # Remove trailing whitespace from lines (but preserve intentional indentation)
        lines = content.split('\n')
        cleaned_lines = [line.rstrip() for line in lines]
        if lines != cleaned_lines:
            content = '\n'.join(cleaned_lines)
            self.fixes_applied.append("Removed trailing whitespace")

        # Ensure file ends with newline (POSIX compliance)
        if content and not content.endswith('\n'):
            content += '\n'
            self.fixes_applied.append("Added trailing newline")

        return content

    def _sanitize_package_json(self, content: str) -> str:
        """Sanitize package.json for npm/pnpm dual compatibility (local + EC2 Docker)."""
        try:
            data = json.loads(content)
            modified = False

            # Ensure name is valid npm package name
            if 'name' in data:
                original_name = data['name']
                # npm package names must be lowercase, no spaces
                sanitized_name = re.sub(r'[^a-z0-9-_.]', '-', original_name.lower())
                sanitized_name = re.sub(r'-+', '-', sanitized_name).strip('-')
                if sanitized_name != original_name:
                    data['name'] = sanitized_name
                    modified = True
                    self.fixes_applied.append(f"Fixed package name: {original_name} -> {sanitized_name}")

            # Ensure version is valid semver
            if 'version' not in data or not data['version']:
                data['version'] = '0.1.0'
                modified = True
                self.fixes_applied.append("Added default version")

            # Move pnpm-specific root-level config to pnpm section (npm ignores pnpm section)
            pnpm_only_fields = [
                'strict-peer-dependencies',
                'auto-install-peers',
                'shamefully-hoist',
                'prefer-workspace-packages',
                'link-workspace-packages',
                'shared-workspace-lockfile',
                'save-workspace-protocol',
                'use-lockfile-v6',
            ]
            pnpm_config_moved = []
            for field in pnpm_only_fields:
                if field in data:
                    # Move to pnpm section instead of deleting (pnpm will read it, npm will ignore)
                    if 'pnpm' not in data:
                        data['pnpm'] = {}
                    data['pnpm'][field] = data[field]
                    del data[field]
                    pnpm_config_moved.append(field)
                    modified = True

            if pnpm_config_moved:
                self.fixes_applied.append(f"Moved pnpm config to pnpm section: {', '.join(pnpm_config_moved)}")

            # Fix overrides that conflict with direct dependencies (npm error)
            if 'overrides' in data and isinstance(data['overrides'], dict):
                deps = set()
                for dep_key in ['dependencies', 'devDependencies']:
                    if dep_key in data and isinstance(data[dep_key], dict):
                        deps.update(data[dep_key].keys())

                conflicting_overrides = []
                for pkg in list(data['overrides'].keys()):
                    # Check if override conflicts with direct dependency
                    if pkg in deps:
                        direct_ver = data.get('dependencies', {}).get(pkg) or data.get('devDependencies', {}).get(pkg)
                        override_ver = data['overrides'][pkg]
                        # Remove override if it conflicts (different version)
                        if direct_ver and override_ver and direct_ver != override_ver:
                            conflicting_overrides.append(f"{pkg}@{override_ver}")
                            del data['overrides'][pkg]
                            modified = True

                if conflicting_overrides:
                    self.fixes_applied.append(f"Removed conflicting overrides: {', '.join(conflicting_overrides)}")

                # Remove empty overrides object
                if 'overrides' in data and not data['overrides']:
                    del data['overrides']
                    modified = True

            # Fix common dependency issues
            for dep_key in ['dependencies', 'devDependencies', 'peerDependencies']:
                if dep_key in data and isinstance(data[dep_key], dict):
                    for pkg, ver in list(data[dep_key].items()):
                        if ver and isinstance(ver, str):
                            # Fix "latest" to "*" for compatibility
                            if ver == 'latest':
                                data[dep_key][pkg] = '*'
                                modified = True
                                self.fixes_applied.append(f"Fixed {pkg} version: latest -> *")
                            # Fix workspace: protocol (pnpm-specific, won't work in npm)
                            if ver.startswith('workspace:'):
                                # Convert workspace:* to * for npm compatibility
                                data[dep_key][pkg] = ver.replace('workspace:', '') or '*'
                                modified = True
                                self.fixes_applied.append(f"Fixed {pkg}: workspace protocol")

            # Ensure scripts object exists
            if 'scripts' not in data:
                data['scripts'] = {}
                modified = True

            # Ensure proper JSON formatting
            content = json.dumps(data, indent=2, ensure_ascii=False) + '\n'

            return content

        except json.JSONDecodeError as e:
            self.fixes_applied.append(f"Warning: Invalid package.json - {e}")
            # Try to fix common JSON errors
            return self._fix_json_errors(content)

    def _sanitize_tsconfig(self, content: str) -> str:
        """Sanitize tsconfig.json/jsconfig.json."""
        try:
            # Remove comments (tsconfig allows them but json.loads doesn't)
            content_no_comments = self._remove_json_comments(content)
            data = json.loads(content_no_comments)

            # Ensure compilerOptions exists
            if 'compilerOptions' not in data:
                data['compilerOptions'] = {}

            # Re-format
            content = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
            return content

        except json.JSONDecodeError as e:
            self.fixes_applied.append(f"Warning: Invalid tsconfig - {e}")
            return self._fix_json_errors(content)

    def _sanitize_yaml(self, content: str) -> str:
        """Sanitize YAML files for Docker Compose compatibility."""
        # Basic YAML fixes without full parsing
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # Fix common indentation issues (must be spaces, not tabs)
            if line.startswith('\t'):
                spaces = len(line) - len(line.lstrip('\t'))
                line = '  ' * spaces + line.lstrip('\t')
                if "Fixed YAML tabs to spaces" not in self.fixes_applied:
                    self.fixes_applied.append("Fixed YAML tabs to spaces")

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _sanitize_dockerfile(self, content: str) -> str:
        """Sanitize Dockerfile for build compatibility."""
        lines = content.split('\n')
        fixed_lines = []
        has_from = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Check for FROM instruction
            if stripped.upper().startswith('FROM '):
                has_from = True

            # Fix common issues
            # 1. Remove Windows-style line continuations
            if line.rstrip().endswith('`'):
                line = line.rstrip()[:-1] + ' \\'
                self.fixes_applied.append("Fixed Dockerfile line continuation")

            fixed_lines.append(line)

        # Ensure FROM instruction exists
        if not has_from and fixed_lines:
            # Don't auto-add FROM as it would break things
            self.fixes_applied.append("Warning: Dockerfile missing FROM instruction")

        return '\n'.join(fixed_lines)

    def _sanitize_javascript(self, content: str) -> str:
        """Sanitize JavaScript/TypeScript files."""
        # Fix common import issues
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # Fix Windows path separators in imports
            if ('import ' in line or 'require(' in line) and '\\' in line:
                line = line.replace('\\\\', '/').replace('\\', '/')
                if "Fixed import paths" not in self.fixes_applied:
                    self.fixes_applied.append("Fixed import paths")

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _sanitize_python(self, content: str) -> str:
        """Sanitize Python files."""
        lines = content.split('\n')

        # Ensure proper encoding declaration for non-ASCII content
        has_encoding = False
        has_shebang = False

        for i, line in enumerate(lines[:2]):
            if 'coding' in line or 'encoding' in line:
                has_encoding = True
            if line.startswith('#!'):
                has_shebang = True

        # Check if non-ASCII characters exist
        has_non_ascii = any(ord(c) > 127 for c in content)

        if has_non_ascii and not has_encoding:
            # Add encoding declaration
            if has_shebang and len(lines) > 0:
                lines.insert(1, '# -*- coding: utf-8 -*-')
            else:
                lines.insert(0, '# -*- coding: utf-8 -*-')
            self.fixes_applied.append("Added Python encoding declaration")

        return '\n'.join(lines)

    def _sanitize_shell_script(self, content: str) -> str:
        """Sanitize shell scripts."""
        lines = content.split('\n')

        # Ensure shebang exists
        if lines and not lines[0].startswith('#!'):
            lines.insert(0, '#!/bin/bash')
            self.fixes_applied.append("Added shell shebang")

        # Fix common issues
        fixed_lines = []
        for line in lines:
            # Remove Windows-style line continuations
            if line.rstrip().endswith('`'):
                line = line.rstrip()[:-1] + ' \\'
                self.fixes_applied.append("Fixed shell line continuation")

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _sanitize_json(self, content: str) -> str:
        """Sanitize generic JSON files."""
        try:
            # Remove comments if present
            content_no_comments = self._remove_json_comments(content)
            data = json.loads(content_no_comments)
            return json.dumps(data, indent=2, ensure_ascii=False) + '\n'
        except json.JSONDecodeError:
            return self._fix_json_errors(content)

    def _sanitize_env_file(self, content: str) -> str:
        """Sanitize .env files."""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                fixed_lines.append(line)
                continue

            # Fix common issues
            if '=' in stripped:
                key, _, value = stripped.partition('=')
                key = key.strip()
                value = value.strip()

                # Remove quotes around values (Docker prefers unquoted)
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    # Keep quotes for values with spaces or special chars
                    inner_value = value[1:-1]
                    if ' ' not in inner_value and '=' not in inner_value:
                        value = inner_value
                        self.fixes_applied.append(f"Simplified .env value: {key}")

                fixed_lines.append(f"{key}={value}")
            else:
                fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _remove_json_comments(self, content: str) -> str:
        """Remove comments from JSON (for tsconfig, etc.)."""
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        return content

    def _fix_json_errors(self, content: str) -> str:
        """Try to fix common JSON errors."""
        original = content

        # Remove trailing commas (common error)
        content = re.sub(r',(\s*[}\]])', r'\1', content)

        # Try to parse
        try:
            data = json.loads(content)
            content = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
            self.fixes_applied.append("Fixed JSON trailing commas")
            return content
        except json.JSONDecodeError:
            pass

        # Return original if can't fix
        return original


# Singleton instance
project_sanitizer = ProjectSanitizer()


def sanitize_project_file(file_path: str, content: str) -> Tuple[str, str, List[str]]:
    """
    Convenience function to sanitize a project file.

    Args:
        file_path: Relative file path
        content: File content

    Returns:
        Tuple of (sanitized_path, sanitized_content, fixes_applied)
    """
    return project_sanitizer.sanitize_file(file_path, content)
