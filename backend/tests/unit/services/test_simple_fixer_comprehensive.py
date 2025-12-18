"""
Comprehensive Unit Tests for SimpleFixer Service
Tests for: error classification, model selection, fix execution, tool handling
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path
import tempfile
import shutil

from app.services.simple_fixer import (
    SimpleFixer,
    SimpleFixResult,
    ErrorComplexity,
    PendingFix,
    _fix_timestamps,
    _pending_fixes
)


class TestErrorClassification:
    """Test error complexity classification"""

    @pytest.fixture
    def fixer(self):
        """Create SimpleFixer instance with mocked API client"""
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            fixer = SimpleFixer()
            return fixer

    def test_classify_syntax_error_as_simple(self, fixer):
        """Test that syntax errors are classified as SIMPLE"""
        errors = [{"message": "SyntaxError: Unexpected token }", "file": "src/index.js", "line": 10}]
        context = "SyntaxError: Unexpected token }"

        complexity = fixer._classify_error_complexity(errors, context)

        assert complexity == ErrorComplexity.SIMPLE

    def test_classify_import_error_as_simple(self, fixer):
        """Test that import errors are classified as SIMPLE"""
        errors = [{"message": "ModuleNotFoundError: No module named 'flask'", "file": "app.py", "line": 1}]
        context = "ModuleNotFoundError: No module named 'flask'"

        complexity = fixer._classify_error_complexity(errors, context)

        assert complexity == ErrorComplexity.SIMPLE

    def test_classify_typescript_error_as_simple(self, fixer):
        """Test that TypeScript errors are classified as SIMPLE"""
        errors = [{"message": "error TS2304: Cannot find name 'MyComponent'", "file": "App.tsx", "line": 5}]
        context = "error TS2304: Cannot find name 'MyComponent'"

        complexity = fixer._classify_error_complexity(errors, context)

        assert complexity == ErrorComplexity.SIMPLE

    def test_classify_python_name_error_as_simple(self, fixer):
        """Test that Python NameError is classified as SIMPLE"""
        errors = [{"message": "NameError: name 'undefined_var' is not defined", "file": "main.py", "line": 20}]
        context = "NameError: name 'undefined_var' is not defined"

        complexity = fixer._classify_error_complexity(errors, context)

        assert complexity == ErrorComplexity.SIMPLE

    def test_classify_multiple_errors_as_complex(self, fixer):
        """Test that multiple errors are classified as COMPLEX"""
        errors = [
            {"message": "Error 1", "file": "file1.js"},
            {"message": "Error 2", "file": "file2.js"},
            {"message": "Error 3", "file": "file3.js"},
            {"message": "Error 4", "file": "file4.js"}
        ]
        context = "Multiple errors"

        complexity = fixer._classify_error_complexity(errors, context)

        assert complexity == ErrorComplexity.COMPLEX

    def test_classify_config_error_as_moderate(self, fixer):
        """Test that config file errors are classified as MODERATE"""
        errors = [{"message": "Invalid tsconfig.json configuration", "file": "tsconfig.json"}]
        context = "tsconfig error"

        complexity = fixer._classify_error_complexity(errors, context)

        assert complexity == ErrorComplexity.MODERATE

    def test_classify_empty_errors_as_simple(self, fixer):
        """Test that empty errors default to SIMPLE"""
        errors = []
        context = ""

        complexity = fixer._classify_error_complexity(errors, context)

        assert complexity == ErrorComplexity.SIMPLE


class TestModelSelection:
    """Test model selection based on complexity"""

    @pytest.fixture
    def fixer(self):
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            return SimpleFixer()

    def test_select_haiku_for_simple(self, fixer):
        """Test Haiku is selected for SIMPLE errors"""
        model = fixer._select_model(ErrorComplexity.SIMPLE)

        assert "haiku" in model.lower()

    def test_select_sonnet_for_moderate(self, fixer):
        """Test Sonnet is selected for MODERATE errors"""
        model = fixer._select_model(ErrorComplexity.MODERATE)

        assert "sonnet" in model.lower()

    def test_select_sonnet_for_complex(self, fixer):
        """Test Sonnet is selected for COMPLEX errors"""
        model = fixer._select_model(ErrorComplexity.COMPLEX)

        assert "sonnet" in model.lower()


class TestCostEstimation:
    """Test cost estimation"""

    @pytest.fixture
    def fixer(self):
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            return SimpleFixer()

    def test_estimate_cost_simple(self, fixer):
        """Test cost estimation for simple errors"""
        cost = fixer._estimate_cost(ErrorComplexity.SIMPLE, 1000)

        assert cost > 0
        assert cost < 1.0  # Should be relatively cheap

    def test_estimate_cost_complex(self, fixer):
        """Test cost estimation for complex errors"""
        cost_simple = fixer._estimate_cost(ErrorComplexity.SIMPLE, 1000)
        cost_complex = fixer._estimate_cost(ErrorComplexity.COMPLEX, 1000)

        # Complex should cost more (uses Sonnet)
        assert cost_complex > cost_simple


class TestRateLimiting:
    """Test rate limiting functionality"""

    @pytest.fixture
    def fixer(self):
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            # Clear rate limit state
            _fix_timestamps.clear()
            return SimpleFixer()

    def test_can_attempt_fix_first_time(self, fixer):
        """Test first fix attempt is allowed"""
        can_fix, reason = fixer._can_attempt_fix("test-project-1")

        assert can_fix is True
        assert reason == "OK"

    def test_rate_limit_cooldown(self, fixer):
        """Test cooldown is enforced after fix attempt"""
        project_id = "test-project-2"

        # Record a fix attempt
        fixer._record_fix_attempt(project_id)

        # Second attempt should be rate limited
        can_fix, reason = fixer._can_attempt_fix(project_id)

        assert can_fix is False
        assert "cooldown" in reason.lower()


class TestPendingFixes:
    """Test pending fix queue functionality"""

    @pytest.fixture
    def fixer(self):
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            # Clear pending fixes
            _pending_fixes.clear()
            fixer = SimpleFixer()
            fixer.auto_fix_enabled = False  # Enable queueing
            return fixer

    def test_queue_fix(self, fixer):
        """Test queuing a fix"""
        result = fixer.queue_fix(
            project_id="test-project",
            errors=[{"message": "Test error", "source": "browser"}],
            context="Error context",
            command="npm run build",
            file_tree=["src/index.js"],
            recently_modified=[]
        )

        assert result["status"] == "pending_confirmation"
        assert "estimated_cost" in result

    def test_get_pending_fix(self, fixer):
        """Test getting pending fix details"""
        project_id = "test-project-get"
        fixer.queue_fix(
            project_id=project_id,
            errors=[{"message": "Test error"}],
            context="",
            command=None,
            file_tree=None,
            recently_modified=None
        )

        pending = fixer.get_pending_fix(project_id)

        assert pending is not None
        assert pending["project_id"] == project_id

    def test_cancel_pending_fix(self, fixer):
        """Test canceling pending fix"""
        project_id = "test-project-cancel"
        fixer.queue_fix(
            project_id=project_id,
            errors=[{"message": "Test error"}],
            context="",
            command=None,
            file_tree=None,
            recently_modified=None
        )

        result = fixer.cancel_pending_fix(project_id)

        assert result is True
        assert fixer.get_pending_fix(project_id) is None


class TestShouldFix:
    """Test should_fix decision logic"""

    @pytest.fixture
    def fixer(self):
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            return SimpleFixer()

    @pytest.mark.asyncio
    async def test_should_fix_non_zero_exit_code(self, fixer):
        """Test fix is needed for non-zero exit code"""
        result = await fixer.should_fix(exit_code=1, output="Some error")

        assert result is True

    @pytest.mark.asyncio
    async def test_should_not_fix_success(self, fixer):
        """Test fix not needed for success output"""
        result = await fixer.should_fix(exit_code=0, output="Compiled successfully")

        assert result is False

    @pytest.mark.asyncio
    async def test_should_fix_syntax_error(self, fixer):
        """Test fix is needed for syntax error in output"""
        result = await fixer.should_fix(exit_code=None, output="SyntaxError: Unexpected token")

        assert result is True

    @pytest.mark.asyncio
    async def test_should_fix_module_not_found(self, fixer):
        """Test fix is needed for module not found"""
        result = await fixer.should_fix(exit_code=None, output="Cannot find module 'react'")

        assert result is True

    @pytest.mark.asyncio
    async def test_should_not_fix_ready_message(self, fixer):
        """Test fix not needed for ready message"""
        result = await fixer.should_fix(exit_code=0, output="Server ready in 200ms")

        assert result is False

    @pytest.mark.asyncio
    async def test_should_fix_build_failure(self, fixer):
        """Test fix is needed for build failure"""
        result = await fixer.should_fix(exit_code=1, output="BUILD FAILURE")

        assert result is True


class TestDeterministicCSSFix:
    """Test deterministic CSS fix functionality"""

    @pytest.fixture
    def fixer(self):
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            return SimpleFixer()

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory"""
        temp_dir = tempfile.mkdtemp()
        src_dir = Path(temp_dir) / "src"
        src_dir.mkdir()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_css_fix_border_border(self, fixer, temp_project):
        """Test fixing @apply border-border class"""
        # Create CSS file with shadcn class
        css_file = temp_project / "src" / "index.css"
        css_file.write_text("@apply border-border;")

        result = await fixer._try_deterministic_css_fix(
            temp_project,
            "The `border-border` class does not exist"
        )

        assert result is not None
        assert result.success is True
        assert len(result.files_modified) > 0

    @pytest.mark.asyncio
    async def test_css_fix_bg_background(self, fixer, temp_project):
        """Test fixing @apply bg-background class"""
        css_file = temp_project / "src" / "index.css"
        css_file.write_text("@apply bg-background;")

        result = await fixer._try_deterministic_css_fix(
            temp_project,
            "The `bg-background` class does not exist"
        )

        assert result is not None
        assert result.success is True

    @pytest.mark.asyncio
    async def test_css_fix_no_match(self, fixer, temp_project):
        """Test no fix when error doesn't match CSS pattern"""
        result = await fixer._try_deterministic_css_fix(
            temp_project,
            "Some other error"
        )

        assert result is None


class TestToolExecution:
    """Test tool execution functionality"""

    @pytest.fixture
    def fixer(self):
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            return SimpleFixer()

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_create_file(self, fixer, temp_project):
        """Test create_file tool"""
        result = await fixer._execute_tool(
            temp_project,
            "create_file",
            {"path": "test.js", "content": "console.log('test');"}
        )

        assert "Created" in result
        assert (temp_project / "test.js").exists()

    @pytest.mark.asyncio
    async def test_create_file_empty_content_rejected(self, fixer, temp_project):
        """Test create_file rejects empty content"""
        result = await fixer._execute_tool(
            temp_project,
            "create_file",
            {"path": "empty.js", "content": ""}
        )

        assert "Error" in result
        assert "empty content" in result.lower()

    @pytest.mark.asyncio
    async def test_str_replace(self, fixer, temp_project):
        """Test str_replace tool"""
        # Create file first
        test_file = temp_project / "replace.js"
        test_file.write_text("const old = 'value';")

        result = await fixer._execute_tool(
            temp_project,
            "str_replace",
            {"path": "replace.js", "old_str": "old", "new_str": "new"}
        )

        assert "Replaced" in result
        assert "new" in test_file.read_text()

    @pytest.mark.asyncio
    async def test_str_replace_not_found(self, fixer, temp_project):
        """Test str_replace when string not found"""
        test_file = temp_project / "noreplace.js"
        test_file.write_text("const value = 'test';")

        result = await fixer._execute_tool(
            temp_project,
            "str_replace",
            {"path": "noreplace.js", "old_str": "nonexistent", "new_str": "replacement"}
        )

        assert "Error" in result
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_view_file(self, fixer, temp_project):
        """Test view_file tool"""
        test_file = temp_project / "view.js"
        test_file.write_text("const content = 'test';")

        result = await fixer._execute_tool(
            temp_project,
            "view_file",
            {"path": "view.js"}
        )

        assert "const content" in result

    @pytest.mark.asyncio
    async def test_view_file_not_found(self, fixer, temp_project):
        """Test view_file when file doesn't exist"""
        result = await fixer._execute_tool(
            temp_project,
            "view_file",
            {"path": "nonexistent.js"}
        )

        assert "Error" in result

    @pytest.mark.asyncio
    async def test_list_directory(self, fixer, temp_project):
        """Test list_directory tool"""
        # Create some files
        (temp_project / "file1.js").write_text("content")
        (temp_project / "file2.js").write_text("content")
        subdir = temp_project / "subdir"
        subdir.mkdir()

        result = await fixer._execute_tool(
            temp_project,
            "list_directory",
            {"path": "."}
        )

        assert "file1.js" in result
        assert "[DIR]" in result or "[FILE]" in result


class TestContextGathering:
    """Test context gathering for AI"""

    @pytest.fixture
    def fixer(self):
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            return SimpleFixer()

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with files"""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)

        # Create package.json
        (project_path / "package.json").write_text('{"name": "test"}')

        # Create source file
        src_dir = project_path / "src"
        src_dir.mkdir()
        (src_dir / "index.js").write_text("console.log('test');\n" * 100)

        yield project_path
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_gather_context_includes_config(self, fixer, temp_project):
        """Test that config files are included in context"""
        errors = [{"message": "Error", "file": "src/index.js", "line": 10}]

        context = await fixer._gather_context_optimized(temp_project, "", errors)

        assert "package.json" in context

    @pytest.mark.asyncio
    async def test_gather_context_extracts_relevant_lines(self, fixer, temp_project):
        """Test that only relevant lines are extracted for large files"""
        errors = [{"message": "Error at line 50", "file": "src/index.js", "line": 50}]

        context = await fixer._gather_context_optimized(temp_project, "line 50", errors)

        # Should have the file in context
        assert any("index.js" in key for key in context.keys())


class TestTokenTracking:
    """Test token usage tracking"""

    @pytest.fixture
    def fixer(self):
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            return SimpleFixer()

    def test_reset_token_tracking(self, fixer):
        """Test resetting token tracking"""
        fixer._total_input_tokens = 100
        fixer._total_output_tokens = 200
        fixer._call_count = 5

        fixer.reset_token_tracking()

        assert fixer._total_input_tokens == 0
        assert fixer._total_output_tokens == 0
        assert fixer._call_count == 0

    def test_get_token_usage(self, fixer):
        """Test getting token usage stats"""
        fixer._total_input_tokens = 500
        fixer._total_output_tokens = 1000
        fixer._call_count = 3

        usage = fixer.get_token_usage()

        assert usage["input_tokens"] == 500
        assert usage["output_tokens"] == 1000
        assert usage["total_tokens"] == 1500
        assert usage["call_count"] == 3


class TestExtractRelevantLines:
    """Test line extraction for partial file context"""

    @pytest.fixture
    def fixer(self):
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            return SimpleFixer()

    def test_extract_lines_around_error(self, fixer):
        """Test extracting lines around error line"""
        content = "\n".join([f"line {i}" for i in range(1, 101)])

        result = fixer._extract_relevant_lines(content, error_line=50, context_lines=5)

        # Should have lines around 50
        assert "line 45" in result or "45" in result
        assert "line 50" in result or "50" in result
        assert "line 55" in result or "55" in result

    def test_extract_lines_at_start(self, fixer):
        """Test extracting lines when error is at start"""
        content = "\n".join([f"line {i}" for i in range(1, 101)])

        result = fixer._extract_relevant_lines(content, error_line=3, context_lines=5)

        # Should handle edge case gracefully
        assert "line 1" in result or "1" in result

    def test_extract_lines_at_end(self, fixer):
        """Test extracting lines when error is at end"""
        content = "\n".join([f"line {i}" for i in range(1, 101)])

        result = fixer._extract_relevant_lines(content, error_line=98, context_lines=5)

        # Should handle edge case gracefully
        assert "line 100" in result or "100" in result


class TestFormatHelpers:
    """Test formatting helper methods"""

    @pytest.fixture
    def fixer(self):
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            return SimpleFixer()

    def test_format_errors(self, fixer):
        """Test formatting errors for prompt"""
        errors = [
            {"message": "Error 1", "source": "browser", "file": "test.js", "line": 10},
            {"message": "Error 2", "source": "build"}
        ]

        result = fixer._format_errors(errors)

        assert "[BROWSER]" in result
        assert "[BUILD]" in result
        assert "test.js:10" in result

    def test_format_recently_modified_empty(self, fixer):
        """Test formatting empty recently modified list"""
        result = fixer._format_recently_modified(None)

        assert result == "(none)"

    def test_format_recently_modified_with_files(self, fixer):
        """Test formatting recently modified files"""
        files = [
            {"path": "src/index.js", "action": "modified"},
            {"path": "package.json", "action": "created"}
        ]

        result = fixer._format_recently_modified(files)

        assert "src/index.js" in result
        assert "modified" in result

    def test_format_files(self, fixer):
        """Test formatting files for prompt"""
        files = {
            "src/index.js": "console.log('test');",
            "package.json": "{}"
        }

        result = fixer._format_files(files)

        assert "=== src/index.js ===" in result
        assert "=== package.json ===" in result

    def test_format_files_empty(self, fixer):
        """Test formatting empty files dict"""
        result = fixer._format_files({})

        assert "No relevant files" in result


class TestGetTools:
    """Test tool definitions"""

    @pytest.fixture
    def fixer(self):
        with patch('app.services.simple_fixer.AsyncAnthropic'):
            return SimpleFixer()

    def test_get_tools_includes_create_file(self, fixer):
        """Test tools include create_file"""
        tools = fixer._get_tools()

        tool_names = [t["name"] for t in tools]
        assert "create_file" in tool_names

    def test_get_tools_includes_str_replace(self, fixer):
        """Test tools include str_replace"""
        tools = fixer._get_tools()

        tool_names = [t["name"] for t in tools]
        assert "str_replace" in tool_names

    def test_get_tools_includes_view_file(self, fixer):
        """Test tools include view_file"""
        tools = fixer._get_tools()

        tool_names = [t["name"] for t in tools]
        assert "view_file" in tool_names

    def test_get_tools_includes_list_directory(self, fixer):
        """Test tools include list_directory"""
        tools = fixer._get_tools()

        tool_names = [t["name"] for t in tools]
        assert "list_directory" in tool_names
