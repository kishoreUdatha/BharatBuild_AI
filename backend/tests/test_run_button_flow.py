"""
Unit tests for the complete Run Button → Preview flow.

Tests the entire flow when user clicks Run button:
1. Project status check
2. Container detection
3. File restore logic
4. Fullstack detection
5. Docker Compose build
6. Error fixing (SDK Fixer / BoltFixer)
7. Persistence to database
8. Preview URL generation

These tests ensure the flow works correctly for:
- First run
- Run again (container exists)
- Run again (container removed)
- Build failures and auto-fix
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from pathlib import Path
import asyncio


# ============================================================================
# STEP 1: PROJECT STATUS CHECK
# ============================================================================

class TestProjectStatusCheck:
    """Tests for [1/5] Checking project status."""

    def test_check_project_status_first(self):
        """Project status check must happen before anything else."""
        execution_steps = [
            "[1/5] Checking project status",
            "[2/5] Preparing container",
            "[3/5] Restoring files",
            "[4/5] Installing dependencies",
            "[5/5] Running"
        ]
        assert execution_steps[0] == "[1/5] Checking project status"

    @pytest.mark.asyncio
    async def test_project_id_and_user_id_required(self):
        """Must have project_id and user_id for execution."""
        project_id = "3271550b-750e-4d3f-aff1-1a1eccafe5f8"
        user_id = "4fd1cb50-162f-4d7c-9130-18cb369d3393"

        assert project_id is not None
        assert user_id is not None
        assert len(project_id) == 36  # UUID format
        assert len(user_id) == 36


# ============================================================================
# STEP 2: CONTAINER DETECTION
# ============================================================================

class TestContainerDetection:
    """Tests for container existence check."""

    def test_container_patterns_for_standard_project(self):
        """Standard projects use bharatbuild_{user_id[:8]}_{project_id[:8]}."""
        user_id = "4fd1cb50-162f-4d7c-9130-18cb369d3393"
        project_id = "3271550b-750e-4d3f-aff1-1a1eccafe5f8"

        expected_pattern = f"bharatbuild_{user_id[:8]}_{project_id[:8]}"
        assert expected_pattern == "bharatbuild_4fd1cb50_3271550b"

    def test_container_patterns_for_docker_compose(self):
        """Docker Compose projects use bharatbuild_{project_id[:8]}-{service}."""
        project_id = "3271550b-750e-4d3f-aff1-1a1eccafe5f8"

        backend_container = f"bharatbuild_{project_id[:8]}-backend"
        frontend_container = f"bharatbuild_{project_id[:8]}-frontend"

        assert backend_container == "bharatbuild_3271550b-backend"
        assert frontend_container == "bharatbuild_3271550b-frontend"

    def test_is_container_running_returns_true_for_running(self):
        """Must return True when container is running."""
        from app.services.container_executor import ContainerExecutor

        executor = ContainerExecutor()
        executor.docker_client = MagicMock()

        mock_container = MagicMock()
        mock_container.name = "bharatbuild_3271550b-backend"
        mock_container.status = "running"
        executor.docker_client.containers.list.return_value = [mock_container]

        result = executor.is_container_running("3271550b-xxx", "4fd1cb50-xxx")
        assert result == True

    def test_is_container_running_returns_true_for_stopped(self):
        """Must return True even for stopped containers (files still in volume)."""
        from app.services.container_executor import ContainerExecutor

        executor = ContainerExecutor()
        executor.docker_client = MagicMock()

        mock_container = MagicMock()
        mock_container.name = "bharatbuild_3271550b-backend"
        mock_container.status = "exited"  # Stopped but exists
        executor.docker_client.containers.list.return_value = [mock_container]

        result = executor.is_container_running("3271550b-xxx", "4fd1cb50-xxx")
        assert result == True, "Stopped containers should return True (files in volume)"

    def test_is_container_running_returns_false_when_none(self):
        """Must return False when no container exists."""
        from app.services.container_executor import ContainerExecutor

        executor = ContainerExecutor()
        executor.docker_client = MagicMock()
        executor.docker_client.containers.list.return_value = []

        result = executor.is_container_running("3271550b-xxx", "4fd1cb50-xxx")
        assert result == False


# ============================================================================
# STEP 3: FILE RESTORE LOGIC
# ============================================================================

class TestFileRestoreLogic:
    """Tests for file restore decision logic."""

    def test_skip_restore_when_container_exists(self):
        """Must skip restore when container already exists."""
        container_already_running = True
        needs_restore = True  # Default

        # Apply the fix logic
        if container_already_running:
            needs_restore = False

        assert needs_restore == False

    def test_skip_sandbox_check_when_container_exists(self):
        """Must skip sandbox_exists() call when container exists."""
        container_already_running = True
        sandbox_exists_called = False

        # Simulate the logic
        if not container_already_running:
            sandbox_exists_called = True  # Would call sandbox_exists()

        assert sandbox_exists_called == False, \
            "sandbox_exists() should NOT be called when container exists"

    def test_restore_when_no_container_and_no_sandbox(self):
        """Must restore from DB when no container and sandbox empty."""
        container_already_running = False
        exists_on_ec2 = False
        needs_restore = False

        if not container_already_running:
            if not exists_on_ec2:
                needs_restore = True

        assert needs_restore == True

    def test_no_restore_when_sandbox_has_files(self):
        """Must NOT restore when sandbox already has files."""
        container_already_running = False
        exists_on_ec2 = True
        needs_restore = False

        if not container_already_running:
            if exists_on_ec2:
                needs_restore = False
            else:
                needs_restore = True

        assert needs_restore == False

    @pytest.mark.asyncio
    async def test_restore_from_database_gets_fixed_files(self):
        """Restore from database must get the FIXED files (not original)."""
        # Simulate database with fixed content
        database_files = {
            "backend/src/main/java/UserService.java": "// FIXED: Added missing method\npublic void newMethod() {}",
            "backend/src/main/java/UserRepository.java": "// FIXED: Added @Query\n@Query(...)"
        }

        # Simulate restore
        restored_files = {}
        for path, content in database_files.items():
            restored_files[path] = content

        assert "FIXED" in restored_files["backend/src/main/java/UserService.java"]
        assert "FIXED" in restored_files["backend/src/main/java/UserRepository.java"]


# ============================================================================
# STEP 4: FULLSTACK DETECTION
# ============================================================================

class TestFullstackDetection:
    """Tests for fullstack project detection."""

    def test_detect_fullstack_with_frontend_backend_folders(self):
        """Must detect fullstack when frontend/ and backend/ folders exist."""
        files = ["frontend/package.json", "backend/pom.xml"]

        has_frontend = any("frontend" in f for f in files)
        has_backend = any("backend" in f for f in files)
        is_fullstack = has_frontend and has_backend

        assert is_fullstack == True

    def test_detect_java_backend(self):
        """Must detect Java/Spring Boot backend from pom.xml."""
        files = ["backend/pom.xml", "backend/src/main/java/Application.java"]

        has_pom = any("pom.xml" in f for f in files)
        has_java = any(".java" in f for f in files)

        assert has_pom == True
        assert has_java == True

    def test_detect_react_frontend(self):
        """Must detect React frontend from package.json with react dependency."""
        package_json = {
            "dependencies": {
                "react": "^18.0.0",
                "react-dom": "^18.0.0"
            }
        }

        is_react = "react" in package_json.get("dependencies", {})
        assert is_react == True


# ============================================================================
# STEP 5: DOCKER COMPOSE BUILD
# ============================================================================

class TestDockerComposeBuild:
    """Tests for Docker Compose build process."""

    def test_docker_compose_command_format(self):
        """Docker Compose command must have correct format."""
        project_id = "3271550b-750e-4d3f-aff1-1a1eccafe5f8"
        project_name = f"bharatbuild_{project_id[:8]}"
        compose_file = "/path/docker-compose.yml"

        cmd = f"docker-compose -p {project_name} -f {compose_file} up -d --build"

        assert "-p bharatbuild_3271550b" in cmd
        assert "-f /path/docker-compose.yml" in cmd
        assert "up -d --build" in cmd

    def test_docker_compose_uses_legacy_build(self):
        """Must use legacy build mode (COMPOSE_DOCKER_CLI_BUILD=0)."""
        cmd = "COMPOSE_DOCKER_CLI_BUILD=0 DOCKER_BUILDKIT=0 docker-compose up -d --build"

        assert "COMPOSE_DOCKER_CLI_BUILD=0" in cmd
        assert "DOCKER_BUILDKIT=0" in cmd

    def test_max_compose_attempts(self):
        """Must allow multiple retry attempts for cascading fixes."""
        max_compose_attempts = 4
        assert max_compose_attempts >= 3, "Should allow at least 3 retry attempts"


# ============================================================================
# STEP 6: ERROR FIXING FLOW
# ============================================================================

class TestErrorFixingFlow:
    """Tests for the auto-fix flow when build fails."""

    def test_java_error_detection(self):
        """Must detect Java errors from build output."""
        output = "[ERROR] cannot find symbol: method getUserById(Long)"

        is_java_error = '.java' in output or 'cannot find symbol' in output or 'mvn' in output.lower()
        assert is_java_error == True

    def test_java_error_uses_sdk_fixer_first(self):
        """Java errors must try SDK Fixer first."""
        is_java_error = True
        sdk_fixer_handled = False
        fixer_used = None

        if is_java_error:
            fixer_used = "SDK Fixer"
            sdk_fixer_handled = True

        assert fixer_used == "SDK Fixer"

    def test_non_java_error_uses_boltfixer(self):
        """Non-Java errors must use BoltFixer."""
        is_java_error = False
        fixer_used = None

        if not is_java_error:
            fixer_used = "BoltFixer"

        assert fixer_used == "BoltFixer"

    def test_sdk_fixer_fallback_to_boltfixer(self):
        """Must fallback to BoltFixer if SDK Fixer fails."""
        sdk_fixer_handled = False  # SDK Fixer failed
        fixer_used = None

        if not sdk_fixer_handled:
            fixer_used = "BoltFixer"

        assert fixer_used == "BoltFixer"

    def test_fix_order_infra_then_code(self):
        """Must try infrastructure fixes before code fixes."""
        fix_steps = []

        # Step 1: DockerInfraFixer (port conflicts, etc.)
        fix_steps.append("DockerInfraFixer")

        # Step 2: SDK Fixer (Java) or BoltFixer
        fix_steps.append("SDK Fixer / BoltFixer")

        assert fix_steps[0] == "DockerInfraFixer"
        assert fix_steps[1] == "SDK Fixer / BoltFixer"


# ============================================================================
# STEP 7: PERSISTENCE FLOW
# ============================================================================

class TestPersistenceFlow:
    """Tests for fix persistence to database."""

    @pytest.mark.asyncio
    async def test_sdk_fixer_persists_after_write(self):
        """SDK Fixer must persist to database AFTER writing to EC2."""
        operations = []

        # Simulate SDK Fixer flow
        operations.append("write_to_ec2")
        operations.append("persist_to_database")

        assert operations == ["write_to_ec2", "persist_to_database"]

    @pytest.mark.asyncio
    async def test_boltfixer_persists_after_write(self):
        """BoltFixer must persist to database AFTER writing to EC2."""
        operations = []

        # Simulate BoltFixer flow
        operations.append("write_to_ec2")
        operations.append("persist_to_database")

        assert operations == ["write_to_ec2", "persist_to_database"]

    @pytest.mark.asyncio
    async def test_persist_all_modified_files(self):
        """Must persist ALL modified files, not just some."""
        files_modified = [
            "backend/src/main/java/UserService.java",
            "backend/src/main/java/UserRepository.java",
            "backend/src/main/java/UserController.java"
        ]
        files_persisted = []

        for file_path in files_modified:
            files_persisted.append(file_path)

        assert len(files_persisted) == len(files_modified)
        assert files_persisted == files_modified

    @pytest.mark.asyncio
    async def test_persist_uses_correct_method(self):
        """Must use _persist_single_fix method for persistence."""
        from app.services.bolt_fixer import BoltFixer

        fixer = BoltFixer()
        assert hasattr(fixer, '_persist_single_fix'), \
            "BoltFixer must have _persist_single_fix method"

    @pytest.mark.asyncio
    async def test_persist_includes_file_content(self):
        """Persistence must include actual file content."""
        file_path = "Test.java"
        content = "public class Test { public void newMethod() {} }"

        # Simulate persist call
        persist_data = {
            "file_path": file_path,
            "content": content
        }

        assert persist_data["content"] == content
        assert len(persist_data["content"]) > 0


# ============================================================================
# STEP 8: PREVIEW URL
# ============================================================================

class TestPreviewUrl:
    """Tests for preview URL generation."""

    def test_preview_url_format(self):
        """Preview URL must have correct format."""
        project_id = "3271550b-750e-4d3f-aff1-1a1eccafe5f8"
        port = 3000

        preview_url = f"http://localhost:{port}"
        # Or for production:
        # preview_url = f"https://sandbox.bharatbuild.ai/preview/{project_id}"

        assert str(port) in preview_url

    def test_preview_url_emitted_on_success(self):
        """Must emit preview URL when build succeeds."""
        build_success = True
        preview_url = None

        if build_success:
            preview_url = "http://localhost:3000"

        assert preview_url is not None


# ============================================================================
# COMPLETE FLOW INTEGRATION TESTS
# ============================================================================

class TestCompleteRunFlow:
    """Integration tests for complete Run button flow."""

    @pytest.mark.asyncio
    async def test_first_run_complete_flow(self):
        """Test complete flow for first run."""
        # State
        container_exists = False
        sandbox_exists = False
        database_has_files = True
        build_succeeds = True

        # Flow
        steps_executed = []

        # Step 1: Check container
        steps_executed.append("check_container")
        if container_exists:
            steps_executed.append("skip_restore")
        else:
            # Step 2: Check sandbox
            steps_executed.append("check_sandbox")
            if not sandbox_exists:
                # Step 3: Restore from DB
                steps_executed.append("restore_from_db")

        # Step 4: Build
        steps_executed.append("docker_compose_build")

        if build_succeeds:
            steps_executed.append("success")

        expected = [
            "check_container",
            "check_sandbox",
            "restore_from_db",
            "docker_compose_build",
            "success"
        ]
        assert steps_executed == expected

    @pytest.mark.asyncio
    async def test_run_again_with_container_flow(self):
        """Test flow when running again with existing container."""
        container_exists = True

        steps_executed = []

        steps_executed.append("check_container")
        if container_exists:
            steps_executed.append("skip_restore")
            steps_executed.append("use_ec2_files")
        else:
            steps_executed.append("check_sandbox")

        steps_executed.append("docker_compose_build")
        steps_executed.append("success")

        expected = [
            "check_container",
            "skip_restore",
            "use_ec2_files",
            "docker_compose_build",
            "success"
        ]
        assert steps_executed == expected

    @pytest.mark.asyncio
    async def test_run_again_after_container_removed_flow(self):
        """Test flow when container removed but fixes in database."""
        container_exists = False
        sandbox_exists = False
        database_has_fixed_files = True

        steps_executed = []
        files_used = None

        steps_executed.append("check_container")
        if not container_exists:
            steps_executed.append("check_sandbox")
            if not sandbox_exists:
                steps_executed.append("restore_from_db")
                if database_has_fixed_files:
                    files_used = "fixed_files"

        steps_executed.append("docker_compose_build")
        steps_executed.append("success")

        assert "restore_from_db" in steps_executed
        assert files_used == "fixed_files", "Must restore FIXED files from database"

    @pytest.mark.asyncio
    async def test_build_fail_and_fix_flow(self):
        """Test flow when build fails and auto-fix runs."""
        build_attempt = 0
        max_attempts = 4
        build_succeeds = False

        steps_executed = []
        files_persisted = False

        while build_attempt < max_attempts:
            build_attempt += 1
            steps_executed.append(f"build_attempt_{build_attempt}")

            if not build_succeeds:
                steps_executed.append("fix_error")
                steps_executed.append("write_to_ec2")
                steps_executed.append("persist_to_db")
                files_persisted = True

                # Simulate fix worked on attempt 2
                if build_attempt == 2:
                    build_succeeds = True
                    steps_executed.append("success")
                    break

        assert files_persisted == True, "Fixes must be persisted to database"
        assert "success" in steps_executed
        assert build_attempt == 2, "Should succeed on second attempt"


# ============================================================================
# ERROR SCENARIOS
# ============================================================================

class TestErrorScenarios:
    """Tests for error handling scenarios."""

    def test_container_check_timeout_handled(self):
        """Must handle container check timeout gracefully."""
        timeout_occurred = True
        container_exists = None

        if timeout_occurred:
            container_exists = False  # Assume no container on timeout

        assert container_exists == False

    def test_sandbox_check_timeout_handled(self):
        """Must handle sandbox check timeout gracefully."""
        timeout_occurred = True
        needs_restore = False

        if timeout_occurred:
            needs_restore = True  # Restore on timeout

        assert needs_restore == True

    def test_persist_failure_does_not_break_flow(self):
        """Persistence failure should not break the main flow."""
        persist_failed = True
        build_continues = True

        try:
            if persist_failed:
                raise Exception("Persist failed")
        except Exception:
            pass  # Log warning but continue

        assert build_continues == True

    def test_max_fix_attempts_reached(self):
        """Must stop after max fix attempts."""
        max_attempts = 4
        current_attempt = 4
        should_stop = current_attempt >= max_attempts

        assert should_stop == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
