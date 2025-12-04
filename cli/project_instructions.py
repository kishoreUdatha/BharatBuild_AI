"""
BharatBuild CLI Project Instructions

Reads and applies BHARATBUILD.md instructions from project root.
Similar to Claude Code's CLAUDE.md feature.

Usage:
  Place a BHARATBUILD.md file in your project root to customize behavior.
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown


@dataclass
class ProjectInstructions:
    """Parsed project instructions"""
    # Meta
    project_name: str = ""
    description: str = ""

    # Behavior
    system_prompt: str = ""
    code_style: Dict[str, Any] = field(default_factory=dict)
    file_patterns: Dict[str, str] = field(default_factory=dict)

    # Permissions
    allowed_paths: List[str] = field(default_factory=list)
    denied_paths: List[str] = field(default_factory=list)
    allowed_commands: List[str] = field(default_factory=list)
    denied_commands: List[str] = field(default_factory=list)

    # Context
    always_include: List[str] = field(default_factory=list)
    ignore_patterns: List[str] = field(default_factory=list)

    # Custom
    custom_rules: List[str] = field(default_factory=list)
    memory_hints: List[str] = field(default_factory=list)

    # Raw
    raw_content: str = ""


# Default template for BHARATBUILD.md
DEFAULT_TEMPLATE = '''# BharatBuild AI Project Instructions

This file customizes how BharatBuild AI works with your project.

## Project Info

- **Name**: My Project
- **Description**: Brief description of your project

## System Prompt

Add custom instructions for the AI here. These will be prepended to every conversation.

```
You are helping with a [type] project. Focus on [key priorities].
Always follow [specific guidelines].
```

## Code Style

Specify your preferred code style:

- **Language**: Python/JavaScript/TypeScript/etc.
- **Indentation**: 4 spaces / 2 spaces / tabs
- **Quotes**: single / double
- **Semicolons**: yes / no (for JS/TS)
- **Line Length**: 80 / 100 / 120

## File Patterns

Map file types to their purposes:

```yaml
src/**/*.py: Source code
tests/**/*.py: Test files
docs/*.md: Documentation
```

## Permissions

### Allowed Paths
Paths the AI can freely read/write:
- src/
- tests/
- docs/

### Denied Paths
Paths the AI should never modify:
- .env
- secrets/
- credentials.json

### Allowed Commands
Commands the AI can run:
- pytest
- npm test
- python

### Denied Commands
Commands the AI should never run:
- rm -rf
- sudo
- format

## Context

### Always Include
Files to always include in context:
- README.md
- src/config.py

### Ignore Patterns
Patterns to ignore when indexing:
- node_modules/
- __pycache__/
- *.pyc
- .git/

## Custom Rules

Add any project-specific rules:

1. Always add docstrings to new functions
2. Follow PEP 8 style guidelines
3. Write tests for new features
4. Use type hints for function parameters

## Memory Hints

Things the AI should remember about this project:

- Main entry point is src/main.py
- Database is PostgreSQL
- Frontend uses React
- API follows REST conventions
'''


class ProjectInstructionsManager:
    """
    Manages project-specific instructions from BHARATBUILD.md.

    Usage:
        manager = ProjectInstructionsManager(project_root, console)

        # Load instructions
        manager.load()

        # Get system prompt additions
        prompt = manager.get_system_prompt()

        # Check if path is allowed
        if manager.is_path_allowed("src/app.py"):
            # proceed
    """

    # Instruction file names to look for (in priority order)
    INSTRUCTION_FILES = [
        "BHARATBUILD.md",
        ".bharatbuild.md",
        "bharatbuild.md",
        ".bharatbuild/instructions.md",
    ]

    def __init__(self, project_root: Path, console: Console):
        self.project_root = project_root
        self.console = console
        self.instructions: Optional[ProjectInstructions] = None
        self._file_path: Optional[Path] = None

    def find_instructions_file(self) -> Optional[Path]:
        """Find the instructions file in the project"""
        for filename in self.INSTRUCTION_FILES:
            filepath = self.project_root / filename
            if filepath.exists():
                return filepath
        return None

    def load(self) -> bool:
        """Load project instructions"""
        self._file_path = self.find_instructions_file()

        if not self._file_path:
            self.instructions = ProjectInstructions()
            return False

        try:
            content = self._file_path.read_text(encoding='utf-8')
            self.instructions = self._parse_instructions(content)
            self.instructions.raw_content = content
            return True

        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not load instructions: {e}[/yellow]")
            self.instructions = ProjectInstructions()
            return False

    def _parse_instructions(self, content: str) -> ProjectInstructions:
        """Parse markdown instructions file"""
        instructions = ProjectInstructions()

        # Extract project name from title
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            instructions.project_name = title_match.group(1).strip()

        # Parse sections
        sections = self._split_sections(content)

        # Project Info
        if 'project info' in sections:
            info = sections['project info']
            name_match = re.search(r'\*\*Name\*\*:\s*(.+)', info)
            if name_match:
                instructions.project_name = name_match.group(1).strip()
            desc_match = re.search(r'\*\*Description\*\*:\s*(.+)', info)
            if desc_match:
                instructions.description = desc_match.group(1).strip()

        # System Prompt
        if 'system prompt' in sections:
            prompt = self._extract_code_block(sections['system prompt'])
            if prompt:
                instructions.system_prompt = prompt
            else:
                # Use the section text as prompt
                text = sections['system prompt'].strip()
                # Remove markdown code fences if present
                text = re.sub(r'^```\w*\n?', '', text)
                text = re.sub(r'\n?```$', '', text)
                instructions.system_prompt = text.strip()

        # Code Style
        if 'code style' in sections:
            instructions.code_style = self._parse_key_value_list(sections['code style'])

        # File Patterns
        if 'file patterns' in sections:
            yaml_block = self._extract_code_block(sections['file patterns'])
            if yaml_block:
                instructions.file_patterns = self._parse_yaml_like(yaml_block)

        # Permissions - Allowed Paths
        if 'allowed paths' in sections:
            instructions.allowed_paths = self._parse_list(sections['allowed paths'])

        # Permissions - Denied Paths
        if 'denied paths' in sections:
            instructions.denied_paths = self._parse_list(sections['denied paths'])

        # Permissions - Allowed Commands
        if 'allowed commands' in sections:
            instructions.allowed_commands = self._parse_list(sections['allowed commands'])

        # Permissions - Denied Commands
        if 'denied commands' in sections:
            instructions.denied_commands = self._parse_list(sections['denied commands'])

        # Context - Always Include
        if 'always include' in sections:
            instructions.always_include = self._parse_list(sections['always include'])

        # Context - Ignore Patterns
        if 'ignore patterns' in sections:
            instructions.ignore_patterns = self._parse_list(sections['ignore patterns'])

        # Custom Rules
        if 'custom rules' in sections:
            instructions.custom_rules = self._parse_numbered_list(sections['custom rules'])

        # Memory Hints
        if 'memory hints' in sections:
            instructions.memory_hints = self._parse_list(sections['memory hints'])

        return instructions

    def _split_sections(self, content: str) -> Dict[str, str]:
        """Split markdown into sections by headers"""
        sections = {}
        current_section = ""
        current_content = []

        for line in content.split('\n'):
            # Check for header
            header_match = re.match(r'^#{1,3}\s+(.+)$', line)
            if header_match:
                # Save previous section
                if current_section:
                    sections[current_section.lower()] = '\n'.join(current_content)

                current_section = header_match.group(1).strip()
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section.lower()] = '\n'.join(current_content)

        return sections

    def _extract_code_block(self, text: str) -> Optional[str]:
        """Extract content from code block"""
        match = re.search(r'```(?:\w*)\n?(.*?)```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _parse_list(self, text: str) -> List[str]:
        """Parse markdown list items"""
        items = []
        for line in text.split('\n'):
            # Match bullet points
            match = re.match(r'^[\s]*[-*]\s+(.+)$', line)
            if match:
                items.append(match.group(1).strip())
        return items

    def _parse_numbered_list(self, text: str) -> List[str]:
        """Parse numbered list items"""
        items = []
        for line in text.split('\n'):
            # Match numbered items
            match = re.match(r'^[\s]*\d+\.\s+(.+)$', line)
            if match:
                items.append(match.group(1).strip())
        return items

    def _parse_key_value_list(self, text: str) -> Dict[str, str]:
        """Parse key-value pairs from list"""
        result = {}
        for line in text.split('\n'):
            # Match "- **Key**: Value" or "- Key: Value"
            match = re.match(r'^[\s]*[-*]\s+\*?\*?(\w+)\*?\*?:\s*(.+)$', line)
            if match:
                key = match.group(1).strip().lower()
                value = match.group(2).strip()
                result[key] = value
        return result

    def _parse_yaml_like(self, text: str) -> Dict[str, str]:
        """Parse YAML-like key: value pairs"""
        result = {}
        for line in text.split('\n'):
            if ':' in line:
                parts = line.split(':', 1)
                key = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else ""
                if key:
                    result[key] = value
        return result

    # ==================== Access Methods ====================

    def get_system_prompt(self) -> str:
        """Get system prompt additions from instructions"""
        if not self.instructions:
            return ""

        parts = []

        # Add custom system prompt
        if self.instructions.system_prompt:
            parts.append(self.instructions.system_prompt)

        # Add code style guidelines
        if self.instructions.code_style:
            style_parts = []
            for key, value in self.instructions.code_style.items():
                style_parts.append(f"- {key}: {value}")
            if style_parts:
                parts.append("Code Style Guidelines:\n" + "\n".join(style_parts))

        # Add custom rules
        if self.instructions.custom_rules:
            rules = "\n".join(f"- {rule}" for rule in self.instructions.custom_rules)
            parts.append(f"Project Rules:\n{rules}")

        # Add memory hints
        if self.instructions.memory_hints:
            hints = "\n".join(f"- {hint}" for hint in self.instructions.memory_hints)
            parts.append(f"Project Notes:\n{hints}")

        return "\n\n".join(parts)

    def is_path_allowed(self, path: str) -> bool:
        """Check if path is allowed for modification"""
        if not self.instructions:
            return True

        # Check denied paths first
        for pattern in self.instructions.denied_paths:
            if self._path_matches(path, pattern):
                return False

        # If allowed paths specified, check them
        if self.instructions.allowed_paths:
            for pattern in self.instructions.allowed_paths:
                if self._path_matches(path, pattern):
                    return True
            return False

        return True

    def is_command_allowed(self, command: str) -> bool:
        """Check if command is allowed"""
        if not self.instructions:
            return True

        # Get base command
        base_cmd = command.split()[0] if command.split() else command

        # Check denied commands first
        for denied in self.instructions.denied_commands:
            if denied in command or base_cmd == denied:
                return False

        # If allowed commands specified, check them
        if self.instructions.allowed_commands:
            for allowed in self.instructions.allowed_commands:
                if base_cmd == allowed or command.startswith(allowed):
                    return True
            return False

        return True

    def _path_matches(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern"""
        import fnmatch

        # Normalize path separators
        path = path.replace('\\', '/')
        pattern = pattern.replace('\\', '/')

        # Remove trailing slashes
        path = path.rstrip('/')
        pattern = pattern.rstrip('/')

        # Check exact match
        if path == pattern:
            return True

        # Check if path starts with pattern (directory)
        if path.startswith(pattern + '/'):
            return True

        # Check glob pattern
        if fnmatch.fnmatch(path, pattern):
            return True

        return False

    def get_always_include_files(self) -> List[Path]:
        """Get list of files to always include in context"""
        if not self.instructions:
            return []

        files = []
        for pattern in self.instructions.always_include:
            # Try as direct path
            filepath = self.project_root / pattern
            if filepath.exists():
                files.append(filepath)
            else:
                # Try glob
                import glob
                matches = glob.glob(str(self.project_root / pattern), recursive=True)
                files.extend(Path(m) for m in matches if Path(m).is_file())

        return files

    def get_ignore_patterns(self) -> List[str]:
        """Get patterns to ignore when indexing"""
        if not self.instructions:
            return []
        return self.instructions.ignore_patterns

    # ==================== Display ====================

    def show_instructions(self):
        """Display current project instructions"""
        if not self.instructions or not self._file_path:
            self.console.print("[dim]No project instructions found[/dim]")
            self.console.print(f"[dim]Create a BHARATBUILD.md file in {self.project_root}[/dim]")
            return

        content_lines = []

        if self.instructions.project_name:
            content_lines.append(f"[bold]Project:[/bold] {self.instructions.project_name}")

        if self.instructions.description:
            content_lines.append(f"[bold]Description:[/bold] {self.instructions.description}")

        content_lines.append(f"[bold]File:[/bold] {self._file_path}")
        content_lines.append("")

        # System prompt preview
        if self.instructions.system_prompt:
            prompt_preview = self.instructions.system_prompt[:100]
            if len(self.instructions.system_prompt) > 100:
                prompt_preview += "..."
            content_lines.append(f"[bold]System Prompt:[/bold]")
            content_lines.append(f"  [dim]{prompt_preview}[/dim]")
            content_lines.append("")

        # Code style
        if self.instructions.code_style:
            content_lines.append("[bold]Code Style:[/bold]")
            for key, value in self.instructions.code_style.items():
                content_lines.append(f"  {key}: {value}")
            content_lines.append("")

        # Permissions summary
        if self.instructions.allowed_paths or self.instructions.denied_paths:
            content_lines.append("[bold]Path Permissions:[/bold]")
            if self.instructions.allowed_paths:
                content_lines.append(f"  Allowed: {', '.join(self.instructions.allowed_paths[:3])}...")
            if self.instructions.denied_paths:
                content_lines.append(f"  Denied: {', '.join(self.instructions.denied_paths[:3])}...")
            content_lines.append("")

        # Custom rules
        if self.instructions.custom_rules:
            content_lines.append(f"[bold]Custom Rules:[/bold] {len(self.instructions.custom_rules)} rules")

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title="[bold cyan]Project Instructions[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

    def show_full_instructions(self):
        """Display full markdown instructions"""
        if not self.instructions or not self.instructions.raw_content:
            self.show_instructions()
            return

        md = Markdown(self.instructions.raw_content)
        self.console.print(md)

    # ==================== Creation ====================

    def create_default(self) -> bool:
        """Create default BHARATBUILD.md file"""
        filepath = self.project_root / "BHARATBUILD.md"

        if filepath.exists():
            self.console.print("[yellow]BHARATBUILD.md already exists[/yellow]")
            return False

        try:
            filepath.write_text(DEFAULT_TEMPLATE, encoding='utf-8')
            self.console.print(f"[green]✓ Created {filepath}[/green]")
            self.console.print("[dim]Edit this file to customize BharatBuild AI behavior[/dim]")
            return True

        except Exception as e:
            self.console.print(f"[red]Error creating file: {e}[/red]")
            return False

    def edit_instructions(self):
        """Open instructions file in editor"""
        if not self._file_path:
            # Create default if not exists
            self.create_default()
            self._file_path = self.project_root / "BHARATBUILD.md"

        # Try to open in editor
        import subprocess
        import platform

        try:
            if platform.system() == 'Darwin':
                subprocess.run(['open', str(self._file_path)])
            elif platform.system() == 'Windows':
                os.startfile(str(self._file_path))
            else:
                # Try common editors
                editor = os.environ.get('EDITOR', 'nano')
                subprocess.run([editor, str(self._file_path)])

        except Exception as e:
            self.console.print(f"[yellow]Could not open editor: {e}[/yellow]")
            self.console.print(f"[dim]Edit manually: {self._file_path}[/dim]")


def load_project_instructions(project_root: Path, console: Console) -> ProjectInstructionsManager:
    """Helper to load project instructions"""
    manager = ProjectInstructionsManager(project_root, console)
    manager.load()
    return manager
