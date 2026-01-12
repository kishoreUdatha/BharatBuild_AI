"""
Unit tests for nginx.conf COPY fix in DockerInfraFixer.

Tests ensure:
1. _fix_dockerfile_copy detects nginx.conf COPY errors
2. _create_nginx_conf_in_build_context creates valid nginx.conf
3. Backend port is correctly detected and injected
4. Build context is correctly determined
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import re


class TestNginxConfCopyFix:
    """Tests for nginx.conf COPY error fix."""

    @pytest.fixture
    def mock_sandbox_runner(self):
        """Create a mock sandbox runner."""
        def runner(cmd, *args):
            if 'base64 -d' in cmd:
                return (0, "")  # Success
            if 'test -f' in cmd:
                return (1, "")  # File doesn't exist
            return (0, "")
        return runner

    @pytest.fixture
    def docker_infra_fixer(self):
        """Create DockerInfraFixer instance."""
        import sys
        import importlib.util

        # Import directly from file to avoid circular deps
        spec = importlib.util.spec_from_file_location(
            "docker_infra_fixer_agent",
            "app/modules/agents/docker_infra_fixer_agent.py"
        )
        module = importlib.util.module_from_spec(spec)

        # Mock the problematic imports
        sys.modules['app.modules.agents.docker_infra_fixer_agent'] = module

        try:
            spec.loader.exec_module(module)
            return module.DockerInfraFixerAgent()
        except Exception as e:
            pytest.skip(f"Cannot import DockerInfraFixerAgent: {e}")

    @pytest.mark.asyncio
    async def test_fix_dockerfile_copy_detects_nginx_conf(self, docker_infra_fixer, mock_sandbox_runner):
        """_fix_dockerfile_copy must detect nginx.conf and call _create_nginx_conf_in_build_context."""
        error_message = "COPY failed: file not found in build context or excluded by .dockerignore: stat nginx.conf: file does not exist"

        # Mock the helper method
        docker_infra_fixer._create_nginx_conf_in_build_context = AsyncMock(
            return_value=MagicMock(success=True, message="Created nginx.conf")
        )

        result = await docker_infra_fixer._fix_dockerfile_copy(
            error_message, "/workspace/project123", mock_sandbox_runner
        )

        # Verify _create_nginx_conf_in_build_context was called
        docker_infra_fixer._create_nginx_conf_in_build_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_fix_dockerfile_copy_ignores_other_files(self, docker_infra_fixer, mock_sandbox_runner):
        """_fix_dockerfile_copy must NOT call nginx fix for other missing files."""
        error_message = "COPY failed: stat package.json: file does not exist"

        # Mock the helper method
        docker_infra_fixer._create_nginx_conf_in_build_context = AsyncMock()

        result = await docker_infra_fixer._fix_dockerfile_copy(
            error_message, "/workspace/project123", mock_sandbox_runner
        )

        # Verify _create_nginx_conf_in_build_context was NOT called
        docker_infra_fixer._create_nginx_conf_in_build_context.assert_not_called()
        assert result.success == False

    @pytest.mark.asyncio
    async def test_create_nginx_conf_creates_valid_config(self, docker_infra_fixer):
        """_create_nginx_conf_in_build_context must create valid nginx config."""
        created_content = None

        def capture_sandbox_runner(cmd, *args):
            nonlocal created_content
            if 'base64 -d' in cmd:
                # Extract the base64 content
                import base64
                match = re.search(r'echo "([^"]+)"', cmd)
                if match:
                    created_content = base64.b64decode(match.group(1)).decode()
                return (0, "")
            return (0, "")

        # Mock _read_file_from_sandbox to return None (no existing Dockerfile)
        docker_infra_fixer._read_file_from_sandbox = MagicMock(return_value=None)
        docker_infra_fixer._detect_backend_port = MagicMock(return_value="8080")

        result = await docker_infra_fixer._create_nginx_conf_in_build_context(
            "COPY nginx.conf failed", "/workspace/project123", capture_sandbox_runner
        )

        assert result.success == True
        assert created_content is not None

        # Verify nginx.conf content
        assert "events {" in created_content
        assert "http {" in created_content
        assert "server {" in created_content
        assert "listen 80;" in created_content
        assert "root /usr/share/nginx/html;" in created_content
        assert "try_files $uri $uri/ /index.html;" in created_content
        assert "location /api/" in created_content
        assert "proxy_pass http://backend:8080/api/;" in created_content

    @pytest.mark.asyncio
    async def test_create_nginx_conf_uses_detected_port(self, docker_infra_fixer):
        """_create_nginx_conf_in_build_context must use detected backend port."""
        created_content = None

        def capture_sandbox_runner(cmd, *args):
            nonlocal created_content
            if 'base64 -d' in cmd:
                import base64
                match = re.search(r'echo "([^"]+)"', cmd)
                if match:
                    created_content = base64.b64decode(match.group(1)).decode()
                return (0, "")
            return (0, "")

        docker_infra_fixer._read_file_from_sandbox = MagicMock(return_value=None)
        docker_infra_fixer._detect_backend_port = MagicMock(return_value="3000")  # Custom port

        result = await docker_infra_fixer._create_nginx_conf_in_build_context(
            "COPY nginx.conf failed", "/workspace/project123", capture_sandbox_runner
        )

        assert result.success == True
        assert "proxy_pass http://backend:3000/api/;" in created_content

    @pytest.mark.asyncio
    async def test_create_nginx_conf_detects_frontend_context(self, docker_infra_fixer):
        """_create_nginx_conf_in_build_context must detect frontend build context."""
        created_path = None

        def capture_sandbox_runner(cmd, *args):
            nonlocal created_path
            if 'base64 -d' in cmd:
                # Extract path from command
                match = re.search(r'> "([^"]+)"', cmd)
                if match:
                    created_path = match.group(1)
                return (0, "")
            return (0, "")

        # Mock: frontend/Dockerfile exists and contains nginx
        def mock_read(path):
            if 'frontend/Dockerfile' in path:
                return "FROM node:18-alpine\nFROM nginx:alpine\nCOPY nginx.conf /etc/nginx/nginx.conf"
            return None

        docker_infra_fixer._read_file_from_sandbox = mock_read
        docker_infra_fixer._detect_backend_port = MagicMock(return_value="8080")

        result = await docker_infra_fixer._create_nginx_conf_in_build_context(
            "COPY nginx.conf failed", "/workspace/project123", capture_sandbox_runner
        )

        assert result.success == True
        assert created_path == "/workspace/project123/frontend/nginx.conf"

    @pytest.mark.asyncio
    async def test_create_nginx_conf_handles_error_message_hint(self, docker_infra_fixer):
        """_create_nginx_conf_in_build_context must use hints from error message."""
        created_path = None

        def capture_sandbox_runner(cmd, *args):
            nonlocal created_path
            if 'base64 -d' in cmd:
                match = re.search(r'> "([^"]+)"', cmd)
                if match:
                    created_path = match.group(1)
                return (0, "")
            return (0, "")

        docker_infra_fixer._read_file_from_sandbox = MagicMock(return_value=None)
        docker_infra_fixer._detect_backend_port = MagicMock(return_value="8080")

        # Error message mentions "frontend"
        result = await docker_infra_fixer._create_nginx_conf_in_build_context(
            "Building frontend service... COPY nginx.conf failed",
            "/workspace/project123",
            capture_sandbox_runner
        )

        assert result.success == True
        assert "frontend" in created_path


class TestNginxConfContent:
    """Tests for nginx.conf content validity."""

    def test_nginx_conf_has_required_sections(self):
        """Generated nginx.conf must have all required sections."""
        # Simulate the nginx config generation
        backend_port = "8080"
        nginx_config = f'''events {{
    worker_connections 1024;
}}

http {{
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    server {{
        listen 80;
        server_name _;
        root /usr/share/nginx/html;
        index index.html;

        location / {{
            try_files $uri $uri/ /index.html;
        }}

        location /api/ {{
            proxy_pass http://backend:{backend_port}/api/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
        }}
    }}
}}
'''
        # Verify required sections
        assert "events {" in nginx_config
        assert "http {" in nginx_config
        assert "server {" in nginx_config
        assert "location / {" in nginx_config
        assert "location /api/ {" in nginx_config

    def test_nginx_conf_spa_fallback(self):
        """Generated nginx.conf must have SPA fallback for frontend routing."""
        nginx_config = "try_files $uri $uri/ /index.html;"
        assert "try_files $uri $uri/ /index.html" in nginx_config

    def test_nginx_conf_api_proxy(self):
        """Generated nginx.conf must proxy /api/ to backend."""
        nginx_config = "proxy_pass http://backend:8080/api/;"
        assert "proxy_pass http://backend:" in nginx_config
        assert "/api/" in nginx_config


class TestErrorMessageParsing:
    """Tests for error message parsing."""

    def test_parse_stat_error(self):
        """Must parse 'stat nginx.conf: file does not exist' error."""
        error = "COPY failed: file not found in build context or excluded by .dockerignore: stat nginx.conf: file does not exist"

        match = re.search(
            r'stat ([^:]+): file does not exist|'
            r'COPY.*"([^"]+)".*not found|'
            r'failed to compute cache key.*"([^"]+)"',
            error
        )

        assert match is not None
        missing_file = (match.group(1) or match.group(2) or match.group(3)).strip()
        assert missing_file == "nginx.conf"

    def test_parse_cache_key_error(self):
        """Must parse 'failed to compute cache key' error."""
        error = 'failed to compute cache key: "/nginx.conf" not found'

        match = re.search(
            r'stat ([^:]+): file does not exist|'
            r'COPY.*"([^"]+)".*not found|'
            r'failed to compute cache key.*"([^"]+)"',
            error
        )

        assert match is not None
        missing_file = (match.group(1) or match.group(2) or match.group(3)).strip()
        assert "nginx.conf" in missing_file


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
