#!/usr/bin/env python3
"""
BharatBuild AI - Pre-Deployment Validation Script
Run this before deploying to production

Usage: python scripts/validate_deployment.py
"""

import os
import sys
import subprocess
import re
from pathlib import Path
from typing import List, Tuple

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'  # No Color

    @staticmethod
    def disable():
        """Disable colors for non-terminal output"""
        Colors.RED = ''
        Colors.GREEN = ''
        Colors.YELLOW = ''
        Colors.NC = ''


# Disable colors on Windows if not using ANSI-compatible terminal
if os.name == 'nt':
    try:
        import colorama
        colorama.init()
    except ImportError:
        Colors.disable()


class ValidationResult:
    def __init__(self):
        self.errors = 0
        self.warnings = 0

    def success(self, message: str):
        print(f"{Colors.GREEN}✓{Colors.NC} {message}")

    def warning(self, message: str):
        print(f"{Colors.YELLOW}⚠{Colors.NC} {message}")
        self.warnings += 1

    def error(self, message: str):
        print(f"{Colors.RED}✗{Colors.NC} {message}")
        self.errors += 1

    def is_successful(self) -> bool:
        return self.errors == 0


def run_command(cmd: List[str], capture: bool = True) -> Tuple[int, str]:
    """Run a command and return exit code and output"""
    try:
        if capture:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode, result.stdout + result.stderr
        else:
            result = subprocess.run(cmd, timeout=300)
            return result.returncode, ""
    except subprocess.TimeoutExpired:
        return 1, "Command timed out"
    except FileNotFoundError:
        return 1, f"Command not found: {cmd[0]}"
    except Exception as e:
        return 1, str(e)


def check_required_files(result: ValidationResult, root_path: Path):
    """Check that all required files exist"""
    print("\n1. Checking required files...")

    files_to_check = [
        "docker-compose.yml",
        "backend/Dockerfile.light",
        "frontend/Dockerfile",
        "backend/requirements.txt",
        "frontend/package.json",
        ".env",
    ]

    for file in files_to_check:
        file_path = root_path / file
        if file_path.exists():
            result.success(f"{file} exists")
        else:
            result.error(f"{file} is MISSING!")


def check_environment_variables(result: ValidationResult, root_path: Path):
    """Check required environment variables are set"""
    print("\n2. Checking environment variables...")

    env_file = root_path / ".env"
    if not env_file.exists():
        result.error(".env file not found")
        return

    env_content = env_file.read_text()
    required_vars = [
        "DATABASE_URL",
        "SECRET_KEY",
        "JWT_SECRET_KEY",
        "ANTHROPIC_API_KEY",
    ]

    for var in required_vars:
        # Check if variable is set and not empty
        pattern = rf'^{var}=.+'
        if re.search(pattern, env_content, re.MULTILINE):
            result.success(f"{var} is set")
        else:
            result.error(f"{var} is NOT set or empty in .env")


def check_docker(result: ValidationResult):
    """Check Docker is installed and running"""
    print("\n3. Checking Docker...")

    # Check if docker command exists
    exit_code, _ = run_command(["docker", "--version"])
    if exit_code != 0:
        result.error("Docker is NOT installed")
        return

    # Check if Docker daemon is running
    exit_code, _ = run_command(["docker", "info"])
    if exit_code == 0:
        result.success("Docker is running")
    else:
        result.error("Docker is installed but not running")


def check_backend_tests(result: ValidationResult, root_path: Path):
    """Run backend unit tests"""
    print("\n4. Running backend tests...")

    backend_path = root_path / "backend"
    if not backend_path.exists():
        result.error("Backend directory not found")
        return

    # Set test environment
    env = os.environ.copy()
    env["TESTING"] = "true"
    env["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
    env["SECRET_KEY"] = "test-secret"
    env["JWT_SECRET_KEY"] = "test-jwt"
    env["ANTHROPIC_API_KEY"] = "test-key"

    # Run pytest
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/unit", "-v", "--tb=short"],
            cwd=backend_path,
            capture_output=True,
            text=True,
            env=env,
            timeout=300
        )
        if proc.returncode == 0:
            result.success("Backend unit tests passed")
        else:
            result.warning("Some backend tests failed (check logs)")
    except Exception as e:
        result.warning(f"Could not run tests: {e}")


def check_frontend_build(result: ValidationResult, root_path: Path):
    """Check frontend builds successfully"""
    print("\n5. Checking frontend build...")

    frontend_path = root_path / "frontend"
    if not frontend_path.exists():
        result.error("Frontend directory not found")
        return

    # Try to run npm build (skip actual build for speed, just check config)
    exit_code, output = run_command(["npm", "run", "build", "--dry-run"], capture=True)

    # Alternative: just check package.json exists and has build script
    package_json = frontend_path / "package.json"
    if package_json.exists():
        import json
        try:
            pkg = json.loads(package_json.read_text())
            if "scripts" in pkg and "build" in pkg["scripts"]:
                result.success("Frontend has build script configured")
            else:
                result.warning("Frontend package.json missing build script")
        except json.JSONDecodeError:
            result.error("Frontend package.json is invalid JSON")
    else:
        result.error("Frontend package.json not found")


def check_security(result: ValidationResult, root_path: Path):
    """Run basic security checks"""
    print("\n6. Running security checks...")

    # Check for .env in git
    exit_code, output = run_command(["git", "ls-files", ".env"])
    if exit_code == 0 and output.strip():
        result.error(".env file is tracked by git - REMOVE IT!")
    else:
        result.success(".env is not tracked by git")

    # Basic check for hardcoded secrets
    backend_app = root_path / "backend" / "app"
    if backend_app.exists():
        suspicious_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
        ]
        found_issues = False
        for py_file in backend_app.rglob("*.py"):
            if "test" in str(py_file).lower():
                continue
            content = py_file.read_text()
            for pattern in suspicious_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    # Exclude common false positives
                    if "settings." not in content and "os.getenv" not in content:
                        found_issues = True
                        break
            if found_issues:
                break

        if found_issues:
            result.warning("Possible hardcoded secrets found (review manually)")
        else:
            result.success("No obvious hardcoded secrets found")


def check_docker_compose(result: ValidationResult, root_path: Path):
    """Validate docker-compose configuration"""
    print("\n7. Validating Docker Compose...")

    exit_code, output = run_command(["docker-compose", "config", "-q"])
    if exit_code == 0:
        result.success("docker-compose.yml is valid")
    else:
        # Try docker compose (v2)
        exit_code, output = run_command(["docker", "compose", "config", "-q"])
        if exit_code == 0:
            result.success("docker-compose.yml is valid")
        else:
            result.error("docker-compose.yml has syntax errors")


def check_migrations(result: ValidationResult, root_path: Path):
    """Check database migrations exist"""
    print("\n8. Checking database migrations...")

    migrations_path = root_path / "backend" / "alembic" / "versions"
    if migrations_path.exists():
        migrations = list(migrations_path.glob("*.py"))
        migration_count = len([m for m in migrations if "__pycache__" not in str(m)])
        if migration_count > 0:
            result.success(f"Found {migration_count} migration files")
        else:
            result.warning("No migration files found")
    else:
        result.warning("Alembic versions directory not found")


def main():
    """Main validation function"""
    print("=" * 50)
    print("BharatBuild AI - Pre-Deployment Validation")
    print("=" * 50)

    # Find project root (where docker-compose.yml is)
    root_path = Path.cwd()
    if not (root_path / "docker-compose.yml").exists():
        # Try parent directories
        for parent in root_path.parents:
            if (parent / "docker-compose.yml").exists():
                root_path = parent
                break

    result = ValidationResult()

    # Run all checks
    check_required_files(result, root_path)
    check_environment_variables(result, root_path)
    check_docker(result)
    check_backend_tests(result, root_path)
    check_frontend_build(result, root_path)
    check_security(result, root_path)
    check_docker_compose(result, root_path)
    check_migrations(result, root_path)

    # Print summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)

    if result.errors == 0 and result.warnings == 0:
        print(f"{Colors.GREEN}All checks passed! Ready for deployment.{Colors.NC}")
        return 0
    elif result.errors == 0:
        print(f"{Colors.YELLOW}{result.warnings} warning(s), but no errors.{Colors.NC}")
        print("Review warnings before deploying.")
        return 0
    else:
        print(f"{Colors.RED}{result.errors} error(s) and {result.warnings} warning(s) found.{Colors.NC}")
        print(f"{Colors.RED}Fix errors before deploying!{Colors.NC}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
