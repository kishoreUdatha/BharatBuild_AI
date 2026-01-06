"""
Technology Validator - Comprehensive pre-build validation for ALL supported technologies

This module ensures all required files exist and are correctly configured
BEFORE the build starts, preventing cascading errors.

SUPPORTED TECHNOLOGIES:
- React/Vite/TypeScript
- Python (FastAPI, Django, Flask)
- Node.js (Express)
- Java (Spring Boot)
- Go
- Full-stack (any combination)
"""

import os
import json
import re
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field

from app.core.logging_config import logger


@dataclass
class ValidationResult:
    """Result of technology validation"""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    files_fixed: List[str] = field(default_factory=list)


# =============================================================================
# DEFAULT FILE TEMPLATES
# =============================================================================

TSCONFIG_NODE_JSON = """{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts", "vite.config.js"]
}"""

POSTCSS_CONFIG_JS = """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}"""

VITE_CONFIG_TS = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
})"""

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>"""

MAIN_TSX = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)"""

APP_TSX = """function App() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <h1 className="text-3xl font-bold">Hello World</h1>
    </div>
  )
}

export default App"""

INDEX_CSS = """@tailwind base;
@tailwind components;
@tailwind utilities;
"""

TAILWIND_CONFIG_JS = """/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}"""


class TechnologyValidator:
    """
    Comprehensive validator for all supported technologies.

    Validates and auto-fixes missing files before build.
    """

    def __init__(self):
        self.file_reader: Optional[Callable] = None
        self.file_writer: Optional[Callable] = None

    def validate_and_fix(
        self,
        project_path: str,
        file_reader: Callable,
        file_writer: Callable
    ) -> ValidationResult:
        """
        Validate project and auto-fix missing files.

        Args:
            project_path: Path to project root
            file_reader: Function to read files (for sandbox support)
            file_writer: Function to write files (for sandbox support)

        Returns:
            ValidationResult with errors, warnings, and files created/fixed
        """
        self.file_reader = file_reader
        self.file_writer = file_writer

        result = ValidationResult()

        # Detect project type(s)
        has_frontend = self._check_exists(project_path, "frontend/package.json") or \
                       self._check_exists(project_path, "package.json")
        has_backend_python = self._check_exists(project_path, "backend/requirements.txt") or \
                             self._check_exists(project_path, "requirements.txt")
        has_backend_node = self._check_exists(project_path, "backend/package.json")
        has_backend_java = self._check_exists(project_path, "backend/pom.xml") or \
                           self._check_exists(project_path, "pom.xml")

        # Validate each detected technology
        if has_frontend:
            frontend_path = os.path.join(project_path, "frontend") if \
                           self._check_exists(project_path, "frontend/package.json") else project_path
            self._validate_react_vite(frontend_path, result)

        if has_backend_python:
            backend_path = os.path.join(project_path, "backend") if \
                          self._check_exists(project_path, "backend/requirements.txt") else project_path
            self._validate_python(backend_path, result)

        if has_backend_java:
            backend_path = os.path.join(project_path, "backend") if \
                          self._check_exists(project_path, "backend/pom.xml") else project_path
            self._validate_java(backend_path, result)

        # Validate Docker files if present
        if self._check_exists(project_path, "docker-compose.yml") or \
           self._check_exists(project_path, "docker-compose.yaml"):
            self._validate_docker_compose(project_path, result)

        # Set overall validity
        result.is_valid = len(result.errors) == 0

        return result

    def _check_exists(self, base_path: str, rel_path: str) -> bool:
        """Check if a file exists"""
        try:
            full_path = os.path.join(base_path, rel_path)
            content = self.file_reader(full_path)
            return content is not None and len(content) > 0
        except:
            return False

    def _read_file(self, base_path: str, rel_path: str) -> Optional[str]:
        """Read file content"""
        try:
            full_path = os.path.join(base_path, rel_path)
            return self.file_reader(full_path)
        except:
            return None

    def _write_file(self, base_path: str, rel_path: str, content: str) -> bool:
        """Write file content"""
        try:
            full_path = os.path.join(base_path, rel_path)
            self.file_writer(full_path, content)
            return True
        except Exception as e:
            logger.error(f"[TechnologyValidator] Failed to write {rel_path}: {e}")
            return False

    # =========================================================================
    # REACT / VITE / TYPESCRIPT VALIDATION
    # =========================================================================

    def _validate_react_vite(self, frontend_path: str, result: ValidationResult):
        """Validate React/Vite/TypeScript project"""
        logger.info(f"[TechnologyValidator] Validating React/Vite project: {frontend_path}")

        # 1. Check package.json exists and is valid
        pkg_content = self._read_file(frontend_path, "package.json")
        if not pkg_content:
            result.errors.append("Missing package.json")
            return

        try:
            pkg_json = json.loads(pkg_content)
        except json.JSONDecodeError as e:
            result.errors.append(f"Invalid package.json: {e}")
            return

        # 2. Check for TypeScript project
        is_typescript = self._check_exists(frontend_path, "tsconfig.json")

        if is_typescript:
            # Check tsconfig.json references
            tsconfig_content = self._read_file(frontend_path, "tsconfig.json")
            if tsconfig_content and "tsconfig.node.json" in tsconfig_content:
                if not self._check_exists(frontend_path, "tsconfig.node.json"):
                    if self._write_file(frontend_path, "tsconfig.node.json", TSCONFIG_NODE_JSON):
                        result.files_created.append("tsconfig.node.json")
                    else:
                        result.errors.append("Missing tsconfig.node.json (referenced in tsconfig.json)")

            # Check tsconfig.app.json if referenced
            if tsconfig_content and "tsconfig.app.json" in tsconfig_content:
                if not self._check_exists(frontend_path, "tsconfig.app.json"):
                    result.warnings.append("Missing tsconfig.app.json (referenced in tsconfig.json)")

        # 3. Check for Vite config
        has_vite_config = self._check_exists(frontend_path, "vite.config.ts") or \
                         self._check_exists(frontend_path, "vite.config.js")
        if not has_vite_config:
            if self._write_file(frontend_path, "vite.config.ts", VITE_CONFIG_TS):
                result.files_created.append("vite.config.ts")
            else:
                result.errors.append("Missing vite.config.ts")

        # 4. Check for index.html
        if not self._check_exists(frontend_path, "index.html"):
            if self._write_file(frontend_path, "index.html", INDEX_HTML):
                result.files_created.append("index.html")
            else:
                result.errors.append("Missing index.html")

        # 5. Check for main entry point
        has_main = self._check_exists(frontend_path, "src/main.tsx") or \
                   self._check_exists(frontend_path, "src/main.ts") or \
                   self._check_exists(frontend_path, "src/main.jsx") or \
                   self._check_exists(frontend_path, "src/main.js") or \
                   self._check_exists(frontend_path, "src/index.tsx") or \
                   self._check_exists(frontend_path, "src/index.js")
        if not has_main:
            ext = "tsx" if is_typescript else "jsx"
            if self._write_file(frontend_path, f"src/main.{ext}", MAIN_TSX):
                result.files_created.append(f"src/main.{ext}")
            else:
                result.errors.append(f"Missing src/main.{ext}")

        # 6. Check for App component
        has_app = self._check_exists(frontend_path, "src/App.tsx") or \
                  self._check_exists(frontend_path, "src/App.ts") or \
                  self._check_exists(frontend_path, "src/App.jsx") or \
                  self._check_exists(frontend_path, "src/App.js")
        if not has_app:
            ext = "tsx" if is_typescript else "jsx"
            if self._write_file(frontend_path, f"src/App.{ext}", APP_TSX):
                result.files_created.append(f"src/App.{ext}")

        # 7. Check Tailwind setup
        deps = {**pkg_json.get("dependencies", {}), **pkg_json.get("devDependencies", {})}
        if "tailwindcss" in deps:
            # Need postcss.config.js
            if not self._check_exists(frontend_path, "postcss.config.js") and \
               not self._check_exists(frontend_path, "postcss.config.cjs") and \
               not self._check_exists(frontend_path, "postcss.config.mjs"):
                if self._write_file(frontend_path, "postcss.config.js", POSTCSS_CONFIG_JS):
                    result.files_created.append("postcss.config.js")

            # Need tailwind.config.js
            if not self._check_exists(frontend_path, "tailwind.config.js") and \
               not self._check_exists(frontend_path, "tailwind.config.ts"):
                if self._write_file(frontend_path, "tailwind.config.js", TAILWIND_CONFIG_JS):
                    result.files_created.append("tailwind.config.js")

            # Need CSS with @tailwind directives
            if not self._check_exists(frontend_path, "src/index.css"):
                if self._write_file(frontend_path, "src/index.css", INDEX_CSS):
                    result.files_created.append("src/index.css")

        # 8. Check package.json for required scripts
        scripts = pkg_json.get("scripts", {})
        if "dev" not in scripts:
            result.warnings.append("Missing 'dev' script in package.json")
        if "build" not in scripts:
            result.warnings.append("Missing 'build' script in package.json")

    # =========================================================================
    # PYTHON VALIDATION
    # =========================================================================

    def _validate_python(self, backend_path: str, result: ValidationResult):
        """Validate Python project"""
        logger.info(f"[TechnologyValidator] Validating Python project: {backend_path}")

        # 1. Check requirements.txt
        req_content = self._read_file(backend_path, "requirements.txt")
        if not req_content:
            result.errors.append("Missing requirements.txt")
            return

        # 2. Check for invalid package names (python- prefix)
        invalid_packages = []
        valid_python_prefixed = ["python-dotenv", "python-dateutil", "python-multipart", "python-jose"]

        for line in req_content.split("\n"):
            line = line.strip()
            if line.startswith("python-") and not any(line.startswith(p) for p in valid_python_prefixed):
                # Extract package name
                pkg_name = line.split("==")[0].split(">=")[0].split("<=")[0].split(">")[0].split("<")[0]
                correct_name = pkg_name.replace("python-", "")
                invalid_packages.append((pkg_name, correct_name))

        if invalid_packages:
            # Fix the requirements.txt
            fixed_content = req_content
            for wrong, correct in invalid_packages:
                fixed_content = fixed_content.replace(wrong, correct)

            if self._write_file(backend_path, "requirements.txt", fixed_content):
                result.files_fixed.append(f"requirements.txt (fixed {len(invalid_packages)} package names)")
            else:
                for wrong, correct in invalid_packages:
                    result.errors.append(f"Invalid package: {wrong} → should be {correct}")

        # 3. Check for main entry point
        has_main = self._check_exists(backend_path, "main.py") or \
                   self._check_exists(backend_path, "app.py") or \
                   self._check_exists(backend_path, "app/__init__.py")
        if not has_main:
            result.warnings.append("No main.py or app.py found")

        # 4. Check Dockerfile for npm ci issues (if it's a multi-service project)
        dockerfile_content = self._read_file(backend_path, "Dockerfile")
        if dockerfile_content:
            self._fix_dockerfile(backend_path, dockerfile_content, result)

    # =========================================================================
    # JAVA VALIDATION
    # =========================================================================

    def _validate_java(self, backend_path: str, result: ValidationResult):
        """Validate Java project"""
        logger.info(f"[TechnologyValidator] Validating Java project: {backend_path}")

        # 1. Check pom.xml or build.gradle
        has_maven = self._check_exists(backend_path, "pom.xml")
        has_gradle = self._check_exists(backend_path, "build.gradle") or \
                     self._check_exists(backend_path, "build.gradle.kts")

        if not has_maven and not has_gradle:
            result.errors.append("Missing pom.xml or build.gradle")
            return

        # 2. Check for main class
        # This is more complex - would need to scan src/main/java

    # =========================================================================
    # DOCKER COMPOSE VALIDATION
    # =========================================================================

    def _validate_docker_compose(self, project_path: str, result: ValidationResult):
        """Validate Docker Compose configuration"""
        logger.info(f"[TechnologyValidator] Validating Docker Compose: {project_path}")

        compose_content = self._read_file(project_path, "docker-compose.yml")
        if not compose_content:
            compose_content = self._read_file(project_path, "docker-compose.yaml")

        if not compose_content:
            return

        # Check for referenced Dockerfiles
        import re
        dockerfile_refs = re.findall(r'dockerfile:\s*(\S+)', compose_content)
        context_refs = re.findall(r'context:\s*(\S+)', compose_content)

        for i, dockerfile in enumerate(dockerfile_refs):
            context = context_refs[i] if i < len(context_refs) else "."
            dockerfile_path = os.path.join(context, dockerfile)
            dockerfile_path = dockerfile_path.replace("./", "")

            if not self._check_exists(project_path, dockerfile_path):
                result.errors.append(f"Missing Dockerfile referenced in docker-compose: {dockerfile_path}")

        # Fix Dockerfiles in all contexts
        for context in context_refs:
            context_clean = context.replace("./", "").strip()
            context_path = os.path.join(project_path, context_clean) if context_clean else project_path

            dockerfile_content = self._read_file(context_path, "Dockerfile")
            if dockerfile_content:
                self._fix_dockerfile(context_path, dockerfile_content, result)

    # =========================================================================
    # DOCKERFILE FIXES
    # =========================================================================

    def _fix_dockerfile(self, base_path: str, content: str, result: ValidationResult):
        """Fix common Dockerfile issues"""
        original_content = content
        fixes = []

        # Check if build step exists
        has_npm_build = "npm run build" in content or "yarn build" in content or "pnpm build" in content

        # 1. Replace npm ci with npm install
        if "npm ci" in content:
            content = content.replace("npm ci", "npm install")
            fixes.append("npm ci → npm install")

        # 2. Handle --only=production and --omit=dev
        if has_npm_build:
            # Remove production-only flags if build step exists
            if "--only=production" in content:
                content = re.sub(r'\s*--only=production\s*', ' ', content)
                fixes.append("Removed --only=production (build needs devDeps)")
            if "--omit=dev" in content:
                content = re.sub(r'\s*--omit=dev\s*', ' ', content)
                fixes.append("Removed --omit=dev (build needs devDeps)")
        else:
            # Just modernize the flag
            if "--only=production" in content:
                content = content.replace("--only=production", "--omit=dev")
                fixes.append("--only=production → --omit=dev")

        # Write back if changed
        if content != original_content:
            if self._write_file(base_path, "Dockerfile", content):
                result.files_fixed.append(f"Dockerfile ({', '.join(fixes)})")


# Singleton instance
technology_validator = TechnologyValidator()
