"""
Claude Agent SDK Integration Module

This module provides SDK-based agents that leverage Anthropic's official
Agent SDK for improved error handling, tool management, and reliability.

Components:
- SDKFixerAgent: Auto-debugging with built-in tools
  - fix_error(): Fix a single error
  - fix_with_retry(): Fix with retry and verification
  - fix_all_errors_smart(): SMART BATCHING - Fix all errors by category (recommended for 100+ errors)
- SDKOrchestrator: Workflow coordinator using SDK patterns
- BuildErrorParser: Parse and categorize compilation errors
- SDK Tools: Bash, TextEditor, FileOps configurations
"""

from .sdk_fixer_agent import SDKFixerAgent, BuildErrorParser, ParsedError, ErrorCategory
from .sdk_tools import SDKToolManager
from .sdk_orchestrator import SDKOrchestrator

__all__ = [
    "SDKFixerAgent",
    "SDKToolManager",
    "SDKOrchestrator",
    "BuildErrorParser",
    "ParsedError",
    "ErrorCategory",
]
