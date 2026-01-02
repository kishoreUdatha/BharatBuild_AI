"""
Unit Tests for ErrorClassifier Service

Tests for rule-based error classification based on actual implementation.
"""
import pytest
from app.services.error_classifier import ErrorClassifier, ErrorType, ClassifiedError


class TestErrorTypeEnum:
    """Test ErrorType enum values"""

    def test_has_all_error_types(self):
        """Test ErrorType has all expected values"""
        # Fixable by Claude
        assert hasattr(ErrorType, 'DEPENDENCY_CONFLICT')
        assert hasattr(ErrorType, 'MISSING_FILE')
        assert hasattr(ErrorType, 'IMPORT_ERROR')
        assert hasattr(ErrorType, 'SYNTAX_ERROR')
        assert hasattr(ErrorType, 'TYPE_ERROR')
        assert hasattr(ErrorType, 'UNDEFINED_VARIABLE')
        assert hasattr(ErrorType, 'MISSING_EXPORT')
        assert hasattr(ErrorType, 'REACT_ERROR')
        assert hasattr(ErrorType, 'CSS_ERROR')
        assert hasattr(ErrorType, 'CONFIG_ERROR')

        # NOT fixable by Claude
        assert hasattr(ErrorType, 'INFRA_ERROR')
        assert hasattr(ErrorType, 'NETWORK_ERROR')
        assert hasattr(ErrorType, 'PORT_CONFLICT')
        assert hasattr(ErrorType, 'PERMISSION_ERROR')
        assert hasattr(ErrorType, 'MEMORY_ERROR')
        assert hasattr(ErrorType, 'TIMEOUT_ERROR')
        assert hasattr(ErrorType, 'REGISTRY_ERROR')

        # Unknown
        assert hasattr(ErrorType, 'UNKNOWN')


class TestClassifiedError:
    """Test ClassifiedError dataclass"""

    def test_create_classified_error(self):
        """Test creating ClassifiedError with all required fields"""
        error = ClassifiedError(
            error_type=ErrorType.SYNTAX_ERROR,
            is_claude_fixable=True,
            confidence=0.95,
            file_path="src/App.java",
            line_number=10,
            original_message="Syntax error at line 10",
            suggested_action="Fix syntax error",
            extracted_context={}
        )

        assert error.error_type == ErrorType.SYNTAX_ERROR
        assert error.is_claude_fixable == True
        assert error.confidence == 0.95
        assert error.file_path == "src/App.java"
        assert error.line_number == 10
        assert error.suggested_action == "Fix syntax error"


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

    def test_unexpected_token_syntax_error(self):
        """Test unexpected token classification"""
        classified = ErrorClassifier.classify(
            error_message="Unexpected token",
            stderr="Unexpected token 'if' at line 5",
            exit_code=1
        )

        assert classified.error_type == ErrorType.SYNTAX_ERROR


class TestUndefinedVariableClassification:
    """Test undefined variable (was MISSING_SYMBOL) error classification"""

    def test_java_cannot_find_symbol(self):
        """Test Java 'cannot find symbol' classification"""
        classified = ErrorClassifier.classify(
            error_message="cannot find symbol: class UserDto",
            stderr="[ERROR] /src/UserController.java:[25,10] cannot find symbol\n  symbol: class UserDto",
            exit_code=1
        )

        assert classified.error_type == ErrorType.UNDEFINED_VARIABLE
        assert classified.is_claude_fixable == True

    def test_typescript_cannot_find_name(self):
        """Test TypeScript 'Cannot find name' classification"""
        classified = ErrorClassifier.classify(
            error_message="Cannot find name 'useState'",
            stderr="error TS2304: Cannot find name 'useState'",
            exit_code=1
        )

        assert classified.error_type == ErrorType.UNDEFINED_VARIABLE
        assert classified.is_claude_fixable == True

    def test_reference_error_not_defined(self):
        """Test ReferenceError not defined classification"""
        classified = ErrorClassifier.classify(
            error_message="ReferenceError: myVar is not defined",
            stderr="ReferenceError: myVar is not defined",
            exit_code=1
        )

        assert classified.error_type == ErrorType.UNDEFINED_VARIABLE


class TestDependencyConflictClassification:
    """Test dependency conflict error classification"""

    def test_npm_module_not_found(self):
        """Test npm 'Cannot find module' classification"""
        classified = ErrorClassifier.classify(
            error_message="Cannot find module 'react'",
            stderr="Error: Cannot find module 'react'\n  Require stack:",
            exit_code=1
        )

        assert classified.error_type == ErrorType.DEPENDENCY_CONFLICT
        assert classified.is_claude_fixable == True

    def test_eresolve_dependency_error(self):
        """Test npm ERESOLVE dependency error classification"""
        classified = ErrorClassifier.classify(
            error_message="npm ERR! ERESOLVE unable to resolve",
            stderr="npm ERR! ERESOLVE unable to resolve dependency tree",
            exit_code=1
        )

        assert classified.error_type == ErrorType.DEPENDENCY_CONFLICT

    def test_peer_dependency_error(self):
        """Test peer dependency error classification"""
        classified = ErrorClassifier.classify(
            error_message="npm ERR! peer dep missing",
            stderr="npm ERR! peer dep missing: react@^17.0.0, required by react-dom@17.0.2",
            exit_code=1
        )

        assert classified.error_type == ErrorType.DEPENDENCY_CONFLICT


class TestImportErrorClassification:
    """Test import error classification"""

    def test_java_package_not_exist(self):
        """Test Java 'package does not exist' classification"""
        classified = ErrorClassifier.classify(
            error_message="package com.lms.dto does not exist",
            stderr="[ERROR] /src/App.java:[5,1] package com.lms.dto does not exist",
            exit_code=1
        )

        assert classified.error_type == ErrorType.IMPORT_ERROR
        assert classified.is_claude_fixable == True

    def test_export_not_found(self):
        """Test 'does not provide an export' classification"""
        classified = ErrorClassifier.classify(
            error_message="does not provide an export named 'default'",
            stderr="error: does not provide an export named 'default'",
            exit_code=1
        )

        assert classified.error_type == ErrorType.IMPORT_ERROR


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

    def test_java_incompatible_types(self):
        """Test Java incompatible types classification"""
        classified = ErrorClassifier.classify(
            error_message="incompatible types: String cannot be converted to int",
            stderr="[ERROR] incompatible types: required: int found: String",
            exit_code=1
        )

        assert classified.error_type == ErrorType.TYPE_ERROR

    def test_java_constructor_error(self):
        """Test Java constructor error classification"""
        classified = ErrorClassifier.classify(
            error_message="no suitable constructor found",
            stderr="[ERROR] no suitable constructor found for class Foo",
            exit_code=1
        )

        assert classified.error_type == ErrorType.TYPE_ERROR


class TestConfigErrorClassification:
    """Test configuration error classification"""

    def test_vite_config_error(self):
        """Test vite.config error classification"""
        classified = ErrorClassifier.classify(
            error_message="error in vite.config",
            stderr="error: vite.config.js has invalid option",
            exit_code=1
        )

        assert classified.error_type == ErrorType.CONFIG_ERROR

    def test_spring_bean_error(self):
        """Test Spring bean configuration error"""
        classified = ErrorClassifier.classify(
            error_message="No qualifying bean of type",
            stderr="No qualifying bean of type 'UserService' available",
            exit_code=1
        )

        assert classified.error_type == ErrorType.CONFIG_ERROR


class TestInfrastructureErrors:
    """Test non-Claude-fixable infrastructure errors"""

    def test_port_conflict(self):
        """Test port conflict classification"""
        classified = ErrorClassifier.classify(
            error_message="port already allocated",
            stderr="Error: port 3000 already allocated",
            exit_code=1
        )

        assert classified.error_type == ErrorType.PORT_CONFLICT
        assert classified.is_claude_fixable == False

    def test_network_error(self):
        """Test network error classification"""
        classified = ErrorClassifier.classify(
            error_message="ETIMEDOUT",
            stderr="Error: ETIMEDOUT connecting to registry.npmjs.org",
            exit_code=1
        )

        assert classified.error_type == ErrorType.NETWORK_ERROR
        assert classified.is_claude_fixable == False

    def test_permission_error(self):
        """Test permission error classification"""
        classified = ErrorClassifier.classify(
            error_message="EACCES permission denied",
            stderr="Error: EACCES: permission denied, open '/etc/passwd'",
            exit_code=1
        )

        assert classified.error_type == ErrorType.PERMISSION_ERROR
        assert classified.is_claude_fixable == False

    def test_memory_error(self):
        """Test memory error classification"""
        classified = ErrorClassifier.classify(
            error_message="JavaScript heap out of memory",
            stderr="FATAL ERROR: JavaScript heap out of memory",
            exit_code=1
        )

        assert classified.error_type == ErrorType.MEMORY_ERROR
        assert classified.is_claude_fixable == False

    def test_command_not_found(self):
        """Test command not found classification"""
        classified = ErrorClassifier.classify(
            error_message="sh: pnpm: not found",
            stderr="sh: pnpm: not found",
            exit_code=127
        )

        assert classified.error_type == ErrorType.INFRA_ERROR
        assert classified.is_claude_fixable == False


class TestUnknownErrorClassification:
    """Test unknown error classification"""

    def test_unknown_error_allows_claude(self):
        """Test unknown errors allow Claude attempt"""
        classified = ErrorClassifier.classify(
            error_message="Some random error we don't recognize",
            stderr="",
            exit_code=1
        )

        assert classified.error_type == ErrorType.UNKNOWN
        # Unknown errors allow Claude to attempt fix
        assert classified.is_claude_fixable == True

    def test_empty_error_still_allows_claude(self):
        """Test empty error message still allows Claude"""
        classified = ErrorClassifier.classify(
            error_message="",
            stderr="",
            exit_code=0
        )

        assert classified.error_type == ErrorType.UNKNOWN
        # Even empty is classified as unknown and allows attempt
        assert classified.is_claude_fixable == True


class TestShouldCallClaude:
    """Test should_call_claude decision logic"""

    def test_should_call_for_fixable_error(self):
        """Test Claude should be called for fixable errors"""
        classified = ClassifiedError(
            error_type=ErrorType.SYNTAX_ERROR,
            is_claude_fixable=True,
            confidence=0.9,
            original_message="SyntaxError",
            file_path=None,
            line_number=None,
            suggested_action="Fix syntax error",
            extracted_context={}
        )

        should_call, reason = ErrorClassifier.should_call_claude(classified)
        assert should_call == True

    def test_should_not_call_for_infra_error(self):
        """Test Claude should not be called for infrastructure errors"""
        classified = ClassifiedError(
            error_type=ErrorType.PORT_CONFLICT,
            is_claude_fixable=False,
            confidence=0.95,
            original_message="port already allocated",
            file_path=None,
            line_number=None,
            suggested_action="Kill existing process",
            extracted_context={}
        )

        should_call, reason = ErrorClassifier.should_call_claude(classified)
        assert should_call == False

    def test_should_not_call_for_low_confidence(self):
        """Test Claude should not be called for low confidence"""
        classified = ClassifiedError(
            error_type=ErrorType.UNKNOWN,
            is_claude_fixable=True,
            confidence=0.2,  # Below 0.3 threshold
            original_message="",
            file_path=None,
            line_number=None,
            suggested_action="Investigate",
            extracted_context={}
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

        # Should extract and normalize file path
        assert classified.file_path is not None
        assert "App.java" in classified.file_path

    def test_extract_typescript_file_path(self):
        """Test extracting file path from TypeScript error"""
        classified = ErrorClassifier.classify(
            error_message="error TS2304",
            stderr="src/components/App.tsx(15,3): error TS2304: Cannot find name 'foo'",
            exit_code=1
        )

        assert classified.file_path is not None
        assert "App.tsx" in classified.file_path


class TestPromptTemplates:
    """Test Claude prompt template generation"""

    def test_syntax_error_template(self):
        """Test syntax error prompt template"""
        template = ErrorClassifier.get_claude_prompt_template(ErrorType.SYNTAX_ERROR)
        assert template is not None
        assert len(template) > 0
        assert "SYNTAX_ERROR" in template

    def test_undefined_variable_template(self):
        """Test undefined variable prompt template"""
        template = ErrorClassifier.get_claude_prompt_template(ErrorType.UNDEFINED_VARIABLE)
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
        assert "UNKNOWN" in template
