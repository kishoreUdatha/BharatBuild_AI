"""
Bolt Fixer - Unified fixer using Bolt.new architecture

This replaces SimpleFixer with the proper Bolt.new pattern:
1. Error Classifier (rule-based, NO AI)
2. Decision Gate (should Claude be called?)
3. Retry Limiter (max attempts)
4. Claude API (strict prompt, diff only)
5. Patch Validator (validate before apply)
6. Diff Parser (pure Python, no git)
7. Patch Applier (atomic with rollback)

Claude is a tool, not a controller.
"""

from typing import Dict, Any, List, Optional, Tuple, Callable, Set
from dataclasses import dataclass
from pathlib import Path
import re

from app.core.logging_config import logger


# =============================================================================
# TECHNOLOGY DETECTION - Maps file extensions to languages
# =============================================================================
EXTENSION_TO_LANGUAGE = {
    # Java/JVM
    '.java': 'java',
    '.kt': 'kotlin',
    '.scala': 'scala',
    '.groovy': 'groovy',
    # Python
    '.py': 'python',
    '.pyx': 'python',
    '.pyi': 'python',
    # JavaScript/TypeScript
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.mjs': 'javascript',
    '.cjs': 'javascript',
    # Go
    '.go': 'go',
    # Rust
    '.rs': 'rust',
    # C/C++
    '.c': 'c',
    '.h': 'c',
    '.cpp': 'cpp',
    '.hpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    # C#
    '.cs': 'csharp',
    # Ruby
    '.rb': 'ruby',
    '.rake': 'ruby',
    # PHP
    '.php': 'php',
    # Swift
    '.swift': 'swift',
    # Dart/Flutter
    '.dart': 'dart',
    # Web
    '.html': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.sass': 'sass',
    '.less': 'less',
    '.vue': 'vue',
    '.svelte': 'svelte',
    # Config/Data
    '.json': 'json',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.xml': 'xml',
    '.toml': 'toml',
    # Shell
    '.sh': 'bash',
    '.bash': 'bash',
    '.zsh': 'zsh',
    # Docker
    'Dockerfile': 'dockerfile',
    # SQL
    '.sql': 'sql',
}

# Language-specific keywords to filter out when extracting class/module names
LANGUAGE_KEYWORDS = {
    'java': {'String', 'int', 'Integer', 'long', 'Long', 'boolean', 'Boolean',
             'void', 'Object', 'List', 'Map', 'Set', 'Collection', 'Optional',
             'Class', 'Exception', 'Error', 'Throwable', 'Double', 'Float'},
    'python': {'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple',
               'None', 'True', 'False', 'object', 'type', 'Exception', 'self',
               'cls', 'async', 'await', 'def', 'class', 'import', 'from'},
    'typescript': {'string', 'number', 'boolean', 'any', 'void', 'null',
                   'undefined', 'never', 'unknown', 'object', 'Array', 'Promise',
                   'Record', 'Partial', 'Required', 'Pick', 'Omit', 'Exclude'},
    'javascript': {'string', 'number', 'boolean', 'null', 'undefined', 'object',
                   'Array', 'Promise', 'function', 'class', 'const', 'let', 'var'},
    'go': {'string', 'int', 'int8', 'int16', 'int32', 'int64', 'uint', 'float32',
           'float64', 'bool', 'byte', 'rune', 'error', 'nil', 'interface', 'struct',
           'map', 'chan', 'func', 'package', 'import', 'type'},
    'rust': {'str', 'String', 'i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64',
             'f32', 'f64', 'bool', 'char', 'Option', 'Result', 'Vec', 'Box', 'Rc',
             'Arc', 'Self', 'self', 'pub', 'mod', 'use', 'fn', 'struct', 'enum'},
    'csharp': {'string', 'int', 'long', 'float', 'double', 'bool', 'void', 'object',
               'var', 'dynamic', 'Task', 'List', 'Dictionary', 'IEnumerable'},
    'ruby': {'String', 'Integer', 'Float', 'Array', 'Hash', 'Symbol', 'nil',
             'true', 'false', 'self', 'class', 'module', 'def', 'end'},
    'php': {'string', 'int', 'float', 'bool', 'array', 'object', 'null', 'void',
            'mixed', 'callable', 'iterable', 'self', 'static', 'parent'},
}

# File patterns for related file detection by language
RELATED_FILE_PATTERNS = {
    'java': {
        'suffixes': ['Service', 'ServiceImpl', 'Repository', 'Controller', 'Dto', 'DTO', 'Entity', 'Model', 'Mapper'],
        'extensions': ['.java'],
    },
    'python': {
        'suffixes': ['_service', '_repository', '_controller', '_model', '_schema', '_dto', '_api', '_views', '_serializer'],
        'extensions': ['.py'],
    },
    'typescript': {
        'suffixes': ['.service', '.component', '.module', '.controller', '.dto', '.entity', '.model', '.interface', '.type', '.hook', '.context', '.store'],
        'extensions': ['.ts', '.tsx'],
    },
    'javascript': {
        'suffixes': ['.service', '.component', '.module', '.controller', '.model', '.hook', '.context', '.store', '.util'],
        'extensions': ['.js', '.jsx'],
    },
    'go': {
        'suffixes': ['_service', '_repository', '_handler', '_controller', '_model', '_dto', '_test'],
        'extensions': ['.go'],
    },
    'rust': {
        'suffixes': ['_service', '_repository', '_handler', '_controller', '_model', '_dto'],
        'extensions': ['.rs'],
    },
    'csharp': {
        'suffixes': ['Service', 'Repository', 'Controller', 'Dto', 'DTO', 'Entity', 'Model', 'Interface'],
        'extensions': ['.cs'],
    },
    'ruby': {
        'suffixes': ['_controller', '_model', '_service', '_serializer', '_job', '_mailer', '_helper'],
        'extensions': ['.rb'],
    },
    'php': {
        'suffixes': ['Service', 'Repository', 'Controller', 'Entity', 'Model', 'DTO', 'Interface'],
        'extensions': ['.php'],
    },
}


def detect_language(file_path: str) -> str:
    """
    Detect programming language from file path.

    Args:
        file_path: File path or name

    Returns:
        Language identifier (e.g., 'java', 'python', 'typescript')
    """
    if not file_path:
        return 'unknown'

    path = Path(file_path)
    name = path.name
    suffix = path.suffix.lower()

    # Check for special files (Dockerfile, etc.)
    if name in EXTENSION_TO_LANGUAGE:
        return EXTENSION_TO_LANGUAGE[name]

    # Check by extension
    if suffix in EXTENSION_TO_LANGUAGE:
        return EXTENSION_TO_LANGUAGE[suffix]

    return 'unknown'


def get_syntax_highlight(file_path: str) -> str:
    """
    Get syntax highlighting language for markdown code blocks.

    Args:
        file_path: File path or name

    Returns:
        Syntax highlighting identifier for markdown
    """
    lang = detect_language(file_path)

    # Map some languages to their markdown syntax names
    syntax_map = {
        'typescript': 'typescript',
        'javascript': 'javascript',
        'python': 'python',
        'java': 'java',
        'go': 'go',
        'rust': 'rust',
        'csharp': 'csharp',
        'ruby': 'ruby',
        'php': 'php',
        'swift': 'swift',
        'dart': 'dart',
        'kotlin': 'kotlin',
        'scala': 'scala',
        'cpp': 'cpp',
        'c': 'c',
        'html': 'html',
        'css': 'css',
        'scss': 'scss',
        'json': 'json',
        'yaml': 'yaml',
        'xml': 'xml',
        'bash': 'bash',
        'sql': 'sql',
        'dockerfile': 'dockerfile',
        'vue': 'vue',
        'svelte': 'svelte',
    }

    return syntax_map.get(lang, lang if lang != 'unknown' else '')


def get_language_keywords(file_path: str) -> Set[str]:
    """
    Get keywords to filter out for a given file's language.

    Args:
        file_path: File path or name

    Returns:
        Set of keywords to filter out
    """
    lang = detect_language(file_path)
    return LANGUAGE_KEYWORDS.get(lang, set())


from app.services.error_classifier import ErrorClassifier, ErrorType, ClassifiedError
from app.services.patch_validator import PatchValidator
from app.services.retry_limiter import retry_limiter
from app.services.diff_parser import DiffParser
from app.services.patch_applier import PatchApplier
from app.services.storage_service import storage_service
from app.services.batch_tracker import batch_tracker
from app.services.dependency_graph import build_dependency_graph, DependencyGraph
from app.services.project_sanitizer import sanitize_project_file


# =============================================================================
# CONTEXT LIMIT CONFIGURATION
# =============================================================================
MAX_CONTEXT_CHARS = 100000      # ~25k tokens - safe limit for Claude
MAX_FILES_PER_BATCH = 6         # Max files to include in one fix
CHARS_PER_FILE_LIMIT = 12000    # Truncate files larger than this
CONTEXT_LINES_AROUND_ERROR = 60 # Lines to keep around error when truncating
MAX_FIX_PASSES = 5              # Maximum multi-pass fix attempts

# =============================================================================
# DOCKERFILE BASE IMAGE FIXES (Deterministic - No AI needed)
# =============================================================================
# Maps deprecated/unavailable Docker base images to working alternatives
DOCKERFILE_BASE_IMAGE_FIXES = {
    # OpenJDK images - use Eclipse Temurin (official OpenJDK distribution)
    "openjdk:latest": "eclipse-temurin:17-jdk-alpine",
    "openjdk:17": "eclipse-temurin:17-jdk-alpine",
    "openjdk:17-slim": "eclipse-temurin:17-jdk-alpine",
    "openjdk:17-jdk-slim": "eclipse-temurin:17-jdk-alpine",
    "openjdk:17-jdk": "eclipse-temurin:17-jdk-alpine",
    "openjdk:11": "eclipse-temurin:11-jdk-alpine",
    "openjdk:11-slim": "eclipse-temurin:11-jdk-alpine",
    "openjdk:11-jdk-slim": "eclipse-temurin:11-jdk-alpine",
    "openjdk:11-jdk": "eclipse-temurin:11-jdk-alpine",
    "openjdk:21": "eclipse-temurin:21-jdk-alpine",
    "openjdk:21-slim": "eclipse-temurin:21-jdk-alpine",
    "openjdk:21-jdk-slim": "eclipse-temurin:21-jdk-alpine",
    "openjdk:21-jdk": "eclipse-temurin:21-jdk-alpine",
    "java:latest": "eclipse-temurin:17-jdk-alpine",
    # Maven images - use eclipse-temurin based versions
    "maven:latest": "maven:3.9-eclipse-temurin-17-alpine",
    "maven:3.8.4-openjdk-17-slim": "maven:3.9-eclipse-temurin-17-alpine",
    "maven:3.8-openjdk-17-slim": "maven:3.9-eclipse-temurin-17-alpine",
    "maven:3.9-openjdk-17-slim": "maven:3.9-eclipse-temurin-17-alpine",
    "maven:3.8-openjdk-17": "maven:3.9-eclipse-temurin-17-alpine",
    "maven:3.9-openjdk-17": "maven:3.9-eclipse-temurin-17-alpine",
    "maven:3.8-openjdk-11-slim": "maven:3.9-eclipse-temurin-11-alpine",
    "maven:3.9-openjdk-11-slim": "maven:3.9-eclipse-temurin-11-alpine",
    # Gradle images
    "gradle:latest": "gradle:8-jdk17-alpine",
    "gradle:7-jdk17": "gradle:8-jdk17-alpine",
    # Node images
    "node:latest": "node:20-alpine",
    "node:18": "node:18-alpine",
    "node:20": "node:20-alpine",
    # Python images
    "python:latest": "python:3.11-slim",
    "python:3": "python:3.11-slim",
}


async def get_ai_image_replacement(bad_image: str, error_message: str = "") -> Optional[str]:
    """
    Use AI to suggest replacement for ANY unavailable Docker image.

    This is a generic approach that works for all technologies:
    - Java, Python, Node, Go, Rust, Ruby, PHP, .NET
    - Databases, web servers, tools
    - Any current or future images

    Args:
        bad_image: The Docker image that failed (e.g., "openjdk:17-jdk-slim")
        error_message: Optional error context for better suggestions

    Returns:
        Replacement image string or None if AI couldn't suggest
    """
    import anthropic
    from app.core.config import settings

    # First check exact match (fast, no AI cost)
    if bad_image in DOCKERFILE_BASE_IMAGE_FIXES:
        return DOCKERFILE_BASE_IMAGE_FIXES[bad_image]

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Focused prompt - minimal tokens, fast response
        prompt = f"""Docker image "{bad_image}" is unavailable (manifest not found).

Return ONLY the working replacement image name. No explanation.

Requirements:
- Must be a real, currently available Docker Hub image
- Prefer official images or well-maintained alternatives
- Use alpine/slim variants when available for smaller size
- Keep the same major version if possible

Examples:
- openjdk:17-jdk-slim → eclipse-temurin:17-jdk-alpine
- maven:3.8-openjdk-17-slim → maven:3.9-eclipse-temurin-17-alpine
- node:18 → node:18-alpine
- python:3.11 → python:3.11-slim

Reply with ONLY the replacement image (e.g., "eclipse-temurin:17-jdk-alpine"):"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,  # Very small - just need image name
            temperature=0,  # Deterministic
            messages=[{"role": "user", "content": prompt}]
        )

        if response.content:
            replacement = response.content[0].text.strip()
            # Validate response looks like a Docker image
            if replacement and ':' in replacement and len(replacement) < 100:
                # Remove any quotes or extra text
                replacement = replacement.strip('"\'').split('\n')[0].strip()
                logger.info(f"[BoltFixer] AI suggested replacement: {bad_image} → {replacement}")
                return replacement

    except Exception as e:
        logger.warning(f"[BoltFixer] AI image replacement failed: {e}")

    return None


@dataclass
class BoltFixResult:
    """Result from BoltFixer - compatible with SimpleFixResult"""
    success: bool
    files_modified: List[str]
    message: str
    patches_applied: int = 0
    error_type: Optional[str] = None
    fix_strategy: Optional[str] = None
    current_pass: int = 1
    remaining_errors: int = 0
    needs_another_pass: bool = False


class BoltFixer:
    """
    Bolt.new style fixer with rule-based classification and atomic patches.

    Flow:
    1. Classify error (rule-based)
    2. Check if Claude-fixable
    3. Check retry limits
    4. Call Claude (strict prompt)
    5. Validate patch
    6. Apply atomically
    """

    # Strict system prompt - Claude returns ONLY diffs
    SYSTEM_PROMPT = """You are an automated code-fix agent supporting ALL programming languages.

STRICT RULES:
- Return ONLY unified diffs or file blocks
- Do NOT explain
- Do NOT invent files
- Do NOT modify unrelated code

CRITICAL - FIX ALL ERROR FILES IN ONE RESPONSE:
The build has MULTIPLE files with errors. You MUST fix ALL of them in a single response.
- Read the ERROR FILES section carefully - each file listed has errors
- Output a separate <file> or <patch> block for EACH file that needs fixing
- Do NOT just fix one file and stop - fix ALL files with errors

IMPORTANT - DEPENDENCY ERRORS (ALL LANGUAGES):
When you see errors like:
- Java: "cannot find symbol: method X()" - Add the missing method to the CLASS that should have it
- Python: "AttributeError: 'X' has no attribute 'y'" - Add the missing attribute/method to class X
- TypeScript: "Property 'x' does not exist on type 'Y'" - Add the property to interface/type Y
- Go: "undefined: X" - Add the missing function/type X
- Rust: "cannot find value/type `x`" - Add the missing item to the module

🚨 MISSING CLASS/FILE ERRORS - CREATE THE FILE:
When you see "cannot find symbol: class XxxDto" or similar CLASS NOT FOUND errors:
- Java: CREATE the missing class/enum/DTO using <newfile path="backend/src/main/java/com/package/XxxDto.java">
- TypeScript: CREATE missing interface/type using <newfile path="src/types/Xxx.ts">
- Python: CREATE missing module using <newfile path="src/xxx.py">

For Java "cannot find symbol: class" errors:
1. Look at the import statement to get the FULL package path
2. Create file at: backend/src/main/java/[package/path]/[ClassName].java
3. Include proper package declaration, imports, and complete class implementation

Example: If error is "cannot find symbol: class OrderStatus" with import "com.goldmart.model.enums.OrderStatus":
<newfile path="backend/src/main/java/com/goldmart/model/enums/OrderStatus.java">
package com.goldmart.model.enums;

public enum OrderStatus {
    PENDING, CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED
}
</newfile>

FIX THE ROOT CAUSE, NOT THE SYMPTOM:
- If OrderService fails because Product is missing getPrice(), fix Product
- If the error file imports/uses another module, check RELATED FILES section for the fix
- Return patches for ALL files that need changes (you can return multiple patches)

MULTI-FILE CONSISTENCY (ALL LANGUAGES):
1. Check ALL RELATED FILES (models, services, controllers, interfaces)
2. Ensure field/method/function names match EXACTLY across related files
3. If interface missing method - add to BOTH interface AND implementation
4. Output MULTIPLE <file> blocks - one for EACH file that needs changes
5. For TypeScript/Python: ensure types/type hints match across files

OUTPUT FORMAT:

For patching existing files:
<patch>
--- path/to/file
+++ path/to/file
@@ -line,count +line,count @@
- old line
+ new line
</patch>

For creating missing files:
<newfile path="path/to/file">
file content
</newfile>

For full file replacement (syntax errors):
<file path="path/to/file">
complete file content
</file>

If no fix possible: <patch></patch>

No text outside blocks. No markdown. No commentary."""

    SYNTAX_FIX_PROMPT = """You are fixing a SYNTAX ERROR.

Return the COMPLETE fixed file using:
<file path="filepath">complete content</file>

Rules:
- Return ENTIRE file, not a patch
- Fix all bracket mismatches
- Remove duplicate code blocks
- Maintain proper structure

No explanations. Only the <file> block."""

    def __init__(self):
        self._claude_client = None
        self._sandbox_file_writer = None  # Set by fix_from_backend if provided
        self._sandbox_file_reader = None  # Set by fix_from_backend if provided
        self._sandbox_file_lister = None  # Set by fix_from_backend if provided
        self._dependency_graph: Optional[DependencyGraph] = None
        self._current_project_id: Optional[str] = None

    @staticmethod
    def _normalize_file_path(file_path: str, add_prefix: bool = True) -> Tuple[str, bool]:
        """
        Centralized path normalization for consistency across all code paths.

        SECURITY: All path validation happens here - no other method should do its own.

        Args:
            file_path: Raw file path from AI or user
            add_prefix: If True, adds backend/frontend prefix based on file type

        Returns:
            Tuple of (normalized_path, is_valid)
            - normalized_path: Cleaned path with correct prefix
            - is_valid: False if path contains dangerous patterns
        """
        if not file_path or not file_path.strip():
            return "", False

        # Step 1: Basic cleanup
        normalized = file_path.strip()

        # Step 2: Normalize separators (Windows -> Unix)
        normalized = normalized.replace('\\', '/')

        # =================================================================
        # Step 3: SECURITY - Check for path traversal BEFORE any stripping
        # This catches absolute paths and .. sequences
        # =================================================================
        if '..' in normalized:
            logger.warning(f"[BoltFixer] SECURITY: Path traversal (..) blocked: {file_path}")
            return "", False

        # Check for absolute paths (must happen BEFORE lstrip)
        if normalized.startswith('/') or (len(normalized) > 1 and normalized[1] == ':'):
            logger.warning(f"[BoltFixer] SECURITY: Absolute path blocked: {file_path}")
            return "", False

        # Step 4: Remove leading dots and slashes (safe now that we checked)
        normalized = normalized.lstrip('./')

        # Step 5: Check for empty after stripping
        if not normalized:
            return "", False

        # Step 6: Check for double prefixes (backend/backend/ or frontend/frontend/)
        while normalized.startswith('backend/backend/'):
            normalized = normalized.replace('backend/backend/', 'backend/', 1)
            logger.warning(f"[BoltFixer] Fixed double backend prefix: {file_path}")
        while normalized.startswith('frontend/frontend/'):
            normalized = normalized.replace('frontend/frontend/', 'frontend/', 1)
            logger.warning(f"[BoltFixer] Fixed double frontend prefix: {file_path}")

        # Step 7: Add backend/frontend prefix if needed
        if add_prefix and not normalized.startswith('backend/') and not normalized.startswith('frontend/'):
            # Determine prefix based on file extension
            if normalized.endswith(('.java', '.kt', '.scala', '.gradle', '.xml', '.properties', '.sql')):
                normalized = f"backend/{normalized}"
            elif normalized.endswith(('.ts', '.tsx', '.js', '.jsx', '.css', '.scss', '.html', '.vue', '.svelte')):
                normalized = f"frontend/{normalized}"
            # Other files (Dockerfile, docker-compose.yml, .env, etc.) stay at root

        # Step 8: Remove any remaining double slashes
        while '//' in normalized:
            normalized = normalized.replace('//', '/')

        # Step 9: Final validation - no dangerous patterns should remain
        if '..' in normalized or normalized.startswith('/'):
            logger.warning(f"[BoltFixer] SECURITY: Final check failed: {normalized}")
            return "", False

        return normalized, True

    def _write_file(self, file_path: Path, content: str, project_id: str) -> bool:
        """
        Write a file using sandbox writer if available, otherwise local.

        In ECS/remote mode, files must be written via sandbox helper container,
        not directly via Python, because the sandbox filesystem is on a different host.

        GAP #8 FIX: Validates that sandbox_file_writer exists in remote mode.
        """
        import os

        try:
            # AUTO-SANITIZE: Apply technology-specific fixes before writing
            # This handles CSS @import order, Tailwind plugins, Vite config, pom.xml, etc.
            try:
                # FIX #3 & #22: Use full relative path for better sanitizer matching
                # Use _ for unused sanitized_path (we use file_path for writing)
                relative_path = str(file_path.name)  # Filename for sanitizer
                _, sanitized_content, fixes = sanitize_project_file(relative_path, content)
                # Only use sanitized content if sanitization succeeded
                if sanitized_content:
                    content = sanitized_content
                if fixes:
                    logger.info(f"[BoltFixer:{project_id}] Sanitizer applied: {', '.join(fixes)}")
            except Exception as sanitize_err:
                # FIX #3: Log warning but continue with original content (safe fallback)
                logger.warning(f"[BoltFixer:{project_id}] Sanitization skipped (using original): {sanitize_err}")

            # =================================================================
            # GAP #8 FIX: Check for remote mode without sandbox_file_writer
            # =================================================================
            is_remote_mode = bool(os.environ.get("SANDBOX_DOCKER_HOST"))

            if self._sandbox_file_writer:
                # Use sandbox file writer (handles remote mode)
                # Use str(file_path) directly - path is already absolute from project_path / relative_path
                # Don't use resolve() as the directory may not exist on backend container
                abs_path = str(file_path)
                success = self._sandbox_file_writer(abs_path, content)
                if success:
                    logger.info(f"[BoltFixer:{project_id}] Wrote file via sandbox: {abs_path}")
                else:
                    logger.error(f"[BoltFixer:{project_id}] Sandbox write failed: {abs_path}")
                return success
            elif is_remote_mode:
                # =================================================================
                # ISSUE #5 FIX: Remote mode without sandbox_file_writer MUST FAIL
                # Returning True here caused infinite retry loops because:
                # - Fix appears successful (returns True)
                # - But file is NOT written to sandbox (different container)
                # - Build fails again with same error
                # - Retry loop continues forever
                #
                # CORRECT BEHAVIOR: Return False so the fix is marked as failed
                # The error will be logged and user can investigate
                # =================================================================
                logger.error(
                    f"[BoltFixer:{project_id}] CRITICAL: Remote mode detected but no sandbox_file_writer! "
                    f"File cannot be written to sandbox: {file_path}. "
                    f"This is a configuration error - check execution.py sandbox_file_writer setup."
                )
                # DO NOT try local fallback - it won't help and causes confusion
                return False
            else:
                # Local mode - direct file write
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding='utf-8')
                logger.info(f"[BoltFixer:{project_id}] Wrote file locally: {file_path}")
                return True
        except Exception as e:
            logger.error(f"[BoltFixer:{project_id}] Error writing file {file_path}: {e}")
            return False

    async def _try_deterministic_dockerfile_fix(
        self,
        project_id: str,
        project_path: Path,
        error_output: str
    ) -> Optional[BoltFixResult]:
        """
        Deterministically fix Docker base image errors (NO AI NEEDED).

        This handles errors like:
        - "manifest for openjdk:17-jdk-slim not found"
        - "manifest unknown: manifest unknown"

        These are caused by deprecated/unavailable Docker base images.
        Fix: Replace with working alternatives from DOCKERFILE_BASE_IMAGE_FIXES.

        Args:
            project_id: Project ID for logging
            project_path: Path to project root
            error_output: Combined stdout/stderr from Docker build

        Returns:
            BoltFixResult if fixed, None if not applicable
        """
        # Check if this is a Docker base image error
        # FIX #1: Use non-capturing group for alternation to avoid IndexError
        manifest_pattern = r'manifest for ([^\s]+) not found|manifest unknown'
        match = re.search(manifest_pattern, error_output, re.IGNORECASE)

        if not match:
            return None

        # Extract the problematic image name
        # FIX #1: Safely check if group exists before accessing
        try:
            bad_image = match.group(1) if match.lastindex and match.lastindex >= 1 else None
        except (IndexError, AttributeError):
            bad_image = None

        logger.info(f"[BoltFixer:{project_id}] Detected Docker base image error: {bad_image or 'unknown'}")

        # Find all Dockerfiles in the project
        dockerfile_paths = []
        possible_dockerfiles = [
            project_path / "Dockerfile",
            project_path / "backend" / "Dockerfile",
            project_path / "backend" / "Dockerfile.light",
            project_path / "frontend" / "Dockerfile",
        ]

        for dockerfile in possible_dockerfiles:
            try:
                if self._sandbox_file_reader:
                    content = self._sandbox_file_reader(str(dockerfile))
                    if content:
                        dockerfile_paths.append((dockerfile, content))
                elif dockerfile.exists():
                    dockerfile_paths.append((dockerfile, dockerfile.read_text(encoding='utf-8')))
            except Exception:
                continue

        if not dockerfile_paths:
            logger.warning(f"[BoltFixer:{project_id}] No Dockerfiles found to fix")
            return None

        files_modified = []

        for dockerfile_path, content in dockerfile_paths:
            original_content = content
            modified = False

            # Try to fix the specific bad image
            if bad_image:
                # Tier 1: Check exact match in dictionary (fast, no AI cost)
                replacement = DOCKERFILE_BASE_IMAGE_FIXES.get(bad_image)

                # Tier 2: Use AI to get replacement (generic, works for any image)
                if not replacement:
                    logger.info(f"[BoltFixer:{project_id}] No exact match for {bad_image}, asking AI...")
                    replacement = await get_ai_image_replacement(bad_image, error_output)

                # Apply the replacement if found
                if replacement:
                    pattern = rf'^(FROM\s+){re.escape(bad_image)}(\s|$)'
                    new_content = re.sub(pattern, rf'\g<1>{replacement}\2', content, flags=re.MULTILINE)
                    if new_content != content:
                        content = new_content
                        modified = True
                        logger.info(f"[BoltFixer:{project_id}] Fixed: {bad_image} -> {replacement}")

            # Also scan for any other deprecated images in the file (dictionary only - fast)
            for old_image, new_image in DOCKERFILE_BASE_IMAGE_FIXES.items():
                if old_image in content:
                    pattern = rf'^(FROM\s+){re.escape(old_image)}(\s|$)'
                    new_content = re.sub(pattern, rf'\g<1>{new_image}\2', content, flags=re.MULTILINE)
                    if new_content != content:
                        content = new_content
                        modified = True
                        logger.info(f"[BoltFixer:{project_id}] Fixed: {old_image} -> {new_image}")

            if modified and content != original_content:
                # Write the fixed content to sandbox
                if self._write_file(dockerfile_path, content, project_id):
                    # Get relative path
                    try:
                        rel_path = str(dockerfile_path.relative_to(project_path))
                    except ValueError:
                        rel_path = str(dockerfile_path)

                    # FIX: Normalize Dockerfile path using helper
                    # add_prefix=False because Dockerfiles stay at root
                    normalized_path, is_valid = self._normalize_file_path(rel_path, add_prefix=False)
                    if not is_valid:
                        logger.warning(f"[BoltFixer:{project_id}] Invalid Dockerfile path: {rel_path}")
                        continue

                    # IMMEDIATELY persist this fix to S3/database
                    # FIX: Check return value of _persist_single_fix()
                    if await self._persist_single_fix(project_id, project_path, normalized_path, content):
                        files_modified.append(normalized_path)
                        logger.info(f"[BoltFixer:{project_id}] ✓ Fixed & persisted: {normalized_path}")
                    else:
                        logger.warning(f"[BoltFixer:{project_id}] Dockerfile fixed but persistence failed: {normalized_path}")

        if files_modified:
            return BoltFixResult(
                success=True,
                files_modified=files_modified,
                message=f"Deterministic fix: Replaced deprecated Docker base images in {len(files_modified)} file(s)",
                patches_applied=len(files_modified),
                error_type="dockerfile_base_image",
                fix_strategy="deterministic"
            )

        return None

    async def _persist_single_fix(
        self,
        project_id: str,
        project_path: Path,
        file_path: str,
        content: str
    ) -> bool:
        """
        Track a SINGLE fix after writing to EC2 sandbox.

        IMPORTANT: This function NO LONGER uploads to S3 during fixes.

        The correct flow is:
        1. BoltFixer fixes file on EC2 sandbox (via _write_file)
        2. This function just tracks that a fix was applied (logs only)
        3. On retry, dir exists → skip S3 restore → use EC2 files
        4. After BUILD SUCCESS → execution.py syncs EC2 to S3

        This prevents the issue where S3 restore would overwrite EC2 fixes on retry.

        Args:
            project_id: Project ID
            project_path: Path to project root
            file_path: Relative path of fixed file
            content: Fixed file content

        Returns:
            True (fix is already on EC2 sandbox via _write_file)
        """
        # =================================================================
        # VALIDATION: file_path should already be normalized by caller
        # =================================================================
        if not file_path or not file_path.strip():
            logger.error(f"[BoltFixer:{project_id}] Invalid empty file path")
            return False

        # Basic cleanup only (caller should have normalized)
        file_path = file_path.strip()

        # =================================================================
        # NO S3 UPLOAD DURING FIX
        #
        # Previously, this function uploaded to S3 immediately after each fix.
        # This caused issues because on retry:
        # - S3 restore would fetch from S3 (overwriting EC2 files)
        # - Fixes were lost because EC2 files were replaced
        #
        # NEW FLOW:
        # 1. Fix is written to EC2 sandbox (already done by _write_file)
        # 2. On retry, dir exists on EC2 → skip S3 restore
        # 3. After BUILD SUCCESS → sync EC2 to S3 (in execution.py)
        # =================================================================

        logger.info(f"[BoltFixer:{project_id}] ✓ Fixed on EC2: {file_path} (S3 sync deferred to BUILD SUCCESS)")

        # The file is already written to EC2 sandbox by _write_file()
        # S3 upload will happen after BUILD SUCCESS in execution.py
        return True

    # ==========================================================================
    # ISSUE #9 FIX: Removed dead code _persist_fix_to_storage()
    # This method was never called - all persistence now happens via
    # _persist_single_fix() immediately after each fix.
    # ==========================================================================

    async def fix_from_backend(
        self,
        project_id: str,
        project_path: Path,
        payload: Dict[str, Any],
        sandbox_file_writer: Optional[Callable[[str, str], bool]] = None,
        sandbox_file_reader: Optional[Callable[[str], Optional[str]]] = None,
        sandbox_file_lister: Optional[Callable[[str, str], List[str]]] = None
    ) -> BoltFixResult:
        """
        BOLT.NEW STYLE: Fix errors from backend execution.

        Same interface as SimpleFixer.fix_from_backend for drop-in replacement.

        Args:
            project_id: Project ID
            project_path: Path to project files
            payload: Error payload from ExecutionContext
            sandbox_file_writer: Optional callback to write files directly to sandbox.
                                 Signature: (file_path: str, content: str) -> bool
                                 If None, uses local Path.write_text() (only works in local mode)
            sandbox_file_reader: Optional callback to read files from sandbox.
                                 Signature: (file_path: str) -> Optional[str]
                                 If None, uses local Path.read_text() (only works in local mode)
            sandbox_file_lister: Optional callback to list files matching a pattern from sandbox.
                                 Signature: (directory: str, pattern: str) -> List[str]
                                 If None, uses local glob (only works in local mode)

        Returns:
            BoltFixResult with success status and modified files
        """
        # Store the sandbox callbacks for use in file operations
        self._sandbox_file_writer = sandbox_file_writer
        self._sandbox_file_reader = sandbox_file_reader
        self._sandbox_file_lister = sandbox_file_lister
        # Extract payload
        stderr = payload.get("stderr", "")
        stdout = payload.get("stdout", "")
        exit_code = payload.get("exit_code", 1)
        error_file = payload.get("error_file")
        error_line = payload.get("error_line")
        primary_error_type = payload.get("primary_error_type")

        # Combine stdout and stderr for classification
        # Vite/esbuild errors often go to stdout, not stderr
        combined_output = f"{stderr}\n{stdout}".strip() if stderr or stdout else ""

        logger.info(
            f"[BoltFixer:{project_id}] fix_from_backend: "
            f"exit_code={exit_code}, stderr_len={len(stderr)}, stdout_len={len(stdout)}"
        )

        # =================================================================
        # STEP 1: CLASSIFY ERROR (Rule-based, NO AI)
        # =================================================================
        classified = ErrorClassifier.classify(
            error_message=combined_output[:2000],
            stderr=combined_output,
            exit_code=exit_code
        )

        logger.info(
            f"[BoltFixer:{project_id}] Classified: {classified.error_type.value}, "
            f"fixable={classified.is_claude_fixable}, confidence={classified.confidence}"
        )

        # =================================================================
        # STEP 2: DECISION GATE - Should Claude be called?
        # =================================================================
        should_call, reason = ErrorClassifier.should_call_claude(classified)
        if not should_call:
            logger.info(f"[BoltFixer:{project_id}] NOT calling Claude: {reason}")
            return BoltFixResult(
                success=False,
                files_modified=[],
                message=reason,
                error_type=classified.error_type.value,
                fix_strategy="skipped"
            )

        # =================================================================
        # STEP 3: CHECK RETRY LIMITS
        # =================================================================
        error_hash = retry_limiter.hash_error(combined_output[:500])
        can_retry, retry_reason = retry_limiter.can_retry(project_id, error_hash)
        if not can_retry:
            logger.warning(f"[BoltFixer:{project_id}] Retry limit: {retry_reason}")
            return BoltFixResult(
                success=False,
                files_modified=[],
                message=retry_reason,
                error_type=classified.error_type.value,
                fix_strategy="retry_blocked"
            )

        # =================================================================
        # STEP 3a: TRY DETERMINISTIC FIXES FIRST (fast, free, no AI cost)
        # =================================================================
        # Docker base image fixes (openjdk:17-jdk-slim -> eclipse-temurin:17-jdk-alpine)
        dockerfile_fix_result = await self._try_deterministic_dockerfile_fix(
            project_id=project_id,
            project_path=project_path,
            error_output=combined_output
        )
        if dockerfile_fix_result:
            logger.info(f"[BoltFixer:{project_id}] Deterministic Dockerfile fix applied - skipping AI")
            retry_limiter.record_attempt(project_id, error_hash, tokens_used=0, fixed=True)
            return dockerfile_fix_result

        # =================================================================
        # STEP 4: GATHER CONTEXT (file content for Claude)
        # =================================================================
        file_content = ""
        related_files_content = ""
        all_error_files_content = ""
        target_file = classified.file_path or error_file
        self._current_project_id = project_id

        # =================================================================
        # STEP 4a: Extract ALL error files with DEPENDENCY-AWARE SELECTION
        # =================================================================
        all_error_files = ErrorClassifier.extract_all_error_files(combined_output)
        total_error_count = len(all_error_files)
        logger.info(f"[BoltFixer:{project_id}] Found {total_error_count} files with errors: {[f[0] for f in all_error_files]}")

        # OPTIMIZATION: Only build dependency graph for multi-file errors
        # Single file errors don't need graph - just fix the file directly
        if total_error_count <= 1:
            logger.info(f"[BoltFixer:{project_id}] Single file error - skipping dependency graph")

        if total_error_count > 1:
            # BUILD DEPENDENCY GRAPH (only for multi-file errors)
            try:
                self._dependency_graph = build_dependency_graph(
                    project_path,
                    file_reader=self._sandbox_file_reader,
                    file_lister=self._sandbox_file_lister
                )
                graph_stats = self._dependency_graph.get_stats()
                logger.info(f"[BoltFixer:{project_id}] Dependency graph: {graph_stats}")
            except Exception as e:
                logger.warning(f"[BoltFixer:{project_id}] Could not build dependency graph: {e}")
                self._dependency_graph = None

            # USE DEPENDENCY GRAPH for smarter prioritization
            if self._dependency_graph:
                # Get fix order from dependency graph
                all_error_files = self._dependency_graph.get_fix_order(all_error_files)
                logger.info(f"[BoltFixer:{project_id}] Dependency-ordered files: {[f[0].split('/')[-1] for f in all_error_files[:6]]}")
            else:
                # Fallback to rule-based prioritization
                all_error_files = self._prioritize_error_files(all_error_files, combined_output)

            # USE BATCH TRACKER for multi-pass fixing
            batch_files, current_pass = batch_tracker.get_next_batch(
                project_id, all_error_files, MAX_FILES_PER_BATCH
            )

            if not batch_files:
                logger.info(f"[BoltFixer:{project_id}] No more batches to process")
                return BoltFixResult(
                    success=False,
                    files_modified=[],
                    message="All batches attempted",
                    error_type=classified.error_type.value,
                    fix_strategy="batch_exhausted",
                    current_pass=current_pass
                )

            # Check if batch can be attempted
            can_attempt, batch_reason = batch_tracker.can_attempt_batch(
                project_id, [f for f, _ in batch_files]
            )
            if not can_attempt:
                logger.warning(f"[BoltFixer:{project_id}] Batch blocked: {batch_reason}")
                return BoltFixResult(
                    success=False,
                    files_modified=[],
                    message=batch_reason,
                    error_type=classified.error_type.value,
                    fix_strategy="batch_blocked",
                    current_pass=current_pass
                )

            all_error_files = batch_files
            logger.info(f"[BoltFixer:{project_id}] Pass {current_pass}: Processing batch of {len(batch_files)} files")

            # READ with smart truncation and context limit tracking
            error_files_sections = []
            total_chars = 0

            for err_file, err_line in all_error_files:
                content = await self._read_file_content(project_path, err_file)
                if not content:
                    continue

                # SMART TRUNCATE: Keep relevant context around error
                if len(content) > CHARS_PER_FILE_LIMIT:
                    content = self._smart_truncate(content, err_line, CHARS_PER_FILE_LIMIT)

                # CHECK CONTEXT LIMIT: Stop if we're approaching max
                if total_chars + len(content) > MAX_CONTEXT_CHARS:
                    logger.warning(f"[BoltFixer:{project_id}] Context limit reached at {total_chars} chars, included {len(error_files_sections)} files")
                    break

                # Dynamic syntax highlighting based on file extension
                syntax = get_syntax_highlight(err_file)
                error_files_sections.append(f"""
--- ERROR FILE: {err_file} (line {err_line}) ---
```{syntax}
{content}
```
""")
                total_chars += len(content)

            if error_files_sections:
                all_error_files_content = "\n".join(error_files_sections)
                logger.info(f"[BoltFixer:{project_id}] Batch fixing {len(error_files_sections)}/{total_error_count} files ({total_chars} chars)")

        if target_file and project_path:
            # Try different paths to find the file
            possible_paths = [
                project_path / target_file,
                project_path / "frontend" / target_file,
                project_path / "backend" / target_file,
            ]

            for file_path in possible_paths:
                try:
                    # Use sandbox_file_reader for remote mode, local read for local mode
                    if self._sandbox_file_reader:
                        content = self._sandbox_file_reader(str(file_path))
                        if content:
                            file_content = content
                            logger.info(f"[BoltFixer:{project_id}] Read file via sandbox: {file_path} ({len(file_content)} chars)")
                            break
                    elif file_path.exists():
                        file_content = file_path.read_text(encoding='utf-8')
                        logger.info(f"[BoltFixer:{project_id}] Read file locally: {file_path} ({len(file_content)} chars)")
                        break
                except Exception as e:
                    logger.debug(f"[BoltFixer:{project_id}] Could not read {file_path}: {e}")
                    continue

            if not file_content:
                logger.warning(f"[BoltFixer:{project_id}] Could not read target file from any path: {target_file}")

        # For all languages, read related files mentioned in the error
        if target_file:
            related_files_content = await self._read_related_files(
                project_path, combined_output, target_file
            )

        # =================================================================
        # STEP 5: CALL CLAUDE (strict prompt)
        # =================================================================
        # Choose prompt based on error type
        if classified.error_type == ErrorType.SYNTAX_ERROR:
            system_prompt = self.SYNTAX_FIX_PROMPT
            max_tokens = 16384
        else:
            system_prompt = self.SYSTEM_PROMPT
            # Increase max_tokens for batch fixing (multiple files)
            max_tokens = 16384 if len(all_error_files) > 1 else 4096

        # Build user prompt
        error_type_template = ErrorClassifier.get_claude_prompt_template(classified.error_type)

        # Include related files section if available
        related_section = ""
        if related_files_content:
            related_section = f"""
RELATED FILES (may need modification):
{related_files_content}
"""

        # Include all error files section for batch fixing
        all_errors_section = ""
        if all_error_files_content:
            all_errors_section = f"""
=== ALL FILES WITH ERRORS (FIX ALL OF THEM) ===
{all_error_files_content}
=== END OF ERROR FILES ===

IMPORTANT: The above files ALL have errors. Output a <file> or <patch> block for EACH one.
"""

        user_prompt = f"""{error_type_template}

ERROR: {combined_output[:2000]}
FILE: {target_file or 'unknown'}
LINE: {classified.line_number or error_line or 0}

FILE CONTENT:
```
{file_content[:10000] if file_content else 'No file content available'}
```
{all_errors_section}{related_section}
BUILD LOG:
{combined_output[-2000:]}
"""

        logger.info(f"[BoltFixer:{project_id}] Calling Claude for {classified.error_type.value}")

        try:
            response = await self._call_claude(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens
            )
        except Exception as e:
            logger.error(f"[BoltFixer:{project_id}] Claude call failed: {e}")
            retry_limiter.record_attempt(project_id, error_hash, tokens_used=0, fixed=False)
            return BoltFixResult(
                success=False,
                files_modified=[],
                message=f"Claude API error: {str(e)}",
                error_type=classified.error_type.value,
                fix_strategy="claude_error"
            )

        # Estimate tokens
        tokens_used = len(user_prompt.split()) + len(response.split())

        # =================================================================
        # STEP 6: PARSE RESPONSE
        # =================================================================
        patches = self._parse_patch_blocks(response)
        full_files = self._parse_file_blocks(response)
        new_files = self._parse_newfile_blocks(response)

        logger.info(
            f"[BoltFixer:{project_id}] Claude returned: "
            f"{len(patches)} patches, {len(full_files)} files, {len(new_files)} new files"
        )

        if not patches and not full_files and not new_files:
            logger.warning(f"[BoltFixer:{project_id}] No fixes in Claude response")
            retry_limiter.record_attempt(project_id, error_hash, tokens_used=tokens_used, fixed=False)
            return BoltFixResult(
                success=False,
                files_modified=[],
                message="Claude returned no fixes",
                error_type=classified.error_type.value,
                fix_strategy="no_fix"
            )

        # =================================================================
        # STEP 7: VALIDATE AND APPLY
        # =================================================================
        files_modified = []
        applier = PatchApplier(project_path)

        # Apply patches using DiffParser
        for patch in patches:
            patch_content = patch.get("patch", "")
            file_path = patch.get("path", "")

            # Validate patch structure
            result = PatchValidator.validate_diff(patch_content, project_path)
            if not result.is_valid:
                logger.warning(f"[BoltFixer:{project_id}] Invalid patch: {result.errors}")
                continue

            # Find target file from DiffParser
            parsed = DiffParser.parse(patch_content)
            actual_file = parsed.new_file or parsed.old_file or file_path

            # =================================================================
            # FIX: Validate DiffParser output for path traversal
            # =================================================================
            if not actual_file or '..' in actual_file:
                logger.warning(f"[BoltFixer:{project_id}] Invalid/dangerous patch path: {actual_file}")
                continue

            # =================================================================
            # FIX: Use centralized path normalization for patches
            # =================================================================
            normalized_path, is_valid = self._normalize_file_path(actual_file)
            if not is_valid:
                logger.warning(f"[BoltFixer:{project_id}] Skipping patch with invalid path: {actual_file}")
                continue

            # Build target path from normalized path
            target_path = project_path / normalized_path

            # Try to read original file content
            original = None
            try:
                if self._sandbox_file_reader:
                    original = self._sandbox_file_reader(str(target_path))
                elif target_path.exists():
                    original = target_path.read_text(encoding='utf-8')
            except Exception as read_err:
                logger.warning(f"[BoltFixer:{project_id}] Could not read {normalized_path}: {read_err}")

            if original and target_path:
                try:
                    apply_result = DiffParser.apply(original, parsed)

                    # FIX #4: Safely check apply_result attributes (could be None)
                    if not apply_result or not hasattr(apply_result, 'success'):
                        logger.warning(f"[BoltFixer:{project_id}] DiffParser returned invalid result for {normalized_path}")
                        continue

                    # FIX #4: Safe content check - handle None case
                    new_content = getattr(apply_result, 'new_content', None)
                    has_content = new_content and isinstance(new_content, str) and new_content.strip()

                    if apply_result.success and has_content:
                        # Use sandbox-aware file writer
                        if self._write_file(target_path, new_content, project_id):
                            # IMMEDIATELY persist to S3/database (survives restore)
                            if await self._persist_single_fix(project_id, project_path, normalized_path, new_content):
                                files_modified.append(normalized_path)
                                logger.info(f"[BoltFixer:{project_id}] Applied & persisted patch: {normalized_path}")
                            else:
                                logger.warning(f"[BoltFixer:{project_id}] Patch applied but persistence failed: {normalized_path}")
                        else:
                            # FIX #5: Log write failure (was silent before)
                            logger.error(f"[BoltFixer:{project_id}] Failed to write patch to {normalized_path}")
                    elif apply_result.success:
                        # FIX #9: Track silent failures explicitly
                        logger.warning(f"[BoltFixer:{project_id}] Patch resulted in empty content: {normalized_path}")
                    else:
                        logger.warning(f"[BoltFixer:{project_id}] Patch application failed for {normalized_path}")
                except Exception as e:
                    logger.error(f"[BoltFixer:{project_id}] Error applying patch to {normalized_path}: {e}")

        # Apply full file replacements
        for file_info in full_files:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")

            # =================================================================
            # ISSUE #3 & #4 FIX: Use centralized path normalization
            # =================================================================
            normalized_path, is_valid = self._normalize_file_path(file_path)
            if not is_valid:
                logger.warning(f"[BoltFixer:{project_id}] Skipping file with invalid path: {file_path}")
                continue

            # =================================================================
            # ISSUE #7 FIX: Validate content not empty
            # =================================================================
            if not content or not content.strip():
                logger.warning(f"[BoltFixer:{project_id}] Skipping file with empty content: {normalized_path}")
                continue

            # PROTECTION: Block full docker-compose.yml replacement
            # AI has been known to corrupt docker-compose.yml by deleting services
            if "docker-compose" in normalized_path.lower():
                logger.warning(
                    f"[BoltFixer:{project_id}] BLOCKING full docker-compose.yml replacement - "
                    "AI must use patches, not full file replacement"
                )
                continue

            # Validate
            result = PatchValidator.validate_full_file(normalized_path, content, project_path)
            if not result.is_valid:
                logger.warning(f"[BoltFixer:{project_id}] Invalid file: {result.errors}")
                continue

            # Build target path from normalized path
            target_path = project_path / normalized_path

            # Use sandbox-aware file writer
            if self._write_file(target_path, content, project_id):
                # IMMEDIATELY persist to S3/database (survives restore)
                # FIX: Check return value of _persist_single_fix()
                if await self._persist_single_fix(project_id, project_path, normalized_path, content):
                    files_modified.append(normalized_path)
                    logger.info(f"[BoltFixer:{project_id}] Wrote & persisted full file: {normalized_path}")
                else:
                    logger.warning(f"[BoltFixer:{project_id}] File written but persistence failed: {normalized_path}")

        # Create new files
        for file_info in new_files:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")

            # =================================================================
            # ISSUE #3 & #4 FIX: Use centralized path normalization
            # =================================================================
            normalized_path, is_valid = self._normalize_file_path(file_path)
            if not is_valid:
                logger.warning(f"[BoltFixer:{project_id}] Skipping new file with invalid path: {file_path}")
                continue

            # =================================================================
            # ISSUE #7 FIX: Validate content not empty
            # =================================================================
            if not content or not content.strip():
                logger.warning(f"[BoltFixer:{project_id}] Skipping new file with empty content: {normalized_path}")
                continue

            # PROTECTION: Don't create new docker-compose.yml if one already exists
            if "docker-compose" in normalized_path.lower():
                existing_compose = project_path / "docker-compose.yml"
                # Check existence using sandbox reader or local check
                exists = False
                if self._sandbox_file_reader:
                    exists = self._sandbox_file_reader(str(existing_compose)) is not None
                else:
                    exists = existing_compose.exists()

                if exists:
                    logger.warning(
                        f"[BoltFixer:{project_id}] BLOCKING creation of new docker-compose.yml - "
                        "original already exists"
                    )
                    continue

            # Validate
            result = PatchValidator.validate_new_file(normalized_path, content, project_path)
            if not result.is_valid:
                logger.warning(f"[BoltFixer:{project_id}] Invalid new file: {result.errors}")
                continue

            # Build target path from normalized path
            target_path = project_path / normalized_path

            # Use sandbox-aware file writer
            if self._write_file(target_path, content, project_id):
                # IMMEDIATELY persist to S3/database (survives restore)
                # FIX: Check return value of _persist_single_fix()
                if await self._persist_single_fix(project_id, project_path, normalized_path, content):
                    files_modified.append(normalized_path)
                    logger.info(f"[BoltFixer:{project_id}] Created & persisted new file: {normalized_path}")
                else:
                    logger.warning(f"[BoltFixer:{project_id}] New file created but persistence failed: {normalized_path}")

        # =================================================================
        # STEP 8: PERSISTENCE NOW HAPPENS IMMEDIATELY (above)
        # Each fix is persisted to S3/database right after it's applied.
        # This ensures fixes survive "restore from database" on retry.
        # Benefits:
        # - No fix is ever lost, even if build fails for another reason
        # - Retry doesn't re-fix the same files (efficient)
        # - If a fix is wrong, next fix attempt will overwrite it
        # =================================================================

        # =================================================================
        # STEP 9: RECORD BATCH ATTEMPT AND RETURN
        # =================================================================
        success = len(files_modified) > 0
        # Never mark as "fixed" - we can't know if fix is complete from here
        # MAX_RETRIES_PER_ERROR (3) prevents infinite loops
        # Container health check determines if truly fixed (container starts successfully)
        retry_limiter.record_attempt(project_id, error_hash, tokens_used=tokens_used, fixed=False)

        # Record batch attempt for multi-pass tracking
        current_pass = 1
        remaining_errors = total_error_count - len(files_modified)
        needs_another_pass = remaining_errors > 0 and success

        if total_error_count > 1:
            batch_tracker.record_batch_attempt(
                project_id=project_id,
                files=[f for f, _ in all_error_files],
                success=success,
                files_fixed=files_modified,
                error_count_before=total_error_count,
                error_count_after=remaining_errors
            )
            progress = batch_tracker.get_fix_progress(project_id)
            current_pass = progress.get("current_pass", 1)
            logger.info(
                f"[BoltFixer:{project_id}] Batch complete: "
                f"pass={current_pass}, fixed={len(files_modified)}, remaining={remaining_errors}"
            )

        return BoltFixResult(
            success=success,
            files_modified=files_modified,
            message=f"Pass {current_pass}: Fixed {len(files_modified)} file(s)" if success else "No files fixed",
            patches_applied=len(files_modified),
            error_type=classified.error_type.value,
            fix_strategy="bolt_fixer",
            current_pass=current_pass,
            remaining_errors=remaining_errors,
            needs_another_pass=needs_another_pass
        )

    async def _call_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096
    ) -> str:
        """Call Claude API with strict prompts."""
        import anthropic

        if self._claude_client is None:
            from app.core.config import settings
            self._claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = self._claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            temperature=0.1,  # Very low for precise fixes
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        return response.content[0].text if response.content else ""

    def _parse_patch_blocks(self, response: str) -> List[Dict[str, str]]:
        """Parse <patch>...</patch> blocks."""
        import re
        patches = []
        pattern = r'<patch>(.*?)</patch>'

        for match in re.findall(pattern, response, re.DOTALL):
            content = match.strip()

            # FIX #12: Empty patch is Claude's "no fix possible" signal - log it
            if not content:
                logger.debug("[BoltFixer] Empty <patch> block - Claude indicates no fix possible")
                continue

            # FIX #2: Safely extract file path with bounds checking
            path_match = re.search(r'^(?:---|\+\+\+)\s+(?:[ab]/)?([^\s]+)', content, re.MULTILINE)
            try:
                file_path = path_match.group(1) if path_match and path_match.lastindex >= 1 else None
            except (IndexError, AttributeError):
                file_path = None

            # FIX #11: Validate path before adding
            if not file_path or not file_path.strip():
                logger.warning("[BoltFixer] Patch has no valid file path - skipping")
                continue

            patches.append({"path": file_path.strip(), "patch": content})

        return patches

    def _parse_file_blocks(self, response: str) -> List[Dict[str, str]]:
        """Parse <file path="...">...</file> blocks."""
        import re
        files = []
        pattern = r'<file\s+path="([^"]+)">(.*?)</file>'

        for path, content in re.findall(pattern, response, re.DOTALL):
            # FIX #11: Validate path and content before adding
            path = path.strip() if path else ""
            content = content.strip() if content else ""
            if not path:
                logger.warning("[BoltFixer] <file> block has empty path - skipping")
                continue
            if not content:
                logger.warning(f"[BoltFixer] <file> block for {path} has empty content - skipping")
                continue
            files.append({"path": path, "content": content})

        return files

    def _parse_newfile_blocks(self, response: str) -> List[Dict[str, str]]:
        """Parse <newfile path="...">...</newfile> blocks."""
        import re
        files = []
        pattern = r'<newfile\s+path="([^"]+)">(.*?)</newfile>'

        for path, content in re.findall(pattern, response, re.DOTALL):
            # FIX #11: Validate path
            path = path.strip() if path else ""
            if not path:
                logger.warning("[BoltFixer] <newfile> block has empty path - skipping")
                continue

            # Clean markdown if present
            content = content.strip() if content else ""
            if content.startswith('```'):
                lines = content.split('\n')[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                content = '\n'.join(lines)

            # FIX #7: Validate content not empty after markdown stripping
            content = content.strip()
            if not content:
                logger.warning(f"[BoltFixer] <newfile> block for {path} has empty content after markdown strip - skipping")
                continue

            files.append({"path": path, "content": content})

        return files

    def _prioritize_error_files(
        self,
        error_files: List[Tuple[str, int]],
        error_output: str
    ) -> List[Tuple[str, int]]:
        """
        Prioritize files by error severity - fix ROOT CAUSE files first.

        Priority order:
        1. DTO/Entity files (often the root cause of "cannot find symbol")
        2. Files with most error mentions
        3. Service/Repository interfaces
        4. Other files

        Returns:
            Sorted list of (file_path, line_num) by priority
        """
        scored_files = []

        for file_path, line_num in error_files:
            score = 0
            file_name = Path(file_path).stem

            # Count how many times this file appears in errors
            error_count = error_output.lower().count(file_name.lower())
            score += error_count * 10

            # HIGH PRIORITY: DTO/Entity files (often root cause)
            if 'Dto' in file_name or 'DTO' in file_name:
                score += 100
            if 'Entity' in file_name or file_name[0].isupper() and len(file_name) < 20:
                # Short capitalized names are often entity classes
                score += 80

            # MEDIUM PRIORITY: Service interfaces (dependencies)
            if 'Service' in file_name and 'Impl' not in file_name:
                score += 60  # Interface before implementation
            if 'Repository' in file_name:
                score += 50

            # LOWER PRIORITY: Implementation files
            if 'ServiceImpl' in file_name or 'Impl' in file_name:
                score += 30
            if 'Controller' in file_name:
                score += 20

            # Boost if "cannot find symbol" mentions this class
            if f"class {file_name}" in error_output or f"symbol: class {file_name}" in error_output:
                score += 70

            # Boost if error location is IN this file
            if f"{file_path}:" in error_output or f"{file_name}.java:" in error_output:
                score += 40

            scored_files.append((file_path, line_num, score))

        # Sort by score (highest first)
        scored_files.sort(key=lambda x: x[2], reverse=True)

        # Log prioritization for debugging
        logger.info(f"[BoltFixer] File priority: {[(f[0].split('/')[-1], f[2]) for f in scored_files[:5]]}")

        # Return without score
        return [(f[0], f[1]) for f in scored_files]

    def _smart_truncate(
        self,
        content: str,
        error_line: int,
        max_chars: int = CHARS_PER_FILE_LIMIT
    ) -> str:
        """
        Truncate file content intelligently, keeping:
        1. Package/import declarations (top)
        2. Context around error line
        3. Class closing braces (bottom)

        Args:
            content: Full file content
            error_line: Line number where error occurred
            max_chars: Maximum characters to return

        Returns:
            Truncated content with markers
        """
        if len(content) <= max_chars:
            return content

        lines = content.split('\n')
        total_lines = len(lines)

        if error_line <= 0:
            error_line = total_lines // 2  # Default to middle

        # Sections to include
        result_sections = []
        chars_used = 0

        # SECTION 1: Keep first 15 lines (package, imports, class declaration)
        header_lines = min(15, total_lines)
        header = '\n'.join(lines[:header_lines])
        result_sections.append(header)
        chars_used += len(header)

        # SECTION 2: Context around error line
        context_lines = CONTEXT_LINES_AROUND_ERROR
        remaining_chars = max_chars - chars_used - 500  # Reserve for footer

        # Adjust context based on remaining space
        while context_lines > 10:
            start = max(header_lines, error_line - context_lines)
            end = min(total_lines - 5, error_line + context_lines)
            context = '\n'.join(lines[start:end])

            if len(context) <= remaining_chars:
                break
            context_lines -= 10

        start = max(header_lines, error_line - context_lines)
        end = min(total_lines - 5, error_line + context_lines)

        if start > header_lines:
            result_sections.append(f"\n// ... [TRUNCATED lines {header_lines + 1}-{start}] ...\n")

        result_sections.append('\n'.join(lines[start:end]))

        # SECTION 3: Keep last 5 lines (closing braces)
        if end < total_lines - 5:
            result_sections.append(f"\n// ... [TRUNCATED lines {end + 1}-{total_lines - 5}] ...\n")

        result_sections.append('\n'.join(lines[-5:]))

        truncated = '\n'.join(result_sections)
        logger.debug(f"[BoltFixer] Truncated file from {len(content)} to {len(truncated)} chars")

        return truncated

    # ==========================================================================
    # REMOVED: _sync_to_s3() - Dead code, never called
    # All persistence now happens via _persist_single_fix() immediately
    # ==========================================================================

    async def _read_related_files(
        self,
        project_path: Path,
        error_output: str,
        current_file: str
    ) -> str:
        """
        Extract and read related files mentioned in compilation/build errors.

        SUPPORTS ALL LANGUAGES: Java, Python, TypeScript, JavaScript, Go, Rust, C#, Ruby, PHP.

        IMPORTANT: This method identifies ROOT CAUSE files, not just mentioned files.
        For errors like "cannot find symbol: method getPrice() in class Product",
        we need to read Product.java because THAT is where the fix should be applied.

        Works with both local and remote sandbox by using the sandbox callbacks.

        Args:
            project_path: Root path of the project
            error_output: Full error output from compilation/build
            current_file: The file already being read (to avoid duplicates)

        Returns:
            Formatted string with related file contents, marking ROOT CAUSE files
        """
        import glob

        # Detect language from current file
        language = detect_language(current_file)
        keywords = get_language_keywords(current_file)

        # Get current file's module/class name to exclude
        current_name = Path(current_file).stem if current_file else None
        project_str = str(project_path)

        # =====================================================================
        # STEP 1: Extract ROOT CAUSE modules/classes from error patterns
        # Language-specific patterns for identifying files that need fixes
        # =====================================================================
        root_cause_names: Set[str] = set()

        # ----- JAVA PATTERNS -----
        if language in ('java', 'kotlin', 'scala'):
            # Pattern: "cannot find symbol...in class X"
            for match in re.finditer(r'cannot find symbol.*?(?:class|interface)\s+(\w+)', error_output, re.IGNORECASE):
                root_cause_names.add(match.group(1))

            # Pattern: "location: variable xxx of type com.package.ClassName"
            for match in re.finditer(r'location:\s*variable\s+\w+\s+of\s+type\s+(?:@[\w.]+\s+)?(?:[\w.]+\.)?(\w+)', error_output, re.IGNORECASE):
                root_cause_names.add(match.group(1))

            # Pattern: "type com.package.ClassName"
            for match in re.finditer(r'\btype\s+(?:[\w.]+\.)?(\w+)(?:\s|$|,)', error_output):
                cls = match.group(1)
                if cls and len(cls) > 0 and cls[0].isupper() and cls not in keywords:
                    root_cause_names.add(cls)

            # Pattern: "no suitable constructor found for X(...)"
            for match in re.finditer(r'no suitable (?:constructor|method).*?for\s+(\w+)', error_output, re.IGNORECASE):
                cls = match.group(1)
                if cls and cls not in keywords:
                    root_cause_names.add(cls)

            # Pattern: "incompatible types...cannot be converted to X"
            for match in re.finditer(r'(?:cannot be converted to|found:\s*)(\w+)', error_output, re.IGNORECASE):
                cls = match.group(1)
                if cls and len(cls) > 0 and cls[0].isupper() and cls not in keywords:
                    root_cause_names.add(cls)

        # ----- PYTHON PATTERNS -----
        elif language == 'python':
            # Pattern: "ImportError: cannot import name 'X' from 'module'"
            for match in re.finditer(r"cannot import name '(\w+)'", error_output):
                root_cause_names.add(match.group(1))

            # Pattern: "ModuleNotFoundError: No module named 'x'"
            for match in re.finditer(r"No module named '([\w.]+)'", error_output):
                module = match.group(1).split('.')[-1]
                root_cause_names.add(module)

            # Pattern: "AttributeError: 'X' object has no attribute 'y'"
            for match in re.finditer(r"'(\w+)' object has no attribute", error_output):
                root_cause_names.add(match.group(1))

            # Pattern: "NameError: name 'X' is not defined"
            for match in re.finditer(r"name '(\w+)' is not defined", error_output):
                name = match.group(1)
                if name and name not in keywords:
                    root_cause_names.add(name)

            # Pattern: "TypeError: X() missing required argument"
            for match in re.finditer(r"TypeError:\s+(\w+)\(\)", error_output):
                root_cause_names.add(match.group(1))

        # ----- TYPESCRIPT/JAVASCRIPT PATTERNS -----
        elif language in ('typescript', 'javascript'):
            # Pattern: "Property 'x' does not exist on type 'Y'"
            for match in re.finditer(r"does not exist on type '(\w+)'", error_output):
                root_cause_names.add(match.group(1))

            # Pattern: "Cannot find module 'x'"
            for match in re.finditer(r"Cannot find module '([^']+)'", error_output):
                module = match.group(1).split('/')[-1].replace('.js', '').replace('.ts', '')
                if module and module not in keywords:
                    root_cause_names.add(module)

            # Pattern: "Module 'x' has no exported member 'Y'"
            for match in re.finditer(r"has no exported member '(\w+)'", error_output):
                root_cause_names.add(match.group(1))

            # Pattern: "Type 'X' is not assignable to type 'Y'"
            for match in re.finditer(r"Type '(\w+)' is not assignable", error_output):
                t = match.group(1)
                if t and t not in keywords:
                    root_cause_names.add(t)

            # Pattern: "'X' is not a valid JSX element"
            for match in re.finditer(r"'(\w+)' is not a valid JSX element", error_output):
                root_cause_names.add(match.group(1))

        # ----- GO PATTERNS -----
        elif language == 'go':
            # Pattern: "undefined: X"
            for match in re.finditer(r'undefined:\s+(\w+)', error_output):
                name = match.group(1)
                if name and name not in keywords:
                    root_cause_names.add(name)

            # Pattern: "cannot find package 'x'"
            for match in re.finditer(r"cannot find package \"([^\"]+)\"", error_output):
                pkg = match.group(1).split('/')[-1]
                root_cause_names.add(pkg)

            # Pattern: "X.Y undefined (type X has no field or method Y)"
            for match in re.finditer(r'(\w+)\.\w+ undefined.*type (\w+) has no', error_output):
                root_cause_names.add(match.group(2))

        # ----- RUST PATTERNS -----
        elif language == 'rust':
            # Pattern: "cannot find value `x` in this scope"
            for match in re.finditer(r'cannot find (?:value|type|function|struct|trait) `(\w+)`', error_output):
                name = match.group(1)
                if name and name not in keywords:
                    root_cause_names.add(name)

            # Pattern: "unresolved import `x`"
            for match in re.finditer(r'unresolved import `(\w+)`', error_output):
                root_cause_names.add(match.group(1))

            # Pattern: "no method named `x` found for struct `Y`"
            for match in re.finditer(r'no method named `\w+` found for (?:struct|type) `(\w+)`', error_output):
                root_cause_names.add(match.group(1))

        # ----- C# PATTERNS -----
        elif language == 'csharp':
            # Pattern: "The type or namespace name 'X' could not be found"
            for match in re.finditer(r"type or namespace name '(\w+)'.*could not be found", error_output, re.IGNORECASE):
                root_cause_names.add(match.group(1))

            # Pattern: "'X' does not contain a definition for 'Y'"
            for match in re.finditer(r"'(\w+)' does not contain a definition for", error_output):
                root_cause_names.add(match.group(1))

        # ----- GENERIC PATTERNS (all languages) -----
        # Pattern: File paths in error messages (e.g., "Error in user_service.py")
        for match in re.finditer(r'[/\\]?([\w-]+)\.(py|ts|tsx|js|jsx|java|go|rs|cs|rb|php)(?::\d+)?', error_output):
            name = match.group(1)
            if name and name != current_name:
                root_cause_names.add(name)

        # =====================================================================
        # STEP 1b: Add RELATED files by naming pattern (language-aware)
        # =====================================================================
        if current_name:
            patterns = RELATED_FILE_PATTERNS.get(language, {})
            suffixes = patterns.get('suffixes', [])

            # Extract base entity name
            entity_name = None
            for suffix in suffixes:
                if current_name.endswith(suffix):
                    entity_name = current_name[:-len(suffix)]
                    break
                if current_name.lower().endswith(suffix.lower()):
                    # Handle case variations
                    entity_name = current_name[:-len(suffix)]
                    break

            if entity_name:
                # Add all related name patterns
                for suffix in suffixes:
                    related_name = f"{entity_name}{suffix}"
                    if related_name != current_name:
                        root_cause_names.add(related_name)
                # Also add the base entity
                root_cause_names.add(entity_name)
                logger.info(f"[BoltFixer] Added related files for entity '{entity_name}'")

        # Filter out keywords
        root_cause_names = {n for n in root_cause_names if n not in keywords}
        logger.info(f"[BoltFixer] Identified root cause names ({language}): {root_cause_names}")

        # =====================================================================
        # STEP 2: Find source files - use sandbox_file_lister if available
        # =====================================================================
        patterns = RELATED_FILE_PATTERNS.get(language, {})
        extensions = patterns.get('extensions', [])

        # Default extensions if language not configured
        if not extensions:
            ext = Path(current_file).suffix if current_file else ''
            extensions = [ext] if ext else ['.py', '.js', '.ts', '.java', '.go', '.rs']

        all_source_files = []
        for ext in extensions:
            pattern = f"*{ext}"
            if self._sandbox_file_lister:
                try:
                    files = self._sandbox_file_lister(project_str, pattern)
                    all_source_files.extend(files)
                except Exception as e:
                    logger.warning(f"[BoltFixer] Sandbox file listing failed for {pattern}: {e}")
            else:
                all_source_files.extend(glob.glob(f"{project_str}/**/{pattern}", recursive=True))

        logger.info(f"[BoltFixer] Found {len(all_source_files)} source files with extensions {extensions}")

        # =====================================================================
        # STEP 3: Read files - prioritize ROOT CAUSE files
        # =====================================================================
        MAX_RELATED_FILES = 8
        related_contents = []
        files_found = 0

        # First pass: Read ROOT CAUSE files
        for source_file in all_source_files:
            if files_found >= MAX_RELATED_FILES:
                break

            file_name = Path(source_file).stem

            if file_name == current_name:
                continue

            if file_name in root_cause_names or file_name.lower() in {n.lower() for n in root_cause_names}:
                content = self._read_source_file(source_file, project_path)
                if content:
                    syntax = get_syntax_highlight(source_file)
                    related_contents.append(f"""
--- {content['path']} --- [ROOT CAUSE - FIX THIS FILE]
```{syntax}
{content['content'][:8000]}
```
""")
                    files_found += 1
                    logger.info(f"[BoltFixer] Read ROOT CAUSE file: {content['path']}")

        # Second pass: Read other mentioned files (for context)
        for source_file in all_source_files:
            if files_found >= MAX_RELATED_FILES:
                break

            file_name = Path(source_file).stem

            if file_name == current_name:
                continue

            if file_name in root_cause_names or file_name.lower() in {n.lower() for n in root_cause_names}:
                continue  # Already read

            # Check if mentioned in error output
            if re.search(rf'\b{re.escape(file_name)}\b', error_output, re.IGNORECASE):
                content = self._read_source_file(source_file, project_path)
                if content:
                    syntax = get_syntax_highlight(source_file)
                    related_contents.append(f"""
--- {content['path']} --- [CONTEXT]
```{syntax}
{content['content'][:8000]}
```
""")
                    files_found += 1
                    logger.info(f"[BoltFixer] Read context file: {content['path']}")

        if related_contents:
            logger.info(f"[BoltFixer] Found {files_found} related files for {language}")

        return "\n".join(related_contents)

    def _read_source_file(self, file_path: str, project_path: Path) -> Optional[Dict[str, str]]:
        """Helper to read a source file from local or remote sandbox."""
        try:
            if self._sandbox_file_reader:
                content = self._sandbox_file_reader(file_path)
            else:
                content = Path(file_path).read_text(encoding='utf-8')

            if content:
                try:
                    rel_path = Path(file_path).relative_to(project_path)
                except ValueError:
                    rel_path = Path(file_path).name
                return {"path": str(rel_path), "content": content}
        except Exception as e:
            logger.warning(f"[BoltFixer] Could not read {file_path}: {e}")
        return None

    async def _read_file_content(self, project_path: Path, file_path: str) -> Optional[str]:
        """
        Read file content by trying multiple possible paths.

        Args:
            project_path: Root project path
            file_path: Relative file path (may or may not include backend/frontend prefix)

        Returns:
            File content or None if not found
        """
        # Try different path combinations
        possible_paths = [
            project_path / file_path,
            project_path / "frontend" / file_path,
            project_path / "backend" / file_path,
        ]

        # Also try without backend/ prefix if file_path already has it
        if file_path.startswith("backend/"):
            possible_paths.append(project_path / file_path.replace("backend/", ""))

        for path in possible_paths:
            try:
                if self._sandbox_file_reader:
                    content = self._sandbox_file_reader(str(path))
                    if content:
                        return content
                elif path.exists():
                    return path.read_text(encoding='utf-8')
            except Exception as e:
                logger.debug(f"[BoltFixer] Could not read {path}: {e}")
                continue

        return None


# Singleton instance
bolt_fixer = BoltFixer()
