"""
Fullstack Integration Service - Automatic Frontend-Backend Integration

This service automatically configures frontend-backend communication for fullstack projects:
1. Detects API endpoints in backend
2. Configures frontend API base URL
3. Sets up proxy configuration (Vite/CRA/Next.js)
4. Creates/updates .env files
5. Configures CORS on backend
6. Creates API service files if missing

Supports:
- React + Spring Boot
- React + Express
- React + FastAPI
- React + Django
- Vue + Any Backend
- Angular + Any Backend
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from app.core.logging_config import logger


class FullstackIntegrator:
    """
    Automatically integrates frontend and backend for fullstack projects.

    Usage:
        integrator = FullstackIntegrator(project_path, frontend_port=3000, backend_port=4000)
        await integrator.integrate()
    """

    def __init__(
        self,
        project_path: Path,
        frontend_port: int = 3000,
        backend_port: int = 4000
    ):
        self.project_path = Path(project_path)
        self.frontend_port = frontend_port
        self.backend_port = backend_port
        self.frontend_path = self.project_path / "frontend"
        self.backend_path = self.project_path / "backend"

        # Detect technologies
        self.frontend_type = self._detect_frontend_type()
        self.backend_type = self._detect_backend_type()

    def _detect_frontend_type(self) -> str:
        """Detect frontend framework type"""
        pkg_path = self.frontend_path / "package.json"
        if not pkg_path.exists():
            return "unknown"

        try:
            with open(pkg_path, 'r') as f:
                pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                if "vite" in deps:
                    return "vite"
                elif "react-scripts" in deps:
                    return "cra"
                elif "next" in deps:
                    return "nextjs"
                elif "vue" in deps:
                    return "vue"
                elif "@angular/core" in deps:
                    return "angular"
                else:
                    return "react"
        except:
            return "unknown"

    def _detect_backend_type(self) -> str:
        """Detect backend framework type"""
        # Spring Boot (Java)
        if (self.backend_path / "pom.xml").exists():
            return "spring-maven"
        if (self.backend_path / "build.gradle").exists():
            return "spring-gradle"

        # Python
        if (self.backend_path / "requirements.txt").exists():
            try:
                with open(self.backend_path / "requirements.txt", 'r') as f:
                    content = f.read().lower()
                    if "fastapi" in content:
                        return "fastapi"
                    elif "flask" in content:
                        return "flask"
                    elif "django" in content:
                        return "django"
            except:
                pass
            return "python"

        # Node.js
        if (self.backend_path / "package.json").exists():
            return "express"

        return "unknown"

    async def integrate(self) -> Dict[str, Any]:
        """
        Perform full integration of frontend and backend.
        Returns dict with integration results.
        """
        results = {
            "success": True,
            "frontend_type": self.frontend_type,
            "backend_type": self.backend_type,
            "actions": []
        }

        try:
            # 1. Configure frontend API URL
            api_configured = await self._configure_frontend_api()
            if api_configured:
                results["actions"].append("Configured frontend API base URL")

            # 2. Setup proxy configuration
            proxy_configured = await self._setup_proxy()
            if proxy_configured:
                results["actions"].append("Setup development proxy")

            # 3. Create/update .env files
            env_configured = await self._configure_env_files()
            if env_configured:
                results["actions"].append("Created/updated .env files")

            # 4. Configure CORS on backend
            cors_configured = await self._configure_cors()
            if cors_configured:
                results["actions"].append("Configured CORS on backend")

            # 5. Create API service if missing
            api_service_created = await self._ensure_api_service()
            if api_service_created:
                results["actions"].append("Created API service file")

            logger.info(f"[FullstackIntegrator] Integration complete: {results['actions']}")

        except Exception as e:
            logger.error(f"[FullstackIntegrator] Integration error: {e}")
            results["success"] = False
            results["error"] = str(e)

        return results

    async def _configure_frontend_api(self) -> bool:
        """Configure the API base URL in frontend"""
        api_url = f"http://localhost:{self.backend_port}"

        # Check for existing API config files
        possible_api_files = [
            self.frontend_path / "src" / "services" / "api.ts",
            self.frontend_path / "src" / "services" / "api.js",
            self.frontend_path / "src" / "api" / "index.ts",
            self.frontend_path / "src" / "api" / "index.js",
            self.frontend_path / "src" / "lib" / "api.ts",
            self.frontend_path / "src" / "utils" / "api.ts",
        ]

        for api_file in possible_api_files:
            if api_file.exists():
                try:
                    content = api_file.read_text()
                    # Update API base URL patterns
                    patterns = [
                        (r'baseURL:\s*[\'"]http://localhost:\d+[\'"]', f'baseURL: "{api_url}"'),
                        (r'BASE_URL\s*=\s*[\'"]http://localhost:\d+[\'"]', f'BASE_URL = "{api_url}"'),
                        (r'API_URL\s*=\s*[\'"]http://localhost:\d+[\'"]', f'API_URL = "{api_url}"'),
                        (r'VITE_API_URL\s*=\s*[\'"]http://localhost:\d+[\'"]', f'VITE_API_URL = "{api_url}"'),
                    ]

                    updated = False
                    for pattern, replacement in patterns:
                        if re.search(pattern, content):
                            content = re.sub(pattern, replacement, content)
                            updated = True

                    if updated:
                        api_file.write_text(content)
                        logger.info(f"[FullstackIntegrator] Updated API URL in {api_file}")
                        return True
                except Exception as e:
                    logger.error(f"[FullstackIntegrator] Failed to update {api_file}: {e}")

        return False

    async def _setup_proxy(self) -> bool:
        """Setup development proxy for API requests"""

        if self.frontend_type == "vite":
            return await self._setup_vite_proxy()
        elif self.frontend_type == "cra":
            return await self._setup_cra_proxy()
        elif self.frontend_type == "nextjs":
            return await self._setup_nextjs_proxy()

        return False

    async def _setup_vite_proxy(self) -> bool:
        """Setup Vite proxy configuration"""
        vite_config_files = [
            self.frontend_path / "vite.config.ts",
            self.frontend_path / "vite.config.js",
        ]

        for config_file in vite_config_files:
            if config_file.exists():
                try:
                    content = config_file.read_text()

                    # Check if proxy is already configured - UPDATE the target port
                    if "proxy:" in content or "'/api'" in content:
                        # Update existing proxy target to correct port
                        updated_content = re.sub(
                            r"target:\s*['\"]http://localhost:\d+['\"]",
                            f"target: 'http://localhost:{self.backend_port}'",
                            content
                        )
                        if updated_content != content:
                            config_file.write_text(updated_content)
                            logger.info(f"[FullstackIntegrator] Updated proxy target to port {self.backend_port} in {config_file}")
                            return True
                        else:
                            logger.info(f"[FullstackIntegrator] Proxy already configured correctly in {config_file}")
                            return True

                    # Add proxy configuration
                    proxy_config = f'''
    server: {{
      proxy: {{
        '/api': {{
          target: 'http://localhost:{self.backend_port}',
          changeOrigin: true,
          secure: false,
        }},
      }},
    }},'''

                    # Insert proxy config into defineConfig
                    if "defineConfig({" in content:
                        content = content.replace(
                            "defineConfig({",
                            f"defineConfig({{{proxy_config}"
                        )
                        config_file.write_text(content)
                        logger.info(f"[FullstackIntegrator] Added proxy to {config_file}")
                        return True

                except Exception as e:
                    logger.error(f"[FullstackIntegrator] Failed to setup Vite proxy: {e}")

        return False

    async def _setup_cra_proxy(self) -> bool:
        """Setup Create React App proxy"""
        pkg_path = self.frontend_path / "package.json"

        if pkg_path.exists():
            try:
                with open(pkg_path, 'r') as f:
                    pkg = json.load(f)

                # Add proxy field
                pkg["proxy"] = f"http://localhost:{self.backend_port}"

                with open(pkg_path, 'w') as f:
                    json.dump(pkg, f, indent=2)

                logger.info(f"[FullstackIntegrator] Added proxy to package.json")
                return True

            except Exception as e:
                logger.error(f"[FullstackIntegrator] Failed to setup CRA proxy: {e}")

        return False

    async def _setup_nextjs_proxy(self) -> bool:
        """Setup Next.js rewrites for API proxy"""
        next_config_files = [
            self.frontend_path / "next.config.js",
            self.frontend_path / "next.config.mjs",
            self.frontend_path / "next.config.ts",
        ]

        for config_file in next_config_files:
            if config_file.exists():
                try:
                    content = config_file.read_text()

                    if "rewrites" in content:
                        return True  # Already configured

                    # Add rewrites configuration
                    rewrite_config = f'''
  async rewrites() {{
    return [
      {{
        source: '/api/:path*',
        destination: 'http://localhost:{self.backend_port}/api/:path*',
      }},
    ];
  }},'''

                    if "module.exports = {" in content:
                        content = content.replace(
                            "module.exports = {",
                            f"module.exports = {{{rewrite_config}"
                        )
                        config_file.write_text(content)
                        return True

                except Exception as e:
                    logger.error(f"[FullstackIntegrator] Failed to setup Next.js proxy: {e}")

        return False

    async def _configure_env_files(self) -> bool:
        """Create/update .env files with API URLs"""
        configured = False

        # Frontend .env
        frontend_env = self.frontend_path / ".env"
        env_content = f"""# API Configuration (Auto-generated)
VITE_API_URL=http://localhost:{self.backend_port}
VITE_API_BASE_URL=http://localhost:{self.backend_port}/api
REACT_APP_API_URL=http://localhost:{self.backend_port}
NEXT_PUBLIC_API_URL=http://localhost:{self.backend_port}
"""

        try:
            if frontend_env.exists():
                existing = frontend_env.read_text()
                if "API_URL" not in existing:
                    frontend_env.write_text(existing + "\n" + env_content)
                    configured = True
            else:
                frontend_env.write_text(env_content)
                configured = True
        except Exception as e:
            logger.error(f"[FullstackIntegrator] Failed to create frontend .env: {e}")

        # Backend .env (for CORS origins)
        backend_env = self.backend_path / ".env"
        backend_env_content = f"""# CORS Configuration (Auto-generated)
CORS_ORIGINS=http://localhost:{self.frontend_port},http://127.0.0.1:{self.frontend_port}
FRONTEND_URL=http://localhost:{self.frontend_port}
"""

        try:
            if backend_env.exists():
                existing = backend_env.read_text()
                if "CORS_ORIGINS" not in existing:
                    backend_env.write_text(existing + "\n" + backend_env_content)
                    configured = True
            else:
                backend_env.write_text(backend_env_content)
                configured = True
        except Exception as e:
            logger.error(f"[FullstackIntegrator] Failed to create backend .env: {e}")

        return configured

    async def _configure_cors(self) -> bool:
        """Configure CORS on backend to allow frontend requests"""

        if self.backend_type in ["spring-maven", "spring-gradle"]:
            return await self._configure_spring_cors()
        elif self.backend_type == "fastapi":
            return await self._configure_fastapi_cors()
        elif self.backend_type == "express":
            return await self._configure_express_cors()
        elif self.backend_type == "flask":
            return await self._configure_flask_cors()

        return False

    async def _configure_spring_cors(self) -> bool:
        """Configure CORS for Spring Boot"""
        # Look for existing CORS config
        cors_config_paths = [
            self.backend_path / "src" / "main" / "java" / "**" / "CorsConfig.java",
            self.backend_path / "src" / "main" / "java" / "**" / "WebConfig.java",
        ]

        # Check if CORS is already configured
        for pattern in cors_config_paths:
            for cors_file in self.backend_path.glob(str(pattern).replace(str(self.backend_path) + "/", "")):
                if cors_file.exists():
                    content = cors_file.read_text()
                    if f"http://localhost:{self.frontend_port}" not in content:
                        # Update CORS origins
                        content = re.sub(
                            r'allowedOrigins\([^)]+\)',
                            f'allowedOrigins("http://localhost:{self.frontend_port}", "http://127.0.0.1:{self.frontend_port}")',
                            content
                        )
                        cors_file.write_text(content)
                        return True
                    return True  # Already configured

        return False

    async def _configure_fastapi_cors(self) -> bool:
        """Configure CORS for FastAPI"""
        main_files = [
            self.backend_path / "main.py",
            self.backend_path / "app" / "main.py",
            self.backend_path / "src" / "main.py",
        ]

        for main_file in main_files:
            if main_file.exists():
                try:
                    content = main_file.read_text()

                    if "CORSMiddleware" in content:
                        # Update existing CORS config
                        if f"http://localhost:{self.frontend_port}" not in content:
                            content = re.sub(
                                r'allow_origins=\[[^\]]*\]',
                                f'allow_origins=["http://localhost:{self.frontend_port}", "http://127.0.0.1:{self.frontend_port}"]',
                                content
                            )
                            main_file.write_text(content)
                        return True
                    else:
                        # Add CORS middleware
                        cors_code = f'''
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:{self.frontend_port}", "http://127.0.0.1:{self.frontend_port}"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
'''
                        # Insert after app = FastAPI()
                        if "app = FastAPI(" in content:
                            content = re.sub(
                                r'(app = FastAPI\([^)]*\))',
                                f'\\1\n{cors_code}',
                                content
                            )
                            main_file.write_text(content)
                            return True

                except Exception as e:
                    logger.error(f"[FullstackIntegrator] Failed to configure FastAPI CORS: {e}")

        return False

    async def _configure_express_cors(self) -> bool:
        """Configure CORS for Express.js"""
        main_files = [
            self.backend_path / "index.js",
            self.backend_path / "app.js",
            self.backend_path / "server.js",
            self.backend_path / "src" / "index.js",
        ]

        for main_file in main_files:
            if main_file.exists():
                try:
                    content = main_file.read_text()

                    if "cors(" in content:
                        return True  # Already has CORS

                    # Add CORS
                    cors_code = f'''
const cors = require('cors');
app.use(cors({{
  origin: ['http://localhost:{self.frontend_port}', 'http://127.0.0.1:{self.frontend_port}'],
  credentials: true
}}));
'''
                    # Insert after app creation
                    if "express()" in content:
                        content = re.sub(
                            r"(const app = express\(\);?)",
                            f"\\1\n{cors_code}",
                            content
                        )
                        main_file.write_text(content)
                        return True

                except Exception as e:
                    logger.error(f"[FullstackIntegrator] Failed to configure Express CORS: {e}")

        return False

    async def _configure_flask_cors(self) -> bool:
        """Configure CORS for Flask"""
        main_files = [
            self.backend_path / "app.py",
            self.backend_path / "main.py",
            self.backend_path / "src" / "app.py",
        ]

        for main_file in main_files:
            if main_file.exists():
                try:
                    content = main_file.read_text()

                    if "CORS(" in content:
                        return True  # Already has CORS

                    # Add CORS
                    cors_import = "from flask_cors import CORS"
                    cors_init = f'CORS(app, origins=["http://localhost:{self.frontend_port}"])'

                    if "from flask" in content:
                        content = content.replace(
                            "from flask",
                            f"{cors_import}\nfrom flask"
                        )

                    if "Flask(__name__)" in content:
                        content = re.sub(
                            r"(app = Flask\(__name__\))",
                            f"\\1\n{cors_init}",
                            content
                        )
                        main_file.write_text(content)
                        return True

                except Exception as e:
                    logger.error(f"[FullstackIntegrator] Failed to configure Flask CORS: {e}")

        return False

    async def _ensure_api_service(self) -> bool:
        """Create API service file if missing"""
        api_service_path = self.frontend_path / "src" / "services" / "api.ts"

        if api_service_path.exists():
            return False  # Already exists

        # Create services directory
        api_service_path.parent.mkdir(parents=True, exist_ok=True)

        # Create API service based on frontend type
        # Use relative URL /api - works with Vite proxy in dev and nginx in production
        api_service_content = f'''// Auto-generated API Service
import axios from 'axios';

// Use relative URL for API calls - Vite proxy forwards /api/* to backend
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({{
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {{
    'Content-Type': 'application/json',
  }},
}});

// Request interceptor
api.interceptors.request.use(
  (config) => {{
    const token = localStorage.getItem('token');
    if (token) {{
      config.headers.Authorization = `Bearer ${{token}}`;
    }}
    return config;
  }},
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {{
    if (error.response?.status === 401) {{
      localStorage.removeItem('token');
      window.location.href = '/login';
    }}
    return Promise.reject(error);
  }}
);

export default api;

// API endpoints
export const endpoints = {{
  // Auth
  login: '/api/auth/login',
  register: '/api/auth/register',
  logout: '/api/auth/logout',

  // Add your endpoints here
}};
'''

        try:
            api_service_path.write_text(api_service_content)
            logger.info(f"[FullstackIntegrator] Created API service at {api_service_path}")
            return True
        except Exception as e:
            logger.error(f"[FullstackIntegrator] Failed to create API service: {e}")
            return False


async def integrate_fullstack_project(
    project_path: Path,
    frontend_port: int = 3000,
    backend_port: int = 4000
) -> Dict[str, Any]:
    """
    Convenience function to integrate a fullstack project.

    Usage:
        result = await integrate_fullstack_project(
            project_path=Path("/path/to/project"),
            frontend_port=3000,
            backend_port=4000
        )
    """
    integrator = FullstackIntegrator(project_path, frontend_port, backend_port)
    return await integrator.integrate()
