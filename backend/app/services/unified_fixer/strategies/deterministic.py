"""
Deterministic Fix Strategy (Tier 1)

FREE - No AI - Pattern-based fixes
Handles ~60% of common errors instantly
"""

import asyncio
import subprocess
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from app.core.logging_config import logger
from app.services.unified_fixer.classifier import ClassifiedError, ErrorCategory


@dataclass
class FixResult:
    """Result of a fix attempt"""
    success: bool
    fix_type: str                    # command, file_create, file_edit, config
    files_modified: List[str]
    command_run: Optional[str] = None
    error: Optional[str] = None
    time_ms: int = 0
    cost: float = 0.0


# Config file templates
CONFIG_TEMPLATES = {
    "tsconfig.node.json": '''{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}''',

    "postcss.config.js": '''module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}''',

    "postcss.config.cjs": '''module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}''',

    "tailwind.config.js": '''/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}''',

    ".env": '''# Environment variables
VITE_API_URL=http://localhost:8000
NODE_ENV=development
''',

    "vite.config.ts": '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})''',
}


class DeterministicStrategy:
    """
    Tier 1: Deterministic fix strategy.

    Handles:
    - Dependency installation (npm, pip)
    - Config file creation
    - Port conflicts
    - Common patterns

    NO AI - FREE - Instant
    """

    def __init__(self, file_manager=None):
        """
        Args:
            file_manager: UnifiedFileManager instance for file operations
        """
        self.file_manager = file_manager

    async def fix(
        self,
        classified_error: ClassifiedError,
        project_path: str,
        project_id: str,
        user_id: str
    ) -> FixResult:
        """
        Apply deterministic fix based on classified error.

        Args:
            classified_error: Classified error from ErrorClassifier
            project_path: Path to project
            project_id: Project ID
            user_id: User ID

        Returns:
            FixResult with success status and details
        """
        import time
        start_time = time.time()

        try:
            category = classified_error.category

            if category == ErrorCategory.DEPENDENCY:
                result = await self._fix_dependency(classified_error, project_path)

            elif category == ErrorCategory.CONFIG:
                result = await self._fix_config(
                    classified_error, project_path, project_id, user_id
                )

            elif category == ErrorCategory.PORT:
                result = await self._fix_port(classified_error)

            else:
                result = FixResult(
                    success=False,
                    fix_type="none",
                    files_modified=[],
                    error=f"Deterministic strategy cannot handle {category.value}"
                )

            result.time_ms = int((time.time() - start_time) * 1000)
            result.cost = 0.0  # Always free

            return result

        except Exception as e:
            logger.error(f"[DeterministicStrategy] Fix failed: {e}")
            return FixResult(
                success=False,
                fix_type="error",
                files_modified=[],
                error=str(e),
                time_ms=int((time.time() - start_time) * 1000)
            )

    async def _fix_dependency(
        self,
        error: ClassifiedError,
        project_path: str
    ) -> FixResult:
        """Install missing dependency"""
        if not error.fix_command:
            return FixResult(
                success=False,
                fix_type="command",
                files_modified=[],
                error="No fix command available"
            )

        command = error.fix_command
        logger.info(f"[DeterministicStrategy] Running: {command}")

        try:
            # Run installation command
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=120  # 2 min timeout
            )

            if process.returncode == 0:
                logger.info(f"[DeterministicStrategy] Installed: {error.module_name}")
                return FixResult(
                    success=True,
                    fix_type="command",
                    files_modified=["package.json"] if "npm" in command else ["requirements.txt"],
                    command_run=command
                )
            else:
                error_msg = stderr.decode()[:500] if stderr else "Unknown error"
                logger.warning(f"[DeterministicStrategy] Install failed: {error_msg}")
                return FixResult(
                    success=False,
                    fix_type="command",
                    files_modified=[],
                    command_run=command,
                    error=error_msg
                )

        except asyncio.TimeoutError:
            return FixResult(
                success=False,
                fix_type="command",
                files_modified=[],
                command_run=command,
                error="Command timed out"
            )

    async def _fix_config(
        self,
        error: ClassifiedError,
        project_path: str,
        project_id: str,
        user_id: str
    ) -> FixResult:
        """Create missing config file"""
        file_path = error.file_path
        content = error.fix_content

        # If no content provided, check templates
        if not content and file_path:
            import os
            filename = os.path.basename(file_path)
            content = CONFIG_TEMPLATES.get(filename)

        if not content or not file_path:
            return FixResult(
                success=False,
                fix_type="file_create",
                files_modified=[],
                error="No content template for this config file"
            )

        logger.info(f"[DeterministicStrategy] Creating config: {file_path}")

        try:
            if self.file_manager:
                # Use UnifiedFileManager (handles remote sandbox)
                success = await self.file_manager.write_file(
                    project_id, user_id, file_path, content,
                    normalize=False  # Config files stay at root
                )
            else:
                # Fallback to direct write
                import os
                full_path = os.path.join(project_path, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(content)
                success = True

            if success:
                return FixResult(
                    success=True,
                    fix_type="file_create",
                    files_modified=[file_path]
                )
            else:
                return FixResult(
                    success=False,
                    fix_type="file_create",
                    files_modified=[],
                    error="Failed to write file"
                )

        except Exception as e:
            return FixResult(
                success=False,
                fix_type="file_create",
                files_modified=[],
                error=str(e)
            )

    async def _fix_port(self, error: ClassifiedError) -> FixResult:
        """Handle port conflict"""
        if not error.module_name:
            return FixResult(
                success=False,
                fix_type="port",
                files_modified=[],
                error="No port number found"
            )

        port = int(error.module_name)
        logger.info(f"[DeterministicStrategy] Port {port} in use, attempting to kill")

        try:
            # Try to kill process using the port
            import platform

            if platform.system() == "Windows":
                # Windows: netstat + taskkill
                cmd = f'for /f "tokens=5" %a in (\'netstat -ano ^| findstr :{port}\') do taskkill /PID %a /F'
            else:
                # Linux/Mac: fuser or lsof
                cmd = f"fuser -k {port}/tcp 2>/dev/null || lsof -ti:{port} | xargs kill -9 2>/dev/null || true"

            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            await process.communicate()

            # Port killing is best-effort
            return FixResult(
                success=True,
                fix_type="port",
                files_modified=[],
                command_run=f"kill_port_{port}"
            )

        except Exception as e:
            logger.warning(f"[DeterministicStrategy] Port kill failed: {e}")
            return FixResult(
                success=False,
                fix_type="port",
                files_modified=[],
                error=str(e)
            )

    def can_handle(self, error: ClassifiedError) -> bool:
        """Check if this strategy can handle the error"""
        return error.category in [
            ErrorCategory.DEPENDENCY,
            ErrorCategory.CONFIG,
            ErrorCategory.PORT
        ]
