"""
API Service Generator - Generates typed frontend API service from detected backend endpoints

This service creates:
1. TypeScript API service file with axios/fetch configuration
2. TypeScript interfaces for request/response types
3. Typed API methods for each endpoint
4. Proper error handling and auth token management

Supports generating for:
- React + Vite (axios)
- React + CRA (axios)
- Next.js (fetch)
- Vue.js (axios)
- Angular (HttpClient)
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.logging_config import logger
from app.services.endpoint_detector import Endpoint, EndpointParam, HttpMethod


class APIServiceGenerator:
    """
    Generates typed frontend API service from detected backend endpoints.

    Usage:
        generator = APIServiceGenerator(
            frontend_path=Path("/project/frontend"),
            endpoints=detected_endpoints,
            schemas=detected_schemas,
            backend_port=4000
        )
        await generator.generate()
    """

    def __init__(
        self,
        frontend_path: Path,
        endpoints: List[Dict[str, Any]],
        schemas: Dict[str, Dict[str, Any]],
        backend_port: int = 4000,
        frontend_type: str = "vite"
    ):
        self.frontend_path = Path(frontend_path)
        self.endpoints = [self._dict_to_endpoint(ep) for ep in endpoints]
        self.schemas = schemas
        self.backend_port = backend_port
        self.frontend_type = frontend_type

    def _dict_to_endpoint(self, ep_dict: Dict[str, Any]) -> Endpoint:
        """Convert dictionary back to Endpoint object"""
        params = [
            EndpointParam(
                name=p["name"],
                param_type=p["param_type"],
                data_type=p["data_type"],
                required=p.get("required", True),
                description=p.get("description", ""),
            )
            for p in ep_dict.get("params", [])
        ]

        return Endpoint(
            path=ep_dict["path"],
            method=HttpMethod(ep_dict["method"]),
            name=ep_dict["name"],
            description=ep_dict.get("description", ""),
            request_body=ep_dict.get("request_body"),
            response_type=ep_dict.get("response_type"),
            params=params,
            auth_required=ep_dict.get("auth_required", False),
            tags=ep_dict.get("tags", []),
            source_file=ep_dict.get("source_file", ""),
        )

    async def generate(self) -> Dict[str, Any]:
        """
        Generate the API service files.

        Returns:
            Dict with generated files and status
        """
        result = {
            "success": True,
            "files_created": [],
            "errors": [],
        }

        try:
            # 1. Generate TypeScript interfaces
            interfaces_content = self._generate_interfaces()
            interfaces_path = self.frontend_path / "src" / "types" / "api.types.ts"
            interfaces_path.parent.mkdir(parents=True, exist_ok=True)
            interfaces_path.write_text(interfaces_content)
            result["files_created"].append(str(interfaces_path))
            logger.info(f"[APIServiceGenerator] Created {interfaces_path}")

            # 2. Generate API service based on frontend type
            if self.frontend_type in ["vite", "cra", "react"]:
                api_content = self._generate_axios_service()
            elif self.frontend_type == "nextjs":
                api_content = self._generate_fetch_service()
            else:
                api_content = self._generate_axios_service()

            api_path = self.frontend_path / "src" / "services" / "api.ts"
            api_path.parent.mkdir(parents=True, exist_ok=True)
            api_path.write_text(api_content)
            result["files_created"].append(str(api_path))
            logger.info(f"[APIServiceGenerator] Created {api_path}")

            # 3. Generate individual API modules for each resource
            resource_apis = self._generate_resource_apis()
            for resource_name, content in resource_apis.items():
                resource_path = self.frontend_path / "src" / "services" / f"{resource_name}.api.ts"
                resource_path.write_text(content)
                result["files_created"].append(str(resource_path))
                logger.info(f"[APIServiceGenerator] Created {resource_path}")

            # 4. Generate API hooks for React
            if self.frontend_type in ["vite", "cra", "react", "nextjs"]:
                hooks_content = self._generate_react_hooks()
                hooks_path = self.frontend_path / "src" / "hooks" / "useApi.ts"
                hooks_path.parent.mkdir(parents=True, exist_ok=True)
                hooks_path.write_text(hooks_content)
                result["files_created"].append(str(hooks_path))
                logger.info(f"[APIServiceGenerator] Created {hooks_path}")

        except Exception as e:
            logger.error(f"[APIServiceGenerator] Error: {e}")
            result["success"] = False
            result["errors"].append(str(e))

        return result

    def _generate_interfaces(self) -> str:
        """Generate TypeScript interfaces from schemas"""
        lines = [
            "/**",
            " * Auto-generated API Types",
            f" * Generated: {datetime.now().isoformat()}",
            " * DO NOT EDIT MANUALLY - Regenerate from backend endpoints",
            " */",
            "",
        ]

        # Generate interfaces from schemas
        for schema_name, schema_def in self.schemas.items():
            lines.append(f"export interface {schema_name} {{")

            properties = schema_def.get("properties", {})
            for prop_name, prop_type in properties.items():
                ts_type = self._java_to_ts_type(prop_type)
                lines.append(f"  {prop_name}: {ts_type};")

            lines.append("}")
            lines.append("")

        # Generate interfaces from endpoints
        generated_types = set(self.schemas.keys())

        for endpoint in self.endpoints:
            # Request body type
            if endpoint.request_body and endpoint.request_body not in generated_types:
                lines.append(f"export interface {endpoint.request_body} {{")
                lines.append("  // TODO: Define request body fields")
                lines.append("  [key: string]: unknown;")
                lines.append("}")
                lines.append("")
                generated_types.add(endpoint.request_body)

            # Response type
            if endpoint.response_type and endpoint.response_type not in generated_types:
                lines.append(f"export interface {endpoint.response_type} {{")
                lines.append("  // TODO: Define response fields")
                lines.append("  [key: string]: unknown;")
                lines.append("}")
                lines.append("")
                generated_types.add(endpoint.response_type)

        # Common types
        lines.extend([
            "// Common API types",
            "export interface ApiResponse<T> {",
            "  data: T;",
            "  message?: string;",
            "  success: boolean;",
            "}",
            "",
            "export interface PaginatedResponse<T> {",
            "  data: T[];",
            "  total: number;",
            "  page: number;",
            "  pageSize: number;",
            "  totalPages: number;",
            "}",
            "",
            "export interface ApiError {",
            "  message: string;",
            "  code?: string;",
            "  details?: Record<string, string[]>;",
            "}",
            "",
        ])

        return "\n".join(lines)

    def _java_to_ts_type(self, java_type: str) -> str:
        """Convert Java/Python type to TypeScript type"""
        type_map = {
            "string": "string",
            "str": "string",
            "String": "string",
            "int": "number",
            "Integer": "number",
            "long": "number",
            "Long": "number",
            "float": "number",
            "Float": "number",
            "double": "number",
            "Double": "number",
            "boolean": "boolean",
            "Boolean": "boolean",
            "bool": "boolean",
            "List": "Array",
            "Set": "Array",
            "Map": "Record",
            "Dict": "Record",
            "dict": "Record<string, unknown>",
            "Any": "unknown",
            "any": "unknown",
            "None": "null",
            "void": "void",
            "LocalDateTime": "string",
            "LocalDate": "string",
            "Date": "string",
            "datetime": "string",
            "UUID": "string",
            "uuid": "string",
        }

        # Handle generic types like List<String>
        generic_match = re.match(r'(\w+)<(.+)>', java_type)
        if generic_match:
            container = generic_match.group(1)
            inner = generic_match.group(2)
            inner_ts = self._java_to_ts_type(inner)

            if container in ["List", "Set", "ArrayList", "list"]:
                return f"{inner_ts}[]"
            elif container in ["Map", "HashMap", "dict", "Dict"]:
                parts = inner.split(',')
                if len(parts) == 2:
                    key_type = self._java_to_ts_type(parts[0].strip())
                    val_type = self._java_to_ts_type(parts[1].strip())
                    return f"Record<{key_type}, {val_type}>"

        # Handle Optional
        if java_type.startswith("Optional"):
            inner_match = re.search(r'Optional\[(.+)\]', java_type)
            if inner_match:
                return f"{self._java_to_ts_type(inner_match.group(1))} | null"

        return type_map.get(java_type, java_type)

    def _generate_axios_service(self) -> str:
        """Generate axios-based API service"""
        return f'''/**
 * Auto-generated API Service
 * Generated: {datetime.now().isoformat()}
 *
 * This file provides a configured axios instance and API methods
 * for all detected backend endpoints.
 */

import axios, {{ AxiosInstance, AxiosResponse, AxiosError, InternalAxiosRequestConfig }} from 'axios';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

// Create axios instance with default config
const api: AxiosInstance = axios.create({{
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {{
    'Content-Type': 'application/json',
  }},
}});

// Request interceptor - Add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {{
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    if (token && config.headers) {{
      config.headers.Authorization = `Bearer ${{token}}`;
    }}
    return config;
  }},
  (error: AxiosError) => {{
    return Promise.reject(error);
  }}
);

// Response interceptor - Handle errors
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {{
    if (error.response?.status === 401) {{
      // Token expired or invalid
      localStorage.removeItem('token');
      sessionStorage.removeItem('token');

      // Redirect to login if not already there
      if (window.location.pathname !== '/login') {{
        window.location.href = '/login';
      }}
    }}
    return Promise.reject(error);
  }}
);

// Export the configured instance
export default api;

// Export base URL for reference
export const API_URL = API_BASE_URL;

{self._generate_api_methods()}
'''

    def _generate_fetch_service(self) -> str:
        """Generate fetch-based API service for Next.js"""
        return f'''/**
 * Auto-generated API Service (Next.js)
 * Generated: {datetime.now().isoformat()}
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

interface RequestConfig extends RequestInit {{
  params?: Record<string, string>;
}}

class ApiClient {{
  private baseUrl: string;

  constructor(baseUrl: string) {{
    this.baseUrl = baseUrl;
  }}

  private getAuthHeaders(): HeadersInit {{
    const token = typeof window !== 'undefined'
      ? localStorage.getItem('token')
      : null;

    return token ? {{ Authorization: `Bearer ${{token}}` }} : {{}};
  }}

  private buildUrl(path: string, params?: Record<string, string>): string {{
    const url = new URL(path, this.baseUrl);
    if (params) {{
      Object.entries(params).forEach(([key, value]) => {{
        url.searchParams.append(key, value);
      }});
    }}
    return url.toString();
  }}

  async request<T>(path: string, config: RequestConfig = {{}}): Promise<T> {{
    const {{ params, ...fetchConfig }} = config;

    const response = await fetch(this.buildUrl(path, params), {{
      ...fetchConfig,
      headers: {{
        'Content-Type': 'application/json',
        ...this.getAuthHeaders(),
        ...fetchConfig.headers,
      }},
    }});

    if (!response.ok) {{
      if (response.status === 401) {{
        if (typeof window !== 'undefined') {{
          localStorage.removeItem('token');
          window.location.href = '/login';
        }}
      }}
      throw new Error(`API Error: ${{response.status}}`);
    }}

    return response.json();
  }}

  get<T>(path: string, params?: Record<string, string>): Promise<T> {{
    return this.request<T>(path, {{ method: 'GET', params }});
  }}

  post<T>(path: string, data?: unknown): Promise<T> {{
    return this.request<T>(path, {{
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }});
  }}

  put<T>(path: string, data?: unknown): Promise<T> {{
    return this.request<T>(path, {{
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }});
  }}

  patch<T>(path: string, data?: unknown): Promise<T> {{
    return this.request<T>(path, {{
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    }});
  }}

  delete<T>(path: string): Promise<T> {{
    return this.request<T>(path, {{ method: 'DELETE' }});
  }}
}}

const api = new ApiClient(API_BASE_URL);
export default api;

{self._generate_api_methods(use_fetch=True)}
'''

    def _generate_api_methods(self, use_fetch: bool = False) -> str:
        """Generate API methods for all endpoints"""
        lines = [
            "",
            "// ============================================",
            "// Auto-generated API Methods",
            "// ============================================",
            "",
        ]

        # Group endpoints by resource
        resources: Dict[str, List[Endpoint]] = {}
        for endpoint in self.endpoints:
            resource = self._get_resource_name(endpoint.path)
            if resource not in resources:
                resources[resource] = []
            resources[resource].append(endpoint)

        # Generate methods for each resource
        for resource_name, endpoints in resources.items():
            lines.append(f"// ----- {resource_name.title()} API -----")
            lines.append(f"export const {resource_name}Api = {{")

            for endpoint in endpoints:
                method_name = self._endpoint_to_method_name(endpoint)
                method_code = self._generate_method(endpoint, use_fetch)
                lines.append(f"  {method_name}: {method_code},")
                lines.append("")

            lines.append("};")
            lines.append("")

        return "\n".join(lines)

    def _generate_method(self, endpoint: Endpoint, use_fetch: bool = False) -> str:
        """Generate a single API method"""
        # Build path with params
        path = endpoint.path

        # Collect parameters
        path_params = [p for p in endpoint.params if p.param_type == "path"]
        query_params = [p for p in endpoint.params if p.param_type == "query"]

        # Build function signature
        params = []
        for p in path_params:
            ts_type = self._java_to_ts_type(p.data_type)
            params.append(f"{p.name}: {ts_type}")

        if endpoint.request_body:
            params.append(f"data: {endpoint.request_body}")
        elif endpoint.method in [HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH]:
            params.append("data: Record<string, unknown>")

        if query_params:
            query_type = ", ".join([f"{p.name}?: {self._java_to_ts_type(p.data_type)}" for p in query_params])
            params.append(f"params?: {{ {query_type} }}")

        params_str = ", ".join(params)

        # Build path string
        path_str = path
        for p in path_params:
            path_str = path_str.replace(f"{{{p.name}}}", f"${{{p.name}}}")

        # Response type
        response_type = endpoint.response_type or "unknown"

        # Generate method body based on HTTP method
        if use_fetch:
            if endpoint.method == HttpMethod.GET:
                if query_params:
                    return f"async ({params_str}) => api.get<{response_type}>(`{path_str}`, params)"
                return f"async ({params_str}) => api.get<{response_type}>(`{path_str}`)"
            elif endpoint.method == HttpMethod.POST:
                return f"async ({params_str}) => api.post<{response_type}>(`{path_str}`, data)"
            elif endpoint.method == HttpMethod.PUT:
                return f"async ({params_str}) => api.put<{response_type}>(`{path_str}`, data)"
            elif endpoint.method == HttpMethod.PATCH:
                return f"async ({params_str}) => api.patch<{response_type}>(`{path_str}`, data)"
            elif endpoint.method == HttpMethod.DELETE:
                return f"async ({params_str}) => api.delete<{response_type}>(`{path_str}`)"
        else:
            if endpoint.method == HttpMethod.GET:
                if query_params:
                    return f"({params_str}) => api.get<{response_type}>(`{path_str}`, {{ params }})"
                return f"({params_str}) => api.get<{response_type}>(`{path_str}`)"
            elif endpoint.method == HttpMethod.POST:
                return f"({params_str}) => api.post<{response_type}>(`{path_str}`, data)"
            elif endpoint.method == HttpMethod.PUT:
                return f"({params_str}) => api.put<{response_type}>(`{path_str}`, data)"
            elif endpoint.method == HttpMethod.PATCH:
                return f"({params_str}) => api.patch<{response_type}>(`{path_str}`, data)"
            elif endpoint.method == HttpMethod.DELETE:
                return f"({params_str}) => api.delete<{response_type}>(`{path_str}`)"

        return "() => Promise.resolve()"

    def _generate_resource_apis(self) -> Dict[str, str]:
        """Generate separate API files for each resource"""
        resources: Dict[str, List[Endpoint]] = {}

        for endpoint in self.endpoints:
            resource = self._get_resource_name(endpoint.path)
            if resource not in resources:
                resources[resource] = []
            resources[resource].append(endpoint)

        result = {}

        for resource_name, endpoints in resources.items():
            lines = [
                f"/**",
                f" * {resource_name.title()} API",
                f" * Auto-generated from backend endpoints",
                f" */",
                "",
                "import api from './api';",
                "",
            ]

            # Generate types
            types_needed = set()
            for ep in endpoints:
                if ep.request_body:
                    types_needed.add(ep.request_body)
                if ep.response_type:
                    types_needed.add(ep.response_type)

            if types_needed:
                lines.append(f"import type {{ {', '.join(types_needed)} }} from '../types/api.types';")
                lines.append("")

            lines.append(f"export const {resource_name}Api = {{")

            for endpoint in endpoints:
                method_name = self._endpoint_to_method_name(endpoint)
                method_code = self._generate_method(endpoint)

                # Add JSDoc comment
                lines.append(f"  /**")
                lines.append(f"   * {endpoint.method.value} {endpoint.path}")
                if endpoint.auth_required:
                    lines.append(f"   * @requires Authentication")
                lines.append(f"   */")
                lines.append(f"  {method_name}: {method_code},")
                lines.append("")

            lines.append("};")
            lines.append("")
            lines.append(f"export default {resource_name}Api;")

            result[resource_name] = "\n".join(lines)

        return result

    def _generate_react_hooks(self) -> str:
        """Generate React hooks for API calls"""
        resources: Dict[str, List[Endpoint]] = {}

        for endpoint in self.endpoints:
            resource = self._get_resource_name(endpoint.path)
            if resource not in resources:
                resources[resource] = []
            resources[resource].append(endpoint)

        lines = [
            "/**",
            " * Auto-generated React API Hooks",
            " * Provides hooks for data fetching with loading/error states",
            " */",
            "",
            "import { useState, useEffect, useCallback } from 'react';",
            "import api from '../services/api';",
            "",
            "interface UseApiState<T> {",
            "  data: T | null;",
            "  loading: boolean;",
            "  error: Error | null;",
            "  refetch: () => Promise<void>;",
            "}",
            "",
            "interface UseMutationState<T> {",
            "  data: T | null;",
            "  loading: boolean;",
            "  error: Error | null;",
            "  mutate: (...args: unknown[]) => Promise<T>;",
            "  reset: () => void;",
            "}",
            "",
            "/**",
            " * Generic hook for GET requests with auto-fetch",
            " */",
            "export function useQuery<T>(url: string, options?: { enabled?: boolean }): UseApiState<T> {",
            "  const [data, setData] = useState<T | null>(null);",
            "  const [loading, setLoading] = useState(true);",
            "  const [error, setError] = useState<Error | null>(null);",
            "",
            "  const fetchData = useCallback(async () => {",
            "    if (options?.enabled === false) return;",
            "    ",
            "    setLoading(true);",
            "    setError(null);",
            "    try {",
            "      const response = await api.get<T>(url);",
            "      setData(response.data);",
            "    } catch (err) {",
            "      setError(err instanceof Error ? err : new Error('Unknown error'));",
            "    } finally {",
            "      setLoading(false);",
            "    }",
            "  }, [url, options?.enabled]);",
            "",
            "  useEffect(() => {",
            "    fetchData();",
            "  }, [fetchData]);",
            "",
            "  return { data, loading, error, refetch: fetchData };",
            "}",
            "",
            "/**",
            " * Generic hook for mutations (POST, PUT, DELETE)",
            " */",
            "export function useMutation<T, V = unknown>(",
            "  mutationFn: (variables: V) => Promise<{ data: T }>",
            "): UseMutationState<T> {",
            "  const [data, setData] = useState<T | null>(null);",
            "  const [loading, setLoading] = useState(false);",
            "  const [error, setError] = useState<Error | null>(null);",
            "",
            "  const mutate = useCallback(async (variables: V): Promise<T> => {",
            "    setLoading(true);",
            "    setError(null);",
            "    try {",
            "      const response = await mutationFn(variables);",
            "      setData(response.data);",
            "      return response.data;",
            "    } catch (err) {",
            "      const error = err instanceof Error ? err : new Error('Unknown error');",
            "      setError(error);",
            "      throw error;",
            "    } finally {",
            "      setLoading(false);",
            "    }",
            "  }, [mutationFn]) as (...args: unknown[]) => Promise<T>;",
            "",
            "  const reset = useCallback(() => {",
            "    setData(null);",
            "    setError(null);",
            "    setLoading(false);",
            "  }, []);",
            "",
            "  return { data, loading, error, mutate, reset };",
            "}",
            "",
        ]

        # Generate specific hooks for each resource
        for resource_name, endpoints in resources.items():
            lines.append(f"// ----- {resource_name.title()} Hooks -----")
            lines.append("")

            for endpoint in endpoints:
                if endpoint.method == HttpMethod.GET:
                    # Generate useQuery hook
                    hook_name = f"use{self._to_pascal_case(endpoint.name)}"
                    path_params = [p for p in endpoint.params if p.param_type == "path"]

                    if path_params:
                        params_def = ", ".join([f"{p.name}: {self._java_to_ts_type(p.data_type)}" for p in path_params])
                        path_build = endpoint.path
                        for p in path_params:
                            path_build = path_build.replace(f"{{{p.name}}}", f"${{{p.name}}}")

                        lines.extend([
                            f"export function {hook_name}({params_def}) {{",
                            f"  return useQuery<unknown>(`{path_build}`);",
                            "}",
                            "",
                        ])
                    else:
                        lines.extend([
                            f"export function {hook_name}() {{",
                            f"  return useQuery<unknown>('{endpoint.path}');",
                            "}",
                            "",
                        ])

        return "\n".join(lines)

    def _get_resource_name(self, path: str) -> str:
        """Extract resource name from path"""
        # /api/users/{id} -> users
        # /api/v1/products -> products
        parts = path.strip('/').split('/')

        # Remove common prefixes
        if parts and parts[0] in ['api', 'v1', 'v2']:
            parts = parts[1:]
        if parts and parts[0] in ['v1', 'v2']:
            parts = parts[1:]

        if parts:
            # Get first non-parameter part
            for part in parts:
                if not part.startswith('{') and not part.startswith(':'):
                    return part.lower()

        return "api"

    def _endpoint_to_method_name(self, endpoint: Endpoint) -> str:
        """Convert endpoint to method name"""
        # GET /users -> getUsers
        # POST /users -> createUser
        # GET /users/{id} -> getUserById
        # PUT /users/{id} -> updateUser
        # DELETE /users/{id} -> deleteUser

        method_prefixes = {
            HttpMethod.GET: "get",
            HttpMethod.POST: "create",
            HttpMethod.PUT: "update",
            HttpMethod.PATCH: "patch",
            HttpMethod.DELETE: "delete",
        }

        prefix = method_prefixes.get(endpoint.method, "")
        resource = self._get_resource_name(endpoint.path)

        # Check if it's a single item or list
        has_id = any(p.param_type == "path" for p in endpoint.params)

        if endpoint.method == HttpMethod.GET:
            if has_id:
                return f"get{self._to_pascal_case(resource)}ById"
            else:
                return f"getAll{self._to_pascal_case(resource)}"
        elif endpoint.method == HttpMethod.POST:
            return f"create{self._to_pascal_case(self._singularize(resource))}"
        elif endpoint.method in [HttpMethod.PUT, HttpMethod.PATCH]:
            return f"update{self._to_pascal_case(self._singularize(resource))}"
        elif endpoint.method == HttpMethod.DELETE:
            return f"delete{self._to_pascal_case(self._singularize(resource))}"

        return endpoint.name

    def _to_pascal_case(self, s: str) -> str:
        """Convert string to PascalCase"""
        return ''.join(word.capitalize() for word in s.replace('-', '_').split('_'))

    def _singularize(self, word: str) -> str:
        """Simple singularization"""
        if word.endswith('ies'):
            return word[:-3] + 'y'
        elif word.endswith('es'):
            return word[:-2]
        elif word.endswith('s') and not word.endswith('ss'):
            return word[:-1]
        return word


async def generate_api_service(
    frontend_path: Path,
    endpoints: List[Dict[str, Any]],
    schemas: Dict[str, Dict[str, Any]],
    backend_port: int = 4000,
    frontend_type: str = "vite"
) -> Dict[str, Any]:
    """
    Convenience function to generate API service.

    Usage:
        result = await generate_api_service(
            frontend_path=Path("/project/frontend"),
            endpoints=detected_endpoints,
            schemas=detected_schemas,
        )
    """
    generator = APIServiceGenerator(
        frontend_path=frontend_path,
        endpoints=endpoints,
        schemas=schemas,
        backend_port=backend_port,
        frontend_type=frontend_type,
    )
    return await generator.generate()
