"""
Project Export Service - Download-Ready Projects

Ensures that when a student downloads a project, it runs locally without errors.

GOALS:
1. Complete package.json with ALL dependencies
2. Clear README.md with setup instructions
3. .env.example for environment variables
4. Remove BharatBuild-specific code (error-capture.js, etc.)
5. Validate project structure before export
6. Generate ZIP file for download

SUPPORTED FRAMEWORKS:
- React (Vite, CRA)
- Next.js
- Vue.js
- Angular
- Node.js/Express
- Python/FastAPI
- Java/Spring Boot
"""

import os
import json
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import re

from app.core.logging_config import logger


# =============================================================================
# PROJECT TEMPLATES
# =============================================================================

README_TEMPLATE = """# {project_name}

{description}

## Prerequisites

{prerequisites}

## Getting Started

### 1. Install Dependencies

```bash
{install_command}
```

### 2. Set Up Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your configuration.

### 3. Run the Project

```bash
{run_command}
```

{additional_instructions}

## Project Structure

```
{project_structure}
```

## Technologies Used

{technologies}

## License

MIT

---

*Generated with [BharatBuild AI](https://bharatbuild.ai)*
"""

ENV_EXAMPLE_TEMPLATE = """# Environment Variables
# Copy this file to .env and fill in your values

# API Configuration
{api_vars}

# Database (if applicable)
{db_vars}

# Other Settings
{other_vars}
"""

GITIGNORE_TEMPLATE = """# Dependencies
node_modules/
__pycache__/
venv/
.venv/
env/

# Environment
.env
.env.local
.env.*.local

# Build
dist/
build/
.next/
out/
target/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
npm-debug.log*

# Testing
coverage/
.pytest_cache/

# Misc
*.pyc
*.pyo
"""


# =============================================================================
# FRAMEWORK CONFIGURATIONS
# =============================================================================

FRAMEWORK_CONFIGS = {
    "react-vite": {
        "prerequisites": "- Node.js 18+ (https://nodejs.org/)\n- npm or yarn",
        "install_command": "npm install",
        "run_command": "npm run dev",
        "build_command": "npm run build",
        "additional_instructions": """
### Development

The app runs on `http://localhost:5173` by default.

### Building for Production

```bash
npm run build
```

The build output will be in the `dist/` folder.
""",
        "required_scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview"
        },
        "core_dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0"
        },
        "dev_dependencies": {
            "vite": "^5.0.0",
            "@vitejs/plugin-react": "^4.2.0"
        }
    },
    "react-cra": {
        "prerequisites": "- Node.js 18+ (https://nodejs.org/)\n- npm or yarn",
        "install_command": "npm install",
        "run_command": "npm start",
        "build_command": "npm run build",
        "additional_instructions": """
### Development

The app runs on `http://localhost:3000` by default.

### Building for Production

```bash
npm run build
```
""",
        "required_scripts": {
            "start": "react-scripts start",
            "build": "react-scripts build",
            "test": "react-scripts test"
        },
        "core_dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "react-scripts": "5.0.1"
        }
    },
    "nextjs": {
        "prerequisites": "- Node.js 18+ (https://nodejs.org/)\n- npm or yarn",
        "install_command": "npm install",
        "run_command": "npm run dev",
        "build_command": "npm run build",
        "additional_instructions": """
### Development

The app runs on `http://localhost:3000` by default.

### Building for Production

```bash
npm run build
npm start
```
""",
        "required_scripts": {
            "dev": "next dev",
            "build": "next build",
            "start": "next start"
        },
        "core_dependencies": {
            "next": "^14.0.0",
            "react": "^18.2.0",
            "react-dom": "^18.2.0"
        }
    },
    "vue": {
        "prerequisites": "- Node.js 18+ (https://nodejs.org/)\n- npm or yarn",
        "install_command": "npm install",
        "run_command": "npm run dev",
        "build_command": "npm run build",
        "additional_instructions": """
### Development

The app runs on `http://localhost:5173` by default.
""",
        "required_scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview"
        },
        "core_dependencies": {
            "vue": "^3.3.0"
        },
        "dev_dependencies": {
            "vite": "^5.0.0",
            "@vitejs/plugin-vue": "^4.5.0"
        }
    },
    "angular": {
        "prerequisites": "- Node.js 18+ (https://nodejs.org/)\n- Angular CLI: `npm install -g @angular/cli`",
        "install_command": "npm install",
        "run_command": "ng serve",
        "build_command": "ng build",
        "additional_instructions": """
### Development

The app runs on `http://localhost:4200` by default.
""",
        "required_scripts": {
            "start": "ng serve",
            "build": "ng build"
        },
        "core_dependencies": {
            "@angular/core": "^17.0.0",
            "@angular/cli": "^17.0.0"
        }
    },
    "express": {
        "prerequisites": "- Node.js 18+ (https://nodejs.org/)\n- npm or yarn",
        "install_command": "npm install",
        "run_command": "npm start",
        "additional_instructions": """
### Development

The server runs on `http://localhost:3000` by default.

### With nodemon (auto-reload)

```bash
npm run dev
```
""",
        "required_scripts": {
            "start": "node index.js",
            "dev": "nodemon index.js"
        },
        "core_dependencies": {
            "express": "^4.18.0"
        },
        "dev_dependencies": {
            "nodemon": "^3.0.0"
        }
    },
    "python-fastapi": {
        "prerequisites": "- Python 3.10+ (https://python.org/)\n- pip",
        "install_command": "pip install -r requirements.txt",
        "run_command": "uvicorn main:app --reload",
        "additional_instructions": """
### Development

The API runs on `http://localhost:8000` by default.

API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Using Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```
""",
        "core_dependencies": [
            "fastapi>=0.100.0",
            "uvicorn>=0.23.0",
            "pydantic>=2.0.0"
        ]
    },
    "python-flask": {
        "prerequisites": "- Python 3.10+ (https://python.org/)\n- pip",
        "install_command": "pip install -r requirements.txt",
        "run_command": "flask run",
        "additional_instructions": """
### Development

The app runs on `http://localhost:5000` by default.

### Using Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```
""",
        "core_dependencies": [
            "flask>=3.0.0",
            "python-dotenv>=1.0.0"
        ]
    },
    "java-spring": {
        "prerequisites": "- Java 17+ (https://adoptium.net/)\n- Maven or Gradle",
        "install_command": "./mvnw install  # or: mvn install",
        "run_command": "./mvnw spring-boot:run  # or: mvn spring-boot:run",
        "additional_instructions": """
### Development

The app runs on `http://localhost:8080` by default.

### Building JAR

```bash
./mvnw package
java -jar target/*.jar
```
"""
    }
}


# =============================================================================
# FILES TO REMOVE BEFORE EXPORT (Platform-specific)
# =============================================================================

FILES_TO_REMOVE = [
    "error-capture.js",
    ".bharatbuild",
    ".bharatbuild.json",
    "__bharatbuild__",
    "bharatbuild.config.js",
]

PATTERNS_TO_REMOVE = [
    r"__ERROR_ENDPOINT__",
    r"__PROJECT_ID__",
    r"window\.__errorCapture",
    r"bharatbuild\.ai",
    r"/api/v1/errors/browser",
]


# =============================================================================
# EXPORT SERVICE
# =============================================================================

@dataclass
class ExportResult:
    """Result of project export"""
    success: bool
    zip_path: Optional[str] = None
    file_count: int = 0
    total_size: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    readme_generated: bool = False
    env_example_generated: bool = False


class ProjectExportService:
    """
    Service to export projects for local development.

    Ensures downloaded projects run without errors by:
    1. Validating project structure
    2. Completing package.json
    3. Generating README.md
    4. Creating .env.example
    5. Removing platform-specific code
    """

    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "bharatbuild_exports"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def export_project(
        self,
        project_path: str,
        project_name: str,
        description: str = "",
        framework: Optional[str] = None,
    ) -> ExportResult:
        """
        Export a project as a download-ready ZIP file.

        Args:
            project_path: Path to project files
            project_name: Name of the project
            description: Project description
            framework: Framework type (auto-detected if not provided)

        Returns:
            ExportResult with ZIP path or errors
        """
        result = ExportResult(success=False)

        try:
            source_path = Path(project_path)
            if not source_path.exists():
                result.errors.append(f"Project path does not exist: {project_path}")
                return result

            # Detect framework
            if not framework:
                framework = self._detect_framework(source_path)
                logger.info(f"[ProjectExport] Detected framework: {framework}")

            # Create temp directory for export
            export_id = f"{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            export_path = self.temp_dir / export_id

            # Copy project files
            shutil.copytree(source_path, export_path, dirs_exist_ok=True)

            # Process the export
            await self._remove_platform_files(export_path, result)
            await self._clean_platform_code(export_path, result)
            await self._ensure_package_json(export_path, framework, project_name, result)
            await self._generate_readme(export_path, project_name, description, framework, result)
            await self._generate_env_example(export_path, framework, result)
            await self._ensure_gitignore(export_path)
            await self._validate_project(export_path, framework, result)

            # Create ZIP file
            zip_path = await self._create_zip(export_path, project_name)

            # Count files and size
            result.file_count = sum(1 for _ in export_path.rglob("*") if _.is_file())
            result.total_size = sum(f.stat().st_size for f in export_path.rglob("*") if f.is_file())

            # Cleanup export directory
            shutil.rmtree(export_path)

            result.success = True
            result.zip_path = str(zip_path)

            logger.info(f"[ProjectExport] Successfully exported {project_name}: {result.file_count} files, {result.total_size} bytes")

        except Exception as e:
            logger.error(f"[ProjectExport] Export failed: {e}")
            result.errors.append(str(e))

        return result

    def _detect_framework(self, path: Path) -> str:
        """Detect project framework from files"""
        # Check for Next.js
        if (path / "next.config.js").exists() or (path / "next.config.mjs").exists():
            return "nextjs"

        # Check for Angular
        if (path / "angular.json").exists():
            return "angular"

        # Check for Vue
        if (path / "vue.config.js").exists() or any(path.glob("**/*.vue")):
            return "vue"

        # Check for Vite (React or Vue)
        if (path / "vite.config.ts").exists() or (path / "vite.config.js").exists():
            package_json = path / "package.json"
            if package_json.exists():
                data = json.loads(package_json.read_text())
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "vue" in deps:
                    return "vue"
                return "react-vite"

        # Check for Create React App
        package_json = path / "package.json"
        if package_json.exists():
            data = json.loads(package_json.read_text())
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "react-scripts" in deps:
                return "react-cra"
            if "express" in deps:
                return "express"

        # Check for Python
        if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
            if any(path.glob("**/main.py")):
                # Check for FastAPI
                reqs = (path / "requirements.txt").read_text() if (path / "requirements.txt").exists() else ""
                if "fastapi" in reqs.lower():
                    return "python-fastapi"
                if "flask" in reqs.lower():
                    return "python-flask"
            return "python-fastapi"  # Default to FastAPI

        # Check for Java
        if (path / "pom.xml").exists() or (path / "build.gradle").exists():
            return "java-spring"

        # Default to React Vite
        return "react-vite"

    async def _remove_platform_files(self, path: Path, result: ExportResult):
        """Remove BharatBuild-specific files"""
        for file_name in FILES_TO_REMOVE:
            for file_path in path.rglob(file_name):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                    result.warnings.append(f"Removed platform file: {file_name}")
                except Exception as e:
                    logger.warning(f"[ProjectExport] Failed to remove {file_path}: {e}")

    async def _clean_platform_code(self, path: Path, result: ExportResult):
        """Remove platform-specific code from files"""
        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in [".js", ".jsx", ".ts", ".tsx", ".html", ".vue"]:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                original = content

                # Remove error capture script injection
                content = re.sub(
                    r'<script[^>]*src=["\'][^"\']*error-capture\.js["\'][^>]*></script>',
                    '',
                    content
                )

                # Remove platform-specific globals
                for pattern in PATTERNS_TO_REMOVE:
                    content = re.sub(pattern, '', content)

                if content != original:
                    file_path.write_text(content, encoding="utf-8")

            except Exception as e:
                logger.warning(f"[ProjectExport] Failed to clean {file_path}: {e}")

    async def _ensure_package_json(
        self,
        path: Path,
        framework: str,
        project_name: str,
        result: ExportResult
    ):
        """Ensure package.json is complete with all dependencies"""
        package_path = path / "package.json"
        config = FRAMEWORK_CONFIGS.get(framework, {})

        if not package_path.exists():
            # Create package.json
            package_data = {
                "name": project_name.lower().replace(" ", "-"),
                "version": "1.0.0",
                "private": True,
                "scripts": config.get("required_scripts", {}),
                "dependencies": config.get("core_dependencies", {}),
                "devDependencies": config.get("dev_dependencies", {})
            }
        else:
            # Update existing package.json
            package_data = json.loads(package_path.read_text())

            # Ensure name
            if not package_data.get("name"):
                package_data["name"] = project_name.lower().replace(" ", "-")

            # Ensure scripts
            if "scripts" not in package_data:
                package_data["scripts"] = {}
            for script, command in config.get("required_scripts", {}).items():
                if script not in package_data["scripts"]:
                    package_data["scripts"][script] = command

            # Ensure core dependencies
            if "dependencies" not in package_data:
                package_data["dependencies"] = {}
            for dep, version in config.get("core_dependencies", {}).items():
                if dep not in package_data["dependencies"]:
                    package_data["dependencies"][dep] = version

            # Ensure dev dependencies
            if "devDependencies" not in package_data:
                package_data["devDependencies"] = {}
            for dep, version in config.get("dev_dependencies", {}).items():
                if dep not in package_data["devDependencies"]:
                    package_data["devDependencies"][dep] = version

        # Write updated package.json
        package_path.write_text(json.dumps(package_data, indent=2))
        logger.info(f"[ProjectExport] Updated package.json with {len(package_data.get('dependencies', {}))} dependencies")

    async def _generate_readme(
        self,
        path: Path,
        project_name: str,
        description: str,
        framework: str,
        result: ExportResult
    ):
        """Generate README.md with setup instructions"""
        readme_path = path / "README.md"
        config = FRAMEWORK_CONFIGS.get(framework, FRAMEWORK_CONFIGS["react-vite"])

        # Generate project structure
        structure_lines = []
        for item in sorted(path.iterdir()):
            if item.name.startswith(".") and item.name not in [".env.example", ".gitignore"]:
                continue
            if item.name == "node_modules":
                continue
            prefix = "├──" if item != list(path.iterdir())[-1] else "└──"
            structure_lines.append(f"{prefix} {item.name}{'/' if item.is_dir() else ''}")

        # Detect technologies
        technologies = self._detect_technologies(path)

        readme_content = README_TEMPLATE.format(
            project_name=project_name,
            description=description or "A web application generated with BharatBuild AI.",
            prerequisites=config.get("prerequisites", "- Node.js 18+"),
            install_command=config.get("install_command", "npm install"),
            run_command=config.get("run_command", "npm run dev"),
            additional_instructions=config.get("additional_instructions", ""),
            project_structure="\n".join(structure_lines),
            technologies="\n".join(f"- {tech}" for tech in technologies)
        )

        readme_path.write_text(readme_content)
        result.readme_generated = True
        logger.info(f"[ProjectExport] Generated README.md")

    def _detect_technologies(self, path: Path) -> List[str]:
        """Detect technologies used in the project"""
        technologies = []

        package_path = path / "package.json"
        if package_path.exists():
            data = json.loads(package_path.read_text())
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

            if "react" in deps:
                technologies.append("React")
            if "next" in deps:
                technologies.append("Next.js")
            if "vue" in deps:
                technologies.append("Vue.js")
            if "@angular/core" in deps:
                technologies.append("Angular")
            if "vite" in deps:
                technologies.append("Vite")
            if "tailwindcss" in deps:
                technologies.append("Tailwind CSS")
            if "typescript" in deps:
                technologies.append("TypeScript")
            if "express" in deps:
                technologies.append("Express.js")

        reqs_path = path / "requirements.txt"
        if reqs_path.exists():
            reqs = reqs_path.read_text().lower()
            if "fastapi" in reqs:
                technologies.append("FastAPI")
            if "flask" in reqs:
                technologies.append("Flask")
            if "django" in reqs:
                technologies.append("Django")

        if not technologies:
            technologies.append("JavaScript")

        return technologies

    async def _generate_env_example(self, path: Path, framework: str, result: ExportResult):
        """Generate .env.example file"""
        env_path = path / ".env.example"

        # Check for existing .env files to copy structure
        existing_env = path / ".env"
        existing_local = path / ".env.local"

        env_vars = []

        if existing_env.exists():
            for line in existing_env.read_text().splitlines():
                if line.strip() and not line.startswith("#") and "=" in line:
                    key = line.split("=")[0]
                    env_vars.append(f"{key}=your_value_here")
        elif existing_local.exists():
            for line in existing_local.read_text().splitlines():
                if line.strip() and not line.startswith("#") and "=" in line:
                    key = line.split("=")[0]
                    env_vars.append(f"{key}=your_value_here")

        # Add framework-specific defaults
        if framework in ["react-vite", "vue"]:
            if not any("VITE_" in v for v in env_vars):
                env_vars.append("VITE_API_URL=http://localhost:3000/api")
        elif framework == "nextjs":
            if not any("NEXT_PUBLIC_" in v for v in env_vars):
                env_vars.append("NEXT_PUBLIC_API_URL=http://localhost:3000/api")
        elif framework in ["python-fastapi", "python-flask"]:
            if not any("DATABASE_URL" in v for v in env_vars):
                env_vars.append("DATABASE_URL=sqlite:///./app.db")

        if env_vars:
            content = "# Environment Variables\n"
            content += "# Copy this file to .env and fill in your values\n\n"
            content += "\n".join(env_vars)
            env_path.write_text(content)
            result.env_example_generated = True
            logger.info(f"[ProjectExport] Generated .env.example with {len(env_vars)} variables")

    async def _ensure_gitignore(self, path: Path):
        """Ensure .gitignore exists"""
        gitignore_path = path / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text(GITIGNORE_TEMPLATE)
            logger.info(f"[ProjectExport] Generated .gitignore")

    async def _validate_project(self, path: Path, framework: str, result: ExportResult):
        """Validate project is ready for local development"""
        # Check for required files based on framework
        if framework in ["react-vite", "react-cra", "nextjs", "vue", "angular", "express"]:
            if not (path / "package.json").exists():
                result.errors.append("Missing package.json")

        if framework in ["python-fastapi", "python-flask"]:
            if not (path / "requirements.txt").exists():
                result.warnings.append("Missing requirements.txt - you may need to create it")

        # Check for entry point
        entry_points = [
            "index.html", "src/index.tsx", "src/index.ts", "src/index.js",
            "src/main.tsx", "src/main.ts", "src/App.tsx", "src/App.js",
            "pages/index.tsx", "pages/index.js", "app/page.tsx",
            "main.py", "app.py", "index.js", "server.js"
        ]
        has_entry = any((path / ep).exists() for ep in entry_points)
        if not has_entry:
            result.warnings.append("No entry point found - project may not run correctly")

    async def _create_zip(self, source_path: Path, project_name: str) -> Path:
        """Create ZIP file from project directory"""
        zip_name = f"{project_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = self.temp_dir / zip_name

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_path.rglob("*"):
                if file_path.is_file():
                    # Skip node_modules
                    if "node_modules" in file_path.parts:
                        continue
                    arcname = file_path.relative_to(source_path)
                    zipf.write(file_path, arcname)

        logger.info(f"[ProjectExport] Created ZIP: {zip_path}")
        return zip_path

    def cleanup_old_exports(self, max_age_hours: int = 24):
        """Clean up old export files"""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)

        for file_path in self.temp_dir.iterdir():
            if file_path.stat().st_mtime < cutoff:
                try:
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                except Exception as e:
                    logger.warning(f"[ProjectExport] Failed to cleanup {file_path}: {e}")


# Singleton instance
project_export = ProjectExportService()
