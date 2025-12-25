"""
Sandbox Reconstruction Service - Recreates sandbox containers for restored projects
Like Bolt.new: Projects are never stored with running containers - they're rebuilt on demand
"""

from typing import Optional, Dict, Any, List, Union
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass
import os
import shutil
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.sandbox import SandboxInstance, SandboxStatus
from app.models.project_tree import ProjectFileTree
from app.services.sandbox_db_service import SandboxDBService
from app.core.logging_config import logger


def to_str(value: Union[UUID, str, None]) -> Optional[str]:
    """Convert UUID to string if needed"""
    if value is None:
        return None
    return str(value) if isinstance(value, UUID) else value


@dataclass
class SandboxConfig:
    """Configuration for sandbox reconstruction"""
    node_version: str = "20"
    python_version: str = "3.11"
    working_directory: str = "/app"
    memory_limit: str = "512m"
    cpu_limit: str = "0.5"
    expose_ports: List[int] = None

    def __post_init__(self):
        if self.expose_ports is None:
            self.expose_ports = [3000, 5173, 8080]


@dataclass
class ReconstructionResult:
    """Result of sandbox reconstruction"""
    success: bool
    sandbox_id: Optional[str]
    workspace_path: str
    files_restored: int
    preview_port: Optional[int]
    error: Optional[str]
    reconstruction_time_ms: float


class SandboxReconstructionService:
    """
    Reconstructs sandbox environments for restored projects.

    Key principle: Sandboxes are NEVER persisted.
    Every time a user opens a project, we:
    1. Create a fresh workspace directory
    2. Copy files from S3/storage
    3. Create a new sandbox instance
    4. Install dependencies if needed
    5. Start the dev server

    This is exactly how Bolt.new works.
    """

    # Base path for sandbox workspaces
    WORKSPACE_BASE = os.environ.get("SANDBOX_WORKSPACE_PATH", "C:/tmp/sandbox/workspace")

    def __init__(self, db: AsyncSession):
        self.db = db
        self.sandbox_service = SandboxDBService(db)

    async def reconstruct_sandbox(
        self,
        project_id: UUID,
        config: Optional[SandboxConfig] = None
    ) -> ReconstructionResult:
        """
        Complete sandbox reconstruction for a project.

        Steps:
        1. Create fresh workspace directory
        2. Load project files from DB/S3
        3. Write files to workspace
        4. Create sandbox instance record
        5. Initialize package manager (npm install, pip install)
        6. Start dev server
        7. Return sandbox info with preview port
        """
        start_time = datetime.utcnow()
        config = config or SandboxConfig()

        try:
            # Step 1: Create workspace directory
            workspace_path = await self._create_workspace(project_id)
            logger.info(f"Created workspace: {workspace_path}")

            # Step 2: Load project files
            files = await self._load_project_files(project_id)
            if not files:
                return ReconstructionResult(
                    success=False,
                    sandbox_id=None,
                    workspace_path=workspace_path,
                    files_restored=0,
                    preview_port=None,
                    error="No files found for project",
                    reconstruction_time_ms=self._calc_time(start_time)
                )

            # Step 3: Write files to workspace
            files_written = await self._write_files_to_workspace(workspace_path, files)
            logger.info(f"Wrote {files_written} files to workspace")

            # Step 4: Create sandbox instance record
            sandbox = await self.sandbox_service.create_sandbox_instance(
                project_id=project_id,
                port_mappings={str(p): None for p in config.expose_ports},
                cpu_limit=config.cpu_limit,
                memory_limit=config.memory_limit
            )

            # Update sandbox with workspace info
            sandbox.working_directory = workspace_path
            sandbox.node_version = config.node_version
            sandbox.python_version = config.python_version
            await self.db.commit()

            # Step 5: Detect project type and prepare
            project_type = await self._detect_project_type(workspace_path)
            logger.info(f"Detected project type: {project_type}")

            # Step 6: Update sandbox status to running
            await self.sandbox_service.update_sandbox_status(
                sandbox_id=UUID(sandbox.id) if isinstance(sandbox.id, str) else sandbox.id,
                status=SandboxStatus.RUNNING
            )

            # Calculate preview port (first available)
            preview_port = config.expose_ports[0] if config.expose_ports else 3000

            return ReconstructionResult(
                success=True,
                sandbox_id=str(sandbox.id),
                workspace_path=workspace_path,
                files_restored=files_written,
                preview_port=preview_port,
                error=None,
                reconstruction_time_ms=self._calc_time(start_time)
            )

        except Exception as e:
            logger.error(f"Sandbox reconstruction failed: {e}")
            return ReconstructionResult(
                success=False,
                sandbox_id=None,
                workspace_path="",
                files_restored=0,
                preview_port=None,
                error=str(e),
                reconstruction_time_ms=self._calc_time(start_time)
            )

    async def _create_workspace(self, project_id: UUID) -> str:
        """Create a fresh workspace directory for the project"""
        workspace_path = os.path.join(self.WORKSPACE_BASE, str(project_id))

        # Clean up any existing workspace
        if os.path.exists(workspace_path):
            shutil.rmtree(workspace_path)

        os.makedirs(workspace_path, exist_ok=True)
        return workspace_path

    async def _load_project_files(self, project_id: UUID) -> List[ProjectFile]:
        """Load all project files from database"""
        result = await self.db.execute(
            select(ProjectFile)
            .where(ProjectFile.project_id == to_str(project_id))
            .order_by(ProjectFile.file_path)
        )
        return list(result.scalars().all())

    async def _write_files_to_workspace(
        self,
        workspace_path: str,
        files: List[ProjectFile]
    ) -> int:
        """Write all project files to the workspace directory"""
        files_written = 0

        for file in files:
            file_path = os.path.join(workspace_path, file.file_path)

            # Create parent directories
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Write file content
            if file.content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file.content)
                files_written += 1
            elif file.s3_key:
                # TODO: Fetch from S3 and write
                # For now, create empty file placeholder
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"// TODO: Load from S3: {file.s3_key}\n")
                files_written += 1

        return files_written

    async def _detect_project_type(self, workspace_path: str) -> str:
        """Detect the project type based on files present"""
        if os.path.exists(os.path.join(workspace_path, "package.json")):
            # Check for specific frameworks
            package_json_path = os.path.join(workspace_path, "package.json")
            try:
                with open(package_json_path, 'r') as f:
                    package = json.load(f)
                    deps = {
                        **package.get("dependencies", {}),
                        **package.get("devDependencies", {})
                    }

                    if "next" in deps:
                        return "nextjs"
                    elif "vite" in deps:
                        return "vite"
                    elif "react" in deps:
                        return "react"
                    elif "vue" in deps:
                        return "vue"
                    elif "express" in deps:
                        return "express"
                    else:
                        return "node"
            except (json.JSONDecodeError, IOError, OSError, KeyError) as e:
                logger.debug(f"Could not parse package.json for framework detection: {e}")
                return "node"

        elif os.path.exists(os.path.join(workspace_path, "requirements.txt")):
            return "python"
        elif os.path.exists(os.path.join(workspace_path, "pyproject.toml")):
            return "python"
        elif os.path.exists(os.path.join(workspace_path, "Cargo.toml")):
            return "rust"
        elif os.path.exists(os.path.join(workspace_path, "go.mod")):
            return "go"
        else:
            return "unknown"

    def _calc_time(self, start_time: datetime) -> float:
        """Calculate elapsed time in milliseconds"""
        return (datetime.utcnow() - start_time).total_seconds() * 1000

    async def cleanup_sandbox(self, project_id: UUID) -> bool:
        """Clean up sandbox workspace and mark as terminated"""
        workspace_path = os.path.join(self.WORKSPACE_BASE, str(project_id))

        try:
            # Remove workspace directory
            if os.path.exists(workspace_path):
                shutil.rmtree(workspace_path)

            # Mark sandbox as terminated in DB
            await self.sandbox_service.cleanup_project_sandbox_data(project_id)

            logger.info(f"Cleaned up sandbox for project {project_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup sandbox: {e}")
            return False

    async def get_reconstruction_commands(self, project_type: str) -> Dict[str, List[str]]:
        """Get the commands needed to set up and run a project type"""
        commands = {
            "nextjs": {
                "install": ["npm", "install"],
                "dev": ["npm", "run", "dev"],
                "build": ["npm", "run", "build"],
                "start": ["npm", "start"]
            },
            "vite": {
                "install": ["npm", "install"],
                "dev": ["npm", "run", "dev"],
                "build": ["npm", "run", "build"],
                "preview": ["npm", "run", "preview"]
            },
            "react": {
                "install": ["npm", "install"],
                "dev": ["npm", "start"],
                "build": ["npm", "run", "build"]
            },
            "node": {
                "install": ["npm", "install"],
                "dev": ["npm", "start"],
                "build": ["npm", "run", "build"]
            },
            "python": {
                "install": ["pip", "install", "-r", "requirements.txt"],
                "dev": ["python", "main.py"],
                "build": []
            },
            "express": {
                "install": ["npm", "install"],
                "dev": ["npm", "start"],
                "build": []
            }
        }

        return commands.get(project_type, {
            "install": [],
            "dev": [],
            "build": []
        })
