"""
Agentic CLI - Full Claude Code-like capabilities

This module provides a complete agentic CLI experience with:
- Project generation
- Code suggestions
- Compilation & build
- Error fixing & debugging
- Root cause analysis
- Running projects
- Code rewriting
- Multi-turn autonomous execution
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator, Callable
from dataclasses import dataclass, field
from enum import Enum

from anthropic import AsyncAnthropic

from cli.config import CLIConfig
from cli.tools import ToolExecutor, CommandResult
from cli.renderer import ResponseRenderer


class ToolType(Enum):
    """Available tool types"""
    READ = "Read"
    WRITE = "Write"
    EDIT = "Edit"
    BASH = "Bash"
    GLOB = "Glob"
    GREP = "Grep"
    LIST_DIR = "ListDir"
    THINK = "Think"


# Comprehensive system prompt with MANDATORY Generate-Run-Fix-Rerun loop
AGENTIC_SYSTEM_PROMPT = '''You are BharatBuild AI, an expert AI coding assistant similar to Claude Code.
You help developers with ALL aspects of software development.

## Your Capabilities
1. **Project Generation** - Create complete projects from scratch
2. **Code Writing** - Write new code, functions, classes, modules
3. **Code Editing** - Modify existing code precisely
4. **Debugging** - Find and fix bugs, identify root causes
5. **Error Fixing** - Analyze errors and fix them
6. **Building & Running** - Compile, build, and run projects
7. **Testing** - Write and run tests
8. **Refactoring** - Improve code quality and structure

## Available Tools

Use these XML tools to interact with the filesystem:

### Read File
```xml
<tool name="Read">
<path>relative/path/to/file</path>
</tool>
```

### Write File
```xml
<tool name="Write">
<path>relative/path/to/file</path>
<content>file content here</content>
</tool>
```

### Edit File
```xml
<tool name="Edit">
<path>relative/path/to/file</path>
<old_string>exact text to find</old_string>
<new_string>replacement text</new_string>
</tool>
```

### Execute Command
```xml
<tool name="Bash">
<command>your command here</command>
<description>Brief description</description>
</tool>
```

### Find Files
```xml
<tool name="Glob">
<pattern>**/*.py</pattern>
</tool>
```

### Search in Files
```xml
<tool name="Grep">
<pattern>search pattern</pattern>
<path>.</path>
</tool>
```

### List Directory
```xml
<tool name="ListDir">
<path>.</path>
</tool>
```

### Think (reasoning)
```xml
<tool name="Think">
<thought>Your detailed reasoning...</thought>
</tool>
```

---

## ⚠️ MANDATORY: Generate → Run → Fix → Re-run Loop

**THIS IS THE MOST IMPORTANT RULE. YOU MUST FOLLOW THIS LOOP UNTIL SUCCESS.**

```
┌─────────────────────────────────────────────────────────────┐
│                    MANDATORY WORKFLOW                        │
│                                                              │
│   1. GENERATE/WRITE CODE                                     │
│            ↓                                                 │
│   2. RUN/BUILD/TEST (verify it works)                       │
│            ↓                                                 │
│   3. ERROR? ──Yes──→ ANALYZE ERROR                          │
│        │                   ↓                                 │
│        No            4. FIX THE ERROR                        │
│        ↓                   ↓                                 │
│   ✅ SUCCESS!        5. RE-RUN (go back to step 2)          │
│                            ↓                                 │
│                      Still error? Try DIFFERENT approach     │
│                            ↓                                 │
│                      Repeat until SUCCESS                    │
└─────────────────────────────────────────────────────────────┘
```

### YOU MUST ALWAYS:
1. **After writing ANY code** → Run/build/test to verify it works
2. **If there's an error** → Fix it and re-run (don't just explain the fix)
3. **If fix doesn't work** → Try a DIFFERENT approach and re-run
4. **Keep looping** → Until the code runs successfully OR you've tried 3+ different approaches

### NEVER DO THIS:
- ❌ Write code and stop without running it
- ❌ See an error and only explain how to fix it (you must actually fix AND re-run)
- ❌ Try the same failing approach twice
- ❌ Give up after one or two failures

---

## Verification Commands by Project Type

After generating or fixing code, ALWAYS run the appropriate verification:

| Project Type | Verification Command |
|--------------|---------------------|
| Python | `python main.py` or `python -m pytest` |
| Node.js | `npm install && npm start` or `npm test` |
| TypeScript | `npx tsc && node dist/index.js` |
| React | `npm install && npm run build` |
| Java | `javac *.java && java Main` |
| Go | `go build && ./main` or `go run .` |
| Rust | `cargo build && cargo run` |
| C/C++ | `gcc main.c -o main && ./main` |

---

## Error Recovery Strategies

When an error occurs, try these approaches IN ORDER:

### Strategy 1: Direct Fix
```
1. Read the error message carefully
2. Identify the exact line/file causing the error
3. Fix that specific issue
4. Re-run → If still fails, go to Strategy 2
```

### Strategy 2: Alternative Approach
```
1. The direct fix didn't work
2. Try a completely different solution
3. Example: If import fails, try relative import
4. Re-run → If still fails, go to Strategy 3
```

### Strategy 3: Rebuild from Scratch
```
1. Multiple fixes have failed
2. Delete/rewrite the problematic section entirely
3. Use a simpler, more standard approach
4. Re-run → If still fails, go to Strategy 4
```

### Strategy 4: Workaround
```
1. The standard approach isn't working
2. Find an alternative way to achieve the goal
3. Example: If npm fails, try yarn; if pip fails, try pip3
4. Re-run
```

---

## Example: Complete Generate-Run-Fix Loop

**User Request:** "Create a Python script that reads a CSV file"

**Turn 1 - GENERATE:**
```xml
<tool name="Write">
<path>csv_reader.py</path>
<content>
import pandas as pd

def read_csv(filename):
    df = pd.read_csv(filename)
    return df

if __name__ == "__main__":
    data = read_csv("data.csv")
    print(data.head())
</content>
</tool>
```

**Turn 2 - RUN:**
```xml
<tool name="Bash">
<command>python csv_reader.py</command>
<description>Test the CSV reader script</description>
</tool>
```

**Turn 3 - ERROR! (ModuleNotFoundError: pandas)**
**ANALYZE:** pandas is not installed
**FIX:**
```xml
<tool name="Bash">
<command>pip install pandas</command>
<description>Install missing pandas dependency</description>
</tool>
```

**Turn 4 - RE-RUN:**
```xml
<tool name="Bash">
<command>python csv_reader.py</command>
<description>Re-test after installing pandas</description>
</tool>
```

**Turn 5 - ERROR! (FileNotFoundError: data.csv)**
**ANALYZE:** data.csv doesn't exist
**FIX:**
```xml
<tool name="Write">
<path>data.csv</path>
<content>name,age,city
Alice,30,New York
Bob,25,Los Angeles
</content>
</tool>
```

**Turn 6 - RE-RUN:**
```xml
<tool name="Bash">
<command>python csv_reader.py</command>
<description>Re-test with sample data file</description>
</tool>
```

**Turn 7 - ✅ SUCCESS!**
Output shows the CSV data. Task complete.

---

## Multi-Approach Problem Solving

When one approach fails, try alternatives:

| Failed Approach | Alternative 1 | Alternative 2 | Alternative 3 |
|-----------------|---------------|---------------|---------------|
| `npm install` fails | Try `yarn` | Try `pnpm` | Delete node_modules and retry |
| `pip install` fails | Try `pip3` | Try `python -m pip` | Use virtual env |
| Edit fails (string not found) | Re-read file first | Use Write to replace entire file | Use Grep to find correct string |
| Import error | Check package name | Try relative import | Install the package |
| Build error | Fix syntax error | Check dependencies | Try different compiler flags |
| Permission denied | Add execute permission | Run with sudo | Check file ownership |

---

## Working Directory
Current working directory: {working_dir}

## Session Context
{session_context}

---

## FINAL REMINDER

🔴 **CRITICAL:** After EVERY code change, you MUST run/test to verify.
🔴 **CRITICAL:** If there's an error, you MUST fix it AND re-run.
🔴 **CRITICAL:** Keep looping until SUCCESS or you've exhausted all approaches.
🔴 **NEVER** stop at an error without attempting to fix and re-run.

You are an autonomous agent. Your job is not done until the code RUNS SUCCESSFULLY.
'''


@dataclass
class ToolResult:
    """Result of a tool execution"""
    tool: str
    success: bool
    output: str
    error: Optional[str] = None


@dataclass
class ApproachAttempt:
    """Tracks a single approach attempt"""
    description: str
    tools_used: List[str] = field(default_factory=list)
    success: bool = False
    failure_reason: Optional[str] = None
    turn_number: int = 0


@dataclass
class AgentState:
    """Tracks agent state across turns with approach tracking"""
    messages: List[Dict[str, str]] = field(default_factory=list)
    files_read: List[str] = field(default_factory=list)
    files_written: List[str] = field(default_factory=list)
    files_edited: List[str] = field(default_factory=list)
    commands_run: List[str] = field(default_factory=list)
    errors_encountered: List[str] = field(default_factory=list)
    total_tokens: int = 0
    turns: int = 0

    # Multi-approach tracking
    approaches_tried: List[ApproachAttempt] = field(default_factory=list)
    current_approach: Optional[str] = None
    consecutive_failures: int = 0
    max_consecutive_failures: int = 3

    # Learned patterns from failures
    failed_commands: List[str] = field(default_factory=list)
    failed_edits: List[Dict[str, str]] = field(default_factory=list)
    working_patterns: List[str] = field(default_factory=list)


class AgenticCLI:
    """Full agentic CLI with Claude Code-like capabilities"""

    def __init__(self, config: CLIConfig, console, renderer: ResponseRenderer):
        self.config = config
        self.console = console
        self.renderer = renderer
        self.tool_executor = ToolExecutor(config, console)
        self.state = AgentState()

        # Initialize Anthropic client
        api_key = config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.client = AsyncAnthropic(api_key=api_key)
        self.model = self._get_model_name()

    def _get_model_name(self) -> str:
        """Get full model name"""
        model_map = {
            "haiku": "claude-3-5-haiku-20241022",
            "sonnet": "claude-3-5-sonnet-20241022",
            "opus": "claude-3-opus-20240229",
        }
        return model_map.get(self.config.model, self.config.model)

    def _get_system_prompt(self) -> str:
        """Generate system prompt with context including failure history"""
        # Build session context
        session_context_parts = []

        # Files already read
        if self.state.files_read:
            session_context_parts.append(f"Files already read: {', '.join(self.state.files_read[-10:])}")

        # Failed commands to avoid
        if self.state.failed_commands:
            session_context_parts.append(
                f"Commands that FAILED (try alternatives): {', '.join(self.state.failed_commands[-5:])}"
            )

        # Failed edit patterns to avoid
        if self.state.failed_edits:
            failed_edit_info = [f"{e.get('path', 'unknown')}" for e in self.state.failed_edits[-3:]]
            session_context_parts.append(
                f"Edits that FAILED (re-read files first): {', '.join(failed_edit_info)}"
            )

        # Previous approaches tried
        if self.state.approaches_tried:
            failed_approaches = [a.description for a in self.state.approaches_tried if not a.success]
            if failed_approaches:
                session_context_parts.append(
                    f"Approaches already tried and FAILED: {'; '.join(failed_approaches[-3:])}"
                )

        # Working patterns
        if self.state.working_patterns:
            session_context_parts.append(
                f"Patterns that WORKED: {'; '.join(self.state.working_patterns[-3:])}"
            )

        # Consecutive failures warning
        if self.state.consecutive_failures >= 2:
            session_context_parts.append(
                f"WARNING: {self.state.consecutive_failures} consecutive failures. "
                "You MUST try a completely different approach now."
            )

        session_context = "\n".join(session_context_parts) if session_context_parts else "No prior context."

        base_prompt = AGENTIC_SYSTEM_PROMPT.format(
            working_dir=self.config.working_directory,
            session_context=session_context
        )

        return base_prompt

    async def run(self, user_prompt: str,
                  on_thinking: Optional[Callable[[str], None]] = None,
                  on_tool_start: Optional[Callable[[str, Dict], None]] = None,
                  on_tool_end: Optional[Callable[[str, ToolResult], None]] = None,
                  on_content: Optional[Callable[[str], None]] = None) -> str:
        """
        Run the agent with a user prompt.

        This is the main entry point that handles multi-turn autonomous execution.
        """
        self.state.messages.append({"role": "user", "content": user_prompt})
        self.state.turns = 0

        final_response = ""
        max_turns = self.config.max_turns

        while self.state.turns < max_turns:
            self.state.turns += 1

            if on_thinking:
                on_thinking(f"Turn {self.state.turns}/{max_turns}")

            # Get response from Claude
            response_text = ""
            try:
                async with self.client.messages.stream(
                    model=self.model,
                    max_tokens=8192,
                    temperature=0.7,
                    system=self._get_system_prompt(),
                    messages=self.state.messages
                ) as stream:
                    async for text in stream.text_stream:
                        response_text += text
                        if on_content:
                            on_content(text)

                # Get final message for token count
                final_message = await stream.get_final_message()
                self.state.total_tokens += (
                    final_message.usage.input_tokens +
                    final_message.usage.output_tokens
                )

            except Exception as e:
                self.console.print(f"[red]API Error: {e}[/red]")
                break

            # Add assistant message to history
            self.state.messages.append({"role": "assistant", "content": response_text})

            # Parse tool calls from response
            tool_calls = self._parse_tool_calls(response_text)

            if not tool_calls:
                # No tool calls - agent is done
                final_response = response_text
                break

            # Execute all tool calls
            tool_results = []
            for tool_call in tool_calls:
                if on_tool_start:
                    on_tool_start(tool_call["tool"], tool_call)

                result = await self._execute_tool(tool_call)
                tool_results.append(result)

                if on_tool_end:
                    on_tool_end(tool_call["tool"], result)

            # Format results for next turn
            results_text = self._format_tool_results(tool_results)
            self.state.messages.append({"role": "user", "content": results_text})

        return final_response

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Parse tool calls from Claude's response"""
        tool_calls = []

        # Pattern to match tool XML blocks
        tool_pattern = r'<tool\s+name="(\w+)">(.*?)</tool>'
        matches = re.findall(tool_pattern, response, re.DOTALL)

        for tool_name, tool_content in matches:
            tool_call = {"tool": tool_name, "raw": tool_content}

            if tool_name == "Read":
                path_match = re.search(r'<path>(.*?)</path>', tool_content, re.DOTALL)
                if path_match:
                    tool_call["path"] = path_match.group(1).strip()

            elif tool_name == "Write":
                path_match = re.search(r'<path>(.*?)</path>', tool_content, re.DOTALL)
                content_match = re.search(r'<content>(.*?)</content>', tool_content, re.DOTALL)
                if path_match:
                    tool_call["path"] = path_match.group(1).strip()
                if content_match:
                    tool_call["content"] = content_match.group(1)

            elif tool_name == "Edit":
                path_match = re.search(r'<path>(.*?)</path>', tool_content, re.DOTALL)
                old_match = re.search(r'<old_string>(.*?)</old_string>', tool_content, re.DOTALL)
                new_match = re.search(r'<new_string>(.*?)</new_string>', tool_content, re.DOTALL)
                if path_match:
                    tool_call["path"] = path_match.group(1).strip()
                if old_match:
                    tool_call["old_string"] = old_match.group(1)
                if new_match:
                    tool_call["new_string"] = new_match.group(1)

            elif tool_name == "Bash":
                cmd_match = re.search(r'<command>(.*?)</command>', tool_content, re.DOTALL)
                desc_match = re.search(r'<description>(.*?)</description>', tool_content, re.DOTALL)
                if cmd_match:
                    tool_call["command"] = cmd_match.group(1).strip()
                if desc_match:
                    tool_call["description"] = desc_match.group(1).strip()

            elif tool_name == "Glob":
                pattern_match = re.search(r'<pattern>(.*?)</pattern>', tool_content, re.DOTALL)
                if pattern_match:
                    tool_call["pattern"] = pattern_match.group(1).strip()

            elif tool_name == "Grep":
                pattern_match = re.search(r'<pattern>(.*?)</pattern>', tool_content, re.DOTALL)
                path_match = re.search(r'<path>(.*?)</path>', tool_content, re.DOTALL)
                if pattern_match:
                    tool_call["pattern"] = pattern_match.group(1).strip()
                if path_match:
                    tool_call["path"] = path_match.group(1).strip()

            elif tool_name == "ListDir":
                path_match = re.search(r'<path>(.*?)</path>', tool_content, re.DOTALL)
                if path_match:
                    tool_call["path"] = path_match.group(1).strip()

            elif tool_name == "Think":
                thought_match = re.search(r'<thought>(.*?)</thought>', tool_content, re.DOTALL)
                if thought_match:
                    tool_call["thought"] = thought_match.group(1).strip()

            tool_calls.append(tool_call)

        return tool_calls

    async def _execute_tool(self, tool_call: Dict[str, Any]) -> ToolResult:
        """Execute a single tool call"""
        tool_name = tool_call["tool"]

        try:
            if tool_name == "Read":
                path = tool_call.get("path", "")
                content = await self.tool_executor.read_file(path)
                self.state.files_read.append(path)

                if content:
                    # Truncate very large files
                    if len(content) > 50000:
                        content = content[:50000] + "\n\n... [truncated, file too large]"
                    return ToolResult(tool_name, True, content)
                else:
                    return ToolResult(tool_name, False, "", f"File not found: {path}")

            elif tool_name == "Write":
                path = tool_call.get("path", "")
                content = tool_call.get("content", "")

                # Permission check
                if self.config.permission_mode == "ask":
                    from rich.prompt import Confirm
                    self.console.print(f"\n[cyan]📝 Write file: {path}[/cyan]")
                    preview = content[:300] + "..." if len(content) > 300 else content
                    self.console.print(f"[dim]{preview}[/dim]")
                    if not Confirm.ask("[yellow]Allow?[/yellow]", default=True):
                        return ToolResult(tool_name, False, "", "Denied by user")

                await self.tool_executor.write_file(path, content)
                self.state.files_written.append(path)
                self.console.print(f"[green]✓ Created: {path}[/green]")
                return ToolResult(tool_name, True, f"File written: {path}")

            elif tool_name == "Edit":
                path = tool_call.get("path", "")
                old_string = tool_call.get("old_string", "")
                new_string = tool_call.get("new_string", "")

                # Permission check
                if self.config.permission_mode == "ask":
                    from rich.prompt import Confirm
                    self.console.print(f"\n[cyan]✏️ Edit file: {path}[/cyan]")
                    self.console.print(f"[red]- {old_string[:100]}...[/red]")
                    self.console.print(f"[green]+ {new_string[:100]}...[/green]")
                    if not Confirm.ask("[yellow]Allow?[/yellow]", default=True):
                        return ToolResult(tool_name, False, "", "Denied by user")

                try:
                    await self.tool_executor.edit_file(path, old_string, new_string)
                    self.state.files_edited.append(path)
                    self.state.working_patterns.append(f"Edit {path} succeeded")
                    self.console.print(f"[green]✓ Edited: {path}[/green]")
                    return ToolResult(tool_name, True, f"File edited: {path}")
                except Exception as edit_error:
                    # Track failed edit for context
                    self.state.failed_edits.append({
                        "path": path,
                        "old_string_preview": old_string[:100],
                        "error": str(edit_error)
                    })
                    self.console.print(f"[red]✗ Edit failed: {edit_error}[/red]")
                    return ToolResult(
                        tool_name, False, "",
                        f"Edit failed: {edit_error}. TRY: 1) Re-read file to get exact content, "
                        f"2) Use Write to replace entire file, 3) Check if path is correct"
                    )

            elif tool_name == "Bash":
                command = tool_call.get("command", "")
                description = tool_call.get("description", "")

                # Permission check
                if self.config.permission_mode == "ask":
                    from rich.prompt import Confirm
                    self.console.print(f"\n[cyan]$ {command}[/cyan]")
                    if description:
                        self.console.print(f"[dim]{description}[/dim]")
                    if not Confirm.ask("[yellow]Execute?[/yellow]", default=True):
                        return ToolResult(tool_name, False, "", "Denied by user")

                self.console.print(f"[cyan]$ {command}[/cyan]")
                result = await self.tool_executor.execute_bash(command, timeout=300)
                self.state.commands_run.append(command)

                output = result.stdout or ""
                if result.stderr:
                    output += f"\nSTDERR:\n{result.stderr}"

                if result.exit_code != 0:
                    self.console.print(f"[yellow]Exit code: {result.exit_code}[/yellow]")
                    self.state.errors_encountered.append(f"Command failed: {command}")
                    # Track failed command for future context
                    self.state.failed_commands.append(command)

                    # Provide helpful suggestions based on error
                    suggestions = self._get_bash_failure_suggestions(command, result.stderr or output)
                    return ToolResult(
                        tool_name, False, output,
                        f"Exit code: {result.exit_code}. {suggestions}"
                    )

                self.state.working_patterns.append(f"Command '{command[:30]}...' succeeded")
                self.console.print(f"[green]✓ Command completed[/green]")
                return ToolResult(tool_name, True, output)

            elif tool_name == "Glob":
                pattern = tool_call.get("pattern", "*")
                files = await self.tool_executor.glob_files(pattern)
                result = "\n".join(files[:100])
                if len(files) > 100:
                    result += f"\n... and {len(files) - 100} more files"
                return ToolResult(tool_name, True, result)

            elif tool_name == "Grep":
                pattern = tool_call.get("pattern", "")
                path = tool_call.get("path", ".")
                results = await self.tool_executor.grep_files(pattern, path)
                output = "\n".join(
                    f"{r['file']}:{r['line']}: {r['content']}"
                    for r in results[:50]
                )
                if len(results) > 50:
                    output += f"\n... and {len(results) - 50} more matches"
                return ToolResult(tool_name, True, output)

            elif tool_name == "ListDir":
                path = tool_call.get("path", ".")
                files = await self.tool_executor.list_files(path)
                return ToolResult(tool_name, True, "\n".join(files[:100]))

            elif tool_name == "Think":
                # Think tool just returns the thought - no action needed
                thought = tool_call.get("thought", "")
                self.console.print(f"[dim]💭 {thought[:200]}...[/dim]")
                return ToolResult(tool_name, True, "Thought processed")

            else:
                return ToolResult(tool_name, False, "", f"Unknown tool: {tool_name}")

        except Exception as e:
            self.state.errors_encountered.append(str(e))
            return ToolResult(tool_name, False, "", str(e))

    def _get_bash_failure_suggestions(self, command: str, error_output: str) -> str:
        """Generate helpful suggestions based on command failure"""
        suggestions = []
        error_lower = error_output.lower()
        command_lower = command.lower()

        # npm/node related
        if "npm" in command_lower or "node" in command_lower:
            if "not found" in error_lower or "command not found" in error_lower:
                suggestions.append("TRY: Check if Node.js is installed, or use 'npx' instead")
            elif "enoent" in error_lower or "no such file" in error_lower:
                suggestions.append("TRY: Run 'npm install' first, or check package.json exists")
            elif "permission" in error_lower:
                suggestions.append("TRY: Run with 'sudo' or fix file permissions")
            else:
                suggestions.append("TRY: 1) npm install, 2) npx instead of npm, 3) yarn as alternative")

        # pip/python related
        elif "pip" in command_lower or "python" in command_lower:
            if "not found" in error_lower:
                suggestions.append("TRY: Use 'pip3' or 'python3' instead")
            elif "permission" in error_lower:
                suggestions.append("TRY: Use 'pip install --user' or virtual environment")
            elif "no module" in error_lower:
                suggestions.append("TRY: Install missing module with pip")
            else:
                suggestions.append("TRY: 1) pip3 instead of pip, 2) python3 -m pip, 3) Create venv first")

        # git related
        elif "git" in command_lower:
            if "not a git repository" in error_lower:
                suggestions.append("TRY: Run 'git init' first")
            elif "conflict" in error_lower:
                suggestions.append("TRY: Resolve conflicts manually or use 'git stash'")
            else:
                suggestions.append("TRY: Check git status, ensure repo is initialized")

        # Build/compile related
        elif any(x in command_lower for x in ["make", "build", "compile", "gcc", "javac", "cargo", "go build"]):
            if "not found" in error_lower:
                suggestions.append("TRY: Install build tools or check PATH")
            elif "error:" in error_lower or "undefined" in error_lower:
                suggestions.append("TRY: Fix syntax errors in source files first")
            else:
                suggestions.append("TRY: 1) Check source files for errors, 2) Install dependencies, 3) Check build config")

        # Generic suggestions
        if not suggestions:
            suggestions.append(
                "TRY: 1) Check if command exists, 2) Install missing dependencies, "
                "3) Check file paths, 4) Try alternative command"
            )

        return " ".join(suggestions)

    def _format_tool_results(self, results: List[ToolResult]) -> str:
        """Format tool results for the next turn with MANDATORY fix-and-rerun enforcement"""
        formatted = ["Tool execution results:"]
        has_failures = False
        failure_count = 0
        has_bash_failure = False
        bash_error = ""

        for result in results:
            if result.success:
                formatted.append(f"\n✓ {result.tool} succeeded:")
                if result.output:
                    # Truncate very long outputs
                    output = result.output
                    if len(output) > 10000:
                        output = output[:10000] + "\n... [output truncated]"
                    formatted.append(output)
                # Track successful pattern
                self.state.consecutive_failures = 0
            else:
                has_failures = True
                failure_count += 1
                formatted.append(f"\n✗ {result.tool} FAILED:")
                formatted.append(result.error or "Unknown error")

                # Track bash failures specifically for re-run enforcement
                if result.tool == "Bash":
                    has_bash_failure = True
                    bash_error = result.error or result.output or "Unknown error"

                # Track the failure
                self.state.consecutive_failures += 1

        # MANDATORY: Enforce the Generate → Run → Fix → Re-run loop
        if has_failures:
            formatted.append("\n" + "=" * 60)
            formatted.append("🔴 MANDATORY ACTION REQUIRED 🔴")
            formatted.append("=" * 60)

            if has_bash_failure:
                formatted.append("\n📋 YOU MUST FOLLOW THIS LOOP:")
                formatted.append("   1. ANALYZE the error above")
                formatted.append("   2. FIX the issue (edit code, install deps, etc.)")
                formatted.append("   3. RE-RUN the command to verify the fix")
                formatted.append("   4. If still failing → try DIFFERENT approach")
                formatted.append("   5. REPEAT until SUCCESS")
                formatted.append("\n⚠️ DO NOT stop here. You MUST fix and re-run!")

            if failure_count == 1:
                formatted.append("\n🔧 SUGGESTED ACTIONS:")
                formatted.append("   - If Bash failed: Fix the issue, then RE-RUN the same command")
                formatted.append("   - If Edit failed: Re-read file first, then try again")
                formatted.append("   - If import error: Install the missing package")
                formatted.append("   - If syntax error: Fix the code and re-run")
            else:
                formatted.append(f"\n⚠️ Multiple failures ({failure_count}) - try DIFFERENT approach:")
                formatted.append("   - Use Think tool to analyze what's going wrong")
                formatted.append("   - Try completely different solution strategy")
                formatted.append("   - Consider rewriting problematic code from scratch")

            if self.state.consecutive_failures >= 2:
                formatted.append(f"\n🚨 ALERT: {self.state.consecutive_failures} CONSECUTIVE FAILURES!")
                formatted.append("   You have tried similar approaches that keep failing.")
                formatted.append("   YOU MUST NOW:")
                formatted.append("   1. Stop and use Think tool to analyze root cause")
                formatted.append("   2. Try a COMPLETELY DIFFERENT approach")
                formatted.append("   3. Consider alternative tools/commands")
                formatted.append("   DO NOT repeat the same failing approach!")

            if self.state.consecutive_failures >= 4:
                formatted.append("\n🆘 CRITICAL: Many failures detected!")
                formatted.append("   Consider:")
                formatted.append("   - Simplifying the approach")
                formatted.append("   - Breaking the task into smaller steps")
                formatted.append("   - Using more basic/standard solutions")

            formatted.append("\n" + "=" * 60)

        return "\n".join(formatted)

    def reset(self):
        """Reset agent state"""
        self.state = AgentState()


class AgenticApp:
    """Main agentic application"""

    def __init__(self, config: CLIConfig):
        from rich.console import Console
        self.config = config
        self.console = Console()
        self.renderer = ResponseRenderer(self.console, config)
        self.agent = AgenticCLI(config, self.console, self.renderer)

    async def run_interactive(self):
        """Run interactive agentic mode"""
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
        from rich.panel import Panel
        from rich.live import Live
        from rich.spinner import Spinner

        self.console.clear()
        self._print_header()

        session = PromptSession(
            history=FileHistory(self.config.history_file),
            auto_suggest=AutoSuggestFromHistory()
        )

        while True:
            try:
                # Get user input
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: session.prompt("\n❯ ")
                )

                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.strip().lower() in ["/quit", "/exit", "/q"]:
                    break

                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue

                # Run agent
                self.console.print()

                def on_content(text):
                    self.console.print(text, end="")

                def on_tool_start(tool, params):
                    self.console.print(f"\n[dim]→ {tool}...[/dim]")

                response = await self.agent.run(
                    user_input,
                    on_content=on_content,
                    on_tool_start=on_tool_start
                )

                self.console.print()

                # Show summary
                self._print_summary()

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted. Use /quit to exit.[/yellow]")
            except EOFError:
                break

        self.console.print("\n[cyan]Goodbye! 👋[/cyan]")

    async def run_single(self, prompt: str):
        """Run a single prompt"""
        def on_content(text):
            print(text, end="", flush=True)

        await self.agent.run(prompt, on_content=on_content)
        print()

    def _print_header(self):
        """Print header"""
        from rich.panel import Panel

        header_text = """[bold cyan]BharatBuild AI[/bold cyan] - Agentic Mode

[green]Full Claude Code-like capabilities:[/green]
  • Generate complete projects
  • Fix errors & debug code
  • Build & run projects
  • Refactor & improve code
  • Write tests & documentation

[dim]Commands: /help, /status, /clear, /quit[/dim]"""

        self.console.print(Panel(header_text, border_style="cyan"))
        self.console.print(f"📁 {self.config.working_directory}")
        self.console.print(f"🤖 {self.config.model} (max {self.config.max_turns} turns)")

    def _print_summary(self):
        """Print execution summary with approach tracking"""
        state = self.agent.state
        if state.files_written or state.files_edited or state.commands_run or state.errors_encountered:
            self.console.print("\n[dim]─── Summary ───[/dim]")
            if state.files_written:
                self.console.print(f"[green]Created:[/green] {', '.join(state.files_written[-5:])}")
            if state.files_edited:
                self.console.print(f"[yellow]Edited:[/yellow] {', '.join(state.files_edited[-5:])}")
            if state.commands_run:
                successful_cmds = len(state.commands_run) - len(state.failed_commands)
                self.console.print(f"[cyan]Commands:[/cyan] {successful_cmds}/{len(state.commands_run)} succeeded")

            # Show failure recovery info
            if state.failed_commands or state.failed_edits:
                recovered = len(state.working_patterns)
                failures = len(state.failed_commands) + len(state.failed_edits)
                if recovered > 0:
                    self.console.print(f"[green]Recovery:[/green] {recovered} successful retries after {failures} failures")
                else:
                    self.console.print(f"[yellow]Failures:[/yellow] {failures} (check errors above)")

            if state.errors_encountered:
                self.console.print(f"[red]Errors:[/red] {len(state.errors_encountered)}")

            self.console.print(f"[dim]Turns: {state.turns}, Tokens: {state.total_tokens}[/dim]")

    async def _handle_command(self, cmd: str):
        """Handle slash commands"""
        cmd_lower = cmd.strip().lower()

        if cmd_lower == "/help":
            self.console.print("""
[bold]Available Commands:[/bold]

  [green]/help[/green]      - Show this help
  [green]/status[/green]    - Show agent status
  [green]/clear[/green]     - Clear conversation history
  [green]/model[/green]     - Show/change model
  [green]/auto[/green]      - Toggle auto-approve mode
  [green]/quit[/green]      - Exit

[bold]Usage Examples:[/bold]

  "Create a React todo app with TypeScript"
  "Fix the error in main.py"
  "Run the tests and fix any failures"
  "Debug why the API is returning 500"
  "Refactor this code to use async/await"
  "Add error handling to all functions"
""")

        elif cmd_lower == "/status":
            state = self.agent.state
            self.console.print(f"""
[bold]Agent Status[/bold]

Model: {self.config.model}
Turns: {state.turns}/{self.config.max_turns}
Tokens: {state.total_tokens}
Files Read: {len(state.files_read)}
Files Written: {len(state.files_written)}
Files Edited: {len(state.files_edited)}
Commands Run: {len(state.commands_run)}
Errors: {len(state.errors_encountered)}
Permission Mode: {self.config.permission_mode}
""")

        elif cmd_lower == "/clear":
            self.agent.reset()
            self.console.print("[green]Conversation cleared[/green]")

        elif cmd_lower.startswith("/model"):
            parts = cmd_lower.split()
            if len(parts) > 1 and parts[1] in ["haiku", "sonnet", "opus"]:
                self.config.model = parts[1]
                self.agent.model = self.agent._get_model_name()
                self.console.print(f"[green]Model changed to {parts[1]}[/green]")
            else:
                self.console.print(f"Current model: {self.config.model}")
                self.console.print("Available: haiku, sonnet, opus")

        elif cmd_lower == "/auto":
            if self.config.permission_mode == "auto":
                self.config.permission_mode = "ask"
                self.console.print("[yellow]Auto-approve disabled[/yellow]")
            else:
                self.config.permission_mode = "auto"
                self.console.print("[green]Auto-approve enabled[/green]")

        else:
            self.console.print(f"[yellow]Unknown command: {cmd}[/yellow]")
