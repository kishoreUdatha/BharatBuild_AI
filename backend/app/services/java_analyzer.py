"""
Java Static Analyzer - Pre-build validation for Java/Spring projects

This analyzer runs AFTER code generation but BEFORE Docker build to catch:
1. Duplicate class names in different packages
2. Missing Lombok annotations (@Data, @Slf4j, @Builder)
3. Missing methods referenced by other classes
4. Wrong import paths
5. Type mismatches between files

The goal is to fix issues BEFORE they become 100 compile errors.
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict

# Use standard logging to avoid config import chain
try:
    from app.core.logging_config import logger
except Exception:
    logger = logging.getLogger(__name__)


@dataclass
class JavaClass:
    """Represents a parsed Java class/interface/enum"""
    name: str
    package: str
    full_name: str  # package.ClassName
    file_path: str
    class_type: str  # class, interface, enum, record
    annotations: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    fields: List[Dict[str, str]] = field(default_factory=list)  # [{name, type}]
    methods: List[Dict[str, Any]] = field(default_factory=list)  # [{name, return_type, params}]
    extends: Optional[str] = None
    implements: List[str] = field(default_factory=list)


@dataclass
class AnalysisIssue:
    """An issue found by the analyzer"""
    severity: str  # error, warning
    issue_type: str
    file_path: str
    line: int
    message: str
    fix_suggestion: Optional[str] = None
    auto_fixable: bool = False


@dataclass
class AnalysisResult:
    """Result of analyzing a Java project"""
    classes: Dict[str, JavaClass]  # full_name -> JavaClass
    issues: List[AnalysisIssue]
    fixes_applied: List[str]


class JavaAnalyzer:
    """
    Static analyzer for Java/Spring Boot projects.

    Catches common issues BEFORE build to prevent 100+ compile errors.
    """

    # Lombok annotations that should be present
    ENTITY_ANNOTATIONS = {'@Entity', '@Data', '@NoArgsConstructor'}
    DTO_ANNOTATIONS = {'@Data', '@NoArgsConstructor', '@AllArgsConstructor'}
    SERVICE_ANNOTATIONS = {'@Service', '@Slf4j', '@RequiredArgsConstructor'}

    # Patterns for parsing Java files
    PACKAGE_PATTERN = re.compile(r'^\s*package\s+([\w.]+)\s*;', re.MULTILINE)
    IMPORT_PATTERN = re.compile(r'^\s*import\s+(?:static\s+)?([\w.*]+)\s*;', re.MULTILINE)
    CLASS_PATTERN = re.compile(
        r'(?:@[\w.]+(?:\([^)]*\))?\s*)*'  # annotations
        r'(?:public\s+|private\s+|protected\s+)?'  # access modifier
        r'(?:abstract\s+|final\s+)?'  # modifiers
        r'(class|interface|enum|record)\s+'  # type
        r'(\w+)'  # name
        r'(?:\s*<[^>]+>)?'  # generics
        r'(?:\s+extends\s+([\w.]+))?'  # extends
        r'(?:\s+implements\s+([\w.,\s]+))?'  # implements
    )
    ANNOTATION_PATTERN = re.compile(r'@(\w+)(?:\([^)]*\))?')
    FIELD_PATTERN = re.compile(
        r'(?:@[\w.]+(?:\([^)]*\))?\s*)*'  # annotations
        r'(?:private|protected|public)\s+'  # access
        r'(?:static\s+)?(?:final\s+)?'  # modifiers
        r'([\w.<>,\s]+?)\s+'  # type
        r'(\w+)\s*'  # name
        r'(?:=|;)'  # assignment or end
    )
    METHOD_PATTERN = re.compile(
        r'(?:@[\w.]+(?:\([^)]*\))?\s*)*'  # annotations
        r'(?:public|private|protected)\s+'  # access
        r'(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?'  # modifiers
        r'([\w.<>,\s]+?)\s+'  # return type
        r'(\w+)\s*'  # method name
        r'\(([^)]*)\)'  # parameters
    )

    def __init__(self):
        self._file_reader = None  # Optional sandbox file reader
        self._file_writer = None  # Optional sandbox file writer
        self._file_lister = None  # Optional sandbox file lister

    def analyze_project(
        self,
        project_path: Path,
        file_reader=None,
        file_writer=None,
        file_lister=None,
        auto_fix: bool = True
    ) -> AnalysisResult:
        """
        Analyze all Java files in a project.

        Args:
            project_path: Root path of the project
            file_reader: Optional callback to read files from sandbox
            file_writer: Optional callback to write files to sandbox
            file_lister: Optional callback to list files from sandbox
            auto_fix: Whether to automatically fix issues

        Returns:
            AnalysisResult with classes, issues, and fixes applied
        """
        self._file_reader = file_reader
        self._file_writer = file_writer
        self._file_lister = file_lister

        logger.info(f"[JavaAnalyzer] Starting analysis of {project_path}")

        # Step 1: Find all Java files
        java_files = self._find_java_files(project_path)
        logger.info(f"[JavaAnalyzer] Found {len(java_files)} Java files")

        # Step 2: Parse all files
        classes: Dict[str, JavaClass] = {}
        for file_path in java_files:
            parsed = self._parse_java_file(file_path, project_path)
            if parsed:
                classes[parsed.full_name] = parsed

        logger.info(f"[JavaAnalyzer] Parsed {len(classes)} classes")

        # Step 3: Detect issues
        issues = []
        issues.extend(self._check_duplicate_classes(classes))
        issues.extend(self._check_missing_lombok(classes))
        issues.extend(self._check_missing_methods(classes))
        issues.extend(self._check_wrong_imports(classes))

        logger.info(f"[JavaAnalyzer] Found {len(issues)} issues")

        # Step 4: Auto-fix if enabled
        fixes_applied = []
        if auto_fix:
            fixes_applied = self._apply_fixes(project_path, classes, issues)
            logger.info(f"[JavaAnalyzer] Applied {len(fixes_applied)} fixes")

        return AnalysisResult(
            classes=classes,
            issues=issues,
            fixes_applied=fixes_applied
        )

    def _find_java_files(self, project_path: Path) -> List[str]:
        """Find all Java files in the project"""
        java_files = []

        if self._file_lister:
            # Use sandbox lister
            try:
                files = self._file_lister(str(project_path), "*.java")
                java_files.extend(files)
            except Exception as e:
                logger.warning(f"[JavaAnalyzer] Sandbox lister failed: {e}")
        else:
            # Use local glob
            for java_file in project_path.rglob("*.java"):
                # Skip test files and generated files
                path_str = str(java_file)
                if '/test/' not in path_str and '/target/' not in path_str:
                    java_files.append(str(java_file))

        return java_files

    def _read_file(self, file_path: str) -> Optional[str]:
        """Read a file using sandbox reader or local read"""
        try:
            if self._file_reader:
                return self._file_reader(file_path)
            else:
                return Path(file_path).read_text(encoding='utf-8')
        except Exception as e:
            logger.warning(f"[JavaAnalyzer] Could not read {file_path}: {e}")
            return None

    def _write_file(self, file_path: str, content: str) -> bool:
        """Write a file using sandbox writer or local write"""
        try:
            if self._file_writer:
                return self._file_writer(file_path, content)
            else:
                Path(file_path).write_text(content, encoding='utf-8')
                return True
        except Exception as e:
            logger.warning(f"[JavaAnalyzer] Could not write {file_path}: {e}")
            return False

    def _parse_java_file(self, file_path: str, project_path: Path) -> Optional[JavaClass]:
        """Parse a Java file and extract class information"""
        content = self._read_file(file_path)
        if not content:
            return None

        # Extract package
        package_match = self.PACKAGE_PATTERN.search(content)
        package = package_match.group(1) if package_match else ""

        # Extract imports
        imports = self.IMPORT_PATTERN.findall(content)

        # Extract class/interface/enum
        class_match = self.CLASS_PATTERN.search(content)
        if not class_match:
            return None

        class_type = class_match.group(1)
        class_name = class_match.group(2)
        extends = class_match.group(3)
        implements_str = class_match.group(4)
        implements = [i.strip() for i in implements_str.split(',')] if implements_str else []

        # Extract annotations (on the class itself)
        # The CLASS_PATTERN includes annotations, so we need to look at the matched section
        class_match_text = class_match.group(0)  # Full match including annotations
        # Also look at 300 chars before the match for multi-line annotations
        class_start = class_match.start()
        pre_class = content[max(0, class_start - 300):class_start]
        annotation_section = pre_class + class_match_text

        # Extract all annotations from this section
        annotations = ['@' + a for a in self.ANNOTATION_PATTERN.findall(annotation_section)]
        # Remove duplicates while preserving order
        seen = set()
        unique_annotations = []
        for a in annotations:
            if a not in seen:
                seen.add(a)
                unique_annotations.append(a)
        annotations = unique_annotations

        # Extract fields
        fields = []
        for match in self.FIELD_PATTERN.finditer(content):
            field_type = match.group(1).strip()
            field_name = match.group(2).strip()
            if field_name and not field_name.startswith('//'):
                fields.append({'name': field_name, 'type': field_type})

        # Extract methods
        methods = []
        for match in self.METHOD_PATTERN.finditer(content):
            return_type = match.group(1).strip()
            method_name = match.group(2).strip()
            params = match.group(3).strip()
            if method_name and not method_name.startswith('//'):
                methods.append({
                    'name': method_name,
                    'return_type': return_type,
                    'params': params
                })

        # Get relative path
        try:
            rel_path = str(Path(file_path).relative_to(project_path))
        except ValueError:
            rel_path = file_path

        return JavaClass(
            name=class_name,
            package=package,
            full_name=f"{package}.{class_name}" if package else class_name,
            file_path=rel_path,
            class_type=class_type,
            annotations=annotations,
            imports=imports,
            fields=fields,
            methods=methods,
            extends=extends,
            implements=implements
        )

    def _check_duplicate_classes(self, classes: Dict[str, JavaClass]) -> List[AnalysisIssue]:
        """Check for duplicate class names in different packages"""
        issues = []

        # Group by simple class name
        by_name: Dict[str, List[JavaClass]] = defaultdict(list)
        for java_class in classes.values():
            by_name[java_class.name].append(java_class)

        # Find duplicates
        for name, class_list in by_name.items():
            if len(class_list) > 1:
                packages = [c.package for c in class_list]

                # Check if it's model vs model.entity conflict
                if any('model.entity' in p for p in packages) and any(
                    p.endswith('.model') or '.model.' in p and 'entity' not in p
                    for p in packages
                ):
                    # This is a real conflict - same class in model and model.entity
                    for c in class_list:
                        if '.model.' in c.package and '.entity' not in c.package:
                            issues.append(AnalysisIssue(
                                severity="error",
                                issue_type="duplicate_class",
                                file_path=c.file_path,
                                line=1,
                                message=f"Duplicate class '{name}' exists in both {packages}. "
                                        f"Remove {c.file_path} or merge with entity version.",
                                fix_suggestion=f"Delete {c.file_path} and use the entity version",
                                auto_fixable=True
                            ))

        return issues

    def _check_missing_lombok(self, classes: Dict[str, JavaClass]) -> List[AnalysisIssue]:
        """Check for missing Lombok annotations"""
        issues = []

        for java_class in classes.values():
            annotations_set = set(java_class.annotations)

            # Check entities
            if '@Entity' in annotations_set:
                missing = self.ENTITY_ANNOTATIONS - annotations_set
                if missing:
                    issues.append(AnalysisIssue(
                        severity="error",
                        issue_type="missing_lombok",
                        file_path=java_class.file_path,
                        line=1,
                        message=f"Entity {java_class.name} missing Lombok annotations: {missing}",
                        fix_suggestion=f"Add {', '.join(missing)} to {java_class.name}",
                        auto_fixable=True
                    ))

            # Check services
            if '@Service' in annotations_set:
                if '@Slf4j' not in annotations_set:
                    issues.append(AnalysisIssue(
                        severity="warning",
                        issue_type="missing_lombok",
                        file_path=java_class.file_path,
                        line=1,
                        message=f"Service {java_class.name} missing @Slf4j annotation",
                        fix_suggestion=f"Add @Slf4j to {java_class.name}",
                        auto_fixable=True
                    ))
                if '@RequiredArgsConstructor' not in annotations_set:
                    # Check if there are final fields
                    has_final_fields = any('final' in f.get('type', '') for f in java_class.fields)
                    if has_final_fields:
                        issues.append(AnalysisIssue(
                            severity="error",
                            issue_type="missing_lombok",
                            file_path=java_class.file_path,
                            line=1,
                            message=f"Service {java_class.name} has final fields but missing @RequiredArgsConstructor",
                            fix_suggestion=f"Add @RequiredArgsConstructor to {java_class.name}",
                            auto_fixable=True
                        ))

            # Check DTOs (classes ending with Dto, DTO, Request, Response)
            if any(java_class.name.endswith(s) for s in ['Dto', 'DTO', 'Request', 'Response']):
                if '@Data' not in annotations_set:
                    issues.append(AnalysisIssue(
                        severity="error",
                        issue_type="missing_lombok",
                        file_path=java_class.file_path,
                        line=1,
                        message=f"DTO {java_class.name} missing @Data annotation (getters/setters won't exist)",
                        fix_suggestion=f"Add @Data to {java_class.name}",
                        auto_fixable=True
                    ))

        return issues

    def _check_missing_methods(self, classes: Dict[str, JavaClass]) -> List[AnalysisIssue]:
        """Check for methods called but not defined"""
        issues = []

        # Build method registry
        method_registry: Dict[str, Set[str]] = {}  # class_name -> set of methods
        for java_class in classes.values():
            methods = {m['name'] for m in java_class.methods}
            # Add getter/setter for fields if @Data present
            if '@Data' in java_class.annotations:
                for field in java_class.fields:
                    field_name = field['name']
                    # Capitalize first letter for getter/setter
                    capitalized = field_name[0].upper() + field_name[1:] if field_name else ''
                    methods.add(f'get{capitalized}')
                    methods.add(f'set{capitalized}')
                    # Boolean fields also get isX
                    if field['type'].lower() == 'boolean':
                        methods.add(f'is{capitalized}')
            # Add builder if @Builder present
            if '@Builder' in java_class.annotations:
                methods.add('builder')

            method_registry[java_class.name] = methods

        # Check each class for method calls to other classes
        for java_class in classes.values():
            content = self._read_file(
                str(Path(java_class.file_path))
                if not java_class.file_path.startswith('/')
                else java_class.file_path
            )
            if not content:
                continue

            # Find variable declarations and their types
            var_types: Dict[str, str] = {}
            for match in re.finditer(r'(\w+)\s+(\w+)\s*[=;]', content):
                var_type = match.group(1)
                var_name = match.group(2)
                var_types[var_name] = var_type

            # Find method calls on variables
            for match in re.finditer(r'(\w+)\.(get\w+|set\w+|is\w+|builder)\s*\(', content):
                var_name = match.group(1)
                method_name = match.group(2)

                # Get type of variable
                var_type = var_types.get(var_name)
                if var_type and var_type in method_registry:
                    if method_name not in method_registry[var_type]:
                        # Method doesn't exist
                        issues.append(AnalysisIssue(
                            severity="error",
                            issue_type="missing_method",
                            file_path=java_class.file_path,
                            line=1,
                            message=f"Method {var_type}.{method_name}() called but doesn't exist. "
                                    f"Add @Data or @Builder to {var_type}?",
                            fix_suggestion=f"Add @Data to {var_type} class",
                            auto_fixable=False  # Need to modify different file
                        ))

        return issues

    def _check_wrong_imports(self, classes: Dict[str, JavaClass]) -> List[AnalysisIssue]:
        """Check for imports that reference non-existent classes or wrong packages"""
        issues = []

        # Build class registry
        class_packages: Dict[str, str] = {}  # simple_name -> full_package
        for java_class in classes.values():
            class_packages[java_class.name] = java_class.package

        for java_class in classes.values():
            for imp in java_class.imports:
                if imp.endswith('.*'):
                    continue

                # Extract class name from import
                parts = imp.split('.')
                if not parts:
                    continue

                imported_class = parts[-1]
                imported_package = '.'.join(parts[:-1])

                # Check if it's a project class with wrong package
                if imported_class in class_packages:
                    correct_package = class_packages[imported_class]
                    if correct_package != imported_package:
                        issues.append(AnalysisIssue(
                            severity="error",
                            issue_type="wrong_import",
                            file_path=java_class.file_path,
                            line=1,
                            message=f"Import {imp} should be {correct_package}.{imported_class}",
                            fix_suggestion=f"Change import to {correct_package}.{imported_class}",
                            auto_fixable=True
                        ))

        return issues

    def _apply_fixes(
        self,
        project_path: Path,
        classes: Dict[str, JavaClass],
        issues: List[AnalysisIssue]
    ) -> List[str]:
        """Apply automatic fixes for issues"""
        fixes_applied = []

        # Group issues by file
        issues_by_file: Dict[str, List[AnalysisIssue]] = defaultdict(list)
        for issue in issues:
            if issue.auto_fixable:
                issues_by_file[issue.file_path].append(issue)

        for file_path, file_issues in issues_by_file.items():
            full_path = project_path / file_path
            content = self._read_file(str(full_path))
            if not content:
                continue

            modified = False

            for issue in file_issues:
                if issue.issue_type == "missing_lombok":
                    # Add missing Lombok annotations
                    if "@Data" in issue.message and "@Data" not in content:
                        content = self._add_lombok_annotation(content, "@Data")
                        modified = True
                        fixes_applied.append(f"Added @Data to {file_path}")

                    if "@Slf4j" in issue.message and "@Slf4j" not in content:
                        content = self._add_lombok_annotation(content, "@Slf4j")
                        # Also add import
                        if "import lombok.extern.slf4j.Slf4j;" not in content:
                            content = self._add_import(content, "lombok.extern.slf4j.Slf4j")
                        modified = True
                        fixes_applied.append(f"Added @Slf4j to {file_path}")

                    if "@RequiredArgsConstructor" in issue.message and "@RequiredArgsConstructor" not in content:
                        content = self._add_lombok_annotation(content, "@RequiredArgsConstructor")
                        if "import lombok.RequiredArgsConstructor;" not in content:
                            content = self._add_import(content, "lombok.RequiredArgsConstructor")
                        modified = True
                        fixes_applied.append(f"Added @RequiredArgsConstructor to {file_path}")

                    if "@NoArgsConstructor" in issue.message and "@NoArgsConstructor" not in content:
                        content = self._add_lombok_annotation(content, "@NoArgsConstructor")
                        if "import lombok.NoArgsConstructor;" not in content:
                            content = self._add_import(content, "lombok.NoArgsConstructor")
                        modified = True
                        fixes_applied.append(f"Added @NoArgsConstructor to {file_path}")

                elif issue.issue_type == "wrong_import":
                    # Fix wrong import
                    if "should be" in issue.message:
                        old_import = issue.message.split("Import ")[1].split(" should be")[0]
                        new_import = issue.message.split("should be ")[1]
                        content = content.replace(f"import {old_import};", f"import {new_import};")
                        modified = True
                        fixes_applied.append(f"Fixed import in {file_path}: {old_import} -> {new_import}")

                elif issue.issue_type == "duplicate_class":
                    # For duplicate classes, we log but don't auto-delete
                    # This is a design decision that needs human review
                    logger.warning(f"[JavaAnalyzer] Duplicate class found: {file_path} - needs manual review")

            if modified:
                self._write_file(str(full_path), content)

        return fixes_applied

    def _add_lombok_annotation(self, content: str, annotation: str) -> str:
        """Add a Lombok annotation before the class declaration"""
        # Find class/interface/enum declaration
        match = self.CLASS_PATTERN.search(content)
        if not match:
            return content

        # Find the position to insert (before any existing annotations or the class keyword)
        insert_pos = match.start()

        # Look backwards for existing annotations
        pre_class = content[:insert_pos]
        last_newline = pre_class.rfind('\n')
        if last_newline != -1:
            insert_pos = last_newline + 1

        # Check if annotation already exists
        if annotation in content[:match.end()]:
            return content

        # Insert annotation
        return content[:insert_pos] + annotation + "\n" + content[insert_pos:]

    def _add_import(self, content: str, import_class: str) -> str:
        """Add an import statement after the package declaration"""
        import_stmt = f"import {import_class};"

        # Find package declaration
        package_match = self.PACKAGE_PATTERN.search(content)
        if package_match:
            insert_pos = package_match.end()
            # Add after any existing imports
            last_import = -1
            for match in self.IMPORT_PATTERN.finditer(content):
                last_import = match.end()
            if last_import > insert_pos:
                insert_pos = last_import

            return content[:insert_pos] + "\n" + import_stmt + content[insert_pos:]

        # No package, add at beginning
        return import_stmt + "\n" + content


# Singleton instance
java_analyzer = JavaAnalyzer()
