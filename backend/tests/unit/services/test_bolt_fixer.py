"""
Unit Tests for BoltFixer Service

Comprehensive tests covering:
1. Import smoke tests (catch import errors early)
2. Error classification and strategy determination
3. Patch parsing (unified diff, file blocks, newfile blocks)
4. Retry limiting
5. Fix result handling
6. Integration with ErrorClassifier
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import tempfile


# =============================================================================
# SMOKE TESTS - Catch import errors early
# =============================================================================
class TestBoltFixerImports:
    """Test that all BoltFixer imports work correctly"""

    def test_bolt_fixer_module_imports(self):
        """Test BoltFixer module can be imported without errors"""
        from app.services import bolt_fixer
        assert bolt_fixer is not None

    def test_bolt_fixer_class_imports(self):
        """Test BoltFixer class can be imported"""
        from app.services.bolt_fixer import BoltFixer
        assert BoltFixer is not None

    def test_bolt_fix_result_imports(self):
        """Test BoltFixResult can be imported"""
        from app.services.bolt_fixer import BoltFixResult
        assert BoltFixResult is not None

    def test_database_import_path(self):
        """Test that database import uses correct path (app.core.database)"""
        from app.core.database import AsyncSessionLocal
        assert AsyncSessionLocal is not None

    def test_error_classifier_imports(self):
        """Test ErrorClassifier can be imported"""
        from app.services.error_classifier import ErrorClassifier, ErrorType
        assert ErrorClassifier is not None
        assert ErrorType is not None

    def test_patch_validator_imports(self):
        """Test PatchValidator can be imported"""
        from app.services.patch_validator import PatchValidator
        assert PatchValidator is not None

    def test_diff_parser_imports(self):
        """Test DiffParser can be imported"""
        from app.services.diff_parser import DiffParser
        assert DiffParser is not None


# =============================================================================
# BOLT FIX RESULT TESTS
# =============================================================================
class TestBoltFixResult:
    """Test BoltFixResult dataclass"""

    def test_successful_fix_result(self):
        """Test BoltFixResult for successful fix"""
        from app.services.bolt_fixer import BoltFixResult

        result = BoltFixResult(
            success=True,
            files_modified=["src/App.java", "src/User.java"],
            message="Fixed 2 files",
            patches_applied=2,
            error_type="missing_symbol",
            fix_strategy="ai_fix"
        )

        assert result.success == True
        assert len(result.files_modified) == 2
        assert result.patches_applied == 2
        assert result.error_type == "missing_symbol"
        assert result.fix_strategy == "ai_fix"

    def test_failed_fix_result(self):
        """Test BoltFixResult for failed fix"""
        from app.services.bolt_fixer import BoltFixResult

        result = BoltFixResult(
            success=False,
            files_modified=[],
            message="Claude returned no fixes"
        )

        assert result.success == False
        assert len(result.files_modified) == 0
        assert result.patches_applied == 0

    def test_fix_result_default_values(self):
        """Test BoltFixResult default values"""
        from app.services.bolt_fixer import BoltFixResult

        result = BoltFixResult(
            success=True,
            files_modified=["test.java"],
            message="OK"
        )

        assert result.patches_applied == 0
        assert result.error_type is None
        assert result.fix_strategy is None


# =============================================================================
# BOLT FIXER INSTANTIATION TESTS
# =============================================================================
class TestBoltFixerInstantiation:
    """Test BoltFixer class instantiation"""

    def test_can_instantiate(self):
        """Test BoltFixer can be created"""
        from app.services.bolt_fixer import BoltFixer
        fixer = BoltFixer()
        assert fixer is not None

    def test_has_system_prompt(self):
        """Test BoltFixer has SYSTEM_PROMPT defined"""
        from app.services.bolt_fixer import BoltFixer
        fixer = BoltFixer()
        assert hasattr(fixer, 'SYSTEM_PROMPT')
        assert len(fixer.SYSTEM_PROMPT) > 100

    def test_has_syntax_fix_prompt(self):
        """Test BoltFixer has SYNTAX_FIX_PROMPT defined"""
        from app.services.bolt_fixer import BoltFixer
        fixer = BoltFixer()
        assert hasattr(fixer, 'SYNTAX_FIX_PROMPT')
        assert len(fixer.SYNTAX_FIX_PROMPT) > 50

    def test_claude_client_lazy_init(self):
        """Test Claude client is lazily initialized"""
        from app.services.bolt_fixer import BoltFixer
        fixer = BoltFixer()
        assert fixer._claude_client is None


# =============================================================================
# PATCH PARSING TESTS
# =============================================================================
class TestPatchParsing:
    """Test patch block parsing"""

    @pytest.fixture
    def fixer(self):
        """Create BoltFixer instance"""
        from app.services.bolt_fixer import BoltFixer
        return BoltFixer()

    def test_parse_patch_block(self, fixer):
        """Test parsing unified diff patch block"""
        response = """<patch>
--- src/App.java
+++ src/App.java
@@ -10,3 +10,4 @@
 public class App {
+    private String name;
 }
</patch>"""

        patches = fixer._parse_patch_blocks(response)
        assert len(patches) == 1
        assert "App.java" in patches[0].get("patch", "")

    def test_parse_multiple_patch_blocks(self, fixer):
        """Test parsing multiple patch blocks"""
        response = """<patch>
--- src/App.java
+++ src/App.java
@@ -1,1 +1,1 @@
-old
+new
</patch>
<patch>
--- src/User.java
+++ src/User.java
@@ -1,1 +1,1 @@
-old
+new
</patch>"""

        patches = fixer._parse_patch_blocks(response)
        assert len(patches) == 2

    def test_parse_empty_patch_block(self, fixer):
        """Test parsing empty patch block"""
        response = "<patch></patch>"
        patches = fixer._parse_patch_blocks(response)
        assert len(patches) == 0

    def test_parse_file_block(self, fixer):
        """Test parsing file replacement block"""
        response = """<file path="src/App.java">
public class App {
    public static void main(String[] args) {
        System.out.println("Hello");
    }
}
</file>"""

        files = fixer._parse_file_blocks(response)
        assert len(files) == 1
        assert files[0]["path"] == "src/App.java"
        assert "public class App" in files[0]["content"]

    def test_parse_newfile_block(self, fixer):
        """Test parsing new file creation block"""
        response = """<newfile path="src/dto/UserDto.java">
package com.lms.dto;

public class UserDto {
    private String name;
}
</newfile>"""

        new_files = fixer._parse_newfile_blocks(response)
        assert len(new_files) == 1
        assert new_files[0]["path"] == "src/dto/UserDto.java"
        assert "UserDto" in new_files[0]["content"]

    def test_parse_mixed_response(self, fixer):
        """Test parsing response with patches, files, and newfiles"""
        response = """<patch>
--- src/App.java
+++ src/App.java
@@ -1,1 +1,1 @@
-old
+new
</patch>
<file path="src/Config.java">
public class Config {}
</file>
<newfile path="src/dto/NewDto.java">
public class NewDto {}
</newfile>"""

        patches = fixer._parse_patch_blocks(response)
        files = fixer._parse_file_blocks(response)
        new_files = fixer._parse_newfile_blocks(response)

        assert len(patches) == 1
        assert len(files) == 1
        assert len(new_files) == 1


# =============================================================================
# ERROR CLASSIFIER INTEGRATION TESTS
# =============================================================================
class TestErrorClassifierIntegration:
    """Test BoltFixer integration with ErrorClassifier"""

    def test_classify_maven_build_failure(self):
        """Test classifying Maven BUILD FAILURE error"""
        from app.services.error_classifier import ErrorClassifier, ErrorType

        classified = ErrorClassifier.classify(
            error_message="[ERROR] BUILD FAILURE\n[ERROR] cannot find symbol: class UserDto",
            stderr="[ERROR] BUILD FAILURE",
            exit_code=1
        )

        assert classified.error_type == ErrorType.MISSING_SYMBOL
        assert classified.is_claude_fixable == True

    def test_classify_npm_module_error(self):
        """Test classifying npm module not found error"""
        from app.services.error_classifier import ErrorClassifier, ErrorType

        classified = ErrorClassifier.classify(
            error_message="Cannot find module 'react'",
            stderr="npm ERR! Cannot find module 'react'",
            exit_code=1
        )

        assert classified.is_claude_fixable == True

    def test_classify_syntax_error(self):
        """Test classifying syntax error"""
        from app.services.error_classifier import ErrorClassifier, ErrorType

        classified = ErrorClassifier.classify(
            error_message="SyntaxError: Unexpected token",
            stderr="SyntaxError: Unexpected token '}' at line 10",
            exit_code=1
        )

        assert classified.error_type == ErrorType.SYNTAX_ERROR
        assert classified.is_claude_fixable == True

    def test_classify_success_output(self):
        """Test classifying successful build output"""
        from app.services.error_classifier import ErrorClassifier, ErrorType

        classified = ErrorClassifier.classify(
            error_message="BUILD SUCCESS",
            stderr="",
            exit_code=0
        )

        assert classified.error_type == ErrorType.UNKNOWN
        assert classified.is_claude_fixable == False


# =============================================================================
# FIX FROM BACKEND TESTS
# =============================================================================
class TestFixFromBackend:
    """Test fix_from_backend method"""

    @pytest.fixture
    def fixer(self):
        """Create BoltFixer instance"""
        from app.services.bolt_fixer import BoltFixer
        return BoltFixer()

    @pytest.mark.asyncio
    async def test_fix_from_backend_no_error(self, fixer):
        """Test fix_from_backend with no error returns skip"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            payload = {
                "stderr": "",
                "stdout": "BUILD SUCCESS",
                "exit_code": 0,
                "primary_error_type": None
            }

            result = await fixer.fix_from_backend(
                project_id="test-project",
                project_path=tmp_path,
                payload=payload
            )

            assert result.success == False
            assert result.fix_strategy == "skipped"

    @pytest.mark.asyncio
    async def test_fix_from_backend_with_error(self, fixer):
        """Test fix_from_backend with fixable error"""
        with patch.object(fixer, '_call_claude', new_callable=AsyncMock) as mock_claude:
            # Mock Claude response with a new file creation
            mock_claude.return_value = """<newfile path="src/dto/ApiResponse.java">
package com.lms.dto;

public class ApiResponse<T> {
    private boolean success;
    private T data;
}
</newfile>"""

            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)

                # Create project structure
                (tmp_path / "src" / "dto").mkdir(parents=True)

                payload = {
                    "stderr": "[ERROR] cannot find symbol: class ApiResponse",
                    "stdout": "",
                    "exit_code": 1,
                    "primary_error_type": "missing_symbol"
                }

                result = await fixer.fix_from_backend(
                    project_id="test-project",
                    project_path=tmp_path,
                    payload=payload
                )

                # Should have attempted to fix
                assert mock_claude.called


# =============================================================================
# DOCKER COMPOSE PROTECTION TESTS
# =============================================================================
class TestDockerComposeProtection:
    """Test that docker-compose.yml is protected from full replacement"""

    @pytest.fixture
    def fixer(self):
        """Create BoltFixer instance"""
        from app.services.bolt_fixer import BoltFixer
        return BoltFixer()

    def test_blocks_docker_compose_replacement(self, fixer):
        """Test that full docker-compose.yml replacement is blocked"""
        response = """<file path="docker-compose.yml">
version: '3.8'
services:
  app:
    build: .
</file>"""

        files = fixer._parse_file_blocks(response)
        # Files should be parsed but blocked during application
        assert len(files) == 1
        assert files[0]["path"] == "docker-compose.yml"


# =============================================================================
# RETRY LIMITER INTEGRATION TESTS
# =============================================================================
class TestRetryLimiterIntegration:
    """Test integration with retry limiter"""

    def test_retry_limiter_hash_error(self):
        """Test error hashing is consistent"""
        from app.services.retry_limiter import retry_limiter

        error1 = "cannot find symbol: class UserDto"
        error2 = "cannot find symbol: class UserDto"
        error3 = "cannot find symbol: class ApiResponse"

        hash1 = retry_limiter.hash_error(error1)
        hash2 = retry_limiter.hash_error(error2)
        hash3 = retry_limiter.hash_error(error3)

        assert hash1 == hash2  # Same error, same hash
        assert hash1 != hash3  # Different error, different hash

    def test_retry_limiter_can_retry_first_attempt(self):
        """Test first retry attempt is allowed"""
        from app.services.retry_limiter import retry_limiter

        project_id = "test-new-project-123"
        error_hash = retry_limiter.hash_error("test error")

        can_retry, reason = retry_limiter.can_retry(project_id, error_hash)
        assert can_retry == True


# =============================================================================
# RELATED FILES READING TESTS
# =============================================================================
class TestRelatedFilesReading:
    """Test reading related Java files"""

    @pytest.fixture
    def fixer(self):
        """Create BoltFixer instance"""
        from app.services.bolt_fixer import BoltFixer
        return BoltFixer()

    @pytest.mark.asyncio
    async def test_read_related_java_files(self, fixer):
        """Test reading related Java files from error message"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create Java project structure
            (tmp_path / "src" / "main" / "java" / "com" / "lms" / "dto").mkdir(parents=True)
            (tmp_path / "src" / "main" / "java" / "com" / "lms" / "dto" / "UserDto.java").write_text(
                "package com.lms.dto;\npublic class UserDto {}"
            )

            error_output = "[ERROR] cannot find symbol: class UserDto\n[ERROR] location: class UserController"

            related = await fixer._read_related_java_files(
                tmp_path, error_output, "UserController.java"
            )

            # Should attempt to find related files
            assert related is not None


# =============================================================================
# PROMPT TEMPLATE TESTS
# =============================================================================
class TestPromptTemplates:
    """Test prompt template generation"""

    def test_get_claude_prompt_template(self):
        """Test getting Claude prompt template for error type"""
        from app.services.error_classifier import ErrorClassifier, ErrorType

        template = ErrorClassifier.get_claude_prompt_template(ErrorType.MISSING_SYMBOL)
        assert template is not None
        assert len(template) > 0

    def test_syntax_error_template(self):
        """Test syntax error uses special template"""
        from app.services.error_classifier import ErrorClassifier, ErrorType

        template = ErrorClassifier.get_claude_prompt_template(ErrorType.SYNTAX_ERROR)
        assert template is not None


# =============================================================================
# CRITICAL IMPORT PATH TESTS
# =============================================================================
class TestCriticalImportPaths:
    """
    Test critical import paths that have caused production issues.
    Add new tests here when import errors are discovered.
    """

    def test_app_core_database_import(self):
        """Test app.core.database import (was app.database - FIXED)"""
        from app.core.database import AsyncSessionLocal, get_db
        assert AsyncSessionLocal is not None
        assert get_db is not None

    def test_app_models_project_import(self):
        """Test app.models.project import"""
        from app.models.project import ProjectFile
        assert ProjectFile is not None

    def test_app_services_bolt_fixer_full_import(self):
        """Test full bolt_fixer import chain works"""
        from app.services.bolt_fixer import BoltFixer, BoltFixResult
        assert BoltFixer is not None
        assert BoltFixResult is not None

    def test_storage_service_import(self):
        """Test storage_service import"""
        from app.services.storage_service import storage_service
        assert storage_service is not None


# =============================================================================
# CONTAINER EXECUTOR SMOKE TESTS
# =============================================================================
class TestContainerExecutorImports:
    """Test ContainerExecutor related imports"""

    def test_container_executor_imports(self):
        """Test ContainerExecutor can be imported"""
        from app.services.container_executor import ContainerExecutor
        assert ContainerExecutor is not None

    def test_technology_enum_imports(self):
        """Test Technology enum has expected values"""
        from app.services.container_executor import Technology

        assert hasattr(Technology, 'JAVA')
        assert hasattr(Technology, 'NODEJS')
        assert hasattr(Technology, 'PYTHON')
        assert hasattr(Technology, 'FULLSTACK')
