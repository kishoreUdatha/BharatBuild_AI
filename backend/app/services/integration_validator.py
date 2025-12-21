"""
Integration Validator - Validates frontend-backend endpoint matching

This service:
1. Detects API calls in frontend code (fetch, axios, etc.)
2. Compares them with detected backend endpoints
3. Reports mismatches, missing endpoints, and issues
4. Provides suggestions for fixing integration problems

Validates:
- Endpoint existence (frontend calls have matching backend routes)
- HTTP method matching (GET calls match GET endpoints)
- Path parameter consistency
- Request body structure (when possible)
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

from app.core.logging_config import logger


class IssueLevel(str, Enum):
    ERROR = "error"  # Will cause runtime failure
    WARNING = "warning"  # Might cause issues
    INFO = "info"  # Suggestion for improvement


@dataclass
class IntegrationIssue:
    """Represents a detected integration issue"""
    level: IssueLevel
    message: str
    frontend_file: str
    frontend_line: int
    backend_endpoint: Optional[str] = None
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "message": self.message,
            "frontend_file": self.frontend_file,
            "frontend_line": self.frontend_line,
            "backend_endpoint": self.backend_endpoint,
            "suggestion": self.suggestion,
        }


@dataclass
class FrontendApiCall:
    """Represents a detected API call in frontend code"""
    path: str
    method: str  # GET, POST, PUT, DELETE
    file: str
    line: int
    has_body: bool = False
    variable_path: bool = False  # True if path contains variables


class IntegrationValidator:
    """
    Validates that frontend API calls match backend endpoints.

    Usage:
        validator = IntegrationValidator(
            project_path=Path("/project"),
            backend_endpoints=[...],  # From EndpointDetector
        )
        result = await validator.validate()
    """

    def __init__(
        self,
        project_path: Path,
        backend_endpoints: List[Dict[str, Any]],
    ):
        self.project_path = Path(project_path)
        self.frontend_path = self._find_frontend_path()
        self.backend_endpoints = backend_endpoints
        self.issues: List[IntegrationIssue] = []
        self.frontend_calls: List[FrontendApiCall] = []

    def _find_frontend_path(self) -> Path:
        """Find the frontend directory"""
        candidates = [
            self.project_path / "frontend",
            self.project_path / "client",
            self.project_path / "web",
            self.project_path / "src",  # Single project
            self.project_path,
        ]

        for candidate in candidates:
            if candidate.exists():
                # Check for package.json or typical frontend files
                if (candidate / "package.json").exists():
                    return candidate
                if (candidate / "src").exists():
                    return candidate

        return self.project_path

    async def validate(self) -> Dict[str, Any]:
        """
        Validate frontend-backend integration.

        Returns:
            Dict with validation results, issues, and statistics
        """
        self.issues = []
        self.frontend_calls = []

        try:
            # 1. Detect all frontend API calls
            await self._detect_frontend_calls()
            logger.info(f"[IntegrationValidator] Found {len(self.frontend_calls)} frontend API calls")

            # 2. Build backend endpoint lookup
            backend_lookup = self._build_endpoint_lookup()
            logger.info(f"[IntegrationValidator] Backend has {len(backend_lookup)} endpoints")

            # 3. Validate each frontend call
            for call in self.frontend_calls:
                self._validate_call(call, backend_lookup)

            # 4. Check for unused backend endpoints
            self._check_unused_endpoints(backend_lookup)

            # 5. Build result summary
            errors = [i for i in self.issues if i.level == IssueLevel.ERROR]
            warnings = [i for i in self.issues if i.level == IssueLevel.WARNING]
            infos = [i for i in self.issues if i.level == IssueLevel.INFO]

            result = {
                "success": len(errors) == 0,
                "valid": len(errors) == 0 and len(warnings) == 0,
                "statistics": {
                    "frontend_calls": len(self.frontend_calls),
                    "backend_endpoints": len(self.backend_endpoints),
                    "errors": len(errors),
                    "warnings": len(warnings),
                    "info": len(infos),
                },
                "issues": [i.to_dict() for i in self.issues],
                "frontend_calls": [
                    {
                        "path": c.path,
                        "method": c.method,
                        "file": c.file,
                        "line": c.line,
                    }
                    for c in self.frontend_calls
                ],
                "matched_endpoints": self._get_matched_endpoints(backend_lookup),
                "unmatched_calls": self._get_unmatched_calls(backend_lookup),
            }

            logger.info(f"[IntegrationValidator] Validation complete: {len(errors)} errors, {len(warnings)} warnings")

            return result

        except Exception as e:
            logger.error(f"[IntegrationValidator] Validation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "issues": [],
            }

    async def _detect_frontend_calls(self):
        """Detect all API calls in frontend code"""
        # Find all JS/TS files
        js_files = list(self.frontend_path.rglob("*.js"))
        ts_files = list(self.frontend_path.rglob("*.ts"))
        tsx_files = list(self.frontend_path.rglob("*.tsx"))
        jsx_files = list(self.frontend_path.rglob("*.jsx"))

        all_files = js_files + ts_files + tsx_files + jsx_files

        # Exclude node_modules and build directories
        all_files = [
            f for f in all_files
            if 'node_modules' not in str(f) and
               'dist' not in str(f) and
               'build' not in str(f) and
               '.next' not in str(f)
        ]

        for file_path in all_files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')

                for i, line in enumerate(lines):
                    calls = self._extract_api_calls_from_line(line, i + 1, file_path)
                    self.frontend_calls.extend(calls)

            except Exception as e:
                logger.debug(f"[IntegrationValidator] Error reading {file_path}: {e}")

    def _extract_api_calls_from_line(
        self,
        line: str,
        line_num: int,
        file_path: Path
    ) -> List[FrontendApiCall]:
        """Extract API calls from a single line of code"""
        calls = []

        # Patterns for API calls
        patterns = [
            # fetch('/api/users')
            (r'fetch\s*\(\s*[`\'"]([^`\'"]+)[`\'"]', 'GET'),
            # fetch('/api/users', { method: 'POST' })
            (r'fetch\s*\(\s*[`\'"]([^`\'"]+)[`\'"].*?method:\s*[\'"](\w+)[\'"]', None),

            # axios.get('/api/users')
            (r'axios\.(get|post|put|patch|delete)\s*\(\s*[`\'"]([^`\'"]+)[`\'"]', None),
            # api.get('/api/users')
            (r'(?:api|client|http)\.(get|post|put|patch|delete)\s*\(\s*[`\'"]([^`\'"]+)[`\'"]', None),

            # axios({ url: '/api/users', method: 'GET' })
            (r'axios\s*\(\s*\{[^}]*url:\s*[`\'"]([^`\'"]+)[`\'"][^}]*method:\s*[\'"](\w+)[\'"]', None),

            # Template literals: fetch(`/api/users/${id}`)
            (r'fetch\s*\(\s*`([^`]+)`', 'GET'),
            (r'axios\.(get|post|put|patch|delete)\s*\(\s*`([^`]+)`', None),
            (r'(?:api|client|http)\.(get|post|put|patch|delete)\s*\(\s*`([^`]+)`', None),
        ]

        for pattern, default_method in patterns:
            for match in re.finditer(pattern, line, re.IGNORECASE):
                groups = match.groups()

                # Determine method and path based on pattern
                if len(groups) == 1:
                    path = groups[0]
                    method = default_method or 'GET'
                elif len(groups) == 2:
                    if groups[0].upper() in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
                        method = groups[0].upper()
                        path = groups[1]
                    else:
                        path = groups[0]
                        method = groups[1].upper() if groups[1] else 'GET'
                else:
                    continue

                # Skip non-API paths
                if not self._is_api_path(path):
                    continue

                # Detect if path has variables
                variable_path = '${' in path or '{' in path

                # Normalize path
                normalized_path = self._normalize_frontend_path(path)

                # Detect if has body
                has_body = method in ['POST', 'PUT', 'PATCH']

                calls.append(FrontendApiCall(
                    path=normalized_path,
                    method=method,
                    file=str(file_path.relative_to(self.project_path)),
                    line=line_num,
                    has_body=has_body,
                    variable_path=variable_path,
                ))

        return calls

    def _is_api_path(self, path: str) -> bool:
        """Check if path looks like an API endpoint"""
        # Skip relative imports, assets, external URLs
        if path.startswith('.') or path.startswith('http') or path.startswith('//'):
            return False

        # Check for common API patterns
        api_patterns = ['/api', '/v1', '/v2', '/graphql', '/rest']
        return any(p in path.lower() for p in api_patterns) or path.startswith('/')

    def _normalize_frontend_path(self, path: str) -> str:
        """Normalize frontend path for comparison"""
        # Handle template literals
        # /api/users/${id} -> /api/users/{id}
        path = re.sub(r'\$\{[^}]+\}', '{id}', path)

        # Handle path parameters
        # /api/users/:id -> /api/users/{id}
        path = re.sub(r':(\w+)', r'{\1}', path)

        # Ensure leading slash
        if not path.startswith('/'):
            path = '/' + path

        # Remove trailing slash
        path = path.rstrip('/')

        return path

    def _build_endpoint_lookup(self) -> Dict[str, Dict[str, Any]]:
        """Build lookup dictionary from backend endpoints"""
        lookup = {}

        for endpoint in self.backend_endpoints:
            path = endpoint['path']
            method = endpoint['method']

            # Normalize path
            path = self._normalize_backend_path(path)

            key = f"{method}:{path}"
            lookup[key] = {
                **endpoint,
                'matched': False,
            }

        return lookup

    def _normalize_backend_path(self, path: str) -> str:
        """Normalize backend path for comparison"""
        # Handle Spring path variables: {id} stays as {id}
        # Handle Flask/FastAPI: <id> -> {id}
        path = re.sub(r'<(?:\w+:)?(\w+)>', r'{\1}', path)

        # Ensure leading slash
        if not path.startswith('/'):
            path = '/' + path

        # Remove trailing slash
        path = path.rstrip('/')

        return path

    def _validate_call(
        self,
        call: FrontendApiCall,
        backend_lookup: Dict[str, Dict[str, Any]]
    ):
        """Validate a single frontend API call"""
        # Build key
        key = f"{call.method}:{call.path}"

        # Direct match
        if key in backend_lookup:
            backend_lookup[key]['matched'] = True
            return

        # Try matching with path parameter normalization
        matched = self._try_fuzzy_match(call, backend_lookup)
        if matched:
            return

        # No match found - report error
        self.issues.append(IntegrationIssue(
            level=IssueLevel.ERROR,
            message=f"No backend endpoint found for {call.method} {call.path}",
            frontend_file=call.file,
            frontend_line=call.line,
            suggestion=self._suggest_endpoint(call, backend_lookup),
        ))

    def _try_fuzzy_match(
        self,
        call: FrontendApiCall,
        backend_lookup: Dict[str, Dict[str, Any]]
    ) -> bool:
        """Try to match with path parameter variations"""
        # For paths with {id}, try matching patterns
        call_pattern = self._path_to_pattern(call.path)

        for key, endpoint in backend_lookup.items():
            method, path = key.split(':', 1)

            if method != call.method:
                continue

            backend_pattern = self._path_to_pattern(path)

            if call_pattern == backend_pattern:
                endpoint['matched'] = True
                return True

        return False

    def _path_to_pattern(self, path: str) -> str:
        """Convert path to pattern for matching"""
        # Replace all {param} with {*}
        return re.sub(r'\{[^}]+\}', '{*}', path)

    def _suggest_endpoint(
        self,
        call: FrontendApiCall,
        backend_lookup: Dict[str, Dict[str, Any]]
    ) -> str:
        """Suggest possible fixes for missing endpoint"""
        suggestions = []

        # Find similar paths
        call_parts = call.path.strip('/').split('/')
        call_resource = call_parts[1] if len(call_parts) > 1 else call_parts[0]

        for key, endpoint in backend_lookup.items():
            method, path = key.split(':', 1)
            path_parts = path.strip('/').split('/')

            # Same method, similar path
            if method == call.method:
                path_resource = path_parts[1] if len(path_parts) > 1 else path_parts[0]
                if call_resource.lower() == path_resource.lower():
                    suggestions.append(f"Did you mean {method} {path}?")

            # Different method, same path
            if path == call.path and method != call.method:
                suggestions.append(f"Path exists but with {method} method instead of {call.method}")

        if suggestions:
            return " ".join(suggestions[:2])

        return f"Add endpoint: {call.method} {call.path} to backend"

    def _check_unused_endpoints(self, backend_lookup: Dict[str, Dict[str, Any]]):
        """Check for backend endpoints not called by frontend"""
        for key, endpoint in backend_lookup.items():
            if not endpoint.get('matched'):
                method, path = key.split(':', 1)

                # Skip common utility endpoints
                if any(p in path.lower() for p in ['health', 'status', 'docs', 'openapi', 'swagger']):
                    continue

                self.issues.append(IntegrationIssue(
                    level=IssueLevel.INFO,
                    message=f"Backend endpoint {method} {path} is not used by frontend",
                    frontend_file="",
                    frontend_line=0,
                    backend_endpoint=path,
                    suggestion="Consider adding frontend call or remove if unused",
                ))

    def _get_matched_endpoints(
        self,
        backend_lookup: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Get list of matched endpoints"""
        return [
            key for key, ep in backend_lookup.items()
            if ep.get('matched')
        ]

    def _get_unmatched_calls(
        self,
        backend_lookup: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Get list of unmatched frontend calls"""
        matched_keys = set()

        for key, ep in backend_lookup.items():
            if ep.get('matched'):
                matched_keys.add(key)

        unmatched = []
        for call in self.frontend_calls:
            key = f"{call.method}:{call.path}"
            pattern_key = f"{call.method}:{self._path_to_pattern(call.path)}"

            # Check both exact and pattern match
            is_matched = False
            for bkey in backend_lookup.keys():
                if bkey == key:
                    is_matched = True
                    break
                method, path = bkey.split(':', 1)
                if method == call.method and self._path_to_pattern(path) == self._path_to_pattern(call.path):
                    is_matched = True
                    break

            if not is_matched:
                unmatched.append({
                    "path": call.path,
                    "method": call.method,
                    "file": call.file,
                    "line": call.line,
                })

        return unmatched


async def validate_integration(
    project_path: Path,
    backend_endpoints: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Convenience function to validate integration.

    Usage:
        result = await validate_integration(
            project_path=Path("/project"),
            backend_endpoints=detected_endpoints,
        )
    """
    validator = IntegrationValidator(
        project_path=project_path,
        backend_endpoints=backend_endpoints,
    )
    return await validator.validate()
