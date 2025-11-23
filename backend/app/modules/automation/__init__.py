"""
Automation Module - Bolt.new-style Automation Engine
Complete automation system for code generation, building, and deployment
"""

from app.modules.automation.file_manager import file_manager, FileManager
from app.modules.automation.package_manager import package_manager, PackageManager, PackageManagerType
from app.modules.automation.build_system import build_system, BuildSystem, BuildTool
from app.modules.automation.error_detector import error_detector, error_recovery, ErrorDetector, ErrorRecoverySystem
from app.modules.automation.preview_server import preview_server_manager, PreviewServerManager
from app.modules.automation.claude_parser import claude_parser, ClaudeResponseParser
from app.modules.automation.automation_engine import automation_engine, AutomationEngine

__all__ = [
    # Singleton instances (ready to use)
    'file_manager',
    'package_manager',
    'build_system',
    'error_detector',
    'error_recovery',
    'preview_server_manager',
    'claude_parser',
    'automation_engine',

    # Classes (for custom instantiation)
    'FileManager',
    'PackageManager',
    'BuildSystem',
    'ErrorDetector',
    'ErrorRecoverySystem',
    'PreviewServerManager',
    'ClaudeResponseParser',
    'AutomationEngine',

    # Enums
    'PackageManagerType',
    'BuildTool',
]
