"""
BharatBuild CLI Subagents/Custom Agents System

Create and manage specialized AI assistants:
  /agents             List available agents
  /agent <name>       Start conversation with agent
  /agent create       Create new agent
"""

import os
import json
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm


class AgentScope(str, Enum):
    """Agent scope/location"""
    PERSONAL = "personal"    # ~/.bharatbuild/agents/
    PROJECT = "project"      # .bharatbuild/agents/
    BUILTIN = "builtin"      # Built-in agents


@dataclass
class AgentConfig:
    """Agent configuration"""
    name: str
    description: str = ""
    version: str = "1.0.0"
    author: str = ""

    # Model settings
    model: str = ""  # Override default model
    temperature: float = 0.7
    max_tokens: int = 4096

    # System prompt
    system_prompt: str = ""
    persona: str = ""

    # Capabilities
    allowed_tools: List[str] = field(default_factory=list)
    denied_tools: List[str] = field(default_factory=list)

    # Context
    include_files: List[str] = field(default_factory=list)  # Always include these
    context_instructions: str = ""

    # Behavior
    auto_approve_reads: bool = True
    auto_approve_writes: bool = False
    require_confirmation: bool = True


@dataclass
class Agent:
    """A complete agent definition"""
    id: str
    config: AgentConfig
    scope: AgentScope
    path: Path
    instructions: str = ""  # Additional instructions from file


# Built-in agents
BUILTIN_AGENTS: Dict[str, AgentConfig] = {
    "coder": AgentConfig(
        name="Coder",
        description="Expert coding assistant focused on writing clean, efficient code",
        persona="expert software engineer",
        system_prompt="""You are an expert software engineer. Your focus is on:
- Writing clean, efficient, and maintainable code
- Following best practices and design patterns
- Providing clear explanations of your code
- Suggesting optimizations and improvements

Be concise and focus on the code. Use comments sparingly but effectively.""",
        temperature=0.3,
        auto_approve_reads=True
    ),

    "reviewer": AgentConfig(
        name="Code Reviewer",
        description="Thorough code reviewer finding bugs and suggesting improvements",
        persona="senior code reviewer",
        system_prompt="""You are a senior code reviewer. Your focus is on:
- Finding bugs and potential issues
- Identifying security vulnerabilities
- Suggesting performance improvements
- Ensuring code follows best practices
- Checking for edge cases and error handling

Be thorough but constructive. Explain why changes are needed.""",
        temperature=0.4,
        allowed_tools=["Read", "Grep", "Glob"],
        denied_tools=["Write", "Bash"]
    ),

    "architect": AgentConfig(
        name="Architect",
        description="System architect for design and planning",
        persona="software architect",
        system_prompt="""You are a software architect. Your focus is on:
- System design and architecture decisions
- Choosing appropriate technologies and patterns
- Planning scalable and maintainable solutions
- Identifying potential technical debt
- Creating clear technical documentation

Think big picture while considering implementation details.""",
        temperature=0.6
    ),

    "debugger": AgentConfig(
        name="Debugger",
        description="Expert debugger for finding and fixing issues",
        persona="debugging expert",
        system_prompt="""You are a debugging expert. Your focus is on:
- Identifying root causes of bugs
- Systematic debugging approaches
- Reading error messages and stack traces
- Suggesting fixes with explanations
- Preventing similar issues in the future

Be methodical and explain your debugging process.""",
        temperature=0.3,
        auto_approve_reads=True
    ),

    "teacher": AgentConfig(
        name="Teacher",
        description="Patient teacher explaining concepts clearly",
        persona="patient programming teacher",
        system_prompt="""You are a patient programming teacher. Your focus is on:
- Explaining concepts clearly with examples
- Breaking down complex topics
- Answering questions thoroughly
- Encouraging learning and experimentation
- Adapting explanations to skill level

Use analogies and real-world examples. Be encouraging and supportive.""",
        temperature=0.7,
        denied_tools=["Write", "Bash"]  # Read-only for safety
    ),

    "security": AgentConfig(
        name="Security Expert",
        description="Security specialist for vulnerability assessment",
        persona="security expert",
        system_prompt="""You are a security expert. Your focus is on:
- Identifying security vulnerabilities
- Suggesting secure coding practices
- Reviewing authentication and authorization
- Checking for OWASP Top 10 issues
- Recommending security improvements

Be thorough and explain the risks of each issue found.""",
        temperature=0.3,
        allowed_tools=["Read", "Grep", "Glob"]
    ),
}


class AgentManager:
    """
    Manages custom AI agents (subagents).

    Agents are specialized assistants with custom prompts,
    configurations, and tool restrictions.

    Directory structure:
    ```
    ~/.bharatbuild/agents/
        my-agent/
            agent.yaml
            instructions.md

    .bharatbuild/agents/
        project-agent/
            agent.yaml
    ```

    Usage:
        manager = AgentManager(console, project_dir, config_dir)

        # List agents
        manager.list_agents()

        # Get agent config
        config = manager.get_agent_config("coder")

        # Start agent session
        manager.start_agent_session("coder")
    """

    def __init__(
        self,
        console: Console,
        project_dir: Path = None,
        config_dir: Path = None
    ):
        self.console = console
        self.project_dir = project_dir or Path.cwd()
        self.config_dir = config_dir or Path.home() / ".bharatbuild"

        # Agent directories
        self.personal_agents_dir = self.config_dir / "agents"
        self.project_agents_dir = self.project_dir / ".bharatbuild" / "agents"

        # Ensure directories exist
        self.personal_agents_dir.mkdir(parents=True, exist_ok=True)

        # Load agents
        self._agents: Dict[str, Agent] = {}
        self._load_agents()

        # Current active agent
        self._active_agent: Optional[Agent] = None

    def _load_agents(self):
        """Load all agents"""
        self._agents.clear()

        # Load built-in agents
        for agent_id, config in BUILTIN_AGENTS.items():
            self._agents[agent_id] = Agent(
                id=agent_id,
                config=config,
                scope=AgentScope.BUILTIN,
                path=Path(),
                instructions=""
            )

        # Load personal agents
        self._load_agents_from_dir(self.personal_agents_dir, AgentScope.PERSONAL)

        # Load project agents (higher priority)
        if self.project_agents_dir.exists():
            self._load_agents_from_dir(self.project_agents_dir, AgentScope.PROJECT)

    def _load_agents_from_dir(self, directory: Path, scope: AgentScope):
        """Load agents from a directory"""
        if not directory.exists():
            return

        for agent_dir in directory.iterdir():
            if agent_dir.is_dir():
                config_file = agent_dir / "agent.yaml"
                if not config_file.exists():
                    config_file = agent_dir / "agent.json"

                if config_file.exists():
                    agent = self._load_agent(config_file, scope)
                    if agent:
                        self._agents[agent.id] = agent

    def _load_agent(self, config_path: Path, scope: AgentScope) -> Optional[Agent]:
        """Load a single agent from config file"""
        try:
            with open(config_path) as f:
                if config_path.suffix == ".yaml":
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

            config = AgentConfig(
                name=data.get("name", config_path.parent.name),
                description=data.get("description", ""),
                version=data.get("version", "1.0.0"),
                author=data.get("author", ""),
                model=data.get("model", ""),
                temperature=data.get("temperature", 0.7),
                max_tokens=data.get("max_tokens", 4096),
                system_prompt=data.get("system_prompt", ""),
                persona=data.get("persona", ""),
                allowed_tools=data.get("allowed_tools", data.get("allowed-tools", [])),
                denied_tools=data.get("denied_tools", data.get("denied-tools", [])),
                include_files=data.get("include_files", []),
                context_instructions=data.get("context_instructions", ""),
                auto_approve_reads=data.get("auto_approve_reads", True),
                auto_approve_writes=data.get("auto_approve_writes", False),
                require_confirmation=data.get("require_confirmation", True)
            )

            agent_id = data.get("id", config_path.parent.name.lower())

            # Load instructions file if exists
            instructions = ""
            instructions_file = config_path.parent / "instructions.md"
            if instructions_file.exists():
                instructions = instructions_file.read_text()

            return Agent(
                id=agent_id,
                config=config,
                scope=scope,
                path=config_path,
                instructions=instructions
            )

        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not load agent {config_path}: {e}[/yellow]")
            return None

    def reload(self):
        """Reload all agents"""
        self._load_agents()
        self.console.print(f"[green]✓ Reloaded {len(self._agents)} agents[/green]")

    # ==================== Agent Access ====================

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID"""
        return self._agents.get(agent_id.lower())

    def get_all_agents(self) -> List[Agent]:
        """Get all loaded agents"""
        return list(self._agents.values())

    def get_agent_system_prompt(self, agent_id: str) -> str:
        """Get full system prompt for an agent"""
        agent = self.get_agent(agent_id)
        if not agent:
            return ""

        parts = []

        # Persona
        if agent.config.persona:
            parts.append(f"You are a {agent.config.persona}.")

        # System prompt
        if agent.config.system_prompt:
            parts.append(agent.config.system_prompt)

        # Additional instructions
        if agent.instructions:
            parts.append(agent.instructions)

        # Context instructions
        if agent.config.context_instructions:
            parts.append(agent.config.context_instructions)

        return "\n\n".join(parts)

    def get_agent_tools(self, agent_id: str) -> tuple:
        """Get allowed/denied tools for an agent"""
        agent = self.get_agent(agent_id)
        if agent:
            return agent.config.allowed_tools, agent.config.denied_tools
        return [], []

    def get_active_agent(self) -> Optional[Agent]:
        """Get currently active agent"""
        return self._active_agent

    def set_active_agent(self, agent_id: str) -> bool:
        """Set the active agent"""
        if not agent_id:
            self._active_agent = None
            self.console.print("[green]✓ Returned to default assistant[/green]")
            return True

        agent = self.get_agent(agent_id)
        if not agent:
            self.console.print(f"[red]Agent not found: {agent_id}[/red]")
            return False

        self._active_agent = agent
        self.console.print(f"[green]✓ Now talking to: {agent.config.name}[/green]")
        self.console.print(f"[dim]{agent.config.description}[/dim]")

        return True

    def clear_active_agent(self):
        """Clear active agent, return to default"""
        self._active_agent = None
        self.console.print("[green]✓ Returned to default assistant[/green]")

    # ==================== Agent Creation ====================

    def create_agent(
        self,
        name: str,
        description: str = "",
        scope: AgentScope = AgentScope.PERSONAL,
        interactive: bool = False
    ) -> Optional[Agent]:
        """Create a new agent"""
        agent_id = name.lower().replace(" ", "-")

        # Check if exists
        if agent_id in self._agents and self._agents[agent_id].scope != AgentScope.BUILTIN:
            self.console.print(f"[red]Agent already exists: {agent_id}[/red]")
            return None

        # Determine directory
        if scope == AgentScope.PROJECT:
            base_dir = self.project_agents_dir
        else:
            base_dir = self.personal_agents_dir

        agent_dir = base_dir / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Interactive creation
        if interactive:
            name = Prompt.ask("Agent name", default=name)
            description = Prompt.ask("Description", default=description)
            persona = Prompt.ask("Persona (e.g., 'expert Python developer')", default="")
            system_prompt = Prompt.ask("System prompt", default="")

            model = Prompt.ask(
                "Model override",
                choices=["", "haiku", "sonnet", "opus"],
                default=""
            )

            temp = float(Prompt.ask("Temperature (0-1)", default="0.7"))
        else:
            persona = ""
            system_prompt = f"You are {name}. {description}"
            model = ""
            temp = 0.7

        # Create config
        config_data = {
            "id": agent_id,
            "name": name,
            "description": description,
            "version": "1.0.0",
            "persona": persona,
            "system_prompt": system_prompt,
            "model": model,
            "temperature": temp,
            "max_tokens": 4096,
            "allowed_tools": [],
            "denied_tools": [],
            "auto_approve_reads": True,
            "auto_approve_writes": False,
            "require_confirmation": True
        }

        config_file = agent_dir / "agent.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)

        # Create instructions file
        instructions_file = agent_dir / "instructions.md"
        instructions_file.write_text(f"""# {name}

Add additional instructions for the agent here.

## Guidelines

- Be helpful and accurate
- Follow the user's requests
- Ask for clarification when needed

## Specific Instructions

Add any specific instructions for this agent.
""")

        # Reload to pick up new agent
        self._load_agents()

        self.console.print(f"[green]✓ Created agent: {name}[/green]")
        self.console.print(f"[dim]Location: {agent_dir}[/dim]")

        return self.get_agent(agent_id)

    def edit_agent(self, agent_id: str):
        """Open agent for editing"""
        agent = self.get_agent(agent_id)

        if not agent:
            self.console.print(f"[red]Agent not found: {agent_id}[/red]")
            return

        if agent.scope == AgentScope.BUILTIN:
            self.console.print("[yellow]Cannot edit built-in agents. Create a custom one instead.[/yellow]")
            return

        # Open in editor
        import subprocess
        import platform

        config_file = agent.path

        try:
            if platform.system() == 'Darwin':
                subprocess.run(['open', str(config_file)])
            elif platform.system() == 'Windows':
                os.startfile(str(config_file))
            else:
                editor = os.environ.get('EDITOR', 'nano')
                subprocess.run([editor, str(config_file)])

            self.console.print(f"[green]✓ Opened {config_file}[/green]")

        except Exception as e:
            self.console.print(f"[yellow]Could not open editor: {e}[/yellow]")
            self.console.print(f"[dim]Edit manually: {config_file}[/dim]")

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent"""
        agent = self.get_agent(agent_id)

        if not agent:
            self.console.print(f"[red]Agent not found: {agent_id}[/red]")
            return False

        if agent.scope == AgentScope.BUILTIN:
            self.console.print("[red]Cannot delete built-in agents[/red]")
            return False

        if not Confirm.ask(f"Delete agent '{agent.config.name}'?"):
            return False

        # Delete directory
        import shutil
        if agent.path.parent.is_dir():
            shutil.rmtree(agent.path.parent)

        del self._agents[agent_id]

        # Clear if active
        if self._active_agent and self._active_agent.id == agent_id:
            self._active_agent = None

        self.console.print(f"[green]✓ Deleted agent: {agent.config.name}[/green]")
        return True

    # ==================== Display ====================

    def list_agents(self):
        """List all available agents"""
        table = Table(title="Available Agents", show_header=True, header_style="bold cyan")
        table.add_column("", width=3)
        table.add_column("Name")
        table.add_column("Description")
        table.add_column("Scope")
        table.add_column("Model")

        for agent in sorted(self._agents.values(), key=lambda a: (a.scope.value, a.config.name)):
            # Active indicator
            is_active = self._active_agent and self._active_agent.id == agent.id
            indicator = "[green]►[/green]" if is_active else " "

            scope_str = {
                AgentScope.BUILTIN: "[cyan]built-in[/cyan]",
                AgentScope.PERSONAL: "[blue]personal[/blue]",
                AgentScope.PROJECT: "[green]project[/green]"
            }.get(agent.scope, agent.scope.value)

            model = agent.config.model or "[dim]default[/dim]"

            table.add_row(
                indicator,
                f"[bold]{agent.config.name}[/bold]",
                agent.config.description[:40] or "[dim]No description[/dim]",
                scope_str,
                model
            )

        self.console.print(table)

        if self._active_agent:
            self.console.print(f"\n[dim]Active: {self._active_agent.config.name}[/dim]")

    def show_agent(self, agent_id: str):
        """Show agent details"""
        agent = self.get_agent(agent_id)

        if not agent:
            self.console.print(f"[red]Agent not found: {agent_id}[/red]")
            return

        content_lines = []
        content_lines.append(f"[bold]Name:[/bold] {agent.config.name}")
        content_lines.append(f"[bold]Description:[/bold] {agent.config.description or 'None'}")
        content_lines.append(f"[bold]Version:[/bold] {agent.config.version}")
        content_lines.append(f"[bold]Scope:[/bold] {agent.scope.value}")

        if agent.path:
            content_lines.append(f"[bold]Path:[/bold] {agent.path}")

        content_lines.append("")
        content_lines.append("[bold]Settings:[/bold]")
        content_lines.append(f"  Model: {agent.config.model or 'default'}")
        content_lines.append(f"  Temperature: {agent.config.temperature}")
        content_lines.append(f"  Max Tokens: {agent.config.max_tokens}")

        if agent.config.persona:
            content_lines.append(f"  Persona: {agent.config.persona}")

        content_lines.append("")
        content_lines.append("[bold]Permissions:[/bold]")
        content_lines.append(f"  Auto-approve reads: {'Yes' if agent.config.auto_approve_reads else 'No'}")
        content_lines.append(f"  Auto-approve writes: {'Yes' if agent.config.auto_approve_writes else 'No'}")

        if agent.config.allowed_tools:
            content_lines.append(f"  Allowed tools: {', '.join(agent.config.allowed_tools)}")

        if agent.config.denied_tools:
            content_lines.append(f"  Denied tools: {', '.join(agent.config.denied_tools)}")

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title=f"[bold cyan]Agent: {agent.config.name}[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

        # Show system prompt preview
        if agent.config.system_prompt:
            self.console.print("\n[bold]System Prompt:[/bold]")
            preview = agent.config.system_prompt[:300]
            if len(agent.config.system_prompt) > 300:
                preview += "..."
            self.console.print(f"[dim]{preview}[/dim]")

    def show_help(self):
        """Show agents help"""
        help_text = """
[bold cyan]Agents System[/bold cyan]

Specialized AI assistants with custom configurations.

[bold]Commands:[/bold]
  [green]/agents[/green]             List available agents
  [green]/agent <name>[/green]       Switch to agent
  [green]/agent show <name>[/green]  Show agent details
  [green]/agent create[/green]       Create new agent
  [green]/agent edit <name>[/green]  Edit agent config
  [green]/agent delete <n>[/green]   Delete agent
  [green]/agent clear[/green]        Return to default
  [green]/agent reload[/green]       Reload all agents

[bold]Built-in Agents:[/bold]
  • coder    - Expert coding assistant
  • reviewer - Thorough code reviewer
  • architect - System design expert
  • debugger - Debugging specialist
  • teacher  - Patient programming teacher
  • security - Security expert

[bold]Agent Locations:[/bold]
  Personal: ~/.bharatbuild/agents/
  Project:  .bharatbuild/agents/

[bold]Config Format (agent.yaml):[/bold]
```yaml
name: My Agent
description: What it does
persona: expert developer
system_prompt: |
  Custom instructions...
temperature: 0.7
allowed_tools:
  - Read
  - Write
```

[bold]Examples:[/bold]
  /agent coder
  /agent create "My Expert"
  /agent clear
"""
        self.console.print(help_text)
