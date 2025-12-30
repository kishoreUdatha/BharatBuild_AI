"""
Import Validator Service

Validates that all imports in generated React/TypeScript files have corresponding
files generated. This fixes the "AI generation gap" where Claude creates App.tsx
with imports for pages/components that were not included in the original plan.

Usage:
    from app.services.import_validator import import_validator

    # After file generation
    missing_files = import_validator.find_missing_imports(generated_files)
    if missing_files:
        # Generate missing files or add to pending queue
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field

from app.core.logging_config import logger


@dataclass
class MissingImport:
    """Represents a missing imported file"""
    path: str
    description: str
    imported_by: str
    import_name: str
    priority: int = 50


@dataclass
class ValidationResult:
    """Result of import validation"""
    valid: bool
    missing_files: List[MissingImport] = field(default_factory=list)
    scanned_files: int = 0
    total_imports: int = 0


class ImportValidatorService:
    """
    Service to validate that all imports in generated files have corresponding files.

    This catches the "AI generation gap" where:
    - Planner lists 70 files
    - Writer generates App.tsx with imports for 85 files
    - 15 files are missing and cause build errors

    The auto-fixer catches these at runtime, but this service can detect them
    proactively after generation.
    """

    # Entry files to scan for imports (most likely to have many imports)
    ENTRY_FILES = {
        'App.tsx', 'App.jsx', 'App.ts', 'App.js',
        'main.tsx', 'main.jsx', 'main.ts', 'main.js',
        'index.tsx', 'index.jsx', 'index.ts', 'index.js',
        'routes.tsx', 'router.tsx', 'Routes.tsx', 'Router.tsx'
    }

    # Import patterns for React/TypeScript
    IMPORT_PATTERNS = [
        # import X from './path'
        re.compile(r"import\s+(?:\{[^}]+\}|\w+)\s+from\s+['\"](\.[^'\"]+)['\"]"),
        # import X from '@/path' (common alias)
        re.compile(r"import\s+(?:\{[^}]+\}|\w+)\s+from\s+['\"]@/([^'\"]+)['\"]"),
        # import X from 'components/path' or 'pages/path' (relative to src)
        re.compile(r"import\s+(?:\{[^}]+\}|\w+)\s+from\s+['\"](?:components|pages|hooks|utils|contexts|types)/([^'\"]+)['\"]"),
    ]

    # Extensions to try when resolving imports
    EXTENSIONS = ['', '.tsx', '.ts', '.jsx', '.js', '/index.tsx', '/index.ts', '/index.jsx', '/index.js']

    # Skip these patterns (node_modules, external packages)
    SKIP_PATTERNS = [
        re.compile(r'^react'),
        re.compile(r'^@tanstack'),
        re.compile(r'^lucide-react'),
        re.compile(r'^react-router'),
        re.compile(r'^@radix'),
        re.compile(r'^framer-motion'),
        re.compile(r'^axios'),
        re.compile(r'^date-fns'),
        re.compile(r'^clsx'),
        re.compile(r'^tailwind'),
    ]

    def find_missing_imports(
        self,
        files_created: List[Dict],
        project_base: str = "frontend"
    ) -> ValidationResult:
        """
        Scan generated files for imports and check if imported files exist.

        Args:
            files_created: List of file dicts with 'path' and 'content' keys
            project_base: Base directory for the project (e.g., 'frontend')

        Returns:
            ValidationResult with list of missing files
        """
        # Build set of generated file paths
        generated_paths: Set[str] = set()
        for f in files_created:
            path = f.get('path', '')
            if path:
                # Normalize path
                path = path.replace('\\', '/').replace('//', '/')
                generated_paths.add(path)
                # Also add without extension for flexibility
                for ext in ['.tsx', '.ts', '.jsx', '.js']:
                    if path.endswith(ext):
                        generated_paths.add(path[:-len(ext)])

        missing_files: List[MissingImport] = []
        scanned_files = 0
        total_imports = 0
        seen_missing: Set[str] = set()  # Avoid duplicates

        for file_info in files_created:
            file_path = file_info.get('path', '')
            file_content = file_info.get('content', '')

            # Check if this is an entry file or a router file
            file_name = Path(file_path).name if file_path else ''
            is_entry = file_name in self.ENTRY_FILES
            is_router = 'route' in file_name.lower() or 'router' in file_name.lower()

            if not (is_entry or is_router):
                continue

            if not file_content:
                continue

            scanned_files += 1

            # Get the base directory of the file
            file_dir = str(Path(file_path).parent) if file_path else ''

            # Extract all imports
            for pattern in self.IMPORT_PATTERNS:
                matches = pattern.findall(file_content)
                for match in matches:
                    total_imports += 1
                    import_path = match.strip()

                    # Skip external packages
                    if self._is_external_import(import_path):
                        continue

                    # Resolve the import path to actual file path
                    resolved_path = self._resolve_import_path(
                        import_path, file_dir, project_base
                    )

                    if not resolved_path:
                        continue

                    # Check if file exists
                    if self._file_exists(resolved_path, generated_paths):
                        continue

                    # File is missing
                    if resolved_path not in seen_missing:
                        seen_missing.add(resolved_path)

                        component_name = Path(import_path).stem
                        missing_files.append(MissingImport(
                            path=resolved_path,
                            description=f"Missing React component/page: {component_name}. Imported in {file_name} but not generated.",
                            imported_by=file_path,
                            import_name=component_name,
                            priority=self._get_priority(import_path)
                        ))

                        logger.warning(
                            f"[ImportValidator] Missing file: {resolved_path} "
                            f"(imported in {file_path})"
                        )

        is_valid = len(missing_files) == 0

        if missing_files:
            logger.info(
                f"[ImportValidator] Found {len(missing_files)} missing files "
                f"(scanned {scanned_files} entry files, {total_imports} imports)"
            )
        else:
            logger.info(
                f"[ImportValidator] All imports valid "
                f"(scanned {scanned_files} entry files, {total_imports} imports)"
            )

        return ValidationResult(
            valid=is_valid,
            missing_files=missing_files,
            scanned_files=scanned_files,
            total_imports=total_imports
        )

    def _is_external_import(self, import_path: str) -> bool:
        """Check if import is an external package (node_modules)"""
        # Relative imports start with . or are known internal patterns
        if import_path.startswith('.'):
            return False
        if import_path.startswith('@/'):
            return False
        if import_path.startswith('components/'):
            return False
        if import_path.startswith('pages/'):
            return False
        if import_path.startswith('hooks/'):
            return False
        if import_path.startswith('utils/'):
            return False
        if import_path.startswith('contexts/'):
            return False
        if import_path.startswith('types/'):
            return False

        # Check skip patterns
        for pattern in self.SKIP_PATTERNS:
            if pattern.match(import_path):
                return True

        return True  # Default to external

    def _resolve_import_path(
        self,
        import_path: str,
        file_dir: str,
        project_base: str
    ) -> Optional[str]:
        """Resolve relative import to absolute file path"""

        # Handle @/ alias (points to src/)
        if import_path.startswith('@/'):
            import_path = import_path[2:]  # Remove @/
            resolved = f"{project_base}/src/{import_path}"

        # Handle ../ (parent directory)
        elif import_path.startswith('../'):
            # Count how many levels up
            levels_up = 0
            temp_path = import_path
            while temp_path.startswith('../'):
                levels_up += 1
                temp_path = temp_path[3:]

            # Go up in file_dir
            parent = Path(file_dir)
            for _ in range(levels_up):
                parent = parent.parent

            resolved = f"{parent}/{temp_path}"

        # Handle ./ (same directory)
        elif import_path.startswith('./'):
            import_path = import_path[2:]  # Remove ./
            resolved = f"{file_dir}/{import_path}"

        # Handle bare paths like 'pages/HomePage'
        elif import_path.startswith(('pages/', 'components/', 'hooks/', 'utils/', 'contexts/', 'types/')):
            resolved = f"{project_base}/src/{import_path}"

        else:
            return None  # Can't resolve

        # Normalize
        resolved = resolved.replace('\\', '/').replace('//', '/')

        # Add .tsx if no extension
        if not any(resolved.endswith(ext) for ext in ['.tsx', '.ts', '.jsx', '.js']):
            resolved = resolved + '.tsx'

        return resolved

    def _file_exists(self, path: str, generated_paths: Set[str]) -> bool:
        """Check if file exists in generated paths, trying multiple extensions"""
        path = path.replace('\\', '/').replace('//', '/')

        # Direct match
        if path in generated_paths:
            return True

        # Try without extension
        for ext in ['.tsx', '.ts', '.jsx', '.js']:
            if path.endswith(ext):
                base = path[:-len(ext)]
                if base in generated_paths:
                    return True

        # Try with different extensions
        base = path
        for ext in ['.tsx', '.ts', '.jsx', '.js']:
            if path.endswith(ext):
                base = path[:-len(ext)]
                break

        for ext in self.EXTENSIONS:
            test_path = base + ext
            if test_path in generated_paths:
                return True

        return False

    def _get_priority(self, import_path: str) -> int:
        """Get generation priority based on file type"""
        if 'page' in import_path.lower():
            return 45  # Pages are important
        if 'component' in import_path.lower():
            return 50
        if 'hook' in import_path.lower():
            return 40
        if 'context' in import_path.lower():
            return 35
        if 'util' in import_path.lower():
            return 55
        if 'type' in import_path.lower():
            return 30
        return 50

    def get_missing_files_for_generation(
        self,
        files_created: List[Dict],
        project_base: str = "frontend"
    ) -> List[Dict]:
        """
        Get missing files in a format ready for the Writer Agent to generate.

        Returns:
            List of file dicts with 'path', 'description', 'priority'
        """
        result = self.find_missing_imports(files_created, project_base)

        return [
            {
                'path': m.path,
                'description': m.description,
                'priority': m.priority
            }
            for m in result.missing_files
        ]


# Singleton instance
import_validator = ImportValidatorService()
