"""
Log Rebuilder Service - Bolt.new Style Log Completion

This service ensures Claude Fixer Agent ALWAYS gets full error context,
even when sandbox logs are truncated or incomplete.

The 3-Layer System:
1. Error Collector - Collects all lines until process exits
2. Log Normalizer - Cleans malformed logs
3. Log Rebuilder - Predicts/completes missing stack lines using templates

Without this, incomplete logs lead to:
- Wrong fixes
- Incomplete patches
- Fix loops
- Wrong file edits
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.core.logging_config import logger


class ErrorType(str, Enum):
    """Detected error types"""
    NODE_MODULE_NOT_FOUND = "node_module_not_found"
    NODE_SYNTAX_ERROR = "node_syntax_error"
    NODE_TYPE_ERROR = "node_type_error"
    NODE_REFERENCE_ERROR = "node_reference_error"
    TYPESCRIPT_ERROR = "typescript_error"
    VITE_BUILD_ERROR = "vite_build_error"
    WEBPACK_ERROR = "webpack_error"
    REACT_ERROR = "react_error"
    NEXTJS_ERROR = "nextjs_error"
    PYTHON_IMPORT_ERROR = "python_import_error"
    PYTHON_SYNTAX_ERROR = "python_syntax_error"
    PYTHON_ATTRIBUTE_ERROR = "python_attribute_error"
    PYTHON_TYPE_ERROR = "python_type_error"
    NPM_ERROR = "npm_error"
    ENOENT_ERROR = "enoent_error"
    PERMISSION_ERROR = "permission_error"
    PORT_IN_USE = "port_in_use"
    GENERIC_ERROR = "generic_error"


@dataclass
class DetectedError:
    """Structured detected error"""
    error_type: ErrorType
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    module: Optional[str] = None
    original_log: str = ""
    rebuilt_log: str = ""
    confidence: float = 0.0


# ============= ERROR DETECTION PATTERNS =============

ERROR_PATTERNS: Dict[ErrorType, List[re.Pattern]] = {
    ErrorType.NODE_MODULE_NOT_FOUND: [
        re.compile(r"Error: Cannot find module ['\"]([^'\"]+)['\"]", re.IGNORECASE),
        re.compile(r"Module not found: Error: Can't resolve ['\"]([^'\"]+)['\"]", re.IGNORECASE),
        re.compile(r"Cannot find module ['\"]([^'\"]+)['\"]", re.IGNORECASE),
    ],
    ErrorType.NODE_SYNTAX_ERROR: [
        re.compile(r"SyntaxError:\s*(.+)", re.IGNORECASE),
        re.compile(r"Unexpected token", re.IGNORECASE),
        re.compile(r"Unexpected identifier", re.IGNORECASE),
    ],
    ErrorType.NODE_TYPE_ERROR: [
        re.compile(r"TypeError:\s*(.+)", re.IGNORECASE),
        re.compile(r"is not a function", re.IGNORECASE),
        re.compile(r"Cannot read propert", re.IGNORECASE),
    ],
    ErrorType.NODE_REFERENCE_ERROR: [
        re.compile(r"ReferenceError:\s*(.+)", re.IGNORECASE),
        re.compile(r"is not defined", re.IGNORECASE),
    ],
    ErrorType.TYPESCRIPT_ERROR: [
        re.compile(r"error TS\d+:\s*(.+)", re.IGNORECASE),
        re.compile(r"Type ['\"]([^'\"]+)['\"] is not assignable", re.IGNORECASE),
        re.compile(r"Property ['\"]([^'\"]+)['\"] does not exist", re.IGNORECASE),
        re.compile(r"Cannot find name ['\"]([^'\"]+)['\"]", re.IGNORECASE),
    ],
    ErrorType.VITE_BUILD_ERROR: [
        re.compile(r"\[vite\].*error", re.IGNORECASE),
        re.compile(r"Pre-transform error", re.IGNORECASE),
        re.compile(r"Failed to resolve import", re.IGNORECASE),
    ],
    ErrorType.WEBPACK_ERROR: [
        re.compile(r"Module build failed", re.IGNORECASE),
        re.compile(r"webpack.*error", re.IGNORECASE),
        re.compile(r"Module parse failed", re.IGNORECASE),
    ],
    ErrorType.REACT_ERROR: [
        re.compile(r"Invalid hook call", re.IGNORECASE),
        re.compile(r"React.*error", re.IGNORECASE),
        re.compile(r"JSX element", re.IGNORECASE),
    ],
    ErrorType.NEXTJS_ERROR: [
        re.compile(r"next.*error", re.IGNORECASE),
        re.compile(r"Failed to compile", re.IGNORECASE),
        re.compile(r"Server Error", re.IGNORECASE),
    ],
    ErrorType.PYTHON_IMPORT_ERROR: [
        re.compile(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]", re.IGNORECASE),
        re.compile(r"ImportError:\s*(.+)", re.IGNORECASE),
        re.compile(r"No module named ['\"]([^'\"]+)['\"]", re.IGNORECASE),
    ],
    ErrorType.PYTHON_SYNTAX_ERROR: [
        re.compile(r"SyntaxError:\s*(.+)", re.IGNORECASE),
        re.compile(r"IndentationError:\s*(.+)", re.IGNORECASE),
    ],
    ErrorType.PYTHON_ATTRIBUTE_ERROR: [
        re.compile(r"AttributeError:\s*(.+)", re.IGNORECASE),
        re.compile(r"has no attribute ['\"]([^'\"]+)['\"]", re.IGNORECASE),
    ],
    ErrorType.PYTHON_TYPE_ERROR: [
        re.compile(r"TypeError:\s*(.+)", re.IGNORECASE),
    ],
    ErrorType.NPM_ERROR: [
        re.compile(r"npm ERR!", re.IGNORECASE),
        re.compile(r"ELIFECYCLE", re.IGNORECASE),
        re.compile(r"npm warn", re.IGNORECASE),
    ],
    ErrorType.ENOENT_ERROR: [
        re.compile(r"ENOENT.*no such file", re.IGNORECASE),
        re.compile(r"Error: ENOENT", re.IGNORECASE),
    ],
    ErrorType.PERMISSION_ERROR: [
        re.compile(r"EACCES", re.IGNORECASE),
        re.compile(r"Permission denied", re.IGNORECASE),
    ],
    ErrorType.PORT_IN_USE: [
        re.compile(r"EADDRINUSE", re.IGNORECASE),
        re.compile(r"address already in use", re.IGNORECASE),
        re.compile(r"port.*already.*use", re.IGNORECASE),
    ],
}


# ============= STACK TRACE TEMPLATES =============

STACK_TEMPLATES: Dict[ErrorType, str] = {
    ErrorType.NODE_MODULE_NOT_FOUND: """Error: Cannot find module '{module}'
Require stack:
- {file}
    at Function.Module._resolveFilename (node:internal/modules/cjs/loader:1075:15)
    at Function.Module._load (node:internal/modules/cjs/loader:920:27)
    at Module.require (node:internal/modules/cjs/loader:1141:19)
    at require (node:internal/modules/cjs/helpers:110:18)
    at Object.<anonymous> ({file}:{line}:{column})

Fix: Run 'npm install {module}' or check if the module name is correct in your import statement.""",

    ErrorType.NODE_SYNTAX_ERROR: """SyntaxError: {message}
    at {file}:{line}:{column}
    at Module._compile (node:internal/modules/cjs/loader:1254:14)
    at Module._extensions..js (node:internal/modules/cjs/loader:1308:10)
    at Module.load (node:internal/modules/cjs/loader:1117:32)
    at Module._load (node:internal/modules/cjs/loader:958:12)

Fix: Check the syntax at the indicated line. Common issues: missing brackets, quotes, or semicolons.""",

    ErrorType.NODE_TYPE_ERROR: """TypeError: {message}
    at {file}:{line}:{column}
    at Module._compile (node:internal/modules/cjs/loader:1254:14)
    at processTicksAndRejections (node:internal/process/task_queues:95:5)

Fix: Check that the variable/property exists and is the correct type before using it.""",

    ErrorType.NODE_REFERENCE_ERROR: """ReferenceError: {message}
    at {file}:{line}:{column}
    at Module._compile (node:internal/modules/cjs/loader:1254:14)
    at Module._extensions..js (node:internal/modules/cjs/loader:1308:10)

Fix: Make sure the variable is declared before use. Check for typos in variable names.""",

    ErrorType.TYPESCRIPT_ERROR: """error TS{code}: {message}

{file}:{line}:{column} - error TS{code}: {message}

{line} | {code_snippet}
     | {error_indicator}

Fix: Check type definitions and ensure all types are compatible.""",

    ErrorType.VITE_BUILD_ERROR: """[vite] Pre-transform error: {message}

{file}:{line}:{column}

Internal server error: {message}
  Plugin: vite:import-analysis
  File: {file}

Fix: Check the import path and ensure the module exists. Run 'npm install' if dependencies are missing.""",

    ErrorType.REACT_ERROR: """Error: {message}

This error occurred in the <{component}> component:
    at {component} ({file}:{line}:{column})
    at renderWithHooks (react-dom.development.js)
    at mountIndeterminateComponent (react-dom.development.js)

Fix: Ensure hooks are called at the top level of function components, not in conditions or loops.""",

    ErrorType.PYTHON_IMPORT_ERROR: """Traceback (most recent call last):
  File "{file}", line {line}, in <module>
    import {module}
ModuleNotFoundError: No module named '{module}'

Fix: Run 'pip install {module}' or check if the module name is correct.""",

    ErrorType.PYTHON_SYNTAX_ERROR: """  File "{file}", line {line}
    {code_snippet}
    {error_indicator}
SyntaxError: {message}

Fix: Check the syntax at the indicated line. Common issues: missing colons, incorrect indentation.""",

    ErrorType.NPM_ERROR: """npm ERR! code ELIFECYCLE
npm ERR! errno 1
npm ERR! {package}@{version} {script}: `{command}`
npm ERR! Exit status 1
npm ERR!
npm ERR! Failed at the {package}@{version} {script} script.
npm ERR! This is probably not a problem with npm.

Fix: Check the error above. Common causes: missing dependencies, build script errors, or syntax errors.""",

    ErrorType.ENOENT_ERROR: """Error: ENOENT: no such file or directory, open '{file}'
    at Object.openSync (node:fs:603:3)
    at Object.readFileSync (node:fs:471:35)

Fix: Ensure the file exists at the specified path. Check for typos in the file path.""",

    ErrorType.PORT_IN_USE: """Error: listen EADDRINUSE: address already in use :{port}
    at Server.setupListenHandle [as _listen2] (node:net:1463:16)
    at listenInCluster (node:net:1511:12)

Fix: Either stop the process using port {port}, or use a different port.
Run: lsof -i :{port} (Mac/Linux) or netstat -ano | findstr :{port} (Windows) to find the process.""",
}


# ============= FILE/LINE EXTRACTION PATTERNS =============

FILE_LINE_PATTERNS = [
    # Node.js style: at Object.<anonymous> (/path/file.js:10:5)
    re.compile(r'at\s+.*?\s+\(([^:]+):(\d+):(\d+)\)'),
    # Direct: /path/file.js:10:5
    re.compile(r'([^\s:]+\.[jt]sx?):(\d+):(\d+)'),
    # Python style: File "/path/file.py", line 10
    re.compile(r'File\s+"([^"]+)",\s+line\s+(\d+)'),
    # Vite/Webpack: src/App.tsx:10:5
    re.compile(r'^([^\s:]+):(\d+):(\d+)'),
    # TypeScript: file.ts(10,5)
    re.compile(r'([^\s:]+\.[jt]sx?)\((\d+),(\d+)\)'),
]

MODULE_PATTERNS = [
    re.compile(r"Cannot find module ['\"]([^'\"]+)['\"]"),
    re.compile(r"Can't resolve ['\"]([^'\"]+)['\"]"),
    re.compile(r"No module named ['\"]([^'\"]+)['\"]"),
    re.compile(r"import ['\"]([^'\"]+)['\"]"),
]


class LogRebuilder:
    """
    Rebuilds incomplete error logs to ensure Claude gets full context.

    Even if sandbox sends only the first line of an error, this will
    complete the stack trace using templates, giving Claude the context
    needed to generate correct fixes.
    """

    def __init__(self):
        self.error_patterns = ERROR_PATTERNS
        self.stack_templates = STACK_TEMPLATES

    def rebuild(self, raw_log: str, context: Optional[Dict] = None) -> DetectedError:
        """
        Main entry point: Rebuild incomplete log into full error context.

        Args:
            raw_log: The original (possibly incomplete) error log
            context: Optional context (file_tree, recent_files, etc.)

        Returns:
            DetectedError with rebuilt full stack trace
        """
        if not raw_log or not raw_log.strip():
            return DetectedError(
                error_type=ErrorType.GENERIC_ERROR,
                message="Empty error log",
                original_log=raw_log,
                rebuilt_log="No error content to analyze",
                confidence=0.0
            )

        # Step 1: Detect error type
        error_type, confidence = self._detect_error_type(raw_log)

        # Step 2: Extract error details (message, file, line, module)
        details = self._extract_error_details(raw_log, error_type)

        # Step 3: Check if log is already complete (has stack trace)
        if self._has_complete_stack(raw_log, error_type):
            # Log is already complete, just normalize it
            rebuilt = self._normalize_log(raw_log)
            return DetectedError(
                error_type=error_type,
                message=details.get("message", raw_log[:200]),
                file=details.get("file"),
                line=details.get("line"),
                column=details.get("column"),
                module=details.get("module"),
                original_log=raw_log,
                rebuilt_log=rebuilt,
                confidence=confidence
            )

        # Step 4: Rebuild incomplete log using template
        rebuilt = self._rebuild_with_template(raw_log, error_type, details, context)

        return DetectedError(
            error_type=error_type,
            message=details.get("message", raw_log[:200]),
            file=details.get("file"),
            line=details.get("line"),
            column=details.get("column"),
            module=details.get("module"),
            original_log=raw_log,
            rebuilt_log=rebuilt,
            confidence=confidence
        )

    def _detect_error_type(self, log: str) -> Tuple[ErrorType, float]:
        """Detect the type of error from the log content"""
        best_match = ErrorType.GENERIC_ERROR
        best_confidence = 0.0

        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if pattern.search(log):
                    # More specific patterns get higher confidence
                    confidence = 0.9 if len(patterns) == 1 else 0.8
                    if confidence > best_confidence:
                        best_match = error_type
                        best_confidence = confidence

        # If no specific match, check for generic error keywords
        if best_confidence == 0.0:
            if "error" in log.lower():
                best_confidence = 0.3
            elif "failed" in log.lower():
                best_confidence = 0.2

        return best_match, best_confidence

    def _extract_error_details(self, log: str, error_type: ErrorType) -> Dict:
        """Extract structured details from error log"""
        details = {
            "message": "",
            "file": None,
            "line": None,
            "column": None,
            "module": None,
        }

        # Extract file, line, column
        for pattern in FILE_LINE_PATTERNS:
            match = pattern.search(log)
            if match:
                groups = match.groups()
                details["file"] = groups[0] if len(groups) > 0 else None
                details["line"] = int(groups[1]) if len(groups) > 1 and groups[1] else None
                details["column"] = int(groups[2]) if len(groups) > 2 and groups[2] else None
                break

        # Extract module name
        for pattern in MODULE_PATTERNS:
            match = pattern.search(log)
            if match:
                details["module"] = match.group(1)
                break

        # Extract error message (first line usually)
        lines = log.strip().split('\n')
        if lines:
            # Clean up the message
            msg = lines[0].strip()
            # Remove common prefixes
            for prefix in ['Error:', 'TypeError:', 'SyntaxError:', 'ReferenceError:',
                          'ModuleNotFoundError:', 'ImportError:', '[vite]', 'npm ERR!']:
                if msg.startswith(prefix):
                    msg = msg[len(prefix):].strip()
            details["message"] = msg[:500]  # Limit length

        return details

    def _has_complete_stack(self, log: str, error_type: ErrorType) -> bool:
        """Check if the log already has a complete stack trace"""
        lines = log.strip().split('\n')

        # Need at least 3 lines for a reasonable stack trace
        if len(lines) < 3:
            return False

        # Check for stack trace indicators
        stack_indicators = [
            '    at ',  # Node.js style
            'Traceback',  # Python style
            '  File "',  # Python style
            'at Function.',  # Node.js
            'at Module.',  # Node.js
            'at Object.',  # Node.js
        ]

        indicator_count = sum(1 for line in lines if any(ind in line for ind in stack_indicators))

        # Consider complete if at least 2 stack frames present
        return indicator_count >= 2

    def _normalize_log(self, log: str) -> str:
        """Normalize an already-complete log for consistency"""
        lines = log.strip().split('\n')

        # Remove empty lines but keep structure
        normalized = []
        for line in lines:
            stripped = line.rstrip()
            if stripped or (normalized and normalized[-1]):  # Keep single empty lines
                normalized.append(stripped)

        return '\n'.join(normalized)

    def _rebuild_with_template(
        self,
        raw_log: str,
        error_type: ErrorType,
        details: Dict,
        context: Optional[Dict] = None
    ) -> str:
        """Rebuild incomplete log using template"""

        # Get template for this error type
        template = self.stack_templates.get(error_type)

        if not template:
            # No template, return original with enhancement note
            return f"""{raw_log}

[Log Rebuilder Note: Stack trace may be incomplete. Error type: {error_type.value}]

Suggested investigation:
- Check the file mentioned in the error
- Look for related errors in the full terminal output
- Verify all dependencies are installed"""

        # Fill in template placeholders
        rebuilt = template

        # Common replacements
        replacements = {
            '{message}': details.get('message', 'Unknown error'),
            '{file}': details.get('file', 'unknown_file'),
            '{line}': str(details.get('line', 1)),
            '{column}': str(details.get('column', 1)),
            '{module}': details.get('module', 'unknown_module'),
            '{package}': details.get('module', 'unknown_package'),
            '{version}': '1.0.0',
            '{script}': 'dev',
            '{command}': 'npm run dev',
            '{port}': '3000',
            '{code}': '2307',  # Common TS error code
            '{component}': 'Component',
            '{code_snippet}': '// code here',
            '{error_indicator}': '^^^^^^^^',
        }

        for placeholder, value in replacements.items():
            rebuilt = rebuilt.replace(placeholder, value)

        # Add original log at the end for reference
        rebuilt += f"""

---
[Original Log (may be truncated)]
{raw_log[:1000]}"""

        return rebuilt

    def detect_and_suggest_fix(self, log: str) -> Dict:
        """
        Detect error and suggest a fix action.

        Returns dict with:
        - error_type: The detected error type
        - suggested_fix: Human-readable fix suggestion
        - auto_fix_command: Command that might fix the issue (if applicable)
        """
        detected = self.rebuild(log)

        suggestions = {
            ErrorType.NODE_MODULE_NOT_FOUND: {
                "fix": f"Install missing module: {detected.module}",
                "command": f"npm install {detected.module}" if detected.module else "npm install"
            },
            ErrorType.PYTHON_IMPORT_ERROR: {
                "fix": f"Install missing Python module: {detected.module}",
                "command": f"pip install {detected.module}" if detected.module else "pip install -r requirements.txt"
            },
            ErrorType.NPM_ERROR: {
                "fix": "Reinstall dependencies",
                "command": "rm -rf node_modules && npm install"
            },
            ErrorType.PORT_IN_USE: {
                "fix": "Kill process using the port or use different port",
                "command": None  # Requires manual intervention
            },
            ErrorType.TYPESCRIPT_ERROR: {
                "fix": "Fix TypeScript type errors",
                "command": None
            },
        }

        suggestion = suggestions.get(detected.error_type, {
            "fix": "Review the error and fix the indicated issue",
            "command": None
        })

        return {
            "error_type": detected.error_type.value,
            "message": detected.message,
            "file": detected.file,
            "line": detected.line,
            "module": detected.module,
            "suggested_fix": suggestion["fix"],
            "auto_fix_command": suggestion["command"],
            "rebuilt_log": detected.rebuilt_log,
            "confidence": detected.confidence
        }


# Global singleton instance
log_rebuilder = LogRebuilder()


def rebuild_log(raw_log: str, context: Optional[Dict] = None) -> DetectedError:
    """Convenience function to rebuild a log"""
    return log_rebuilder.rebuild(raw_log, context)


def get_fixer_payload_with_rebuilt_log(raw_log: str, context: Optional[Dict] = None) -> Dict:
    """
    Get a complete fixer payload with rebuilt log.

    This is the main entry point for integration with the Fixer Agent.
    """
    detected = log_rebuilder.rebuild(raw_log, context)
    suggestion = log_rebuilder.detect_and_suggest_fix(raw_log)

    return {
        "error": {
            "type": detected.error_type.value,
            "message": detected.message,
            "file": detected.file,
            "line": detected.line,
            "column": detected.column,
            "module": detected.module,
        },
        "logs": {
            "original": detected.original_log,
            "rebuilt": detected.rebuilt_log,
            "confidence": detected.confidence,
        },
        "suggestion": {
            "fix": suggestion["suggested_fix"],
            "command": suggestion["auto_fix_command"],
        },
        "context": context or {}
    }
