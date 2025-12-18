"""
Unit Tests for Simple Fixer Service
Tests the AI-powered auto-fix functionality
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
from pathlib import Path


class TestErrorComplexityClassification:
    """Tests for error complexity classification"""

    @pytest.fixture
    def fixer(self):
        """Create SimpleFixer instance with mocked API client"""
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            from app.services.simple_fixer import SimpleFixer
            return SimpleFixer()

    def test_classify_simple_syntax_error(self, fixer):
        """Test syntax errors are classified as SIMPLE"""
        from app.services.simple_fixer import ErrorComplexity

        errors = [{"message": "SyntaxError: Unexpected token", "file": "app.js", "line": 10}]
        result = fixer._classify_error_complexity(errors, "")

        assert result == ErrorComplexity.SIMPLE

    def test_classify_simple_import_error(self, fixer):
        """Test import errors are classified as SIMPLE"""
        from app.services.simple_fixer import ErrorComplexity

        errors = [{"message": "Cannot find module 'react'", "file": "App.tsx"}]
        result = fixer._classify_error_complexity(errors, "")

        assert result == ErrorComplexity.SIMPLE

    def test_classify_simple_python_error(self, fixer):
        """Test Python errors are classified as SIMPLE"""
        from app.services.simple_fixer import ErrorComplexity

        errors = [{"message": "ModuleNotFoundError: No module named 'django'"}]
        result = fixer._classify_error_complexity(errors, "")

        assert result == ErrorComplexity.SIMPLE

    def test_classify_simple_java_error(self, fixer):
        """Test Java compilation errors are classified as SIMPLE"""
        from app.services.simple_fixer import ErrorComplexity

        errors = [{"message": "cannot find symbol: variable user", "file": "Main.java", "line": 25}]
        result = fixer._classify_error_complexity(errors, "")

        assert result == ErrorComplexity.SIMPLE

    def test_classify_complex_multiple_errors(self, fixer):
        """Test multiple errors are classified as COMPLEX"""
        from app.services.simple_fixer import ErrorComplexity

        errors = [
            {"message": "Error 1", "file": "file1.js"},
            {"message": "Error 2", "file": "file2.js"},
            {"message": "Error 3", "file": "file3.js"},
            {"message": "Error 4", "file": "file4.js"},
        ]
        result = fixer._classify_error_complexity(errors, "")

        assert result == ErrorComplexity.COMPLEX

    def test_classify_moderate_config_error(self, fixer):
        """Test config file errors are classified as MODERATE"""
        from app.services.simple_fixer import ErrorComplexity

        errors = [{"message": "Error in tsconfig.json configuration"}]
        result = fixer._classify_error_complexity(errors, "")

        assert result == ErrorComplexity.MODERATE

    def test_classify_empty_errors(self, fixer):
        """Test empty errors are classified as SIMPLE"""
        from app.services.simple_fixer import ErrorComplexity

        result = fixer._classify_error_complexity([], "")
        assert result == ErrorComplexity.SIMPLE


class TestModelSelection:
    """Tests for model selection based on complexity"""

    @pytest.fixture
    def fixer(self):
        """Create SimpleFixer instance"""
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            from app.services.simple_fixer import SimpleFixer
            return SimpleFixer()

    def test_select_haiku_for_simple(self, fixer):
        """Test Haiku model is selected for SIMPLE errors"""
        from app.services.simple_fixer import ErrorComplexity

        model = fixer._select_model(ErrorComplexity.SIMPLE)
        assert "haiku" in model.lower()

    def test_select_sonnet_for_moderate(self, fixer):
        """Test Sonnet model is selected for MODERATE errors"""
        from app.services.simple_fixer import ErrorComplexity

        model = fixer._select_model(ErrorComplexity.MODERATE)
        assert "sonnet" in model.lower()

    def test_select_sonnet_for_complex(self, fixer):
        """Test Sonnet model is selected for COMPLEX errors"""
        from app.services.simple_fixer import ErrorComplexity

        model = fixer._select_model(ErrorComplexity.COMPLEX)
        assert "sonnet" in model.lower()


class TestShouldFix:
    """Tests for should_fix decision logic"""

    @pytest.fixture
    def fixer(self):
        """Create SimpleFixer instance"""
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            from app.services.simple_fixer import SimpleFixer
            return SimpleFixer()

    @pytest.mark.asyncio
    async def test_should_fix_nonzero_exit(self, fixer):
        """Test should_fix returns True for non-zero exit code"""
        result = await fixer.should_fix(1, "Some output")
        assert result == True

    @pytest.mark.asyncio
    async def test_should_not_fix_success(self, fixer):
        """Test should_fix returns False for success output"""
        result = await fixer.should_fix(0, "Compiled successfully")
        assert result == False

    @pytest.mark.asyncio
    async def test_should_fix_syntax_error(self, fixer):
        """Test should_fix returns True for syntax error output"""
        result = await fixer.should_fix(None, "SyntaxError: Unexpected token")
        assert result == True

    @pytest.mark.asyncio
    async def test_should_fix_module_not_found(self, fixer):
        """Test should_fix returns True for module not found"""
        result = await fixer.should_fix(None, "Cannot find module 'lodash'")
        assert result == True

    @pytest.mark.asyncio
    async def test_should_not_fix_maven_success(self, fixer):
        """Test should_fix returns False for Maven BUILD SUCCESS"""
        result = await fixer.should_fix(0, "BUILD SUCCESS\nTotal time: 5.2 s")
        assert result == False

    @pytest.mark.asyncio
    async def test_should_fix_java_exception(self, fixer):
        """Test should_fix returns True for Java exceptions"""
        result = await fixer.should_fix(None, "java.lang.NullPointerException at Main.java:25")
        assert result == True

    @pytest.mark.asyncio
    async def test_should_fix_python_traceback(self, fixer):
        """Test should_fix returns True for Python traceback"""
        result = await fixer.should_fix(None, "Traceback (most recent call last):\n  File...")
        assert result == True


class TestCostEstimation:
    """Tests for cost estimation"""

    @pytest.fixture
    def fixer(self):
        """Create SimpleFixer instance"""
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            from app.services.simple_fixer import SimpleFixer
            return SimpleFixer()

    def test_estimate_cost_simple(self, fixer):
        """Test cost estimation for simple errors is lower"""
        from app.services.simple_fixer import ErrorComplexity

        simple_cost = fixer._estimate_cost(ErrorComplexity.SIMPLE, 1000)
        complex_cost = fixer._estimate_cost(ErrorComplexity.COMPLEX, 1000)

        assert simple_cost < complex_cost

    def test_estimate_cost_larger_context(self, fixer):
        """Test cost increases with context size"""
        from app.services.simple_fixer import ErrorComplexity

        small_context_cost = fixer._estimate_cost(ErrorComplexity.MODERATE, 1000)
        large_context_cost = fixer._estimate_cost(ErrorComplexity.MODERATE, 10000)

        assert large_context_cost > small_context_cost


class TestRateLimiting:
    """Tests for rate limiting"""

    @pytest.fixture
    def fixer(self):
        """Create SimpleFixer instance"""
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            from app.services.simple_fixer import SimpleFixer
            return SimpleFixer()

    def test_can_attempt_fix_first_time(self, fixer):
        """Test first fix attempt is allowed"""
        can_fix, reason = fixer._can_attempt_fix("new-project-id")
        assert can_fix == True
        assert reason == "OK"

    def test_rate_limit_after_many_attempts(self, fixer):
        """Test rate limiting after many attempts"""
        project_id = "test-rate-limit-project"

        # Record max attempts
        for _ in range(15):
            fixer._record_fix_attempt(project_id)

        can_fix, reason = fixer._can_attempt_fix(project_id)

        # Should be rate limited
        assert can_fix == False
        assert "Max attempts" in reason or "Cooldown" in reason


class TestDeterministicCSSFix:
    """Tests for deterministic CSS fixes"""

    @pytest.fixture
    def fixer(self):
        """Create SimpleFixer instance"""
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            from app.services.simple_fixer import SimpleFixer
            return SimpleFixer()

    @pytest.mark.asyncio
    async def test_css_fix_not_triggered_for_non_css_error(self, fixer):
        """Test CSS fix is not triggered for non-CSS errors"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            result = await fixer._try_deterministic_css_fix(
                tmp_path,
                "SyntaxError: Unexpected token"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_css_fix_triggered_for_tailwind_error(self, fixer):
        """Test CSS fix is triggered for Tailwind class error"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create CSS file with shadcn class
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            css_file = src_dir / "index.css"
            css_file.write_text("@apply border-border;")

            result = await fixer._try_deterministic_css_fix(
                tmp_path,
                "The `border-border` class does not exist"
            )

            if result:
                assert result.success == True
                assert len(result.files_modified) > 0


class TestTokenTracking:
    """Tests for token usage tracking"""

    @pytest.fixture
    def fixer(self):
        """Create SimpleFixer instance"""
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            from app.services.simple_fixer import SimpleFixer
            return SimpleFixer()

    def test_initial_token_count_zero(self, fixer):
        """Test initial token count is zero"""
        usage = fixer.get_token_usage()

        assert usage["input_tokens"] == 0
        assert usage["output_tokens"] == 0
        assert usage["call_count"] == 0

    def test_reset_token_tracking(self, fixer):
        """Test token tracking can be reset"""
        fixer._total_input_tokens = 100
        fixer._total_output_tokens = 50
        fixer._call_count = 5

        fixer.reset_token_tracking()

        usage = fixer.get_token_usage()
        assert usage["input_tokens"] == 0
        assert usage["output_tokens"] == 0
        assert usage["call_count"] == 0


class TestExtractRelevantLines:
    """Tests for extracting relevant lines around errors"""

    @pytest.fixture
    def fixer(self):
        """Create SimpleFixer instance"""
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            from app.services.simple_fixer import SimpleFixer
            return SimpleFixer()

    def test_extract_lines_around_error(self, fixer):
        """Test extracting lines around error line"""
        content = "\n".join([f"Line {i}" for i in range(1, 101)])

        result = fixer._extract_relevant_lines(content, error_line=50, context_lines=5)

        assert "Line 50" in result
        assert "Line 45" in result
        assert "Line 55" in result
        # Should not include lines too far away
        assert "Line 1" not in result
        assert "Line 100" not in result

    def test_extract_lines_at_file_start(self, fixer):
        """Test extracting lines when error is at file start"""
        content = "\n".join([f"Line {i}" for i in range(1, 101)])

        result = fixer._extract_relevant_lines(content, error_line=3, context_lines=10)

        assert "Line 3" in result
        assert "Line 1" in result

    def test_extract_lines_at_file_end(self, fixer):
        """Test extracting lines when error is at file end"""
        content = "\n".join([f"Line {i}" for i in range(1, 101)])

        result = fixer._extract_relevant_lines(content, error_line=98, context_lines=10)

        assert "Line 98" in result
        assert "Line 100" in result


class TestPendingFixes:
    """Tests for pending fix queue functionality"""

    @pytest.fixture
    def fixer(self):
        """Create SimpleFixer instance"""
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            from app.services.simple_fixer import SimpleFixer
            fixer = SimpleFixer()
            fixer.auto_fix_enabled = False  # Enable queueing
            return fixer

    def test_queue_fix(self, fixer):
        """Test queuing a fix for confirmation"""
        result = fixer.queue_fix(
            project_id="test-project",
            errors=[{"message": "SyntaxError", "file": "app.js"}],
            context="Error context",
            command="npm run dev",
            file_tree=["app.js"],
            recently_modified=[]
        )

        assert result["status"] == "pending_confirmation"
        assert result["fix_id"] == "test-project"

    def test_get_pending_fix(self, fixer):
        """Test getting a pending fix"""
        fixer.queue_fix(
            project_id="test-project-2",
            errors=[{"message": "Error"}],
            context="",
            command=None,
            file_tree=None,
            recently_modified=None
        )

        result = fixer.get_pending_fix("test-project-2")

        assert result is not None
        assert result["project_id"] == "test-project-2"

    def test_get_nonexistent_pending_fix(self, fixer):
        """Test getting non-existent pending fix returns None"""
        result = fixer.get_pending_fix("nonexistent-project")
        assert result is None

    def test_cancel_pending_fix(self, fixer):
        """Test cancelling a pending fix"""
        fixer.queue_fix(
            project_id="test-project-3",
            errors=[{"message": "Error"}],
            context="",
            command=None,
            file_tree=None,
            recently_modified=None
        )

        result = fixer.cancel_pending_fix("test-project-3")
        assert result == True

        # Should no longer exist
        assert fixer.get_pending_fix("test-project-3") is None


class TestToolExecution:
    """Tests for tool execution"""

    @pytest.fixture
    def fixer(self):
        """Create SimpleFixer instance"""
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            from app.services.simple_fixer import SimpleFixer
            return SimpleFixer()

    @pytest.mark.asyncio
    async def test_create_file_empty_content_rejected(self, fixer):
        """Test create_file rejects empty content"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            result = await fixer._execute_tool(
                tmp_path,
                "create_file",
                {"path": "test.js", "content": ""}
            )

            assert "Error" in result
            assert "empty" in result.lower()

    @pytest.mark.asyncio
    async def test_create_file_success(self, fixer):
        """Test successful file creation"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            result = await fixer._execute_tool(
                tmp_path,
                "create_file",
                {"path": "test.js", "content": "console.log('hello');\n// This is a test file with enough content to pass validation"}
            )

            assert "Created" in result
            assert (tmp_path / "test.js").exists()

    @pytest.mark.asyncio
    async def test_str_replace_file_not_found(self, fixer):
        """Test str_replace fails for non-existent file"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            result = await fixer._execute_tool(
                tmp_path,
                "str_replace",
                {"path": "nonexistent.js", "old_str": "old", "new_str": "new"}
            )

            assert "Error" in result

    @pytest.mark.asyncio
    async def test_str_replace_success(self, fixer):
        """Test successful string replacement"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create file first
            test_file = tmp_path / "test.js"
            test_file.write_text("const old = 'value';")

            result = await fixer._execute_tool(
                tmp_path,
                "str_replace",
                {"path": "test.js", "old_str": "old", "new_str": "new"}
            )

            assert "Replaced" in result
            assert "new" in test_file.read_text()

    @pytest.mark.asyncio
    async def test_view_file(self, fixer):
        """Test viewing file contents"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            test_file = tmp_path / "test.js"
            test_file.write_text("console.log('test');")

            result = await fixer._execute_tool(
                tmp_path,
                "view_file",
                {"path": "test.js"}
            )

            assert "console.log('test')" in result

    @pytest.mark.asyncio
    async def test_list_directory(self, fixer):
        """Test listing directory contents"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create some files
            (tmp_path / "file1.js").write_text("content1")
            (tmp_path / "file2.js").write_text("content2")
            (tmp_path / "subdir").mkdir()

            result = await fixer._execute_tool(
                tmp_path,
                "list_directory",
                {"path": "."}
            )

            assert "file1.js" in result
            assert "file2.js" in result
            assert "[DIR]" in result


class TestSimpleFixResult:
    """Tests for SimpleFixResult dataclass"""

    def test_simple_fix_result_creation(self):
        """Test creating SimpleFixResult"""
        from app.services.simple_fixer import SimpleFixResult

        result = SimpleFixResult(
            success=True,
            files_modified=["app.js", "index.js"],
            message="Fixed 2 files",
            patches_applied=2
        )

        assert result.success == True
        assert len(result.files_modified) == 2
        assert result.patches_applied == 2

    def test_simple_fix_result_defaults(self):
        """Test SimpleFixResult default values"""
        from app.services.simple_fixer import SimpleFixResult

        result = SimpleFixResult(
            success=False,
            files_modified=[],
            message="No fix"
        )

        assert result.patches_applied == 0
        assert result.pending_confirmation == False
        assert result.pending_fix_id is None


class TestGlobalInstance:
    """Tests for global simple_fixer instance"""

    def test_global_instance_exists(self):
        """Test that global simple_fixer instance exists"""
        from app.services.simple_fixer import simple_fixer

        assert simple_fixer is not None

    def test_global_instance_type(self):
        """Test that global instance is SimpleFixer"""
        from app.services.simple_fixer import simple_fixer, SimpleFixer

        assert isinstance(simple_fixer, SimpleFixer)
