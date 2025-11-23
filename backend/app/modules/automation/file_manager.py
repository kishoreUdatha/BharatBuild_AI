"""
File System Manager - Create, read, update, delete project files
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime

from app.core.logging_config import logger
from app.modules.bolt.patch_applier import apply_unified_patch


class FileManager:
    """Manages project files on the file system"""

    def __init__(self, base_path: str = "./user_projects"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_project_path(self, project_id: str) -> Path:
        """Get the full path for a project"""
        return self.base_path / project_id

    async def create_project(self, project_id: str, name: str) -> Dict:
        """Create a new project directory"""
        try:
            project_path = self.get_project_path(project_id)

            if project_path.exists():
                raise FileExistsError(f"Project {project_id} already exists")

            project_path.mkdir(parents=True, exist_ok=True)

            # Create metadata file
            metadata = {
                "id": project_id,
                "name": name,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            metadata_path = project_path / ".project_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Created project: {project_id}")

            return {
                "success": True,
                "project_id": project_id,
                "path": str(project_path)
            }

        except Exception as e:
            logger.error(f"Error creating project {project_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def create_file(self, project_id: str, file_path: str, content: str) -> Dict:
        """Create a new file in the project"""
        try:
            project_path = self.get_project_path(project_id)
            full_path = project_path / file_path

            # Create parent directories
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Created file: {project_id}/{file_path}")

            return {
                "success": True,
                "path": file_path,
                "size": len(content)
            }

        except Exception as e:
            logger.error(f"Error creating file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def read_file(self, project_id: str, file_path: str) -> Optional[str]:
        """Read file content"""
        try:
            project_path = self.get_project_path(project_id)
            full_path = project_path / file_path

            if not full_path.exists():
                return None

            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None

    async def update_file(self, project_id: str, file_path: str, content: str) -> Dict:
        """Update existing file content"""
        try:
            project_path = self.get_project_path(project_id)
            full_path = project_path / file_path

            if not full_path.exists():
                return await self.create_file(project_id, file_path, content)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Updated file: {project_id}/{file_path}")

            return {
                "success": True,
                "path": file_path,
                "size": len(content)
            }

        except Exception as e:
            logger.error(f"Error updating file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def apply_patch(self, project_id: str, file_path: str, patch: str) -> Dict:
        """Apply a unified diff patch to a file"""
        try:
            # Read original content
            original_content = await self.read_file(project_id, file_path)

            if original_content is None:
                return {
                    "success": False,
                    "error": f"File {file_path} not found"
                }

            # Apply patch
            result = apply_unified_patch(original_content, patch)

            if not result.get('success'):
                return result

            # Write patched content
            await self.update_file(project_id, file_path, result['patched_content'])

            return {
                "success": True,
                "path": file_path,
                "changes": result.get('changes', [])
            }

        except Exception as e:
            logger.error(f"Error applying patch to {file_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def delete_file(self, project_id: str, file_path: str) -> Dict:
        """Delete a file"""
        try:
            project_path = self.get_project_path(project_id)
            full_path = project_path / file_path

            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File {file_path} not found"
                }

            full_path.unlink()

            logger.info(f"Deleted file: {project_id}/{file_path}")

            return {
                "success": True,
                "path": file_path
            }

        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_file_tree(self, project_id: str) -> List[Dict]:
        """Get the project file tree structure"""
        try:
            project_path = self.get_project_path(project_id)

            if not project_path.exists():
                return []

            def build_tree(path: Path, parent_path: str = "") -> List[Dict]:
                items = []

                try:
                    for item in sorted(path.iterdir()):
                        # Skip hidden files and metadata
                        if item.name.startswith('.'):
                            continue

                        relative_path = str(item.relative_to(project_path))

                        if item.is_dir():
                            items.append({
                                "path": relative_path,
                                "name": item.name,
                                "type": "directory",
                                "children": build_tree(item, relative_path)
                            })
                        else:
                            # Detect language from extension
                            ext = item.suffix.lower()
                            language_map = {
                                '.js': 'javascript',
                                '.jsx': 'javascript',
                                '.ts': 'typescript',
                                '.tsx': 'typescript',
                                '.py': 'python',
                                '.java': 'java',
                                '.go': 'go',
                                '.rs': 'rust',
                                '.html': 'html',
                                '.css': 'css',
                                '.json': 'json',
                                '.md': 'markdown',
                                '.yml': 'yaml',
                                '.yaml': 'yaml',
                            }

                            items.append({
                                "path": relative_path,
                                "name": item.name,
                                "type": "file",
                                "language": language_map.get(ext, 'plaintext'),
                                "size": item.stat().st_size
                            })

                except PermissionError:
                    pass

                return items

            return build_tree(project_path)

        except Exception as e:
            logger.error(f"Error getting file tree for {project_id}: {e}")
            return []

    async def delete_project(self, project_id: str) -> Dict:
        """Delete entire project"""
        try:
            project_path = self.get_project_path(project_id)

            if not project_path.exists():
                return {
                    "success": False,
                    "error": f"Project {project_id} not found"
                }

            shutil.rmtree(project_path)

            logger.info(f"Deleted project: {project_id}")

            return {
                "success": True,
                "project_id": project_id
            }

        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
file_manager = FileManager()
