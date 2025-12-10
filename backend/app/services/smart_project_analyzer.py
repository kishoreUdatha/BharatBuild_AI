"""
Smart Project Analyzer - Proactive Project Intelligence

This module provides intelligent, proactive project analysis and auto-configuration
for 100K+ users with different technologies. Instead of reactive error fixing,
it PREVENTS errors by understanding project structure before execution.

Supports ALL major technologies:
- JavaScript/TypeScript: React, Vue, Angular, Svelte, Next.js, Express, Node.js
- Python: FastAPI, Django, Flask, Streamlit, ML/AI projects
- Java: Spring Boot, Android, Maven, Gradle
- Go: Standard Go projects
- Rust: Cargo projects
- Fullstack: Monorepo structures with frontend/backend

Key Features:
1. Proactive structure detection - understand project BEFORE running
2. Auto-fix common issues - missing configs, wrong directories
3. Technology-specific intelligence - knows each framework's requirements
4. Working directory detection - handles monorepos intelligently
5. Dependency validation - ensures all required files exist
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from app.core.logging_config import logger
from app.services.unified_storage import unified_storage as storage


class Technology(Enum):
    """Supported technologies"""
    # JavaScript/TypeScript Frontend
    REACT_VITE = "react-vite"
    REACT_CRA = "react-cra"
    NEXTJS = "nextjs"
    VUE_VITE = "vue-vite"
    VUE_CLI = "vue-cli"
    ANGULAR = "angular"
    SVELTE = "svelte"
    VANILLA_JS = "vanilla-js"

    # JavaScript/TypeScript Backend
    EXPRESS = "express"
    NESTJS = "nestjs"

    # Python
    FASTAPI = "fastapi"
    DJANGO = "django"
    FLASK = "flask"
    STREAMLIT = "streamlit"
    PYTHON_ML = "python-ml"
    PYTHON_SCRIPT = "python-script"

    # Java
    SPRING_BOOT_MAVEN = "spring-boot-maven"
    SPRING_BOOT_GRADLE = "spring-boot-gradle"
    ANDROID = "android"

    # Other
    GO = "go"
    RUST = "rust"
    STATIC_HTML = "static-html"

    # Fullstack Monorepo
    FULLSTACK_REACT_EXPRESS = "fullstack-react-express"
    FULLSTACK_REACT_FASTAPI = "fullstack-react-fastapi"
    FULLSTACK_REACT_SPRING = "fullstack-react-spring"

    UNKNOWN = "unknown"


@dataclass
class ProjectStructure:
    """Detected project structure"""
    technology: Technology
    root_path: Path
    working_directory: Path  # Where to run commands from
    entry_points: List[str]  # Main entry files
    config_files: Dict[str, bool]  # Config file -> exists
    missing_required: List[str]  # Missing required files
    has_dependencies: bool
    install_command: str
    run_command: str
    build_command: str
    default_port: int
    issues: List[str] = field(default_factory=list)
    auto_fixes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AutoFix:
    """An automatic fix to apply"""
    file_path: str
    content: str
    reason: str


class SmartProjectAnalyzer:
    """
    Intelligent Project Analyzer for Multi-Technology Support

    This analyzer proactively:
    1. Detects project technology and structure
    2. Identifies the correct working directory
    3. Finds missing required files
    4. Generates auto-fixes for common issues
    5. Provides correct commands for each technology
    """

    # Required config files per technology
    REQUIRED_FILES: Dict[Technology, List[str]] = {
        Technology.REACT_VITE: ["package.json", "vite.config.ts", "index.html"],
        Technology.REACT_CRA: ["package.json", "public/index.html"],
        Technology.NEXTJS: ["package.json", "next.config.js"],
        Technology.VUE_VITE: ["package.json", "vite.config.ts", "index.html"],
        Technology.ANGULAR: ["package.json", "angular.json"],
        Technology.SVELTE: ["package.json", "svelte.config.js"],
        Technology.EXPRESS: ["package.json"],
        Technology.FASTAPI: ["main.py", "requirements.txt"],
        Technology.DJANGO: ["manage.py", "requirements.txt"],
        Technology.FLASK: ["app.py", "requirements.txt"],
        Technology.STREAMLIT: ["app.py", "requirements.txt"],
        Technology.SPRING_BOOT_MAVEN: ["pom.xml", "src/main/java"],
        Technology.SPRING_BOOT_GRADLE: ["build.gradle", "src/main/java"],
        Technology.GO: ["go.mod", "main.go"],
        Technology.RUST: ["Cargo.toml", "src/main.rs"],
    }

    # Default ports per technology
    DEFAULT_PORTS: Dict[Technology, int] = {
        Technology.REACT_VITE: 5173,
        Technology.REACT_CRA: 3000,
        Technology.NEXTJS: 3000,
        Technology.VUE_VITE: 5173,
        Technology.ANGULAR: 4200,
        Technology.SVELTE: 5173,
        Technology.EXPRESS: 3000,
        Technology.FASTAPI: 8000,
        Technology.DJANGO: 8000,
        Technology.FLASK: 5000,
        Technology.STREAMLIT: 8501,
        Technology.SPRING_BOOT_MAVEN: 8080,
        Technology.SPRING_BOOT_GRADLE: 8080,
        Technology.GO: 8080,
        Technology.RUST: 8080,
    }

    # Install commands per technology
    INSTALL_COMMANDS: Dict[Technology, str] = {
        Technology.REACT_VITE: "npm install",
        Technology.REACT_CRA: "npm install",
        Technology.NEXTJS: "npm install",
        Technology.VUE_VITE: "npm install",
        Technology.ANGULAR: "npm install",
        Technology.SVELTE: "npm install",
        Technology.EXPRESS: "npm install",
        Technology.FASTAPI: "pip install -r requirements.txt",
        Technology.DJANGO: "pip install -r requirements.txt",
        Technology.FLASK: "pip install -r requirements.txt",
        Technology.STREAMLIT: "pip install -r requirements.txt",
        Technology.SPRING_BOOT_MAVEN: "mvn install -DskipTests",
        Technology.SPRING_BOOT_GRADLE: "gradle build -x test",
        Technology.GO: "go mod download",
        Technology.RUST: "cargo build",
    }

    # Run commands per technology (with port placeholder {port})
    RUN_COMMANDS: Dict[Technology, str] = {
        Technology.REACT_VITE: "npm run dev -- --host 0.0.0.0 --port {port}",
        Technology.REACT_CRA: "npm start",
        Technology.NEXTJS: "npm run dev -- -p {port}",
        Technology.VUE_VITE: "npm run dev -- --host 0.0.0.0 --port {port}",
        Technology.ANGULAR: "npm start -- --host 0.0.0.0 --port {port}",
        Technology.SVELTE: "npm run dev -- --host 0.0.0.0 --port {port}",
        Technology.EXPRESS: "npm start",
        Technology.FASTAPI: "uvicorn main:app --host 0.0.0.0 --port {port}",
        Technology.DJANGO: "python manage.py runserver 0.0.0.0:{port}",
        Technology.FLASK: "flask run --host 0.0.0.0 --port {port}",
        Technology.STREAMLIT: "streamlit run app.py --server.port {port}",
        Technology.SPRING_BOOT_MAVEN: "java -jar target/*.jar --server.port={port}",
        Technology.SPRING_BOOT_GRADLE: "java -jar build/libs/*.jar --server.port={port}",
        Technology.GO: "go run . --port {port}",
        Technology.RUST: "cargo run",
    }

    async def analyze_project(
        self,
        project_id: str,
        user_id: str,
        project_path: Optional[Path] = None
    ) -> ProjectStructure:
        """
        Analyze a project and return its structure with recommendations.

        This is the main entry point - call this BEFORE running a project!

        Args:
            project_id: Project identifier
            user_id: User identifier
            project_path: Optional explicit project path

        Returns:
            ProjectStructure with all analysis results
        """
        logger.info(f"[SmartAnalyzer:{project_id}] Starting project analysis...")

        # Get project path
        if project_path is None:
            project_path = Path(storage.get_sandbox_path(project_id, user_id))

        # Detect technology
        technology = await self._detect_technology(project_path)
        logger.info(f"[SmartAnalyzer:{project_id}] Detected technology: {technology.value}")

        # Find working directory (handles monorepos)
        working_dir = await self._find_working_directory(project_path, technology)
        logger.info(f"[SmartAnalyzer:{project_id}] Working directory: {working_dir}")

        # Check required files
        config_files, missing = await self._check_required_files(working_dir, technology)

        # Find entry points
        entry_points = await self._find_entry_points(working_dir, technology)

        # Detect issues and generate auto-fixes
        issues, auto_fixes = await self._analyze_issues(
            project_path, working_dir, technology, missing
        )

        # Build structure
        structure = ProjectStructure(
            technology=technology,
            root_path=project_path,
            working_directory=working_dir,
            entry_points=entry_points,
            config_files=config_files,
            missing_required=missing,
            has_dependencies=self._has_dependency_file(working_dir, technology),
            install_command=self.INSTALL_COMMANDS.get(technology, "npm install"),
            run_command=self.RUN_COMMANDS.get(technology, "npm run dev"),
            build_command=self._get_build_command(technology),
            default_port=self.DEFAULT_PORTS.get(technology, 3000),
            issues=issues,
            auto_fixes=auto_fixes
        )

        logger.info(f"[SmartAnalyzer:{project_id}] Analysis complete: {len(issues)} issues, {len(auto_fixes)} auto-fixes")

        return structure

    async def apply_auto_fixes(
        self,
        project_id: str,
        user_id: str,
        structure: ProjectStructure
    ) -> List[str]:
        """
        Apply all auto-fixes from the analysis.

        Returns list of files that were created/modified.
        """
        files_modified = []

        for fix in structure.auto_fixes:
            file_path = fix.get("file_path", "")
            content = fix.get("content", "")
            reason = fix.get("reason", "")

            if file_path and content:
                try:
                    # Make path relative to working directory
                    if structure.working_directory != structure.root_path:
                        rel_working = structure.working_directory.relative_to(structure.root_path)
                        full_path = str(rel_working / file_path)
                    else:
                        full_path = file_path

                    await storage.write_to_sandbox(project_id, full_path, content, user_id)
                    files_modified.append(full_path)
                    logger.info(f"[SmartAnalyzer:{project_id}] Auto-fix applied: {full_path} ({reason})")
                except Exception as e:
                    logger.error(f"[SmartAnalyzer:{project_id}] Failed to apply fix {file_path}: {e}")

        return files_modified

    async def _detect_technology(self, project_path: Path) -> Technology:
        """Detect the project's technology from files"""

        # Check for monorepo structure first
        frontend_dir = project_path / "frontend"
        backend_dir = project_path / "backend"

        if frontend_dir.exists() and backend_dir.exists():
            return await self._detect_fullstack_technology(project_path, frontend_dir, backend_dir)

        # Check for frontend in subfolder (frontend exists, backend empty or missing)
        if frontend_dir.exists() and (frontend_dir / "package.json").exists():
            if not backend_dir.exists() or not any(backend_dir.iterdir()):
                # Frontend-only in subfolder
                return await self._detect_frontend_technology(frontend_dir)

        # Standard detection from root
        return await self._detect_single_technology(project_path)

    async def _detect_fullstack_technology(
        self,
        project_path: Path,
        frontend_dir: Path,
        backend_dir: Path
    ) -> Technology:
        """Detect fullstack monorepo technology"""

        # Check backend type
        has_spring = (backend_dir / "pom.xml").exists() or (backend_dir / "build.gradle").exists()
        has_fastapi = (backend_dir / "main.py").exists() or (backend_dir / "requirements.txt").exists()
        has_express = (backend_dir / "package.json").exists()

        # Check frontend type
        frontend_pkg = frontend_dir / "package.json"
        has_react = False
        if frontend_pkg.exists():
            try:
                with open(frontend_pkg) as f:
                    pkg = json.load(f)
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    has_react = "react" in deps
            except:
                pass

        if has_react:
            if has_spring:
                return Technology.FULLSTACK_REACT_SPRING
            elif has_fastapi:
                return Technology.FULLSTACK_REACT_FASTAPI
            elif has_express:
                return Technology.FULLSTACK_REACT_EXPRESS

        # Fallback to single technology detection
        return await self._detect_single_technology(project_path)

    async def _detect_frontend_technology(self, frontend_dir: Path) -> Technology:
        """Detect frontend technology from frontend/ directory"""
        pkg_path = frontend_dir / "package.json"

        if not pkg_path.exists():
            return Technology.UNKNOWN

        try:
            with open(pkg_path) as f:
                pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                # Check for React + Vite
                if "react" in deps:
                    if "vite" in deps or "@vitejs/plugin-react" in deps:
                        return Technology.REACT_VITE
                    elif "next" in deps:
                        return Technology.NEXTJS
                    else:
                        return Technology.REACT_CRA

                # Check for Vue
                if "vue" in deps:
                    if "vite" in deps:
                        return Technology.VUE_VITE
                    return Technology.VUE_CLI

                # Check for Angular
                if "@angular/core" in deps:
                    return Technology.ANGULAR

                # Check for Svelte
                if "svelte" in deps:
                    return Technology.SVELTE
        except:
            pass

        return Technology.UNKNOWN

    async def _detect_single_technology(self, project_path: Path) -> Technology:
        """Detect technology for a standard project structure"""

        # Check package.json for Node.js projects
        pkg_path = project_path / "package.json"
        if pkg_path.exists():
            try:
                with open(pkg_path) as f:
                    pkg = json.load(f)
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                    # Frontend frameworks
                    if "react" in deps:
                        if "vite" in deps or "@vitejs/plugin-react" in deps:
                            return Technology.REACT_VITE
                        elif "next" in deps:
                            return Technology.NEXTJS
                        return Technology.REACT_CRA

                    if "vue" in deps:
                        if "vite" in deps:
                            return Technology.VUE_VITE
                        return Technology.VUE_CLI

                    if "@angular/core" in deps:
                        return Technology.ANGULAR

                    if "svelte" in deps:
                        return Technology.SVELTE

                    # Backend frameworks
                    if "express" in deps:
                        return Technology.EXPRESS

                    if "@nestjs/core" in deps:
                        return Technology.NESTJS
            except:
                pass

        # Check for Python projects
        if (project_path / "requirements.txt").exists() or (project_path / "pyproject.toml").exists():
            if (project_path / "manage.py").exists():
                return Technology.DJANGO
            if (project_path / "main.py").exists():
                # Check content for FastAPI
                try:
                    with open(project_path / "main.py") as f:
                        content = f.read()
                        if "fastapi" in content.lower():
                            return Technology.FASTAPI
                        if "flask" in content.lower():
                            return Technology.FLASK
                        if "streamlit" in content.lower():
                            return Technology.STREAMLIT
                except:
                    pass
                return Technology.FASTAPI  # Default Python web
            if (project_path / "app.py").exists():
                return Technology.FLASK
            return Technology.PYTHON_SCRIPT

        # Check for Java projects
        if (project_path / "pom.xml").exists():
            return Technology.SPRING_BOOT_MAVEN
        if (project_path / "build.gradle").exists() or (project_path / "build.gradle.kts").exists():
            # Check for Android
            if (project_path / "app" / "src" / "main" / "AndroidManifest.xml").exists():
                return Technology.ANDROID
            return Technology.SPRING_BOOT_GRADLE

        # Check for Go
        if (project_path / "go.mod").exists():
            return Technology.GO

        # Check for Rust
        if (project_path / "Cargo.toml").exists():
            return Technology.RUST

        # Check for static HTML
        if (project_path / "index.html").exists():
            return Technology.STATIC_HTML

        return Technology.UNKNOWN

    async def _find_working_directory(
        self,
        project_path: Path,
        technology: Technology
    ) -> Path:
        """Find the correct working directory for running commands"""

        # For fullstack projects, ALWAYS use project root
        # Commands like "cd frontend && ..." and "cd backend && ..." need to run from root
        if technology in [
            Technology.FULLSTACK_REACT_EXPRESS,
            Technology.FULLSTACK_REACT_FASTAPI,
            Technology.FULLSTACK_REACT_SPRING
        ]:
            logger.info(f"[SmartAnalyzer] Fullstack project - using project root for {technology}")
            return project_path

        # For frontend-only projects with subfolder structure
        frontend_dir = project_path / "frontend"
        backend_dir = project_path / "backend"

        if frontend_dir.exists() and (frontend_dir / "package.json").exists():
            # Check if backend is empty
            backend_empty = not backend_dir.exists() or not any(
                f for f in backend_dir.iterdir()
                if not f.name.startswith('.')
            )

            if backend_empty:
                logger.info(f"[SmartAnalyzer] Detected frontend-only project in subfolder")
                return frontend_dir

        # Check if root has no package.json but frontend/ does
        if not (project_path / "package.json").exists():
            if frontend_dir.exists() and (frontend_dir / "package.json").exists():
                return frontend_dir

        # Default to project root
        return project_path

    async def _check_required_files(
        self,
        working_dir: Path,
        technology: Technology
    ) -> Tuple[Dict[str, bool], List[str]]:
        """Check for required files and return missing ones"""

        required = self.REQUIRED_FILES.get(technology, [])
        config_files = {}
        missing = []

        for file_path in required:
            full_path = working_dir / file_path
            exists = full_path.exists()
            config_files[file_path] = exists
            if not exists:
                missing.append(file_path)

        return config_files, missing

    async def _find_entry_points(
        self,
        working_dir: Path,
        technology: Technology
    ) -> List[str]:
        """Find the main entry points for the project"""

        entry_points = []

        # Common entry points by technology
        entry_map = {
            Technology.REACT_VITE: ["src/main.tsx", "src/main.ts", "src/index.tsx"],
            Technology.REACT_CRA: ["src/index.tsx", "src/index.js"],
            Technology.NEXTJS: ["pages/_app.tsx", "app/page.tsx"],
            Technology.VUE_VITE: ["src/main.ts", "src/main.js"],
            Technology.ANGULAR: ["src/main.ts"],
            Technology.EXPRESS: ["src/index.ts", "src/index.js", "index.js", "server.js"],
            Technology.FASTAPI: ["main.py", "app/main.py"],
            Technology.DJANGO: ["manage.py"],
            Technology.FLASK: ["app.py", "main.py"],
            Technology.GO: ["main.go", "cmd/main.go"],
            Technology.RUST: ["src/main.rs"],
        }

        for entry in entry_map.get(technology, []):
            if (working_dir / entry).exists():
                entry_points.append(entry)

        return entry_points

    async def _analyze_issues(
        self,
        project_path: Path,
        working_dir: Path,
        technology: Technology,
        missing_files: List[str]
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Analyze issues and generate auto-fixes"""

        issues = []
        auto_fixes = []

        # Issue: Missing required files
        for missing in missing_files:
            issues.append(f"Missing required file: {missing}")

            # Generate auto-fix for common missing files
            fix_content = await self._generate_fix_for_missing(missing, technology, working_dir)
            if fix_content:
                auto_fixes.append({
                    "file_path": missing,
                    "content": fix_content,
                    "reason": f"Auto-generated missing {missing}"
                })

        # Issue: React/Vite without proper config
        if technology == Technology.REACT_VITE:
            if not (working_dir / "vite.config.ts").exists():
                auto_fixes.append({
                    "file_path": "vite.config.ts",
                    "content": self._generate_vite_config(),
                    "reason": "Missing Vite configuration"
                })

            if not (working_dir / "tailwind.config.js").exists() and self._uses_tailwind(working_dir):
                auto_fixes.append({
                    "file_path": "tailwind.config.js",
                    "content": self._generate_tailwind_config(),
                    "reason": "Missing Tailwind configuration"
                })

            if not (working_dir / "postcss.config.js").exists() and self._uses_tailwind(working_dir):
                auto_fixes.append({
                    "file_path": "postcss.config.js",
                    "content": self._generate_postcss_config(),
                    "reason": "Missing PostCSS configuration"
                })

            if not (working_dir / "tsconfig.node.json").exists():
                auto_fixes.append({
                    "file_path": "tsconfig.node.json",
                    "content": self._generate_tsconfig_node(),
                    "reason": "Missing TypeScript node config"
                })

        # Issue: Python without requirements
        if technology in [Technology.FASTAPI, Technology.FLASK, Technology.DJANGO]:
            if not (working_dir / "requirements.txt").exists():
                auto_fixes.append({
                    "file_path": "requirements.txt",
                    "content": self._generate_requirements(technology),
                    "reason": "Missing Python requirements"
                })

        return issues, auto_fixes

    def _has_dependency_file(self, working_dir: Path, technology: Technology) -> bool:
        """Check if dependency file exists"""
        if technology.value.startswith("react") or technology.value.startswith("vue") or technology in [
            Technology.ANGULAR, Technology.SVELTE, Technology.EXPRESS, Technology.NESTJS
        ]:
            return (working_dir / "package.json").exists()

        if technology in [Technology.FASTAPI, Technology.FLASK, Technology.DJANGO, Technology.STREAMLIT]:
            return (working_dir / "requirements.txt").exists()

        if technology in [Technology.SPRING_BOOT_MAVEN]:
            return (working_dir / "pom.xml").exists()

        if technology in [Technology.SPRING_BOOT_GRADLE]:
            return (working_dir / "build.gradle").exists()

        if technology == Technology.GO:
            return (working_dir / "go.mod").exists()

        if technology == Technology.RUST:
            return (working_dir / "Cargo.toml").exists()

        return True

    def _get_build_command(self, technology: Technology) -> str:
        """Get build command for technology"""
        build_commands = {
            Technology.REACT_VITE: "npm run build",
            Technology.REACT_CRA: "npm run build",
            Technology.NEXTJS: "npm run build",
            Technology.VUE_VITE: "npm run build",
            Technology.ANGULAR: "npm run build",
            Technology.SVELTE: "npm run build",
            Technology.EXPRESS: "npm run build",
            Technology.SPRING_BOOT_MAVEN: "mvn package -DskipTests",
            Technology.SPRING_BOOT_GRADLE: "gradle build -x test",
            Technology.GO: "go build .",
            Technology.RUST: "cargo build --release",
        }
        return build_commands.get(technology, "npm run build")

    def _uses_tailwind(self, working_dir: Path) -> bool:
        """Check if project uses Tailwind CSS"""
        pkg_path = working_dir / "package.json"
        if pkg_path.exists():
            try:
                with open(pkg_path) as f:
                    pkg = json.load(f)
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    return "tailwindcss" in deps
            except:
                pass
        return False

    async def _generate_fix_for_missing(
        self,
        missing_file: str,
        technology: Technology,
        working_dir: Path
    ) -> Optional[str]:
        """Generate content for a missing file"""

        if missing_file == "vite.config.ts":
            return self._generate_vite_config()

        if missing_file == "tailwind.config.js":
            return self._generate_tailwind_config()

        if missing_file == "postcss.config.js":
            return self._generate_postcss_config()

        if missing_file == "tsconfig.node.json":
            return self._generate_tsconfig_node()

        if missing_file == "requirements.txt":
            return self._generate_requirements(technology)

        return None

    def _generate_vite_config(self) -> str:
        return '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
})
'''

    def _generate_tailwind_config(self) -> str:
        return '''/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
'''

    def _generate_postcss_config(self) -> str:
        return '''export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
'''

    def _generate_tsconfig_node(self) -> str:
        return '''{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
'''

    def _generate_requirements(self, technology: Technology) -> str:
        base = """# Auto-generated requirements
"""
        if technology == Technology.FASTAPI:
            return base + """fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic>=2.0.0
"""
        elif technology == Technology.FLASK:
            return base + """flask>=2.3.0
python-dotenv>=1.0.0
"""
        elif technology == Technology.DJANGO:
            return base + """django>=4.2.0
djangorestframework>=3.14.0
"""
        elif technology == Technology.STREAMLIT:
            return base + """streamlit>=1.28.0
pandas>=2.0.0
"""
        return base


# Singleton instance
smart_analyzer = SmartProjectAnalyzer()
