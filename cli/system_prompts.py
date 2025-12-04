"""
BharatBuild CLI Custom System Prompts

Enables custom system prompts and personas:
  /prompt set expert-python
  /prompt create my-assistant
  /prompt list
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.text import Text


@dataclass
class SystemPrompt:
    """A custom system prompt configuration"""
    name: str
    content: str
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_builtin: bool = False
    tags: List[str] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)  # Template variables


# Built-in system prompts
BUILTIN_PROMPTS = {
    "default": SystemPrompt(
        name="default",
        content="""You are BharatBuild AI, an intelligent coding assistant designed to help students learn and build software projects. You are helpful, patient, and explain concepts clearly.

Key behaviors:
- Write clean, well-documented code
- Explain your reasoning step by step
- Suggest best practices and improvements
- Be encouraging and supportive of learning
- Ask clarifying questions when needed""",
        description="Default helpful coding assistant",
        is_builtin=True,
        tags=["general", "learning"]
    ),

    "expert-python": SystemPrompt(
        name="expert-python",
        content="""You are an expert Python developer with deep knowledge of:
- Python best practices and PEP guidelines
- Modern Python features (3.10+)
- Type hints and static typing
- Testing (pytest, unittest)
- Async programming (asyncio)
- Popular frameworks (FastAPI, Django, Flask)
- Data science libraries (pandas, numpy, scikit-learn)

When writing Python code:
- Use type hints consistently
- Follow PEP 8 style guidelines
- Write comprehensive docstrings
- Handle errors properly with specific exceptions
- Suggest performance optimizations where relevant""",
        description="Python expert with best practices focus",
        is_builtin=True,
        tags=["python", "expert"]
    ),

    "expert-typescript": SystemPrompt(
        name="expert-typescript",
        content="""You are an expert TypeScript/JavaScript developer with deep knowledge of:
- TypeScript best practices and strict mode
- Modern JavaScript (ES2022+)
- React, Next.js, Vue, Svelte
- Node.js and Express/Fastify
- Testing (Jest, Vitest, Playwright)
- State management (Redux, Zustand, Pinia)

When writing TypeScript code:
- Use strict TypeScript configuration
- Define proper interfaces and types
- Avoid 'any' type
- Use proper error handling
- Follow modern React patterns (hooks, functional components)
- Suggest performance optimizations""",
        description="TypeScript/JavaScript expert",
        is_builtin=True,
        tags=["typescript", "javascript", "expert"]
    ),

    "code-reviewer": SystemPrompt(
        name="code-reviewer",
        content="""You are a senior code reviewer focused on:
- Code quality and maintainability
- Security vulnerabilities
- Performance issues
- Best practices and design patterns
- Test coverage

When reviewing code:
1. First, understand the overall purpose
2. Check for bugs and logical errors
3. Identify security concerns
4. Suggest performance improvements
5. Recommend style and structure improvements
6. Be constructive and explain the "why"

Format your review with:
- 🔴 Critical issues (must fix)
- 🟡 Suggestions (should consider)
- 🟢 Good practices (positive feedback)""",
        description="Code review specialist",
        is_builtin=True,
        tags=["review", "quality"]
    ),

    "debugger": SystemPrompt(
        name="debugger",
        content="""You are an expert debugger and troubleshooter. Your approach:

1. **Understand the Problem**
   - What is the expected behavior?
   - What is the actual behavior?
   - When did it start happening?

2. **Gather Information**
   - Error messages and stack traces
   - Relevant code sections
   - Environment details

3. **Systematic Analysis**
   - Form hypotheses
   - Test each hypothesis
   - Narrow down the cause

4. **Solution**
   - Explain the root cause
   - Provide the fix
   - Suggest prevention measures

Be methodical, ask questions when needed, and explain your reasoning.""",
        description="Debugging and troubleshooting expert",
        is_builtin=True,
        tags=["debug", "troubleshoot"]
    ),

    "architect": SystemPrompt(
        name="architect",
        content="""You are a software architect focused on:
- System design and scalability
- Clean architecture principles
- Design patterns
- Technology selection
- Trade-off analysis

When discussing architecture:
1. Understand requirements (functional and non-functional)
2. Consider scale, performance, cost
3. Propose clear component boundaries
4. Explain data flow and integration points
5. Document assumptions and trade-offs

Use diagrams (in Mermaid format) when helpful. Focus on maintainability and extensibility.""",
        description="Software architecture expert",
        is_builtin=True,
        tags=["architecture", "design"]
    ),

    "teacher": SystemPrompt(
        name="teacher",
        content="""You are a patient and encouraging programming teacher. Your approach:

- **Explain concepts** clearly with examples
- **Use analogies** to make complex ideas accessible
- **Provide exercises** to reinforce learning
- **Give hints** rather than full solutions when teaching
- **Celebrate progress** and encourage questions
- **Adapt** to the learner's level

When teaching:
1. Start with the "why" - motivation matters
2. Build from simple to complex
3. Use visual aids and diagrams
4. Provide working examples
5. Include practice problems
6. Summarize key takeaways

Be supportive and remember: there are no stupid questions!""",
        description="Patient programming teacher",
        is_builtin=True,
        tags=["learning", "education"]
    ),

    "concise": SystemPrompt(
        name="concise",
        content="""You are a direct and efficient assistant.

Rules:
- Give brief, focused responses
- No unnecessary explanations
- Code first, explanation only if needed
- Use bullet points
- Skip pleasantries
- Be precise

If asked to explain, keep it short.""",
        description="Minimal, direct responses",
        is_builtin=True,
        tags=["minimal", "efficient"]
    ),

    "documentation": SystemPrompt(
        name="documentation",
        content="""You are a technical documentation expert. Focus on:

- **Clear writing** - Simple, precise language
- **Good structure** - Headers, lists, tables
- **Examples** - Code snippets and use cases
- **Completeness** - Cover edge cases
- **Accessibility** - Write for all skill levels

Documentation types:
- API documentation
- User guides
- README files
- Code comments
- Architecture docs

Always consider: Who will read this? What do they need to know?""",
        description="Technical documentation writer",
        is_builtin=True,
        tags=["documentation", "writing"]
    ),

    "security": SystemPrompt(
        name="security",
        content="""You are a security-focused developer. Consider:

**OWASP Top 10:**
- Injection (SQL, command, etc.)
- Broken Authentication
- Sensitive Data Exposure
- XML External Entities
- Broken Access Control
- Security Misconfiguration
- Cross-Site Scripting (XSS)
- Insecure Deserialization
- Using Components with Vulnerabilities
- Insufficient Logging

When writing code:
- Validate and sanitize all inputs
- Use parameterized queries
- Implement proper authentication
- Encrypt sensitive data
- Follow least privilege principle
- Log security events

Flag security concerns prominently with ⚠️""",
        description="Security-focused development",
        is_builtin=True,
        tags=["security", "owasp"]
    )
}


class SystemPromptManager:
    """
    Manages custom system prompts.

    Usage:
        manager = SystemPromptManager(console, config_dir)

        # Set active prompt
        manager.set_active("expert-python")

        # Get active prompt content
        content = manager.get_active_content()

        # Create custom prompt
        manager.create_prompt("my-assistant", "You are...")
    """

    def __init__(
        self,
        console: Console,
        config_dir: Optional[Path] = None
    ):
        self.console = console
        self.config_dir = config_dir or (Path.home() / ".bharatbuild" / "prompts")
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self._prompts: Dict[str, SystemPrompt] = {}
        self._active_prompt: str = "default"

        # Load built-in prompts
        for name, prompt in BUILTIN_PROMPTS.items():
            self._prompts[name] = prompt

        # Load custom prompts
        self._load_custom_prompts()
        self._load_state()

    def _load_custom_prompts(self):
        """Load custom prompts from disk"""
        prompts_file = self.config_dir / "custom_prompts.json"

        if prompts_file.exists():
            try:
                with open(prompts_file) as f:
                    data = json.load(f)

                for name, prompt_data in data.items():
                    self._prompts[name] = SystemPrompt(
                        name=name,
                        content=prompt_data["content"],
                        description=prompt_data.get("description", ""),
                        created_at=prompt_data.get("created_at", ""),
                        updated_at=prompt_data.get("updated_at", ""),
                        is_builtin=False,
                        tags=prompt_data.get("tags", []),
                        variables=prompt_data.get("variables", {})
                    )

            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load custom prompts: {e}[/yellow]")

    def _save_custom_prompts(self):
        """Save custom prompts to disk"""
        prompts_file = self.config_dir / "custom_prompts.json"

        try:
            data = {}
            for name, prompt in self._prompts.items():
                if not prompt.is_builtin:
                    data[name] = {
                        "content": prompt.content,
                        "description": prompt.description,
                        "created_at": prompt.created_at,
                        "updated_at": prompt.updated_at,
                        "tags": prompt.tags,
                        "variables": prompt.variables
                    }

            with open(prompts_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not save custom prompts: {e}[/yellow]")

    def _load_state(self):
        """Load active prompt state"""
        state_file = self.config_dir / "state.json"

        if state_file.exists():
            try:
                with open(state_file) as f:
                    data = json.load(f)
                self._active_prompt = data.get("active", "default")
            except Exception:
                pass

    def _save_state(self):
        """Save active prompt state"""
        state_file = self.config_dir / "state.json"

        try:
            with open(state_file, 'w') as f:
                json.dump({"active": self._active_prompt}, f)
        except Exception:
            pass

    # ==================== Prompt Management ====================

    def set_active(self, name: str) -> bool:
        """Set the active system prompt"""
        if name not in self._prompts:
            self.console.print(f"[red]Prompt '{name}' not found[/red]")
            return False

        self._active_prompt = name
        self._save_state()

        prompt = self._prompts[name]
        self.console.print(f"[green]✓ Active prompt: {name}[/green]")
        self.console.print(f"[dim]  {prompt.description}[/dim]")

        return True

    def get_active(self) -> SystemPrompt:
        """Get the active system prompt"""
        return self._prompts.get(self._active_prompt, self._prompts["default"])

    def get_active_content(self, variables: Optional[Dict[str, str]] = None) -> str:
        """Get the active prompt content with variable substitution"""
        prompt = self.get_active()
        content = prompt.content

        # Apply variables
        all_vars = {**prompt.variables, **(variables or {})}
        for key, value in all_vars.items():
            content = content.replace(f"{{{key}}}", value)
            content = content.replace(f"${{{key}}}", value)

        return content

    def create_prompt(
        self,
        name: str,
        content: str,
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> bool:
        """Create a new custom prompt"""
        if name in self._prompts and self._prompts[name].is_builtin:
            self.console.print(f"[red]Cannot overwrite built-in prompt '{name}'[/red]")
            return False

        self._prompts[name] = SystemPrompt(
            name=name,
            content=content,
            description=description,
            tags=tags or [],
            is_builtin=False
        )

        self._save_custom_prompts()
        self.console.print(f"[green]✓ Created prompt '{name}'[/green]")

        return True

    def update_prompt(
        self,
        name: str,
        content: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Update an existing custom prompt"""
        if name not in self._prompts:
            self.console.print(f"[red]Prompt '{name}' not found[/red]")
            return False

        prompt = self._prompts[name]

        if prompt.is_builtin:
            self.console.print(f"[red]Cannot modify built-in prompt '{name}'[/red]")
            return False

        if content is not None:
            prompt.content = content
        if description is not None:
            prompt.description = description
        if tags is not None:
            prompt.tags = tags

        prompt.updated_at = datetime.now().isoformat()

        self._save_custom_prompts()
        self.console.print(f"[green]✓ Updated prompt '{name}'[/green]")

        return True

    def delete_prompt(self, name: str) -> bool:
        """Delete a custom prompt"""
        if name not in self._prompts:
            self.console.print(f"[red]Prompt '{name}' not found[/red]")
            return False

        if self._prompts[name].is_builtin:
            self.console.print(f"[red]Cannot delete built-in prompt '{name}'[/red]")
            return False

        del self._prompts[name]

        if self._active_prompt == name:
            self._active_prompt = "default"
            self._save_state()

        self._save_custom_prompts()
        self.console.print(f"[green]✓ Deleted prompt '{name}'[/green]")

        return True

    def get_prompt(self, name: str) -> Optional[SystemPrompt]:
        """Get a specific prompt"""
        return self._prompts.get(name)

    def list_prompts(self, tag: Optional[str] = None) -> List[SystemPrompt]:
        """List all prompts, optionally filtered by tag"""
        prompts = list(self._prompts.values())

        if tag:
            prompts = [p for p in prompts if tag in p.tags]

        return sorted(prompts, key=lambda p: (not p.is_builtin, p.name))

    # ==================== Display ====================

    def show_prompts(self, show_content: bool = False):
        """Display available prompts"""
        table = Table(title="System Prompts", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("Description")
        table.add_column("Tags")

        for prompt in self.list_prompts():
            # Mark active
            name = prompt.name
            if name == self._active_prompt:
                name = f"[bold green]* {name}[/bold green]"
            else:
                name = f"  {name}"

            type_text = "[dim]built-in[/dim]" if prompt.is_builtin else "[cyan]custom[/cyan]"

            table.add_row(
                name,
                type_text,
                prompt.description[:40] + "..." if len(prompt.description) > 40 else prompt.description,
                ", ".join(prompt.tags[:3])
            )

        self.console.print(table)

        if show_content:
            active = self.get_active()
            self.console.print(f"\n[bold]Active prompt content:[/bold]")
            self.console.print(Panel(
                active.content[:500] + "..." if len(active.content) > 500 else active.content,
                title=f"[bold]{active.name}[/bold]",
                border_style="cyan"
            ))

    def show_prompt(self, name: str):
        """Show details of a specific prompt"""
        prompt = self._prompts.get(name)

        if not prompt:
            self.console.print(f"[red]Prompt '{name}' not found[/red]")
            return

        # Build info
        info_lines = []
        info_lines.append(f"[bold]Name:[/bold] {prompt.name}")
        info_lines.append(f"[bold]Type:[/bold] {'Built-in' if prompt.is_builtin else 'Custom'}")
        info_lines.append(f"[bold]Description:[/bold] {prompt.description}")

        if prompt.tags:
            info_lines.append(f"[bold]Tags:[/bold] {', '.join(prompt.tags)}")

        if not prompt.is_builtin:
            info_lines.append(f"[bold]Created:[/bold] {prompt.created_at[:19]}")
            info_lines.append(f"[bold]Updated:[/bold] {prompt.updated_at[:19]}")

        info_text = "\n".join(info_lines)

        self.console.print(Panel(
            info_text,
            title="[bold cyan]Prompt Info[/bold cyan]",
            border_style="cyan"
        ))

        # Content
        self.console.print(Panel(
            prompt.content,
            title="[bold]Content[/bold]",
            border_style="dim"
        ))

    def show_help(self):
        """Show help for prompt commands"""
        help_text = """
[bold cyan]System Prompts[/bold cyan]

Customize how the AI behaves with system prompts.

[bold]Commands:[/bold]
  [green]/prompt list[/green]              List all prompts
  [green]/prompt set <name>[/green]        Set active prompt
  [green]/prompt show <name>[/green]       Show prompt details
  [green]/prompt create <name>[/green]     Create new prompt
  [green]/prompt edit <name>[/green]       Edit a prompt
  [green]/prompt delete <name>[/green]     Delete custom prompt

[bold]Built-in prompts:[/bold]
  • default         - General coding assistant
  • expert-python   - Python expert
  • expert-typescript - TypeScript/JS expert
  • code-reviewer   - Code review specialist
  • debugger        - Debugging expert
  • architect       - Software architect
  • teacher         - Patient teacher
  • concise         - Minimal responses
  • documentation   - Docs writer
  • security        - Security focused

[bold]Example:[/bold]
  /prompt set expert-python
  /prompt create my-helper --desc "Custom assistant"
"""
        panel = Panel(
            Text.from_markup(help_text),
            title="[bold]System Prompts Help[/bold]",
            border_style="cyan"
        )
        self.console.print(panel)
