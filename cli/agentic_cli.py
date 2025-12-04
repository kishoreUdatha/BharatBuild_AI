"""
BharatBuild AI CLI - Claude Code Style
=======================================

A professional CLI that feels exactly like Claude Code:
- Real-time streaming text output
- Beautiful tool call visualization with spinners
- Permission prompts before file/bash operations
- Keyboard shortcuts (Ctrl+C to cancel)
- Professional terminal UI

All conversations go through BharatBuild backend API.
"""

import asyncio
import os
import subprocess
import re
import time
import json
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

import httpx
from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich.box import ROUNDED, SIMPLE
from rich.style import Style
from rich.padding import Padding
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.formatted_text import HTML

from cli.config import CLIConfig


# =============================================================================
# Colors and Styles (Claude Code inspired)
# =============================================================================

COLORS = {
    "primary": "#7C3AED",      # Purple - main accent
    "secondary": "#06B6D4",    # Cyan - secondary accent
    "success": "#10B981",      # Green - success
    "warning": "#F59E0B",      # Yellow - warning
    "error": "#EF4444",        # Red - error
    "muted": "#6B7280",        # Gray - muted text
    "text": "#E5E7EB",         # Light gray - main text
}

# Prompt toolkit style
PT_STYLE = PTStyle.from_dict({
    'prompt': '#7C3AED bold',
    'input': '#E5E7EB',
})


@dataclass
class ToolResult:
    """Result of a tool execution"""
    tool_use_id: str
    tool_name: str
    success: bool
    output: str
    error: Optional[str] = None
    duration: float = 0.0


class ClaudeCodeCLI:
    """
    A CLI that feels exactly like Claude Code.
    """

    def __init__(self, config: CLIConfig, console: Console = None):
        self.config = config
        self.console = console or Console(force_terminal=True, color_system="truecolor")
        self.working_dir = Path(config.working_directory).resolve()

        # API configuration
        self.api_base_url = config.api_base_url.rstrip('/')
        self.auth_token = config.auth_token

        # Model selection
        self.model = config.model or "sonnet"

        # Conversation state
        self.messages: List[Dict] = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.tool_calls_count = 0

        # Permission mode
        self.permission_mode = config.permission_mode or "ask"

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }

    # =========================================================================
    # Beautiful Display Methods (Claude Code Style)
    # =========================================================================

    def _print_welcome(self):
        """Print welcome banner"""
        self.console.print()

        # Simple, clean header like Claude Code
        title = Text()
        title.append("BharatBuild AI", style="bold #7C3AED")
        title.append(" v1.0", style="dim")
        self.console.print(title)

        # Working directory
        self.console.print(f"[dim]cwd:[/dim] {self.working_dir}", style="dim")
        self.console.print()

        # Tips
        tips = Text()
        tips.append("Tips: ", style="dim")
        tips.append("Press ", style="dim")
        tips.append("Ctrl+C", style="bold dim")
        tips.append(" to cancel, ", style="dim")
        tips.append("/help", style="bold dim")
        tips.append(" for commands", style="dim")
        self.console.print(tips)
        self.console.print()

    def _print_tool_start(self, tool_name: str, tool_input: Dict) -> Live:
        """Print tool call start with spinner"""
        # Tool icons
        icons = {
            "read_file": "Read",
            "write_file": "Write",
            "edit_file": "Edit",
            "bash": "Bash",
            "glob": "Glob",
            "grep": "Grep",
            "list_directory": "List"
        }

        icon = icons.get(tool_name, "Tool")

        # Build display
        tool_text = Text()
        tool_text.append(f"  {icon}", style="bold #7C3AED")

        # Show key parameter
        if tool_name == "read_file":
            tool_text.append(f" {tool_input.get('path', '')}", style="#06B6D4")
        elif tool_name == "write_file":
            tool_text.append(f" {tool_input.get('path', '')}", style="#06B6D4")
        elif tool_name == "edit_file":
            tool_text.append(f" {tool_input.get('path', '')}", style="#06B6D4")
        elif tool_name == "bash":
            cmd = tool_input.get('command', '')
            if len(cmd) > 60:
                cmd = cmd[:57] + "..."
            tool_text.append(f" {cmd}", style="#06B6D4")
        elif tool_name == "glob":
            tool_text.append(f" {tool_input.get('pattern', '')}", style="#06B6D4")
        elif tool_name == "grep":
            tool_text.append(f" {tool_input.get('pattern', '')}", style="#06B6D4")
        elif tool_name == "list_directory":
            tool_text.append(f" {tool_input.get('path', '.')}", style="#06B6D4")

        self.console.print(tool_text)
        return None

    def _print_tool_result(self, result: ToolResult):
        """Print tool result"""
        if result.success:
            # Show success with duration
            status = Text()
            status.append("    ", style="dim")
            status.append("Done", style="#10B981")
            status.append(f" ({result.duration:.1f}s)", style="dim")
            self.console.print(status)

            # Show output preview for certain tools
            if result.tool_name in ["read_file", "glob", "grep", "list_directory"]:
                output = result.output
                lines = output.split('\n')
                if len(lines) > 5:
                    preview = '\n'.join(lines[:5])
                    self.console.print(f"[dim]    ... {len(lines)} lines[/dim]")
        else:
            # Show error
            status = Text()
            status.append("    ", style="dim")
            status.append("Error: ", style="#EF4444 bold")
            status.append(str(result.error)[:50], style="#EF4444")
            self.console.print(status)

    def _stream_text(self, text: str):
        """Stream text character by character (simulated for non-streaming API)"""
        # For markdown, just print it nicely
        if text.strip():
            self.console.print()
            try:
                self.console.print(Markdown(text))
            except:
                self.console.print(text)

    def _print_thinking(self) -> Live:
        """Show thinking spinner"""
        spinner = Spinner("dots", text="Thinking...", style="#7C3AED")
        live = Live(spinner, console=self.console, refresh_per_second=10)
        live.start()
        return live

    def _print_cost_summary(self):
        """Print token usage and cost"""
        self.console.print()

        summary = Text()
        summary.append("  ", style="dim")
        summary.append(f"{self.total_input_tokens:,}", style="dim bold")
        summary.append(" input ", style="dim")
        summary.append(f"{self.total_output_tokens:,}", style="dim bold")
        summary.append(" output tokens", style="dim")

        if self.tool_calls_count > 0:
            summary.append(" | ", style="dim")
            summary.append(f"{self.tool_calls_count}", style="dim bold")
            summary.append(" tool calls", style="dim")

        self.console.print(summary)

    # =========================================================================
    # Permission Prompts (Claude Code Style)
    # =========================================================================

    async def _ask_permission(self, tool_name: str, tool_input: Dict) -> bool:
        """Ask for permission before executing a tool"""
        if self.permission_mode == "auto":
            return True
        if self.permission_mode == "deny":
            return False

        # Show what will be done
        self.console.print()

        box = Table(box=ROUNDED, show_header=False, padding=(0, 1))
        box.add_column(style="dim")

        if tool_name == "write_file":
            box.add_row(Text("Create/overwrite file:", style="bold #F59E0B"))
            box.add_row(Text(f"  {tool_input.get('path', '')}", style="#06B6D4"))
            content = tool_input.get('content', '')
            box.add_row(Text(f"  ({len(content)} bytes)", style="dim"))

        elif tool_name == "edit_file":
            box.add_row(Text("Edit file:", style="bold #F59E0B"))
            box.add_row(Text(f"  {tool_input.get('path', '')}", style="#06B6D4"))

        elif tool_name == "bash":
            box.add_row(Text("Run command:", style="bold #F59E0B"))
            cmd = tool_input.get('command', '')
            box.add_row(Text(f"  {cmd}", style="#06B6D4"))

        self.console.print(box)

        # Ask for permission
        self.console.print()
        response = self.console.input("[bold #7C3AED]Allow?[/bold #7C3AED] [dim](y/n)[/dim] ")

        return response.lower() in ['y', 'yes', '']

    # =========================================================================
    # Tool Implementations
    # =========================================================================

    async def _execute_tool(self, tool_use_id: str, tool_name: str, tool_input: Dict) -> ToolResult:
        """Execute a tool locally"""
        start_time = time.time()

        try:
            # Check permission for destructive operations
            if tool_name in ["write_file", "edit_file", "bash"]:
                if not await self._ask_permission(tool_name, tool_input):
                    return ToolResult(
                        tool_use_id=tool_use_id,
                        tool_name=tool_name,
                        success=False,
                        output="",
                        error="Permission denied by user"
                    )

            # Execute the tool
            if tool_name == "read_file":
                result = await self._tool_read_file(tool_input["path"])
            elif tool_name == "write_file":
                result = await self._tool_write_file(tool_input["path"], tool_input["content"])
            elif tool_name == "edit_file":
                result = await self._tool_edit_file(
                    tool_input["path"],
                    tool_input["old_string"],
                    tool_input["new_string"]
                )
            elif tool_name == "bash":
                result = await self._tool_bash(
                    tool_input["command"],
                    tool_input.get("timeout", 60)
                )
            elif tool_name == "glob":
                result = await self._tool_glob(tool_input["pattern"])
            elif tool_name == "grep":
                result = await self._tool_grep(
                    tool_input["pattern"],
                    tool_input.get("path", "."),
                    tool_input.get("include", "*")
                )
            elif tool_name == "list_directory":
                result = await self._tool_list_directory(tool_input.get("path", "."))
            else:
                return ToolResult(
                    tool_use_id=tool_use_id,
                    tool_name=tool_name,
                    success=False,
                    output="",
                    error=f"Unknown tool: {tool_name}"
                )

            duration = time.time() - start_time
            return ToolResult(
                tool_use_id=tool_use_id,
                tool_name=tool_name,
                success=True,
                output=result,
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            return ToolResult(
                tool_use_id=tool_use_id,
                tool_name=tool_name,
                success=False,
                output="",
                error=str(e),
                duration=duration
            )

    async def _tool_read_file(self, path: str) -> str:
        """Read file contents"""
        file_path = self.working_dir / path
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not file_path.is_file():
            raise ValueError(f"Not a file: {path}")

        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        numbered = [f"{i:4d} | {line}" for i, line in enumerate(lines, 1)]
        return '\n'.join(numbered)

    async def _tool_write_file(self, path: str, content: str) -> str:
        """Write file contents"""
        file_path = self.working_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        return f"Created {path} ({len(content)} bytes)"

    async def _tool_edit_file(self, path: str, old_string: str, new_string: str) -> str:
        """Edit file by replacing string"""
        file_path = self.working_dir / path
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        content = file_path.read_text(encoding='utf-8')
        if old_string not in content:
            raise ValueError("String not found in file")

        count = content.count(old_string)
        new_content = content.replace(old_string, new_string, 1)
        file_path.write_text(new_content, encoding='utf-8')
        return f"Edited {path} ({count} replacement)"

    async def _tool_bash(self, command: str, timeout: int = 60) -> str:
        """Execute bash command"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.working_dir)
            )

            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            output += f"\n[exit code: {result.returncode}]"
            return output.strip()

        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Command timed out after {timeout}s")

    async def _tool_glob(self, pattern: str) -> str:
        """Find files matching pattern"""
        matches = sorted(list(self.working_dir.glob(pattern)))[:100]
        if not matches:
            return f"No files found matching: {pattern}"

        results = []
        for m in matches:
            rel_path = m.relative_to(self.working_dir)
            if m.is_dir():
                results.append(f"[dir]  {rel_path}/")
            else:
                size = m.stat().st_size
                results.append(f"[file] {rel_path} ({size}b)")
        return '\n'.join(results)

    async def _tool_grep(self, pattern: str, path: str = ".", include: str = "*") -> str:
        """Search for pattern in files"""
        search_path = self.working_dir / path
        results = []

        files = [search_path] if search_path.is_file() else list(search_path.rglob(include))

        for file_path in files[:50]:
            if not file_path.is_file() or '.git' in str(file_path):
                continue
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                for i, line in enumerate(content.split('\n'), 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        rel_path = file_path.relative_to(self.working_dir)
                        results.append(f"{rel_path}:{i}: {line.strip()[:80]}")
                        if len(results) >= 50:
                            break
            except:
                continue
            if len(results) >= 50:
                break

        return '\n'.join(results) if results else f"No matches for: {pattern}"

    async def _tool_list_directory(self, path: str = ".") -> str:
        """List directory contents"""
        dir_path = self.working_dir / path
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        if not dir_path.is_dir():
            raise ValueError(f"Not a directory: {path}")

        items = sorted(dir_path.iterdir())
        results = []
        for item in items:
            if item.name.startswith('.'):
                continue
            if item.is_dir():
                results.append(f"[dir]  {item.name}/")
            else:
                results.append(f"[file] {item.name} ({item.stat().st_size}b)")
        return '\n'.join(results) if results else "Empty directory"

    # =========================================================================
    # API Communication
    # =========================================================================

    async def _call_api(self, tool_results: Optional[List[ToolResult]] = None) -> Dict:
        """Call the BharatBuild agentic API"""
        request_data = {
            "messages": self.messages,
            "working_dir": str(self.working_dir),
            "model": self.model,
            "max_tokens": 8192
        }

        if tool_results:
            request_data["tool_results"] = [
                {
                    "tool_use_id": r.tool_use_id,
                    "content": r.output if r.success else f"Error: {r.error}",
                    "is_error": not r.success
                }
                for r in tool_results
            ]

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.api_base_url}/agentic/chat",
                headers=self._get_headers(),
                json=request_data
            )

            if response.status_code == 401:
                raise Exception("Authentication failed. Run: bharatbuild login")
            if response.status_code != 200:
                raise Exception(f"API error ({response.status_code}): {response.text}")

            return response.json()

    # =========================================================================
    # Main Loop
    # =========================================================================

    async def run(self, prompt: str) -> str:
        """Run the agentic loop for a single prompt"""
        self.messages = [{"role": "user", "content": prompt}]

        max_iterations = self.config.max_turns or 20
        iteration = 0
        final_response = ""
        tool_results = None

        while iteration < max_iterations:
            iteration += 1

            # Show thinking spinner
            thinking = self._print_thinking()

            try:
                response = await self._call_api(tool_results)
            except Exception as e:
                thinking.stop()
                self.console.print(f"\n[#EF4444]Error: {e}[/#EF4444]")
                break
            finally:
                thinking.stop()

            # Track tokens
            usage = response.get("usage", {})
            self.total_input_tokens += usage.get("input_tokens", 0)
            self.total_output_tokens += usage.get("output_tokens", 0)

            # Display text response
            if response.get("text"):
                self._stream_text(response["text"])
                final_response += response["text"]

            # Get tool calls
            tool_calls = response.get("tool_calls", [])

            if not tool_calls:
                break

            # Execute tools
            tool_results = []
            self.console.print()  # Spacing

            for tool_call in tool_calls:
                self.tool_calls_count += 1

                # Show tool being called
                self._print_tool_start(tool_call["name"], tool_call["input"])

                # Execute
                result = await self._execute_tool(
                    tool_call["id"],
                    tool_call["name"],
                    tool_call["input"]
                )

                # Show result
                self._print_tool_result(result)
                tool_results.append(result)

            # Update conversation
            assistant_content = []
            if response.get("text"):
                assistant_content.append({"type": "text", "text": response["text"]})
            for tc in tool_calls:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["input"]
                })
            self.messages.append({"role": "assistant", "content": assistant_content})

            if response.get("stop_reason") == "end_turn":
                break

        self._print_cost_summary()
        return final_response

    async def run_interactive(self):
        """Run interactive REPL mode"""
        self._print_welcome()

        # History
        history_file = Path.home() / ".bharatbuild" / "history"
        history_file.parent.mkdir(exist_ok=True)
        session = PromptSession(
            history=FileHistory(str(history_file)),
            style=PT_STYLE
        )

        while True:
            try:
                # Claude Code style prompt
                user_input = await session.prompt_async(
                    HTML('<ansipurple><b>></b></ansipurple> ')
                )

                if not user_input.strip():
                    continue

                # Commands
                cmd = user_input.strip().lower()

                if cmd in ["/quit", "/exit", "/q"]:
                    self.console.print("\n[dim]Goodbye![/dim]")
                    break

                if cmd in ["/clear", "/reset"]:
                    self.messages = []
                    self.total_input_tokens = 0
                    self.total_output_tokens = 0
                    self.tool_calls_count = 0
                    os.system('cls' if os.name == 'nt' else 'clear')
                    self._print_welcome()
                    continue

                if cmd == "/help":
                    self._show_help()
                    continue

                if cmd == "/cost":
                    self._print_cost_summary()
                    continue

                # Run the prompt
                await self.run(user_input)
                self.console.print()

            except KeyboardInterrupt:
                self.console.print("\n[dim]Cancelled[/dim]")
                continue
            except EOFError:
                break

    def _show_help(self):
        """Show help"""
        self.console.print()

        help_text = """[bold #7C3AED]Commands:[/bold #7C3AED]
  [#06B6D4]/help[/#06B6D4]     Show this help
  [#06B6D4]/clear[/#06B6D4]    Clear conversation
  [#06B6D4]/cost[/#06B6D4]     Show token usage
  [#06B6D4]/quit[/#06B6D4]     Exit

[bold #7C3AED]What I can do:[/bold #7C3AED]
  - Read, write, and edit files
  - Run bash commands
  - Search code with grep/glob
  - Debug and fix issues

[bold #7C3AED]Examples:[/bold #7C3AED]
  [dim]"Create a Python hello world"[/dim]
  [dim]"Fix the bug in main.py"[/dim]
  [dim]"Run the tests"[/dim]
  [dim]"What does this code do?"[/dim]
"""
        self.console.print(help_text)


# =============================================================================
# Backwards compatibility alias
# =============================================================================
AgenticCLI = ClaudeCodeCLI


# =============================================================================
# Entry Point
# =============================================================================

async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="BharatBuild AI CLI")
    parser.add_argument("prompt", nargs="?", help="Prompt to execute")
    parser.add_argument("-d", "--directory", default=".", help="Working directory")
    parser.add_argument("-m", "--model", default="sonnet", choices=["haiku", "sonnet"])
    parser.add_argument("--max-turns", type=int, default=20)
    parser.add_argument("--server-url", default="http://localhost:8000/api/v1")

    args = parser.parse_args()

    config = CLIConfig(
        model=args.model,
        working_directory=os.path.abspath(args.directory),
        max_turns=args.max_turns,
        api_base_url=args.server_url
    )

    cli = ClaudeCodeCLI(config)

    if args.prompt:
        await cli.run(args.prompt)
    else:
        await cli.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())
