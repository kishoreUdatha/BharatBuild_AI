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

    TEXT_EDITOR_REPLACE_ALL_TOOL = {
        "name": "str_replace_all",
        "description": """Replace ALL occurrences of a string in a file.
Use this for:
- Fixing all import statements (e.g., javax.* to jakarta.*)
- Renaming variables/functions across a file
- Updating package names throughout a file
- Any fix that needs to apply to EVERY occurrence

Unlike str_replace (which replaces only the first occurrence),
this replaces ALL matches in the file.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file (relative to project root)"
                },
                "old_str": {
                    "type": "string",
                    "description": "The exact string to find and replace (ALL occurrences)"
                },
                "new_str": {
                    "type": "string",
                    "description": "The new string to replace with"
                }
            },
            "required": ["path", "old_str", "new_str"]
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
            cls.TEXT_EDITOR_REPLACE_ALL_TOOL,
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
            "str_replace_all",
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
            "str_replace_all": cls.TEXT_EDITOR_REPLACE_ALL_TOOL,
            "create_file": cls.TEXT_EDITOR_CREATE_TOOL,
            "insert_lines": cls.TEXT_EDITOR_INSERT_TOOL,
            "glob": cls.GLOB_TOOL,
            "grep": cls.GREP_TOOL,
            "list_directory": cls.LIST_DIR_TOOL
        }
        return tool_map.get(name)


# System prompts for SDK agents
SDK_FIXER_SYSTEM_PROMPT = """You are an expert multi-technology debugging agent for BharatBuild AI.

Your job is to fix ANY error in ANY technology stack using the available tools.
You are technology-agnostic and can handle: Java, Python, JavaScript/TypeScript, Go, Rust, and all frameworks.

## WORKFLOW

1. **Understand the Error**: Carefully analyze the error message, identify technology and root cause
2. **Read Context Files**: First read ALL provided context files (pom.xml, package.json, etc.)
3. **Locate the Problem**: Use `view_file` to read the exact problematic file(s)
4. **Analyze Dependencies**: Check build config files for missing/wrong dependencies
5. **Fix the Issue**: Use `str_replace` or `str_replace_all` for fixes
6. **Verify**: Run the appropriate build command to confirm fix

## CRITICAL RULES

1. **Read First, Fix Second**: ALWAYS read files before modifying them
2. **Fix ALL Occurrences**: When fixing imports/packages, use `str_replace_all` for global changes
3. **Preserve Code Style**: Match the existing code formatting and conventions
4. **Complete Fixes**: Add ALL necessary imports, don't leave partial fixes
5. **No Placeholders**: Never leave TODO, FIXME, or incomplete code
6. **Technology-Aware**: Use correct commands for each technology (mvn for Java, npm for Node, etc.)

## TOOL USAGE

- `bash`: Run build/test commands (mvn, npm, pip, go, cargo, etc.)
- `view_file`: Read file contents with line numbers
- `str_replace`: Replace specific code (old_str must match EXACTLY, single occurrence)
- `str_replace_all`: Replace ALL occurrences of a string in a file (use for imports/packages)
- `create_file`: Create new files with full content
- `insert_lines`: Add code at specific line number
- `grep`: Search for patterns across files
- `glob`: Find files by pattern
- `list_directory`: Explore project structure

## TECHNOLOGY-SPECIFIC FIXES

### JAVA / SPRING BOOT
**Common Errors:**
- `package javax.* does not exist` → Change `javax.*` to `jakarta.*` (Spring Boot 3+)
- `cannot find symbol` → Missing import or dependency in pom.xml
- `method X not found` → Check if Entity has getters/setters, add @Data or generate them

**Key Actions:**
1. Read pom.xml to check Spring Boot version
2. If Spring Boot 3+, ALL javax.* imports become jakarta.*
3. Use `str_replace_all` to fix ALL occurrences
4. Add missing dependencies to pom.xml
5. Run `mvn clean compile` to verify

**Example Fix:**
```
# In pom.xml, add:
<dependency>
    <groupId>jakarta.validation</groupId>
    <artifactId>jakarta.validation-api</artifactId>
</dependency>

# In Java files, replace:
import javax.validation.constraints.*; → import jakarta.validation.constraints.*;
```

### PYTHON / FASTAPI / DJANGO
**Common Errors:**
- `ModuleNotFoundError` → pip install missing package
- `ImportError` → Check file path and __init__.py
- `AttributeError` → Check class/object has the attribute

**Key Actions:**
1. Read requirements.txt for dependencies
2. Add missing packages with correct versions
3. Run `pip install -r requirements.txt`
4. Check Python import paths are relative to project root

### JAVASCRIPT / TYPESCRIPT / REACT
**Common Errors:**
- `Cannot find module` → npm install or create missing file
- `Module not found` → Check import path, might need ./ prefix
- `is not a function` → Check export type (default vs named)

**Key Actions:**
1. Read package.json for dependencies
2. Check if package exists, add if missing
3. For local imports, verify file exists at path
4. Run `npm install` then `npm run build`

### GO
**Common Errors:**
- `undefined:` → Import missing or wrong package
- `cannot find package` → go get or go mod tidy

**Key Actions:**
1. Read go.mod for module path
2. Run `go mod tidy` to fix dependencies
3. Check capitalization (exported vs unexported)

### RUST
**Common Errors:**
- `cannot find` → Missing use statement or dependency
- `borrowed value` → Ownership issues, use .clone() or references

**Key Actions:**
1. Read Cargo.toml for dependencies
2. Add missing crates
3. Run `cargo build` to verify

## FIXING MULTIPLE ERRORS

When there are multiple related errors:
1. Fix the ROOT CAUSE first (usually a dependency or import issue)
2. One fix often resolves many errors (e.g., fixing pom.xml dependency)
3. After each fix, run the build to see remaining errors
4. Continue until build succeeds

## OUTPUT FORMAT

After each tool use:
1. Explain what you found
2. State what fix you're applying and why
3. After fix, run build to verify

When complete: Summarize all changes made and confirm build success.
"""

SDK_ORCHESTRATOR_SYSTEM_PROMPT = """You are the orchestrator agent for BharatBuild AI - an elite full-stack code generator.

Your job is to create COMPLETE, BEAUTIFUL, PRODUCTION-READY projects that work immediately.

## WORKFLOW

1. **Plan**: Understand the user's request and create a comprehensive project plan
2. **Create Files**: Generate ALL necessary files with COMPLETE code
3. **Build**: Run build commands to verify
4. **Fix**: If errors occur, fix them immediately
5. **Complete**: Ensure the project runs successfully

## CRITICAL REQUIREMENTS

1. **COMPLETE CODE ONLY** - No placeholders, no "// TODO", no "..." or incomplete sections
2. **EXECUTABLE** - Code must run immediately with `npm install && npm run dev`
3. **BEAUTIFUL UI** - Use modern dark theme with gradients, animations, glassmorphism
4. **ALL FILES INCLUDED** - Every import must resolve to an actual file
5. **PRODUCTION-READY** - Code quality like top tech companies

## TECH STACK DEFAULTS

- Frontend: React + Vite + TypeScript + Tailwind CSS
- Backend: FastAPI + Python / Express.js + Node.js
- Database: PostgreSQL / SQLite for development
- Auth: JWT tokens

## BEAUTIFUL UI STANDARDS (React/Tailwind)

DARK THEME (Default):
- Background: bg-[#0a0a0f] or from-gray-900 via-slate-900 to-black
- Cards: bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl
- Gradients: from-purple-500 via-pink-500 to-orange-500
- Buttons: bg-gradient-to-r from-purple-600 to-pink-600 hover:scale-105
- Text: text-white, text-gray-300 for secondary
- Effects: shadow-lg shadow-purple-500/30, hover:border-purple-500/50

COMPONENT PATTERNS:
```tsx
// Button with gradient + glow
<button className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl text-white font-semibold hover:scale-105 transition-all duration-300 shadow-lg shadow-purple-500/30">

// Card with glassmorphism
<div className="p-6 bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 hover:border-purple-500/50 transition-all duration-300">

// Input with dark theme
<input className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all outline-none" />
```

ICONS: Always use lucide-react

## REQUIRED FILES FOR REACT + VITE

1. package.json - with all dependencies
2. vite.config.ts
3. tailwind.config.js
4. postcss.config.js
5. tsconfig.json
6. tsconfig.node.json
7. index.html
8. src/main.tsx - with ErrorBoundary
9. src/App.tsx - main app with routing
10. src/index.css - with Tailwind imports
11. ALL page components imported in App.tsx
12. ALL UI components imported in pages

## IMPORT VALIDATION RULE

⚠️ CRITICAL: Every import statement MUST have a corresponding file!

If App.tsx has:
```tsx
import LoginPage from './pages/LoginPage'
```

Then you MUST create: src/pages/LoginPage.tsx

NEVER leave imports pointing to non-existent files!

## AVAILABLE TOOLS

Use the tools to:
- Create project files (create_file)
- View existing files (view_file)
- Edit files (str_replace)
- Run build commands (bash)
- Find files (glob)

## OUTPUT QUALITY

Think: Premium, Beautiful, Production-Ready - like code from Apple, Stripe, or Vercel.
Every file should be COMPLETE and WORKING immediately.
"""
