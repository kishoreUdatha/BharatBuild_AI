"""
Standalone CLI Mode - Direct Claude API Integration

This module provides a standalone CLI that works directly with Claude API
without requiring the backend server. Similar to how Claude Code works.
"""

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass

from anthropic import AsyncAnthropic

from cli.config import CLIConfig
from cli.tools import ToolExecutor, CommandResult
from cli.renderer import ResponseRenderer

# System prompt for Claude (similar to Claude Code)
SYSTEM_PROMPT = """You are BharatBuild AI, an expert AI assistant that helps developers write code, fix bugs, and build applications.

You have access to the following tools:

1. **Read** - Read file contents
   Usage: <read path="filepath"/>

2. **Write** - Create or overwrite a file
   Usage: <write path="filepath">file content here</write>

3. **Edit** - Edit a file by replacing text
   Usage: <edit path="filepath">
   <old>text to find</old>
   <new>text to replace with</new>
   </edit>

4. **Bash** - Execute shell commands
   Usage: <bash>command here</bash>

5. **Glob** - Find files matching a pattern
   Usage: <glob pattern="**/*.py"/>

6. **Grep** - Search for text in files
   Usage: <grep pattern="search term" path="."/>

When the user asks you to do something:
1. First, understand what files exist and their structure
2. Plan your approach
3. Execute the necessary tool calls
4. Verify your changes work

Important guidelines:
- Always read files before modifying them
- Make minimal, focused changes
- Explain what you're doing
- Handle errors gracefully
- Use relative paths from the working directory

Your responses should include tool calls wrapped in XML tags as shown above.
After executing tools, provide a summary of what was done.

Working directory: {working_dir}
"""


@dataclass
class ToolCall:
    """Represents a parsed tool call"""
    tool: str
    params: Dict[str, str]
    content: str = ""


class StandaloneCLI:
    """Standalone CLI that works directly with Claude API"""

    def __init__(self, config: CLIConfig, console, renderer: ResponseRenderer):
        self.config = config
        self.console = console
        self.renderer = renderer
        self.tool_executor = ToolExecutor(config, console)

        # Initialize Anthropic client
        api_key = config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Please set it in environment or config."
            )

        self.client = AsyncAnthropic(api_key=api_key)
        self.model = self._get_model_name()
        self.messages: List[Dict[str, str]] = []
        self.max_turns = config.max_turns

    def _get_model_name(self) -> str:
        """Get full model name from config"""
        model_map = {
            "haiku": "claude-3-5-haiku-20241022",
            "sonnet": "claude-3-5-sonnet-20241022",
        }
        return model_map.get(self.config.model, self.config.model)

    def _get_system_prompt(self) -> str:
        """Generate system prompt with context"""
        return SYSTEM_PROMPT.format(
            working_dir=self.config.working_directory
        )

    async def process_prompt(self, prompt: str) -> AsyncGenerator[str, None]:
        """Process a prompt and yield streaming response"""
        # Add user message
        self.messages.append({"role": "user", "content": prompt})

        turns = 0
        while turns < self.max_turns:
            turns += 1

            # Stream response from Claude
            response_text = ""

            async with self.client.messages.stream(
                model=self.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=self._get_system_prompt(),
                messages=self.messages
            ) as stream:
                async for text in stream.text_stream:
                    response_text += text
                    yield text

            # Add assistant message
            self.messages.append({"role": "assistant", "content": response_text})

            # Parse and execute tool calls
            tool_calls = self._parse_tool_calls(response_text)

            if not tool_calls:
                # No tool calls, we're done
                break

            # Execute tool calls
            tool_results = await self._execute_tool_calls(tool_calls)

            if not tool_results:
                break

            # Add tool results as user message for next turn
            results_message = "\n\nTool execution results:\n" + "\n".join(tool_results)
            self.messages.append({"role": "user", "content": results_message})

            yield f"\n\n[Executing tools...]\n"

        # Return final message info
        final_message = await stream.get_final_message()
        yield f"\n\n[Tokens: {final_message.usage.input_tokens} in, {final_message.usage.output_tokens} out]"

    def _parse_tool_calls(self, response: str) -> List[ToolCall]:
        """Parse tool calls from response text"""
        tool_calls = []

        # Parse <read path="..."/>
        for match in re.finditer(r'<read\s+path="([^"]+)"\s*/>', response):
            tool_calls.append(ToolCall(tool="read", params={"path": match.group(1)}))

        # Parse <write path="...">content</write>
        for match in re.finditer(r'<write\s+path="([^"]+)">(.*?)</write>', response, re.DOTALL):
            tool_calls.append(ToolCall(
                tool="write",
                params={"path": match.group(1)},
                content=match.group(2).strip()
            ))

        # Parse <edit path="..."><old>...</old><new>...</new></edit>
        for match in re.finditer(
            r'<edit\s+path="([^"]+)">\s*<old>(.*?)</old>\s*<new>(.*?)</new>\s*</edit>',
            response, re.DOTALL
        ):
            tool_calls.append(ToolCall(
                tool="edit",
                params={
                    "path": match.group(1),
                    "old": match.group(2).strip(),
                    "new": match.group(3).strip()
                }
            ))

        # Parse <bash>command</bash>
        for match in re.finditer(r'<bash>(.*?)</bash>', response, re.DOTALL):
            tool_calls.append(ToolCall(
                tool="bash",
                params={},
                content=match.group(1).strip()
            ))

        # Parse <glob pattern="..."/>
        for match in re.finditer(r'<glob\s+pattern="([^"]+)"\s*/>', response):
            tool_calls.append(ToolCall(tool="glob", params={"pattern": match.group(1)}))

        # Parse <grep pattern="..." path="..."/>
        for match in re.finditer(r'<grep\s+pattern="([^"]+)"\s+path="([^"]+)"\s*/>', response):
            tool_calls.append(ToolCall(
                tool="grep",
                params={"pattern": match.group(1), "path": match.group(2)}
            ))

        return tool_calls

    async def _execute_tool_calls(self, tool_calls: List[ToolCall]) -> List[str]:
        """Execute tool calls and return results"""
        results = []

        for call in tool_calls:
            try:
                result = await self._execute_single_tool(call)
                results.append(f"✓ {call.tool}: {result[:500]}")
                self.console.print(f"[green]✓ {call.tool}[/green]: {call.params}")
            except Exception as e:
                results.append(f"✗ {call.tool}: Error - {str(e)}")
                self.console.print(f"[red]✗ {call.tool}[/red]: {str(e)}")

        return results

    async def _execute_single_tool(self, call: ToolCall) -> str:
        """Execute a single tool call"""
        if call.tool == "read":
            path = call.params["path"]

            # Permission check
            if self.config.permission_mode == "ask":
                from rich.prompt import Confirm
                if not Confirm.ask(f"[yellow]Read {path}?[/yellow]"):
                    return "Skipped by user"

            content = await self.tool_executor.read_file(path)
            return content[:1000] + "..." if len(content or "") > 1000 else (content or "File not found")

        elif call.tool == "write":
            path = call.params["path"]
            content = call.content

            # Permission check
            if self.config.permission_mode == "ask":
                from rich.prompt import Confirm
                self.console.print(f"\n[cyan]File: {path}[/cyan]")
                self.console.print(f"[dim]Content preview: {content[:200]}...[/dim]")
                if not Confirm.ask(f"[yellow]Write file?[/yellow]"):
                    return "Skipped by user"

            await self.tool_executor.write_file(path, content)
            self.renderer.render_file(path, content)
            return f"Written {len(content)} bytes to {path}"

        elif call.tool == "edit":
            path = call.params["path"]
            old = call.params["old"]
            new = call.params["new"]

            # Permission check
            if self.config.permission_mode == "ask":
                from rich.prompt import Confirm
                self.console.print(f"\n[cyan]Edit: {path}[/cyan]")
                self.console.print(f"[red]- {old[:100]}...[/red]")
                self.console.print(f"[green]+ {new[:100]}...[/green]")
                if not Confirm.ask(f"[yellow]Apply edit?[/yellow]"):
                    return "Skipped by user"

            await self.tool_executor.edit_file(path, old, new)
            return f"Edited {path}"

        elif call.tool == "bash":
            command = call.content

            # Permission check
            if self.config.permission_mode == "ask":
                from rich.prompt import Confirm
                self.console.print(f"\n[cyan]Command: {command}[/cyan]")
                if not Confirm.ask(f"[yellow]Execute?[/yellow]"):
                    return "Skipped by user"

            result = await self.tool_executor.execute_bash(command)
            self.renderer.render_command_result(command, result)

            output = result.stdout or result.stderr
            return output[:500] if output else f"Exit code: {result.exit_code}"

        elif call.tool == "glob":
            pattern = call.params["pattern"]
            files = await self.tool_executor.glob_files(pattern)
            return "\n".join(files[:50])

        elif call.tool == "grep":
            pattern = call.params["pattern"]
            path = call.params.get("path", ".")
            results = await self.tool_executor.grep_files(pattern, path)
            return "\n".join(
                f"{r['file']}:{r['line']}: {r['content']}"
                for r in results[:20]
            )

        return f"Unknown tool: {call.tool}"

    def clear_history(self):
        """Clear conversation history"""
        self.messages.clear()


class StandaloneApp:
    """Standalone application wrapper"""

    def __init__(self, config: CLIConfig):
        from rich.console import Console
        self.config = config
        self.console = Console()
        self.renderer = ResponseRenderer(self.console, config)
        self.cli = StandaloneCLI(config, self.console, self.renderer)

    async def run_interactive(self):
        """Run interactive mode"""
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

        self.console.clear()
        self._print_header()

        session = PromptSession(
            history=FileHistory(self.config.history_file),
            auto_suggest=AutoSuggestFromHistory()
        )

        while True:
            try:
                prompt = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: session.prompt("❯ ")
                )

                if not prompt.strip():
                    continue

                if prompt.strip().lower() in ["/quit", "/exit", "/q"]:
                    break

                if prompt.startswith("/"):
                    await self._handle_command(prompt)
                    continue

                # Process prompt
                async for chunk in self.cli.process_prompt(prompt):
                    self.console.print(chunk, end="")

                self.console.print()

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Ctrl+C to cancel, /quit to exit[/yellow]")
            except EOFError:
                break

        self.console.print("\n[cyan]Goodbye! 👋[/cyan]")

    async def run_single(self, prompt: str):
        """Run single prompt"""
        async for chunk in self.cli.process_prompt(prompt):
            print(chunk, end="", flush=True)
        print()

    def _print_header(self):
        """Print header"""
        from rich.panel import Panel
        header = Panel(
            "[bold cyan]BharatBuild AI[/bold cyan] - Standalone Mode\n"
            "[dim]Direct Claude API integration (no server required)[/dim]",
            border_style="cyan"
        )
        self.console.print(header)
        self.console.print(f"📁 {self.config.working_directory}")
        self.console.print(f"🤖 {self.config.model}\n")

    async def _handle_command(self, cmd: str):
        """Handle slash commands"""
        cmd = cmd.strip().lower()

        if cmd == "/help":
            self.console.print("""
[bold]Available Commands:[/bold]
  /help    - Show this help
  /clear   - Clear conversation
  /model   - Show/change model
  /quit    - Exit
            """)
        elif cmd == "/clear":
            self.cli.clear_history()
            self.console.print("[green]Conversation cleared[/green]")
        elif cmd.startswith("/model"):
            parts = cmd.split()
            if len(parts) > 1 and parts[1] in ["haiku", "sonnet"]:
                self.config.model = parts[1]
                self.cli.model = self.cli._get_model_name()
                self.console.print(f"[green]Model changed to {parts[1]}[/green]")
            else:
                self.console.print(f"Current model: {self.config.model}")
        else:
            self.console.print(f"[yellow]Unknown command: {cmd}[/yellow]")
