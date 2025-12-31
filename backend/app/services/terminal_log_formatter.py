"""
Terminal Log Formatter - User-Friendly Display

IMPORTANT: This formatter is for DISPLAY ONLY.
Raw logs remain unchanged for fixer parsing.

The formatter adds display metadata without modifying the original message.
"""

import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class LogLevel(str, Enum):
    """Log severity levels"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"
    SYSTEM = "system"


class LogCategory(str, Enum):
    """Log categories for grouping"""
    BUILD = "build"
    INSTALL = "install"
    SERVER = "server"
    TEST = "test"
    LINT = "lint"
    ERROR = "error"
    NETWORK = "network"
    FILE = "file"
    GENERAL = "general"


@dataclass
class FormattedLog:
    """
    Formatted log entry for display.

    Contains both raw message (for fixers) and display hints (for UI).
    """
    # Original data - NEVER MODIFY
    raw_message: str
    raw_type: str  # stdout, stderr, error, exit

    # Display hints - for UI rendering
    level: LogLevel
    category: LogCategory
    icon: str
    label: str
    color: str  # CSS color hint

    # Extracted info
    file_path: Optional[str] = None
    line_number: Optional[int] = None

    # Metadata
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON response"""
        return {
            # Raw data preserved
            "raw": self.raw_message,
            "type": self.raw_type,
            # Display hints
            "display": {
                "level": self.level.value,
                "category": self.category.value,
                "icon": self.icon,
                "label": self.label,
                "color": self.color,
            },
            # Extracted info
            "file": self.file_path,
            "line": self.line_number,
            "timestamp": self.timestamp,
        }


class TerminalLogFormatter:
    """
    Formats terminal logs for user-friendly display.

    IMPORTANT: Does NOT modify raw logs - only adds display metadata.
    Fixers continue to receive raw unformatted logs.

    Usage:
        formatter = TerminalLogFormatter()

        # Format a single log event
        formatted = formatter.format_event({
            "type": "stdout",
            "data": "npm install completed"
        })

        # Returns FormattedLog with display hints
    """

    # Display configurations
    LEVEL_CONFIG = {
        LogLevel.INFO: {"icon": "ℹ️", "color": "#64B5F6", "label": "INFO"},
        LogLevel.SUCCESS: {"icon": "✓", "color": "#81C784", "label": "SUCCESS"},
        LogLevel.WARNING: {"icon": "⚠", "color": "#FFD54F", "label": "WARN"},
        LogLevel.ERROR: {"icon": "✗", "color": "#E57373", "label": "ERROR"},
        LogLevel.DEBUG: {"icon": "🔍", "color": "#B0BEC5", "label": "DEBUG"},
        LogLevel.SYSTEM: {"icon": "⚙", "color": "#90CAF9", "label": "SYS"},
    }

    CATEGORY_CONFIG = {
        LogCategory.BUILD: {"icon": "🔨", "label": "BUILD"},
        LogCategory.INSTALL: {"icon": "📦", "label": "INSTALL"},
        LogCategory.SERVER: {"icon": "🌐", "label": "SERVER"},
        LogCategory.TEST: {"icon": "🧪", "label": "TEST"},
        LogCategory.LINT: {"icon": "📝", "label": "LINT"},
        LogCategory.ERROR: {"icon": "❌", "label": "ERROR"},
        LogCategory.NETWORK: {"icon": "🔗", "label": "NETWORK"},
        LogCategory.FILE: {"icon": "📄", "label": "FILE"},
        LogCategory.GENERAL: {"icon": "▸", "label": ""},
    }

    # Patterns for detecting log type (compiled for performance)
    SUCCESS_PATTERNS = [
        re.compile(r"compiled successfully", re.I),
        re.compile(r"build completed", re.I),
        re.compile(r"ready in \d+", re.I),
        re.compile(r"server running", re.I),
        re.compile(r"listening on", re.I),
        re.compile(r"started server", re.I),
        re.compile(r"✓|✔|√", re.I),
        re.compile(r"success", re.I),
        re.compile(r"done\.?$", re.I),
        re.compile(r"completed\.?$", re.I),
        re.compile(r"added \d+ packages", re.I),
    ]

    WARNING_PATTERNS = [
        re.compile(r"warn(ing)?[\s:]", re.I),
        re.compile(r"⚠|⚡", re.I),
        re.compile(r"deprecated", re.I),
        re.compile(r"peer dep", re.I),
        re.compile(r"skipping", re.I),
    ]

    ERROR_PATTERNS = [
        re.compile(r"error[\s:\[]", re.I),
        re.compile(r"failed", re.I),
        re.compile(r"cannot find", re.I),
        re.compile(r"not found", re.I),
        re.compile(r"exception", re.I),
        re.compile(r"traceback", re.I),
        re.compile(r"ERR!|ERR_", re.I),
        re.compile(r"ENOENT|EACCES|EADDRINUSE", re.I),
        re.compile(r"✗|✖|×", re.I),
        re.compile(r"SyntaxError|TypeError|ReferenceError", re.I),
    ]

    # Category detection patterns
    BUILD_PATTERNS = [
        re.compile(r"vite|webpack|esbuild|rollup|parcel", re.I),
        re.compile(r"compil(e|ing)", re.I),
        re.compile(r"build(ing)?", re.I),
        re.compile(r"bundl(e|ing)", re.I),
        re.compile(r"transform(ing)?", re.I),
    ]

    INSTALL_PATTERNS = [
        re.compile(r"npm (i|install|ci)", re.I),
        re.compile(r"yarn (add|install)", re.I),
        re.compile(r"pnpm (add|install)", re.I),
        re.compile(r"pip install", re.I),
        re.compile(r"added \d+ packages", re.I),
        re.compile(r"resolving|fetching|linking", re.I),
    ]

    SERVER_PATTERNS = [
        re.compile(r"server|listening|port \d+", re.I),
        re.compile(r"localhost:\d+|127\.0\.0\.1:\d+", re.I),
        re.compile(r"http://|https://", re.I),
        re.compile(r"running (on|at)", re.I),
    ]

    TEST_PATTERNS = [
        re.compile(r"test(s|ing)?", re.I),
        re.compile(r"jest|vitest|mocha|pytest", re.I),
        re.compile(r"passed|failed \d+", re.I),
    ]

    LINT_PATTERNS = [
        re.compile(r"eslint|prettier|tslint", re.I),
        re.compile(r"lint(ing)?", re.I),
    ]

    # File/line extraction patterns
    FILE_LINE_PATTERNS = [
        re.compile(r'([a-zA-Z0-9_\-./\\]+\.(tsx?|jsx?|py|java|go|rs|vue|svelte)):(\d+)'),
        re.compile(r'File "([^"]+)", line (\d+)'),
        re.compile(r'at\s+([^\s]+):(\d+):(\d+)'),
    ]

    def __init__(self):
        pass

    def format_event(self, event: Dict[str, Any]) -> FormattedLog:
        """
        Format a single terminal event for display.

        Args:
            event: Raw event dict with 'type' and 'data' keys

        Returns:
            FormattedLog with display hints
        """
        raw_type = event.get("type", "stdout")
        raw_message = str(event.get("data", ""))

        # Detect level
        level = self._detect_level(raw_type, raw_message)

        # Detect category
        category = self._detect_category(raw_message)

        # Get display config
        level_config = self.LEVEL_CONFIG.get(level, self.LEVEL_CONFIG[LogLevel.INFO])
        category_config = self.CATEGORY_CONFIG.get(category, self.CATEGORY_CONFIG[LogCategory.GENERAL])

        # Use category icon if not error/warning
        icon = level_config["icon"] if level in [LogLevel.ERROR, LogLevel.WARNING] else category_config["icon"]

        # Extract file/line info
        file_path, line_number = self._extract_file_line(raw_message)

        # Build label
        label = self._build_label(level, category, level_config, category_config)

        return FormattedLog(
            raw_message=raw_message,
            raw_type=raw_type,
            level=level,
            category=category,
            icon=icon,
            label=label,
            color=level_config["color"],
            file_path=file_path,
            line_number=line_number,
            timestamp=datetime.utcnow().strftime("%H:%M:%S"),
        )

    def _detect_level(self, raw_type: str, message: str) -> LogLevel:
        """Detect log level from type and message"""
        # stderr is usually error/warning
        if raw_type == "stderr":
            # Check if it's actually an error
            for pattern in self.ERROR_PATTERNS:
                if pattern.search(message):
                    return LogLevel.ERROR
            # Default stderr to warning (many tools output to stderr)
            return LogLevel.WARNING

        if raw_type == "error":
            return LogLevel.ERROR

        # Check patterns in stdout
        for pattern in self.ERROR_PATTERNS:
            if pattern.search(message):
                return LogLevel.ERROR

        for pattern in self.WARNING_PATTERNS:
            if pattern.search(message):
                return LogLevel.WARNING

        for pattern in self.SUCCESS_PATTERNS:
            if pattern.search(message):
                return LogLevel.SUCCESS

        return LogLevel.INFO

    def _detect_category(self, message: str) -> LogCategory:
        """Detect log category from message"""
        # Check each category
        for pattern in self.INSTALL_PATTERNS:
            if pattern.search(message):
                return LogCategory.INSTALL

        for pattern in self.BUILD_PATTERNS:
            if pattern.search(message):
                return LogCategory.BUILD

        for pattern in self.SERVER_PATTERNS:
            if pattern.search(message):
                return LogCategory.SERVER

        for pattern in self.TEST_PATTERNS:
            if pattern.search(message):
                return LogCategory.TEST

        for pattern in self.LINT_PATTERNS:
            if pattern.search(message):
                return LogCategory.LINT

        return LogCategory.GENERAL

    def _extract_file_line(self, message: str) -> tuple:
        """Extract file path and line number from message"""
        for pattern in self.FILE_LINE_PATTERNS:
            match = pattern.search(message)
            if match:
                groups = match.groups()
                file_path = groups[0]
                try:
                    line_number = int(groups[1]) if len(groups) > 1 else None
                except (ValueError, TypeError):
                    line_number = None
                return file_path, line_number

        return None, None

    def _build_label(
        self,
        level: LogLevel,
        category: LogCategory,
        level_config: dict,
        category_config: dict
    ) -> str:
        """Build display label"""
        parts = []

        # Add category label if meaningful
        if category != LogCategory.GENERAL and category_config["label"]:
            parts.append(category_config["label"])

        # Add level for errors/warnings
        if level in [LogLevel.ERROR, LogLevel.WARNING]:
            parts.append(level_config["label"])

        return " ".join(parts) if parts else ""

    def format_exit_event(self, exit_code: int, success: bool) -> FormattedLog:
        """Format exit event with clear status"""
        if success:
            message = f"Command completed successfully (exit code: {exit_code})"
            level = LogLevel.SUCCESS
            icon = "✓"
            color = "#81C784"
        else:
            message = f"Command failed (exit code: {exit_code})"
            level = LogLevel.ERROR
            icon = "✗"
            color = "#E57373"

        return FormattedLog(
            raw_message=message,
            raw_type="exit",
            level=level,
            category=LogCategory.GENERAL,
            icon=icon,
            label="EXIT",
            color=color,
            timestamp=datetime.utcnow().strftime("%H:%M:%S"),
        )

    def format_system_message(self, message: str, level: LogLevel = LogLevel.SYSTEM) -> FormattedLog:
        """Format system/status messages"""
        level_config = self.LEVEL_CONFIG.get(level, self.LEVEL_CONFIG[LogLevel.SYSTEM])

        return FormattedLog(
            raw_message=message,
            raw_type="system",
            level=level,
            category=LogCategory.GENERAL,
            icon=level_config["icon"],
            label="SYSTEM",
            color=level_config["color"],
            timestamp=datetime.utcnow().strftime("%H:%M:%S"),
        )


# Singleton instance
terminal_formatter = TerminalLogFormatter()


def format_terminal_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to format a terminal event.

    Returns dict with both raw data and display hints.

    Usage in streaming endpoint:
        for event in manager.execute_command(...):
            formatted = format_terminal_event(event)
            yield f"data: {json.dumps(formatted)}\n\n"
    """
    if event.get("type") == "exit":
        formatted = terminal_formatter.format_exit_event(
            exit_code=event.get("data", 0),
            success=event.get("success", False)
        )
    else:
        formatted = terminal_formatter.format_event(event)

    return formatted.to_dict()
