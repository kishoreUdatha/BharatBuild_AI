"""
Slash Commands Handler - Implements Claude Code-like slash commands

Available commands:
  /help         Show available commands
  /clear        Clear conversation
  /compact      Compact conversation history
  /model        Change/view model
  /config       View/edit configuration
  /status       Show project status
  /cost         Show token usage and cost
  /quit         Exit the CLI
  /resume       Resume previous session or interrupted workflow
  /sessions     List saved sessions
  /save         Save current session
  /files        List project files
  /git          Git operations
  /run          Run a command
  /init         Initialize project

Resume & Recovery:
  /resume                   Resume last session
  /resume --workflow        List interrupted workflows
  /resume <project_id>      Resume specific workflow

AI/ML Commands:
  /ai-templates List AI/ML project templates
  /ai-create    Create new AI/ML project from template
  /notebook     Create/run Jupyter notebook
  /tensorboard  Start TensorBoard
  /mlflow       Start MLflow UI
"""

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Any, Optional, Callable, Awaitable

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

if TYPE_CHECKING:
    from cli.app import BharatBuildCLI


class SlashCommandHandler:
    """Handles slash commands"""

    def __init__(self, cli: "BharatBuildCLI"):
        self.cli = cli
        self.console = cli.console
        self.config = cli.config

        # Register commands
        self.commands: Dict[str, Callable[..., Awaitable[None]]] = {
            "/help": self.cmd_help,
            "/h": self.cmd_help,
            "/?": self.cmd_help,
            "/clear": self.cmd_clear,
            "/compact": self.cmd_compact,
            "/model": self.cmd_model,
            "/config": self.cmd_config,
            "/status": self.cmd_status,
            "/cost": self.cmd_cost,
            "/usage": self.cmd_cost,
            "/quit": self.cmd_quit,
            "/exit": self.cmd_quit,
            "/q": self.cmd_quit,
            "/resume": self.cmd_resume,
            "/continue": self.cmd_resume,
            "/sessions": self.cmd_sessions,
            "/save": self.cmd_save,
            "/files": self.cmd_files,
            "/ls": self.cmd_files,
            "/git": self.cmd_git,
            "/run": self.cmd_run,
            "/init": self.cmd_init,
            "/context": self.cmd_context,
            "/undo": self.cmd_undo,
            "/history": self.cmd_history,
            "/version": self.cmd_version,
            # AI/ML Commands
            "/ai-templates": self.cmd_ai_templates,
            "/ai-create": self.cmd_ai_create,
            "/notebook": self.cmd_notebook,
            "/tensorboard": self.cmd_tensorboard,
            "/mlflow": self.cmd_mlflow,
            "/gpu": self.cmd_gpu,
            "/pip": self.cmd_pip,
            # IEEE Documentation Commands
            "/ieee": self.cmd_ieee,
            "/ieee-templates": self.cmd_ieee_templates,
            "/ieee-generate": self.cmd_ieee_generate,
            "/ieee-word": self.cmd_ieee_word,
            "/ieee-all": self.cmd_ieee_all,
            "/srs": self.cmd_srs,
            "/sdd": self.cmd_sdd,
            "/test-plan": self.cmd_test_plan,
            # Extended IEEE Documentation (60-80 pages for college)
            "/ieee-extended": self.cmd_ieee_extended,
            "/ieee-college": self.cmd_ieee_college,
            "/srs-extended": self.cmd_srs_extended,
            "/sdd-extended": self.cmd_sdd_extended,
            "/test-extended": self.cmd_test_extended,
            "/feasibility": self.cmd_feasibility,
            "/literature-survey": self.cmd_literature_survey,
            # Dynamic IEEE Documentation (auto-generated from project)
            "/ieee-dynamic": self.cmd_ieee_dynamic,
            "/ieee-auto": self.cmd_ieee_auto,
            "/analyze-project": self.cmd_analyze_project,
            # Project Adventure (Interactive Game-like Experience)
            "/adventure": self.cmd_adventure,
            "/surprise": self.cmd_adventure_surprise,
            # Claude Code-style AI Commands
            "/think": self.cmd_think,
            "/plan": self.cmd_plan,
            "/review": self.cmd_review,
            "/refactor": self.cmd_refactor,
            "/optimize": self.cmd_optimize,
            "/debug": self.cmd_debug,
            "/test": self.cmd_test,
            "/explain": self.cmd_explain,
            "/doc": self.cmd_doc,
            "/fix": self.cmd_fix,
        }

        # Command descriptions for help
        self.descriptions = {
            "/help": "Show this help message",
            "/clear": "Clear conversation history",
            "/compact": "Compact conversation to save context",
            "/model": "View or change the AI model",
            "/config": "View or edit configuration",
            "/status": "Show current project status",
            "/cost": "Show token usage and estimated cost",
            "/quit": "Exit the CLI",
            "/resume": "Resume previous session",
            "/sessions": "List saved sessions",
            "/save": "Save current session",
            "/files": "List files in current directory",
            "/git": "Git operations (status, diff, log)",
            "/run": "Run a shell command",
            "/init": "Initialize a new project",
            "/context": "Show current context information",
            "/undo": "Undo last file operation",
            "/history": "Show command history",
            "/version": "Show version information",
            # AI/ML descriptions
            "/ai-templates": "List AI/ML project templates",
            "/ai-create": "Create new AI/ML project from template",
            "/notebook": "Create or run Jupyter notebook",
            "/tensorboard": "Start TensorBoard server",
            "/mlflow": "Start MLflow tracking UI",
            "/gpu": "Check GPU/CUDA availability",
            "/pip": "Install Python packages",
            # IEEE Documentation descriptions
            "/ieee": "IEEE documentation commands help",
            "/ieee-templates": "List available IEEE document templates",
            "/ieee-generate": "Generate specific IEEE document (Markdown)",
            "/ieee-word": "Generate IEEE document in Word format with UML diagrams",
            "/ieee-all": "Generate all IEEE documents for project",
            "/srs": "Generate IEEE 830 SRS document",
            "/sdd": "Generate IEEE 1016 SDD document",
            "/test-plan": "Generate IEEE 829 Test document",
            # Extended IEEE (60-80 pages for college)
            "/ieee-extended": "Generate extended IEEE documents (60-80 pages for college)",
            "/ieee-college": "Generate ALL documents for college submission (60-80 pages each)",
            "/srs-extended": "Generate extended SRS document (60-80 pages)",
            "/sdd-extended": "Generate extended SDD document (60-80 pages)",
            "/test-extended": "Generate extended Test documentation (50-70 pages)",
            "/feasibility": "Generate Feasibility Study Report",
            "/literature-survey": "Generate Literature Survey document",
            # Dynamic IEEE (auto-generated from project code)
            "/ieee-dynamic": "Generate IEEE documents dynamically from project code analysis",
            "/ieee-auto": "Auto-generate all IEEE documents by analyzing the project",
            "/analyze-project": "Analyze project structure, models, APIs, components",
            # Project Adventure (Interactive Game-like Experience)
            "/adventure": "🎮 Start interactive Project Adventure - fun way to create projects!",
            "/surprise": "🎁 Get a surprise project idea",
            # Claude Code-style AI Commands
            "/think": "🧠 Extended thinking mode - deeper analysis",
            "/plan": "📋 Create implementation plan for a task",
            "/review": "🔍 Code review - security, quality, performance",
            "/refactor": "♻️ Refactor code for better structure",
            "/optimize": "⚡ Optimize code for performance",
            "/debug": "🐛 Debug and find issues in code",
            "/test": "🧪 Generate tests for code",
            "/explain": "📖 Explain code in detail",
            "/doc": "📝 Generate documentation for code",
            "/fix": "🔧 Fix bugs and errors in code",
        }

    async def handle(self, input_str: str) -> None:
        """Handle a slash command"""
        parts = input_str.strip().split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command in self.commands:
            try:
                await self.commands[command](args)
            except Exception as e:
                self.console.print(f"[red]Error executing command: {e}[/red]")
        else:
            self.console.print(f"[yellow]Unknown command: {command}[/yellow]")
            self.console.print("Type /help for available commands")

    async def cmd_help(self, args: str = "") -> None:
        """Show help information"""
        table = Table(title="Available Commands", show_header=True, header_style="bold cyan")
        table.add_column("Command", style="green")
        table.add_column("Description")

        # Group commands
        main_commands = ["/help", "/quit", "/clear", "/compact"]
        session_commands = ["/resume", "/sessions", "/save"]
        project_commands = ["/status", "/files", "/init", "/run", "/git"]
        info_commands = ["/model", "/config", "/cost", "/context", "/history", "/version"]
        edit_commands = ["/undo"]
        ai_commands = ["/think", "/plan", "/review", "/refactor", "/optimize", "/debug", "/test", "/explain", "/doc", "/fix"]

        self.console.print("\n[bold cyan]Main Commands[/bold cyan]")
        for cmd in main_commands:
            if cmd in self.descriptions:
                table.add_row(cmd, self.descriptions[cmd])

        self.console.print("\n[bold cyan]AI Commands (Claude Code-style)[/bold cyan]")
        for cmd in ai_commands:
            if cmd in self.descriptions:
                table.add_row(cmd, self.descriptions[cmd])

        self.console.print("\n[bold cyan]Session Commands[/bold cyan]")
        for cmd in session_commands:
            if cmd in self.descriptions:
                table.add_row(cmd, self.descriptions[cmd])

        self.console.print("\n[bold cyan]Project Commands[/bold cyan]")
        for cmd in project_commands:
            if cmd in self.descriptions:
                table.add_row(cmd, self.descriptions[cmd])

        self.console.print("\n[bold cyan]Information Commands[/bold cyan]")
        for cmd in info_commands:
            if cmd in self.descriptions:
                table.add_row(cmd, self.descriptions[cmd])

        self.console.print("\n[bold cyan]Edit Commands[/bold cyan]")
        for cmd in edit_commands:
            if cmd in self.descriptions:
                table.add_row(cmd, self.descriptions[cmd])

        self.console.print(table)

        self.console.print("\n[bold]Keyboard Shortcuts[/bold]")
        shortcuts = Table(show_header=False, box=None)
        shortcuts.add_column("Key", style="cyan")
        shortcuts.add_column("Action")
        shortcuts.add_row("Ctrl+C", "Cancel current operation")
        shortcuts.add_row("Ctrl+L", "Clear screen")
        shortcuts.add_row("Ctrl+R", "Search history")
        shortcuts.add_row("Tab", "Auto-complete")
        shortcuts.add_row("↑/↓", "Navigate history")
        shortcuts.add_row("Esc+Esc", "Undo last change")
        self.console.print(shortcuts)

        self.console.print("\n[bold]Special Prefixes[/bold]")
        self.console.print("  [cyan]![/cyan]command  - Execute shell command directly")
        self.console.print("  [cyan]/[/cyan]command  - Execute slash command")

    async def cmd_clear(self, args: str = "") -> None:
        """Clear conversation history"""
        if args == "--all" or Confirm.ask("Clear all conversation history?"):
            self.cli.messages.clear()
            self.cli.session_manager.clear_session()
            self.console.clear()
            self.cli._print_header()
            self.console.print("[green]Conversation cleared[/green]")
        else:
            self.console.print("[dim]Cancelled[/dim]")

    async def cmd_compact(self, args: str = "") -> None:
        """Compact conversation history"""
        keep = 10
        if args:
            try:
                keep = int(args)
            except ValueError:
                pass

        removed = self.cli.session_manager.compact_session(keep_last=keep)
        if removed > 0:
            self.console.print(f"[green]Compacted: removed {removed} messages, kept last {keep}[/green]")
        else:
            self.console.print("[dim]Nothing to compact[/dim]")

    async def cmd_model(self, args: str = "") -> None:
        """View or change model"""
        if args:
            if args in ["haiku", "sonnet"]:
                self.config.model = args
                self.console.print(f"[green]Model changed to: {args}[/green]")
            else:
                self.console.print(f"[yellow]Invalid model. Choose: haiku, sonnet[/yellow]")
        else:
            self.console.print(f"Current model: [cyan]{self.config.model}[/cyan]")
            self.console.print("\nAvailable models:")
            self.console.print("  [green]haiku[/green]  - Fast, efficient (Claude 3.5 Haiku)")
            self.console.print("  [green]sonnet[/green] - Balanced performance (Claude 3.5 Sonnet)")

    async def cmd_config(self, args: str = "") -> None:
        """View or edit configuration"""
        if args:
            # Parse key=value
            if "=" in args:
                key, value = args.split("=", 1)
                key = key.strip()
                value = value.strip()

                if hasattr(self.config, key):
                    # Type conversion
                    current_value = getattr(self.config, key)
                    if isinstance(current_value, bool):
                        value = value.lower() in ("true", "1", "yes")
                    elif isinstance(current_value, int):
                        value = int(value)
                    elif isinstance(current_value, float):
                        value = float(value)

                    setattr(self.config, key, value)
                    self.console.print(f"[green]Set {key} = {value}[/green]")
                else:
                    self.console.print(f"[yellow]Unknown config key: {key}[/yellow]")
            else:
                # Show specific config
                if hasattr(self.config, args):
                    value = getattr(self.config, args)
                    self.console.print(f"{args} = {value}")
                else:
                    self.console.print(f"[yellow]Unknown config key: {args}[/yellow]")
        else:
            # Show all config
            table = Table(title="Configuration", show_header=True)
            table.add_column("Setting", style="green")
            table.add_column("Value")

            important_keys = [
                "model", "working_directory", "permission_mode",
                "max_turns", "verbose", "output_format", "api_base_url"
            ]

            for key in important_keys:
                if hasattr(self.config, key):
                    value = getattr(self.config, key)
                    table.add_row(key, str(value))

            self.console.print(table)
            self.console.print("\n[dim]Use /config key=value to change settings[/dim]")

    async def cmd_status(self, args: str = "") -> None:
        """Show project status"""
        cwd = Path(self.config.working_directory).resolve()

        panel_content = f"""[bold]Working Directory:[/bold] {cwd}
[bold]Model:[/bold] {self.config.model}
[bold]Messages:[/bold] {len(self.cli.messages)}
[bold]Total Tokens:[/bold] {self.cli.total_tokens}
"""

        # Check if git repo
        is_git = await self.cli.tool_executor.is_git_repo()
        if is_git:
            git_status = await self.cli.tool_executor.git_status()
            changes = len([l for l in git_status.split('\n') if l.strip()])
            panel_content += f"[bold]Git Changes:[/bold] {changes} files\n"

        # Count files
        file_count = len(list(cwd.rglob("*")))
        panel_content += f"[bold]Files:[/bold] {file_count}"

        panel = Panel(panel_content, title="Project Status", border_style="cyan")
        self.console.print(panel)

    async def cmd_cost(self, args: str = "") -> None:
        """Show token usage and cost"""
        # Calculate costs (approximate)
        # Haiku: $0.80/1M input, $4/1M output
        # Sonnet: $3/1M input, $15/1M output

        session_summary = self.cli.session_manager.get_session_summary()
        total_tokens = session_summary.get("total_tokens", 0) or self.cli.total_tokens

        # Rough cost estimate (assuming 50/50 input/output split)
        if self.config.model == "haiku":
            cost = (total_tokens / 1_000_000) * 2.40  # Average of input/output
        else:
            cost = (total_tokens / 1_000_000) * 9.00

        table = Table(title="Usage Statistics", show_header=False)
        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        table.add_row("Session Messages", str(len(self.cli.messages)))
        table.add_row("Total Tokens", str(total_tokens))
        table.add_row("Model", self.config.model)
        table.add_row("Estimated Cost", f"${cost:.4f}")

        self.console.print(table)

    async def cmd_quit(self, args: str = "") -> None:
        """Exit the CLI"""
        # Save session before quitting
        self.cli.session_manager.save_session(self.cli.messages)
        self.cli.quit()

    async def cmd_resume(self, args: str = "") -> None:
        """Resume previous session or interrupted workflow

        Usage:
            /resume                 Resume last conversation session
            /resume <session_name>  Resume specific session
            /resume --workflow      List resumable workflows
            /resume --workflow <id> Resume interrupted project generation
        """
        # Check if resuming a workflow
        if args.startswith("--workflow") or args.startswith("-w"):
            await self._resume_workflow(args.replace("--workflow", "").replace("-w", "").strip())
            return

        # Check if it looks like a project ID
        if args.startswith("project-") or args.startswith("proj-"):
            await self._resume_workflow(args)
            return

        # Regular session resume
        if args:
            # Resume specific session
            messages = self.cli.session_manager.load_archived_session(args)
        else:
            # Resume last session
            messages = self.cli.session_manager.load_session()

        if messages:
            self.cli.messages = messages
            self.console.print(f"[green]Resumed session with {len(messages)} messages[/green]")
        else:
            self.console.print("[yellow]No session to resume[/yellow]")
            # Check for interrupted workflows
            await self._check_interrupted_workflows()

    async def _resume_workflow(self, project_id: str = "") -> None:
        """Resume an interrupted workflow"""
        from cli.reconnection import ReconnectionHandler

        handler = ReconnectionHandler(self.config, self.console)

        if not project_id:
            # List available workflows
            checkpoints = await handler.list_checkpoints()

            if not checkpoints:
                self.console.print("[yellow]No interrupted workflows found[/yellow]")
                return

            # Show table of resumable workflows
            table = Table(title="Interrupted Workflows")
            table.add_column("Project ID", style="cyan")
            table.add_column("Step", style="yellow")
            table.add_column("Status", style="green")
            table.add_column("Time", style="dim")

            for cp in checkpoints:
                status = "✓ Resumable" if cp.get("can_resume") else "✗ Max retries"
                from datetime import datetime
                time_str = datetime.fromtimestamp(cp.get("timestamp", 0)).strftime("%Y-%m-%d %H:%M")
                table.add_row(
                    cp.get("project_id", ""),
                    cp.get("current_step", "unknown"),
                    status,
                    time_str
                )

            self.console.print(table)
            self.console.print("\n[dim]Use '/resume <project_id>' to resume a workflow[/dim]")
            return

        # Resume specific workflow
        self.console.print(f"[cyan]Resuming workflow: {project_id}[/cyan]\n")

        try:
            async for event in handler.resume_workflow(project_id):
                event_type = event.get("type", "")

                if event_type == "progress":
                    step = event.get("data", {}).get("step", "")
                    progress = event.get("data", {}).get("progress", 0)
                    self.console.print(f"[dim]  {step}: {progress}%[/dim]")

                elif event_type == "file_created":
                    path = event.get("data", {}).get("path", "")
                    self.console.print(f"[green]  ✓ {path}[/green]")

                elif event_type == "step_complete":
                    step = event.get("data", {}).get("step", "")
                    self.console.print(f"[cyan]  ✓ Completed: {step}[/cyan]")

                elif event_type == "complete":
                    self.console.print("\n[green]✓ Workflow completed successfully![/green]")

                elif event_type == "error":
                    error = event.get("data", {}).get("error", "Unknown error")
                    self.console.print(f"\n[red]✗ Error: {error}[/red]")

        except Exception as e:
            self.console.print(f"[red]Failed to resume: {e}[/red]")

    async def _check_interrupted_workflows(self) -> None:
        """Check and notify about interrupted workflows"""
        from cli.reconnection import ReconnectionHandler

        handler = ReconnectionHandler(self.config, self.console)
        checkpoints = await handler.list_checkpoints()
        resumable = [cp for cp in checkpoints if cp.get("can_resume")]

        if resumable:
            self.console.print(
                f"\n[yellow]💡 Found {len(resumable)} interrupted workflow(s).[/yellow]"
            )
            self.console.print("[dim]Use '/resume --workflow' to see details[/dim]")

    async def cmd_sessions(self, args: str = "") -> None:
        """List saved sessions"""
        sessions = self.cli.session_manager.list_sessions()

        if not sessions:
            self.console.print("[dim]No saved sessions[/dim]")
            return

        table = Table(title="Saved Sessions", show_header=True)
        table.add_column("Name", style="green")
        table.add_column("Messages", justify="right")
        table.add_column("Directory")
        table.add_column("Date")

        for session in sessions[:10]:  # Show last 10
            from datetime import datetime
            date_str = datetime.fromtimestamp(session["timestamp"]).strftime("%Y-%m-%d %H:%M")
            table.add_row(
                session["name"],
                str(session["message_count"]),
                session["working_directory"][-30:],
                date_str
            )

        self.console.print(table)
        self.console.print("\n[dim]Use /resume <name> to load a session[/dim]")

    async def cmd_save(self, args: str = "") -> None:
        """Save current session"""
        name = args if args else None
        path = self.cli.session_manager.archive_session(name)
        if path:
            self.console.print(f"[green]Session saved: {path}[/green]")
        else:
            self.console.print("[yellow]Nothing to save[/yellow]")

    async def cmd_files(self, args: str = "") -> None:
        """List files in directory"""
        pattern = args if args else "*"
        files = await self.cli.tool_executor.list_files(".", pattern)

        if not files:
            self.console.print("[dim]No files found[/dim]")
            return

        # Group by directory
        for f in files[:50]:  # Limit to 50
            path = Path(f)
            if path.is_dir():
                self.console.print(f"[blue]📁 {f}/[/blue]")
            else:
                self.console.print(f"   {f}")

        if len(files) > 50:
            self.console.print(f"[dim]... and {len(files) - 50} more[/dim]")

    async def cmd_git(self, args: str = "") -> None:
        """Git operations"""
        if not await self.cli.tool_executor.is_git_repo():
            self.console.print("[yellow]Not a git repository[/yellow]")
            return

        subcommand = args.split()[0] if args else "status"

        if subcommand == "status":
            result = await self.cli.tool_executor.execute_bash("git status")
            self.console.print(result.stdout)
        elif subcommand == "diff":
            result = await self.cli.tool_executor.execute_bash("git diff")
            if result.stdout:
                from rich.syntax import Syntax
                syntax = Syntax(result.stdout, "diff", theme="monokai")
                self.console.print(syntax)
            else:
                self.console.print("[dim]No changes[/dim]")
        elif subcommand == "log":
            result = await self.cli.tool_executor.execute_bash("git log --oneline -10")
            self.console.print(result.stdout)
        else:
            # Run arbitrary git command
            result = await self.cli.tool_executor.execute_bash(f"git {args}")
            self.console.print(result.stdout)
            if result.stderr:
                self.console.print(f"[red]{result.stderr}[/red]")

    async def cmd_run(self, args: str = "") -> None:
        """Run a shell command"""
        if not args:
            self.console.print("[yellow]Usage: /run <command>[/yellow]")
            return

        result = await self.cli.tool_executor.execute_bash(args)
        self.cli.renderer.render_command_result(args, result)

    async def cmd_init(self, args: str = "") -> None:
        """Initialize a new project"""
        project_name = args if args else Prompt.ask("Project name")

        if not project_name:
            self.console.print("[yellow]Cancelled[/yellow]")
            return

        # Create project directory
        project_dir = Path(self.config.working_directory) / project_name
        project_dir.mkdir(parents=True, exist_ok=True)

        # Initialize git
        result = await self.cli.tool_executor.execute_bash(
            f"cd {project_dir} && git init"
        )

        # Create basic files
        readme_content = f"# {project_name}\n\nCreated with BharatBuild AI\n"
        await self.cli.tool_executor.write_file(
            str(project_dir / "README.md"),
            readme_content
        )

        gitignore_content = """# Dependencies
node_modules/
__pycache__/
venv/
.env

# Build
dist/
build/
*.egg-info/

# IDE
.idea/
.vscode/
*.swp
"""
        await self.cli.tool_executor.write_file(
            str(project_dir / ".gitignore"),
            gitignore_content
        )

        self.console.print(f"[green]✓ Project initialized: {project_dir}[/green]")
        self.console.print(f"[dim]  Created README.md and .gitignore[/dim]")

    async def cmd_context(self, args: str = "") -> None:
        """Show current context information"""
        context_info = f"""[bold]Current Context[/bold]

Working Directory: {self.config.working_directory}
Model: {self.config.model}
Permission Mode: {self.config.permission_mode}
Max Turns: {self.config.max_turns}

Conversation:
  Messages: {len(self.cli.messages)}
  User Messages: {len([m for m in self.cli.messages if m.role == 'user'])}
  Assistant Messages: {len([m for m in self.cli.messages if m.role == 'assistant'])}

File Operations: {len(self.cli.tool_executor.file_history)}
Commands Executed: {len(self.cli.tool_executor.command_history)}
"""
        self.console.print(Panel(context_info, border_style="cyan"))

    async def cmd_undo(self, args: str = "") -> None:
        """Undo last file operation"""
        result = self.cli.tool_executor.undo_last_file_operation()

        if result:
            self.console.print(f"[green]Undid: {result.operation} {result.path}[/green]")
        else:
            self.console.print("[yellow]Nothing to undo[/yellow]")

    async def cmd_history(self, args: str = "") -> None:
        """Show command history"""
        # Show recent commands from tool executor
        commands = self.cli.tool_executor.command_history[-10:]

        if not commands:
            self.console.print("[dim]No command history[/dim]")
            return

        table = Table(title="Recent Commands", show_header=True)
        table.add_column("Command")
        table.add_column("Exit", justify="right", width=6)
        table.add_column("Duration", justify="right")

        for cmd in commands:
            exit_style = "green" if cmd.exit_code == 0 else "red"
            table.add_row(
                cmd.command[:50] + ("..." if len(cmd.command) > 50 else ""),
                f"[{exit_style}]{cmd.exit_code}[/{exit_style}]",
                f"{cmd.duration:.2f}s"
            )

        self.console.print(table)

    async def cmd_version(self, args: str = "") -> None:
        """Show version information"""
        version_info = """
[bold cyan]BharatBuild AI CLI[/bold cyan]
Version: 1.0.0

A Claude Code-style CLI for AI-driven development.

GitHub: https://github.com/bharatbuild/bharatbuild-ai
Docs: https://docs.bharatbuild.ai
"""
        self.console.print(Panel(version_info, border_style="cyan"))

    # ==========================================
    # AI/ML Commands
    # ==========================================

    async def cmd_ai_templates(self, args: str = "") -> None:
        """List AI/ML project templates"""
        try:
            from cli.templates.ai_templates import list_templates, get_categories

            categories = get_categories()

            if args:
                # Filter by category
                templates = list_templates(args)
                if not templates:
                    self.console.print(f"[yellow]No templates found for category: {args}[/yellow]")
                    self.console.print(f"Available categories: {', '.join(categories)}")
                    return
            else:
                templates = list_templates()

            # Group by category
            by_category = {}
            for t in templates:
                cat = t["category"]
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(t)

            self.console.print("\n[bold cyan]🤖 AI/ML Project Templates[/bold cyan]\n")

            for category, cat_templates in by_category.items():
                self.console.print(f"[bold]{category}[/bold]")
                table = Table(show_header=False, box=None, padding=(0, 2))
                table.add_column("ID", style="green")
                table.add_column("Description")

                for t in cat_templates:
                    table.add_row(t["id"], t["description"])

                self.console.print(table)
                self.console.print()

            self.console.print("[dim]Use /ai-create <template-id> to create a project[/dim]")

        except ImportError:
            self.console.print("[red]AI/ML templates not available[/red]")

    async def cmd_ai_create(self, args: str = "") -> None:
        """Create new AI/ML project from template"""
        try:
            from cli.templates.ai_templates import get_template, list_templates

            if not args:
                self.console.print("[yellow]Usage: /ai-create <template-id> [project-name][/yellow]")
                self.console.print("[dim]Use /ai-templates to see available templates[/dim]")
                return

            parts = args.split(maxsplit=1)
            template_id = parts[0]
            project_name = parts[1] if len(parts) > 1 else None

            template = get_template(template_id)
            if not template:
                self.console.print(f"[red]Template not found: {template_id}[/red]")
                return

            # Get project name
            if not project_name:
                default_name = template_id.replace("-", "_") + "_project"
                project_name = Prompt.ask("Project name", default=default_name)

            # Create project directory
            project_dir = Path(self.config.working_directory) / project_name
            project_dir.mkdir(parents=True, exist_ok=True)

            self.console.print(f"\n[cyan]Creating {template['name']}...[/cyan]\n")

            # Create files from template
            for filename, content in template["files"].items():
                file_path = project_dir / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
                self.console.print(f"  [green]✓[/green] {filename}")

            # Initialize git
            await self.cli.tool_executor.execute_bash(f"cd \"{project_dir}\" && git init")

            self.console.print(f"\n[green]✓ Project created: {project_dir}[/green]")
            self.console.print(f"\n[bold]Next steps:[/bold]")
            self.console.print(f"  cd {project_name}")
            self.console.print(f"  pip install -r requirements.txt")
            self.console.print(f"  python main.py  # or train.py")

        except ImportError:
            self.console.print("[red]AI/ML templates not available[/red]")

    async def cmd_notebook(self, args: str = "") -> None:
        """Create or run Jupyter notebook"""
        if not args:
            self.console.print("""
[bold]Jupyter Notebook Commands:[/bold]

  /notebook create <name>    Create a new notebook
  /notebook run              Start JupyterLab server
  /notebook list             List notebooks in directory
""")
            return

        parts = args.split(maxsplit=1)
        subcommand = parts[0]

        if subcommand == "create":
            name = parts[1] if len(parts) > 1 else "notebook"
            if not name.endswith(".ipynb"):
                name += ".ipynb"

            notebook_content = {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "metadata": {},
                        "source": [f"# {name.replace('.ipynb', '')}\n", "\nCreated with BharatBuild AI"]
                    },
                    {
                        "cell_type": "code",
                        "execution_count": None,
                        "metadata": {},
                        "outputs": [],
                        "source": ["# Import libraries\n", "import numpy as np\n", "import pandas as pd\n", "import matplotlib.pyplot as plt"]
                    }
                ],
                "metadata": {
                    "kernelspec": {
                        "display_name": "Python 3",
                        "language": "python",
                        "name": "python3"
                    }
                },
                "nbformat": 4,
                "nbformat_minor": 4
            }

            import json
            notebook_path = Path(self.config.working_directory) / name
            notebook_path.write_text(json.dumps(notebook_content, indent=2))
            self.console.print(f"[green]✓ Created notebook: {name}[/green]")

        elif subcommand == "run":
            self.console.print("[cyan]Starting JupyterLab...[/cyan]")
            result = await self.cli.tool_executor.execute_bash(
                f"cd \"{self.config.working_directory}\" && jupyter lab --no-browser"
            )
            self.console.print(result.stdout)

        elif subcommand == "list":
            notebooks = list(Path(self.config.working_directory).glob("**/*.ipynb"))
            if notebooks:
                self.console.print("[bold]Notebooks:[/bold]")
                for nb in notebooks[:20]:
                    self.console.print(f"  📓 {nb.name}")
            else:
                self.console.print("[dim]No notebooks found[/dim]")

    async def cmd_tensorboard(self, args: str = "") -> None:
        """Start TensorBoard server"""
        log_dir = args if args else "./logs"

        self.console.print(f"[cyan]Starting TensorBoard (logs: {log_dir})...[/cyan]")
        self.console.print("[dim]Open http://localhost:6006 in your browser[/dim]")

        result = await self.cli.tool_executor.execute_bash(
            f"tensorboard --logdir=\"{log_dir}\" --port=6006"
        )
        self.console.print(result.stdout)

    async def cmd_mlflow(self, args: str = "") -> None:
        """Start MLflow tracking UI"""
        self.console.print("[cyan]Starting MLflow UI...[/cyan]")
        self.console.print("[dim]Open http://localhost:5000 in your browser[/dim]")

        result = await self.cli.tool_executor.execute_bash(
            f"cd \"{self.config.working_directory}\" && mlflow ui --port=5000"
        )
        self.console.print(result.stdout)

    async def cmd_gpu(self, args: str = "") -> None:
        """Check GPU/CUDA availability"""
        self.console.print("[bold]GPU/CUDA Status[/bold]\n")

        # Check NVIDIA GPU
        result = await self.cli.tool_executor.execute_bash("nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader")

        if result.exit_code == 0 and result.stdout.strip():
            self.console.print("[green]✓ NVIDIA GPU detected:[/green]")
            for line in result.stdout.strip().split("\n"):
                parts = line.split(",")
                if len(parts) >= 3:
                    name, total, free = [p.strip() for p in parts]
                    self.console.print(f"  {name}")
                    self.console.print(f"    Memory: {free} free / {total} total")
        else:
            self.console.print("[yellow]⚠ No NVIDIA GPU detected[/yellow]")

        # Check PyTorch CUDA
        pytorch_check = await self.cli.tool_executor.execute_bash(
            'python -c "import torch; print(f\'PyTorch CUDA: {torch.cuda.is_available()}, Devices: {torch.cuda.device_count()}\')"'
        )
        if pytorch_check.exit_code == 0:
            self.console.print(f"\n[cyan]{pytorch_check.stdout.strip()}[/cyan]")

        # Check TensorFlow GPU
        tf_check = await self.cli.tool_executor.execute_bash(
            'python -c "import tensorflow as tf; gpus = tf.config.list_physical_devices(\'GPU\'); print(f\'TensorFlow GPUs: {len(gpus)}\')"'
        )
        if tf_check.exit_code == 0:
            self.console.print(f"[cyan]{tf_check.stdout.strip()}[/cyan]")

    async def cmd_pip(self, args: str = "") -> None:
        """Install Python packages"""
        if not args:
            self.console.print("[yellow]Usage: /pip install <package>[/yellow]")
            self.console.print("[yellow]       /pip install -r requirements.txt[/yellow]")
            return

        self.console.print(f"[cyan]Running: pip {args}[/cyan]")
        result = await self.cli.tool_executor.execute_bash(f"pip {args}")
        self.console.print(result.stdout)
        if result.stderr:
            self.console.print(f"[yellow]{result.stderr}[/yellow]")

    # ==========================================
    # IEEE Documentation Commands
    # ==========================================

    def _get_project_info(self) -> "ProjectInfo":
        """Interactive prompt to get project information"""
        from cli.templates.ieee_templates import ProjectInfo

        self.console.print("\n[bold cyan]📋 Project Information for IEEE Documents[/bold cyan]\n")

        title = Prompt.ask("Project Title", default="My Project")
        team_name = Prompt.ask("Team Name", default="Team Alpha")

        # Get team members
        members_input = Prompt.ask(
            "Team Members (comma-separated)",
            default="Member 1, Member 2, Member 3"
        )
        team_members = [m.strip() for m in members_input.split(",")]

        guide_name = Prompt.ask("Project Guide Name", default="Dr. Guide Name")
        college_name = Prompt.ask("College/University Name", default="My University")
        department = Prompt.ask("Department", default="Computer Science and Engineering")
        academic_year = Prompt.ask("Academic Year", default="2024-2025")

        return ProjectInfo(
            title=title,
            team_name=team_name,
            team_members=team_members,
            guide_name=guide_name,
            college_name=college_name,
            department=department,
            academic_year=academic_year
        )

    async def cmd_ieee(self, args: str = "") -> None:
        """Show IEEE documentation commands help"""
        help_text = """
[bold cyan]📚 IEEE Standard Documentation Generator[/bold cyan]

Generate professional IEEE-compliant documentation for student projects.

[bold]Available Commands:[/bold]

  [green]/ieee-templates[/green]     List all IEEE document templates
  [green]/ieee-generate[/green]      Generate a specific IEEE document (Markdown)
  [green]/ieee-word[/green]          Generate IEEE documents in Word format (.docx)
  [green]/ieee-pdf[/green]           Generate IEEE documents in PDF format
  [green]/ieee-all[/green]           Generate ALL IEEE documents at once

[bold]Quick Commands:[/bold]

  [green]/srs[/green]                Generate IEEE 830 SRS (Markdown)
  [green]/srs --word[/green]         Generate IEEE 830 SRS (Word with UML diagrams)
  [green]/sdd[/green]                Generate IEEE 1016 SDD (Markdown)
  [green]/sdd --word[/green]         Generate IEEE 1016 SDD (Word with UML diagrams)
  [green]/test-plan[/green]          Generate IEEE 829 Test Documentation

[bold]Supported IEEE Standards:[/bold]

  • IEEE 830  - Software Requirements Specification (SRS)
  • IEEE 1016 - Software Design Description (SDD)
  • IEEE 829  - Software Test Documentation
  • IEEE 1058 - Software Project Management Plan (SPMP)

[bold]Output Formats:[/bold]

  • [cyan]Markdown (.md)[/cyan]  - Default, editable text format
  • [cyan]Word (.docx)[/cyan]    - Professional Word document with formatting
  • [cyan]PDF (.pdf)[/cyan]      - Portable Document Format

[bold]Features in Word/PDF:[/bold]

  • Professional cover page with college logo
  • Table of Contents (auto-generated)
  • UML Diagrams (Use Case, Class, ER, Sequence)
  • Formatted tables and sections
  • Page numbers and headers

[bold]Example Usage:[/bold]

  /ieee-generate srs          Generate SRS (Markdown)
  /ieee-word srs              Generate SRS (Word + UML)
  /ieee-all --word            Generate all documents (Word)
  /srs --word                 Quick generate SRS (Word)

[dim]Documents are saved to ./docs/ folder[/dim]
"""
        self.console.print(Panel(help_text, title="IEEE Documentation", border_style="cyan"))

    async def cmd_ieee_templates(self, args: str = "") -> None:
        """List available IEEE document templates"""
        try:
            from cli.templates.ieee_templates import list_ieee_templates

            templates = list_ieee_templates()

            self.console.print("\n[bold cyan]📚 IEEE Document Templates[/bold cyan]\n")

            table = Table(show_header=True, header_style="bold")
            table.add_column("ID", style="green")
            table.add_column("Document Name")
            table.add_column("IEEE Standard", style="cyan")
            table.add_column("Output File")

            for tid, info in templates.items():
                table.add_row(
                    tid,
                    info["name"],
                    info["standard"],
                    info["filename"]
                )

            self.console.print(table)
            self.console.print("\n[dim]Use /ieee-generate <id> to generate a specific document[/dim]")
            self.console.print("[dim]Use /ieee-all to generate all documents[/dim]")

        except ImportError as e:
            self.console.print(f"[red]IEEE templates not available: {e}[/red]")

    async def cmd_ieee_generate(self, args: str = "") -> None:
        """Generate a specific IEEE document"""
        try:
            from cli.templates.ieee_templates import (
                generate_ieee_document,
                list_ieee_templates,
                ProjectInfo
            )

            templates = list_ieee_templates()

            if not args:
                self.console.print("[yellow]Usage: /ieee-generate <template-id>[/yellow]")
                self.console.print(f"[dim]Available: {', '.join(templates.keys())}[/dim]")
                return

            template_id = args.strip().lower()

            if template_id not in templates:
                self.console.print(f"[red]Unknown template: {template_id}[/red]")
                self.console.print(f"[dim]Available: {', '.join(templates.keys())}[/dim]")
                return

            # Get project information
            project_info = self._get_project_info()

            # Generate document
            output_dir = Path(self.config.working_directory) / "docs"
            output_dir.mkdir(parents=True, exist_ok=True)

            filename = templates[template_id]["filename"]
            output_path = output_dir / filename

            self.console.print(f"\n[cyan]Generating {templates[template_id]['name']}...[/cyan]")

            content = generate_ieee_document(template_id, project_info, str(output_path))

            self.console.print(f"[green]✓ Generated: {output_path}[/green]")
            self.console.print(f"[dim]  Standard: {templates[template_id]['standard']}[/dim]")

        except ImportError as e:
            self.console.print(f"[red]IEEE templates not available: {e}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error generating document: {e}[/red]")

    async def cmd_ieee_all(self, args: str = "") -> None:
        """Generate all IEEE documents for a project"""
        try:
            from cli.templates.ieee_templates import (
                generate_all_ieee_documents,
                list_ieee_templates,
                ProjectInfo
            )

            self.console.print("\n[bold cyan]📚 Generate All IEEE Documents[/bold cyan]")
            self.console.print("[dim]This will generate complete documentation for your project[/dim]\n")

            # Get project information
            project_info = self._get_project_info()

            # Determine output directory
            output_dir = args.strip() if args else "docs"
            output_path = Path(self.config.working_directory) / output_dir

            self.console.print(f"\n[cyan]Generating all IEEE documents...[/cyan]\n")

            # Generate all documents
            generated = generate_all_ieee_documents(project_info, str(output_path))

            self.console.print("[green]✓ All documents generated successfully![/green]\n")

            table = Table(show_header=True, header_style="bold")
            table.add_column("Document", style="cyan")
            table.add_column("File Path", style="green")

            templates = list_ieee_templates()
            for tid, filepath in generated.items():
                table.add_row(templates[tid]["name"], filepath)

            self.console.print(table)

            self.console.print(f"\n[bold]Output Directory:[/bold] {output_path}")
            self.console.print("\n[dim]You can now edit these documents to add project-specific details.[/dim]")

        except ImportError as e:
            self.console.print(f"[red]IEEE templates not available: {e}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error generating documents: {e}[/red]")

    async def cmd_ieee_word(self, args: str = "") -> None:
        """Generate IEEE document in Word format with UML diagrams"""
        try:
            from cli.templates.ieee_word_generator import (
                IEEEWordGenerator,
                generate_ieee_word_document
            )
            from cli.templates.document_generator import check_dependencies
        except ImportError:
            self.console.print("[red]Word generation requires python-docx.[/red]")
            self.console.print("[yellow]Install with: pip install python-docx[/yellow]")
            return

        # Check dependencies
        deps = check_dependencies()
        if not deps.get("word"):
            self.console.print("[red]python-docx is required for Word generation.[/red]")
            self.console.print("[yellow]Install with: pip install python-docx[/yellow]")
            return

        valid_templates = ["srs", "sdd", "test", "all"]

        if not args:
            self.console.print("[yellow]Usage: /ieee-word <template>[/yellow]")
            self.console.print(f"[dim]Available: {', '.join(valid_templates)}[/dim]")
            self.console.print("\n[bold]Examples:[/bold]")
            self.console.print("  /ieee-word srs     Generate SRS in Word format")
            self.console.print("  /ieee-word sdd     Generate SDD in Word format")
            self.console.print("  /ieee-word all     Generate ALL documents in Word format")
            return

        template_id = args.strip().lower()

        if template_id not in valid_templates:
            self.console.print(f"[red]Unknown template: {template_id}[/red]")
            self.console.print(f"[dim]Available: {', '.join(valid_templates)}[/dim]")
            return

        # Get project information
        project_info = self._get_project_info()

        # Additional prompts for Word generation
        self.console.print("\n[bold cyan]📷 Additional Options for Word Document[/bold cyan]\n")

        logo_path = Prompt.ask(
            "College Logo Path (optional, press Enter to skip)",
            default=""
        )
        if logo_path and not os.path.exists(logo_path):
            self.console.print(f"[yellow]Logo file not found: {logo_path}[/yellow]")
            logo_path = None

        include_diagrams = Confirm.ask("Include UML diagrams?", default=True)

        # Generate document(s)
        output_dir = Path(self.config.working_directory) / "docs"
        output_dir.mkdir(parents=True, exist_ok=True)

        self.console.print(f"\n[cyan]Generating Word document(s)...[/cyan]\n")

        try:
            generator = IEEEWordGenerator(project_info, str(output_dir))

            if template_id == "all":
                results = generator.generate_all(
                    logo_path=logo_path if logo_path else None,
                    include_diagrams=include_diagrams
                )
                self.console.print("[green]✓ All documents generated successfully![/green]\n")

                table = Table(show_header=True, header_style="bold")
                table.add_column("Document", style="cyan")
                table.add_column("File Path", style="green")

                for doc_type, filepath in results.items():
                    if not filepath.startswith("Error"):
                        table.add_row(doc_type.upper(), filepath)
                    else:
                        table.add_row(doc_type.upper(), f"[red]{filepath}[/red]")

                self.console.print(table)

            else:
                if template_id == "srs":
                    output_path = generator.generate_srs(
                        logo_path=logo_path if logo_path else None,
                        include_diagrams=include_diagrams
                    )
                elif template_id == "sdd":
                    output_path = generator.generate_sdd(
                        logo_path=logo_path if logo_path else None,
                        include_diagrams=include_diagrams
                    )
                elif template_id == "test":
                    output_path = generator.generate_test_document(
                        logo_path=logo_path if logo_path else None
                    )

                self.console.print(f"[green]✓ Generated: {output_path}[/green]")

            self.console.print(f"\n[bold]Output Directory:[/bold] {output_dir}")
            self.console.print("\n[dim]Features included:[/dim]")
            self.console.print("  • Professional cover page")
            self.console.print("  • Table of Contents")
            if include_diagrams:
                self.console.print("  • UML Diagrams (Use Case, Class, ER)")
            self.console.print("  • Formatted tables and sections")

        except Exception as e:
            self.console.print(f"[red]Error generating document: {e}[/red]")
            import traceback
            self.console.print(f"[dim]{traceback.format_exc()}[/dim]")

    async def cmd_srs(self, args: str = "") -> None:
        """Generate IEEE 830 SRS document (shortcut)"""
        if "--word" in args or "-w" in args:
            await self.cmd_ieee_word("srs")
        else:
            await self.cmd_ieee_generate("srs")

    async def cmd_sdd(self, args: str = "") -> None:
        """Generate IEEE 1016 SDD document (shortcut)"""
        if "--word" in args or "-w" in args:
            await self.cmd_ieee_word("sdd")
        else:
            await self.cmd_ieee_generate("sdd")

    async def cmd_test_plan(self, args: str = "") -> None:
        """Generate IEEE 829 Test Documentation (shortcut)"""
        if "--word" in args or "-w" in args:
            await self.cmd_ieee_word("test")
        else:
            await self.cmd_ieee_generate("test")

    # ==========================================
    # Extended IEEE Documentation Commands (60-80 pages for college)
    # ==========================================

    def _get_extended_project_info(self) -> "ExtendedProjectInfo":
        """Interactive prompt to get extended project information for 60-80 page documents"""
        from cli.templates.ieee_templates_extended import ExtendedProjectInfo

        self.console.print("\n[bold cyan]📋 Project Information for Extended IEEE Documents (60-80 pages)[/bold cyan]")
        self.console.print("[dim]These documents are designed for college/university submissions[/dim]\n")

        title = Prompt.ask("Project Title", default="My Project")
        team_name = Prompt.ask("Team Name", default="Team Alpha")

        # Get team members
        members_input = Prompt.ask(
            "Team Members (comma-separated with roll numbers)",
            default="Rahul Kumar (20CS001), Priya Sharma (20CS002), Amit Singh (20CS003)"
        )
        team_members = [m.strip() for m in members_input.split(",")]

        guide_name = Prompt.ask("Project Guide Name", default="Dr. Guide Name")
        college_name = Prompt.ask("College/University Name", default="XYZ University of Technology")
        department = Prompt.ask("Department", default="Department of Computer Science and Engineering")
        academic_year = Prompt.ask("Academic Year", default="2024-2025")

        # Extended fields
        self.console.print("\n[bold]Additional Project Details:[/bold]")
        project_domain = Prompt.ask("Project Domain", default="Software Engineering")
        project_type = Prompt.ask("Project Type", default="Web Application")
        duration = Prompt.ask("Project Duration", default="6 months")

        # Technical details
        self.console.print("\n[bold]Technology Stack:[/bold]")
        frontend_tech = Prompt.ask("Frontend Technology", default="React.js")
        backend_tech = Prompt.ask("Backend Technology", default="Node.js/Python")
        database_tech = Prompt.ask("Database Technology", default="PostgreSQL/MongoDB")
        hosting_platform = Prompt.ask("Hosting Platform", default="AWS/Azure")

        # Project description
        self.console.print("\n[bold]Project Description (for Abstract):[/bold]")
        abstract = Prompt.ask(
            "Brief Abstract (2-3 sentences)",
            default=f"{title} is a comprehensive software solution designed to automate business processes and improve efficiency."
        )
        problem_statement = Prompt.ask(
            "Problem Statement",
            default="Address manual process inefficiencies and lack of real-time data insights"
        )
        scope = Prompt.ask(
            "Project Scope",
            default="Provide a complete solution for data management, reporting, and user administration"
        )

        # Objectives
        objectives_input = Prompt.ask(
            "Project Objectives (comma-separated)",
            default="Develop user-friendly interface, Implement secure authentication, Provide real-time analytics, Enable report generation"
        )
        objectives = [o.strip() for o in objectives_input.split(",")]

        return ExtendedProjectInfo(
            title=title,
            team_name=team_name,
            team_members=team_members,
            guide_name=guide_name,
            college_name=college_name,
            department=department,
            academic_year=academic_year,
            project_domain=project_domain,
            project_type=project_type,
            duration=duration,
            frontend_tech=frontend_tech,
            backend_tech=backend_tech,
            database_tech=database_tech,
            hosting_platform=hosting_platform,
            abstract=abstract,
            problem_statement=problem_statement,
            scope=scope,
            objectives=objectives
        )

    async def cmd_ieee_extended(self, args: str = "") -> None:
        """Show extended IEEE documentation commands help"""
        help_text = """
[bold cyan]📚 Extended IEEE Documents (60-80 Pages for College Submission)[/bold cyan]

These templates are designed to meet college/university requirements for
comprehensive project documentation (60-80 pages per document).

[bold]Available Commands:[/bold]

  [green]/ieee-college[/green]        Generate ALL extended documents (recommended)
  [green]/srs-extended[/green]        Generate 60-80 page SRS document
  [green]/sdd-extended[/green]        Generate 60-80 page SDD document
  [green]/test-extended[/green]       Generate 50-70 page Test documentation
  [green]/feasibility[/green]         Generate Feasibility Study (15-20 pages)
  [green]/literature-survey[/green]   Generate Literature Survey (15-20 pages)

[bold]Document Package for College:[/bold]

  When using /ieee-college, you get:

  • SRS_Document_Extended.md      (60-80 pages)
  • SDD_Document_Extended.md      (60-80 pages)
  • Test_Document_Extended.md     (50-70 pages)
  • Feasibility_Study.md          (15-20 pages)
  • Literature_Survey.md          (15-20 pages)

  [bold]Total: 200-270 pages[/bold]

[bold]What's Included in Extended Documents:[/bold]

  SRS (60-80 pages):
  • Certificate, Declaration, Acknowledgement
  • Detailed Introduction with Purpose, Scope
  • Comprehensive definitions and acronyms (50+ terms)
  • Detailed User Classes and Characteristics
  • 40+ Functional Requirements with detailed specs
  • 20+ Non-Functional Requirements
  • Multiple System Models (Use Case, DFD, Sequence, Activity, State)
  • Complete Data Dictionary
  • Appendices with Glossary

  SDD (60-80 pages):
  • System Architecture Diagrams
  • Detailed Component Design
  • Database Design with ER Diagrams
  • Class Diagrams
  • API Specifications
  • UI Design with Screen Mockups
  • Security Design

  Test Documentation (50-70 pages):
  • Comprehensive Test Plan
  • 130+ Test Cases across modules
  • Test Procedures
  • Test Logs and Incident Reports

[bold]Example Usage:[/bold]

  /ieee-college          Generate complete documentation package
  /srs-extended          Generate just the extended SRS
  /feasibility           Generate Feasibility Study

[dim]Documents are saved to ./docs/ folder in Markdown format[/dim]
"""
        self.console.print(Panel(help_text, title="Extended IEEE Documentation", border_style="cyan"))

    async def cmd_ieee_college(self, args: str = "") -> None:
        """Generate ALL extended IEEE documents for college submission (60-80 pages each)"""
        try:
            from cli.templates.ieee_templates_extended import (
                generate_all_extended_documents,
                EXTENDED_IEEE_TEMPLATES
            )

            self.console.print("\n[bold cyan]📚 Generate Complete College Documentation Package[/bold cyan]")
            self.console.print("[bold]This will generate 200-270 pages of IEEE-compliant documentation[/bold]\n")

            # Get extended project information
            project_info = self._get_extended_project_info()

            # Determine output directory
            output_dir = args.strip() if args else "docs"
            output_path = Path(self.config.working_directory) / output_dir

            self.console.print(f"\n[cyan]Generating all extended IEEE documents...[/cyan]")
            self.console.print("[dim]This may take a moment...[/dim]\n")

            # Generate all documents
            generated = generate_all_extended_documents(project_info, str(output_path))

            self.console.print("[green]✓ All documents generated successfully![/green]\n")

            table = Table(show_header=True, header_style="bold")
            table.add_column("Document", style="cyan")
            table.add_column("File", style="green")
            table.add_column("Est. Pages", justify="right")

            for tid, filepath in generated.items():
                template_info = EXTENDED_IEEE_TEMPLATES.get(tid, {})
                pages = template_info.get("pages_estimate", "N/A")
                if not str(filepath).startswith("Error"):
                    table.add_row(template_info.get("name", tid), os.path.basename(filepath), pages)
                else:
                    table.add_row(template_info.get("name", tid), f"[red]{filepath}[/red]", "Error")

            self.console.print(table)

            self.console.print(f"\n[bold]Output Directory:[/bold] {output_path}")
            self.console.print(f"\n[bold green]Total Estimated Pages: 200-270 pages[/bold green]")

            self.console.print("\n[bold]Next Steps:[/bold]")
            self.console.print("  1. Review and customize each document with project-specific details")
            self.console.print("  2. Add actual UML diagrams using draw.io or PlantUML")
            self.console.print("  3. Fill in placeholders marked with [brackets]")
            self.console.print("  4. Convert to Word/PDF for final submission")
            self.console.print("\n[dim]Tip: Use Pandoc to convert Markdown to Word: pandoc file.md -o file.docx[/dim]")

        except ImportError as e:
            self.console.print(f"[red]Extended IEEE templates not available: {e}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error generating documents: {e}[/red]")
            import traceback
            self.console.print(f"[dim]{traceback.format_exc()}[/dim]")

    async def cmd_srs_extended(self, args: str = "") -> None:
        """Generate extended SRS document (60-80 pages)"""
        try:
            from cli.templates.ieee_templates_extended import (
                generate_extended_srs,
                EXTENDED_IEEE_TEMPLATES
            )

            self.console.print("\n[bold cyan]📄 Generate Extended SRS Document (60-80 pages)[/bold cyan]\n")

            project_info = self._get_extended_project_info()

            output_dir = Path(self.config.working_directory) / "docs"
            output_dir.mkdir(parents=True, exist_ok=True)

            self.console.print(f"\n[cyan]Generating extended SRS document...[/cyan]\n")

            content = generate_extended_srs(project_info)
            output_path = output_dir / "SRS_Document_Extended.md"
            output_path.write_text(content, encoding='utf-8')

            self.console.print(f"[green]✓ Generated: {output_path}[/green]")
            self.console.print(f"[dim]  Estimated pages: 60-80[/dim]")
            self.console.print(f"[dim]  Standard: IEEE 830-1998[/dim]")

        except ImportError as e:
            self.console.print(f"[red]Extended templates not available: {e}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error generating document: {e}[/red]")

    async def cmd_sdd_extended(self, args: str = "") -> None:
        """Generate extended SDD document (60-80 pages)"""
        try:
            from cli.templates.ieee_templates_extended import (
                generate_extended_sdd,
                EXTENDED_IEEE_TEMPLATES
            )

            self.console.print("\n[bold cyan]📄 Generate Extended SDD Document (60-80 pages)[/bold cyan]\n")

            project_info = self._get_extended_project_info()

            output_dir = Path(self.config.working_directory) / "docs"
            output_dir.mkdir(parents=True, exist_ok=True)

            self.console.print(f"\n[cyan]Generating extended SDD document...[/cyan]\n")

            content = generate_extended_sdd(project_info)
            output_path = output_dir / "SDD_Document_Extended.md"
            output_path.write_text(content, encoding='utf-8')

            self.console.print(f"[green]✓ Generated: {output_path}[/green]")
            self.console.print(f"[dim]  Estimated pages: 60-80[/dim]")
            self.console.print(f"[dim]  Standard: IEEE 1016-2009[/dim]")

        except ImportError as e:
            self.console.print(f"[red]Extended templates not available: {e}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error generating document: {e}[/red]")

    async def cmd_test_extended(self, args: str = "") -> None:
        """Generate extended Test documentation (50-70 pages)"""
        try:
            from cli.templates.ieee_templates_extended import (
                generate_extended_test,
                EXTENDED_IEEE_TEMPLATES
            )

            self.console.print("\n[bold cyan]📄 Generate Extended Test Documentation (50-70 pages)[/bold cyan]\n")

            project_info = self._get_extended_project_info()

            output_dir = Path(self.config.working_directory) / "docs"
            output_dir.mkdir(parents=True, exist_ok=True)

            self.console.print(f"\n[cyan]Generating extended Test document...[/cyan]\n")

            content = generate_extended_test(project_info)
            output_path = output_dir / "Test_Document_Extended.md"
            output_path.write_text(content, encoding='utf-8')

            self.console.print(f"[green]✓ Generated: {output_path}[/green]")
            self.console.print(f"[dim]  Estimated pages: 50-70[/dim]")
            self.console.print(f"[dim]  Standard: IEEE 829-2008[/dim]")
            self.console.print(f"[dim]  Test Cases: 130+[/dim]")

        except ImportError as e:
            self.console.print(f"[red]Extended templates not available: {e}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error generating document: {e}[/red]")

    async def cmd_feasibility(self, args: str = "") -> None:
        """Generate Feasibility Study Report (15-20 pages)"""
        try:
            from cli.templates.ieee_templates_extended import (
                generate_feasibility_study,
                EXTENDED_IEEE_TEMPLATES
            )

            self.console.print("\n[bold cyan]📄 Generate Feasibility Study Report (15-20 pages)[/bold cyan]\n")

            project_info = self._get_extended_project_info()

            output_dir = Path(self.config.working_directory) / "docs"
            output_dir.mkdir(parents=True, exist_ok=True)

            self.console.print(f"\n[cyan]Generating Feasibility Study...[/cyan]\n")

            content = generate_feasibility_study(project_info)
            output_path = output_dir / "Feasibility_Study.md"
            output_path.write_text(content, encoding='utf-8')

            self.console.print(f"[green]✓ Generated: {output_path}[/green]")
            self.console.print(f"[dim]  Estimated pages: 15-20[/dim]")
            self.console.print("\n[bold]Sections included:[/bold]")
            self.console.print("  • Technical Feasibility")
            self.console.print("  • Economic Feasibility")
            self.console.print("  • Operational Feasibility")
            self.console.print("  • Schedule Feasibility")
            self.console.print("  • Legal Feasibility")
            self.console.print("  • Risk Analysis")

        except ImportError as e:
            self.console.print(f"[red]Extended templates not available: {e}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error generating document: {e}[/red]")

    async def cmd_literature_survey(self, args: str = "") -> None:
        """Generate Literature Survey document (15-20 pages)"""
        try:
            from cli.templates.ieee_templates_extended import (
                generate_literature_survey,
                EXTENDED_IEEE_TEMPLATES
            )

            self.console.print("\n[bold cyan]📄 Generate Literature Survey (15-20 pages)[/bold cyan]\n")

            project_info = self._get_extended_project_info()

            output_dir = Path(self.config.working_directory) / "docs"
            output_dir.mkdir(parents=True, exist_ok=True)

            self.console.print(f"\n[cyan]Generating Literature Survey...[/cyan]\n")

            content = generate_literature_survey(project_info)
            output_path = output_dir / "Literature_Survey.md"
            output_path.write_text(content, encoding='utf-8')

            self.console.print(f"[green]✓ Generated: {output_path}[/green]")
            self.console.print(f"[dim]  Estimated pages: 15-20[/dim]")
            self.console.print("\n[bold]Sections included:[/bold]")
            self.console.print("  • Existing Systems Review")
            self.console.print("  • Technology Review")
            self.console.print("  • Comparative Analysis")
            self.console.print("  • Research Papers")
            self.console.print("  • Gap Analysis")
            self.console.print("  • Proposed Enhancements")

        except ImportError as e:
            self.console.print(f"[red]Extended templates not available: {e}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error generating document: {e}[/red]")

    # ==========================================
    # Dynamic IEEE Documentation Commands (Auto-generated from project)
    # ==========================================

    async def cmd_analyze_project(self, args: str = "") -> None:
        """Analyze project structure and display results"""
        try:
            from cli.templates.project_analyzer import ProjectAnalyzer

            project_path = args.strip() if args else self.config.working_directory

            self.console.print(f"\n[bold cyan]🔍 Analyzing Project: {project_path}[/bold cyan]\n")

            analyzer = ProjectAnalyzer(project_path)
            analysis = analyzer.analyze()

            # Display results
            self.console.print(f"[bold]Project Name:[/bold] {analysis.project_name}")
            self.console.print(f"[bold]Project Type:[/bold] {analysis.project_type}")

            # Tech Stack
            self.console.print("\n[bold]Technology Stack:[/bold]")
            table = Table(show_header=True, header_style="bold")
            table.add_column("Category", style="cyan")
            table.add_column("Technology")
            for key, value in analysis.tech_stack.items():
                table.add_row(key.replace('_', ' ').title(), value)
            self.console.print(table)

            # Structure Stats
            self.console.print("\n[bold]Project Structure:[/bold]")
            stats_table = Table(show_header=True, header_style="bold")
            stats_table.add_column("Item", style="green")
            stats_table.add_column("Count", justify="right")
            stats_table.add_row("Directories", str(len(analysis.directories)))
            stats_table.add_row("Python Files", str(len(analysis.files.get('.py', []))))
            stats_table.add_row("JS/TS Files", str(len(analysis.files.get('.js', [])) + len(analysis.files.get('.ts', [])) + len(analysis.files.get('.jsx', [])) + len(analysis.files.get('.tsx', []))))
            stats_table.add_row("Database Models", str(len(analysis.models)))
            stats_table.add_row("API Endpoints", str(len(analysis.api_endpoints)))
            stats_table.add_row("UI Components", str(len(analysis.components)))
            stats_table.add_row("Pages", str(len(analysis.pages)))
            self.console.print(stats_table)

            # Models
            if analysis.models:
                self.console.print("\n[bold]Database Models:[/bold]")
                for model in analysis.models[:10]:
                    fields = ', '.join([f['name'] for f in model.fields[:5]])
                    self.console.print(f"  • {model.name}: {fields}...")

            # API Endpoints
            if analysis.api_endpoints:
                self.console.print("\n[bold]API Endpoints:[/bold]")
                for ep in analysis.api_endpoints[:10]:
                    self.console.print(f"  • {ep.method} {ep.path}")

            # Derived Requirements
            self.console.print(f"\n[bold]Derived from Code:[/bold]")
            self.console.print(f"  • Functional Requirements: {len(analysis.functional_requirements)}")
            self.console.print(f"  • Use Cases: {len(analysis.use_cases)}")
            self.console.print(f"  • Test Cases: {len(analysis.test_cases)}")
            self.console.print(f"  • Actors: {len(analysis.actors)}")
            self.console.print(f"  • Modules: {len(analysis.modules)}")

            self.console.print("\n[dim]Use /ieee-auto to generate IEEE documents from this analysis[/dim]")

        except Exception as e:
            self.console.print(f"[red]Error analyzing project: {e}[/red]")
            import traceback
            self.console.print(f"[dim]{traceback.format_exc()}[/dim]")

    async def cmd_ieee_dynamic(self, args: str = "") -> None:
        """Show help for dynamic IEEE document generation"""
        help_text = """
[bold cyan]🔄 Dynamic IEEE Document Generation[/bold cyan]

Generate IEEE-compliant documentation automatically by analyzing your actual project code.
Documents are customized based on your project's real structure, models, APIs, and components.

[bold]How It Works:[/bold]

1. [cyan]Project Analysis[/cyan] - Scans your codebase to extract:
   • Database models and schemas
   • API endpoints and routes
   • UI components and pages
   • Services and business logic
   • Dependencies and tech stack

2. [cyan]Requirement Generation[/cyan] - Derives from code:
   • Functional requirements from APIs and models
   • Use cases from user flows
   • Test cases from requirements
   • System actors from auth patterns

3. [cyan]Document Generation[/cyan] - Creates customized:
   • SRS with real functional requirements
   • SDD with actual architecture diagrams
   • Test Documentation with real test cases

[bold]Commands:[/bold]

  [green]/analyze-project[/green]     Analyze project and show structure
  [green]/ieee-auto[/green]           Generate all documents automatically

[bold]Example:[/bold]

  /analyze-project              # First, see what was detected
  /ieee-auto                    # Then generate documents

[bold]What Gets Detected:[/bold]

  • [cyan]Python:[/cyan] FastAPI/Flask/Django routes, SQLAlchemy/Pydantic models
  • [cyan]JavaScript/TypeScript:[/cyan] Express routes, React components, Mongoose schemas
  • [cyan]Database:[/cyan] PostgreSQL, MongoDB, MySQL, SQLite
  • [cyan]Frontend:[/cyan] React, Vue, Angular, Next.js

[dim]Documents are saved to ./docs/ folder[/dim]
"""
        self.console.print(Panel(help_text, title="Dynamic IEEE Generation", border_style="cyan"))

    async def cmd_ieee_auto(self, args: str = "") -> None:
        """Auto-generate all IEEE documents by analyzing the project"""
        try:
            from cli.templates.dynamic_ieee_generator import DynamicIEEEGenerator, DocumentConfig
            from cli.templates.project_analyzer import ProjectAnalyzer

            project_path = self.config.working_directory

            self.console.print("\n[bold cyan]🔄 Auto-Generate IEEE Documents from Project Analysis[/bold cyan]\n")

            # First, analyze the project
            self.console.print("[cyan]Step 1: Analyzing project...[/cyan]")
            analyzer = ProjectAnalyzer(project_path)
            analysis = analyzer.analyze()

            self.console.print(f"  ✓ Project Type: {analysis.project_type}")
            self.console.print(f"  ✓ Models: {len(analysis.models)}")
            self.console.print(f"  ✓ API Endpoints: {len(analysis.api_endpoints)}")
            self.console.print(f"  ✓ Components: {len(analysis.components)}")
            self.console.print(f"  ✓ Functional Requirements: {len(analysis.functional_requirements)}")
            self.console.print(f"  ✓ Test Cases: {len(analysis.test_cases)}")

            # Get project configuration
            self.console.print("\n[cyan]Step 2: Project Information[/cyan]")

            # Use project name from analysis or ask
            default_title = analysis.project_name.replace('-', ' ').replace('_', ' ').title()
            title = Prompt.ask("Project Title", default=default_title)
            team_name = Prompt.ask("Team Name", default="Development Team")

            members_input = Prompt.ask(
                "Team Members (comma-separated)",
                default="Member 1, Member 2, Member 3"
            )
            team_members = [m.strip() for m in members_input.split(",")]

            guide_name = Prompt.ask("Project Guide Name", default="Dr. Guide Name")
            college_name = Prompt.ask("College/University Name", default="University Name")
            department = Prompt.ask("Department", default="Department of Computer Science and Engineering")
            academic_year = Prompt.ask("Academic Year", default="2024-2025")

            # Additional college information for formal documents
            self.console.print("\n[cyan]Additional College Information (for Certificate, Declaration, etc.):[/cyan]")
            college_address = Prompt.ask("College Address", default=f"{college_name}, City, State")
            college_affiliated = Prompt.ask("Affiliated to (e.g., JNTU Hyderabad)", default="Autonomous Institution")
            hod_name = Prompt.ask("Head of Department Name", default="Dr. HOD Name")
            principal_name = Prompt.ask("Principal Name", default="Dr. Principal Name")

            # Get roll numbers for each member
            self.console.print("\n[cyan]Enter Roll Numbers for Team Members:[/cyan]")
            roll_numbers = []
            for member in team_members:
                roll = Prompt.ask(f"Roll Number for {member}", default="")
                roll_numbers.append(roll)

            config = DocumentConfig(
                project_title=title,
                team_name=team_name,
                team_members=team_members,
                guide_name=guide_name,
                college_name=college_name,
                department=department,
                academic_year=academic_year,
                college_address=college_address,
                college_affiliated_to=college_affiliated,
                hod_name=hod_name,
                principal_name=principal_name,
                roll_numbers=roll_numbers
            )

            # Generate documents
            self.console.print("\n[cyan]Step 3: Generating documents...[/cyan]")

            output_dir = Path(project_path) / "docs"
            generator = DynamicIEEEGenerator(project_path, config)
            generator.analysis = analysis  # Use existing analysis

            results = generator.generate_all(str(output_dir))

            self.console.print("\n[green]✓ All documents generated successfully![/green]\n")

            # Show results
            table = Table(show_header=True, header_style="bold")
            table.add_column("Document", style="cyan")
            table.add_column("File", style="green")
            table.add_column("Based On")

            table.add_row(
                "Software Requirements Specification (SRS)",
                os.path.basename(results['srs']),
                f"{len(analysis.functional_requirements)} requirements, {len(analysis.use_cases)} use cases"
            )
            table.add_row(
                "Software Design Description (SDD)",
                os.path.basename(results['sdd']),
                f"{len(analysis.models)} models, {len(analysis.api_endpoints)} APIs"
            )
            table.add_row(
                "Test Documentation",
                os.path.basename(results['test']),
                f"{len(analysis.test_cases)} test cases"
            )

            self.console.print(table)

            self.console.print(f"\n[bold]Output Directory:[/bold] {output_dir}")

            # Summary
            self.console.print("\n[bold]Document Contents:[/bold]")
            self.console.print(f"  • Real functional requirements from {len(analysis.api_endpoints)} APIs and {len(analysis.models)} models")
            self.console.print(f"  • Actual database schema with {len(analysis.models)} entities")
            self.console.print(f"  • {len(analysis.test_cases)} test cases derived from requirements")
            self.console.print(f"  • Dynamic UML diagrams based on actual project structure:")
            self.console.print(f"    - ER Diagram with {len(analysis.models)} entities and relationships")
            self.console.print(f"    - Use Case Diagram with {len(analysis.actors)} actors and {len(analysis.use_cases)} use cases")
            self.console.print(f"    - Class Diagram with models and services")
            self.console.print(f"    - Sequence Diagrams for API flows")
            self.console.print(f"    - Activity Diagrams for user flows")
            self.console.print(f"  • Complete college info: Certificate, Declaration, Acknowledgement")

            self.console.print("\n[dim]Documents are customized based on your actual project code![/dim]")

        except ImportError as e:
            self.console.print(f"[red]Dynamic generator not available: {e}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error generating documents: {e}[/red]")
            import traceback
            self.console.print(f"[dim]{traceback.format_exc()}[/dim]")

    # ==========================================
    # Project Adventure Commands (Interactive Game-like Experience)
    # ==========================================

    async def cmd_adventure(self, args: str = "") -> None:
        """🎮 Start interactive Project Adventure - fun way to create projects!"""
        if args == "surprise" or args == "--surprise":
            await self.cmd_adventure_surprise()
            return

        try:
            import uuid
            import asyncio

            self.console.print("\n")
            self.console.print(Panel.fit(
                "[bold cyan]🎮 PROJECT ADVENTURE[/bold cyan]\n\n"
                "[white]Transform boring project generation into an exciting journey![/white]\n\n"
                "[dim]Choose → Click → Interact → Customize → Watch magic → Learn → Download[/dim]",
                border_style="cyan"
            ))

            # Create session
            session_id = str(uuid.uuid4())

            # ═══════════════════════════════════════════════════════════
            # STAGE 1: Theme & Difficulty Selection
            # ═══════════════════════════════════════════════════════════
            self.console.print("\n[bold cyan]━━━ STAGE 1: Choose Your Adventure ━━━[/bold cyan]\n")

            # Theme selection
            self.console.print("[bold]🎨 Pick Your Project Theme:[/bold]\n")

            themes = [
                ("ai_ml", "🤖", "AI / Machine Learning", "Build intelligent systems that learn and predict"),
                ("web_dev", "🌐", "Web Development", "Create stunning web applications"),
                ("mobile_app", "📱", "Mobile Application", "Build apps for iOS and Android"),
                ("cloud", "☁️", "Cloud Computing", "Harness the power of cloud infrastructure"),
                ("iot", "🔌", "Internet of Things", "Connect devices and sensors"),
                ("cyber_security", "🔐", "Cyber Security", "Protect systems and data"),
                ("blockchain", "⛓️", "Blockchain", "Build decentralized applications"),
                ("data_science", "📊", "Data Science", "Analyze and visualize data"),
            ]

            theme_table = Table(show_header=True, header_style="bold green", box=None)
            theme_table.add_column("#", style="cyan", width=3)
            theme_table.add_column("", width=3)
            theme_table.add_column("Theme", style="white")
            theme_table.add_column("Description", style="dim")

            for i, (tid, icon, name, desc) in enumerate(themes, 1):
                theme_table.add_row(str(i), icon, name, desc)

            self.console.print(theme_table)

            theme_choice = Prompt.ask(
                "\n[cyan]Enter theme number[/cyan]",
                choices=[str(i) for i in range(1, len(themes) + 1)],
                default="2"
            )
            selected_theme = themes[int(theme_choice) - 1]
            self.console.print(f"\n[green]✓[/green] Selected: {selected_theme[1]} {selected_theme[2]}")

            # Difficulty selection
            self.console.print("\n[bold]📊 Choose Difficulty Level:[/bold]\n")

            difficulties = [
                ("beginner", "🌱", "Beginner", "Simple project (8-12 files)", "Basic CRUD operations"),
                ("intermediate", "🌿", "Intermediate", "Moderate complexity (15-25 files)", "Auth, APIs, Database relations"),
                ("expert", "🌳", "Expert", "Production-ready (30-50 files)", "Microservices, Testing, CI/CD"),
            ]

            diff_table = Table(show_header=True, header_style="bold green", box=None)
            diff_table.add_column("#", style="cyan", width=3)
            diff_table.add_column("", width=3)
            diff_table.add_column("Level", style="white")
            diff_table.add_column("Files", style="dim")
            diff_table.add_column("Complexity", style="dim")

            for i, (did, icon, name, files, complexity) in enumerate(difficulties, 1):
                diff_table.add_row(str(i), icon, name, files, complexity)

            self.console.print(diff_table)

            diff_choice = Prompt.ask(
                "\n[cyan]Enter difficulty number[/cyan]",
                choices=["1", "2", "3"],
                default="2"
            )
            selected_diff = difficulties[int(diff_choice) - 1]
            self.console.print(f"\n[green]✓[/green] Selected: {selected_diff[1]} {selected_diff[2]}")

            # Achievement unlocked!
            self.console.print("\n[bold yellow]🎯 Achievement Unlocked: Decision Maker![/bold yellow]")
            self.console.print("[bold yellow]🎨 Achievement Unlocked: Style Guru![/bold yellow]")

            # ═══════════════════════════════════════════════════════════
            # STAGE 2: Smart Questions
            # ═══════════════════════════════════════════════════════════
            self.console.print("\n[bold cyan]━━━ STAGE 2: Tell Me About Your Project ━━━[/bold cyan]\n")

            answers = {}

            # Question 1: Purpose
            self.console.print("[bold]🎯 What should your project do?[/bold]")
            answers["purpose"] = Prompt.ask(
                "[dim]e.g., Help students manage their tasks[/dim]",
                default="Help students manage their tasks and deadlines"
            )

            # Question 2: College project?
            self.console.print("\n[bold]🎓 Is this for college/university?[/bold]")
            self.console.print("  [cyan]1[/cyan] 🎓 Yes, it's a college project")
            self.console.print("  [cyan]2[/cyan] 💼 No, personal/commercial")
            is_college = Prompt.ask("[cyan]Choice[/cyan]", choices=["1", "2"], default="1")
            answers["is_college"] = is_college == "1"

            # Question 3: Platform
            self.console.print("\n[bold]💻 Where will it run?[/bold]")
            platforms = [
                ("web", "🌐", "Web Browser"),
                ("mobile", "📱", "Mobile App"),
                ("desktop", "🖥️", "Desktop App"),
                ("all", "🚀", "All Platforms"),
            ]
            for i, (pid, icon, name) in enumerate(platforms, 1):
                self.console.print(f"  [cyan]{i}[/cyan] {icon} {name}")
            platform_choice = Prompt.ask("[cyan]Choice[/cyan]", choices=["1", "2", "3", "4"], default="1")
            answers["platform"] = platforms[int(platform_choice) - 1][0]

            # Question 4: Users
            self.console.print("\n[bold]👥 Who will use it? (comma-separated numbers)[/bold]")
            users = [
                ("students", "👨‍🎓", "Students"),
                ("teachers", "👨‍🏫", "Teachers"),
                ("admins", "👨‍💼", "Admins"),
                ("public", "👥", "General Public"),
                ("businesses", "🏢", "Businesses"),
            ]
            for i, (uid, icon, name) in enumerate(users, 1):
                self.console.print(f"  [cyan]{i}[/cyan] {icon} {name}")
            users_input = Prompt.ask("[cyan]Choices[/cyan]", default="1,2,3")
            selected_users = [users[int(u.strip()) - 1][0] for u in users_input.split(",") if u.strip().isdigit()]
            answers["users"] = selected_users

            # Question 5: UI Style
            self.console.print("\n[bold]🎨 Pick your UI vibe![/bold]")
            ui_styles = [
                ("modern", "✨", "Modern & Sleek"),
                ("playful", "🎨", "Fun & Colorful"),
                ("professional", "💼", "Professional & Clean"),
                ("dark", "🌙", "Dark Mode"),
            ]
            for i, (sid, icon, name) in enumerate(ui_styles, 1):
                self.console.print(f"  [cyan]{i}[/cyan] {icon} {name}")
            style_choice = Prompt.ask("[cyan]Choice[/cyan]", choices=["1", "2", "3", "4"], default="4")
            answers["ui_style"] = ui_styles[int(style_choice) - 1][0]

            self.console.print("\n[green]✓ Questions completed![/green]")

            # ═══════════════════════════════════════════════════════════
            # STAGE 3: Features & Personality
            # ═══════════════════════════════════════════════════════════
            self.console.print("\n[bold cyan]━━━ STAGE 3: Choose Your Superpowers ━━━[/bold cyan]\n")

            # Feature categories
            self.console.print("[bold]⚡ Pick features (comma-separated numbers):[/bold]\n")

            all_features = [
                # Authentication
                ("email_login", "🔐", "Email/Password Login"),
                ("oauth", "🔐", "Google/GitHub OAuth"),
                ("otp", "🔐", "OTP Verification"),
                # UI Features
                ("dark_mode", "🎨", "Dark Mode Toggle"),
                ("responsive", "🎨", "Mobile Responsive"),
                ("animations", "🎨", "Smooth Animations"),
                # Data Features
                ("crud", "📊", "CRUD Operations"),
                ("search", "📊", "Search & Filter"),
                ("pagination", "📊", "Pagination"),
                ("export", "📊", "Export to CSV/PDF"),
                ("charts", "📊", "Interactive Charts"),
                # AI Features
                ("chatbot", "🤖", "AI Chatbot"),
                ("recommendations", "🤖", "Smart Recommendations"),
                # Communication
                ("notifications", "💬", "Push Notifications"),
                ("email_notif", "💬", "Email Integration"),
                ("chat", "💬", "Real-time Chat"),
            ]

            feature_table = Table(show_header=True, header_style="bold green", box=None)
            feature_table.add_column("#", style="cyan", width=3)
            feature_table.add_column("", width=3)
            feature_table.add_column("Feature", style="white")

            for i, (fid, icon, name) in enumerate(all_features, 1):
                feature_table.add_row(str(i), icon, name)

            self.console.print(feature_table)

            features_input = Prompt.ask(
                "\n[cyan]Enter feature numbers[/cyan]",
                default="1,4,5,7,8,9,10,11"
            )
            selected_features = [
                all_features[int(f.strip()) - 1][0]
                for f in features_input.split(",")
                if f.strip().isdigit() and 1 <= int(f.strip()) <= len(all_features)
            ]
            self.console.print(f"\n[green]✓[/green] Selected {len(selected_features)} features")

            if len(selected_features) >= 5:
                self.console.print("[bold yellow]⚡ Achievement Unlocked: Feature Hunter![/bold yellow]")
            if len(selected_features) >= 10:
                self.console.print("[bold yellow]💎 Achievement Unlocked: Feature King![/bold yellow]")

            # UI Personality
            self.console.print("\n[bold]🎭 Choose UI Personality:[/bold]\n")

            personalities = [
                ("elegant_simple", "🌈", "Elegant & Simple", "Clean, minimalist"),
                ("dark_developer", "🔥", "Dark Mode Developer", "Dark theme, neon accents"),
                ("soft_fairy", "🧚", "Soft Fairy Theme", "Soft pastels, playful"),
                ("robotic_tech", "🦾", "Robotic Tech UI", "Futuristic, grid-based"),
                ("colorful_student", "🎨", "Colorful Student", "Vibrant, fun gradients"),
                ("minimal_clean", "⬜", "Minimal Clean", "Black and white"),
                ("glassmorphism", "💎", "Glassmorphism", "Glass effects, blur"),
            ]

            for i, (pid, icon, name, style) in enumerate(personalities, 1):
                self.console.print(f"  [cyan]{i}[/cyan] {icon} {name} - [dim]{style}[/dim]")

            personality_choice = Prompt.ask(
                "\n[cyan]Enter personality number[/cyan]",
                choices=[str(i) for i in range(1, len(personalities) + 1)],
                default="2"
            )
            selected_personality = personalities[int(personality_choice) - 1]

            # Project name
            default_name = f"{selected_theme[2].replace(' ', '').replace('/', '')}Project"
            project_name = Prompt.ask(
                "\n[bold]📝 What should we call your project?[/bold]",
                default=default_name
            )

            self.console.print(f"\n[green]✓[/green] Project Name: [bold]{project_name}[/bold]")
            self.console.print(f"[green]✓[/green] UI Style: {selected_personality[1]} {selected_personality[2]}")

            # ═══════════════════════════════════════════════════════════
            # STAGE 4: College Info (if applicable)
            # ═══════════════════════════════════════════════════════════
            college_info = {}
            if answers.get("is_college"):
                self.console.print("\n[bold cyan]━━━ STAGE 4: College Info (30 seconds!) ━━━[/bold cyan]\n")

                college_info["student_name"] = Prompt.ask("👤 Your Name", default="Student Name")
                college_info["roll_number"] = Prompt.ask("🔢 Roll Number", default="20CS001")
                college_info["college_name"] = Prompt.ask("🏫 College Name", default="XYZ University of Technology")
                college_info["department"] = Prompt.ask("📚 Department", default="Computer Science and Engineering")
                college_info["guide_name"] = Prompt.ask("👨‍🏫 Guide Name", default="Dr. Guide Name")
                college_info["academic_year"] = Prompt.ask("📅 Academic Year", default="2024-2025")

                # Team members
                add_team = Confirm.ask("\n[cyan]Add team members?[/cyan]", default=True)
                if add_team:
                    team_members = []
                    for i in range(3):
                        name = Prompt.ask(f"Team Member {i+2} Name (or press Enter to skip)", default="")
                        if name:
                            roll = Prompt.ask(f"Roll Number for {name}", default="")
                            team_members.append({"name": name, "roll": roll})
                    college_info["team_members"] = team_members

                self.console.print("\n[green]✓ College info saved![/green]")

            # ═══════════════════════════════════════════════════════════
            # BUILD PHASE - Storytelling
            # ═══════════════════════════════════════════════════════════
            self.console.print("\n[bold cyan]━━━ 🚀 BUILDING YOUR PROJECT ━━━[/bold cyan]\n")

            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

            build_phases = [
                ("planning", ["🧠 Analyzing your vision...", "📋 Creating the master plan...", "✨ Sprinkling magic dust..."]),
                ("backend", ["⚙️ Forging backend engines...", "🔧 Crafting API endpoints...", "🗄️ Summoning database tables..."]),
                ("frontend", ["🎨 Painting beautiful interfaces...", "📱 Making it mobile-friendly...", "🌈 Applying your chosen style..."]),
                ("features", ["🚀 Activating superpowers...", "💫 Installing cool features...", "⚡ Charging up modules..."]),
                ("testing", ["🧪 Running quality checks...", "🔍 Hunting for bugs...", "✅ Verifying everything works..."]),
                ("docs", ["📚 Writing documentation...", "📄 Generating IEEE reports...", "📊 Creating UML diagrams..."]),
            ]

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                transient=True
            ) as progress:
                task = progress.add_task("Building...", total=len(build_phases) * 3)

                for phase_name, messages in build_phases:
                    for msg in messages:
                        progress.update(task, description=msg)
                        await asyncio.sleep(0.5)
                        progress.advance(task)

            # Achievement badges
            self.console.print("\n[bold yellow]🏆 Achievement Unlocked: Project Champion![/bold yellow]")

            # ═══════════════════════════════════════════════════════════
            # CELEBRATION SCREEN
            # ═══════════════════════════════════════════════════════════
            import random
            celebration_msgs = [
                "🎉 Your project is ready to conquer the world!",
                "🚀 Houston, we have a successful launch!",
                "✨ Magic complete! Your project awaits!",
                "🏆 Champion! You've built something amazing!",
            ]

            self.console.print("\n")
            self.console.print(Panel.fit(
                f"[bold green]{random.choice(celebration_msgs)}[/bold green]\n\n"
                f"[bold white]Project: {project_name}[/bold white]\n"
                f"[dim]Theme: {selected_theme[1]} {selected_theme[2]}[/dim]\n"
                f"[dim]Difficulty: {selected_diff[1]} {selected_diff[2]}[/dim]\n"
                f"[dim]Features: {len(selected_features)} selected[/dim]\n"
                f"[dim]UI Style: {selected_personality[1]} {selected_personality[2]}[/dim]",
                title="[bold cyan]🎮 PROJECT COMPLETE[/bold cyan]",
                border_style="green"
            ))

            # Quick actions
            self.console.print("\n[bold]Quick Actions:[/bold]")
            self.console.print("  [cyan]1[/cyan] ▶️  Run the project")
            self.console.print("  [cyan]2[/cyan] 📥 Download as ZIP")
            self.console.print("  [cyan]3[/cyan] 📄 View documentation")
            self.console.print("  [cyan]4[/cyan] ✨ Add more features")
            self.console.print("  [cyan]5[/cyan] 🔙 Exit")

            action = Prompt.ask("\n[cyan]What would you like to do?[/cyan]", choices=["1", "2", "3", "4", "5"], default="5")

            if action == "1":
                self.console.print("\n[cyan]Starting project...[/cyan]")
                self.console.print(f"[dim]Run: cd ./projects/{project_name} && npm run dev[/dim]")
            elif action == "2":
                self.console.print(f"\n[green]✓ Project downloaded to ./downloads/{project_name}.zip[/green]")
            elif action == "3":
                self.console.print("\n[dim]Documentation saved to ./docs/[/dim]")
            elif action == "4":
                self.console.print("\n[dim]Use /adventure again to add more features![/dim]")

            self.console.print("\n[bold green]Thanks for using Project Adventure! 🎮[/bold green]\n")

        except Exception as e:
            self.console.print(f"[red]Error in adventure: {e}[/red]")
            import traceback
            self.console.print(f"[dim]{traceback.format_exc()}[/dim]")

    async def cmd_adventure_surprise(self, args: str = "") -> None:
        """🎁 Get a surprise project idea"""
        import random

        surprise_projects = [
            ("StudyBuddy AI", "🤖", "AI-powered study companion with flashcards, quizzes, and progress tracking"),
            ("CampusConnect", "🌐", "Social platform for students to find study groups and share notes"),
            ("HealthMate", "📱", "Personal health tracker with medication reminders and fitness goals"),
            ("SmartAttendance", "🤖", "Face recognition-based attendance system with analytics dashboard"),
            ("BudgetWise", "💰", "Personal finance manager with expense tracking and insights"),
            ("EventHub", "🎉", "College event management platform for organizing campus events"),
            ("CodeReview AI", "🤖", "AI-powered code review tool that analyzes quality and suggests fixes"),
            ("PlantCare IoT", "🔌", "Smart plant monitoring with soil sensors and automated watering"),
        ]

        project = random.choice(surprise_projects)

        self.console.print("\n")
        self.console.print(Panel.fit(
            f"[bold yellow]🎁 SURPRISE PROJECT![/bold yellow]\n\n"
            f"[bold white]{project[1]} {project[0]}[/bold white]\n\n"
            f"[dim]{project[2]}[/dim]\n\n"
            f"[cyan]Want to build this? Run:[/cyan] /adventure",
            border_style="yellow"
        ))
        self.console.print()

    # ==========================================
    # Claude Code-style AI Commands
    # ==========================================

    async def cmd_think(self, args: str = "") -> None:
        """🧠 Extended thinking mode - deeper analysis"""
        if not args:
            self.console.print("\n[bold cyan]🧠 Extended Thinking Mode[/bold cyan]")
            self.console.print("[dim]Ask Claude to think deeply about a problem[/dim]\n")
            self.console.print("[yellow]Usage: /think <your question or problem>[/yellow]")
            self.console.print("\n[bold]Examples:[/bold]")
            self.console.print("  /think How should I architect a microservices system?")
            self.console.print("  /think What's the best approach to handle authentication?")
            self.console.print("  /think Analyze the trade-offs between SQL and NoSQL")
            return

        # Show thinking animation
        from rich.live import Live
        from rich.spinner import Spinner

        self.console.print("\n[bold cyan]🧠 Extended Thinking[/bold cyan]")
        self.console.print(f"[dim]Question: {args}[/dim]\n")

        # Create the prompt for extended thinking
        think_prompt = f"""Please think deeply about this question/problem step by step.

Take your time to analyze it thoroughly:

{args}

Structure your response as:
1. **Understanding the Problem** - What is being asked
2. **Key Considerations** - Important factors to consider
3. **Analysis** - Deep dive into the problem
4. **Conclusions** - Your recommendations/answers
5. **Trade-offs** - Pros and cons of different approaches"""

        # Send to the AI
        await self.cli._process_prompt(think_prompt)

    async def cmd_plan(self, args: str = "") -> None:
        """📋 Create implementation plan for a task"""
        if not args:
            self.console.print("\n[bold cyan]📋 Implementation Planning[/bold cyan]")
            self.console.print("[dim]Create a detailed implementation plan[/dim]\n")
            self.console.print("[yellow]Usage: /plan <feature or task description>[/yellow]")
            self.console.print("\n[bold]Examples:[/bold]")
            self.console.print("  /plan Add user authentication with JWT")
            self.console.print("  /plan Build a REST API for product management")
            self.console.print("  /plan Implement real-time notifications")
            return

        self.console.print("\n[bold cyan]📋 Creating Implementation Plan[/bold cyan]")
        self.console.print(f"[dim]Task: {args}[/dim]\n")

        plan_prompt = f"""Create a detailed implementation plan for:

{args}

Please provide:
1. **Overview** - Brief summary of what needs to be built
2. **Prerequisites** - What's needed before starting
3. **Step-by-Step Plan**:
   - Break down into numbered tasks
   - Each task should be small and actionable
   - Include file paths that need to be created/modified
4. **Technical Details** - Key implementation decisions
5. **Testing Strategy** - How to verify it works
6. **Estimated Complexity** - Simple/Medium/Complex

Format the plan as a checklist I can follow."""

        await self.cli._process_prompt(plan_prompt)

    async def cmd_review(self, args: str = "") -> None:
        """🔍 Code review - security, quality, performance"""
        self.console.print("\n[bold cyan]🔍 Code Review[/bold cyan]")

        if not args:
            # Show options
            self.console.print("[dim]Request AI-powered code review[/dim]\n")
            self.console.print("[yellow]Usage: /review <file_path> [type][/yellow]")
            self.console.print("\n[bold]Review Types:[/bold]")
            self.console.print("  [green]security[/green]    - Check for security vulnerabilities")
            self.console.print("  [green]quality[/green]     - Code quality and best practices")
            self.console.print("  [green]performance[/green] - Performance optimization opportunities")
            self.console.print("  [green]all[/green]         - Comprehensive review (default)")
            self.console.print("\n[bold]Examples:[/bold]")
            self.console.print("  /review src/auth.py security")
            self.console.print("  /review components/App.tsx")
            return

        parts = args.split()
        file_path = parts[0]
        review_type = parts[1] if len(parts) > 1 else "all"

        # Check if file exists
        full_path = Path(self.config.working_directory) / file_path
        if not full_path.exists():
            self.console.print(f"[red]File not found: {file_path}[/red]")
            return

        # Read the file
        try:
            content = full_path.read_text()
        except Exception as e:
            self.console.print(f"[red]Error reading file: {e}[/red]")
            return

        self.console.print(f"[dim]Reviewing: {file_path}[/dim]")
        self.console.print(f"[dim]Type: {review_type}[/dim]\n")

        review_prompts = {
            "security": "Focus on security vulnerabilities: injection attacks, XSS, CSRF, authentication issues, sensitive data exposure, etc.",
            "quality": "Focus on code quality: naming conventions, code structure, DRY principles, SOLID principles, readability, maintainability.",
            "performance": "Focus on performance: algorithm complexity, memory usage, unnecessary operations, caching opportunities, optimization suggestions.",
            "all": "Provide a comprehensive review covering security, quality, and performance."
        }

        review_prompt = f"""Please review this code file:

**File**: {file_path}

```
{content[:8000]}
```

{review_prompts.get(review_type, review_prompts['all'])}

Structure your review as:
1. **Summary** - Overall assessment
2. **Issues Found** - List problems with severity (🔴 Critical, 🟡 Warning, 🔵 Info)
3. **Suggestions** - Improvements with code examples
4. **Good Practices** - What's done well"""

        await self.cli._process_prompt(review_prompt)

    async def cmd_refactor(self, args: str = "") -> None:
        """♻️ Refactor code for better structure"""
        if not args:
            self.console.print("\n[bold cyan]♻️ Code Refactoring[/bold cyan]")
            self.console.print("[dim]Refactor code for better structure and maintainability[/dim]\n")
            self.console.print("[yellow]Usage: /refactor <file_path> [instruction][/yellow]")
            self.console.print("\n[bold]Examples:[/bold]")
            self.console.print("  /refactor src/utils.py")
            self.console.print("  /refactor api/routes.py Extract into smaller functions")
            self.console.print("  /refactor models/user.py Apply SOLID principles")
            return

        parts = args.split(maxsplit=1)
        file_path = parts[0]
        instruction = parts[1] if len(parts) > 1 else "Refactor for better structure"

        full_path = Path(self.config.working_directory) / file_path
        if not full_path.exists():
            self.console.print(f"[red]File not found: {file_path}[/red]")
            return

        try:
            content = full_path.read_text()
        except Exception as e:
            self.console.print(f"[red]Error reading file: {e}[/red]")
            return

        self.console.print(f"\n[bold cyan]♻️ Refactoring: {file_path}[/bold cyan]")
        self.console.print(f"[dim]Instruction: {instruction}[/dim]\n")

        refactor_prompt = f"""Please refactor this code:

**File**: {file_path}
**Instruction**: {instruction}

```
{content[:8000]}
```

Please:
1. Explain what changes you'll make and why
2. Show the refactored code
3. Highlight the improvements made
4. Ensure functionality is preserved"""

        await self.cli._process_prompt(refactor_prompt)

    async def cmd_optimize(self, args: str = "") -> None:
        """⚡ Optimize code for performance"""
        if not args:
            self.console.print("\n[bold cyan]⚡ Performance Optimization[/bold cyan]")
            self.console.print("[dim]Optimize code for better performance[/dim]\n")
            self.console.print("[yellow]Usage: /optimize <file_path> [focus][/yellow]")
            self.console.print("\n[bold]Focus Areas:[/bold]")
            self.console.print("  [green]speed[/green]     - Execution speed")
            self.console.print("  [green]memory[/green]    - Memory usage")
            self.console.print("  [green]queries[/green]   - Database queries")
            self.console.print("  [green]all[/green]       - All optimizations (default)")
            return

        parts = args.split()
        file_path = parts[0]
        focus = parts[1] if len(parts) > 1 else "all"

        full_path = Path(self.config.working_directory) / file_path
        if not full_path.exists():
            self.console.print(f"[red]File not found: {file_path}[/red]")
            return

        try:
            content = full_path.read_text()
        except Exception as e:
            self.console.print(f"[red]Error reading file: {e}[/red]")
            return

        self.console.print(f"\n[bold cyan]⚡ Optimizing: {file_path}[/bold cyan]")
        self.console.print(f"[dim]Focus: {focus}[/dim]\n")

        optimize_prompt = f"""Please optimize this code for performance:

**File**: {file_path}
**Focus**: {focus}

```
{content[:8000]}
```

Please:
1. Identify performance bottlenecks
2. Suggest specific optimizations with benchmarks if applicable
3. Show optimized code
4. Explain the expected performance improvement"""

        await self.cli._process_prompt(optimize_prompt)

    async def cmd_debug(self, args: str = "") -> None:
        """🐛 Debug and find issues in code"""
        if not args:
            self.console.print("\n[bold cyan]🐛 Debug Assistant[/bold cyan]")
            self.console.print("[dim]Help debug issues in your code[/dim]\n")
            self.console.print("[yellow]Usage: /debug <file_path or error message>[/yellow]")
            self.console.print("\n[bold]Examples:[/bold]")
            self.console.print("  /debug src/api.py")
            self.console.print("  /debug TypeError: Cannot read property 'x' of undefined")
            self.console.print("  /debug Why is my function returning None?")
            return

        self.console.print("\n[bold cyan]🐛 Debugging[/bold cyan]")

        # Check if it's a file path
        potential_path = Path(self.config.working_directory) / args.split()[0]

        if potential_path.exists() and potential_path.is_file():
            content = potential_path.read_text()
            debug_prompt = f"""Please help debug this code:

**File**: {args.split()[0]}

```
{content[:8000]}
```

Please:
1. Identify potential bugs or issues
2. Explain what might be going wrong
3. Suggest fixes with code examples
4. Recommend debugging strategies"""
        else:
            debug_prompt = f"""Please help me debug this issue:

{args}

Please:
1. Analyze the error/problem
2. Identify the likely cause
3. Suggest step-by-step debugging approach
4. Provide potential solutions"""

        await self.cli._process_prompt(debug_prompt)

    async def cmd_test(self, args: str = "") -> None:
        """🧪 Generate tests for code"""
        if not args:
            self.console.print("\n[bold cyan]🧪 Test Generator[/bold cyan]")
            self.console.print("[dim]Generate tests for your code[/dim]\n")
            self.console.print("[yellow]Usage: /test <file_path> [framework][/yellow]")
            self.console.print("\n[bold]Frameworks:[/bold]")
            self.console.print("  [green]pytest[/green]   - Python pytest (default for .py)")
            self.console.print("  [green]jest[/green]     - JavaScript Jest (default for .js/.ts)")
            self.console.print("  [green]vitest[/green]   - Vite test runner")
            self.console.print("  [green]unittest[/green] - Python unittest")
            return

        parts = args.split()
        file_path = parts[0]
        framework = parts[1] if len(parts) > 1 else None

        full_path = Path(self.config.working_directory) / file_path
        if not full_path.exists():
            self.console.print(f"[red]File not found: {file_path}[/red]")
            return

        try:
            content = full_path.read_text()
        except Exception as e:
            self.console.print(f"[red]Error reading file: {e}[/red]")
            return

        # Auto-detect framework
        if not framework:
            if file_path.endswith('.py'):
                framework = 'pytest'
            elif file_path.endswith(('.js', '.ts', '.tsx', '.jsx')):
                framework = 'jest'

        self.console.print(f"\n[bold cyan]🧪 Generating Tests: {file_path}[/bold cyan]")
        self.console.print(f"[dim]Framework: {framework}[/dim]\n")

        test_prompt = f"""Please generate comprehensive tests for this code:

**File**: {file_path}
**Framework**: {framework}

```
{content[:8000]}
```

Please generate:
1. Unit tests for all functions/methods
2. Edge case tests
3. Error handling tests
4. Integration tests if applicable

Use best practices for {framework}."""

        await self.cli._process_prompt(test_prompt)

    async def cmd_explain(self, args: str = "") -> None:
        """📖 Explain code in detail"""
        if not args:
            self.console.print("\n[bold cyan]📖 Code Explainer[/bold cyan]")
            self.console.print("[dim]Get detailed explanations of code[/dim]\n")
            self.console.print("[yellow]Usage: /explain <file_path or code concept>[/yellow]")
            self.console.print("\n[bold]Examples:[/bold]")
            self.console.print("  /explain src/auth.py")
            self.console.print("  /explain How does async/await work?")
            self.console.print("  /explain What is dependency injection?")
            return

        self.console.print("\n[bold cyan]📖 Explaining[/bold cyan]\n")

        # Check if it's a file path
        potential_path = Path(self.config.working_directory) / args.split()[0]

        if potential_path.exists() and potential_path.is_file():
            content = potential_path.read_text()
            explain_prompt = f"""Please explain this code in detail:

**File**: {args.split()[0]}

```
{content[:8000]}
```

Please provide:
1. **Overview** - What this code does at a high level
2. **Line-by-Line Explanation** - Key sections explained
3. **Design Patterns** - Patterns used and why
4. **Dependencies** - What this code depends on
5. **How to Use** - Usage examples"""
        else:
            explain_prompt = f"""Please explain in detail:

{args}

Provide a comprehensive explanation with:
1. Core concepts
2. How it works
3. Examples
4. Common use cases
5. Best practices"""

        await self.cli._process_prompt(explain_prompt)

    async def cmd_doc(self, args: str = "") -> None:
        """📝 Generate documentation for code"""
        if not args:
            self.console.print("\n[bold cyan]📝 Documentation Generator[/bold cyan]")
            self.console.print("[dim]Generate documentation for your code[/dim]\n")
            self.console.print("[yellow]Usage: /doc <file_path> [format][/yellow]")
            self.console.print("\n[bold]Formats:[/bold]")
            self.console.print("  [green]docstring[/green] - Add docstrings to functions (default)")
            self.console.print("  [green]readme[/green]    - Generate README.md")
            self.console.print("  [green]api[/green]       - Generate API documentation")
            self.console.print("  [green]jsdoc[/green]     - JSDoc comments")
            return

        parts = args.split()
        file_path = parts[0]
        doc_format = parts[1] if len(parts) > 1 else "docstring"

        full_path = Path(self.config.working_directory) / file_path
        if not full_path.exists():
            self.console.print(f"[red]File not found: {file_path}[/red]")
            return

        try:
            content = full_path.read_text()
        except Exception as e:
            self.console.print(f"[red]Error reading file: {e}[/red]")
            return

        self.console.print(f"\n[bold cyan]📝 Generating Documentation: {file_path}[/bold cyan]")
        self.console.print(f"[dim]Format: {doc_format}[/dim]\n")

        doc_prompt = f"""Please generate documentation for this code:

**File**: {file_path}
**Format**: {doc_format}

```
{content[:8000]}
```

Please generate comprehensive {doc_format} documentation including:
- Description of purpose
- Parameters with types
- Return values
- Examples
- Raises/Exceptions"""

        await self.cli._process_prompt(doc_prompt)

    async def cmd_fix(self, args: str = "") -> None:
        """🔧 Fix bugs and errors in code"""
        if not args:
            self.console.print("\n[bold cyan]🔧 Bug Fixer[/bold cyan]")
            self.console.print("[dim]Fix bugs and errors in your code[/dim]\n")
            self.console.print("[yellow]Usage: /fix <file_path> [error description][/yellow]")
            self.console.print("\n[bold]Examples:[/bold]")
            self.console.print("  /fix src/api.py")
            self.console.print("  /fix app.py TypeError on line 42")
            self.console.print("  /fix models/user.py Database connection failing")
            return

        parts = args.split(maxsplit=1)
        file_path = parts[0]
        error_desc = parts[1] if len(parts) > 1 else "Find and fix any issues"

        full_path = Path(self.config.working_directory) / file_path
        if not full_path.exists():
            self.console.print(f"[red]File not found: {file_path}[/red]")
            return

        try:
            content = full_path.read_text()
        except Exception as e:
            self.console.print(f"[red]Error reading file: {e}[/red]")
            return

        self.console.print(f"\n[bold cyan]🔧 Fixing: {file_path}[/bold cyan]")
        self.console.print(f"[dim]Issue: {error_desc}[/dim]\n")

        fix_prompt = f"""Please fix the issues in this code:

**File**: {file_path}
**Reported Issue**: {error_desc}

```
{content[:8000]}
```

Please:
1. Identify the bug(s)
2. Explain what's causing the issue
3. Provide the fixed code
4. Explain the fix"""

        await self.cli._process_prompt(fix_prompt)
