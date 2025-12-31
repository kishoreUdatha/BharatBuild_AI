"""
Error Classifier - Rule-based error classification (NO AI)

This module classifies errors BEFORE calling Claude.
Claude is told WHAT type of error it is, not asked to figure it out.

Bolt.new Architecture Pattern:
- Rules decide WHEN to call Claude
- Claude decides HOW to fix code
- Runtime decides WHAT gets applied
"""

import re
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from app.core.logging_config import logger


class ErrorType(Enum):
    """Error types with their fix eligibility"""
    # Fixable by Claude
    DEPENDENCY_CONFLICT = "dependency_conflict"
    MISSING_FILE = "missing_file"
    IMPORT_ERROR = "import_error"
    SYNTAX_ERROR = "syntax_error"
    TYPE_ERROR = "type_error"
    UNDEFINED_VARIABLE = "undefined_variable"
    MISSING_EXPORT = "missing_export"
    REACT_ERROR = "react_error"
    CSS_ERROR = "css_error"
    CONFIG_ERROR = "config_error"

    # NOT fixable by Claude - require infrastructure action
    INFRA_ERROR = "infra_error"
    NETWORK_ERROR = "network_error"
    PORT_CONFLICT = "port_conflict"
    PERMISSION_ERROR = "permission_error"
    MEMORY_ERROR = "memory_error"
    TIMEOUT_ERROR = "timeout_error"
    REGISTRY_ERROR = "registry_error"

    # Unknown - may need investigation
    UNKNOWN = "unknown"


@dataclass
class ClassifiedError:
    """Result of error classification"""
    error_type: ErrorType
    is_claude_fixable: bool
    file_path: Optional[str]
    line_number: Optional[int]
    original_message: str
    suggested_action: str
    confidence: float  # 0.0 to 1.0
    extracted_context: Dict[str, Any]


class ErrorClassifier:
    """
    Rule-based error classifier.

    Classifies errors using regex patterns BEFORE calling Claude.
    This ensures Claude only sees errors it can actually fix.
    """

    # Patterns for errors Claude CAN fix
    FIXABLE_PATTERNS: List[Tuple[str, ErrorType, str, float]] = [
        # Dependency errors
        (r'ERESOLVE|EOVERRIDE|peer\s+dep|conflicting\s+peer',
         ErrorType.DEPENDENCY_CONFLICT,
         "Resolve dependency version conflict", 0.95),
        (r'Cannot\s+find\s+module|Module\s+not\s+found|ENOENT.*node_modules',
         ErrorType.DEPENDENCY_CONFLICT,
         "Install missing dependency", 0.9),

        # Missing file errors
        (r'ENOENT.*no\s+such\s+file|Failed\s+to\s+resolve\s+config|Cannot\s+find\s+module\s+[\'"][^/]',
         ErrorType.MISSING_FILE,
         "Create missing file", 0.95),
        (r'tsconfig\.node\.json|postcss\.config|tailwind\.config',
         ErrorType.MISSING_FILE,
         "Create missing config file", 0.95),

        # Import/Export errors
        (r'No\s+matching\s+export.*for\s+import',
         ErrorType.MISSING_EXPORT,
         "Fix export/import mismatch", 0.95),
        (r'export\s+.*\s+was\s+not\s+found|does\s+not\s+provide\s+an\s+export\s+named',
         ErrorType.IMPORT_ERROR,
         "Fix import statement", 0.9),
        (r'Cannot\s+find\s+name|is\s+not\s+defined|ReferenceError.*not\s+defined',
         ErrorType.UNDEFINED_VARIABLE,
         "Fix undefined variable/import", 0.85),

        # Syntax errors
        (r'Unexpected\s+["\']?\}|Unexpected\s+["\']?\)|Unexpected\s+token',
         ErrorType.SYNTAX_ERROR,
         "Fix syntax error - bracket mismatch", 0.9),
        (r'Expected\s+["\']?[\}\)\]]\s+but\s+found',
         ErrorType.SYNTAX_ERROR,
         "Fix syntax error - expected token", 0.9),
        (r'Unterminated\s+string|Parse\s+error|SyntaxError:',
         ErrorType.SYNTAX_ERROR,
         "Fix syntax error", 0.85),

        # Type errors
        (r'Type\s+[\'"].*[\'"]\s+is\s+not\s+assignable|TS\d{4}',
         ErrorType.TYPE_ERROR,
         "Fix TypeScript type error", 0.85),
        (r'Property\s+[\'"].*[\'"]\s+does\s+not\s+exist',
         ErrorType.TYPE_ERROR,
         "Fix missing property", 0.85),

        # React-specific errors
        (r'Invalid\s+hook\s+call|Hooks\s+can\s+only\s+be\s+called',
         ErrorType.REACT_ERROR,
         "Fix React hooks usage", 0.9),
        (r'React.*hydration|Expected\s+server\s+HTML',
         ErrorType.REACT_ERROR,
         "Fix hydration mismatch", 0.8),
        (r'Cannot\s+read\s+propert.*of\s+undefined|undefined\s+is\s+not\s+an\s+object',
         ErrorType.REACT_ERROR,
         "Add null check", 0.85),

        # CSS/Tailwind errors
        (r'Unknown\s+at\s+rule\s+@|PostCSS|tailwind.*unknown',
         ErrorType.CSS_ERROR,
         "Fix CSS/Tailwind configuration", 0.85),

        # Config errors
        (r'vite\.config|tsconfig|babel\.config|webpack\.config',
         ErrorType.CONFIG_ERROR,
         "Fix configuration file", 0.85),
    ]

    # Patterns for errors Claude CANNOT fix (infrastructure issues)
    NON_FIXABLE_PATTERNS: List[Tuple[str, ErrorType, str, float]] = [
        # Command not found - missing tools in container
        (r'sh:\s*\w+:\s*not\s+found|command\s+not\s+found|bash:.*not\s+found',
         ErrorType.INFRA_ERROR,
         "Install missing tool in container", 0.95),
        (r'pnpm:\s*not\s+found|yarn:\s*not\s+found|npx:\s*not\s+found',
         ErrorType.INFRA_ERROR,
         "Install missing package manager", 0.95),

        # Network errors
        (r'ETIMEDOUT|ECONNRESET|ECONNREFUSED|getaddrinfo|DNS',
         ErrorType.NETWORK_ERROR,
         "Retry - network issue", 0.95),
        (r'registry\.npmjs\.org|npm\s+ERR!\s+network',
         ErrorType.REGISTRY_ERROR,
         "Retry - npm registry issue", 0.95),

        # Port/Infra errors
        (r'port\s+already\s+allocated|address\s+already\s+in\s+use|EADDRINUSE',
         ErrorType.PORT_CONFLICT,
         "Kill existing process or change port", 0.95),
        (r'container.*failed|docker.*error|OCI\s+runtime',
         ErrorType.INFRA_ERROR,
         "Recreate container", 0.9),

        # Permission errors
        (r'EACCES|permission\s+denied|EPERM',
         ErrorType.PERMISSION_ERROR,
         "Fix file permissions", 0.9),

        # Memory errors
        (r'ENOMEM|out\s+of\s+memory|heap\s+out\s+of\s+memory|JavaScript\s+heap',
         ErrorType.MEMORY_ERROR,
         "Increase memory or optimize", 0.95),

        # Timeout errors
        (r'timeout.*exceeded|operation\s+timed\s+out|ESOCKETTIMEDOUT',
         ErrorType.TIMEOUT_ERROR,
         "Retry with longer timeout", 0.9),
    ]

    # Patterns to extract file path and line number
    FILE_PATTERNS = [
        r'(?:at\s+|in\s+|file:\s*)?([a-zA-Z0-9_\-./\\]+\.[jt]sx?):(\d+)',  # file.tsx:123
        r'([a-zA-Z0-9_\-./\\]+\.[jt]sx?)\s*\((\d+),\s*\d+\)',  # file.tsx (123, 45)
        r'Error\s+in\s+([a-zA-Z0-9_\-./\\]+\.[jt]sx?):(\d+)',  # Error in file.tsx:123
        r'→\s*([a-zA-Z0-9_\-./\\]+\.[jt]sx?):(\d+)',  # → file.tsx:123
    ]

    @classmethod
    def classify(cls, error_message: str, stderr: str = "", exit_code: int = 1) -> ClassifiedError:
        """
        Classify an error message into a type.

        This is called BEFORE Claude to determine:
        1. What type of error this is
        2. Whether Claude should be called
        3. What context to provide to Claude

        Args:
            error_message: The primary error message
            stderr: Full stderr output (for more context)
            exit_code: Process exit code

        Returns:
            ClassifiedError with type and fix eligibility
        """
        combined = f"{error_message}\n{stderr}"

        # Extract file path and line number
        file_path, line_number = cls._extract_file_location(combined)

        # First check non-fixable patterns (infrastructure issues)
        for pattern, error_type, action, confidence in cls.NON_FIXABLE_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                logger.info(f"[ErrorClassifier] Classified as {error_type.value} (NOT fixable by Claude)")
                return ClassifiedError(
                    error_type=error_type,
                    is_claude_fixable=False,
                    file_path=file_path,
                    line_number=line_number,
                    original_message=error_message,
                    suggested_action=action,
                    confidence=confidence,
                    extracted_context=cls._extract_context(combined, error_type)
                )

        # Then check fixable patterns
        for pattern, error_type, action, confidence in cls.FIXABLE_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                logger.info(f"[ErrorClassifier] Classified as {error_type.value} (Claude fixable)")
                return ClassifiedError(
                    error_type=error_type,
                    is_claude_fixable=True,
                    file_path=file_path,
                    line_number=line_number,
                    original_message=error_message,
                    suggested_action=action,
                    confidence=confidence,
                    extracted_context=cls._extract_context(combined, error_type)
                )

        # Unknown error - log and allow Claude to attempt
        logger.warning(f"[ErrorClassifier] Unknown error type, allowing Claude attempt")
        return ClassifiedError(
            error_type=ErrorType.UNKNOWN,
            is_claude_fixable=True,  # Allow attempt for unknown
            file_path=file_path,
            line_number=line_number,
            original_message=error_message,
            suggested_action="Investigate and fix",
            confidence=0.5,
            extracted_context={}
        )

    @classmethod
    def _extract_file_location(cls, text: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract file path and line number from error text"""
        for pattern in cls.FILE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                file_path = match.group(1)
                line_number = int(match.group(2)) if match.lastindex >= 2 else None
                # Normalize path
                file_path = file_path.replace('\\', '/')
                return file_path, line_number
        return None, None

    @classmethod
    def _extract_context(cls, text: str, error_type: ErrorType) -> Dict[str, Any]:
        """Extract error-specific context for Claude"""
        context = {}

        if error_type == ErrorType.DEPENDENCY_CONFLICT:
            # Extract package names
            pkg_match = re.findall(r'([a-z@][a-z0-9\-/@.]+)@[\d.]+', text, re.IGNORECASE)
            if pkg_match:
                context['packages'] = list(set(pkg_match[:10]))

        elif error_type == ErrorType.MISSING_EXPORT:
            # Extract export name
            export_match = re.search(r'for\s+import\s+[\'"](\w+)[\'"]', text)
            if export_match:
                context['missing_export'] = export_match.group(1)

        elif error_type in (ErrorType.IMPORT_ERROR, ErrorType.UNDEFINED_VARIABLE):
            # Extract variable/module name
            name_match = re.search(r'Cannot\s+find\s+(?:module|name)\s+[\'"]([^"\']+)[\'"]', text)
            if name_match:
                context['missing_name'] = name_match.group(1)

        elif error_type == ErrorType.TYPE_ERROR:
            # Extract TS error code
            ts_match = re.search(r'TS(\d{4})', text)
            if ts_match:
                context['ts_error_code'] = f"TS{ts_match.group(1)}"

        return context

    @classmethod
    def should_call_claude(cls, classified: ClassifiedError) -> Tuple[bool, str]:
        """
        Decision gate: Should Claude be called for this error?

        Returns:
            Tuple of (should_call, reason)
        """
        if not classified.is_claude_fixable:
            return False, f"Infrastructure error ({classified.error_type.value}): {classified.suggested_action}"

        if classified.confidence < 0.3:
            return False, f"Low confidence classification ({classified.confidence})"

        return True, f"Error fixable by Claude ({classified.error_type.value})"

    @classmethod
    def get_claude_prompt_template(cls, error_type: ErrorType) -> str:
        """
        Get the appropriate prompt template for each error type.

        Claude is told WHAT type of error it is fixing.
        It doesn't need to figure that out.
        """
        templates = {
            ErrorType.DEPENDENCY_CONFLICT: """Error type: DEPENDENCY_CONFLICT
Fix the dependency version conflict in package.json.
Return ONLY a unified diff for package.json.""",

            ErrorType.MISSING_FILE: """Error type: MISSING_FILE
Create the missing configuration file.
Return the file using <newfile path="...">content</newfile>""",

            ErrorType.MISSING_EXPORT: """Error type: MISSING_EXPORT
Add the missing default export to the component.
Return ONLY a unified diff.""",

            ErrorType.IMPORT_ERROR: """Error type: IMPORT_ERROR
Fix the import statement.
Return ONLY a unified diff.""",

            ErrorType.SYNTAX_ERROR: """Error type: SYNTAX_ERROR
Fix the syntax error (mismatched brackets/tokens).
Return the COMPLETE fixed file using <file path="...">content</file>""",

            ErrorType.TYPE_ERROR: """Error type: TYPE_ERROR
Fix the TypeScript type error.
Return ONLY a unified diff.""",

            ErrorType.UNDEFINED_VARIABLE: """Error type: UNDEFINED_VARIABLE
Fix the undefined variable by adding import or declaration.
Return ONLY a unified diff.""",

            ErrorType.REACT_ERROR: """Error type: REACT_ERROR
Fix the React error.
Return ONLY a unified diff.""",

            ErrorType.CSS_ERROR: """Error type: CSS_ERROR
Fix the CSS/Tailwind configuration.
Return ONLY a unified diff or create missing file.""",

            ErrorType.CONFIG_ERROR: """Error type: CONFIG_ERROR
Fix the configuration file.
Return ONLY a unified diff.""",
        }

        return templates.get(error_type, """Error type: UNKNOWN
Analyze and fix the error.
Return ONLY a unified diff.""")


# Singleton instance
error_classifier = ErrorClassifier()
