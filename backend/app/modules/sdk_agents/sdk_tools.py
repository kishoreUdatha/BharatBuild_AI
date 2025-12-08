"""
Claude Agent SDK Tools Configuration

This module defines the tools available to SDK-based agents.
Tools are configured to work with BharatBuild's sandbox environment.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
from app.core.logging_config import logger


@dataclass
class ToolDefinition:
    """Definition for a Claude SDK tool"""
    name: str
    description: str
    input_schema: Dict[str, Any]


class SDKToolManager:
    """
    Manages tool definitions and configurations for Claude Agent SDK.

    Provides standardized tool schemas that work with:
    - Anthropic's tool use API
    - BharatBuild's sandbox environment
    - Project file system operations
    """

    # =========================================================================
    # TOOL DEFINITIONS (Compatible with Claude SDK tool_use)
    # =========================================================================

    BASH_TOOL = {
        "name": "bash",
        "description": """Execute a bash command in the sandbox environment.
Use this for:
- Running build commands (npm install, npm run build, pip install)
- Executing tests (npm test, pytest)
- Checking file system (ls, cat, head)
- Running development servers
- Any shell operations

The command runs in the project's sandbox directory.
Returns stdout, stderr, and exit code.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 120)",
                    "default": 120
                }
            },
            "required": ["command"]
        }
    }

    TEXT_EDITOR_VIEW_TOOL = {
        "name": "view_file",
        "description": """Read the contents of a file or list directory contents.
Use this to:
- Read source code files to understand their content
- View error logs
- Check configuration files
- List files in a directory

Returns the file content with line numbers.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file or directory (relative to project root)"
                },
                "start_line": {
                    "type": "integer",
                    "description": "Starting line number (1-indexed, optional)"
                },
                "end_line": {
                    "type": "integer",
                    "description": "Ending line number (optional)"
                }
            },
            "required": ["path"]
        }
    }

    TEXT_EDITOR_EDIT_TOOL = {
        "name": "str_replace",
        "description": """Replace a specific string in a file with new content.
Use this for:
- Fixing bugs by replacing broken code
- Updating imports
- Modifying configuration values
- Any surgical code changes

The old_str must match EXACTLY (including whitespace).
Use view_file first to see the exact content.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file (relative to project root)"
                },
                "old_str": {
                    "type": "string",
                    "description": "The exact string to find and replace (must match exactly)"
                },
                "new_str": {
                    "type": "string",
                    "description": "The new string to replace it with"
                }
            },
            "required": ["path", "old_str", "new_str"]
        }
    }

    TEXT_EDITOR_CREATE_TOOL = {
        "name": "create_file",
        "description": """Create a new file with the specified content.
Use this for:
- Creating missing configuration files
- Adding new source files
- Creating documentation

The file will be created at the specified path.
Parent directories will be created if they don't exist.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path for the new file (relative to project root)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["path", "content"]
        }
    }

    TEXT_EDITOR_INSERT_TOOL = {
        "name": "insert_lines",
        "description": """Insert new lines at a specific position in a file.
Use this for:
- Adding new imports at the top of a file
- Inserting new functions or methods
- Adding configuration entries

Line numbers are 1-indexed. Content is inserted AFTER the specified line.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file (relative to project root)"
                },
                "line": {
                    "type": "integer",
                    "description": "Line number after which to insert (1-indexed, 0 = beginning)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to insert"
                }
            },
            "required": ["path", "line", "content"]
        }
    }

    GLOB_TOOL = {
        "name": "glob",
        "description": """Find files matching a glob pattern.
Use this for:
- Finding all files of a certain type (*.tsx, *.py)
- Locating configuration files
- Searching for files by name pattern

Returns a list of matching file paths.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g., '**/*.tsx', 'src/**/*.py')"
                }
            },
            "required": ["pattern"]
        }
    }

    GREP_TOOL = {
        "name": "grep",
        "description": """Search for a pattern in files.
Use this for:
- Finding where a function/variable is defined or used
- Searching for error strings
- Locating specific code patterns

Returns matching lines with file paths and line numbers.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Search pattern (supports regex)"
                },
                "path": {
                    "type": "string",
                    "description": "Path to search in (file or directory)",
                    "default": "."
                },
                "include": {
                    "type": "string",
                    "description": "File pattern to include (e.g., '*.tsx')"
                }
            },
            "required": ["pattern"]
        }
    }

    LIST_DIR_TOOL = {
        "name": "list_directory",
        "description": """List contents of a directory.
Use this for:
- Understanding project structure
- Finding files in a specific folder
- Checking if files exist

Returns a list of files and directories.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path (relative to project root)",
                    "default": "."
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to list recursively",
                    "default": False
                }
            },
            "required": []
        }
    }

    @classmethod
    def get_fixer_tools(cls) -> List[Dict[str, Any]]:
        """Get tools for the Fixer Agent"""
        return [
            cls.BASH_TOOL,
            cls.TEXT_EDITOR_VIEW_TOOL,
            cls.TEXT_EDITOR_EDIT_TOOL,
            cls.TEXT_EDITOR_CREATE_TOOL,
            cls.TEXT_EDITOR_INSERT_TOOL,
            cls.GLOB_TOOL,
            cls.GREP_TOOL,
            cls.LIST_DIR_TOOL
        ]

    @classmethod
    def get_orchestrator_tools(cls) -> List[Dict[str, Any]]:
        """Get tools for the Orchestrator Agent"""
        return cls.get_fixer_tools()  # Same tools for now

    @classmethod
    def get_tool_names(cls) -> List[str]:
        """Get list of all tool names"""
        return [
            "bash",
            "view_file",
            "str_replace",
            "create_file",
            "insert_lines",
            "glob",
            "grep",
            "list_directory"
        ]

    @classmethod
    def get_tool_by_name(cls, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific tool definition by name"""
        tool_map = {
            "bash": cls.BASH_TOOL,
            "view_file": cls.TEXT_EDITOR_VIEW_TOOL,
            "str_replace": cls.TEXT_EDITOR_EDIT_TOOL,
            "create_file": cls.TEXT_EDITOR_CREATE_TOOL,
            "insert_lines": cls.TEXT_EDITOR_INSERT_TOOL,
            "glob": cls.GLOB_TOOL,
            "grep": cls.GREP_TOOL,
            "list_directory": cls.LIST_DIR_TOOL
        }
        return tool_map.get(name)


# System prompts for SDK agents
SDK_FIXER_SYSTEM_PROMPT = """You are an expert debugging agent for BharatBuild AI.

Your job is to fix errors in code projects using the available tools.

## WORKFLOW

1. **Understand the Error**: Read the error message and stack trace carefully
2. **Locate the Problem**: Use `view_file` to read the problematic file
3. **Find Context**: Use `grep` to find related code if needed
4. **Fix the Issue**: Use `str_replace` for minimal surgical fixes
5. **Verify**: Use `bash` to run the build/test again

## RULES

1. **Minimal Changes**: Only change what's necessary to fix the error
2. **One Fix at a Time**: Don't try to fix multiple unrelated issues
3. **Preserve Style**: Match the existing code style
4. **Complete Fixes**: Ensure imports are added if needed
5. **No Placeholders**: Never leave TODO or incomplete code

## TOOL USAGE

- `bash`: Run commands to see errors, test fixes
- `view_file`: Read file contents to understand code
- `str_replace`: Replace specific code (old_str must match EXACTLY)
- `create_file`: Create missing config files
- `grep`: Search for patterns across files
- `glob`: Find files by pattern

## ERROR TYPES

### Syntax Errors
- Missing brackets, quotes, semicolons
- Invalid syntax for the language

### Import Errors
- Module not found → Check if package installed, fix import path
- Cannot find module → Create missing file or fix path

### Type Errors
- Null/undefined access → Add null checks
- Type mismatch → Fix types

### Build Errors
- Missing dependencies → Use bash to install
- Config errors → Fix or create config files

## OUTPUT

After each tool use, explain what you found and what you'll do next.
When the error is fixed, confirm by running the build command again.
"""

SDK_ORCHESTRATOR_SYSTEM_PROMPT = """You are the orchestrator agent for BharatBuild AI project generator.

Your job is to coordinate the creation of complete, runnable projects.

## WORKFLOW

1. **Plan**: Understand the user's request and create a project plan
2. **Create Files**: Generate all necessary files
3. **Build**: Run build commands to verify
4. **Fix**: If errors occur, fix them
5. **Complete**: Ensure the project runs successfully

## AVAILABLE TOOLS

Use the tools to:
- Create project files
- Run build commands
- Fix any errors that occur
- Verify the project works

## RULES

1. Generate complete, runnable code
2. Include all necessary configuration files
3. Use modern best practices
4. Ensure the project builds without errors
"""
