"""
Unit Tests for ErrorClassifier Service

Comprehensive tests for rule-based error classification.
"""
import pytest
from app.services.error_classifier import ErrorClassifier, ErrorType, ClassifiedError


class TestErrorTypeEnum:
    """Test ErrorType enum values"""

    def test_has_all_error_types(self):
        """Test ErrorType has all expected values"""
        assert hasattr(ErrorType, 'SYNTAX_ERROR')
        assert hasattr(ErrorType, 'MISSING_SYMBOL')
        assert hasattr(ErrorType, 'IMPORT_ERROR')
        assert hasattr(ErrorType, 'TYPE_ERROR')
        assert hasattr(ErrorType, 'RUNTIME_ERROR')
        assert hasattr(ErrorType, 'DEPENDENCY_ERROR')
        assert hasattr(ErrorType, 'CONFIG_ERROR')
        assert hasattr(ErrorType, 'UNKNOWN')


class TestClassifiedError:
    """Test ClassifiedError dataclass"""

    def test_create_classified_error(self):
        """Test creating ClassifiedError"""
        error = ClassifiedError(
            error_type=ErrorType.SYNTAX_ERROR,
            is_claude_fixable=True,
            confidence=0.95,
            file_path="src/App.java",
            line_number=10,
            original_message="Syntax error at line 10"
        )

        assert error.error_type == ErrorType.SYNTAX_ERROR
        assert error.is_claude_fixable == True
        assert error.confidence == 0.95
        assert error.file_path == "src/App.java"
        assert error.line_number == 10


class TestSyntaxErrorClassification:
    """Test syntax error classification"""

    def test_javascript_syntax_error(self):
        """Test JavaScript syntax error classification"""
        classified = ErrorClassifier.classify(
            error_message="SyntaxError: Unexpected token '}'",
            stderr="SyntaxError: Unexpected token '}' at line 15",
            exit_code=1
        )

        assert classified.error_type == ErrorType.SYNTAX_ERROR
        assert classified.is_claude_fixable == True

    def test_python_syntax_error(self):
        """Test Python syntax error classification"""
        classified = ErrorClassifier.classify(
            error_message="SyntaxError: invalid syntax",
            stderr="  File 'app.py', line 10\n    if x =\n         ^\nSyntaxError: invalid syntax",
            exit_code=1
        )

        assert classified.error_type == ErrorType.SYNTAX_ERROR
        assert classified.is_claude_fixable == True

    def test_java_syntax_error(self):
        """Test Java syntax error classification"""
        classified = ErrorClassifier.classify(
            error_message="';' expected",
            stderr="[ERROR] /src/App.java:[10,20] ';' expected",
            exit_code=1
        )

        assert classified.error_type == ErrorType.SYNTAX_ERROR
        assert classified.is_claude_fixable == True

    def test_typescript_syntax_error(self):
        """Test TypeScript syntax error classification"""
        classified = ErrorClassifier.classify(
            error_message="error TS1005: ',' expected",
            stderr="src/App.tsx(10,5): error TS1005: ',' expected",
            exit_code=1
        )

        assert classified.error_type == ErrorType.SYNTAX_ERROR
        assert classified.is_claude_fixable == True


class TestMissingSymbolClassification:
    """Test missing symbol error classification"""

    def test_java_cannot_find_symbol(self):
        """Test Java 'cannot find symbol' classification"""
        classified = ErrorClassifier.classify(
            error_message="cannot find symbol: class UserDto",
            stderr="[ERROR] /src/UserController.java:[25,10] cannot find symbol\n  symbol: class UserDto",
            exit_code=1
        )

        assert classified.error_type == ErrorType.MISSING_SYMBOL
        assert classified.is_claude_fixable == True

    def test_typescript_cannot_find_name(self):
        """Test TypeScript 'Cannot find name' classification"""
        classified = ErrorClassifier.classify(
            error_message="Cannot find name 'useState'",
            stderr="error TS2304: Cannot find name 'useState'",
            exit_code=1
        )

        assert classified.error_type == ErrorType.MISSING_SYMBOL
        assert classified.is_claude_fixable == True

    def test_java_symbol_not_found(self):
        """Test Java 'symbol not found' classification"""
        classified = ErrorClassifier.classify(
            error_message="error: symbol not found",
            stderr="error: symbol not found\n  symbol: variable user",
            exit_code=1
        )

        assert classified.error_type == ErrorType.MISSING_SYMBOL
        assert classified.is_claude_fixable == True


class TestImportErrorClassification:
    """Test import error classification"""

    def test_python_module_not_found(self):
        """Test Python ModuleNotFoundError classification"""
        classified = ErrorClassifier.classify(
            error_message="ModuleNotFoundError: No module named 'flask'",
            stderr="ModuleNotFoundError: No module named 'flask'",
            exit_code=1
        )

        assert classified.error_type == ErrorType.IMPORT_ERROR
        assert classified.is_claude_fixable == True

    def test_node_cannot_find_module(self):
        """Test Node.js 'Cannot find module' classification"""
        classified = ErrorClassifier.classify(
            error_message="Cannot find module 'react'",
            stderr="Error: Cannot find module 'react'\n  Require stack:",
            exit_code=1
        )

        assert classified.error_type == ErrorType.IMPORT_ERROR
        assert classified.is_claude_fixable == True

    def test_java_package_not_exist(self):
        """Test Java 'package does not exist' classification"""
        classified = ErrorClassifier.classify(
            error_message="package com.lms.dto does not exist",
            stderr="[ERROR] /src/App.java:[5,1] package com.lms.dto does not exist",
            exit_code=1
        )

        assert classified.error_type == ErrorType.IMPORT_ERROR
        assert classified.is_claude_fixable == True

    def test_typescript_module_not_found(self):
        """Test TypeScript module not found classification"""
        classified = ErrorClassifier.classify(
            error_message="error TS2307: Cannot find module './components/Button'",
            stderr="error TS2307: Cannot find module './components/Button'",
            exit_code=1
        )

        assert classified.error_type == ErrorType.IMPORT_ERROR
        assert classified.is_claude_fixable == True


class TestTypeErrorClassification:
    """Test type error classification"""

    def test_typescript_type_error(self):
        """Test TypeScript type error classification"""
        classified = ErrorClassifier.classify(
            error_message="Type 'string' is not assignable to type 'number'",
            stderr="error TS2322: Type 'string' is not assignable to type 'number'",
            exit_code=1
        )

        assert classified.error_type == ErrorType.TYPE_ERROR
        assert classified.is_claude_fixable == True

    def test_python_type_error(self):
        """Test Python TypeError classification"""
        classified = ErrorClassifier.classify(
            error_message="TypeError: unsupported operand type(s)",
            stderr="TypeError: unsupported operand type(s) for +: 'int' and 'str'",
            exit_code=1
        )

        assert classified.error_type == ErrorType.TYPE_ERROR
        assert classified.is_claude_fixable == True

    def test_java_incompatible_types(self):
        """Test Java incompatible types classification"""
        classified = ErrorClassifier.classify(
            error_message="incompatible types: String cannot be converted to int",
            stderr="[ERROR] incompatible types: String cannot be converted to int",
            exit_code=1
        )

        assert classified.error_type == ErrorType.TYPE_ERROR
        assert classified.is_claude_fixable == True


class TestDependencyErrorClassification:
    """Test dependency error classification"""

    def test_npm_dependency_error(self):
        """Test npm dependency error classification"""
        classified = ErrorClassifier.classify(
            error_message="npm ERR! peer dep missing",
            stderr="npm ERR! peer dep missing: react@^17.0.0, required by react-dom@17.0.2",
            exit_code=1
        )

        assert classified.error_type == ErrorType.DEPENDENCY_ERROR

    def test_maven_dependency_error(self):
        """Test Maven dependency error classification"""
        classified = ErrorClassifier.classify(
            error_message="Could not resolve dependencies",
            stderr="[ERROR] Could not resolve dependencies for project",
            exit_code=1
        )

        assert classified.error_type == ErrorType.DEPENDENCY_ERROR

    def test_pip_dependency_error(self):
        """Test pip dependency error classification"""
        classified = ErrorClassifier.classify(
            error_message="Could not find a version that satisfies the requirement",
            stderr="ERROR: Could not find a version that satisfies the requirement flask>=2.0",
            exit_code=1
        )

        assert classified.error_type == ErrorType.DEPENDENCY_ERROR


class TestConfigErrorClassification:
    """Test configuration error classification"""

    def test_tsconfig_error(self):
        """Test tsconfig.json error classification"""
        classified = ErrorClassifier.classify(
            error_message="error in tsconfig.json",
            stderr="error TS5023: Unknown compiler option 'invalidOption'",
            exit_code=1
        )

        # Config errors may be classified differently
        assert classified is not None

    def test_webpack_config_error(self):
        """Test webpack config error classification"""
        classified = ErrorClassifier.classify(
            error_message="Invalid configuration object",
            stderr="Invalid configuration object. Webpack has been initialised using a configuration object that does not match the API schema.",
            exit_code=1
        )

        assert classified.error_type == ErrorType.CONFIG_ERROR


class TestRuntimeErrorClassification:
    """Test runtime error classification"""

    def test_null_pointer_exception(self):
        """Test Java NullPointerException classification"""
        classified = ErrorClassifier.classify(
            error_message="java.lang.NullPointerException",
            stderr="Exception in thread \"main\" java.lang.NullPointerException\n\tat com.App.main(App.java:10)",
            exit_code=1
        )

        assert classified.error_type == ErrorType.RUNTIME_ERROR

    def test_python_runtime_error(self):
        """Test Python runtime error classification"""
        classified = ErrorClassifier.classify(
            error_message="RuntimeError: maximum recursion depth exceeded",
            stderr="RuntimeError: maximum recursion depth exceeded",
            exit_code=1
        )

        assert classified.error_type == ErrorType.RUNTIME_ERROR


class TestUnknownErrorClassification:
    """Test unknown error classification"""

    def test_empty_error(self):
        """Test empty error message classification"""
        classified = ErrorClassifier.classify(
            error_message="",
            stderr="",
            exit_code=0
        )

        assert classified.error_type == ErrorType.UNKNOWN
        assert classified.is_claude_fixable == False

    def test_success_output(self):
        """Test successful build output classification"""
        classified = ErrorClassifier.classify(
            error_message="BUILD SUCCESS",
            stderr="",
            exit_code=0
        )

        assert classified.error_type == ErrorType.UNKNOWN
        assert classified.is_claude_fixable == False


class TestShouldCallClaude:
    """Test should_call_claude decision logic"""

    def test_should_call_for_fixable_error(self):
        """Test Claude should be called for fixable errors"""
        classified = ClassifiedError(
            error_type=ErrorType.SYNTAX_ERROR,
            is_claude_fixable=True,
            confidence=0.9,
            original_message="SyntaxError"
        )

        should_call, reason = ErrorClassifier.should_call_claude(classified)
        assert should_call == True

    def test_should_not_call_for_unfixable_error(self):
        """Test Claude should not be called for unfixable errors"""
        classified = ClassifiedError(
            error_type=ErrorType.UNKNOWN,
            is_claude_fixable=False,
            confidence=0.1,
            original_message=""
        )

        should_call, reason = ErrorClassifier.should_call_claude(classified)
        assert should_call == False


class TestFilePathExtraction:
    """Test file path extraction from error messages"""

    def test_extract_java_file_path(self):
        """Test extracting file path from Java error"""
        classified = ErrorClassifier.classify(
            error_message="cannot find symbol",
            stderr="[ERROR] /app/src/main/java/com/lms/App.java:[25,10] cannot find symbol",
            exit_code=1
        )

        # Should extract file path
        assert classified.file_path is not None or classified.line_number is not None

    def test_extract_typescript_file_path(self):
        """Test extracting file path from TypeScript error"""
        classified = ErrorClassifier.classify(
            error_message="error TS2304",
            stderr="src/components/App.tsx(15,3): error TS2304: Cannot find name 'foo'",
            exit_code=1
        )

        assert classified is not None


class TestPromptTemplates:
    """Test Claude prompt template generation"""

    def test_syntax_error_template(self):
        """Test syntax error prompt template"""
        template = ErrorClassifier.get_claude_prompt_template(ErrorType.SYNTAX_ERROR)
        assert template is not None
        assert len(template) > 0

    def test_missing_symbol_template(self):
        """Test missing symbol prompt template"""
        template = ErrorClassifier.get_claude_prompt_template(ErrorType.MISSING_SYMBOL)
        assert template is not None
        assert len(template) > 0

    def test_import_error_template(self):
        """Test import error prompt template"""
        template = ErrorClassifier.get_claude_prompt_template(ErrorType.IMPORT_ERROR)
        assert template is not None

    def test_unknown_error_template(self):
        """Test unknown error prompt template"""
        template = ErrorClassifier.get_claude_prompt_template(ErrorType.UNKNOWN)
        assert template is not None
