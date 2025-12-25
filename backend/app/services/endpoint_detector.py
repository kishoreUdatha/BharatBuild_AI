"""
Endpoint Detector Service - Detects API endpoints from generated backend code

This service parses backend code to extract API endpoint information:
- Route paths (/api/users, /api/products/:id)
- HTTP methods (GET, POST, PUT, DELETE)
- Request/Response types (from DTOs, Pydantic models, etc.)
- Authentication requirements

Supports:
- FastAPI (Python)
- Spring Boot (Java)
- Express.js (Node.js)
- Django REST Framework (Python)
- Flask (Python)
"""

import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

from app.core.logging_config import logger


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


@dataclass
class EndpointParam:
    """Represents a parameter in an endpoint"""
    name: str
    param_type: str  # path, query, body
    data_type: str  # string, number, object, etc.
    required: bool = True
    description: str = ""


@dataclass
class Endpoint:
    """Represents a detected API endpoint"""
    path: str
    method: HttpMethod
    name: str  # Function/method name
    description: str = ""
    request_body: Optional[str] = None  # DTO/Schema type
    response_type: Optional[str] = None  # Response DTO/Schema type
    params: List[EndpointParam] = field(default_factory=list)
    auth_required: bool = False
    tags: List[str] = field(default_factory=list)
    source_file: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EndpointDetector:
    """
    Detects API endpoints from backend source code.

    Usage:
        detector = EndpointDetector(project_path)
        endpoints = await detector.detect()
    """

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.backend_path = self._find_backend_path()
        self.endpoints: List[Endpoint] = []
        self.schemas: Dict[str, Dict[str, Any]] = {}  # Detected DTOs/Schemas

    def _find_backend_path(self) -> Path:
        """Find the backend directory"""
        # Check common patterns
        candidates = [
            self.project_path / "backend",
            self.project_path / "server",
            self.project_path / "api",
            self.project_path / "src" / "main",  # Spring Boot
            self.project_path,  # Backend-only project
        ]

        for candidate in candidates:
            if candidate.exists():
                # Verify it's actually a backend
                if self._is_backend_dir(candidate):
                    return candidate

        return self.project_path

    def _is_backend_dir(self, path: Path) -> bool:
        """Check if directory contains backend code"""
        indicators = [
            "requirements.txt",
            "pom.xml",
            "build.gradle",
            "package.json",
            "main.py",
            "app.py",
            "manage.py",
        ]
        return any((path / ind).exists() for ind in indicators)

    async def detect(self) -> Dict[str, Any]:
        """
        Detect all API endpoints from the backend code.

        Returns:
            Dict with endpoints, schemas, and metadata
        """
        self.endpoints = []
        self.schemas = {}

        # Detect backend type and parse accordingly
        backend_type = self._detect_backend_type()
        logger.info(f"[EndpointDetector] Detected backend type: {backend_type}")

        if backend_type == "fastapi":
            await self._detect_fastapi_endpoints()
        elif backend_type == "spring":
            await self._detect_spring_endpoints()
        elif backend_type == "express":
            await self._detect_express_endpoints()
        elif backend_type == "django":
            await self._detect_django_endpoints()
        elif backend_type == "flask":
            await self._detect_flask_endpoints()
        else:
            logger.warning(f"[EndpointDetector] Unknown backend type, trying all parsers")
            await self._detect_fastapi_endpoints()
            await self._detect_spring_endpoints()
            await self._detect_express_endpoints()

        # Normalize paths
        self._normalize_endpoints()

        logger.info(f"[EndpointDetector] Detected {len(self.endpoints)} endpoints")

        return {
            "backend_type": backend_type,
            "endpoints": [ep.to_dict() for ep in self.endpoints],
            "schemas": self.schemas,
            "base_path": self._detect_base_path(),
            "auth_type": self._detect_auth_type(),
        }

    def _detect_backend_type(self) -> str:
        """Detect the backend framework type"""
        # Check for Python frameworks
        req_file = self.backend_path / "requirements.txt"
        if not req_file.exists():
            req_file = self.backend_path / "backend" / "requirements.txt"

        if req_file.exists():
            content = req_file.read_text().lower()
            if "fastapi" in content:
                return "fastapi"
            elif "django" in content:
                return "django"
            elif "flask" in content:
                return "flask"

        # Check for Java/Spring
        if (self.backend_path / "pom.xml").exists() or (self.backend_path / "build.gradle").exists():
            return "spring"

        # Check for Node.js/Express
        pkg_file = self.backend_path / "package.json"
        if not pkg_file.exists():
            pkg_file = self.backend_path / "backend" / "package.json"

        if pkg_file.exists():
            try:
                pkg = json.loads(pkg_file.read_text())
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "express" in deps:
                    return "express"
                elif "fastify" in deps:
                    return "fastify"
                elif "koa" in deps:
                    return "koa"
            except (json.JSONDecodeError, IOError, OSError, KeyError) as e:
                logger.debug(f"Could not detect backend framework from package.json: {e}")

        return "unknown"

    async def _detect_fastapi_endpoints(self):
        """Parse FastAPI/Starlette endpoints"""
        python_files = list(self.backend_path.rglob("*.py"))

        # Patterns for FastAPI decorators
        decorator_patterns = [
            # @app.get("/path"), @router.post("/path"), etc.
            r'@(?:app|router|api|api_router)\.(\w+)\s*\(\s*["\']([^"\']+)["\']',
            # @app.api_route("/path", methods=["GET", "POST"])
            r'@(?:app|router)\.api_route\s*\(\s*["\']([^"\']+)["\'].*?methods\s*=\s*\[([^\]]+)\]',
        ]

        # Pattern for function definition after decorator
        func_pattern = r'(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)'

        for py_file in python_files:
            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')

                for i, line in enumerate(lines):
                    for pattern in decorator_patterns:
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            # Extract method and path
                            if "api_route" in pattern:
                                path = match.group(1)
                                methods_str = match.group(2)
                                methods = re.findall(r'["\'](\w+)["\']', methods_str)
                            else:
                                method_str = match.group(1).upper()
                                path = match.group(2)
                                methods = [method_str]

                            # Find function name in next few lines
                            func_name = "unknown"
                            params = []
                            request_body = None

                            for j in range(i + 1, min(i + 5, len(lines))):
                                func_match = re.search(func_pattern, lines[j])
                                if func_match:
                                    func_name = func_match.group(1)
                                    params_str = func_match.group(2)

                                    # Parse parameters
                                    params, request_body = self._parse_fastapi_params(params_str)
                                    break

                            # Check for authentication
                            auth_required = self._check_fastapi_auth(content, i)

                            # Create endpoint for each method
                            for method in methods:
                                try:
                                    http_method = HttpMethod(method.upper())
                                except ValueError:
                                    continue

                                endpoint = Endpoint(
                                    path=path,
                                    method=http_method,
                                    name=func_name,
                                    params=params,
                                    request_body=request_body,
                                    auth_required=auth_required,
                                    source_file=str(py_file.relative_to(self.project_path)),
                                )
                                self.endpoints.append(endpoint)

                # Also detect Pydantic schemas
                self._detect_pydantic_schemas(content, py_file)

            except Exception as e:
                logger.debug(f"[EndpointDetector] Error parsing {py_file}: {e}")

    def _parse_fastapi_params(self, params_str: str) -> Tuple[List[EndpointParam], Optional[str]]:
        """Parse FastAPI function parameters"""
        params = []
        request_body = None

        # Remove type hints complexity for parsing
        param_parts = params_str.split(',')

        for part in param_parts:
            part = part.strip()
            if not part or part in ['self', 'request', 'response', 'db', 'session']:
                continue

            # Check for path parameter: item_id: int
            path_match = re.match(r'(\w+)\s*:\s*(\w+)', part)
            if path_match:
                name = path_match.group(1)
                dtype = path_match.group(2)

                # Check if it's a body parameter (Pydantic model)
                if dtype[0].isupper() and dtype not in ['str', 'int', 'float', 'bool', 'Request', 'Response']:
                    request_body = dtype
                elif name.endswith('_id') or name == 'id':
                    params.append(EndpointParam(
                        name=name,
                        param_type="path",
                        data_type=dtype.lower(),
                    ))
                else:
                    params.append(EndpointParam(
                        name=name,
                        param_type="query",
                        data_type=dtype.lower(),
                    ))

        return params, request_body

    def _check_fastapi_auth(self, content: str, line_num: int) -> bool:
        """Check if endpoint requires authentication"""
        # Look for Depends with auth-related functions
        auth_patterns = [
            r'Depends\s*\(\s*(?:get_current_user|require_auth|auth|verify_token)',
            r'Security\s*\(',
            r'OAuth2PasswordBearer',
            r'HTTPBearer',
        ]

        # Check the function and a few lines above/below
        lines = content.split('\n')
        start = max(0, line_num - 2)
        end = min(len(lines), line_num + 10)
        context = '\n'.join(lines[start:end])

        return any(re.search(p, context) for p in auth_patterns)

    def _detect_pydantic_schemas(self, content: str, file_path: Path):
        """Detect Pydantic model schemas"""
        # Pattern for class MyModel(BaseModel):
        schema_pattern = r'class\s+(\w+)\s*\(\s*(?:BaseModel|Schema)\s*\):'

        for match in re.finditer(schema_pattern, content):
            schema_name = match.group(1)

            # Extract fields (simplified)
            start_pos = match.end()
            fields = {}

            # Look for field definitions
            field_pattern = r'(\w+)\s*:\s*([^=\n]+)'
            for field_match in re.finditer(field_pattern, content[start_pos:start_pos + 500]):
                field_name = field_match.group(1)
                field_type = field_match.group(2).strip()

                if field_name.startswith('_') or field_name in ['Config', 'class']:
                    break

                fields[field_name] = field_type

            if fields:
                self.schemas[schema_name] = {
                    "type": "object",
                    "properties": fields,
                    "source": str(file_path.relative_to(self.project_path)),
                }

    async def _detect_spring_endpoints(self):
        """Parse Spring Boot/MVC endpoints"""
        java_files = list(self.backend_path.rglob("*.java"))

        # Patterns for Spring annotations
        mapping_patterns = [
            # @GetMapping("/path"), @PostMapping, etc.
            r'@(Get|Post|Put|Delete|Patch)Mapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']',
            r'@(Get|Post|Put|Delete|Patch)Mapping\s*\(\s*\)',  # No path
            # @RequestMapping(value = "/path", method = RequestMethod.GET)
            r'@RequestMapping\s*\([^)]*value\s*=\s*["\']([^"\']+)["\'][^)]*method\s*=\s*RequestMethod\.(\w+)',
            r'@RequestMapping\s*\([^)]*["\']([^"\']+)["\']',  # Just path
        ]

        # Pattern for method definition
        method_pattern = r'(?:public|private|protected)\s+(?:ResponseEntity<([^>]+)>|(\w+))\s+(\w+)\s*\(([^)]*)\)'

        for java_file in java_files:
            try:
                content = java_file.read_text(encoding='utf-8', errors='ignore')

                # Get class-level @RequestMapping prefix
                class_prefix = ""
                class_mapping = re.search(r'@RequestMapping\s*\(\s*["\']([^"\']+)["\']', content)
                if class_mapping:
                    class_prefix = class_mapping.group(1)

                lines = content.split('\n')

                for i, line in enumerate(lines):
                    for pattern in mapping_patterns:
                        match = re.search(pattern, line)
                        if match:
                            groups = match.groups()

                            # Determine method and path based on pattern
                            if 'RequestMethod' in pattern:
                                path = groups[0]
                                method_str = groups[1]
                            elif len(groups) == 2:
                                method_str = groups[0]
                                path = groups[1]
                            elif len(groups) == 1:
                                method_str = groups[0]
                                path = ""
                            else:
                                continue

                            # Find method definition
                            func_name = "unknown"
                            response_type = None
                            request_body = None
                            params = []

                            for j in range(i + 1, min(i + 10, len(lines))):
                                method_match = re.search(method_pattern, lines[j])
                                if method_match:
                                    response_type = method_match.group(1) or method_match.group(2)
                                    func_name = method_match.group(3)
                                    params_str = method_match.group(4)

                                    params, request_body = self._parse_spring_params(params_str)
                                    break

                            # Build full path
                            full_path = class_prefix + path
                            if not full_path.startswith('/'):
                                full_path = '/' + full_path

                            try:
                                http_method = HttpMethod(method_str.upper())
                            except ValueError:
                                continue

                            # Check for auth
                            auth_required = self._check_spring_auth(content, i)

                            endpoint = Endpoint(
                                path=full_path,
                                method=http_method,
                                name=func_name,
                                response_type=response_type,
                                request_body=request_body,
                                params=params,
                                auth_required=auth_required,
                                source_file=str(java_file.relative_to(self.project_path)),
                            )
                            self.endpoints.append(endpoint)

                # Detect DTOs
                self._detect_java_dtos(content, java_file)

            except Exception as e:
                logger.debug(f"[EndpointDetector] Error parsing {java_file}: {e}")

    def _parse_spring_params(self, params_str: str) -> Tuple[List[EndpointParam], Optional[str]]:
        """Parse Spring method parameters"""
        params = []
        request_body = None

        # Look for @PathVariable, @RequestParam, @RequestBody
        path_var_pattern = r'@PathVariable(?:\s*\([^)]*\))?\s+(\w+)\s+(\w+)'
        query_param_pattern = r'@RequestParam(?:\s*\([^)]*\))?\s+(\w+)\s+(\w+)'
        body_pattern = r'@RequestBody\s+(\w+)'

        for match in re.finditer(path_var_pattern, params_str):
            params.append(EndpointParam(
                name=match.group(2),
                param_type="path",
                data_type=match.group(1).lower(),
            ))

        for match in re.finditer(query_param_pattern, params_str):
            params.append(EndpointParam(
                name=match.group(2),
                param_type="query",
                data_type=match.group(1).lower(),
            ))

        body_match = re.search(body_pattern, params_str)
        if body_match:
            request_body = body_match.group(1)

        return params, request_body

    def _check_spring_auth(self, content: str, line_num: int) -> bool:
        """Check if Spring endpoint requires auth"""
        auth_patterns = [
            r'@PreAuthorize',
            r'@Secured',
            r'@RolesAllowed',
            r'SecurityContextHolder',
        ]

        lines = content.split('\n')
        start = max(0, line_num - 5)
        end = min(len(lines), line_num + 5)
        context = '\n'.join(lines[start:end])

        return any(re.search(p, context) for p in auth_patterns)

    def _detect_java_dtos(self, content: str, file_path: Path):
        """Detect Java DTO classes"""
        # Look for classes with DTO, Request, Response in name
        dto_pattern = r'(?:public\s+)?class\s+(\w+(?:DTO|Request|Response|Entity))\s*(?:extends|implements|{)'

        for match in re.finditer(dto_pattern, content):
            dto_name = match.group(1)
            fields = {}

            # Extract fields
            field_pattern = r'private\s+(\w+(?:<[^>]+>)?)\s+(\w+)\s*;'
            for field_match in re.finditer(field_pattern, content):
                field_type = field_match.group(1)
                field_name = field_match.group(2)
                fields[field_name] = field_type

            if fields:
                self.schemas[dto_name] = {
                    "type": "object",
                    "properties": fields,
                    "source": str(file_path.relative_to(self.project_path)),
                }

    async def _detect_express_endpoints(self):
        """Parse Express.js endpoints"""
        js_files = list(self.backend_path.rglob("*.js")) + list(self.backend_path.rglob("*.ts"))

        # Patterns for Express routes
        route_patterns = [
            # app.get('/path', handler) or router.get('/path', handler)
            r'(?:app|router|api)\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']',
            # Route definition: route('/path').get().post()
            r'\.route\s*\(\s*["\']([^"\']+)["\'].*?\.(get|post|put|patch|delete)',
        ]

        for js_file in js_files:
            try:
                content = js_file.read_text(encoding='utf-8', errors='ignore')

                # Get router prefix if using express.Router()
                router_prefix = ""
                prefix_match = re.search(r'app\.use\s*\(\s*["\']([^"\']+)["\'].*?router', content)
                if prefix_match:
                    router_prefix = prefix_match.group(1)

                for pattern in route_patterns:
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        if 'route' in pattern:
                            path = match.group(1)
                            method_str = match.group(2)
                        else:
                            method_str = match.group(1)
                            path = match.group(2)

                        # Extract path parameters
                        params = []
                        path_params = re.findall(r':(\w+)', path)
                        for param in path_params:
                            params.append(EndpointParam(
                                name=param,
                                param_type="path",
                                data_type="string",
                            ))

                        # Determine if body is expected
                        request_body = None
                        if method_str.lower() in ['post', 'put', 'patch']:
                            request_body = "RequestBody"

                        full_path = router_prefix + path
                        if not full_path.startswith('/'):
                            full_path = '/' + full_path

                        try:
                            http_method = HttpMethod(method_str.upper())
                        except ValueError:
                            continue

                        # Check for auth middleware
                        auth_required = self._check_express_auth(content, match.start())

                        endpoint = Endpoint(
                            path=full_path,
                            method=http_method,
                            name=self._path_to_func_name(path, method_str),
                            params=params,
                            request_body=request_body,
                            auth_required=auth_required,
                            source_file=str(js_file.relative_to(self.project_path)),
                        )
                        self.endpoints.append(endpoint)

            except Exception as e:
                logger.debug(f"[EndpointDetector] Error parsing {js_file}: {e}")

    def _check_express_auth(self, content: str, position: int) -> bool:
        """Check if Express route has auth middleware"""
        # Look for auth middleware in the route
        line_start = content.rfind('\n', 0, position) + 1
        line_end = content.find('\n', position)
        line = content[line_start:line_end]

        auth_patterns = ['auth', 'authenticate', 'protect', 'verify', 'jwt', 'bearer']
        return any(p in line.lower() for p in auth_patterns)

    async def _detect_django_endpoints(self):
        """Parse Django REST Framework endpoints"""
        python_files = list(self.backend_path.rglob("*.py"))

        for py_file in python_files:
            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore')

                # Detect URL patterns from urls.py
                if 'urls.py' in str(py_file):
                    self._parse_django_urls(content, py_file)

                # Detect ViewSet actions
                self._parse_django_viewsets(content, py_file)

            except Exception as e:
                logger.debug(f"[EndpointDetector] Error parsing {py_file}: {e}")

    def _parse_django_urls(self, content: str, file_path: Path):
        """Parse Django URL patterns"""
        # path('api/users/', views.UserList.as_view())
        url_pattern = r"path\s*\(\s*['\"]([^'\"]+)['\"].*?(?:(\w+)\.as_view|(\w+))"

        for match in re.finditer(url_pattern, content):
            path = '/' + match.group(1).rstrip('/')
            view_name = match.group(2) or match.group(3)

            # Infer method from view name
            method = HttpMethod.GET
            if 'create' in view_name.lower() or 'post' in view_name.lower():
                method = HttpMethod.POST
            elif 'update' in view_name.lower() or 'put' in view_name.lower():
                method = HttpMethod.PUT
            elif 'delete' in view_name.lower() or 'destroy' in view_name.lower():
                method = HttpMethod.DELETE

            # Extract path parameters
            params = []
            param_matches = re.findall(r'<(?:\w+:)?(\w+)>', path)
            for param in param_matches:
                params.append(EndpointParam(
                    name=param,
                    param_type="path",
                    data_type="string",
                ))

            endpoint = Endpoint(
                path=path,
                method=method,
                name=view_name,
                params=params,
                source_file=str(file_path.relative_to(self.project_path)),
            )
            self.endpoints.append(endpoint)

    def _parse_django_viewsets(self, content: str, file_path: Path):
        """Parse Django REST ViewSet classes"""
        # Detect ModelViewSet which auto-generates CRUD
        viewset_pattern = r'class\s+(\w+)\s*\(\s*(?:viewsets\.)?ModelViewSet\s*\)'

        for match in re.finditer(viewset_pattern, content):
            viewset_name = match.group(1)
            base_name = viewset_name.replace('ViewSet', '').lower()
            base_path = f'/api/{base_name}s'

            # ModelViewSet creates: list, create, retrieve, update, destroy
            actions = [
                (base_path, HttpMethod.GET, f"list_{base_name}s"),
                (base_path, HttpMethod.POST, f"create_{base_name}"),
                (f"{base_path}/{{id}}", HttpMethod.GET, f"get_{base_name}"),
                (f"{base_path}/{{id}}", HttpMethod.PUT, f"update_{base_name}"),
                (f"{base_path}/{{id}}", HttpMethod.DELETE, f"delete_{base_name}"),
            ]

            for path, method, name in actions:
                endpoint = Endpoint(
                    path=path,
                    method=method,
                    name=name,
                    source_file=str(file_path.relative_to(self.project_path)),
                )
                self.endpoints.append(endpoint)

    async def _detect_flask_endpoints(self):
        """Parse Flask endpoints"""
        python_files = list(self.backend_path.rglob("*.py"))

        # Pattern for Flask routes
        route_pattern = r'@(?:app|bp|blueprint)\.route\s*\(\s*["\']([^"\']+)["\'](?:.*?methods\s*=\s*\[([^\]]+)\])?'

        for py_file in python_files:
            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')

                for i, line in enumerate(lines):
                    match = re.search(route_pattern, line, re.IGNORECASE)
                    if match:
                        path = match.group(1)
                        methods_str = match.group(2)

                        if methods_str:
                            methods = re.findall(r'["\'](\w+)["\']', methods_str)
                        else:
                            methods = ['GET']

                        # Find function name
                        func_name = "unknown"
                        for j in range(i + 1, min(i + 3, len(lines))):
                            func_match = re.search(r'def\s+(\w+)\s*\(', lines[j])
                            if func_match:
                                func_name = func_match.group(1)
                                break

                        # Extract path parameters
                        params = []
                        param_matches = re.findall(r'<(?:\w+:)?(\w+)>', path)
                        for param in param_matches:
                            params.append(EndpointParam(
                                name=param,
                                param_type="path",
                                data_type="string",
                            ))

                        for method in methods:
                            try:
                                http_method = HttpMethod(method.upper())
                            except ValueError:
                                continue

                            endpoint = Endpoint(
                                path=path,
                                method=http_method,
                                name=func_name,
                                params=params,
                                source_file=str(py_file.relative_to(self.project_path)),
                            )
                            self.endpoints.append(endpoint)

            except Exception as e:
                logger.debug(f"[EndpointDetector] Error parsing {py_file}: {e}")

    def _normalize_endpoints(self):
        """Normalize endpoint paths and remove duplicates"""
        seen = set()
        unique_endpoints = []

        for ep in self.endpoints:
            # Normalize path
            ep.path = ep.path.replace('//', '/')
            if not ep.path.startswith('/'):
                ep.path = '/' + ep.path

            # Convert path params to consistent format
            ep.path = re.sub(r':(\w+)', r'{\1}', ep.path)  # :id -> {id}
            ep.path = re.sub(r'<(?:\w+:)?(\w+)>', r'{\1}', ep.path)  # <int:id> -> {id}

            # Remove duplicates
            key = (ep.path, ep.method)
            if key not in seen:
                seen.add(key)
                unique_endpoints.append(ep)

        self.endpoints = unique_endpoints

    def _detect_base_path(self) -> str:
        """Detect common base path for all endpoints"""
        if not self.endpoints:
            return "/api"

        paths = [ep.path for ep in self.endpoints]

        # Find common prefix
        if len(paths) == 1:
            return "/api"

        common = paths[0]
        for path in paths[1:]:
            while not path.startswith(common):
                common = common.rsplit('/', 1)[0]
                if not common:
                    return "/api"

        return common if common else "/api"

    def _detect_auth_type(self) -> str:
        """Detect authentication type used"""
        # Check requirements/dependencies
        files_to_check = list(self.backend_path.rglob("*.py")) + \
                        list(self.backend_path.rglob("*.java")) + \
                        list(self.backend_path.rglob("*.js")) + \
                        list(self.backend_path.rglob("*.ts"))

        jwt_indicators = ['jwt', 'jsonwebtoken', 'pyjwt', 'jjwt']
        oauth_indicators = ['oauth', 'oauth2']
        session_indicators = ['session', 'cookie']

        for f in files_to_check[:20]:  # Check first 20 files
            try:
                content = f.read_text(encoding='utf-8', errors='ignore').lower()

                if any(ind in content for ind in jwt_indicators):
                    return "jwt"
                if any(ind in content for ind in oauth_indicators):
                    return "oauth2"
                if any(ind in content for ind in session_indicators):
                    return "session"
            except (IOError, OSError) as e:
                logger.debug(f"Could not read file for auth type detection: {e}")

        return "none"

    def _path_to_func_name(self, path: str, method: str) -> str:
        """Convert path to function name"""
        # /api/users/:id -> getUserById
        parts = path.strip('/').split('/')
        parts = [p for p in parts if not p.startswith(':') and not p.startswith('{')]

        if not parts:
            return method.lower()

        resource = parts[-1]

        method_prefixes = {
            'get': 'get',
            'post': 'create',
            'put': 'update',
            'patch': 'update',
            'delete': 'delete',
        }

        prefix = method_prefixes.get(method.lower(), method.lower())
        return f"{prefix}{resource.title()}"


async def detect_endpoints(project_path: Path) -> Dict[str, Any]:
    """
    Convenience function to detect endpoints.

    Usage:
        result = await detect_endpoints(Path("/path/to/project"))
        endpoints = result["endpoints"]
    """
    detector = EndpointDetector(project_path)
    return await detector.detect()
