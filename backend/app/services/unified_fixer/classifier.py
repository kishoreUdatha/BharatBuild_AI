"""
Error Classifier - Fast rule-based error classification

NO AI - Pure regex patterns - < 1ms classification
Categorizes errors for optimal fix strategy selection
"""

import re
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Tuple


class ErrorCategory(Enum):
    """Error categories for fix strategy selection"""
    DEPENDENCY = "dependency"      # npm install, pip install
    IMPORT = "import"              # Missing imports, wrong paths
    SYNTAX = "syntax"              # Parse errors, typos
    TYPE = "type"                  # TypeScript/type errors
    CONFIG = "config"              # Missing config files
    PORT = "port"                  # Port in use
    PERMISSION = "permission"      # File permission errors
    ENV = "env"                    # Environment variables
    RUNTIME = "runtime"            # Runtime logic errors
    BUILD = "build"                # Build/compile errors
    UNKNOWN = "unknown"            # Needs AI analysis


class ErrorSeverity(Enum):
    """Error severity for prioritization"""
    LOW = 1       # Warnings, style issues
    MEDIUM = 2    # Fixable errors
    HIGH = 3      # Blocking errors
    CRITICAL = 4  # System failures


class FixTier(Enum):
    """Fix strategy tier"""
    DETERMINISTIC = 1  # Free, instant, pattern-based
    HAIKU = 2          # Fast AI, $0.001
    SONNET = 3         # Smart AI, $0.01


@dataclass
class ClassifiedError:
    """Classified error with metadata"""
    original_error: str
    category: ErrorCategory
    severity: ErrorSeverity
    recommended_tier: FixTier

    # Extracted info
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    module_name: Optional[str] = None

    # For deterministic fixes
    fix_command: Optional[str] = None
    fix_content: Optional[str] = None

    # Confidence
    confidence: float = 0.9


class ErrorClassifier:
    """
    Fast rule-based error classifier.

    Patterns are ordered by specificity - first match wins.
    NO AI calls - pure regex - < 1ms classification.
    """

    # =========================================================================
    # TIER 1: Deterministic patterns (can be fixed without AI)
    # =========================================================================

    DEPENDENCY_PATTERNS = [
        # NPM
        (r"Cannot find module ['\"]([^'\"]+)['\"]", "npm_module"),
        (r"Module not found:.*['\"]([^'\"]+)['\"]", "npm_module"),
        (r"npm ERR! code ERESOLVE", "npm_resolve"),
        (r"npm ERR! peer dep missing", "npm_peer"),
        (r"npm ERR! code E404.*([^\s]+)", "npm_404"),

        # Python
        (r"ModuleNotFoundError: No module named ['\"]?([^'\"]+)['\"]?", "pip_module"),
        (r"ImportError: No module named ([^\s]+)", "pip_module"),
        (r"No matching distribution found for ([^\s]+)", "pip_404"),

        # PostCSS/Tailwind
        (r"\[postcss\].*Cannot find module ['\"]([^'\"]+)['\"]", "postcss_plugin"),
        (r"Error: Cannot find module ['\"](@tailwindcss/[^'\"]+)['\"]", "tailwind_plugin"),
    ]

    CONFIG_PATTERNS = [
        (r"ENOENT.*tsconfig\.node\.json", "tsconfig_node"),
        (r"Cannot find.*tsconfig\.json", "tsconfig"),
        (r"Cannot find.*postcss\.config", "postcss_config"),
        (r"Cannot find.*tailwind\.config", "tailwind_config"),
        (r"Cannot find.*vite\.config", "vite_config"),
        (r"parsing.*\.env.*failed", "env_file"),
    ]

    PORT_PATTERNS = [
        (r"EADDRINUSE.*:(\d+)", "port_in_use"),
        (r"address already in use.*:(\d+)", "port_in_use"),
        (r"port (\d+) is already in use", "port_in_use"),
    ]

    # =========================================================================
    # TIER 2: Simple AI patterns (Haiku can handle)
    # =========================================================================

    IMPORT_PATTERNS = [
        (r"Cannot find module ['\"]\.\/([^'\"]+)['\"]", "local_import"),
        (r"Failed to resolve import ['\"]([^'\"]+)['\"]", "import_resolve"),
        (r"Module ['\"]([^'\"]+)['\"] has no exported member", "named_import"),
        (r"'([^']+)' is not exported from", "export_missing"),
    ]

    SYNTAX_PATTERNS = [
        (r"SyntaxError: (.+)", "syntax"),
        (r"Unexpected token (.+)", "token"),
        (r"Parse error: (.+)", "parse"),
        (r"Expected (.+) but found (.+)", "expected"),
        (r"Unterminated string", "string"),
        (r"Missing semicolon", "semicolon"),
    ]

    TYPE_PATTERNS = [
        (r"Type '([^']+)' is not assignable to type '([^']+)'", "type_mismatch"),
        (r"Property '([^']+)' does not exist on type", "missing_property"),
        (r"Cannot find name '([^']+)'", "undefined_name"),
        (r"'([^']+)' is declared but.*never used", "unused"),
    ]

    # =========================================================================
    # TIER 3: Complex patterns (Sonnet needed)
    # =========================================================================

    RUNTIME_PATTERNS = [
        (r"TypeError: (.+)", "type_error"),
        (r"ReferenceError: (.+) is not defined", "reference"),
        (r"RangeError: (.+)", "range"),
        (r"Error: (.+)", "generic"),
    ]

    BUILD_PATTERNS = [
        (r"Build failed", "build_fail"),
        (r"Compilation failed", "compile_fail"),
        (r"error TS\d+:", "typescript"),
        (r"\[ERROR\].*BUILD FAILURE", "maven"),
        (r"FAILURE: Build failed", "gradle"),
    ]

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for speed"""
        self._compiled = {
            ErrorCategory.DEPENDENCY: [(re.compile(p, re.I | re.M), t) for p, t in self.DEPENDENCY_PATTERNS],
            ErrorCategory.CONFIG: [(re.compile(p, re.I | re.M), t) for p, t in self.CONFIG_PATTERNS],
            ErrorCategory.PORT: [(re.compile(p, re.I | re.M), t) for p, t in self.PORT_PATTERNS],
            ErrorCategory.IMPORT: [(re.compile(p, re.I | re.M), t) for p, t in self.IMPORT_PATTERNS],
            ErrorCategory.SYNTAX: [(re.compile(p, re.I | re.M), t) for p, t in self.SYNTAX_PATTERNS],
            ErrorCategory.TYPE: [(re.compile(p, re.I | re.M), t) for p, t in self.TYPE_PATTERNS],
            ErrorCategory.RUNTIME: [(re.compile(p, re.I | re.M), t) for p, t in self.RUNTIME_PATTERNS],
            ErrorCategory.BUILD: [(re.compile(p, re.I | re.M), t) for p, t in self.BUILD_PATTERNS],
        }

    def classify(self, error: str, file_path: str = None) -> ClassifiedError:
        """
        Classify an error and recommend fix strategy.

        Args:
            error: Error message/output
            file_path: Optional file path for context

        Returns:
            ClassifiedError with category, severity, and recommended tier
        """
        # Extract file path and line number from error if not provided
        if not file_path:
            file_path = self._extract_file_path(error)
        line_number = self._extract_line_number(error)

        # Try each category in order of tier (cheapest first)

        # TIER 1: Deterministic (free)
        for category in [ErrorCategory.DEPENDENCY, ErrorCategory.CONFIG, ErrorCategory.PORT]:
            match, error_type, groups = self._match_category(error, category)
            if match:
                return self._create_tier1_result(
                    error, category, error_type, groups,
                    file_path, line_number
                )

        # TIER 2: Simple AI (Haiku)
        for category in [ErrorCategory.IMPORT, ErrorCategory.SYNTAX, ErrorCategory.TYPE]:
            match, error_type, groups = self._match_category(error, category)
            if match:
                return ClassifiedError(
                    original_error=error,
                    category=category,
                    severity=ErrorSeverity.MEDIUM,
                    recommended_tier=FixTier.HAIKU,
                    file_path=file_path,
                    line_number=line_number,
                    module_name=groups[0] if groups else None
                )

        # TIER 3: Complex AI (Sonnet)
        for category in [ErrorCategory.RUNTIME, ErrorCategory.BUILD]:
            match, error_type, groups = self._match_category(error, category)
            if match:
                return ClassifiedError(
                    original_error=error,
                    category=category,
                    severity=ErrorSeverity.HIGH,
                    recommended_tier=FixTier.SONNET,
                    file_path=file_path,
                    line_number=line_number
                )

        # Unknown - needs Sonnet
        return ClassifiedError(
            original_error=error,
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.MEDIUM,
            recommended_tier=FixTier.SONNET,
            file_path=file_path,
            line_number=line_number
        )

    def _match_category(
        self,
        error: str,
        category: ErrorCategory
    ) -> Tuple[bool, Optional[str], List[str]]:
        """Match error against category patterns"""
        patterns = self._compiled.get(category, [])

        for pattern, error_type in patterns:
            match = pattern.search(error)
            if match:
                return True, error_type, list(match.groups())

        return False, None, []

    def _create_tier1_result(
        self,
        error: str,
        category: ErrorCategory,
        error_type: str,
        groups: List[str],
        file_path: str,
        line_number: int
    ) -> ClassifiedError:
        """Create result for Tier 1 (deterministic) errors with fix command/content"""
        result = ClassifiedError(
            original_error=error,
            category=category,
            severity=ErrorSeverity.MEDIUM,
            recommended_tier=FixTier.DETERMINISTIC,
            file_path=file_path,
            line_number=line_number
        )

        # Generate deterministic fix
        if error_type == "npm_module" and groups:
            module = groups[0].split('/')[0]  # Get base package
            if module.startswith('@'):
                # Scoped package
                module = '/'.join(groups[0].split('/')[:2])
            result.module_name = module
            result.fix_command = f"npm install {module}"

        elif error_type == "pip_module" and groups:
            result.module_name = groups[0]
            result.fix_command = f"pip install {groups[0]}"

        elif error_type == "postcss_plugin" and groups:
            result.module_name = groups[0]
            result.fix_command = f"npm install -D {groups[0]}"

        elif error_type == "tailwind_plugin" and groups:
            result.module_name = groups[0]
            result.fix_command = f"npm install -D {groups[0]}"

        elif error_type == "tsconfig_node":
            result.file_path = "tsconfig.node.json"
            result.fix_content = '''{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}'''

        elif error_type == "postcss_config":
            result.file_path = "postcss.config.js"
            result.fix_content = '''module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}'''

        elif error_type == "port_in_use" and groups:
            port = int(groups[0])
            result.fix_command = f"kill_port_{port}"  # Special command
            result.module_name = str(port)

        return result

    def _extract_file_path(self, error: str) -> Optional[str]:
        """Extract file path from error message"""
        patterns = [
            r'(?:at |in |File )["\']?([^"\':\s]+\.[a-zA-Z]+)',
            r'([a-zA-Z0-9_\-./]+\.[tj]sx?):?\d*',
            r'([a-zA-Z0-9_\-./]+\.py):?\d*',
        ]

        for pattern in patterns:
            match = re.search(pattern, error)
            if match:
                return match.group(1)

        return None

    def _extract_line_number(self, error: str) -> Optional[int]:
        """Extract line number from error message"""
        patterns = [
            r':(\d+):\d+',
            r'line (\d+)',
            r'Line (\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, error)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass

        return None


# Singleton instance
error_classifier = ErrorClassifier()
