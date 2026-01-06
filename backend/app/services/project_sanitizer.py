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
        elif ext in ('.css', '.scss', '.sass'):
            sanitized_content = self._sanitize_css(sanitized_content)
        elif file_name == 'tailwind.config.js' or file_name == 'tailwind.config.ts':
            sanitized_content = self._sanitize_tailwind_config(sanitized_content)
        elif file_name == 'vite.config.ts' or file_name == 'vite.config.js':
            sanitized_content = self._sanitize_vite_config(sanitized_content)
        elif file_name == 'pom.xml':
            sanitized_content = self._sanitize_pom_xml(sanitized_content)
        elif file_name == 'build.gradle' or file_name == 'build.gradle.kts':
            sanitized_content = self._sanitize_gradle(sanitized_content)
        elif file_name == 'go.mod':
            sanitized_content = self._sanitize_go_mod(sanitized_content)
        elif file_name == 'Cargo.toml':
            sanitized_content = self._sanitize_cargo_toml(sanitized_content)
        elif file_name == 'requirements.txt':
            sanitized_content = self._sanitize_requirements_txt(sanitized_content)
        elif file_name == 'application.properties' or file_name == 'application.yml':
            sanitized_content = self._sanitize_spring_config(sanitized_content)
        # AI/ML Projects
        elif file_name == 'environment.yml' or file_name == 'environment.yaml':
            sanitized_content = self._sanitize_conda_env(sanitized_content)
        elif file_name == 'pyproject.toml':
            sanitized_content = self._sanitize_pyproject_toml(sanitized_content)
        elif file_name == 'setup.py':
            sanitized_content = self._sanitize_setup_py(sanitized_content)
        elif ext == '.ipynb':
            sanitized_content = self._sanitize_jupyter_notebook(sanitized_content)
        # Blockchain Projects
        elif file_name == 'hardhat.config.js' or file_name == 'hardhat.config.ts':
            sanitized_content = self._sanitize_hardhat_config(sanitized_content)
        elif file_name == 'truffle-config.js':
            sanitized_content = self._sanitize_truffle_config(sanitized_content)
        elif file_name == 'foundry.toml':
            sanitized_content = self._sanitize_foundry_toml(sanitized_content)
        elif ext == '.sol':
            sanitized_content = self._sanitize_solidity(sanitized_content)
        # Cyber Security
        elif file_name == 'docker-compose.yml' or file_name == 'docker-compose.yaml':
            sanitized_content = self._sanitize_docker_compose_security(sanitized_content)
        elif 'security' in file_path.lower() and file_name == 'requirements.txt':
            sanitized_content = self._sanitize_security_requirements(sanitized_content)
        elif 'scanner' in file_name.lower() and ext == '.py':
            sanitized_content = self._sanitize_security_scanner_py(sanitized_content)
        elif 'encryption' in file_name.lower() or 'crypto' in file_name.lower():
            if ext == '.py':
                sanitized_content = self._sanitize_encryption_py(sanitized_content)
        elif file_name == 'security_config.yaml' or file_name == 'security_config.yml':
            sanitized_content = self._sanitize_security_config_yaml(sanitized_content)
        elif 'analyzer' in file_name.lower() and ext == '.py':
            sanitized_content = self._sanitize_log_analyzer_py(sanitized_content)

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

            # AUTO-INSTALL TAILWIND PLUGINS
            # If tailwindcss is in dependencies, ensure all common plugins are in devDependencies
            all_deps = {}
            all_deps.update(data.get('dependencies', {}))
            all_deps.update(data.get('devDependencies', {}))

            if 'tailwindcss' in all_deps:
                if 'devDependencies' not in data:
                    data['devDependencies'] = {}

                # Common Tailwind plugins that should always be available
                tailwind_plugins = {
                    '@tailwindcss/forms': '^0.5.7',
                    '@tailwindcss/typography': '^0.5.10',
                    '@tailwindcss/aspect-ratio': '^0.4.2',
                    '@tailwindcss/container-queries': '^0.1.1',
                }

                added_plugins = []
                for plugin, version in tailwind_plugins.items():
                    if plugin not in all_deps:
                        data['devDependencies'][plugin] = version
                        added_plugins.append(plugin)
                        modified = True

                if added_plugins:
                    self.fixes_applied.append(f"Added Tailwind plugins: {', '.join(added_plugins)}")

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

            # 2. Replace 'npm ci' with 'npm install' (npm ci requires package-lock.json)
            # Generated projects don't have package-lock.json, so npm ci fails
            if 'npm ci' in line:
                line = line.replace('npm ci', 'npm install')
                if "Replaced npm ci with npm install" not in self.fixes_applied:
                    self.fixes_applied.append("Replaced npm ci with npm install")

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

    def _sanitize_css(self, content: str) -> str:
        """
        Sanitize CSS files to fix common issues.

        Fixes:
        1. @import must come before @tailwind directives
        2. Remove @apply with undefined classes like border-border

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Move @import statements to the top (before @tailwind)
            # CSS spec requires @import to precede all other statements except @charset
            import_pattern = r'@import\s+url\([^)]+\)\s*;?\n?'
            imports = re.findall(import_pattern, content, re.IGNORECASE)

            if imports:
                # Check if @import comes after @tailwind
                tailwind_pos = content.lower().find('@tailwind')
                first_import_pos = content.lower().find('@import')

                if tailwind_pos != -1 and first_import_pos > tailwind_pos:
                    # Remove all @import statements
                    content = re.sub(import_pattern, '', content, flags=re.IGNORECASE)

                    # Add them at the beginning
                    imports_block = '\n'.join(imports) + '\n\n'
                    content = imports_block + content.lstrip()
                    self.fixes_applied.append("Moved @import statements before @tailwind directives")

            # Fix 2: Remove @apply border-border (undefined class)
            if '@apply' in content and 'border-border' in content:
                content = re.sub(r'@apply[^;]*border-border[^;]*;?\n?', '', content)
                self.fixes_applied.append("Removed @apply with undefined border-border class")

            # Fix 3: Clean up multiple blank lines
            content = re.sub(r'\n{3,}', '\n\n', content)

            if content != original:
                logger.info(f"[Sanitizer] CSS fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] CSS sanitization failed (returning original): {e}")
            return original

    def _sanitize_tailwind_config(self, content: str) -> str:
        """
        Sanitize tailwind.config.js/ts to fix common issues.

        Fixes:
        1. Remove references to plugins that aren't installed
        2. Ensure plugins array is empty or has only valid plugins

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Common plugins that cause issues if not installed
            problematic_plugins = [
                '@tailwindcss/forms',
                '@tailwindcss/typography',
                '@tailwindcss/aspect-ratio',
                '@tailwindcss/container-queries',
                'daisyui',
                'flowbite',
            ]

            # Check if any problematic plugins are referenced
            for plugin in problematic_plugins:
                if plugin in content:
                    # Remove require/import for this plugin
                    content = re.sub(rf"require\(['\"]{ re.escape(plugin) }['\"]\)\s*,?\s*", '', content)
                    content = re.sub(rf"import\s+\w+\s+from\s+['\"]{ re.escape(plugin) }['\"].*\n?", '', content)
                    # Remove from plugins array
                    content = re.sub(rf"['\"]{ re.escape(plugin) }['\"]\s*,?\s*", '', content)
                    self.fixes_applied.append(f"Removed non-installed plugin: {plugin}")

            # If plugins array is now empty with just whitespace, clean it up
            content = re.sub(r'plugins:\s*\[\s*,*\s*\]', 'plugins: []', content)

            if content != original:
                logger.info(f"[Sanitizer] Tailwind config fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] Tailwind config sanitization failed (returning original): {e}")
            return original

    def _sanitize_vite_config(self, content: str) -> str:
        """
        Sanitize vite.config.ts/js to fix common issues.

        Fixes:
        1. Fix corrupted base path (x27 escape sequences)
        2. Ensure base is './' for relative paths

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix corrupted base path like: base: x27./x27,
            if 'x27' in content:
                content = re.sub(r"base:\s*x27\.?/?x27\s*,?", "base: './',", content)
                self.fixes_applied.append("Fixed corrupted base path in vite.config")

            # Fix escaped quotes in base path
            if "base:" in content:
                # Fix patterns like base: '\\'' or base: "\""
                content = re.sub(r"base:\s*['\"]\\+['\"]\.?/?\\+['\"]\s*,?", "base: './',", content)

            if content != original:
                logger.info(f"[Sanitizer] Vite config fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] Vite config sanitization failed (returning original): {e}")
            return original

    def _sanitize_pom_xml(self, content: str) -> str:
        """
        Sanitize Maven pom.xml to fix common issues.

        Fixes:
        1. Fix malformed XML declarations
        2. Ensure proper encoding declaration
        3. Fix common dependency issues

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Ensure XML declaration is at the very beginning
            if not content.strip().startswith('<?xml'):
                # Add XML declaration if missing
                content = '<?xml version="1.0" encoding="UTF-8"?>\n' + content.lstrip()
                self.fixes_applied.append("Added missing XML declaration to pom.xml")

            # Fix 2: Fix common encoding issues
            if '<?xml' in content and 'encoding=' not in content.split('?>')[0]:
                content = content.replace('<?xml version="1.0"?>', '<?xml version="1.0" encoding="UTF-8"?>')
                self.fixes_applied.append("Added encoding declaration to pom.xml")

            # Fix 3: Fix self-closing tags that should have content
            # e.g., <version/> should be <version>1.0.0</version>
            if '<version/>' in content:
                content = content.replace('<version/>', '<version>1.0.0-SNAPSHOT</version>')
                self.fixes_applied.append("Fixed empty version tag in pom.xml")

            # Fix 4: Fix missing modelVersion
            if '<project' in content and '<modelVersion>' not in content:
                # Insert after <project ...>
                content = re.sub(
                    r'(<project[^>]*>)',
                    r'\1\n    <modelVersion>4.0.0</modelVersion>',
                    content,
                    count=1
                )
                self.fixes_applied.append("Added missing modelVersion to pom.xml")

            if content != original:
                logger.info(f"[Sanitizer] pom.xml fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] pom.xml sanitization failed (returning original): {e}")
            return original

    def _sanitize_gradle(self, content: str) -> str:
        """
        Sanitize Gradle build files to fix common issues.

        Fixes:
        1. Fix plugin declaration syntax
        2. Fix repository declarations
        3. Fix dependency syntax

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Fix common plugin syntax issues
            # Old style: apply plugin: 'java' -> New style: plugins { id 'java' }
            # (Only fix if clearly broken, don't change working syntax)

            # Fix 2: Ensure repositories block exists for dependencies
            if 'dependencies {' in content and 'repositories {' not in content:
                # Add repositories before dependencies
                content = content.replace(
                    'dependencies {',
                    'repositories {\n    mavenCentral()\n}\n\ndependencies {'
                )
                self.fixes_applied.append("Added missing repositories block to build.gradle")

            # Fix 3: Fix common typos in dependency configurations
            typo_fixes = [
                ('implmentation', 'implementation'),
                ('complie', 'compile'),
                ('testimplementation', 'testImplementation'),
                ('runtimenly', 'runtimeOnly'),
            ]
            for typo, correct in typo_fixes:
                if typo in content.lower():
                    content = re.sub(typo, correct, content, flags=re.IGNORECASE)
                    self.fixes_applied.append(f"Fixed typo in build.gradle: {typo} -> {correct}")

            if content != original:
                logger.info(f"[Sanitizer] build.gradle fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] build.gradle sanitization failed (returning original): {e}")
            return original

    def _sanitize_go_mod(self, content: str) -> str:
        """
        Sanitize Go go.mod to fix common issues.

        Fixes:
        1. Ensure module declaration exists
        2. Fix Go version declaration
        3. Clean up require statements

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Ensure module declaration is at the top
            if not content.strip().startswith('module '):
                # Check if module is declared elsewhere
                if 'module ' not in content:
                    # Add default module declaration
                    content = 'module app\n\n' + content
                    self.fixes_applied.append("Added missing module declaration to go.mod")

            # Fix 2: Ensure Go version is declared
            if 'go ' not in content or not re.search(r'go\s+\d+\.\d+', content):
                # Add Go version after module declaration
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith('module '):
                        lines.insert(i + 1, '\ngo 1.21')
                        break
                content = '\n'.join(lines)
                self.fixes_applied.append("Added Go version declaration to go.mod")

            # Fix 3: Fix common syntax issues in require blocks
            # Remove duplicate newlines in require block
            content = re.sub(r'(require\s*\(\s*)\n+', r'\1\n', content)

            if content != original:
                logger.info(f"[Sanitizer] go.mod fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] go.mod sanitization failed (returning original): {e}")
            return original

    def _sanitize_cargo_toml(self, content: str) -> str:
        """
        Sanitize Rust Cargo.toml to fix common issues.

        Fixes:
        1. Ensure [package] section exists
        2. Fix missing required fields (name, version, edition)
        3. Fix TOML syntax issues

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Ensure [package] section exists
            if '[package]' not in content:
                content = '[package]\nname = "app"\nversion = "0.1.0"\nedition = "2021"\n\n' + content
                self.fixes_applied.append("Added missing [package] section to Cargo.toml")
            else:
                # Fix 2: Ensure required fields exist in [package]
                package_section = re.search(r'\[package\](.*?)(?=\n\[|\Z)', content, re.DOTALL)
                if package_section:
                    package_content = package_section.group(1)

                    # Check for missing name
                    if 'name' not in package_content:
                        content = content.replace('[package]', '[package]\nname = "app"')
                        self.fixes_applied.append("Added missing name field to Cargo.toml")

                    # Check for missing version
                    if 'version' not in package_content:
                        content = content.replace('[package]', '[package]\nversion = "0.1.0"')
                        self.fixes_applied.append("Added missing version field to Cargo.toml")

                    # Check for missing edition
                    if 'edition' not in package_content:
                        content = content.replace('[package]', '[package]\nedition = "2021"')
                        self.fixes_applied.append("Added missing edition field to Cargo.toml")

            # Fix 3: Fix common TOML syntax issues
            # Ensure proper spacing around = in key-value pairs
            content = re.sub(r'(\w+)\s*=\s*', r'\1 = ', content)

            if content != original:
                logger.info(f"[Sanitizer] Cargo.toml fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] Cargo.toml sanitization failed (returning original): {e}")
            return original

    def _sanitize_requirements_txt(self, content: str) -> str:
        """
        Sanitize Python requirements.txt to fix common issues.

        Fixes:
        1. Remove invalid package specifications
        2. Fix common typos in package names
        3. Remove duplicate packages
        4. Fix version specifier syntax

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            lines = content.split('\n')
            cleaned_lines = []
            seen_packages = set()

            for line in lines:
                stripped = line.strip()

                # Skip empty lines and comments
                if not stripped or stripped.startswith('#'):
                    cleaned_lines.append(line)
                    continue

                # Fix common typos in package names
                typo_fixes = {
                    'flaskk': 'flask',
                    'djang': 'django',
                    'numpyy': 'numpy',
                    'pandass': 'pandas',
                    'request': 'requests',  # Common typo
                    'beautifulsoup': 'beautifulsoup4',
                }

                package_name = stripped.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].lower()

                for typo, correct in typo_fixes.items():
                    if package_name == typo:
                        stripped = stripped.replace(typo, correct, 1)
                        self.fixes_applied.append(f"Fixed typo in requirements.txt: {typo} -> {correct}")

                # Remove duplicates (keep first occurrence)
                base_package = stripped.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].strip().lower()
                if base_package in seen_packages:
                    self.fixes_applied.append(f"Removed duplicate package: {base_package}")
                    continue

                seen_packages.add(base_package)

                # Fix version specifier syntax (e.g., "package = 1.0" -> "package==1.0")
                if ' = ' in stripped and '==' not in stripped:
                    stripped = stripped.replace(' = ', '==')
                    self.fixes_applied.append("Fixed version specifier syntax in requirements.txt")

                cleaned_lines.append(stripped)

            content = '\n'.join(cleaned_lines)

            # Ensure file ends with newline
            if content and not content.endswith('\n'):
                content += '\n'

            if content != original:
                logger.info(f"[Sanitizer] requirements.txt fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] requirements.txt sanitization failed (returning original): {e}")
            return original

    def _sanitize_spring_config(self, content: str) -> str:
        """
        Sanitize Spring Boot application.properties/yml to fix common issues.

        Fixes:
        1. Fix common property key typos
        2. Ensure server.port is set
        3. Fix database connection strings

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Common property key typos
            typo_fixes = [
                ('spring.datasource.urll', 'spring.datasource.url'),
                ('spring.datasource.usrname', 'spring.datasource.username'),
                ('spring.datasource.pasword', 'spring.datasource.password'),
                ('server.prot', 'server.port'),
                ('spring.jpa.hibernate.ddl-atuo', 'spring.jpa.hibernate.ddl-auto'),
            ]

            for typo, correct in typo_fixes:
                if typo in content:
                    content = content.replace(typo, correct)
                    self.fixes_applied.append(f"Fixed typo in Spring config: {typo} -> {correct}")

            # Fix 2: Ensure server.port is set (for .properties files)
            if content.strip() and 'server.port' not in content:
                if '=' in content:  # It's a .properties file
                    content = 'server.port=8080\n' + content
                    self.fixes_applied.append("Added default server.port to Spring config")

            # Fix 3: Fix H2 console path if H2 is used
            if 'h2' in content.lower() and 'spring.h2.console.enabled' not in content:
                if '=' in content:  # .properties format
                    content += '\nspring.h2.console.enabled=true\n'
                    self.fixes_applied.append("Enabled H2 console in Spring config")

            if content != original:
                logger.info(f"[Sanitizer] Spring config fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] Spring config sanitization failed (returning original): {e}")
            return original

    # =========================================================================
    # AI/ML PROJECT SANITIZERS
    # =========================================================================

    def _sanitize_conda_env(self, content: str) -> str:
        """
        Sanitize Conda environment.yml to fix common issues.

        Fixes:
        1. Ensure name field exists
        2. Fix channel ordering (conda-forge should be first for ML packages)
        3. Fix common package name typos

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Ensure name field exists
            if 'name:' not in content:
                content = 'name: ml-env\n' + content
                self.fixes_applied.append("Added missing name field to environment.yml")

            # Fix 2: Ensure channels section exists with conda-forge
            if 'channels:' not in content:
                # Add channels after name
                content = re.sub(
                    r'(name:\s*\S+)',
                    r'\1\nchannels:\n  - conda-forge\n  - defaults',
                    content,
                    count=1
                )
                self.fixes_applied.append("Added channels section to environment.yml")

            # Fix 3: Common ML package typos
            typo_fixes = {
                'tensorflow-gpu': 'tensorflow',  # GPU version is deprecated
                'pytorch': 'torch',  # Common mistake
                'scikit_learn': 'scikit-learn',
                'opencv': 'opencv-python',
            }
            for typo, correct in typo_fixes.items():
                if typo in content and correct not in content:
                    content = content.replace(typo, correct)
                    self.fixes_applied.append(f"Fixed package name: {typo} -> {correct}")

            if content != original:
                logger.info(f"[Sanitizer] environment.yml fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] environment.yml sanitization failed (returning original): {e}")
            return original

    def _sanitize_pyproject_toml(self, content: str) -> str:
        """
        Sanitize pyproject.toml to fix common issues.

        Fixes:
        1. Ensure [project] or [tool.poetry] section exists
        2. Fix missing required fields
        3. Fix build system declaration

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Ensure build-system exists
            if '[build-system]' not in content:
                content = '[build-system]\nrequires = ["setuptools>=61.0"]\nbuild-backend = "setuptools.build_meta"\n\n' + content
                self.fixes_applied.append("Added [build-system] section to pyproject.toml")

            # Fix 2: Ensure project section exists
            if '[project]' not in content and '[tool.poetry]' not in content:
                content += '\n[project]\nname = "app"\nversion = "0.1.0"\n'
                self.fixes_applied.append("Added [project] section to pyproject.toml")

            if content != original:
                logger.info(f"[Sanitizer] pyproject.toml fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] pyproject.toml sanitization failed (returning original): {e}")
            return original

    def _sanitize_setup_py(self, content: str) -> str:
        """
        Sanitize setup.py to fix common issues.

        Fixes:
        1. Ensure setup() call exists
        2. Fix common import issues

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Ensure setuptools import
            if 'from setuptools import' not in content and 'import setuptools' not in content:
                content = 'from setuptools import setup, find_packages\n\n' + content
                self.fixes_applied.append("Added setuptools import to setup.py")

            # Fix 2: Ensure setup() call exists
            if 'setup(' not in content:
                content += '\nsetup(\n    name="app",\n    version="0.1.0",\n    packages=find_packages(),\n)\n'
                self.fixes_applied.append("Added setup() call to setup.py")

            if content != original:
                logger.info(f"[Sanitizer] setup.py fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] setup.py sanitization failed (returning original): {e}")
            return original

    def _sanitize_jupyter_notebook(self, content: str) -> str:
        """
        Sanitize Jupyter notebook (.ipynb) to fix common issues.

        Fixes:
        1. Fix invalid JSON structure
        2. Ensure required notebook fields exist
        3. Fix kernel specification

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            import json

            # Parse notebook
            try:
                notebook = json.loads(content)
            except json.JSONDecodeError:
                # Try to fix trailing commas
                fixed_content = re.sub(r',(\s*[}\]])', r'\1', content)
                notebook = json.loads(fixed_content)
                self.fixes_applied.append("Fixed JSON syntax in notebook")

            # Fix 1: Ensure nbformat exists
            if 'nbformat' not in notebook:
                notebook['nbformat'] = 4
                self.fixes_applied.append("Added nbformat to notebook")

            if 'nbformat_minor' not in notebook:
                notebook['nbformat_minor'] = 5
                self.fixes_applied.append("Added nbformat_minor to notebook")

            # Fix 2: Ensure cells array exists
            if 'cells' not in notebook:
                notebook['cells'] = []
                self.fixes_applied.append("Added cells array to notebook")

            # Fix 3: Ensure metadata exists
            if 'metadata' not in notebook:
                notebook['metadata'] = {
                    "kernelspec": {
                        "display_name": "Python 3",
                        "language": "python",
                        "name": "python3"
                    }
                }
                self.fixes_applied.append("Added metadata to notebook")

            content = json.dumps(notebook, indent=2) + '\n'

            if content != original:
                logger.info(f"[Sanitizer] Jupyter notebook fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] Jupyter notebook sanitization failed (returning original): {e}")
            return original

    # =========================================================================
    # BLOCKCHAIN PROJECT SANITIZERS
    # =========================================================================

    def _sanitize_hardhat_config(self, content: str) -> str:
        """
        Sanitize Hardhat config to fix common issues.

        Fixes:
        1. Fix missing module.exports or export default
        2. Ensure solidity version is specified
        3. Fix network configuration

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Ensure exports exist
            if 'module.exports' not in content and 'export default' not in content:
                content += '\n\nmodule.exports = {\n  solidity: "0.8.19",\n};\n'
                self.fixes_applied.append("Added module.exports to hardhat.config")

            # Fix 2: Ensure solidity version is specified
            if 'solidity' not in content:
                if 'module.exports = {' in content:
                    content = content.replace(
                        'module.exports = {',
                        'module.exports = {\n  solidity: "0.8.19",'
                    )
                    self.fixes_applied.append("Added solidity version to hardhat.config")

            # Fix 3: Fix common hardhat plugin typos
            typo_fixes = [
                ('@nomiclabs/hardhat-waffle', '@nomicfoundation/hardhat-toolbox'),
                ('hardhat-waffle', '@nomicfoundation/hardhat-toolbox'),
            ]
            for typo, correct in typo_fixes:
                if typo in content:
                    content = content.replace(typo, correct)
                    self.fixes_applied.append(f"Updated deprecated plugin: {typo} -> {correct}")

            if content != original:
                logger.info(f"[Sanitizer] hardhat.config fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] hardhat.config sanitization failed (returning original): {e}")
            return original

    def _sanitize_truffle_config(self, content: str) -> str:
        """
        Sanitize Truffle config to fix common issues.

        Fixes:
        1. Fix missing module.exports
        2. Ensure compiler version is specified
        3. Fix network configuration

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Ensure module.exports exists
            if 'module.exports' not in content:
                content = 'module.exports = {\n  compilers: {\n    solc: {\n      version: "0.8.19"\n    }\n  }\n};\n'
                self.fixes_applied.append("Added module.exports to truffle-config")

            # Fix 2: Ensure compiler version
            if 'compilers' not in content and 'solc' not in content:
                if 'module.exports = {' in content:
                    content = content.replace(
                        'module.exports = {',
                        'module.exports = {\n  compilers: {\n    solc: {\n      version: "0.8.19"\n    }\n  },'
                    )
                    self.fixes_applied.append("Added compiler config to truffle-config")

            if content != original:
                logger.info(f"[Sanitizer] truffle-config fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] truffle-config sanitization failed (returning original): {e}")
            return original

    def _sanitize_foundry_toml(self, content: str) -> str:
        """
        Sanitize Foundry configuration to fix common issues.

        Fixes:
        1. Ensure [profile.default] section exists
        2. Fix src/out/libs paths
        3. Fix solidity version

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Ensure profile.default section
            if '[profile.default]' not in content:
                content = '[profile.default]\nsrc = "src"\nout = "out"\nlibs = ["lib"]\nsolc = "0.8.19"\n\n' + content
                self.fixes_applied.append("Added [profile.default] section to foundry.toml")

            # Fix 2: Ensure solc version
            if 'solc' not in content:
                content = content.replace(
                    '[profile.default]',
                    '[profile.default]\nsolc = "0.8.19"'
                )
                self.fixes_applied.append("Added solc version to foundry.toml")

            if content != original:
                logger.info(f"[Sanitizer] foundry.toml fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] foundry.toml sanitization failed (returning original): {e}")
            return original

    def _sanitize_solidity(self, content: str) -> str:
        """
        Sanitize Solidity contracts to fix common issues.

        Fixes:
        1. Ensure SPDX license identifier exists
        2. Ensure pragma solidity version exists
        3. Fix common syntax issues

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Ensure SPDX license (required since Solidity 0.6.8)
            if 'SPDX-License-Identifier' not in content:
                content = '// SPDX-License-Identifier: MIT\n' + content
                self.fixes_applied.append("Added SPDX license identifier to Solidity file")

            # Fix 2: Ensure pragma solidity version
            if 'pragma solidity' not in content:
                # Insert after SPDX
                if 'SPDX-License-Identifier' in content:
                    content = re.sub(
                        r'(// SPDX-License-Identifier:[^\n]*\n)',
                        r'\1pragma solidity ^0.8.19;\n',
                        content,
                        count=1
                    )
                else:
                    content = 'pragma solidity ^0.8.19;\n' + content
                self.fixes_applied.append("Added pragma solidity to Solidity file")

            if content != original:
                logger.info(f"[Sanitizer] Solidity fixes applied: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] Solidity sanitization failed (returning original): {e}")
            return original

    # =========================================================================
    # CYBER SECURITY SANITIZERS
    # =========================================================================

    def _sanitize_docker_compose_security(self, content: str) -> str:
        """
        Sanitize docker-compose.yml for security best practices.

        Fixes:
        1. Remove privileged mode if not needed
        2. Add security_opt for containers
        3. Fix exposed ports (don't bind to 0.0.0.0 by default)
        4. Remove hardcoded secrets

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Warn about privileged mode (don't remove, just log)
            if 'privileged: true' in content:
                logger.warning("[Sanitizer] docker-compose.yml uses privileged mode - security risk!")
                self.fixes_applied.append("WARNING: privileged mode detected")

            # Fix 2: Check for hardcoded passwords (don't remove, just warn)
            password_patterns = [
                r'password:\s*["\']?[^$\s{][^"\'\s]*',  # Not using env vars
                r'MYSQL_ROOT_PASSWORD:\s*["\']?[^$\s{][^"\'\s]*',
                r'POSTGRES_PASSWORD:\s*["\']?[^$\s{][^"\'\s]*',
            ]
            for pattern in password_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    logger.warning("[Sanitizer] docker-compose.yml contains hardcoded password!")
                    self.fixes_applied.append("WARNING: hardcoded password detected - use environment variables")
                    break

            # Fix 3: Check for ports bound to 0.0.0.0
            if re.search(r'ports:\s*\n\s*-\s*["\']?\d+:\d+', content):
                # This binds to all interfaces - might want to use 127.0.0.1
                logger.info("[Sanitizer] docker-compose.yml exposes ports to all interfaces")

            # Fix 4: Ensure version is specified (for older compose files)
            if not content.strip().startswith('version:') and 'services:' in content:
                # Modern compose doesn't need version, but adding for compatibility
                pass  # Don't add version - modern compose doesn't need it

            if self.fixes_applied and content != original:
                logger.info(f"[Sanitizer] docker-compose security checks: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] docker-compose security sanitization failed (returning original): {e}")
            return original

    def _sanitize_security_requirements(self, content: str) -> str:
        """
        Sanitize requirements.txt for security projects.

        Fixes:
        1. Ensure essential security packages have versions
        2. Fix common package name typos
        3. Add recommended security packages if missing

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            lines = content.split('\n')
            new_lines = []
            has_cryptography = False
            has_requests = False

            # Essential security packages with recommended versions
            security_packages = {
                'cryptography': 'cryptography>=41.0.0',
                'paramiko': 'paramiko>=3.0.0',
                'scapy': 'scapy>=2.5.0',
                'python-nmap': 'python-nmap>=0.7.1',
                'requests': 'requests>=2.31.0',
                'beautifulsoup4': 'beautifulsoup4>=4.12.0',
            }

            # Common typos
            typo_fixes = {
                'cyptography': 'cryptography',
                'crytography': 'cryptography',
                'paramioko': 'paramiko',
                'scappy': 'scapy',
                'beutifulsoup': 'beautifulsoup4',
                'beautifulsoup': 'beautifulsoup4',
            }

            for line in lines:
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    new_lines.append(line)
                    continue

                # Fix typos
                pkg_name = stripped.split('==')[0].split('>=')[0].split('<=')[0].lower()
                if pkg_name in typo_fixes:
                    corrected = typo_fixes[pkg_name]
                    line = line.replace(stripped.split('==')[0].split('>=')[0].split('<=')[0], corrected)
                    self.fixes_applied.append(f"Fixed typo: {pkg_name} -> {corrected}")

                # Track essential packages
                if 'cryptography' in line.lower():
                    has_cryptography = True
                if 'requests' in line.lower():
                    has_requests = True

                new_lines.append(line)

            # Add essential packages if missing
            if not has_cryptography:
                new_lines.append(security_packages['cryptography'])
                self.fixes_applied.append("Added cryptography package")

            if not has_requests:
                new_lines.append(security_packages['requests'])
                self.fixes_applied.append("Added requests package")

            content = '\n'.join(new_lines)

            if self.fixes_applied:
                logger.info(f"[Sanitizer] Security requirements.txt fixes: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] Security requirements.txt sanitization failed (returning original): {e}")
            return original

    def _sanitize_security_scanner_py(self, content: str) -> str:
        """
        Sanitize Python security scanner scripts.

        Fixes:
        1. Add proper exception handling for network operations
        2. Add timeout parameters to socket/request calls
        3. Add input validation warnings

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Ensure socket operations have timeout
            if 'socket.socket' in content and 'settimeout' not in content:
                # Add a comment warning about timeout
                if 'import socket' in content:
                    content = content.replace(
                        'import socket',
                        'import socket  # Remember to use settimeout() for network operations'
                    )
                    self.fixes_applied.append("Added timeout reminder for socket operations")

            # Fix 2: Ensure requests have timeout
            if 'requests.get' in content or 'requests.post' in content:
                if 'timeout=' not in content and 'timeout:' not in content:
                    self.fixes_applied.append("WARNING: requests calls should include timeout parameter")

            # Fix 3: Check for proper error handling
            if 'socket.connect' in content or 'requests.get' in content:
                if 'try:' not in content and 'except' not in content:
                    self.fixes_applied.append("WARNING: Network operations should have try/except blocks")

            # Fix 4: Ensure proper imports for type hints
            if 'def scan' in content or 'def check' in content:
                if 'from typing import' not in content and 'from typing' not in content:
                    if content.startswith('import') or content.startswith('from'):
                        content = 'from typing import List, Dict, Optional, Tuple\n' + content
                    else:
                        content = 'from typing import List, Dict, Optional, Tuple\n\n' + content
                    self.fixes_applied.append("Added typing imports for type hints")

            if self.fixes_applied:
                logger.info(f"[Sanitizer] Security scanner.py fixes: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] Security scanner.py sanitization failed (returning original): {e}")
            return original

    def _sanitize_encryption_py(self, content: str) -> str:
        """
        Sanitize Python encryption utility scripts.

        Fixes:
        1. Ensure proper cryptography imports
        2. Add security warnings for weak algorithms
        3. Ensure proper key handling

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Warn about weak algorithms
            weak_algorithms = ['md5', 'sha1', 'des', 'rc4', 'blowfish']
            for algo in weak_algorithms:
                if algo in content.lower() and 'hashlib' in content:
                    self.fixes_applied.append(f"WARNING: {algo.upper()} is considered weak - use SHA-256 or better")

            # Fix 2: Ensure secrets module for key generation
            if 'random' in content and 'secrets' not in content:
                if 'import random' in content:
                    content = content.replace(
                        'import random',
                        'import random\nimport secrets  # Use secrets for cryptographic randomness'
                    )
                    self.fixes_applied.append("Added secrets module import (use instead of random for crypto)")

            # Fix 3: Add proper imports if using cryptography
            if 'Fernet' in content and 'from cryptography.fernet import Fernet' not in content:
                if 'import Fernet' in content:
                    content = content.replace(
                        'import Fernet',
                        'from cryptography.fernet import Fernet'
                    )
                    self.fixes_applied.append("Fixed Fernet import")

            # Fix 4: Ensure proper error handling for decryption
            if 'decrypt' in content:
                if 'InvalidToken' not in content and 'try:' not in content:
                    self.fixes_applied.append("WARNING: Decryption should handle InvalidToken exception")

            if self.fixes_applied:
                logger.info(f"[Sanitizer] Encryption.py fixes: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] Encryption.py sanitization failed (returning original): {e}")
            return original

    def _sanitize_security_config_yaml(self, content: str) -> str:
        """
        Sanitize security configuration YAML files.

        Fixes:
        1. Ensure scan targets are not hardcoded production IPs
        2. Check for proper timeout settings
        3. Validate port ranges

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Warn about hardcoded IPs that look like production
            production_ip_patterns = [
                r'\b(?:10\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.)',
                r'\b(?:172\.(?:1[6-9]|2[0-9]|3[0-1])\.)',
                r'\b(?:192\.168\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.)',
            ]
            for pattern in production_ip_patterns:
                if re.search(pattern, content):
                    self.fixes_applied.append("WARNING: Config contains internal IP ranges - ensure authorized for testing")
                    break

            # Fix 2: Ensure timeout is reasonable
            if 'timeout:' in content:
                timeout_match = re.search(r'timeout:\s*(\d+)', content)
                if timeout_match:
                    timeout_val = int(timeout_match.group(1))
                    if timeout_val > 60:
                        self.fixes_applied.append("WARNING: High timeout value may cause slow scans")
                    elif timeout_val < 1:
                        content = re.sub(r'timeout:\s*\d+', 'timeout: 5', content)
                        self.fixes_applied.append("Fixed too-low timeout value (set to 5s)")

            # Fix 3: Validate port ranges
            port_match = re.search(r'ports:\s*\[([^\]]+)\]', content)
            if port_match:
                port_str = port_match.group(1)
                if '65536' in port_str or '100000' in port_str:
                    self.fixes_applied.append("WARNING: Invalid port numbers detected (max is 65535)")

            if self.fixes_applied:
                logger.info(f"[Sanitizer] security_config.yaml fixes: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] security_config.yaml sanitization failed (returning original): {e}")
            return original

    def _sanitize_log_analyzer_py(self, content: str) -> str:
        """
        Sanitize Python log analyzer scripts for security projects.

        Fixes:
        1. Ensure proper file handling (with statement)
        2. Add regex import if using patterns
        3. Ensure proper exception handling for file operations

        FAIL-SAFE: Returns original content if any error occurs.
        """
        original = content

        try:
            # Fix 1: Ensure 're' module is imported if regex is used
            if 're.search' in content or 're.match' in content or 're.findall' in content:
                if 'import re' not in content:
                    if content.startswith('import') or content.startswith('from'):
                        content = 'import re\n' + content
                    else:
                        content = 'import re\n\n' + content
                    self.fixes_applied.append("Added missing 're' module import")

            # Fix 2: Ensure collections import for defaultdict
            if 'defaultdict' in content and 'from collections' not in content:
                if 'import re' in content:
                    content = content.replace(
                        'import re',
                        'import re\nfrom collections import defaultdict'
                    )
                else:
                    content = 'from collections import defaultdict\n' + content
                self.fixes_applied.append("Added defaultdict import")

            # Fix 3: Warn about file handling without 'with'
            if 'open(' in content and 'with open' not in content:
                self.fixes_applied.append("WARNING: Use 'with open()' for proper file handling")

            # Fix 4: Ensure datetime import for timestamp parsing
            if 'datetime' in content.lower() and 'from datetime import' not in content and 'import datetime' not in content:
                content = 'from datetime import datetime\n' + content
                self.fixes_applied.append("Added datetime import")

            if self.fixes_applied:
                logger.info(f"[Sanitizer] Log analyzer.py fixes: {self.fixes_applied}")

            return content

        except Exception as e:
            logger.warning(f"[Sanitizer] Log analyzer.py sanitization failed (returning original): {e}")
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
