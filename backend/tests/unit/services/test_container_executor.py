"""
Unit Tests for Container Executor Service
Tests the dynamic container spawning for project execution
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
import os
from pathlib import Path


class TestTechnologyDetection:
    """Tests for technology detection from project files"""

    @pytest.fixture
    def executor(self):
        """Create ContainerExecutor instance"""
        from app.services.container_executor import ContainerExecutor
        return ContainerExecutor()

    def test_detect_nodejs_from_package_json(self, executor, tmp_path):
        """Test Node.js detection from package.json"""
        from app.services.container_executor import Technology

        (tmp_path / "package.json").write_text('{"name": "test"}')

        result = executor.detect_technology(str(tmp_path))
        assert result == Technology.NODEJS

    def test_detect_java_from_pom_xml(self, executor, tmp_path):
        """Test Java detection from pom.xml"""
        from app.services.container_executor import Technology

        (tmp_path / "pom.xml").write_text('<project></project>')

        result = executor.detect_technology(str(tmp_path))
        assert result == Technology.JAVA

    def test_detect_java_from_build_gradle(self, executor, tmp_path):
        """Test Java detection from build.gradle"""
        from app.services.container_executor import Technology

        (tmp_path / "build.gradle").write_text('plugins {}')

        result = executor.detect_technology(str(tmp_path))
        assert result == Technology.JAVA

    def test_detect_java_from_build_gradle_kts(self, executor, tmp_path):
        """Test Java detection from build.gradle.kts"""
        from app.services.container_executor import Technology

        (tmp_path / "build.gradle.kts").write_text('plugins {}')

        result = executor.detect_technology(str(tmp_path))
        assert result == Technology.JAVA

    def test_detect_python_from_requirements(self, executor, tmp_path):
        """Test Python detection from requirements.txt"""
        from app.services.container_executor import Technology

        (tmp_path / "requirements.txt").write_text('fastapi==0.100.0')

        result = executor.detect_technology(str(tmp_path))
        assert result == Technology.PYTHON

    def test_detect_python_from_pyproject(self, executor, tmp_path):
        """Test Python detection from pyproject.toml"""
        from app.services.container_executor import Technology

        (tmp_path / "pyproject.toml").write_text('[build-system]')

        result = executor.detect_technology(str(tmp_path))
        assert result == Technology.PYTHON

    def test_detect_go_from_go_mod(self, executor, tmp_path):
        """Test Go detection from go.mod"""
        from app.services.container_executor import Technology

        (tmp_path / "go.mod").write_text('module example.com/test')

        result = executor.detect_technology(str(tmp_path))
        assert result == Technology.GO

    def test_detect_nodejs_from_tsx_extension(self, executor, tmp_path):
        """Test Node.js detection from .tsx file extension"""
        from app.services.container_executor import Technology

        (tmp_path / "App.tsx").write_text('export default function App() {}')

        result = executor.detect_technology(str(tmp_path))
        assert result == Technology.NODEJS

    def test_detect_unknown_empty_dir(self, executor, tmp_path):
        """Test unknown detection for empty directory"""
        from app.services.container_executor import Technology

        result = executor.detect_technology(str(tmp_path))
        assert result == Technology.UNKNOWN

    def test_detect_unknown_nonexistent_path(self, executor):
        """Test unknown detection for non-existent path"""
        from app.services.container_executor import Technology

        result = executor.detect_technology("/nonexistent/path")
        assert result == Technology.UNKNOWN

    def test_nodejs_takes_priority_over_extension(self, executor, tmp_path):
        """Test package.json takes priority over file extensions"""
        from app.services.container_executor import Technology

        (tmp_path / "package.json").write_text('{}')
        (tmp_path / "main.py").write_text('print("test")')

        result = executor.detect_technology(str(tmp_path))
        assert result == Technology.NODEJS


class TestContainerConfig:
    """Tests for container configuration"""

    def test_technology_configs_exist(self):
        """Test that all technology configs are defined"""
        from app.services.container_executor import TECHNOLOGY_CONFIGS, Technology

        assert Technology.NODEJS in TECHNOLOGY_CONFIGS
        assert Technology.JAVA in TECHNOLOGY_CONFIGS
        assert Technology.PYTHON in TECHNOLOGY_CONFIGS
        assert Technology.GO in TECHNOLOGY_CONFIGS

    def test_nodejs_config_values(self):
        """Test Node.js configuration values"""
        from app.services.container_executor import TECHNOLOGY_CONFIGS, Technology

        config = TECHNOLOGY_CONFIGS[Technology.NODEJS]

        assert config.image == "node:20-alpine"
        assert config.build_command == "npm install"
        assert config.run_command == "npm run dev"
        assert config.port == 3000
        assert config.memory_limit == "512m"

    def test_java_config_values(self):
        """Test Java configuration values"""
        from app.services.container_executor import TECHNOLOGY_CONFIGS, Technology

        config = TECHNOLOGY_CONFIGS[Technology.JAVA]

        assert "maven" in config.image.lower() or "temurin" in config.image.lower()
        assert "mvn" in config.build_command
        assert config.port == 8080
        assert config.memory_limit == "1g"

    def test_python_config_values(self):
        """Test Python configuration values"""
        from app.services.container_executor import TECHNOLOGY_CONFIGS, Technology

        config = TECHNOLOGY_CONFIGS[Technology.PYTHON]

        assert "python" in config.image.lower()
        assert "pip install" in config.build_command
        assert config.port == 8000

    def test_go_config_values(self):
        """Test Go configuration values"""
        from app.services.container_executor import TECHNOLOGY_CONFIGS, Technology

        config = TECHNOLOGY_CONFIGS[Technology.GO]

        assert "golang" in config.image.lower()
        assert "go mod download" in config.build_command
        assert config.port == 8080


class TestContainerExecutorInit:
    """Tests for ContainerExecutor initialization"""

    def test_executor_initial_state(self):
        """Test executor initial state"""
        from app.services.container_executor import ContainerExecutor

        executor = ContainerExecutor()

        assert executor.docker_client is None
        assert executor.active_containers == {}
        assert executor._cleanup_task is None

    @pytest.mark.asyncio
    @patch('app.services.container_executor.docker')
    async def test_initialize_success(self, mock_docker):
        """Test successful Docker client initialization"""
        from app.services.container_executor import ContainerExecutor

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_docker.DockerClient.return_value = mock_client

        executor = ContainerExecutor()
        result = await executor.initialize()

        # Should try to initialize
        assert mock_docker.DockerClient.called or mock_docker.from_env.called

    @pytest.mark.asyncio
    @patch('app.services.container_executor.docker')
    async def test_initialize_failure(self, mock_docker):
        """Test Docker client initialization failure"""
        from app.services.container_executor import ContainerExecutor

        mock_docker.DockerClient.side_effect = Exception("Connection failed")
        mock_docker.from_env.side_effect = Exception("Connection failed")

        executor = ContainerExecutor()
        result = await executor.initialize()

        assert result == False


class TestContainerLifecycle:
    """Tests for container lifecycle management"""

    @pytest.fixture
    def mock_executor(self):
        """Create executor with mocked Docker client"""
        from app.services.container_executor import ContainerExecutor

        executor = ContainerExecutor()
        executor.docker_client = MagicMock()
        return executor

    @pytest.mark.asyncio
    async def test_create_container_no_docker_client(self, mock_executor):
        """Test create_container fails without Docker client"""
        mock_executor.docker_client = None

        success, message, port = await mock_executor.create_container(
            project_id="test-project",
            user_id="test-user",
            project_path="/tmp/test"
        )

        assert success == False
        assert "not initialized" in message.lower()
        assert port is None

    @pytest.mark.asyncio
    async def test_create_container_unknown_technology(self, mock_executor, tmp_path):
        """Test create_container fails for unknown technology"""
        success, message, port = await mock_executor.create_container(
            project_id="test-project",
            user_id="test-user",
            project_path=str(tmp_path)
        )

        assert success == False
        assert "could not detect" in message.lower()
        assert port is None

    @pytest.mark.asyncio
    async def test_stop_container_not_found(self, mock_executor):
        """Test stop_container returns False for non-existent container"""
        success, message = await mock_executor.stop_container("nonexistent-project")

        assert success == False
        assert "not found" in message.lower()

    @pytest.mark.asyncio
    async def test_stop_container_success(self, mock_executor):
        """Test successful container stop"""
        mock_container = MagicMock()
        mock_executor.docker_client.containers.get.return_value = mock_container

        mock_executor.active_containers["test-project"] = {
            "container_id": "abc123",
            "container_name": "test_container",
            "user_id": "user1",
            "technology": "nodejs",
            "port": 10000
        }

        success, message = await mock_executor.stop_container("test-project")

        assert success == True
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()
        assert "test-project" not in mock_executor.active_containers

    @pytest.mark.asyncio
    async def test_get_container_logs_not_found(self, mock_executor):
        """Test get_container_logs returns None for non-existent container"""
        result = await mock_executor.get_container_logs("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_container_status_not_found(self, mock_executor):
        """Test get_container_status returns None for non-existent container"""
        result = await mock_executor.get_container_status("nonexistent")
        assert result is None


class TestPortAllocation:
    """Tests for port allocation"""

    def test_find_available_port_in_range(self):
        """Test port allocation returns port in valid range"""
        from app.services.container_executor import ContainerExecutor

        executor = ContainerExecutor()
        port = executor._find_available_port(start=10000, end=10100)

        assert 10000 <= port < 10100

    def test_find_available_port_avoids_used(self):
        """Test port allocation avoids already used ports"""
        from app.services.container_executor import ContainerExecutor
        from datetime import datetime, timedelta

        executor = ContainerExecutor()

        # Mark port 10000 as used
        executor.active_containers["project1"] = {
            "port": 10000,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=1)
        }

        port = executor._find_available_port(start=10000, end=10100)

        assert port != 10000
        assert 10000 < port < 10100


class TestExecuteCommand:
    """Tests for command execution in containers"""

    @pytest.fixture
    def executor_with_container(self):
        """Create executor with a mock container"""
        from app.services.container_executor import ContainerExecutor
        from datetime import datetime, timedelta

        executor = ContainerExecutor()
        executor.docker_client = MagicMock()
        executor.active_containers["test-project"] = {
            "container_id": "abc123",
            "container_name": "test_container",
            "user_id": "user1",
            "technology": "nodejs",
            "port": 10000,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=1)
        }
        return executor

    @pytest.mark.asyncio
    async def test_execute_command_container_not_found(self):
        """Test execute_command fails for non-existent container"""
        from app.services.container_executor import ContainerExecutor

        executor = ContainerExecutor()
        executor.docker_client = MagicMock()

        success, output = await executor.execute_command("nonexistent", "ls")

        assert success == False
        assert "not found" in output.lower()

    @pytest.mark.asyncio
    async def test_execute_command_success(self, executor_with_container):
        """Test successful command execution"""
        mock_container = MagicMock()
        mock_container.exec_run.return_value = (0, (b"file1.js\nfile2.js", b""))
        executor_with_container.docker_client.containers.get.return_value = mock_container

        success, output = await executor_with_container.execute_command("test-project", "ls")

        assert success == True
        assert "file1.js" in output

    @pytest.mark.asyncio
    async def test_execute_command_failure(self, executor_with_container):
        """Test failed command execution"""
        mock_container = MagicMock()
        mock_container.exec_run.return_value = (1, (b"", b"Command not found"))
        executor_with_container.docker_client.containers.get.return_value = mock_container

        success, output = await executor_with_container.execute_command("test-project", "invalid-cmd")

        assert success == False
        assert "not found" in output.lower() or output != ""


class TestCleanup:
    """Tests for container cleanup"""

    @pytest.mark.asyncio
    async def test_cleanup_all_containers(self):
        """Test cleanup_all stops all containers"""
        from app.services.container_executor import ContainerExecutor
        from datetime import datetime, timedelta

        executor = ContainerExecutor()
        executor.docker_client = MagicMock()

        mock_container = MagicMock()
        executor.docker_client.containers.get.return_value = mock_container

        # Add multiple containers
        for i in range(3):
            executor.active_containers[f"project-{i}"] = {
                "container_id": f"container-{i}",
                "container_name": f"test_container_{i}",
                "user_id": "user1",
                "technology": "nodejs",
                "port": 10000 + i,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(hours=1)
            }

        await executor.cleanup_all()

        assert len(executor.active_containers) == 0


class TestGlobalInstance:
    """Tests for global container_executor instance"""

    def test_global_instance_exists(self):
        """Test that global container_executor instance exists"""
        from app.services.container_executor import container_executor

        assert container_executor is not None

    def test_global_instance_type(self):
        """Test that global instance is ContainerExecutor"""
        from app.services.container_executor import container_executor, ContainerExecutor

        assert isinstance(container_executor, ContainerExecutor)
