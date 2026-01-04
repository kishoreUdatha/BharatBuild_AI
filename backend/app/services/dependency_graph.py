"""
Dependency Graph - Import chain awareness for cascading error fixes

Features:
1. Build import dependency graph from source files
2. Detect root cause files (depended upon by error files)
3. Order fixes by dependency (fix dependencies first)
4. Identify cascading error patterns
"""

import re
from typing import Dict, Set, List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict

from app.core.logging_config import logger


@dataclass
class FileNode:
    """Node in the dependency graph"""
    path: str
    class_name: str
    package: str = ""
    imports: Set[str] = field(default_factory=set)
    imported_by: Set[str] = field(default_factory=set)
    has_error: bool = False
    error_line: int = 0


class DependencyGraph:
    """
    Build and analyze import dependency graphs.

    Supports:
    - Java (import statements)
    - TypeScript/JavaScript (import/require)
    - Python (import/from statements)
    """

    def __init__(self):
        self._nodes: Dict[str, FileNode] = {}
        self._class_to_file: Dict[str, str] = {}  # Maps class names to file paths

    # Supported file extensions for dependency graph
    SUPPORTED_EXTENSIONS = [
        # JavaScript/TypeScript
        "*.ts", "*.tsx", "*.js", "*.jsx",
        # Java
        "*.java",
        # Python
        "*.py",
        # Go
        "*.go",
        # Rust
        "*.rs",
        # C/C++
        "*.c", "*.cpp", "*.cc", "*.h", "*.hpp",
        # C#
        "*.cs",
        # PHP
        "*.php",
        # Ruby
        "*.rb",
        # Dart/Flutter
        "*.dart",
        # Solidity
        "*.sol",
    ]

    def build_from_files(
        self,
        project_path: Path,
        file_reader: Optional[Callable[[str], Optional[str]]] = None,
        file_lister: Optional[Callable[[str, str], List[str]]] = None
    ) -> None:
        """
        Build dependency graph from project files.

        Args:
            project_path: Root path of the project
            file_reader: Optional callback to read files (for remote sandbox)
            file_lister: Optional callback to list files (for remote sandbox)
        """
        # Find all source files
        all_files = []
        project_str = str(project_path)

        if file_lister:
            # Use sandbox file lister for all supported extensions
            for ext in self.SUPPORTED_EXTENSIONS:
                try:
                    all_files.extend(file_lister(project_str, ext))
                except Exception:
                    pass  # Skip if extension not supported
        else:
            # Use local glob for all supported extensions
            import glob
            for ext in self.SUPPORTED_EXTENSIONS:
                all_files.extend(glob.glob(f"{project_str}/**/{ext}", recursive=True))

        logger.info(f"[DependencyGraph] Building graph from {len(all_files)} files")

        # Parse each file
        for file_path in all_files:
            try:
                # Read file content
                if file_reader:
                    content = file_reader(file_path)
                else:
                    content = Path(file_path).read_text(encoding='utf-8')

                if content:
                    self._parse_file(file_path, content, project_path)
            except Exception as e:
                logger.debug(f"[DependencyGraph] Could not parse {file_path}: {e}")

        # Build reverse dependencies (imported_by)
        self._build_reverse_dependencies()

        logger.info(
            f"[DependencyGraph] Built graph: {len(self._nodes)} nodes, "
            f"{sum(len(n.imports) for n in self._nodes.values())} edges"
        )

    def _parse_file(self, file_path: str, content: str, project_path: Path) -> None:
        """Parse a file and extract its imports"""
        path_obj = Path(file_path)
        ext = path_obj.suffix.lower()
        class_name = path_obj.stem

        try:
            rel_path = str(path_obj.relative_to(project_path))
        except ValueError:
            rel_path = file_path

        node = FileNode(
            path=rel_path,
            class_name=class_name,
            imports=set()
        )

        if ext == '.java':
            node.package, node.imports = self._parse_java_imports(content)
            # Map fully qualified class name to file
            if node.package:
                fqn = f"{node.package}.{class_name}"
                self._class_to_file[fqn] = rel_path
            self._class_to_file[class_name] = rel_path

        elif ext in ('.ts', '.tsx', '.js', '.jsx'):
            node.imports = self._parse_js_imports(content, rel_path)

        elif ext == '.py':
            node.imports = self._parse_python_imports(content)

        elif ext == '.go':
            node.imports = self._parse_go_imports(content)

        elif ext == '.rs':
            node.imports = self._parse_rust_imports(content)

        elif ext in ('.c', '.cpp', '.cc', '.h', '.hpp'):
            node.imports = self._parse_c_imports(content)

        elif ext == '.cs':
            node.imports = self._parse_csharp_imports(content)

        elif ext == '.php':
            node.imports = self._parse_php_imports(content)

        elif ext == '.rb':
            node.imports = self._parse_ruby_imports(content)

        elif ext == '.dart':
            node.imports = self._parse_dart_imports(content, rel_path)

        elif ext == '.sol':
            node.imports = self._parse_solidity_imports(content)

        self._nodes[rel_path] = node

    def _parse_java_imports(self, content: str) -> Tuple[str, Set[str]]:
        """Parse Java import statements"""
        imports = set()
        package = ""

        # Extract package
        pkg_match = re.search(r'package\s+([\w.]+)\s*;', content)
        if pkg_match:
            package = pkg_match.group(1)

        # Extract imports
        import_pattern = r'import\s+(?:static\s+)?([\w.]+)(?:\.\*)?;'
        for match in re.finditer(import_pattern, content):
            import_path = match.group(1)
            # Get class name (last part)
            class_name = import_path.split('.')[-1]
            imports.add(class_name)
            imports.add(import_path)  # Also add full path

        # Extract class references from the code (for same-package refs)
        class_ref_pattern = r'\b([A-Z][a-zA-Z0-9]*)\s*(?:\(|<|\.)'
        for match in re.finditer(class_ref_pattern, content):
            class_name = match.group(1)
            if class_name not in ('String', 'Integer', 'Boolean', 'Object', 'List', 'Map', 'Set', 'Optional'):
                imports.add(class_name)

        return package, imports

    def _parse_js_imports(self, content: str, file_path: str) -> Set[str]:
        """Parse JavaScript/TypeScript import statements"""
        imports = set()
        base_dir = str(Path(file_path).parent)

        # ES6 imports: import X from './file'
        import_pattern = r'import\s+.*?\s+from\s+[\'"]([^"\']+)[\'"]'
        for match in re.finditer(import_pattern, content):
            import_path = match.group(1)
            if import_path.startswith('.'):
                # Relative import - resolve to file path
                resolved = self._resolve_js_import(base_dir, import_path)
                if resolved:
                    imports.add(resolved)
            else:
                # Node module import
                imports.add(import_path)

        # require() calls
        require_pattern = r'require\s*\(\s*[\'"]([^"\']+)[\'"]\s*\)'
        for match in re.finditer(require_pattern, content):
            import_path = match.group(1)
            if import_path.startswith('.'):
                resolved = self._resolve_js_import(base_dir, import_path)
                if resolved:
                    imports.add(resolved)
            else:
                imports.add(import_path)

        return imports

    def _resolve_js_import(self, base_dir: str, import_path: str) -> Optional[str]:
        """Resolve relative JS/TS import to file path"""
        # Normalize path
        import_path = import_path.replace('\\', '/')
        base_dir = base_dir.replace('\\', '/')

        # Simple resolution - add common extensions
        base = Path(base_dir) / import_path
        for ext in ['', '.ts', '.tsx', '.js', '.jsx', '/index.ts', '/index.tsx', '/index.js']:
            candidate = str(base) + ext
            candidate = candidate.replace('\\', '/')
            # Normalize the path
            try:
                candidate = str(Path(candidate).resolve())
            except:
                pass
            return candidate.replace('\\', '/')

        return None

    def _parse_python_imports(self, content: str) -> Set[str]:
        """Parse Python import statements"""
        imports = set()

        # import X, Y, Z
        import_pattern = r'^import\s+(.+)$'
        for match in re.finditer(import_pattern, content, re.MULTILINE):
            modules = match.group(1).split(',')
            for mod in modules:
                mod = mod.strip().split(' as ')[0]  # Remove 'as alias'
                imports.add(mod.split('.')[0])  # Add root module

        # from X import Y
        from_pattern = r'^from\s+([\w.]+)\s+import'
        for match in re.finditer(from_pattern, content, re.MULTILINE):
            module = match.group(1)
            imports.add(module.split('.')[0])
            imports.add(module)

        return imports

    def _parse_go_imports(self, content: str) -> Set[str]:
        """Parse Go import statements"""
        imports = set()

        # Single import: import "fmt"
        single_pattern = r'import\s+"([^"]+)"'
        for match in re.finditer(single_pattern, content):
            imports.add(match.group(1))

        # Multi import: import ( "fmt" "os" )
        multi_pattern = r'import\s*\(([\s\S]*?)\)'
        for match in re.finditer(multi_pattern, content):
            block = match.group(1)
            for line in block.split('\n'):
                pkg_match = re.search(r'"([^"]+)"', line)
                if pkg_match:
                    imports.add(pkg_match.group(1))

        return imports

    def _parse_rust_imports(self, content: str) -> Set[str]:
        """Parse Rust use statements"""
        imports = set()

        # use statements: use std::io;
        use_pattern = r'use\s+([\w:]+)'
        for match in re.finditer(use_pattern, content):
            path = match.group(1)
            imports.add(path.split('::')[0])  # Add crate name
            imports.add(path)

        # extern crate
        extern_pattern = r'extern\s+crate\s+(\w+)'
        for match in re.finditer(extern_pattern, content):
            imports.add(match.group(1))

        # mod statements
        mod_pattern = r'mod\s+(\w+)\s*;'
        for match in re.finditer(mod_pattern, content):
            imports.add(match.group(1))

        return imports

    def _parse_c_imports(self, content: str) -> Set[str]:
        """Parse C/C++ #include statements"""
        imports = set()

        # #include <header.h> or #include "header.h"
        include_pattern = r'#include\s*[<"]([^>"]+)[>"]'
        for match in re.finditer(include_pattern, content):
            header = match.group(1)
            imports.add(header)
            # Also add base name
            imports.add(Path(header).stem)

        return imports

    def _parse_csharp_imports(self, content: str) -> Set[str]:
        """Parse C# using statements"""
        imports = set()

        # using statements
        using_pattern = r'using\s+([\w.]+)\s*;'
        for match in re.finditer(using_pattern, content):
            namespace = match.group(1)
            imports.add(namespace)
            imports.add(namespace.split('.')[0])  # Root namespace

        return imports

    def _parse_php_imports(self, content: str) -> Set[str]:
        """Parse PHP use/require/include statements"""
        imports = set()

        # use statements
        use_pattern = r'use\s+([\w\\]+)'
        for match in re.finditer(use_pattern, content):
            imports.add(match.group(1).replace('\\', '/'))

        # require/include
        require_pattern = r'(?:require|include)(?:_once)?\s*[\'"]([^"\']+)[\'"]'
        for match in re.finditer(require_pattern, content):
            imports.add(match.group(1))

        return imports

    def _parse_ruby_imports(self, content: str) -> Set[str]:
        """Parse Ruby require/load statements"""
        imports = set()

        # require statements
        require_pattern = r'require\s+[\'"]([^"\']+)[\'"]'
        for match in re.finditer(require_pattern, content):
            imports.add(match.group(1))

        # require_relative
        require_rel_pattern = r'require_relative\s+[\'"]([^"\']+)[\'"]'
        for match in re.finditer(require_rel_pattern, content):
            imports.add(match.group(1))

        # load statements
        load_pattern = r'load\s+[\'"]([^"\']+)[\'"]'
        for match in re.finditer(load_pattern, content):
            imports.add(match.group(1))

        return imports

    def _parse_dart_imports(self, content: str, file_path: str) -> Set[str]:
        """Parse Dart import statements"""
        imports = set()
        base_dir = str(Path(file_path).parent)

        # import statements
        import_pattern = r'import\s+[\'"]([^"\']+)[\'"]'
        for match in re.finditer(import_pattern, content):
            import_path = match.group(1)
            if import_path.startswith('package:'):
                # Package import
                imports.add(import_path.split(':')[1].split('/')[0])
            else:
                imports.add(import_path)

        # part/part of
        part_pattern = r'part\s+[\'"]([^"\']+)[\'"]'
        for match in re.finditer(part_pattern, content):
            imports.add(match.group(1))

        return imports

    def _parse_solidity_imports(self, content: str) -> Set[str]:
        """Parse Solidity import statements"""
        imports = set()

        # import "file.sol";
        import_pattern = r'import\s+[\'"]([^"\']+)[\'"]'
        for match in re.finditer(import_pattern, content):
            imports.add(match.group(1))

        # import {Symbol} from "file.sol";
        import_from_pattern = r'import\s+\{[^}]+\}\s+from\s+[\'"]([^"\']+)[\'"]'
        for match in re.finditer(import_from_pattern, content):
            imports.add(match.group(1))

        return imports

    def _build_reverse_dependencies(self) -> None:
        """Build imported_by relationships"""
        for path, node in self._nodes.items():
            for import_name in node.imports:
                # Find the file that exports this import
                target_path = self._find_import_target(import_name)
                if target_path and target_path in self._nodes:
                    self._nodes[target_path].imported_by.add(path)

    def _find_import_target(self, import_name: str) -> Optional[str]:
        """Find the file path for an import"""
        # Check class-to-file mapping
        if import_name in self._class_to_file:
            return self._class_to_file[import_name]

        # Check if it's a file path
        for path in self._nodes.keys():
            if import_name in path or Path(path).stem == import_name:
                return path

        return None

    def mark_error_files(self, error_files: List[Tuple[str, int]]) -> None:
        """Mark files that have errors"""
        for file_path, line_number in error_files:
            # Normalize path
            file_path = file_path.replace('\\', '/')

            # Try to find matching node
            for node_path, node in self._nodes.items():
                if file_path in node_path or node_path in file_path or Path(node_path).stem == Path(file_path).stem:
                    node.has_error = True
                    node.error_line = line_number
                    break

    def get_root_cause_files(self, error_files: List[Tuple[str, int]]) -> List[Tuple[str, int, str]]:
        """
        Get root cause files that should be fixed first.

        A root cause file is one that:
        1. Is imported by error files
        2. Has no dependencies with errors
        3. Or is a DTO/Entity (likely source of "cannot find symbol")

        Returns:
            List of (file_path, line_number, reason) tuples sorted by fix priority
        """
        self.mark_error_files(error_files)

        root_causes = []
        error_paths = {f for f, _ in error_files}

        for path, node in self._nodes.items():
            if not node.has_error:
                continue

            # Calculate root cause score
            score = 0
            reason = []

            # Score 1: Files imported by many error files
            error_dependents = sum(1 for dep in node.imported_by if self._is_error_file(dep))
            if error_dependents > 0:
                score += error_dependents * 30
                reason.append(f"imported by {error_dependents} error files")

            # Score 2: DTO/Entity files (often root cause)
            if 'Dto' in node.class_name or 'DTO' in node.class_name:
                score += 100
                reason.append("DTO file")
            if 'Entity' in node.class_name:
                score += 80
                reason.append("Entity file")

            # Score 3: Interface files (fix interface before implementation)
            if 'Service' in node.class_name and 'Impl' not in node.class_name:
                score += 60
                reason.append("Service interface")
            if 'Repository' in node.class_name:
                score += 50
                reason.append("Repository")

            # Score 4: Files with no error dependencies (leaf nodes)
            error_dependencies = sum(1 for imp in node.imports if self._is_error_file_by_import(imp))
            if error_dependencies == 0:
                score += 40
                reason.append("no error dependencies")

            if score > 0:
                root_causes.append((path, node.error_line, ", ".join(reason), score))

        # Sort by score (highest first)
        root_causes.sort(key=lambda x: x[3], reverse=True)

        logger.info(f"[DependencyGraph] Found {len(root_causes)} root cause files")
        for path, line, reason, score in root_causes[:5]:
            logger.info(f"  - {Path(path).name}: {reason} (score={score})")

        return [(path, line, reason) for path, line, reason, _ in root_causes]

    def get_fix_order(self, error_files: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
        """
        Get optimal order for fixing files based on dependencies.

        Files that are depended upon should be fixed first.

        Returns:
            List of (file_path, line_number) in optimal fix order
        """
        self.mark_error_files(error_files)

        # Build priority scores
        scored_files = []
        for file_path, line_number in error_files:
            node = self._find_node(file_path)
            if not node:
                scored_files.append((file_path, line_number, 0))
                continue

            # Score based on how many error files depend on this
            dependents = sum(1 for dep in node.imported_by if self._is_error_file(dep))

            # Bonus for specific file types
            type_score = 0
            if 'Dto' in node.class_name or 'DTO' in node.class_name:
                type_score = 100
            elif 'Entity' in node.class_name:
                type_score = 80
            elif 'Service' in node.class_name and 'Impl' not in node.class_name:
                type_score = 60
            elif 'Repository' in node.class_name:
                type_score = 50

            total_score = dependents * 20 + type_score
            scored_files.append((file_path, line_number, total_score))

        # Sort by score (highest first)
        scored_files.sort(key=lambda x: x[2], reverse=True)

        return [(f, l) for f, l, _ in scored_files]

    def get_related_files(self, file_path: str, max_depth: int = 2) -> List[str]:
        """
        Get files related to a given file (imports and imported-by).

        Args:
            file_path: The file to find relations for
            max_depth: Maximum depth to traverse

        Returns:
            List of related file paths
        """
        node = self._find_node(file_path)
        if not node:
            return []

        related = set()
        to_visit = [(node.path, 0)]
        visited = set()

        while to_visit:
            current_path, depth = to_visit.pop(0)
            if current_path in visited or depth > max_depth:
                continue

            visited.add(current_path)
            current_node = self._nodes.get(current_path)
            if not current_node:
                continue

            # Add direct imports
            for imp in current_node.imports:
                target = self._find_import_target(imp)
                if target and target != file_path:
                    related.add(target)
                    if depth < max_depth:
                        to_visit.append((target, depth + 1))

            # Add files that import this
            for dep in current_node.imported_by:
                if dep != file_path:
                    related.add(dep)
                    if depth < max_depth:
                        to_visit.append((dep, depth + 1))

        return list(related)

    def _find_node(self, file_path: str) -> Optional[FileNode]:
        """Find node by file path (with fuzzy matching)"""
        file_path = file_path.replace('\\', '/')

        # Exact match
        if file_path in self._nodes:
            return self._nodes[file_path]

        # Fuzzy match
        for node_path, node in self._nodes.items():
            if file_path in node_path or node_path in file_path:
                return node
            if Path(node_path).stem == Path(file_path).stem:
                return node

        return None

    def _is_error_file(self, file_path: str) -> bool:
        """Check if a file path corresponds to an error file"""
        node = self._find_node(file_path)
        return node.has_error if node else False

    def _is_error_file_by_import(self, import_name: str) -> bool:
        """Check if an import corresponds to an error file"""
        target = self._find_import_target(import_name)
        if target:
            return self._is_error_file(target)
        return False

    def get_stats(self) -> Dict:
        """Get graph statistics"""
        return {
            "total_files": len(self._nodes),
            "total_imports": sum(len(n.imports) for n in self._nodes.values()),
            "error_files": sum(1 for n in self._nodes.values() if n.has_error),
            "java_files": sum(1 for p in self._nodes.keys() if p.endswith('.java')),
            "ts_files": sum(1 for p in self._nodes.keys() if p.endswith('.ts') or p.endswith('.tsx')),
            "py_files": sum(1 for p in self._nodes.keys() if p.endswith('.py'))
        }


# Factory function to create and build a dependency graph
def build_dependency_graph(
    project_path: Path,
    file_reader: Optional[Callable[[str], Optional[str]]] = None,
    file_lister: Optional[Callable[[str, str], List[str]]] = None
) -> DependencyGraph:
    """
    Build a dependency graph for a project.

    Args:
        project_path: Root path of the project
        file_reader: Optional callback to read files (for remote sandbox)
        file_lister: Optional callback to list files (for remote sandbox)

    Returns:
        DependencyGraph instance with parsed dependencies
    """
    graph = DependencyGraph()
    graph.build_from_files(project_path, file_reader, file_lister)
    return graph
