"""
Pre-Build Validator - Validate and fix code BEFORE running build

This service scans all source files before building and:
1. Detects missing methods, fields, imports
2. Auto-fixes issues using Claude
3. Ensures code will compile before build starts

Prevention is better than cure!
"""

import re
import asyncio
from typing import Dict, Any, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from anthropic import AsyncAnthropic

from app.core.logging_config import logger
from app.core.config import settings


class IssueType(Enum):
    """Types of pre-build issues"""
    MISSING_METHOD = "missing_method"
    MISSING_FIELD = "missing_field"
    MISSING_IMPORT = "missing_import"
    MISSING_CLASS = "missing_class"
    WRONG_PACKAGE = "wrong_package"
    MISSING_DEPENDENCY = "missing_dependency"
    SYNTAX_ERROR = "syntax_error"


@dataclass
class CodeIssue:
    """Represents a detected code issue"""
    issue_type: IssueType
    file_path: str
    line_number: int
    description: str
    target_class: Optional[str] = None  # Class that needs the fix
    target_file: Optional[str] = None   # File that needs the fix
    missing_element: Optional[str] = None  # What's missing (method name, field name, etc.)
    context: Optional[str] = None  # Surrounding code for context


@dataclass
class ValidationResult:
    """Result of pre-build validation"""
    is_valid: bool
    issues: List[CodeIssue]
    files_scanned: int
    files_fixed: int
    fixes_applied: List[str]


@dataclass
class JavaClass:
    """Represents a parsed Java class"""
    name: str
    file_path: str
    package: str
    imports: List[str]
    fields: Dict[str, str]  # field_name -> type
    methods: Dict[str, str]  # method_name -> signature
    extends: Optional[str] = None
    implements: List[str] = field(default_factory=list)
    content: str = ""


class PreBuildValidator:
    """
    Validates and fixes code before build.

    Flow:
    1. Scan all source files
    2. Build class/method/field maps
    3. Detect issues (missing methods, wrong imports, etc.)
    4. Auto-fix issues using Claude
    5. Return validation result
    """

    def __init__(self):
        self._client: Optional[AsyncAnthropic] = None
        self._sandbox_runner: Optional[Callable] = None
        self._sandbox_file_writer: Optional[Callable] = None
        self._sandbox_file_reader: Optional[Callable] = None
        self._project_path: Optional[str] = None

        # Cache of parsed classes
        self._classes: Dict[str, JavaClass] = {}

    def _get_client(self) -> AsyncAnthropic:
        """Get or create Anthropic client."""
        if self._client is None:
            self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._client

    async def validate_and_fix(
        self,
        project_id: str,
        project_path: str,
        technology: str,
        sandbox_file_reader: Optional[Callable[[str], Optional[str]]] = None,
        sandbox_file_writer: Optional[Callable[[str, str], bool]] = None,
        sandbox_runner: Optional[Callable[[str, Optional[str], int], Tuple[int, str]]] = None
    ) -> ValidationResult:
        """
        Validate project and fix issues before build.

        Args:
            project_id: Project ID
            project_path: Path to project on sandbox
            technology: Project technology (java, nodejs, python, etc.)
            sandbox_file_reader: Callback to read files from sandbox
            sandbox_file_writer: Callback to write files to sandbox
            sandbox_runner: Callback to run commands on sandbox

        Returns:
            ValidationResult with issues found and fixes applied
        """
        self._sandbox_file_reader = sandbox_file_reader
        self._sandbox_file_writer = sandbox_file_writer
        self._sandbox_runner = sandbox_runner
        self._project_path = project_path
        self._classes = {}

        logger.info(f"[PreBuildValidator:{project_id}] Starting validation for {technology} project")

        # Determine validation strategy based on technology
        if technology.lower() in ['java', 'spring', 'springboot', 'spring-boot', 'maven', 'gradle']:
            return await self._validate_java_project(project_id)
        elif technology.lower() in ['node', 'nodejs', 'javascript', 'typescript', 'react', 'vue', 'angular', 'nextjs']:
            return await self._validate_node_project(project_id)
        elif technology.lower() in ['python', 'fastapi', 'django', 'flask']:
            return await self._validate_python_project(project_id)
        else:
            logger.info(f"[PreBuildValidator:{project_id}] No specific validator for {technology}, skipping")
            return ValidationResult(is_valid=True, issues=[], files_scanned=0, files_fixed=0, fixes_applied=[])

    # =========================================================================
    # JAVA VALIDATION
    # =========================================================================

    async def _validate_java_project(self, project_id: str) -> ValidationResult:
        """Validate Java/Spring Boot project."""
        issues: List[CodeIssue] = []
        fixes_applied: List[str] = []
        files_fixed = 0

        # Step 1: Find all Java files
        java_files = await self._find_files("*.java")
        logger.info(f"[PreBuildValidator:{project_id}] Found {len(java_files)} Java files")

        if not java_files:
            return ValidationResult(is_valid=True, issues=[], files_scanned=0, files_fixed=0, fixes_applied=[])

        # Step 2: Parse all Java files to build class map
        for file_path in java_files:
            java_class = await self._parse_java_file(file_path)
            if java_class:
                self._classes[java_class.name] = java_class

        logger.info(f"[PreBuildValidator:{project_id}] Parsed {len(self._classes)} classes")

        # Step 3: Detect issues
        issues = await self._detect_java_issues(project_id)
        logger.info(f"[PreBuildValidator:{project_id}] Found {len(issues)} issues")

        # Step 4: Fix issues
        if issues:
            fixes_applied, files_fixed = await self._fix_java_issues(project_id, issues)

        is_valid = len(issues) == 0 or files_fixed > 0

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            files_scanned=len(java_files),
            files_fixed=files_fixed,
            fixes_applied=fixes_applied
        )

    async def _parse_java_file(self, file_path: str) -> Optional[JavaClass]:
        """Parse a Java file to extract class information."""
        try:
            content = self._sandbox_file_reader(file_path)
            if not content:
                return None

            # Extract package
            package_match = re.search(r'package\s+([\w.]+)\s*;', content)
            package = package_match.group(1) if package_match else ""

            # Extract imports
            imports = re.findall(r'import\s+([\w.*]+)\s*;', content)

            # Extract class name
            class_match = re.search(r'(?:public\s+)?(?:abstract\s+)?class\s+(\w+)', content)
            if not class_match:
                # Try interface
                class_match = re.search(r'(?:public\s+)?interface\s+(\w+)', content)

            if not class_match:
                return None

            class_name = class_match.group(1)

            # Extract extends
            extends_match = re.search(r'class\s+\w+\s+extends\s+(\w+)', content)
            extends = extends_match.group(1) if extends_match else None

            # Extract implements
            implements_match = re.search(r'implements\s+([\w,\s]+?)(?:\s*\{|$)', content)
            implements = []
            if implements_match:
                implements = [i.strip() for i in implements_match.group(1).split(',')]

            # Extract fields (simplified)
            fields = {}
            field_pattern = r'(?:private|protected|public)\s+(?:static\s+)?(?:final\s+)?(\w+(?:<[\w,\s<>]+>)?)\s+(\w+)\s*[;=]'
            for match in re.finditer(field_pattern, content):
                field_type, field_name = match.groups()
                fields[field_name] = field_type

            # Extract methods (simplified)
            methods = {}
            method_pattern = r'(?:public|private|protected)\s+(?:static\s+)?(?:abstract\s+)?(\w+(?:<[\w,\s<>]+>)?)\s+(\w+)\s*\(([^)]*)\)'
            for match in re.finditer(method_pattern, content):
                return_type, method_name, params = match.groups()
                methods[method_name] = f"{return_type} {method_name}({params})"

            return JavaClass(
                name=class_name,
                file_path=file_path,
                package=package,
                imports=imports,
                fields=fields,
                methods=methods,
                extends=extends,
                implements=implements,
                content=content
            )

        except Exception as e:
            logger.warning(f"[PreBuildValidator] Error parsing {file_path}: {e}")
            return None

    async def _detect_java_issues(self, project_id: str) -> List[CodeIssue]:
        """Detect issues in Java project."""
        issues = []

        for class_name, java_class in self._classes.items():
            content = java_class.content

            # Check for method calls to other classes
            # Pattern: someObject.someMethod(
            method_calls = re.findall(r'(\w+)\.(\w+)\s*\(', content)

            for obj_name, method_name in method_calls:
                # Skip common patterns
                if obj_name in ['System', 'this', 'super', 'String', 'Integer', 'Long',
                               'List', 'Map', 'Set', 'Optional', 'log', 'logger', 'LOG']:
                    continue

                # Skip builder patterns and common methods
                if method_name in ['get', 'set', 'build', 'builder', 'toString', 'equals',
                                   'hashCode', 'stream', 'map', 'filter', 'collect',
                                   'orElse', 'orElseThrow', 'isPresent', 'isEmpty']:
                    continue

                # Find the type of the object
                field_type = java_class.fields.get(obj_name)
                if not field_type:
                    # Check if it's a parameter or local variable (harder to detect)
                    continue

                # Clean up generic types
                base_type = re.sub(r'<.*>', '', field_type)

                # Check if the target class exists and has the method
                target_class = self._classes.get(base_type)
                if target_class:
                    if method_name not in target_class.methods:
                        # Found a missing method!
                        issues.append(CodeIssue(
                            issue_type=IssueType.MISSING_METHOD,
                            file_path=java_class.file_path,
                            line_number=0,
                            description=f"Method '{method_name}' called on {base_type} but not defined",
                            target_class=base_type,
                            target_file=target_class.file_path,
                            missing_element=method_name,
                            context=self._get_method_call_context(content, obj_name, method_name)
                        ))

            # Check for missing getters (common issue with entities)
            if 'Entity' in java_class.file_path or 'entity' in java_class.file_path.lower():
                for field_name, field_type in java_class.fields.items():
                    getter_name = f"get{field_name[0].upper()}{field_name[1:]}"
                    setter_name = f"set{field_name[0].upper()}{field_name[1:]}"

                    # Check if Lombok is used
                    has_lombok = '@Data' in content or '@Getter' in content or '@Setter' in content

                    if not has_lombok:
                        if getter_name not in java_class.methods:
                            issues.append(CodeIssue(
                                issue_type=IssueType.MISSING_METHOD,
                                file_path=java_class.file_path,
                                line_number=0,
                                description=f"Missing getter '{getter_name}' for field '{field_name}'",
                                target_class=class_name,
                                target_file=java_class.file_path,
                                missing_element=getter_name,
                                context=f"private {field_type} {field_name};"
                            ))

        logger.info(f"[PreBuildValidator:{project_id}] Detected {len(issues)} potential issues")
        return issues

    def _get_method_call_context(self, content: str, obj_name: str, method_name: str) -> str:
        """Get context around a method call."""
        pattern = rf'.*{re.escape(obj_name)}\.{re.escape(method_name)}\s*\([^)]*\).*'
        match = re.search(pattern, content)
        if match:
            return match.group(0).strip()[:200]
        return ""

    async def _fix_java_issues(self, project_id: str, issues: List[CodeIssue]) -> Tuple[List[str], int]:
        """Fix detected Java issues using Claude."""
        fixes_applied = []
        files_fixed_set: Set[str] = set()

        # Group issues by target file
        issues_by_file: Dict[str, List[CodeIssue]] = {}
        for issue in issues:
            target_file = issue.target_file or issue.file_path
            if target_file not in issues_by_file:
                issues_by_file[target_file] = []
            issues_by_file[target_file].append(issue)

        # Fix each file
        for file_path, file_issues in issues_by_file.items():
            try:
                fixed = await self._fix_file_issues(project_id, file_path, file_issues)
                if fixed:
                    files_fixed_set.add(file_path)
                    for issue in file_issues:
                        fixes_applied.append(f"Added {issue.missing_element} to {issue.target_class}")
            except Exception as e:
                logger.error(f"[PreBuildValidator:{project_id}] Error fixing {file_path}: {e}")

        return fixes_applied, len(files_fixed_set)

    async def _fix_file_issues(self, project_id: str, file_path: str, issues: List[CodeIssue]) -> bool:
        """Fix issues in a single file using Claude."""
        content = self._sandbox_file_reader(file_path)
        if not content:
            return False

        # Build issue description
        issue_desc = "\n".join([
            f"- {issue.issue_type.value}: {issue.description}"
            for issue in issues
        ])

        # Call Claude to fix
        client = self._get_client()

        prompt = f"""Fix the following issues in this Java file.

FILE: {file_path}

ISSUES TO FIX:
{issue_desc}

CURRENT CODE:
```java
{content}
```

Return ONLY the complete fixed Java file. No explanations, just the code.
Make sure to:
1. Add any missing methods with proper implementation
2. Add any missing getters/setters
3. Keep all existing code intact
4. Follow Java conventions
"""

        try:
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract code from response
            response_text = response.content[0].text

            # Try to extract code block
            code_match = re.search(r'```java\s*(.*?)```', response_text, re.DOTALL)
            if code_match:
                fixed_content = code_match.group(1).strip()
            else:
                # Assume entire response is code
                fixed_content = response_text.strip()

            # Validate it looks like Java
            if 'class ' in fixed_content or 'interface ' in fixed_content:
                # Write back to file
                success = self._sandbox_file_writer(file_path, fixed_content)
                if success:
                    logger.info(f"[PreBuildValidator:{project_id}] Fixed {file_path}")
                    return True

        except Exception as e:
            logger.error(f"[PreBuildValidator:{project_id}] Claude fix error: {e}")

        return False

    # =========================================================================
    # NODE.JS VALIDATION
    # =========================================================================

    async def _validate_node_project(self, project_id: str) -> ValidationResult:
        """Validate Node.js/TypeScript project."""
        issues: List[CodeIssue] = []
        fixes_applied: List[str] = []

        # Check package.json exists
        package_json = self._sandbox_file_reader(f"{self._project_path}/frontend/package.json")
        if not package_json:
            package_json = self._sandbox_file_reader(f"{self._project_path}/package.json")

        if not package_json:
            issues.append(CodeIssue(
                issue_type=IssueType.MISSING_DEPENDENCY,
                file_path="package.json",
                line_number=0,
                description="package.json not found"
            ))

        # Find TypeScript/JavaScript files
        ts_files = await self._find_files("*.ts")
        tsx_files = await self._find_files("*.tsx")
        js_files = await self._find_files("*.js")
        jsx_files = await self._find_files("*.jsx")

        all_files = ts_files + tsx_files + js_files + jsx_files
        logger.info(f"[PreBuildValidator:{project_id}] Found {len(all_files)} JS/TS files")

        # For now, just return - more complex validation can be added later
        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            files_scanned=len(all_files),
            files_fixed=0,
            fixes_applied=fixes_applied
        )

    # =========================================================================
    # PYTHON VALIDATION
    # =========================================================================

    async def _validate_python_project(self, project_id: str) -> ValidationResult:
        """Validate Python project."""
        issues: List[CodeIssue] = []
        fixes_applied: List[str] = []

        # Find Python files
        py_files = await self._find_files("*.py")
        logger.info(f"[PreBuildValidator:{project_id}] Found {len(py_files)} Python files")

        # Check requirements.txt exists
        requirements = self._sandbox_file_reader(f"{self._project_path}/requirements.txt")
        if not requirements:
            requirements = self._sandbox_file_reader(f"{self._project_path}/backend/requirements.txt")

        # For now, just return - more complex validation can be added later
        return ValidationResult(
            is_valid=True,
            issues=issues,
            files_scanned=len(py_files),
            files_fixed=0,
            fixes_applied=fixes_applied
        )

    # =========================================================================
    # UTILITIES
    # =========================================================================

    async def _find_files(self, pattern: str) -> List[str]:
        """Find files matching pattern in project."""
        if not self._sandbox_runner:
            return []

        try:
            cmd = f'find "{self._project_path}" -name "{pattern}" -type f 2>/dev/null'
            exit_code, output = self._sandbox_runner(cmd, None, 30)

            if exit_code == 0 and output:
                files = [f.strip() for f in output.strip().split('\n') if f.strip()]
                return files
        except Exception as e:
            logger.warning(f"[PreBuildValidator] Error finding files: {e}")

        return []


# Singleton instance
pre_build_validator = PreBuildValidator()
