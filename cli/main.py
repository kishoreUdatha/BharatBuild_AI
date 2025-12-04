#!/usr/bin/env python3
"""
BharatBuild AI CLI - Main Entry Point

Usage:
    bharatbuild                     # Start interactive REPL (server mode)
    bharatbuild --standalone        # Start standalone mode (direct Claude API)
    bharatbuild "create a todo app" # Run single prompt
    bharatbuild -p "prompt"         # Run with prompt flag
    bharatbuild --help              # Show help

Modes:
    Server Mode (default):
        Connects to BharatBuild backend server for orchestrated workflows.
        Requires the backend server to be running.

    Standalone Mode (--standalone):
        Works directly with Claude API, no server required.
        Similar to how Claude Code CLI works.
"""

import argparse
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.config import CLIConfig


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI"""
    parser = argparse.ArgumentParser(
        prog="bharatbuild",
        description="BharatBuild AI - Claude Code Style CLI for AI-driven development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  bharatbuild login                            Login to your account
  bharatbuild logout                           Logout from CLI
  bharatbuild status                           Check login status
  bharatbuild                                  Start interactive mode
  bharatbuild "create a React todo app"        Generate project
  bharatbuild "fix the errors in main.py"      Debug and fix code
  bharatbuild -m sonnet "your request"         Use Claude Sonnet model

How It Works (Claude Code Style):
  BharatBuild CLI works like Claude Code - it can:
  - Read, write, and edit files in your project
  - Execute bash commands (builds, tests, git, etc.)
  - Search code with glob and grep patterns
  - Iterate until the task is complete

  All conversations go through BharatBuild backend API.
  Tools are executed locally on your machine.

Authentication:
  Register on the web portal first, then login via CLI.
  Your requests are processed using the platform's API.

Capabilities:
  - Project Generation    Create complete projects from scratch
  - Code Writing          Write new code, functions, modules
  - Debugging             Find bugs and identify root causes
  - Error Fixing          Analyze and fix compilation errors
  - Build & Run           Compile, build, and run projects
  - Documentation         Generate IEEE documents (60-80 pages)
  - Testing               Write and run tests

Keyboard Shortcuts (Interactive Mode):
  Ctrl+C          Cancel current operation
  Ctrl+L          Clear screen
  Ctrl+R          Search command history
  Tab             Auto-complete commands
  Up/Down         Navigate history

Slash Commands:
  /help           Show available commands
  /clear          Clear conversation
  /model          Change AI model
  /status         Show agent status
  /ieee-auto      Generate college documents
  /quit           Exit
        """
    )

    # Subcommands for auth
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Login command
    login_parser = subparsers.add_parser("login", help="Login to BharatBuild")
    login_parser.add_argument("--token", "-t", help="Login with CLI token from web portal")

    # Logout command
    subparsers.add_parser("logout", help="Logout from BharatBuild")

    # Status command
    subparsers.add_parser("status", help="Show authentication status")

    # Whoami command
    subparsers.add_parser("whoami", help="Show current user info")

    # Positional argument for prompt
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Prompt to execute (starts interactive mode if omitted)"
    )

    # Prompt flag (alternative to positional)
    parser.add_argument(
        "-p", "--prompt",
        dest="prompt_flag",
        help="Prompt to execute"
    )

    # Model selection
    parser.add_argument(
        "-m", "--model",
        choices=["haiku", "sonnet"],
        default="haiku",
        help="Claude model to use (default: haiku)"
    )

    # Output format
    parser.add_argument(
        "--output-format",
        choices=["text", "json", "stream-json"],
        default="text",
        help="Output format (default: text)"
    )

    # Continue session
    parser.add_argument(
        "-c", "--continue",
        dest="continue_session",
        action="store_true",
        help="Continue from last session"
    )

    # Max turns for agentic mode
    parser.add_argument(
        "--max-turns",
        type=int,
        default=10,
        help="Maximum turns for agentic execution (default: 10)"
    )

    # Working directory
    parser.add_argument(
        "-d", "--directory",
        type=str,
        default=".",
        help="Working directory (default: current directory)"
    )

    # Verbose mode
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    # Print version
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )

    # System prompt customization
    parser.add_argument(
        "--system-prompt",
        type=str,
        help="Custom system prompt"
    )

    parser.add_argument(
        "--append-system-prompt",
        type=str,
        help="Append to default system prompt"
    )

    # Permission mode
    parser.add_argument(
        "--permission-mode",
        choices=["ask", "auto", "deny"],
        default="ask",
        help="Permission mode for file/bash operations (default: ask)"
    )

    # Allowed/disallowed tools
    parser.add_argument(
        "--allowed-tools",
        type=str,
        help="Comma-separated list of allowed tools"
    )

    parser.add_argument(
        "--disallowed-tools",
        type=str,
        help="Comma-separated list of disallowed tools"
    )

    # Non-interactive mode (for scripting)
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (no prompts)"
    )

    # Config file
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config file"
    )

    # Standalone mode (direct Claude API, no server)
    parser.add_argument(
        "--standalone", "-s",
        action="store_true",
        help="Run in standalone mode (direct Claude API, no server required)"
    )


    # API Key (for standalone mode)
    parser.add_argument(
        "--api-key",
        type=str,
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)"
    )

    # Server URL (for server mode)
    parser.add_argument(
        "--server-url",
        type=str,
        default="http://localhost:8000/api/v1",
        help="Backend server URL (default: http://localhost:8000/api/v1)"
    )

    return parser


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()

    # Import auth manager
    from cli.auth import get_auth_manager
    from rich.console import Console

    console = Console()

    # Get auth manager
    auth_manager = get_auth_manager(args.server_url)

    # Handle authentication commands first
    if args.command == "login":
        # Login command
        if args.token:
            # Login with token
            success = asyncio.run(auth_manager.login_with_token(args.token))
        else:
            # Interactive login
            success = asyncio.run(auth_manager.interactive_login())

        if success:
            console.print("\n[green]✓ Login successful![/green]")
            console.print(f"Welcome, [bold]{auth_manager.credentials.name}[/bold]!")
            console.print("\nYou can now use BharatBuild AI. Try:")
            console.print("  [cyan]bharatbuild[/cyan]                    Start interactive mode")
            console.print('  [cyan]bharatbuild "your request"[/cyan]    Run a single prompt')
        else:
            console.print("\n[red]✗ Login failed[/red]")
            console.print("Please check your credentials or register at the web portal.")
        sys.exit(0 if success else 1)

    elif args.command == "logout":
        # Logout command
        auth_manager.logout()
        sys.exit(0)

    elif args.command == "status" or args.command == "whoami":
        # Status command
        auth_manager.show_status()
        sys.exit(0)

    # For all operations, require authentication (uses backend API)
    if not auth_manager.is_authenticated():
        console.print("\n[red]✗ Authentication required[/red]")
        console.print("\nPlease login first:")
        console.print("  [cyan]bharatbuild login[/cyan]           Interactive login")
        console.print("  [cyan]bharatbuild login -t TOKEN[/cyan]  Login with CLI token")
        console.print("\nDon't have an account? Register at the web portal.")
        sys.exit(1)

    # Determine the prompt
    prompt = args.prompt or args.prompt_flag

    # Create config with auth info
    config = CLIConfig(
        model=args.model,
        output_format=args.output_format,
        max_turns=args.max_turns,
        working_directory=os.path.abspath(args.directory),
        verbose=args.verbose,
        permission_mode=args.permission_mode,
        system_prompt=args.system_prompt,
        append_system_prompt=args.append_system_prompt,
        allowed_tools=args.allowed_tools.split(",") if args.allowed_tools else None,
        disallowed_tools=args.disallowed_tools.split(",") if args.disallowed_tools else None,
        non_interactive=args.non_interactive,
        continue_session=args.continue_session,
        api_base_url=args.server_url,
        api_key=args.api_key,
        # Add auth info to config
        auth_token=auth_manager.credentials.access_token,
        user_id=auth_manager.credentials.user_id,
        user_email=auth_manager.credentials.email,
        user_name=auth_manager.credentials.name
    )

    # Load config file if specified
    if args.config:
        config.load_from_file(args.config)

    try:
        # Default: Agentic mode (Claude Code style) - uses backend API
        # Orchestrator mode available with --orchestrator flag for project generation

        if args.standalone:
            # Standalone mode is disabled
            console.print("[yellow]Note: Standalone mode is disabled.[/yellow]")
            console.print("All requests are processed through the BharatBuild platform.\n")
            sys.exit(1)

        # Create config for agentic mode
        agentic_config = CLIConfig(
            model=args.model,
            output_format=args.output_format,
            max_turns=args.max_turns,
            working_directory=os.path.abspath(args.directory),
            verbose=args.verbose,
            permission_mode=args.permission_mode,
            system_prompt=args.system_prompt,
            append_system_prompt=args.append_system_prompt,
            api_base_url=args.server_url,
            auth_token=auth_manager.credentials.access_token,
            user_id=auth_manager.credentials.user_id,
            user_email=auth_manager.credentials.email,
            user_name=auth_manager.credentials.name
        )

        from cli.agentic_cli import AgenticCLI
        cli = AgenticCLI(agentic_config, console)

        console.print(f"[green]Logged in as:[/green] {auth_manager.credentials.name}")
        console.print(f"[dim]Working directory: {agentic_config.working_directory}[/dim]")
        console.print()

        if prompt:
            asyncio.run(cli.run(prompt))
        else:
            asyncio.run(cli.run_interactive())

    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋")
        sys.exit(0)
    except ConnectionError as e:
        print(f"\n❌ Connection Error: {e}")
        print("\nThe BharatBuild server is not available.")
        print("Please try again later or contact support.")
        sys.exit(1)
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
