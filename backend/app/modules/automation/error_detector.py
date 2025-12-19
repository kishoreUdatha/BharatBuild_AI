"""
Error Detector and Auto-Fix System
Parses build/runtime errors and attempts automatic fixes
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass

from app.core.logging_config import logger
from app.utils.claude_client import claude_client


@dataclass
class ErrorPattern:
    """Pattern for matching errors"""
    pattern: str
    error_type: str
    severity: str  # 'critical', 'warning', 'info'
    auto_fixable: bool


class ErrorDetector:
    """Detects and analyzes errors from build/runtime output"""

    # Comprehensive error patterns (~200 like Bolt.new)
    ERROR_PATTERNS = [
        # ============= NODE/JAVASCRIPT ERRORS =============
        ErrorPattern(r"Module not found: Error: Can't resolve '(.+?)'", "missing_module", "critical", True),
        ErrorPattern(r"Cannot find module '(.+?)'", "missing_module", "critical", True),
        ErrorPattern(r"Module '(.+?)' has no exported member '(.+?)'", "missing_export", "critical", True),
        ErrorPattern(r"SyntaxError: (.+)", "syntax_error", "critical", True),
        ErrorPattern(r"ReferenceError: (.+?) is not defined", "undefined_reference", "critical", True),
        ErrorPattern(r"TypeError: (.+)", "type_error", "critical", True),
        ErrorPattern(r"RangeError: (.+)", "range_error", "critical", True),
        ErrorPattern(r"URIError: (.+)", "uri_error", "critical", True),
        ErrorPattern(r"EvalError: (.+)", "eval_error", "critical", True),
        ErrorPattern(r"Unexpected token (.+)", "syntax_error", "critical", True),
        ErrorPattern(r"Uncaught Error: (.+)", "uncaught_error", "critical", True),
        ErrorPattern(r"Unhandled Promise Rejection", "promise_rejection", "critical", True),

        # ============= TYPESCRIPT ERRORS =============
        ErrorPattern(r"Property '(.+?)' does not exist on type '(.+?)'", "ts_property_error", "critical", True),
        ErrorPattern(r"Type '(.+?)' is not assignable to type '(.+?)'", "ts_type_mismatch", "critical", True),
        ErrorPattern(r"Argument of type '(.+?)' is not assignable", "ts_argument_error", "critical", True),
        ErrorPattern(r"Cannot find name '(.+?)'", "ts_undefined", "critical", True),
        ErrorPattern(r"Object is possibly 'undefined'", "ts_null_check", "critical", True),
        ErrorPattern(r"Object is possibly 'null'", "ts_null_check", "critical", True),
        ErrorPattern(r"TS\d+: (.+)", "typescript_error", "critical", True),
        ErrorPattern(r"error TS(\d+):", "typescript_error", "critical", True),
        ErrorPattern(r"Parameter '(.+?)' implicitly has an 'any' type", "ts_implicit_any", "warning", True),
        ErrorPattern(r"'(.+?)' is declared but its value is never read", "ts_unused", "warning", True),
        ErrorPattern(r"File '(.+?)' not found", "ts_file_not_found", "critical", True),

        # ============= REACT ERRORS =============
        ErrorPattern(r"Invalid hook call", "react_hook_error", "critical", True),
        ErrorPattern(r"React Hook \"(.+?)\" is called conditionally", "react_hook_error", "critical", True),
        ErrorPattern(r"Cannot update a component .+ while rendering", "react_render_error", "critical", True),
        ErrorPattern(r"Maximum update depth exceeded", "react_infinite_loop", "critical", True),
        ErrorPattern(r"Each child in a list should have a unique \"key\" prop", "react_key_error", "warning", True),
        ErrorPattern(r"Failed prop type", "react_prop_error", "warning", True),
        ErrorPattern(r"React.createElement: type is invalid", "react_component_error", "critical", True),
        ErrorPattern(r"Element type is invalid", "react_element_error", "critical", True),
        ErrorPattern(r"Minified React error #(\d+)", "react_minified_error", "critical", True),

        # ============= VITE/WEBPACK ERRORS =============
        ErrorPattern(r"\[vite\] (.+?) error", "vite_error", "critical", True),
        ErrorPattern(r"failed to load config from (.+)", "vite_config_error", "critical", True),
        ErrorPattern(r"\[plugin:(.+?)\] (.+)", "vite_plugin_error", "critical", True),
        ErrorPattern(r"Pre-transform error: (.+)", "vite_transform_error", "critical", True),
        ErrorPattern(r"Internal server error: (.+)", "vite_server_error", "critical", True),
        ErrorPattern(r"\[HMR\] (.+)", "hmr_error", "critical", True),
        ErrorPattern(r"webpack compiled with (\d+) error", "webpack_error", "critical", True),
        ErrorPattern(r"ModuleBuildError: (.+)", "webpack_build_error", "critical", True),
        ErrorPattern(r"Module parse failed: (.+)", "webpack_parse_error", "critical", True),

        # ============= NPM/YARN/PNPM ERRORS =============
        ErrorPattern(r"npm ERR! (.+)", "npm_error", "critical", True),
        ErrorPattern(r"npm WARN (.+)", "npm_warning", "warning", False),
        ErrorPattern(r"ERESOLVE unable to resolve dependency tree", "npm_dependency_error", "critical", True),
        ErrorPattern(r"peer dep missing: (.+)", "npm_peer_dep", "warning", True),
        ErrorPattern(r"yarn error (.+)", "yarn_error", "critical", True),
        ErrorPattern(r"error Command failed with exit code (\d+)", "yarn_command_error", "critical", True),
        ErrorPattern(r"pnpm ERR! (.+)", "pnpm_error", "critical", True),
        ErrorPattern(r"ERR_PNPM_(.+)", "pnpm_error", "critical", True),

        # ============= PORT/NETWORK ERRORS =============
        ErrorPattern(r"Port (\d+) is already in use", "port_in_use", "critical", True),
        ErrorPattern(r"EADDRINUSE.*:(\d+)", "port_in_use", "critical", True),
        ErrorPattern(r"address already in use", "port_in_use", "critical", True),
        ErrorPattern(r"ECONNREFUSED", "connection_refused", "critical", True),
        ErrorPattern(r"ETIMEDOUT", "connection_timeout", "critical", True),
        ErrorPattern(r"ENOTFOUND", "host_not_found", "critical", True),
        ErrorPattern(r"getaddrinfo ENOTFOUND", "dns_error", "critical", True),
        ErrorPattern(r"socket hang up", "socket_error", "critical", True),

        # ============= FILE SYSTEM ERRORS =============
        ErrorPattern(r"ENOENT: no such file or directory", "file_not_found", "critical", True),
        ErrorPattern(r"EACCES: permission denied", "permission_denied", "critical", True),
        ErrorPattern(r"EPERM: operation not permitted", "operation_denied", "critical", True),
        ErrorPattern(r"EEXIST: file already exists", "file_exists", "warning", True),
        ErrorPattern(r"EISDIR: illegal operation on a directory", "directory_error", "critical", True),
        ErrorPattern(r"ENOTDIR: not a directory", "not_directory", "critical", True),
        ErrorPattern(r"EMFILE: too many open files", "too_many_files", "critical", True),

        # ============= PYTHON ERRORS =============
        ErrorPattern(r"ModuleNotFoundError: No module named '(.+?)'", "missing_python_module", "critical", True),
        ErrorPattern(r"ImportError: cannot import name '(.+?)' from '(.+?)'", "python_import_error", "critical", True),
        ErrorPattern(r"ImportError: (.+)", "python_import_error", "critical", True),
        ErrorPattern(r"NameError: name '(.+?)' is not defined", "python_name_error", "critical", True),
        ErrorPattern(r"AttributeError: '(.+?)' object has no attribute '(.+?)'", "python_attr_error", "critical", True),
        ErrorPattern(r"KeyError: (.+)", "python_key_error", "critical", True),
        ErrorPattern(r"IndexError: (.+)", "python_index_error", "critical", True),
        ErrorPattern(r"ValueError: (.+)", "python_value_error", "critical", True),
        ErrorPattern(r"IndentationError: (.+)", "python_indent_error", "critical", True),
        ErrorPattern(r"TabError: (.+)", "python_tab_error", "critical", True),
        ErrorPattern(r"Traceback \(most recent call last\)", "python_traceback", "critical", True),
        ErrorPattern(r"SyntaxError: invalid syntax", "python_syntax_error", "critical", True),
        ErrorPattern(r"ZeroDivisionError: (.+)", "python_zero_div", "critical", True),
        ErrorPattern(r"RecursionError: (.+)", "python_recursion", "critical", True),
        ErrorPattern(r"FileNotFoundError: (.+)", "python_file_not_found", "critical", True),

        # ============= JAVA ERRORS =============
        ErrorPattern(r"package (.+?) does not exist", "missing_java_package", "critical", True),
        ErrorPattern(r"cannot find symbol", "java_symbol_error", "critical", True),
        ErrorPattern(r"NullPointerException", "java_npe", "critical", True),
        ErrorPattern(r"ClassNotFoundException: (.+)", "java_class_not_found", "critical", True),
        ErrorPattern(r"NoSuchMethodError: (.+)", "java_method_error", "critical", True),
        ErrorPattern(r"java\.lang\.(.+?)Exception", "java_exception", "critical", True),
        ErrorPattern(r"BUILD FAILURE", "maven_build_failure", "critical", True),
        ErrorPattern(r"Could not resolve dependencies", "maven_dependency_error", "critical", True),

        # ============= GO ERRORS =============
        ErrorPattern(r"cannot find package \"(.+?)\"", "go_package_error", "critical", True),
        ErrorPattern(r"undefined: (.+)", "go_undefined", "critical", True),
        ErrorPattern(r"imported and not used: \"(.+?)\"", "go_unused_import", "warning", True),
        ErrorPattern(r"declared but not used", "go_unused_var", "warning", True),
        ErrorPattern(r"go: (.+?) requires go (\d+\.\d+)", "go_version_error", "critical", True),
        ErrorPattern(r"go mod tidy: (.+)", "go_mod_error", "critical", True),

        # ============= RUST ERRORS =============
        ErrorPattern(r"error\[E(\d+)\]: (.+)", "rust_error", "critical", True),
        ErrorPattern(r"cannot find (.+?) in this scope", "rust_scope_error", "critical", True),
        ErrorPattern(r"mismatched types", "rust_type_error", "critical", True),
        ErrorPattern(r"borrow of moved value", "rust_borrow_error", "critical", True),
        ErrorPattern(r"cargo build failed", "cargo_build_error", "critical", True),

        # ============= DOCKER ERRORS =============
        ErrorPattern(r"docker: Error response from daemon: (.+)", "docker_daemon_error", "critical", True),
        ErrorPattern(r"Cannot connect to the Docker daemon", "docker_connection_error", "critical", True),
        ErrorPattern(r"no matching manifest for", "docker_manifest_error", "critical", True),
        ErrorPattern(r"error during connect:", "docker_connect_error", "critical", True),
        ErrorPattern(r"OCI runtime create failed", "docker_oci_error", "critical", True),
        ErrorPattern(r"Exited with code (\d+)", "container_exit_error", "critical", True),
        ErrorPattern(r"container (.+?) is unhealthy", "container_health_error", "critical", True),

        # ============= DATABASE ERRORS =============
        ErrorPattern(r"SQLITE_ERROR: (.+)", "sqlite_error", "critical", True),
        ErrorPattern(r"ER_(.+?):", "mysql_error", "critical", True),
        ErrorPattern(r"FATAL: (.+)", "postgres_error", "critical", True),
        ErrorPattern(r"MongoError: (.+)", "mongo_error", "critical", True),
        ErrorPattern(r"Connection refused", "db_connection_error", "critical", True),
        ErrorPattern(r"prisma (.+?) error", "prisma_error", "critical", True),

        # ============= NEXT.JS ERRORS =============
        ErrorPattern(r"Error: Failed to collect page data", "nextjs_build_error", "critical", True),
        ErrorPattern(r"Error occurred prerendering page", "nextjs_prerender_error", "critical", True),
        ErrorPattern(r"getServerSideProps(.+)Error", "nextjs_gsp_error", "critical", True),
        ErrorPattern(r"getStaticProps(.+)Error", "nextjs_gssp_error", "critical", True),

        # ============= GENERIC ERRORS =============
        ErrorPattern(r"fatal error: (.+)", "fatal_error", "critical", True),
        ErrorPattern(r"Error: (.+)", "generic_error", "critical", True),
        ErrorPattern(r"error: (.+)", "generic_error", "critical", True),
        ErrorPattern(r"failed to compile", "compile_error", "critical", True),
        ErrorPattern(r"Build failed", "build_error", "critical", True),
        ErrorPattern(r"FATAL ERROR: (.+)", "fatal_error", "critical", True),
        ErrorPattern(r"Segmentation fault", "segfault", "critical", True),
        ErrorPattern(r"Out of memory", "oom_error", "critical", True),
        ErrorPattern(r"Stack overflow", "stack_overflow", "critical", True),

        # ============= AI/ML ERRORS (TensorFlow, PyTorch, etc.) =============
        ErrorPattern(r"CUDA out of memory", "cuda_oom", "critical", True),
        ErrorPattern(r"RuntimeError: CUDA error", "cuda_error", "critical", True),
        ErrorPattern(r"Could not load dynamic library 'libcudart'", "cuda_library_error", "critical", True),
        ErrorPattern(r"No GPU found", "no_gpu", "warning", True),
        ErrorPattern(r"tensorflow\.python\.framework\.errors_impl\.(.+?)Error", "tensorflow_error", "critical", True),
        ErrorPattern(r"ModuleNotFoundError: No module named 'tensorflow'", "missing_tensorflow", "critical", True),
        ErrorPattern(r"ModuleNotFoundError: No module named 'torch'", "missing_pytorch", "critical", True),
        ErrorPattern(r"ModuleNotFoundError: No module named 'keras'", "missing_keras", "critical", True),
        ErrorPattern(r"RuntimeError: Expected (.+?) but got (.+?)", "tensor_shape_error", "critical", True),
        ErrorPattern(r"ValueError: shapes (.+?) and (.+?) not aligned", "shape_mismatch", "critical", True),
        ErrorPattern(r"RuntimeError: mat1 and mat2 shapes cannot be multiplied", "matrix_error", "critical", True),
        ErrorPattern(r"OOM when allocating tensor", "oom_tensor", "critical", True),
        ErrorPattern(r"ResourceExhaustedError", "resource_exhausted", "critical", True),
        ErrorPattern(r"InvalidArgumentError", "invalid_argument", "critical", True),
        ErrorPattern(r"ModuleNotFoundError: No module named 'sklearn'", "missing_sklearn", "critical", True),
        ErrorPattern(r"ModuleNotFoundError: No module named 'numpy'", "missing_numpy", "critical", True),
        ErrorPattern(r"ModuleNotFoundError: No module named 'pandas'", "missing_pandas", "critical", True),
        ErrorPattern(r"ConvergenceWarning", "ml_convergence_warning", "warning", False),
        ErrorPattern(r"UserWarning: (.+?) is deprecated", "ml_deprecation", "warning", False),

        # ============= BLOCKCHAIN/WEB3 ERRORS (Solidity, Ethereum, etc.) =============
        ErrorPattern(r"Error: VM Exception while processing transaction", "solidity_vm_error", "critical", True),
        ErrorPattern(r"revert (.+)", "solidity_revert", "critical", True),
        ErrorPattern(r"out of gas", "solidity_out_of_gas", "critical", True),
        ErrorPattern(r"CompilerError: (.+)", "solidity_compiler_error", "critical", True),
        ErrorPattern(r"ParserError: (.+)", "solidity_parser_error", "critical", True),
        ErrorPattern(r"TypeError: (.+?) is not implicitly convertible", "solidity_type_error", "critical", True),
        ErrorPattern(r"DeclarationError: (.+)", "solidity_declaration_error", "critical", True),
        ErrorPattern(r"Error: insufficient funds", "web3_insufficient_funds", "critical", True),
        ErrorPattern(r"Error: nonce too low", "web3_nonce_error", "critical", True),
        ErrorPattern(r"Error: replacement transaction underpriced", "web3_gas_error", "critical", True),
        ErrorPattern(r"Error: execution reverted", "web3_revert", "critical", True),
        ErrorPattern(r"MetaMask - RPC Error", "metamask_rpc_error", "critical", True),
        ErrorPattern(r"ethers\.js error", "ethers_error", "critical", True),
        ErrorPattern(r"web3\.exceptions\.(.+)", "web3_exception", "critical", True),
        ErrorPattern(r"hardhat error", "hardhat_error", "critical", True),
        ErrorPattern(r"truffle error", "truffle_error", "critical", True),
        ErrorPattern(r"ganache error", "ganache_error", "critical", True),
        ErrorPattern(r"Contract deployment failed", "contract_deploy_error", "critical", True),
        ErrorPattern(r"UNPREDICTABLE_GAS_LIMIT", "gas_limit_error", "critical", True),

        # ============= ANDROID ERRORS (Kotlin, Java, Gradle) =============
        ErrorPattern(r"Android resource linking failed", "android_resource_error", "critical", True),
        ErrorPattern(r"AAPT: error: (.+)", "android_aapt_error", "critical", True),
        ErrorPattern(r"Execution failed for task ':app:(.+?)'", "android_gradle_task_error", "critical", True),
        ErrorPattern(r"Could not resolve (.+?) for configuration", "android_dependency_error", "critical", True),
        ErrorPattern(r"Manifest merger failed", "android_manifest_error", "critical", True),
        ErrorPattern(r"No signature of method: (.+)", "gradle_method_error", "critical", True),
        ErrorPattern(r"Could not find com\.android\.tools\.build:gradle", "android_plugin_error", "critical", True),
        ErrorPattern(r"SDK location not found", "android_sdk_error", "critical", True),
        ErrorPattern(r"NDK not configured", "android_ndk_error", "critical", True),
        ErrorPattern(r"minSdkVersion (.+?) cannot be smaller", "android_min_sdk_error", "critical", True),
        ErrorPattern(r"Duplicate class (.+?) found", "android_duplicate_class", "critical", True),
        ErrorPattern(r"Could not initialize class (.+)", "android_init_error", "critical", True),
        ErrorPattern(r"Kotlin: (.+)", "kotlin_error", "critical", True),
        ErrorPattern(r"e: (.+?)\.kt: (.+)", "kotlin_compile_error", "critical", True),
        ErrorPattern(r"Unresolved reference: (.+)", "kotlin_unresolved_ref", "critical", True),
        ErrorPattern(r"Type mismatch: inferred type is (.+?) but (.+?) was expected", "kotlin_type_mismatch", "critical", True),
        ErrorPattern(r"The Android Gradle plugin supports only Kotlin Gradle plugin", "kotlin_gradle_mismatch", "critical", True),
        ErrorPattern(r"Jetpack Compose compiler (.+?) error", "compose_error", "critical", True),
        ErrorPattern(r"@Composable invocations can only happen", "compose_invocation_error", "critical", True),

        # ============= iOS/SWIFT ERRORS (Xcode, Swift, CocoaPods) =============
        ErrorPattern(r"error: (.+?)\.swift:(\d+):(\d+): (.+)", "swift_compile_error", "critical", True),
        ErrorPattern(r"Cannot find '(.+?)' in scope", "swift_scope_error", "critical", True),
        ErrorPattern(r"Type '(.+?)' has no member '(.+?)'", "swift_member_error", "critical", True),
        ErrorPattern(r"Cannot convert value of type '(.+?)' to expected argument type '(.+?)'", "swift_type_error", "critical", True),
        ErrorPattern(r"Missing required module '(.+?)'", "swift_module_error", "critical", True),
        ErrorPattern(r"No such module '(.+?)'", "swift_no_module", "critical", True),
        ErrorPattern(r"Undefined symbol: (.+)", "swift_undefined_symbol", "critical", True),
        ErrorPattern(r"Linker command failed", "xcode_linker_error", "critical", True),
        ErrorPattern(r"Build failed with (.+?) error", "xcode_build_error", "critical", True),
        ErrorPattern(r"Code signing error", "xcode_signing_error", "critical", True),
        ErrorPattern(r"Provisioning profile (.+?) doesn't", "xcode_provision_error", "critical", True),
        ErrorPattern(r"error: (.+?) requires a provisioning profile", "xcode_profile_error", "critical", True),
        ErrorPattern(r"\[CocoaPods\] Error: (.+)", "cocoapods_error", "critical", True),
        ErrorPattern(r"pod install failed", "cocoapods_install_error", "critical", True),
        ErrorPattern(r"Unable to find a specification for (.+)", "cocoapods_spec_error", "critical", True),
        ErrorPattern(r"error: (.+?) has no member named '(.+?)'", "objc_member_error", "critical", True),
        ErrorPattern(r"Segmentation fault: 11", "swift_segfault", "critical", True),
        ErrorPattern(r"fatal error: 'UIKit/UIKit\.h' file not found", "uikit_error", "critical", True),
        ErrorPattern(r"SwiftUI: (.+?) error", "swiftui_error", "critical", True),
        ErrorPattern(r"Carthage error: (.+)", "carthage_error", "critical", True),
        ErrorPattern(r"SPM error: (.+)", "spm_error", "critical", True),

        # ============= CYBERSECURITY ERRORS =============
        ErrorPattern(r"SSL: CERTIFICATE_VERIFY_FAILED", "ssl_cert_error", "critical", True),
        ErrorPattern(r"SSL: WRONG_VERSION_NUMBER", "ssl_version_error", "critical", True),
        ErrorPattern(r"SSLError: (.+)", "ssl_error", "critical", True),
        ErrorPattern(r"CORS policy: (.+)", "cors_error", "critical", True),
        ErrorPattern(r"Access-Control-Allow-Origin", "cors_header_error", "critical", True),
        ErrorPattern(r"Cross-Origin Request Blocked", "cors_blocked", "critical", True),
        ErrorPattern(r"CSP: (.+)", "csp_error", "critical", True),
        ErrorPattern(r"Content Security Policy", "csp_violation", "critical", True),
        ErrorPattern(r"CSRF token mismatch", "csrf_error", "critical", True),
        ErrorPattern(r"Invalid CSRF token", "csrf_invalid", "critical", True),
        ErrorPattern(r"Authentication failed", "auth_failed", "critical", True),
        ErrorPattern(r"401 Unauthorized", "unauthorized", "critical", True),
        ErrorPattern(r"403 Forbidden", "forbidden", "critical", True),
        ErrorPattern(r"JWT (.+?) error", "jwt_error", "critical", True),
        ErrorPattern(r"Token expired", "token_expired", "critical", True),
        ErrorPattern(r"Invalid token", "invalid_token", "critical", True),
        ErrorPattern(r"Permission denied", "permission_denied", "critical", True),
        ErrorPattern(r"SQL injection detected", "sql_injection", "critical", True),
        ErrorPattern(r"XSS detected", "xss_detected", "critical", True),
        ErrorPattern(r"Potential security vulnerability", "security_vulnerability", "warning", True),
        ErrorPattern(r"npm audit (.+?) vulnerabilities", "npm_audit_vuln", "warning", True),
        ErrorPattern(r"High severity vulnerability", "high_severity_vuln", "critical", True),
        ErrorPattern(r"Critical severity vulnerability", "critical_vuln", "critical", True),
        ErrorPattern(r"OWASP: (.+)", "owasp_warning", "warning", True),
        ErrorPattern(r"Insecure dependency", "insecure_dep", "warning", True),
        ErrorPattern(r"Deprecated cipher", "deprecated_cipher", "warning", True),
        ErrorPattern(r"Weak password", "weak_password", "warning", True),
        ErrorPattern(r"Rate limit exceeded", "rate_limit", "warning", True),
        ErrorPattern(r"Too many requests", "too_many_requests", "warning", True),

        # ============= FLUTTER/DART ERRORS =============
        ErrorPattern(r"Error: (.+?)\.dart:(\d+):(\d+): (.+)", "dart_compile_error", "critical", True),
        ErrorPattern(r"The method '(.+?)' isn't defined", "dart_method_error", "critical", True),
        ErrorPattern(r"The getter '(.+?)' isn't defined", "dart_getter_error", "critical", True),
        ErrorPattern(r"Undefined name '(.+?)'", "dart_undefined", "critical", True),
        ErrorPattern(r"A value of type '(.+?)' can't be assigned", "dart_type_error", "critical", True),
        ErrorPattern(r"Target of URI doesn't exist", "dart_uri_error", "critical", True),
        ErrorPattern(r"flutter: (.+?) error", "flutter_error", "critical", True),
        ErrorPattern(r"PlatformException\((.+?)\)", "flutter_platform_error", "critical", True),
        ErrorPattern(r"MissingPluginException", "flutter_plugin_error", "critical", True),
        ErrorPattern(r"pub get failed", "flutter_pub_error", "critical", True),

        # ============= WARNINGS =============
        ErrorPattern(r"warning: (.+)", "warning", "warning", False),
        ErrorPattern(r"WARN (.+)", "warning", "warning", False),
        ErrorPattern(r"deprecated: (.+)", "deprecation", "warning", False),
    ]

    def detect_errors(self, output: str) -> List[Dict]:
        """
        Detect errors in build/runtime output

        Args:
            output: Build or runtime output text

        Returns:
            List of detected errors with details
        """
        detected_errors = []

        for pattern_obj in self.ERROR_PATTERNS:
            matches = re.finditer(pattern_obj.pattern, output, re.MULTILINE | re.IGNORECASE)

            for match in matches:
                error = {
                    "type": pattern_obj.error_type,
                    "severity": pattern_obj.severity,
                    "auto_fixable": pattern_obj.auto_fixable,
                    "message": match.group(0),
                    "line": self._find_line_number(output, match.start()),
                    "context": self._get_context(output, match.start()),
                }

                # Extract specific details based on error type
                if pattern_obj.error_type == "missing_module":
                    error["module_name"] = match.group(1)
                elif pattern_obj.error_type == "port_in_use":
                    error["port"] = match.group(1)
                elif pattern_obj.error_type == "missing_python_module":
                    error["module_name"] = match.group(1)

                detected_errors.append(error)

        return detected_errors

    def _find_line_number(self, text: str, position: int) -> int:
        """Find line number for a position in text"""
        return text[:position].count('\n') + 1

    def _get_context(self, text: str, position: int, lines_before: int = 2, lines_after: int = 2) -> str:
        """Get context lines around the error"""
        all_lines = text.split('\n')
        line_num = self._find_line_number(text, position)

        start = max(0, line_num - lines_before - 1)
        end = min(len(all_lines), line_num + lines_after)

        return '\n'.join(all_lines[start:end])

    async def suggest_fix(self, error: Dict, project_context: Optional[str] = None) -> Optional[Dict]:
        """
        Suggest a fix for an error

        Args:
            error: Error dictionary from detect_errors
            project_context: Additional project context

        Returns:
            Fix suggestion or None
        """
        if not error.get("auto_fixable"):
            return None

        error_type = error.get("type")

        # Auto-fixable errors
        if error_type == "missing_module":
            return self._fix_missing_module(error)
        elif error_type == "missing_python_module":
            return self._fix_missing_python_module(error)
        elif error_type == "port_in_use":
            return self._fix_port_in_use(error)
        elif error_type == "missing_java_package":
            return self._fix_missing_java_package(error)

        return None

    def _fix_missing_module(self, error: Dict) -> Dict:
        """Fix missing Node module by installing it"""
        module_name = error.get("module_name", "")

        # Clean up module name (remove @ prefixes, paths, etc.)
        # Example: '@react/component' -> '@react/component'
        # Example: './utils' -> skip (local module)
        if module_name.startswith('.'):
            return None

        # Remove file extensions
        module_name = re.sub(r'\.(js|jsx|ts|tsx|css|scss)$', '', module_name)

        return {
            "type": "install_package",
            "package_manager": "npm",
            "packages": [module_name],
            "description": f"Install missing module: {module_name}",
            "command": f"npm install {module_name}"
        }

    def _fix_missing_python_module(self, error: Dict) -> Dict:
        """Fix missing Python module by installing it"""
        module_name = error.get("module_name", "")

        return {
            "type": "install_package",
            "package_manager": "pip",
            "packages": [module_name],
            "description": f"Install missing Python module: {module_name}",
            "command": f"pip install {module_name}"
        }

    def _fix_missing_java_package(self, error: Dict) -> Dict:
        """Fix missing Java package (suggest Maven dependency)"""
        package_name = error.get("module_name", "")

        return {
            "type": "add_dependency",
            "package_manager": "maven",
            "description": f"Add Maven dependency for package: {package_name}",
            "manual": True,  # Requires manual POM edit
            "suggestion": f"Add the appropriate dependency for '{package_name}' to pom.xml"
        }

    def _fix_port_in_use(self, error: Dict) -> Dict:
        """Fix port in use error"""
        port = error.get("port", "3000")

        return {
            "type": "kill_port",
            "port": port,
            "description": f"Kill process using port {port}",
            "command": f"lsof -ti:{port} | xargs kill -9"  # Unix/Mac
        }

    async def auto_fix_with_claude(self, error: Dict, code_context: str) -> Optional[Dict]:
        """
        Use Claude to suggest a fix for complex errors

        Args:
            error: Error dictionary
            code_context: The code where the error occurred

        Returns:
            Fix suggestion from Claude
        """
        try:
            prompt = f"""You are a code debugging expert. Analyze this error and suggest a fix.

ERROR:
Type: {error.get('type')}
Message: {error.get('message')}

CODE CONTEXT:
{error.get('context', 'No context available')}

FULL CODE:
{code_context[:1000]}  # Limit context size

Provide a concise fix suggestion in this format:
1. What's wrong
2. How to fix it
3. Code snippet (if applicable)
"""

            response = await claude_client.generate(
                prompt=prompt,
                model="haiku",  # Use faster model for quick fixes
                max_tokens=500
            )

            return {
                "type": "claude_suggestion",
                "suggestion": response.get("content", ""),
                "description": f"Claude's suggestion for {error.get('type')}"
            }

        except Exception as e:
            logger.error(f"Error getting Claude fix suggestion: {e}")
            return None


class ErrorRecoverySystem:
    """Attempts to automatically recover from errors"""

    def __init__(self):
        self.detector = ErrorDetector()
        self.fix_history = []

    async def analyze_and_fix(
        self,
        output: str,
        project_id: str,
        max_auto_fixes: int = 3
    ) -> Dict:
        """
        Analyze errors and attempt automatic fixes

        Args:
            output: Build/runtime output with errors
            project_id: Project ID
            max_auto_fixes: Maximum number of automatic fix attempts

        Returns:
            Dict with detected errors and suggested fixes
        """
        # Detect errors
        errors = self.detector.detect_errors(output)

        if not errors:
            return {
                "success": True,
                "errors_found": 0,
                "message": "No errors detected"
            }

        # Categorize errors
        critical_errors = [e for e in errors if e['severity'] == 'critical']
        auto_fixable = [e for e in errors if e['auto_fixable']]

        # Generate fix suggestions
        fixes = []
        for error in auto_fixable[:max_auto_fixes]:
            fix = await self.detector.suggest_fix(error)
            if fix:
                fixes.append(fix)

        return {
            "success": False,
            "errors_found": len(errors),
            "critical_errors": len(critical_errors),
            "auto_fixable": len(auto_fixable),
            "errors": errors,
            "suggested_fixes": fixes,
            "can_auto_fix": len(fixes) > 0
        }


# Singleton instances
error_detector = ErrorDetector()
error_recovery = ErrorRecoverySystem()
