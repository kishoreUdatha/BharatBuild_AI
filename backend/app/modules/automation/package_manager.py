"""
Package Manager - Install dependencies for different tech stacks
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum

from app.core.logging_config import logger


class PackageManagerType(str, Enum):
    """Supported package managers"""
    NPM = "npm"
    YARN = "yarn"
    PNPM = "pnpm"
    PIP = "pip"
    POETRY = "poetry"
    MAVEN = "maven"
    GRADLE = "gradle"
    GO = "go"
    CARGO = "cargo"


class PackageManager:
    """Manages package installation for different tech stacks"""

    def __init__(self, base_path: str = "./user_projects"):
        self.base_path = Path(base_path)

    def get_project_path(self, project_id: str) -> Path:
        """Get the full path for a project"""
        return self.base_path / project_id

    def detect_package_manager(self, project_id: str) -> PackageManagerType:
        """Auto-detect package manager from project files"""
        project_path = self.get_project_path(project_id)

        # Check for lock files
        if (project_path / "pnpm-lock.yaml").exists():
            return PackageManagerType.PNPM
        elif (project_path / "yarn.lock").exists():
            return PackageManagerType.YARN
        elif (project_path / "package-lock.json").exists() or (project_path / "package.json").exists():
            return PackageManagerType.NPM

        # Check for Python
        if (project_path / "requirements.txt").exists():
            return PackageManagerType.PIP
        elif (project_path / "pyproject.toml").exists():
            return PackageManagerType.POETRY

        # Check for Java
        if (project_path / "pom.xml").exists():
            return PackageManagerType.MAVEN
        elif (project_path / "build.gradle").exists():
            return PackageManagerType.GRADLE

        # Check for Go
        if (project_path / "go.mod").exists():
            return PackageManagerType.GO

        # Check for Rust
        if (project_path / "Cargo.toml").exists():
            return PackageManagerType.CARGO

        # Default to npm
        return PackageManagerType.NPM

    async def install(
        self,
        project_id: str,
        packages: Optional[List[str]] = None,
        manager: Optional[PackageManagerType] = None,
        dev: bool = False
    ) -> Dict:
        """
        Install packages

        Args:
            project_id: Project ID
            packages: List of packages to install (None = install all from manifest)
            manager: Package manager to use (auto-detect if None)
            dev: Install as dev dependencies

        Returns:
            Dict with success, output, error
        """
        try:
            project_path = self.get_project_path(project_id)

            if not project_path.exists():
                return {
                    "success": False,
                    "error": f"Project {project_id} not found"
                }

            # Auto-detect manager if not provided
            if manager is None:
                manager = self.detect_package_manager(project_id)

            # Build install command
            command = self._build_install_command(manager, packages, dev)

            logger.info(f"Installing packages in {project_id}: {command}")

            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            success = process.returncode == 0

            return {
                "success": success,
                "manager": manager.value,
                "packages": packages or "all",
                "output": stdout.decode('utf-8') if stdout else "",
                "error": stderr.decode('utf-8') if stderr else "",
                "exit_code": process.returncode
            }

        except Exception as e:
            logger.error(f"Error installing packages: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def install_stream(
        self,
        project_id: str,
        packages: Optional[List[str]] = None,
        manager: Optional[PackageManagerType] = None,
        dev: bool = False
    ):
        """
        Install packages with streaming output

        Yields:
            Lines of installation output
        """
        try:
            project_path = self.get_project_path(project_id)

            if not project_path.exists():
                yield f"Error: Project {project_id} not found"
                return

            if manager is None:
                manager = self.detect_package_manager(project_id)

            command = self._build_install_command(manager, packages, dev)

            logger.info(f"Installing packages (streaming): {command}")

            # Execute with streaming output
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            # Stream output line by line
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                yield line.decode('utf-8').rstrip()

            await process.wait()

            if process.returncode == 0:
                yield "✓ Installation completed successfully"
            else:
                yield f"✗ Installation failed with exit code {process.returncode}"

        except Exception as e:
            logger.error(f"Error in install_stream: {e}")
            yield f"Error: {str(e)}"

    def _build_install_command(
        self,
        manager: PackageManagerType,
        packages: Optional[List[str]],
        dev: bool
    ) -> str:
        """Build the install command based on manager type"""

        if manager == PackageManagerType.NPM:
            if packages:
                dev_flag = "--save-dev" if dev else "--save"
                return f"npm install {dev_flag} {' '.join(packages)}"
            return "npm install"

        elif manager == PackageManagerType.YARN:
            if packages:
                dev_flag = "--dev" if dev else ""
                return f"yarn add {dev_flag} {' '.join(packages)}"
            return "yarn install"

        elif manager == PackageManagerType.PNPM:
            if packages:
                dev_flag = "--save-dev" if dev else ""
                return f"pnpm add {dev_flag} {' '.join(packages)}"
            return "pnpm install"

        elif manager == PackageManagerType.PIP:
            if packages:
                return f"pip install {' '.join(packages)}"
            return "pip install -r requirements.txt"

        elif manager == PackageManagerType.POETRY:
            if packages:
                dev_flag = "--group dev" if dev else ""
                return f"poetry add {dev_flag} {' '.join(packages)}"
            return "poetry install"

        elif manager == PackageManagerType.MAVEN:
            return "mvn clean install"

        elif manager == PackageManagerType.GRADLE:
            return "gradle build"

        elif manager == PackageManagerType.GO:
            if packages:
                return f"go get {' '.join(packages)}"
            return "go mod download"

        elif manager == PackageManagerType.CARGO:
            if packages:
                return f"cargo add {' '.join(packages)}"
            return "cargo build"

        return "echo 'Unknown package manager'"

    async def add_package_to_manifest(
        self,
        project_id: str,
        package_name: str,
        version: Optional[str] = None,
        dev: bool = False
    ) -> Dict:
        """
        Add a package to package.json (for npm/yarn/pnpm projects)

        Args:
            project_id: Project ID
            package_name: Package name
            version: Package version (latest if None)
            dev: Add to devDependencies
        """
        try:
            project_path = self.get_project_path(project_id)
            package_json_path = project_path / "package.json"

            if not package_json_path.exists():
                return {
                    "success": False,
                    "error": "package.json not found"
                }

            # Read package.json
            with open(package_json_path, 'r') as f:
                package_json = json.load(f)

            # Add package
            dep_key = "devDependencies" if dev else "dependencies"

            if dep_key not in package_json:
                package_json[dep_key] = {}

            package_json[dep_key][package_name] = version or "latest"

            # Write back
            with open(package_json_path, 'w') as f:
                json.dump(package_json, f, indent=2)

            logger.info(f"Added {package_name} to {dep_key}")

            return {
                "success": True,
                "package": package_name,
                "version": version or "latest",
                "type": dep_key
            }

        except Exception as e:
            logger.error(f"Error adding package to manifest: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_installed_packages(self, project_id: str) -> Dict:
        """Get list of installed packages"""
        try:
            project_path = self.get_project_path(project_id)
            manager = self.detect_package_manager(project_id)

            if manager in [PackageManagerType.NPM, PackageManagerType.YARN, PackageManagerType.PNPM]:
                package_json_path = project_path / "package.json"
                if package_json_path.exists():
                    with open(package_json_path, 'r') as f:
                        data = json.load(f)
                        return {
                            "success": True,
                            "dependencies": data.get("dependencies", {}),
                            "devDependencies": data.get("devDependencies", {})
                        }

            elif manager == PackageManagerType.PIP:
                req_path = project_path / "requirements.txt"
                if req_path.exists():
                    with open(req_path, 'r') as f:
                        packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                        return {
                            "success": True,
                            "dependencies": packages
                        }

            return {
                "success": False,
                "error": "No package manifest found"
            }

        except Exception as e:
            logger.error(f"Error getting installed packages: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
package_manager = PackageManager()
