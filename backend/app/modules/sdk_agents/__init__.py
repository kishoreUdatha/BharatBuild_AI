"""
Claude Agent SDK Integration Module

This module provides SDK-based agents that leverage Anthropic's official
Agent SDK for improved error handling, tool management, and reliability.

Components:
- SDKFixerAgent: Auto-debugging with built-in tools
- SDKOrchestrator: Workflow coordinator using SDK patterns
- SDK Tools: Bash, TextEditor, FileOps configurations
"""

from .sdk_fixer_agent import SDKFixerAgent
from .sdk_tools import SDKToolManager
from .sdk_orchestrator import SDKOrchestrator

__all__ = [
    "SDKFixerAgent",
    "SDKToolManager",
    "SDKOrchestrator"
]
