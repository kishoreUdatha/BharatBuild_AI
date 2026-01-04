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

        # Java compilation errors
        (r'no\s+suitable\s+constructor\s+found|constructor.*is\s+not\s+applicable',
         ErrorType.TYPE_ERROR,
         "Fix Java constructor mismatch", 0.95),
        (r'cannot\s+find\s+symbol|symbol:\s+(?:class|variable|method)',
         ErrorType.UNDEFINED_VARIABLE,
         "Fix missing Java symbol", 0.9),
        (r'incompatible\s+types|required:.*found:',
         ErrorType.TYPE_ERROR,
         "Fix Java type mismatch", 0.9),
        (r'method\s+.*\s+cannot\s+be\s+applied|actual\s+and\s+formal\s+argument\s+lists\s+differ',
         ErrorType.TYPE_ERROR,
         "Fix Java method argument mismatch", 0.9),
        (r'package\s+.*\s+does\s+not\s+exist|cannot\s+access\s+class',
         ErrorType.IMPORT_ERROR,
         "Fix Java import", 0.85),

        # Spring/Bean errors
        (r'No\s+qualifying\s+bean|expected\s+at\s+least\s+1\s+bean',
         ErrorType.CONFIG_ERROR,
         "Fix Spring bean configuration", 0.85),
        (r'UnsatisfiedDependencyException|BeanCreationException',
         ErrorType.CONFIG_ERROR,
         "Fix Spring dependency injection", 0.85),
        (r'@Autowired.*failed|Could\s+not\s+autowire',
         ErrorType.CONFIG_ERROR,
         "Fix Spring autowiring", 0.85),

        # =================================================================
        # PYTHON ERRORS (AI/ML, Django, Flask, FastAPI)
        # =================================================================
        (r'IndentationError:|TabError:',
         ErrorType.SYNTAX_ERROR,
         "Fix Python indentation", 0.95),
        (r'ModuleNotFoundError:|ImportError:',
         ErrorType.IMPORT_ERROR,
         "Fix Python import", 0.9),
        (r'NameError:\s+name\s+[\'"].*[\'"]\s+is\s+not\s+defined',
         ErrorType.UNDEFINED_VARIABLE,
         "Fix undefined Python variable", 0.9),
        (r'AttributeError:\s+.*has\s+no\s+attribute',
         ErrorType.TYPE_ERROR,
         "Fix missing Python attribute", 0.85),
        (r'TypeError:\s+.*argument|TypeError:\s+.*expected',
         ErrorType.TYPE_ERROR,
         "Fix Python type error", 0.85),
        (r'KeyError:|IndexError:',
         ErrorType.TYPE_ERROR,
         "Fix Python key/index error", 0.8),
        (r'ValueError:\s+|ZeroDivisionError:',
         ErrorType.TYPE_ERROR,
         "Fix Python value error", 0.8),
        # TensorFlow/PyTorch/ML errors
        (r'tensorflow.*error|tf\..*Error|InvalidArgumentError',
         ErrorType.CONFIG_ERROR,
         "Fix TensorFlow configuration", 0.85),
        (r'RuntimeError:.*CUDA|torch.*error|cuDNN',
         ErrorType.CONFIG_ERROR,
         "Fix PyTorch/CUDA configuration", 0.8),
        (r'shape\s+mismatch|dimension.*mismatch|incompatible\s+shapes',
         ErrorType.TYPE_ERROR,
         "Fix tensor shape mismatch", 0.85),
        # Django/Flask errors
        (r'django\..*Error|ImproperlyConfigured',
         ErrorType.CONFIG_ERROR,
         "Fix Django configuration", 0.85),
        (r'flask\..*error|werkzeug.*error',
         ErrorType.CONFIG_ERROR,
         "Fix Flask configuration", 0.85),

        # =================================================================
        # GO ERRORS
        # =================================================================
        (r'undefined:\s+\w+|undeclared\s+name',
         ErrorType.UNDEFINED_VARIABLE,
         "Fix undefined Go variable", 0.9),
        (r'cannot\s+use.*as.*in|incompatible.*type',
         ErrorType.TYPE_ERROR,
         "Fix Go type mismatch", 0.9),
        (r'imported\s+and\s+not\s+used|declared\s+and\s+not\s+used',
         ErrorType.IMPORT_ERROR,
         "Fix unused Go import/variable", 0.9),
        (r'no\s+required\s+module\s+provides|missing\s+go\.sum\s+entry',
         ErrorType.DEPENDENCY_CONFLICT,
         "Fix Go module dependency", 0.9),
        (r'syntax\s+error:.*unexpected',
         ErrorType.SYNTAX_ERROR,
         "Fix Go syntax error", 0.9),

        # =================================================================
        # RUST ERRORS
        # =================================================================
        (r'error\[E\d+\]:|cannot\s+find.*in\s+this\s+scope',
         ErrorType.UNDEFINED_VARIABLE,
         "Fix Rust undefined symbol", 0.9),
        (r'mismatched\s+types|expected.*found',
         ErrorType.TYPE_ERROR,
         "Fix Rust type mismatch", 0.9),
        (r'borrow\s+checker|cannot\s+borrow|borrowed\s+value',
         ErrorType.TYPE_ERROR,
         "Fix Rust borrow checker error", 0.85),
        (r'use\s+of\s+moved\s+value|value\s+moved\s+here',
         ErrorType.TYPE_ERROR,
         "Fix Rust ownership error", 0.85),
        (r'unresolved\s+import|could\s+not\s+find.*in.*crate',
         ErrorType.IMPORT_ERROR,
         "Fix Rust import", 0.9),
        (r'failed\s+to\s+resolve.*dependencies|Cargo.*error',
         ErrorType.DEPENDENCY_CONFLICT,
         "Fix Cargo dependency", 0.9),

        # =================================================================
        # C/C++ ERRORS (GCC, Clang)
        # =================================================================
        (r'error:.*undeclared|use\s+of\s+undeclared\s+identifier',
         ErrorType.UNDEFINED_VARIABLE,
         "Fix C/C++ undeclared variable", 0.9),
        (r'error:.*undefined\s+reference|undefined\s+symbol',
         ErrorType.IMPORT_ERROR,
         "Fix C/C++ linker error", 0.85),
        (r'error:.*incompatible.*type|cannot\s+convert',
         ErrorType.TYPE_ERROR,
         "Fix C/C++ type error", 0.9),
        (r'error:.*expected.*before|expected.*declaration',
         ErrorType.SYNTAX_ERROR,
         "Fix C/C++ syntax error", 0.9),
        (r'fatal\s+error:.*No\s+such\s+file|cannot\s+find.*include',
         ErrorType.MISSING_FILE,
         "Fix C/C++ include path", 0.9),
        (r'segmentation\s+fault|SIGSEGV',
         ErrorType.TYPE_ERROR,
         "Fix C/C++ memory error", 0.7),

        # =================================================================
        # .NET / C# ERRORS
        # =================================================================
        (r'CS\d{4}:|error\s+CS\d+',
         ErrorType.TYPE_ERROR,
         "Fix C# compiler error", 0.9),
        (r'The\s+type\s+or\s+namespace.*could\s+not\s+be\s+found',
         ErrorType.IMPORT_ERROR,
         "Fix C# namespace/using", 0.9),
        (r'does\s+not\s+contain\s+a\s+definition\s+for',
         ErrorType.UNDEFINED_VARIABLE,
         "Fix C# undefined member", 0.9),
        (r'NullReferenceException|Object\s+reference\s+not\s+set',
         ErrorType.TYPE_ERROR,
         "Fix C# null reference", 0.85),
        (r'Cannot\s+implicitly\s+convert\s+type',
         ErrorType.TYPE_ERROR,
         "Fix C# type conversion", 0.9),

        # =================================================================
        # PHP ERRORS
        # =================================================================
        (r'PHP\s+Parse\s+error|syntax\s+error,\s+unexpected',
         ErrorType.SYNTAX_ERROR,
         "Fix PHP syntax error", 0.9),
        (r'Undefined\s+variable|Undefined\s+index',
         ErrorType.UNDEFINED_VARIABLE,
         "Fix PHP undefined variable", 0.9),
        (r'Class\s+[\'"].*[\'"]\s+not\s+found|Interface.*not\s+found',
         ErrorType.IMPORT_ERROR,
         "Fix PHP class not found", 0.9),
        (r'Call\s+to\s+undefined\s+function|Call\s+to\s+undefined\s+method',
         ErrorType.UNDEFINED_VARIABLE,
         "Fix PHP undefined function", 0.9),
        (r'Type\s+error:.*must\s+be|TypeError:.*Argument',
         ErrorType.TYPE_ERROR,
         "Fix PHP type error", 0.85),

        # =================================================================
        # RUBY ERRORS
        # =================================================================
        (r'NameError:.*undefined\s+local\s+variable',
         ErrorType.UNDEFINED_VARIABLE,
         "Fix Ruby undefined variable", 0.9),
        (r'NoMethodError:.*undefined\s+method',
         ErrorType.UNDEFINED_VARIABLE,
         "Fix Ruby undefined method", 0.9),
        (r'LoadError:.*cannot\s+load\s+such\s+file',
         ErrorType.IMPORT_ERROR,
         "Fix Ruby require/load error", 0.9),
        (r'SyntaxError:.*unexpected',
         ErrorType.SYNTAX_ERROR,
         "Fix Ruby syntax error", 0.9),
        (r'TypeError:.*no\s+implicit\s+conversion',
         ErrorType.TYPE_ERROR,
         "Fix Ruby type error", 0.85),
        (r'Bundler::GemNotFound|Could\s+not\s+find\s+gem',
         ErrorType.DEPENDENCY_CONFLICT,
         "Fix Ruby gem dependency", 0.9),

        # =================================================================
        # FLUTTER / DART ERRORS
        # =================================================================
        (r'Error:.*isn\'t\s+defined|Undefined\s+name',
         ErrorType.UNDEFINED_VARIABLE,
         "Fix Dart undefined name", 0.9),
        (r'Error:.*can\'t\s+be\s+assigned\s+to|type.*can\'t\s+be\s+assigned',
         ErrorType.TYPE_ERROR,
         "Fix Dart type error", 0.9),
        (r'Error:.*Expected.*found|Unexpected.*token',
         ErrorType.SYNTAX_ERROR,
         "Fix Dart syntax error", 0.9),
        (r'Error:.*getter.*isn\'t\s+defined|setter.*isn\'t\s+defined',
         ErrorType.UNDEFINED_VARIABLE,
         "Fix Dart getter/setter", 0.9),
        (r'flutter.*error|pub\s+get\s+failed|Could\s+not\s+find\s+package',
         ErrorType.DEPENDENCY_CONFLICT,
         "Fix Flutter/pub dependency", 0.9),
        (r'RenderFlex.*overflowed|A\s+RenderFlex\s+overflowed',
         ErrorType.REACT_ERROR,
         "Fix Flutter layout overflow", 0.85),

        # =================================================================
        # SOLIDITY / BLOCKCHAIN ERRORS
        # =================================================================
        (r'DeclarationError:|TypeError:.*solidity',
         ErrorType.TYPE_ERROR,
         "Fix Solidity type error", 0.9),
        (r'Undeclared\s+identifier|not\s+found\s+in\s+scope',
         ErrorType.UNDEFINED_VARIABLE,
         "Fix Solidity undefined identifier", 0.9),
        (r'ParserError:|SyntaxError:.*solidity',
         ErrorType.SYNTAX_ERROR,
         "Fix Solidity syntax error", 0.9),
        (r'CompilerError:|InternalCompilerError',
         ErrorType.CONFIG_ERROR,
         "Fix Solidity compiler error", 0.85),
        (r'out\s+of\s+gas|gas\s+required\s+exceeds',
         ErrorType.CONFIG_ERROR,
         "Fix Solidity gas issue", 0.8),
        (r'revert|require\s+failed|assert\s+failed',
         ErrorType.TYPE_ERROR,
         "Fix Solidity require/assert", 0.8),

        # =================================================================
        # ANGULAR / VUE ERRORS
        # =================================================================
        (r'NG\d+:|Angular.*error|@angular.*error',
         ErrorType.CONFIG_ERROR,
         "Fix Angular error", 0.9),
        (r'Template\s+parse\s+errors|Can\'t\s+bind\s+to',
         ErrorType.CONFIG_ERROR,
         "Fix Angular template error", 0.9),
        (r'\[Vue\s+warn\]|VueCompilerError|vue.*error',
         ErrorType.CONFIG_ERROR,
         "Fix Vue error", 0.9),
        (r'Component.*is\s+not\s+defined|Unknown\s+custom\s+element',
         ErrorType.IMPORT_ERROR,
         "Fix Vue/Angular component import", 0.9),
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
        # JavaScript/TypeScript patterns
        r'(?:at\s+|in\s+|file:\s*)?([a-zA-Z0-9_\-./\\]+\.[jt]sx?):(\d+)',  # file.tsx:123
        r'([a-zA-Z0-9_\-./\\]+\.[jt]sx?)\s*\((\d+),\s*\d+\)',  # file.tsx (123, 45)
        r'Error\s+in\s+([a-zA-Z0-9_\-./\\]+\.[jt]sx?):(\d+)',  # Error in file.tsx:123
        r'→\s*([a-zA-Z0-9_\-./\\]+\.[jt]sx?):(\d+)',  # → file.tsx:123
        # Java patterns
        r'\[ERROR\]\s*(/[a-zA-Z0-9_\-./\\]+\.java):\[(\d+),\d+\]',  # [ERROR] /path/File.java:[42,21]
        r'([a-zA-Z0-9_\-./\\]+\.java):\[(\d+),\s*\d+\]',  # File.java:[42,21]
        r'at\s+[a-zA-Z0-9_.]+\(([a-zA-Z0-9_]+\.java):(\d+)\)',  # at com.foo.Bar(File.java:42)
        r'([a-zA-Z0-9_\-./\\]+\.java):(\d+):',  # File.java:42:
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
        """
        Extract file path and line number from error text.

        IMPORTANT: For Java compilation errors, we must find the ACTUAL error file,
        not just the first file mentioned. The error format is:
        [ERROR] /app/src/main/java/com/example/File.java:[42,9] error message

        The fix must target THIS file, not other files mentioned in the output.
        """
        # =====================================================================
        # STEP 1: For Java errors, specifically look for [ERROR] lines first
        # These are the ACTUAL compilation errors, not just mentions
        # =====================================================================
        java_error_pattern = r'\[ERROR\]\s*(/[a-zA-Z0-9_\-./\\]+\.java):\[(\d+),\s*\d+\]'
        java_errors = re.findall(java_error_pattern, text)

        if java_errors:
            # Return the FIRST actual error (not the first mention)
            file_path, line_str = java_errors[0]
            line_number = int(line_str) if line_str else None
            file_path = file_path.replace('\\', '/')
            file_path = cls._normalize_container_path(file_path)
            logger.info(f"[ErrorClassifier] Extracted Java error file: {file_path}:{line_number}")
            return file_path, line_number

        # =====================================================================
        # STEP 2: Fallback to general patterns for non-Java errors
        # =====================================================================
        for pattern in cls.FILE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                file_path = match.group(1)
                line_number = int(match.group(2)) if match.lastindex >= 2 else None
                # Normalize path
                file_path = file_path.replace('\\', '/')
                # Strip container path prefixes (Docker containers use /app as workdir)
                file_path = cls._normalize_container_path(file_path)
                return file_path, line_number
        return None, None

    @classmethod
    def extract_all_error_files(cls, text: str) -> List[Tuple[str, int]]:
        """
        Extract ALL files with errors, useful for batch fixing.

        Returns:
            List of (file_path, line_number) tuples for all files with errors
        """
        error_files = []
        seen_files = set()

        # For Java, extract all [ERROR] lines
        java_error_pattern = r'\[ERROR\]\s*(/[a-zA-Z0-9_\-./\\]+\.java):\[(\d+),\s*\d+\]'
        for match in re.finditer(java_error_pattern, text):
            file_path = match.group(1)
            line_number = int(match.group(2)) if match.group(2) else 0
            file_path = file_path.replace('\\', '/')
            file_path = cls._normalize_container_path(file_path)

            if file_path not in seen_files:
                error_files.append((file_path, line_number))
                seen_files.add(file_path)

        # Also check general patterns for non-Java files
        for pattern in cls.FILE_PATTERNS:
            for match in re.finditer(pattern, text):
                file_path = match.group(1)
                line_number = int(match.group(2)) if match.lastindex >= 2 else 0
                file_path = file_path.replace('\\', '/')
                file_path = cls._normalize_container_path(file_path)

                if file_path not in seen_files:
                    error_files.append((file_path, line_number))
                    seen_files.add(file_path)

        return error_files

    @classmethod
    def _normalize_container_path(cls, file_path: str) -> str:
        """
        Normalize container paths to local project paths.

        Container paths like /app/src/main/java/... need to be mapped to:
        - backend/src/main/java/... for Java files
        - frontend/src/... for JS/TS files (if in /app/src without java)
        """
        # Strip common container workdir prefixes
        container_prefixes = ['/app/', '/workspace/', '/home/app/', '/var/app/']
        for prefix in container_prefixes:
            if file_path.startswith(prefix):
                file_path = file_path[len(prefix):]
                break

        # For Java files, ensure backend/ prefix if it's a src/main/java path
        if file_path.endswith('.java'):
            if file_path.startswith('src/main/java/') or file_path.startswith('src/test/java/'):
                # This is likely a backend Java file
                file_path = 'backend/' + file_path

        return file_path

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
For Java: add missing package import (e.g., import java.time.LocalDateTime;)
For JavaScript/TypeScript: fix the import path or named import.
Return ONLY a unified diff or <file path="...">complete content</file>.""",

            ErrorType.SYNTAX_ERROR: """Error type: SYNTAX_ERROR
Fix the syntax error (mismatched brackets/tokens).
Return the COMPLETE fixed file using <file path="...">content</file>""",

            ErrorType.TYPE_ERROR: """Error type: TYPE_ERROR
Fix the type error (TypeScript or Java).
For Java constructor errors: add the missing constructor or fix method signatures.
For TypeScript: fix the type annotation.
Return ONLY a unified diff or <file path="...">complete content</file> for Java.""",

            ErrorType.UNDEFINED_VARIABLE: """Error type: UNDEFINED_VARIABLE
Fix the undefined variable/symbol by adding import or declaration.
For Java: add missing import statement or declare the missing class/method.
Return ONLY a unified diff or <file path="...">complete content</file>.""",

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
