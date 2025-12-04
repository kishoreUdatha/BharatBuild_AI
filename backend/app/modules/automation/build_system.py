"""
Build System - Build and compile projects for different tech stacks
"""

import asyncio
from pathlib import Path
from typing import Dict, Optional, AsyncGenerator
from enum import Enum

from app.core.logging_config import logger


class BuildTool(str, Enum):
    """Supported build tools"""
    VITE = "vite"
    WEBPACK = "webpack"
    NEXT = "next"
    CREATE_REACT_APP = "create-react-app"
    TSC = "tsc"
    MAVEN = "maven"
    GRADLE = "gradle"
    GO = "go"
    CARGO = "cargo"
    PYTHON = "python"


class BuildSystem:
    """Manages building and compilation for different tech stacks"""

    def __init__(self, base_path: str = None):
        if base_path is None:
            from app.core.config import settings
            base_path = str(settings.USER_PROJECTS_DIR)
        self.base_path = Path(base_path)

    def get_project_path(self, project_id: str) -> Path:
        """Get the full path for a project"""
        return self.base_path / project_id

    def detect_build_tool(self, project_id: str) -> Optional[BuildTool]:
        """Auto-detect build tool from project files"""
        project_path = self.get_project_path(project_id)

        # Check package.json for Node projects
        package_json = project_path / "package.json"
        if package_json.exists():
            import json
            with open(package_json, 'r') as f:
                data = json.load(f)
                scripts = data.get("scripts", {})
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

                # Check for Next.js
                if "next" in deps:
                    return BuildTool.NEXT

                # Check for Vite
                if "vite" in deps or "vite" in scripts.get("dev", ""):
                    return BuildTool.VITE

                # Check for Create React App
                if "react-scripts" in deps:
                    return BuildTool.CREATE_REACT_APP

                # Check for webpack
                if "webpack" in deps:
                    return BuildTool.WEBPACK

                # Check for TypeScript
                if "typescript" in deps:
                    return BuildTool.TSC

        # Check for Java
        if (project_path / "pom.xml").exists():
            return BuildTool.MAVEN
        if (project_path / "build.gradle").exists():
            return BuildTool.GRADLE

        # Check for Go
        if (project_path / "go.mod").exists():
            return BuildTool.GO

        # Check for Rust
        if (project_path / "Cargo.toml").exists():
            return BuildTool.CARGO

        # Check for Python
        if (project_path / "setup.py").exists() or (project_path / "pyproject.toml").exists():
            return BuildTool.PYTHON

        return None

    def get_build_command(self, build_tool: BuildTool) -> str:
        """Get the build command for a specific tool"""
        commands = {
            BuildTool.VITE: "npm run build",
            BuildTool.WEBPACK: "npm run build",
            BuildTool.NEXT: "npm run build",
            BuildTool.CREATE_REACT_APP: "npm run build",
            BuildTool.TSC: "tsc",
            BuildTool.MAVEN: "mvn clean package",
            BuildTool.GRADLE: "gradle build",
            BuildTool.GO: "go build",
            BuildTool.CARGO: "cargo build --release",
            BuildTool.PYTHON: "python setup.py build"
        }
        return commands.get(build_tool, "npm run build")

    def get_dev_command(self, build_tool: BuildTool) -> str:
        """Get the dev server command for a specific tool"""
        commands = {
            BuildTool.VITE: "npm run dev",
            BuildTool.WEBPACK: "npm run dev",
            BuildTool.NEXT: "npm run dev",
            BuildTool.CREATE_REACT_APP: "npm start",
            BuildTool.TSC: "tsc --watch",
            BuildTool.MAVEN: "mvn spring-boot:run",
            BuildTool.GRADLE: "gradle bootRun",
            BuildTool.GO: "go run .",
            BuildTool.CARGO: "cargo run",
            BuildTool.PYTHON: "python main.py"
        }
        return commands.get(build_tool, "npm run dev")

    async def build(
        self,
        project_id: str,
        build_tool: Optional[BuildTool] = None
    ) -> Dict:
        """
        Build the project

        Args:
            project_id: Project ID
            build_tool: Build tool to use (auto-detect if None)

        Returns:
            Dict with success, output, error, build_time
        """
        try:
            project_path = self.get_project_path(project_id)

            if not project_path.exists():
                return {
                    "success": False,
                    "error": f"Project {project_id} not found"
                }

            # Auto-detect build tool
            if build_tool is None:
                build_tool = self.detect_build_tool(project_id)

            if build_tool is None:
                return {
                    "success": False,
                    "error": "Could not detect build tool"
                }

            # Get build command
            command = self.get_build_command(build_tool)

            logger.info(f"Building {project_id} with {build_tool.value}: {command}")

            # Execute build
            import time
            start_time = time.time()

            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            build_time = time.time() - start_time
            success = process.returncode == 0

            result = {
                "success": success,
                "build_tool": build_tool.value,
                "command": command,
                "output": stdout.decode('utf-8') if stdout else "",
                "error": stderr.decode('utf-8') if stderr else "",
                "exit_code": process.returncode,
                "build_time": round(build_time, 2)
            }

            if success:
                logger.info(f"Build successful for {project_id} ({build_time:.2f}s)")
            else:
                logger.error(f"Build failed for {project_id}: {stderr.decode('utf-8')}")

            return result

        except Exception as e:
            logger.error(f"Error building project: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def build_stream(
        self,
        project_id: str,
        build_tool: Optional[BuildTool] = None
    ) -> AsyncGenerator[str, None]:
        """
        Build the project with streaming output

        Yields:
            Lines of build output
        """
        try:
            project_path = self.get_project_path(project_id)

            if not project_path.exists():
                yield f"Error: Project {project_id} not found"
                return

            if build_tool is None:
                build_tool = self.detect_build_tool(project_id)

            if build_tool is None:
                yield "Error: Could not detect build tool"
                return

            command = self.get_build_command(build_tool)

            logger.info(f"Building (streaming): {command}")

            yield f"Building with {build_tool.value}..."
            yield f"Command: {command}"
            yield ""

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

            yield ""
            if process.returncode == 0:
                yield "[OK] Build completed successfully"
            else:
                yield f"[FAIL] Build failed with exit code {process.returncode}"

        except Exception as e:
            logger.error(f"Error in build_stream: {e}")
            yield f"Error: {str(e)}"

    async def test(
        self,
        project_id: str,
        test_command: Optional[str] = None
    ) -> Dict:
        """
        Run tests

        Args:
            project_id: Project ID
            test_command: Custom test command (uses package.json script if None)

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

            # Default test command
            if test_command is None:
                build_tool = self.detect_build_tool(project_id)
                if build_tool in [BuildTool.VITE, BuildTool.NEXT, BuildTool.WEBPACK]:
                    test_command = "npm test"
                elif build_tool == BuildTool.MAVEN:
                    test_command = "mvn test"
                elif build_tool == BuildTool.GRADLE:
                    test_command = "gradle test"
                elif build_tool == BuildTool.GO:
                    test_command = "go test ./..."
                elif build_tool == BuildTool.CARGO:
                    test_command = "cargo test"
                elif build_tool == BuildTool.PYTHON:
                    test_command = "pytest"
                else:
                    test_command = "npm test"

            logger.info(f"Running tests: {test_command}")

            process = await asyncio.create_subprocess_shell(
                test_command,
                cwd=str(project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            success = process.returncode == 0

            return {
                "success": success,
                "command": test_command,
                "output": stdout.decode('utf-8') if stdout else "",
                "error": stderr.decode('utf-8') if stderr else "",
                "exit_code": process.returncode
            }

        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def lint(self, project_id: str) -> Dict:
        """Run linting"""
        try:
            project_path = self.get_project_path(project_id)

            # Try common linting commands
            commands = [
                "npm run lint",
                "eslint .",
                "pylint .",
                "mvn checkstyle:check"
            ]

            for command in commands:
                process = await asyncio.create_subprocess_shell(
                    command,
                    cwd=str(project_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                if process.returncode != 127:  # Command exists
                    return {
                        "success": process.returncode == 0,
                        "command": command,
                        "output": stdout.decode('utf-8') if stdout else "",
                        "error": stderr.decode('utf-8') if stderr else ""
                    }

            return {
                "success": False,
                "error": "No linting tool found"
            }

        except Exception as e:
            logger.error(f"Error running lint: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
build_system = BuildSystem()
