"""
BharatBuild CLI Headless Mode

Non-interactive execution for automation:
  bharatbuild -p "query"              Execute query and exit
  bharatbuild --print "query"         Same as -p
  bharatbuild -p --output-format json Output as JSON
  cat file | bharatbuild -p "query"   Process piped input
"""

import sys
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Generator
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from rich.console import Console


class OutputFormat(str, Enum):
    """Output format options"""
    TEXT = "text"
    JSON = "json"
    STREAM_JSON = "stream-json"


class InputFormat(str, Enum):
    """Input format options"""
    TEXT = "text"
    STREAM_JSON = "stream-json"


@dataclass
class HeadlessConfig:
    """Headless mode configuration"""
    output_format: OutputFormat = OutputFormat.TEXT
    input_format: InputFormat = InputFormat.TEXT
    max_turns: int = 10
    verbose: bool = False
    include_partial: bool = False
    json_schema: Optional[str] = None
    allowed_tools: List[str] = None
    disallowed_tools: List[str] = None
    system_prompt: Optional[str] = None
    append_system_prompt: Optional[str] = None


@dataclass
class HeadlessResult:
    """Result from headless execution"""
    success: bool
    output: str
    session_id: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    turns: int = 1
    error: Optional[str] = None


class HeadlessModeManager:
    """
    Manages headless/non-interactive mode for BharatBuild CLI.

    Features:
    - Single query execution (-p flag)
    - Multiple output formats (text, json, stream-json)
    - Piped input support
    - Tool allowlists/denylists
    - Multi-turn conversations
    - Schema validation

    Usage:
        manager = HeadlessModeManager()

        # Execute single query
        result = manager.execute("Explain this code")

        # With options
        result = manager.execute(
            query="Fix the bug",
            output_format=OutputFormat.JSON,
            max_turns=5
        )
    """

    def __init__(
        self,
        console: Console = None,
        config: HeadlessConfig = None
    ):
        self.console = console or Console()
        self.config = config or HeadlessConfig()

        # Session state
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._conversation: List[Dict[str, Any]] = []
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    # ==================== Execution ====================

    def execute(
        self,
        query: str,
        output_format: OutputFormat = None,
        max_turns: int = None,
        **kwargs
    ) -> HeadlessResult:
        """Execute a query in headless mode"""
        start_time = time.time()

        # Apply config overrides
        output_format = output_format or self.config.output_format
        max_turns = max_turns or self.config.max_turns

        try:
            # Check for piped input
            piped_content = self._get_piped_input()
            if piped_content:
                query = f"{query}\n\n```\n{piped_content}\n```"

            # Execute query (this would call the actual AI backend)
            response = self._execute_query(query, max_turns)

            # Calculate metrics
            duration_ms = int((time.time() - start_time) * 1000)

            result = HeadlessResult(
                success=True,
                output=response,
                session_id=self._session_id,
                model=kwargs.get("model", "claude-3-sonnet"),
                input_tokens=self._total_input_tokens,
                output_tokens=self._total_output_tokens,
                cost_usd=self._calculate_cost(),
                duration_ms=duration_ms,
                turns=len(self._conversation) // 2
            )

            # Output based on format
            self._output_result(result, output_format)

            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            result = HeadlessResult(
                success=False,
                output="",
                session_id=self._session_id,
                model=kwargs.get("model", "claude-3-sonnet"),
                duration_ms=duration_ms,
                error=str(e)
            )

            self._output_result(result, output_format)

            return result

    def execute_stream(
        self,
        query: str,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """Execute query with streaming output"""
        start_time = time.time()

        try:
            # Check for piped input
            piped_content = self._get_piped_input()
            if piped_content:
                query = f"{query}\n\n```\n{piped_content}\n```"

            # Stream events (this would stream from actual AI backend)
            for event in self._stream_query(query):
                yield event

            # Final event
            duration_ms = int((time.time() - start_time) * 1000)
            yield {
                "type": "result",
                "session_id": self._session_id,
                "input_tokens": self._total_input_tokens,
                "output_tokens": self._total_output_tokens,
                "cost_usd": self._calculate_cost(),
                "duration_ms": duration_ms
            }

        except Exception as e:
            yield {
                "type": "error",
                "error": str(e)
            }

    def _execute_query(self, query: str, max_turns: int) -> str:
        """Execute query (placeholder for actual implementation)"""
        # This would integrate with the actual AI backend
        # For now, return a placeholder

        # Add to conversation
        self._conversation.append({"role": "user", "content": query})

        # Simulate token counting
        self._total_input_tokens += len(query.split()) * 2

        # In production, this would call the AI API
        response = f"[Headless mode response to: {query[:50]}...]"

        self._conversation.append({"role": "assistant", "content": response})
        self._total_output_tokens += len(response.split()) * 2

        return response

    def _stream_query(self, query: str) -> Generator[Dict[str, Any], None, None]:
        """Stream query response (placeholder)"""
        # Start event
        yield {"type": "start", "session_id": self._session_id}

        # Add to conversation
        self._conversation.append({"role": "user", "content": query})
        self._total_input_tokens += len(query.split()) * 2

        # Simulate streaming response
        response = f"[Headless mode streaming response to: {query[:50]}...]"
        words = response.split()

        for i, word in enumerate(words):
            yield {
                "type": "content",
                "content": word + " ",
                "index": i
            }
            self._total_output_tokens += 2

        self._conversation.append({"role": "assistant", "content": response})

    def _get_piped_input(self) -> Optional[str]:
        """Get piped input if available"""
        if not sys.stdin.isatty():
            try:
                return sys.stdin.read()
            except Exception:
                pass
        return None

    def _calculate_cost(self) -> float:
        """Calculate estimated cost"""
        # Simplified cost calculation
        input_cost = self._total_input_tokens * 0.000003  # $3/M tokens
        output_cost = self._total_output_tokens * 0.000015  # $15/M tokens
        return input_cost + output_cost

    # ==================== Output ====================

    def _output_result(self, result: HeadlessResult, format: OutputFormat):
        """Output result in specified format"""
        if format == OutputFormat.JSON:
            self._output_json(result)
        elif format == OutputFormat.STREAM_JSON:
            self._output_stream_json(result)
        else:
            self._output_text(result)

    def _output_text(self, result: HeadlessResult):
        """Output as plain text"""
        if result.success:
            print(result.output)
        else:
            print(f"Error: {result.error}", file=sys.stderr)

        if self.config.verbose:
            print(f"\n---", file=sys.stderr)
            print(f"Session: {result.session_id}", file=sys.stderr)
            print(f"Tokens: {result.input_tokens} in / {result.output_tokens} out", file=sys.stderr)
            print(f"Cost: ${result.cost_usd:.6f}", file=sys.stderr)
            print(f"Duration: {result.duration_ms}ms", file=sys.stderr)

    def _output_json(self, result: HeadlessResult):
        """Output as JSON"""
        output = {
            "success": result.success,
            "output": result.output,
            "session_id": result.session_id,
            "model": result.model,
            "usage": {
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "total_tokens": result.input_tokens + result.output_tokens
            },
            "cost_usd": result.cost_usd,
            "duration_ms": result.duration_ms,
            "turns": result.turns
        }

        if result.error:
            output["error"] = result.error

        print(json.dumps(output, indent=2))

    def _output_stream_json(self, result: HeadlessResult):
        """Output as newline-delimited JSON (JSONL)"""
        # Content event
        print(json.dumps({
            "type": "content",
            "content": result.output
        }))

        # Result event
        print(json.dumps({
            "type": "result",
            "success": result.success,
            "session_id": result.session_id,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cost_usd": result.cost_usd,
            "duration_ms": result.duration_ms
        }))

    # ==================== Multi-turn ====================

    def continue_conversation(self, query: str) -> HeadlessResult:
        """Continue existing conversation"""
        return self.execute(query)

    def reset_conversation(self):
        """Reset conversation state"""
        self._conversation = []
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ==================== Schema Validation ====================

    def validate_output(self, output: str, schema_path: str) -> bool:
        """Validate JSON output against schema"""
        try:
            import jsonschema

            # Load schema
            with open(schema_path) as f:
                schema = json.load(f)

            # Parse output as JSON
            data = json.loads(output)

            # Validate
            jsonschema.validate(data, schema)
            return True

        except json.JSONDecodeError as e:
            if self.config.verbose:
                print(f"Invalid JSON output: {e}", file=sys.stderr)
            return False

        except Exception as e:
            if self.config.verbose:
                print(f"Schema validation failed: {e}", file=sys.stderr)
            return False


class CLIArgumentParser:
    """
    Parse CLI arguments for headless mode.

    Supports:
    - -p, --print: Non-interactive mode
    - -c, --continue: Continue conversation
    - -r, --resume: Resume session
    - --output-format: text, json, stream-json
    - --max-turns: Limit agentic turns
    - --model: Specify model
    - --verbose: Enable verbose output
    - --system-prompt: Custom system prompt
    - --allowed-tools: Tool allowlist
    - --disallowed-tools: Tool denylist
    - --dangerously-skip-permissions: Skip prompts
    """

    def __init__(self, args: List[str] = None):
        self.args = args or sys.argv[1:]
        self.parsed = self._parse()

    def _parse(self) -> Dict[str, Any]:
        """Parse command line arguments"""
        result = {
            "headless": False,
            "continue": False,
            "resume": None,
            "query": None,
            "output_format": "text",
            "input_format": "text",
            "max_turns": 10,
            "model": None,
            "verbose": False,
            "system_prompt": None,
            "system_prompt_file": None,
            "append_system_prompt": None,
            "allowed_tools": [],
            "disallowed_tools": [],
            "skip_permissions": False,
            "json_schema": None,
            "include_partial": False,
            "add_dirs": [],
            "agents": None,
            "permission_mode": None
        }

        i = 0
        while i < len(self.args):
            arg = self.args[i]

            # Headless mode
            if arg in ["-p", "--print"]:
                result["headless"] = True
                # Next arg might be query
                if i + 1 < len(self.args) and not self.args[i + 1].startswith("-"):
                    i += 1
                    result["query"] = self.args[i]

            # Continue conversation
            elif arg in ["-c", "--continue"]:
                result["continue"] = True

            # Resume session
            elif arg in ["-r", "--resume"]:
                if i + 1 < len(self.args):
                    i += 1
                    result["resume"] = self.args[i]

            # Output format
            elif arg == "--output-format":
                if i + 1 < len(self.args):
                    i += 1
                    result["output_format"] = self.args[i]

            # Input format
            elif arg == "--input-format":
                if i + 1 < len(self.args):
                    i += 1
                    result["input_format"] = self.args[i]

            # Max turns
            elif arg == "--max-turns":
                if i + 1 < len(self.args):
                    i += 1
                    result["max_turns"] = int(self.args[i])

            # Model
            elif arg == "--model":
                if i + 1 < len(self.args):
                    i += 1
                    result["model"] = self.args[i]

            # Verbose
            elif arg in ["-v", "--verbose"]:
                result["verbose"] = True

            # System prompt
            elif arg == "--system-prompt":
                if i + 1 < len(self.args):
                    i += 1
                    result["system_prompt"] = self.args[i]

            # System prompt file
            elif arg == "--system-prompt-file":
                if i + 1 < len(self.args):
                    i += 1
                    result["system_prompt_file"] = self.args[i]

            # Append system prompt
            elif arg == "--append-system-prompt":
                if i + 1 < len(self.args):
                    i += 1
                    result["append_system_prompt"] = self.args[i]

            # Allowed tools
            elif arg == "--allowedTools":
                if i + 1 < len(self.args):
                    i += 1
                    result["allowed_tools"] = self.args[i].split(",")

            # Disallowed tools
            elif arg == "--disallowedTools":
                if i + 1 < len(self.args):
                    i += 1
                    result["disallowed_tools"] = self.args[i].split(",")

            # Skip permissions
            elif arg == "--dangerously-skip-permissions":
                result["skip_permissions"] = True

            # JSON schema
            elif arg == "--json-schema":
                if i + 1 < len(self.args):
                    i += 1
                    result["json_schema"] = self.args[i]

            # Include partial messages
            elif arg == "--include-partial-messages":
                result["include_partial"] = True

            # Add directories
            elif arg == "--add-dir":
                if i + 1 < len(self.args):
                    i += 1
                    result["add_dirs"].append(self.args[i])

            # Agents JSON
            elif arg == "--agents":
                if i + 1 < len(self.args):
                    i += 1
                    result["agents"] = self.args[i]

            # Permission mode
            elif arg == "--permission-mode":
                if i + 1 < len(self.args):
                    i += 1
                    result["permission_mode"] = self.args[i]

            # Positional argument (query)
            elif not arg.startswith("-") and not result["query"]:
                result["query"] = arg

            i += 1

        return result

    def is_headless(self) -> bool:
        """Check if running in headless mode"""
        return self.parsed["headless"]

    def get_query(self) -> Optional[str]:
        """Get the query to execute"""
        return self.parsed["query"]

    def get_config(self) -> HeadlessConfig:
        """Get headless configuration from parsed args"""
        return HeadlessConfig(
            output_format=OutputFormat(self.parsed["output_format"]),
            input_format=InputFormat(self.parsed["input_format"]),
            max_turns=self.parsed["max_turns"],
            verbose=self.parsed["verbose"],
            include_partial=self.parsed["include_partial"],
            json_schema=self.parsed["json_schema"],
            allowed_tools=self.parsed["allowed_tools"],
            disallowed_tools=self.parsed["disallowed_tools"],
            system_prompt=self.parsed["system_prompt"],
            append_system_prompt=self.parsed["append_system_prompt"]
        )

    def to_dict(self) -> Dict[str, Any]:
        """Get all parsed arguments as dict"""
        return self.parsed


# Factory function
def get_headless_manager(
    console: Console = None,
    config: HeadlessConfig = None
) -> HeadlessModeManager:
    """Get headless mode manager instance"""
    return HeadlessModeManager(
        console=console,
        config=config
    )


def run_headless(args: List[str] = None) -> int:
    """Run in headless mode, return exit code"""
    parser = CLIArgumentParser(args)

    if not parser.is_headless():
        return -1  # Not headless mode

    query = parser.get_query()
    if not query:
        print("Error: No query provided", file=sys.stderr)
        return 1

    config = parser.get_config()
    manager = HeadlessModeManager(config=config)

    result = manager.execute(query, model=parser.parsed.get("model"))

    return 0 if result.success else 1
