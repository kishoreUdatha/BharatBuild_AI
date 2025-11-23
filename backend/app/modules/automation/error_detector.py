"""
Error Detector and Auto-Fix System
Parses build/runtime errors and attempts automatic fixes
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass

from app.core.logging_config import logger
from app.utils.claude_client import claude_client


@dataclass
class ErrorPattern:
    """Pattern for matching errors"""
    pattern: str
    error_type: str
    severity: str  # 'critical', 'warning', 'info'
    auto_fixable: bool


class ErrorDetector:
    """Detects and analyzes errors from build/runtime output"""

    # Common error patterns
    ERROR_PATTERNS = [
        # Node/JavaScript/TypeScript errors
        ErrorPattern(
            pattern=r"Module not found: Error: Can't resolve '(.+?)'",
            error_type="missing_module",
            severity="critical",
            auto_fixable=True
        ),
        ErrorPattern(
            pattern=r"Cannot find module '(.+?)'",
            error_type="missing_module",
            severity="critical",
            auto_fixable=True
        ),
        ErrorPattern(
            pattern=r"Module '(.+?)' has no exported member '(.+?)'",
            error_type="missing_export",
            severity="critical",
            auto_fixable=False
        ),
        ErrorPattern(
            pattern=r"Property '(.+?)' does not exist on type '(.+?)'",
            error_type="typescript_type_error",
            severity="critical",
            auto_fixable=False
        ),
        ErrorPattern(
            pattern=r"SyntaxError: (.+)",
            error_type="syntax_error",
            severity="critical",
            auto_fixable=False
        ),
        ErrorPattern(
            pattern=r"ReferenceError: (.+?) is not defined",
            error_type="undefined_reference",
            severity="critical",
            auto_fixable=False
        ),

        # Port errors
        ErrorPattern(
            pattern=r"Port (\d+) is already in use",
            error_type="port_in_use",
            severity="critical",
            auto_fixable=True
        ),
        ErrorPattern(
            pattern=r"EADDRINUSE.*:(\d+)",
            error_type="port_in_use",
            severity="critical",
            auto_fixable=True
        ),

        # Python errors
        ErrorPattern(
            pattern=r"ModuleNotFoundError: No module named '(.+?)'",
            error_type="missing_python_module",
            severity="critical",
            auto_fixable=True
        ),
        ErrorPattern(
            pattern=r"ImportError: cannot import name '(.+?)' from '(.+?)'",
            error_type="missing_import",
            severity="critical",
            auto_fixable=False
        ),

        # Java errors
        ErrorPattern(
            pattern=r"package (.+?) does not exist",
            error_type="missing_java_package",
            severity="critical",
            auto_fixable=True
        ),

        # General warnings
        ErrorPattern(
            pattern=r"warning: (.+)",
            error_type="warning",
            severity="warning",
            auto_fixable=False
        ),
    ]

    def detect_errors(self, output: str) -> List[Dict]:
        """
        Detect errors in build/runtime output

        Args:
            output: Build or runtime output text

        Returns:
            List of detected errors with details
        """
        detected_errors = []

        for pattern_obj in self.ERROR_PATTERNS:
            matches = re.finditer(pattern_obj.pattern, output, re.MULTILINE | re.IGNORECASE)

            for match in matches:
                error = {
                    "type": pattern_obj.error_type,
                    "severity": pattern_obj.severity,
                    "auto_fixable": pattern_obj.auto_fixable,
                    "message": match.group(0),
                    "line": self._find_line_number(output, match.start()),
                    "context": self._get_context(output, match.start()),
                }

                # Extract specific details based on error type
                if pattern_obj.error_type == "missing_module":
                    error["module_name"] = match.group(1)
                elif pattern_obj.error_type == "port_in_use":
                    error["port"] = match.group(1)
                elif pattern_obj.error_type == "missing_python_module":
                    error["module_name"] = match.group(1)

                detected_errors.append(error)

        return detected_errors

    def _find_line_number(self, text: str, position: int) -> int:
        """Find line number for a position in text"""
        return text[:position].count('\n') + 1

    def _get_context(self, text: str, position: int, lines_before: int = 2, lines_after: int = 2) -> str:
        """Get context lines around the error"""
        all_lines = text.split('\n')
        line_num = self._find_line_number(text, position)

        start = max(0, line_num - lines_before - 1)
        end = min(len(all_lines), line_num + lines_after)

        return '\n'.join(all_lines[start:end])

    async def suggest_fix(self, error: Dict, project_context: Optional[str] = None) -> Optional[Dict]:
        """
        Suggest a fix for an error

        Args:
            error: Error dictionary from detect_errors
            project_context: Additional project context

        Returns:
            Fix suggestion or None
        """
        if not error.get("auto_fixable"):
            return None

        error_type = error.get("type")

        # Auto-fixable errors
        if error_type == "missing_module":
            return self._fix_missing_module(error)
        elif error_type == "missing_python_module":
            return self._fix_missing_python_module(error)
        elif error_type == "port_in_use":
            return self._fix_port_in_use(error)
        elif error_type == "missing_java_package":
            return self._fix_missing_java_package(error)

        return None

    def _fix_missing_module(self, error: Dict) -> Dict:
        """Fix missing Node module by installing it"""
        module_name = error.get("module_name", "")

        # Clean up module name (remove @ prefixes, paths, etc.)
        # Example: '@react/component' -> '@react/component'
        # Example: './utils' -> skip (local module)
        if module_name.startswith('.'):
            return None

        # Remove file extensions
        module_name = re.sub(r'\.(js|jsx|ts|tsx|css|scss)$', '', module_name)

        return {
            "type": "install_package",
            "package_manager": "npm",
            "packages": [module_name],
            "description": f"Install missing module: {module_name}",
            "command": f"npm install {module_name}"
        }

    def _fix_missing_python_module(self, error: Dict) -> Dict:
        """Fix missing Python module by installing it"""
        module_name = error.get("module_name", "")

        return {
            "type": "install_package",
            "package_manager": "pip",
            "packages": [module_name],
            "description": f"Install missing Python module: {module_name}",
            "command": f"pip install {module_name}"
        }

    def _fix_missing_java_package(self, error: Dict) -> Dict:
        """Fix missing Java package (suggest Maven dependency)"""
        package_name = error.get("module_name", "")

        return {
            "type": "add_dependency",
            "package_manager": "maven",
            "description": f"Add Maven dependency for package: {package_name}",
            "manual": True,  # Requires manual POM edit
            "suggestion": f"Add the appropriate dependency for '{package_name}' to pom.xml"
        }

    def _fix_port_in_use(self, error: Dict) -> Dict:
        """Fix port in use error"""
        port = error.get("port", "3000")

        return {
            "type": "kill_port",
            "port": port,
            "description": f"Kill process using port {port}",
            "command": f"lsof -ti:{port} | xargs kill -9"  # Unix/Mac
        }

    async def auto_fix_with_claude(self, error: Dict, code_context: str) -> Optional[Dict]:
        """
        Use Claude to suggest a fix for complex errors

        Args:
            error: Error dictionary
            code_context: The code where the error occurred

        Returns:
            Fix suggestion from Claude
        """
        try:
            prompt = f"""You are a code debugging expert. Analyze this error and suggest a fix.

ERROR:
Type: {error.get('type')}
Message: {error.get('message')}

CODE CONTEXT:
{error.get('context', 'No context available')}

FULL CODE:
{code_context[:1000]}  # Limit context size

Provide a concise fix suggestion in this format:
1. What's wrong
2. How to fix it
3. Code snippet (if applicable)
"""

            response = await claude_client.generate(
                prompt=prompt,
                model="haiku",  # Use faster model for quick fixes
                max_tokens=500
            )

            return {
                "type": "claude_suggestion",
                "suggestion": response.get("content", ""),
                "description": f"Claude's suggestion for {error.get('type')}"
            }

        except Exception as e:
            logger.error(f"Error getting Claude fix suggestion: {e}")
            return None


class ErrorRecoverySystem:
    """Attempts to automatically recover from errors"""

    def __init__(self):
        self.detector = ErrorDetector()
        self.fix_history = []

    async def analyze_and_fix(
        self,
        output: str,
        project_id: str,
        max_auto_fixes: int = 3
    ) -> Dict:
        """
        Analyze errors and attempt automatic fixes

        Args:
            output: Build/runtime output with errors
            project_id: Project ID
            max_auto_fixes: Maximum number of automatic fix attempts

        Returns:
            Dict with detected errors and suggested fixes
        """
        # Detect errors
        errors = self.detector.detect_errors(output)

        if not errors:
            return {
                "success": True,
                "errors_found": 0,
                "message": "No errors detected"
            }

        # Categorize errors
        critical_errors = [e for e in errors if e['severity'] == 'critical']
        auto_fixable = [e for e in errors if e['auto_fixable']]

        # Generate fix suggestions
        fixes = []
        for error in auto_fixable[:max_auto_fixes]:
            fix = await self.detector.suggest_fix(error)
            if fix:
                fixes.append(fix)

        return {
            "success": False,
            "errors_found": len(errors),
            "critical_errors": len(critical_errors),
            "auto_fixable": len(auto_fixable),
            "errors": errors,
            "suggested_fixes": fixes,
            "can_auto_fix": len(fixes) > 0
        }


# Singleton instances
error_detector = ErrorDetector()
error_recovery = ErrorRecoverySystem()
