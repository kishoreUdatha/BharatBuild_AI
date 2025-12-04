"""
BharatBuild CLI Skills System

Model-invoked capabilities via SKILL.md files:
  /skills             List available skills
  /skill <name>       View skill details
  /skill create       Create new skill
"""

import os
import re
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm


class SkillScope(str, Enum):
    """Skill scope/location"""
    PERSONAL = "personal"    # ~/.bharatbuild/skills/
    PROJECT = "project"      # .bharatbuild/skills/
    PLUGIN = "plugin"        # From installed plugins


@dataclass
class SkillMetadata:
    """Skill metadata from frontmatter"""
    name: str
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)  # Restrict tools
    denied_tools: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)  # Auto-activation keywords
    priority: int = 0  # Higher = checked first


@dataclass
class Skill:
    """A complete skill definition"""
    id: str
    metadata: SkillMetadata
    content: str  # The skill prompt/instructions
    scope: SkillScope
    path: Path
    supporting_files: List[str] = field(default_factory=list)


class SkillsManager:
    """
    Manages model-invoked skills.

    Skills are markdown files (SKILL.md) that provide specialized
    capabilities the model can invoke based on context.

    Directory structure:
    ```
    ~/.bharatbuild/skills/
        my-skill/
            SKILL.md
            template.txt
            ...

    .bharatbuild/skills/
        project-skill/
            SKILL.md
    ```

    SKILL.md format:
    ```markdown
    ---
    name: My Skill
    description: Does something useful
    triggers:
      - keyword1
      - keyword2
    allowed-tools:
      - Read
      - Write
    ---

    # My Skill

    Instructions for the model...
    ```

    Usage:
        manager = SkillsManager(console, project_dir, config_dir)

        # List skills
        manager.list_skills()

        # Get skill for context
        skill = manager.find_skill_for_context("user message")

        # Invoke skill
        prompt = manager.get_skill_prompt("my-skill")
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

        # Skill directories
        self.personal_skills_dir = self.config_dir / "skills"
        self.project_skills_dir = self.project_dir / ".bharatbuild" / "skills"

        # Ensure directories exist
        self.personal_skills_dir.mkdir(parents=True, exist_ok=True)

        # Load skills
        self._skills: Dict[str, Skill] = {}
        self._load_skills()

    def _load_skills(self):
        """Load all skills from all locations"""
        self._skills.clear()

        # Load personal skills
        self._load_skills_from_dir(self.personal_skills_dir, SkillScope.PERSONAL)

        # Load project skills (higher priority)
        if self.project_skills_dir.exists():
            self._load_skills_from_dir(self.project_skills_dir, SkillScope.PROJECT)

    def _load_skills_from_dir(self, directory: Path, scope: SkillScope):
        """Load skills from a directory"""
        if not directory.exists():
            return

        for skill_dir in directory.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    skill = self._load_skill(skill_file, scope)
                    if skill:
                        self._skills[skill.id] = skill

        # Also check for standalone SKILL.md files
        for skill_file in directory.glob("*.md"):
            if skill_file.name.upper() == "SKILL.MD" or skill_file.stem.lower().endswith("_skill"):
                skill = self._load_skill(skill_file, scope)
                if skill:
                    self._skills[skill.id] = skill

    def _load_skill(self, path: Path, scope: SkillScope) -> Optional[Skill]:
        """Load a single skill from file"""
        try:
            content = path.read_text(encoding='utf-8')

            # Parse frontmatter
            metadata, body = self._parse_frontmatter(content)

            if not metadata.get("name"):
                # Use directory or file name
                if path.name.upper() == "SKILL.MD":
                    metadata["name"] = path.parent.name
                else:
                    metadata["name"] = path.stem

            # Create skill ID
            skill_id = metadata["name"].lower().replace(" ", "-")

            # Get supporting files
            supporting_files = []
            if path.parent.is_dir() and path.name.upper() == "SKILL.MD":
                for f in path.parent.iterdir():
                    if f.is_file() and f.name != "SKILL.md":
                        supporting_files.append(f.name)

            return Skill(
                id=skill_id,
                metadata=SkillMetadata(
                    name=metadata.get("name", skill_id),
                    description=metadata.get("description", ""),
                    version=metadata.get("version", "1.0.0"),
                    author=metadata.get("author", ""),
                    tags=metadata.get("tags", []),
                    allowed_tools=metadata.get("allowed-tools", metadata.get("allowed_tools", [])),
                    denied_tools=metadata.get("denied-tools", metadata.get("denied_tools", [])),
                    triggers=metadata.get("triggers", []),
                    priority=metadata.get("priority", 0)
                ),
                content=body,
                scope=scope,
                path=path,
                supporting_files=supporting_files
            )

        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not load skill {path}: {e}[/yellow]")
            return None

    def _parse_frontmatter(self, content: str) -> tuple:
        """Parse YAML frontmatter from markdown"""
        metadata = {}
        body = content

        # Check for frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()
                except Exception:
                    pass

        return metadata, body

    def reload(self):
        """Reload all skills"""
        self._load_skills()
        self.console.print(f"[green]✓ Reloaded {len(self._skills)} skills[/green]")

    # ==================== Skill Access ====================

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID"""
        return self._skills.get(skill_id.lower())

    def get_all_skills(self) -> List[Skill]:
        """Get all loaded skills"""
        return list(self._skills.values())

    def get_skill_prompt(self, skill_id: str) -> Optional[str]:
        """Get the prompt content for a skill"""
        skill = self.get_skill(skill_id)
        if skill:
            return skill.content
        return None

    def get_skill_tools(self, skill_id: str) -> tuple:
        """Get allowed/denied tools for a skill"""
        skill = self.get_skill(skill_id)
        if skill:
            return skill.metadata.allowed_tools, skill.metadata.denied_tools
        return [], []

    def find_skill_for_context(self, context: str) -> Optional[Skill]:
        """Find a skill that matches the given context"""
        context_lower = context.lower()

        # Sort by priority
        sorted_skills = sorted(
            self._skills.values(),
            key=lambda s: -s.metadata.priority
        )

        for skill in sorted_skills:
            # Check triggers
            for trigger in skill.metadata.triggers:
                if trigger.lower() in context_lower:
                    return skill

            # Check tags
            for tag in skill.metadata.tags:
                if tag.lower() in context_lower:
                    return skill

        return None

    def get_skills_for_display(self) -> str:
        """Get formatted string of available skills for model context"""
        if not self._skills:
            return ""

        lines = ["Available Skills:"]
        for skill in self._skills.values():
            lines.append(f"- {skill.metadata.name}: {skill.metadata.description}")
            if skill.metadata.triggers:
                lines.append(f"  Triggers: {', '.join(skill.metadata.triggers)}")

        return "\n".join(lines)

    # ==================== Skill Creation ====================

    def create_skill(
        self,
        name: str,
        description: str = "",
        scope: SkillScope = SkillScope.PERSONAL,
        interactive: bool = False
    ) -> Optional[Skill]:
        """Create a new skill"""
        skill_id = name.lower().replace(" ", "-")

        # Check if exists
        if skill_id in self._skills:
            self.console.print(f"[red]Skill already exists: {skill_id}[/red]")
            return None

        # Determine directory
        if scope == SkillScope.PROJECT:
            base_dir = self.project_skills_dir
        else:
            base_dir = self.personal_skills_dir

        skill_dir = base_dir / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Interactive creation
        if interactive:
            name = Prompt.ask("Skill name", default=name)
            description = Prompt.ask("Description", default=description)

            triggers_str = Prompt.ask("Triggers (comma-separated)", default="")
            triggers = [t.strip() for t in triggers_str.split(",") if t.strip()]

            tags_str = Prompt.ask("Tags (comma-separated)", default="")
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]

            content = Prompt.ask("Skill instructions", default="")
        else:
            triggers = []
            tags = []
            content = f"# {name}\n\nDescribe what this skill does and how to use it."

        # Create SKILL.md
        skill_content = f"""---
name: {name}
description: {description}
version: 1.0.0
triggers:
{self._format_yaml_list(triggers)}
tags:
{self._format_yaml_list(tags)}
---

{content}
"""

        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(skill_content)

        # Reload to pick up new skill
        self._load_skills()

        self.console.print(f"[green]✓ Created skill: {name}[/green]")
        self.console.print(f"[dim]Location: {skill_file}[/dim]")

        return self.get_skill(skill_id)

    def _format_yaml_list(self, items: List[str]) -> str:
        """Format list for YAML"""
        if not items:
            return "  []"
        return "\n".join(f"  - {item}" for item in items)

    def edit_skill(self, skill_id: str):
        """Open skill for editing"""
        skill = self.get_skill(skill_id)

        if not skill:
            self.console.print(f"[red]Skill not found: {skill_id}[/red]")
            return

        # Open in editor
        import subprocess
        import platform

        try:
            if platform.system() == 'Darwin':
                subprocess.run(['open', str(skill.path)])
            elif platform.system() == 'Windows':
                os.startfile(str(skill.path))
            else:
                editor = os.environ.get('EDITOR', 'nano')
                subprocess.run([editor, str(skill.path)])

            self.console.print(f"[green]✓ Opened {skill.path}[/green]")

        except Exception as e:
            self.console.print(f"[yellow]Could not open editor: {e}[/yellow]")
            self.console.print(f"[dim]Edit manually: {skill.path}[/dim]")

    def delete_skill(self, skill_id: str) -> bool:
        """Delete a skill"""
        skill = self.get_skill(skill_id)

        if not skill:
            self.console.print(f"[red]Skill not found: {skill_id}[/red]")
            return False

        if skill.scope == SkillScope.PLUGIN:
            self.console.print("[red]Cannot delete plugin skills[/red]")
            return False

        if not Confirm.ask(f"Delete skill '{skill.metadata.name}'?"):
            return False

        # Delete directory or file
        import shutil

        if skill.path.parent.name == skill_id:
            shutil.rmtree(skill.path.parent)
        else:
            skill.path.unlink()

        del self._skills[skill_id]

        self.console.print(f"[green]✓ Deleted skill: {skill.metadata.name}[/green]")
        return True

    # ==================== Display ====================

    def list_skills(self):
        """List all available skills"""
        if not self._skills:
            self.console.print("[dim]No skills available[/dim]")
            self.console.print("[dim]Create one with /skill create[/dim]")
            return

        table = Table(title="Available Skills", show_header=True, header_style="bold cyan")
        table.add_column("Name")
        table.add_column("Description")
        table.add_column("Scope")
        table.add_column("Triggers")

        for skill in sorted(self._skills.values(), key=lambda s: s.metadata.name):
            scope_str = {
                SkillScope.PERSONAL: "[blue]personal[/blue]",
                SkillScope.PROJECT: "[green]project[/green]",
                SkillScope.PLUGIN: "[magenta]plugin[/magenta]"
            }.get(skill.scope, skill.scope.value)

            triggers = ", ".join(skill.metadata.triggers[:3])
            if len(skill.metadata.triggers) > 3:
                triggers += "..."

            table.add_row(
                f"[bold]{skill.metadata.name}[/bold]",
                skill.metadata.description[:40] or "[dim]No description[/dim]",
                scope_str,
                triggers or "[dim]-[/dim]"
            )

        self.console.print(table)

    def show_skill(self, skill_id: str):
        """Show skill details"""
        skill = self.get_skill(skill_id)

        if not skill:
            self.console.print(f"[red]Skill not found: {skill_id}[/red]")
            return

        content_lines = []
        content_lines.append(f"[bold]Name:[/bold] {skill.metadata.name}")
        content_lines.append(f"[bold]Description:[/bold] {skill.metadata.description or 'None'}")
        content_lines.append(f"[bold]Version:[/bold] {skill.metadata.version}")
        content_lines.append(f"[bold]Author:[/bold] {skill.metadata.author or 'Unknown'}")
        content_lines.append(f"[bold]Scope:[/bold] {skill.scope.value}")
        content_lines.append(f"[bold]Path:[/bold] {skill.path}")
        content_lines.append("")

        if skill.metadata.triggers:
            content_lines.append(f"[bold]Triggers:[/bold] {', '.join(skill.metadata.triggers)}")

        if skill.metadata.tags:
            content_lines.append(f"[bold]Tags:[/bold] {', '.join(skill.metadata.tags)}")

        if skill.metadata.allowed_tools:
            content_lines.append(f"[bold]Allowed Tools:[/bold] {', '.join(skill.metadata.allowed_tools)}")

        if skill.metadata.denied_tools:
            content_lines.append(f"[bold]Denied Tools:[/bold] {', '.join(skill.metadata.denied_tools)}")

        if skill.supporting_files:
            content_lines.append(f"[bold]Supporting Files:[/bold] {', '.join(skill.supporting_files)}")

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title=f"[bold cyan]Skill: {skill.metadata.name}[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

        # Show content preview
        if skill.content:
            self.console.print("\n[bold]Instructions:[/bold]")
            preview = skill.content[:500]
            if len(skill.content) > 500:
                preview += "..."
            self.console.print(Markdown(preview))

    def show_help(self):
        """Show skills help"""
        help_text = """
[bold cyan]Skills System[/bold cyan]

Model-invoked capabilities via SKILL.md files.

[bold]Commands:[/bold]
  [green]/skills[/green]             List available skills
  [green]/skill <name>[/green]       Show skill details
  [green]/skill create[/green]       Create new skill
  [green]/skill edit <name>[/green]  Edit skill
  [green]/skill delete <n>[/green]   Delete skill
  [green]/skill reload[/green]       Reload all skills

[bold]Skill Locations:[/bold]
  Personal: ~/.bharatbuild/skills/
  Project:  .bharatbuild/skills/

[bold]SKILL.md Format:[/bold]
```markdown
---
name: My Skill
description: What it does
triggers:
  - keyword1
  - keyword2
allowed-tools:
  - Read
  - Write
---

# Instructions

The model will follow these instructions...
```

[bold]Auto-Activation:[/bold]
  Skills can be automatically activated based on:
  - Trigger keywords in user messages
  - Tags matching context
  - Priority ordering

[bold]Examples:[/bold]
  /skill create "Code Review"
  /skill show code-review
  /skills
"""
        self.console.print(help_text)


# Default skill templates
DEFAULT_SKILLS = {
    "code-review": """---
name: Code Review
description: Review code for quality, bugs, and improvements
triggers:
  - review
  - code review
  - check code
tags:
  - quality
  - review
---

# Code Review Skill

When reviewing code:

1. **Check for bugs**: Look for potential runtime errors, edge cases, null checks
2. **Code quality**: Assess readability, naming conventions, structure
3. **Performance**: Identify potential bottlenecks or inefficiencies
4. **Security**: Check for common vulnerabilities (injection, XSS, etc.)
5. **Best practices**: Verify adherence to language/framework conventions

Provide specific, actionable feedback with code examples where helpful.
""",

    "test-writer": """---
name: Test Writer
description: Generate comprehensive tests for code
triggers:
  - write tests
  - add tests
  - test coverage
tags:
  - testing
  - quality
---

# Test Writer Skill

When writing tests:

1. Identify the code to test
2. Determine appropriate test framework
3. Write tests covering:
   - Happy path scenarios
   - Edge cases
   - Error conditions
   - Boundary values
4. Use descriptive test names
5. Follow AAA pattern (Arrange, Act, Assert)

Generate complete, runnable test files.
""",

    "documentation": """---
name: Documentation
description: Generate documentation for code
triggers:
  - document
  - add docs
  - documentation
tags:
  - docs
  - documentation
---

# Documentation Skill

When documenting code:

1. Add clear docstrings/comments to functions and classes
2. Explain parameters, return values, and exceptions
3. Include usage examples
4. Generate README sections if needed
5. Follow language-specific documentation conventions

Focus on clarity and completeness.
""",
}
