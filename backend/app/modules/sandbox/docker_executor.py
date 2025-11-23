"""
Docker Sandbox Executor
Executes user code in isolated Docker containers
Based on how Bolt.new and Replit execute code safely
"""

import docker
import tempfile
import os
import tarfile
import io
import asyncio
from typing import Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
import shutil

from app.core.logging_config import logger


@dataclass
class ExecutionResult:
    success: bool
    output: str
    error: Optional[str]
    exit_code: int
    execution_time: float
    container_id: Optional[str]


class DockerSandboxExecutor:
    """Execute code in Docker containers with resource limits"""

    # Container images for different environments
    IMAGES = {
        'node': 'node:18-alpine',
        'python': 'python:3.11-slim',
        'react': 'node:18-alpine',
        'nextjs': 'node:18-alpine',
        'vue': 'node:18-alpine'
    }

    # Default resource limits
    DEFAULT_LIMITS = {
        'mem_limit': '512m',          # 512MB RAM
        'memswap_limit': '512m',      # No swap
        'cpu_period': 100000,         # CPU period in microseconds
        'cpu_quota': 50000,           # CPU quota (50% of one core)
        'pids_limit': 100,            # Max processes
        'network_disabled': False,    # Allow network (for npm install)
    }

    def __init__(self):
        try:
            self.client = docker.from_env()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.client = None

    async def execute(
        self,
        files: List[Dict],
        command: str = "npm run dev",
        environment: str = "node",
        timeout: int = 30,
        stream_logs: bool = False
    ) -> ExecutionResult:
        """
        Execute code in a Docker container

        Args:
            files: List of file dicts with 'path' and 'content'
            command: Command to run
            environment: Environment type (node, python, react, etc.)
            timeout: Timeout in seconds
            stream_logs: Whether to stream logs in real-time

        Returns:
            ExecutionResult with output, errors, and metadata
        """
        if not self.client:
            return ExecutionResult(
                success=False,
                output="",
                error="Docker client not available",
                exit_code=1,
                execution_time=0.0,
                container_id=None
            )

        start_time = datetime.now()
        container = None
        temp_dir = None

        try:
            # Create temporary directory for project files
            temp_dir = tempfile.mkdtemp(prefix='bolt_sandbox_')

            # Write files to temp directory
            for file in files:
                if file.get('type') == 'folder':
                    continue

                file_path = os.path.join(temp_dir, file['path'])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file.get('content', ''))

            # Get container image
            image = self.IMAGES.get(environment, self.IMAGES['node'])

            # Pull image if not exists
            try:
                self.client.images.get(image)
            except docker.errors.ImageNotFound:
                logger.info(f"Pulling Docker image: {image}")
                self.client.images.pull(image)

            # Create container with resource limits
            container = self.client.containers.create(
                image=image,
                command=f'/bin/sh -c "{command}"',
                detach=True,
                mem_limit=self.DEFAULT_LIMITS['mem_limit'],
                memswap_limit=self.DEFAULT_LIMITS['memswap_limit'],
                cpu_period=self.DEFAULT_LIMITS['cpu_period'],
                cpu_quota=self.DEFAULT_LIMITS['cpu_quota'],
                pids_limit=self.DEFAULT_LIMITS['pids_limit'],
                network_disabled=self.DEFAULT_LIMITS['network_disabled'],
                working_dir='/app',
                volumes={
                    temp_dir: {'bind': '/app', 'mode': 'rw'}
                },
                # Security options
                security_opt=['no-new-privileges'],
                read_only=False,  # Need write for npm install
                tmpfs={
                    '/tmp': 'size=100M',
                    '/root/.npm': 'size=100M'
                }
            )

            # Start container
            container.start()

            # Wait for container with timeout
            try:
                result = container.wait(timeout=timeout)
                exit_code = result['StatusCode']
            except Exception as e:
                logger.warning(f"Container timeout: {e}")
                container.stop(timeout=5)
                exit_code = -1

            # Get logs
            output = container.logs(stdout=True, stderr=False).decode('utf-8')
            error_output = container.logs(stdout=False, stderr=True).decode('utf-8')

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            return ExecutionResult(
                success=(exit_code == 0),
                output=output,
                error=error_output if error_output else None,
                exit_code=exit_code,
                execution_time=execution_time,
                container_id=container.id
            )

        except Exception as e:
            logger.error(f"Docker execution error: {e}", exc_info=True)
            execution_time = (datetime.now() - start_time).total_seconds()

            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                exit_code=1,
                execution_time=execution_time,
                container_id=container.id if container else None
            )

        finally:
            # Cleanup
            if container:
                try:
                    container.remove(force=True)
                except Exception as e:
                    logger.warning(f"Failed to remove container: {e}")

            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to remove temp dir: {e}")

    async def execute_stream(
        self,
        files: List[Dict],
        command: str = "npm run dev",
        environment: str = "node",
        timeout: int = 30
    ) -> AsyncGenerator[str, None]:
        """
        Execute code and stream logs in real-time

        Yields:
            Log lines as they are generated
        """
        if not self.client:
            yield "ERROR: Docker client not available\n"
            return

        temp_dir = None
        container = None

        try:
            # Create temp directory and write files
            temp_dir = tempfile.mkdtemp(prefix='bolt_sandbox_')

            for file in files:
                if file.get('type') == 'folder':
                    continue

                file_path = os.path.join(temp_dir, file['path'])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file.get('content', ''))

            # Get image
            image = self.IMAGES.get(environment, self.IMAGES['node'])

            # Pull if needed
            try:
                self.client.images.get(image)
            except docker.errors.ImageNotFound:
                yield f"Pulling image {image}...\n"
                self.client.images.pull(image)

            # Create and start container
            container = self.client.containers.run(
                image=image,
                command=f'/bin/sh -c "{command}"',
                detach=True,
                mem_limit=self.DEFAULT_LIMITS['mem_limit'],
                memswap_limit=self.DEFAULT_LIMITS['memswap_limit'],
                cpu_period=self.DEFAULT_LIMITS['cpu_period'],
                cpu_quota=self.DEFAULT_LIMITS['cpu_quota'],
                pids_limit=self.DEFAULT_LIMITS['pids_limit'],
                network_disabled=self.DEFAULT_LIMITS['network_disabled'],
                working_dir='/app',
                volumes={
                    temp_dir: {'bind': '/app', 'mode': 'rw'}
                },
                security_opt=['no-new-privileges'],
                tmpfs={
                    '/tmp': 'size=100M',
                    '/root/.npm': 'size=100M'
                }
            )

            # Stream logs
            for log in container.logs(stream=True, follow=True):
                yield log.decode('utf-8')

                # Check if timeout exceeded
                # (In production, use asyncio.wait_for)

        except Exception as e:
            logger.error(f"Stream execution error: {e}", exc_info=True)
            yield f"ERROR: {str(e)}\n"

        finally:
            if container:
                try:
                    container.stop(timeout=5)
                    container.remove(force=True)
                except Exception as e:
                    logger.warning(f"Cleanup error: {e}")

            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Temp dir cleanup error: {e}")

    async def install_dependencies(
        self,
        files: List[Dict],
        environment: str = "node"
    ) -> ExecutionResult:
        """
        Install project dependencies

        Args:
            files: Project files
            environment: Environment type

        Returns:
            ExecutionResult with installation output
        """
        if environment in ['node', 'react', 'nextjs', 'vue']:
            # Check if package.json exists
            has_package_json = any(f['path'] == 'package.json' for f in files)

            if has_package_json:
                return await self.execute(
                    files=files,
                    command="npm install",
                    environment=environment,
                    timeout=120  # 2 minutes for npm install
                )
        elif environment == 'python':
            # Check if requirements.txt exists
            has_requirements = any(f['path'] == 'requirements.txt' for f in files)

            if has_requirements:
                return await self.execute(
                    files=files,
                    command="pip install -r requirements.txt",
                    environment=environment,
                    timeout=120
                )

        return ExecutionResult(
            success=True,
            output="No dependencies to install",
            error=None,
            exit_code=0,
            execution_time=0.0,
            container_id=None
        )

    async def run_tests(
        self,
        files: List[Dict],
        environment: str = "node"
    ) -> ExecutionResult:
        """Run project tests"""
        if environment in ['node', 'react', 'nextjs', 'vue']:
            command = "npm test"
        elif environment == 'python':
            command = "pytest"
        else:
            command = "echo 'No test command defined'"

        return await self.execute(
            files=files,
            command=command,
            environment=environment,
            timeout=60
        )

    async def build_project(
        self,
        files: List[Dict],
        environment: str = "node"
    ) -> ExecutionResult:
        """Build project for production"""
        if environment in ['node', 'react', 'nextjs', 'vue']:
            command = "npm run build"
        elif environment == 'python':
            command = "python setup.py build"
        else:
            command = "echo 'No build command defined'"

        return await self.execute(
            files=files,
            command=command,
            environment=environment,
            timeout=120
        )

    def check_docker_available(self) -> bool:
        """Check if Docker is available"""
        return self.client is not None

    async def get_container_stats(self, container_id: str) -> Dict:
        """Get resource usage stats for a container"""
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)
            return stats
        except Exception as e:
            logger.error(f"Failed to get container stats: {e}")
            return {}


# Singleton instance
docker_executor = DockerSandboxExecutor()
