"""
BharatBuild CLI Init Command

Initialize projects and configuration:
  /init              Initialize in current directory
  /init --global     Initialize global config
  /init --template   Use a template
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table


class ProjectTemplate(str, Enum):
    """Available project templates"""
    PYTHON = "python"
    NODEJS = "nodejs"
    REACT = "react"
    NEXTJS = "nextjs"
    FASTAPI = "fastapi"
    FLASK = "flask"
    EXPRESS = "express"
    GENERIC = "generic"


@dataclass
class TemplateConfig:
    """Configuration for a project template"""
    name: str
    description: str
    files: Dict[str, str]  # filename -> content
    directories: List[str]
    dependencies: List[str]
    dev_dependencies: List[str]
    scripts: Dict[str, str]
    bharatbuild_config: Dict[str, Any]


# Template definitions
TEMPLATES: Dict[ProjectTemplate, TemplateConfig] = {
    ProjectTemplate.PYTHON: TemplateConfig(
        name="Python Project",
        description="Basic Python project structure",
        files={
            "requirements.txt": "# Add your dependencies here\n",
            "main.py": '''"""
Main entry point
"""

def main():
    print("Hello from BharatBuild!")

if __name__ == "__main__":
    main()
''',
            ".gitignore": """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.venv/
venv/
.env
""",
        },
        directories=["src", "tests"],
        dependencies=[],
        dev_dependencies=["pytest", "black", "flake8"],
        scripts={},
        bharatbuild_config={
            "language": "Python",
            "code_style": {"indentation": "4 spaces", "quotes": "double"},
        }
    ),

    ProjectTemplate.FASTAPI: TemplateConfig(
        name="FastAPI Project",
        description="FastAPI web API project",
        files={
            "requirements.txt": """fastapi
uvicorn[standard]
pydantic
""",
            "main.py": '''"""
FastAPI Application
"""
from fastapi import FastAPI

app = FastAPI(title="My API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Hello from BharatBuild!"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
''',
            ".gitignore": """# Python
__pycache__/
*.py[cod]
.venv/
venv/
.env
""",
        },
        directories=["app", "app/api", "app/models", "tests"],
        dependencies=["fastapi", "uvicorn", "pydantic"],
        dev_dependencies=["pytest", "httpx"],
        scripts={"start": "uvicorn main:app --reload"},
        bharatbuild_config={
            "language": "Python",
            "framework": "FastAPI",
            "code_style": {"indentation": "4 spaces"},
        }
    ),

    ProjectTemplate.NODEJS: TemplateConfig(
        name="Node.js Project",
        description="Basic Node.js project",
        files={
            "index.js": '''/**
 * Main entry point
 */

function main() {
    console.log("Hello from BharatBuild!");
}

main();
''',
            ".gitignore": """# Node
node_modules/
.env
dist/
coverage/
""",
        },
        directories=["src", "tests"],
        dependencies=[],
        dev_dependencies=["jest"],
        scripts={"start": "node index.js", "test": "jest"},
        bharatbuild_config={
            "language": "JavaScript",
            "code_style": {"indentation": "2 spaces", "quotes": "single", "semicolons": "yes"},
        }
    ),

    ProjectTemplate.REACT: TemplateConfig(
        name="React Project",
        description="React frontend project",
        files={
            "src/App.jsx": '''import React from 'react';

function App() {
  return (
    <div className="App">
      <h1>Hello from BharatBuild!</h1>
    </div>
  );
}

export default App;
''',
            "src/index.jsx": '''import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
''',
            ".gitignore": """node_modules/
dist/
.env
coverage/
""",
        },
        directories=["src", "src/components", "src/hooks", "public"],
        dependencies=["react", "react-dom"],
        dev_dependencies=["vite", "@vitejs/plugin-react"],
        scripts={"dev": "vite", "build": "vite build"},
        bharatbuild_config={
            "language": "JavaScript/React",
            "code_style": {"indentation": "2 spaces", "quotes": "single"},
        }
    ),

    ProjectTemplate.GENERIC: TemplateConfig(
        name="Generic Project",
        description="Minimal project setup",
        files={
            ".gitignore": """# Common
.env
.DS_Store
*.log
""",
        },
        directories=["src", "docs"],
        dependencies=[],
        dev_dependencies=[],
        scripts={},
        bharatbuild_config={}
    ),
}


class InitCommand:
    """
    Initialize BharatBuild projects and configuration.

    Usage:
        init = InitCommand(console)

        # Interactive init
        init.run_interactive()

        # Init with template
        init.init_project(ProjectTemplate.FASTAPI)

        # Init global config
        init.init_global_config()
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

    def run_interactive(self):
        """Run interactive initialization"""
        self.console.print("\n[bold cyan]BharatBuild AI Project Setup[/bold cyan]\n")

        # Check if already initialized
        if (self.project_dir / "BHARATBUILD.md").exists():
            if not Confirm.ask("Project already has BHARATBUILD.md. Reinitialize?"):
                return

        # Choose template
        self.console.print("[bold]Available Templates:[/bold]")
        for i, (key, template) in enumerate(TEMPLATES.items(), 1):
            self.console.print(f"  {i}. {template.name} - {template.description}")

        choice = Prompt.ask(
            "Select template",
            choices=[str(i) for i in range(1, len(TEMPLATES) + 1)],
            default="1"
        )

        template_key = list(TEMPLATES.keys())[int(choice) - 1]

        # Get project name
        default_name = self.project_dir.name
        project_name = Prompt.ask("Project name", default=default_name)

        # Get description
        description = Prompt.ask("Project description", default="A BharatBuild AI project")

        # Initialize
        self.init_project(
            template=template_key,
            project_name=project_name,
            description=description
        )

        # Ask about global config
        if not (self.config_dir / "config.json").exists():
            if Confirm.ask("\nSet up global configuration?"):
                self.init_global_config()

    def init_project(
        self,
        template: ProjectTemplate = ProjectTemplate.GENERIC,
        project_name: str = "",
        description: str = "",
        create_files: bool = True
    ):
        """Initialize project with template"""
        template_config = TEMPLATES.get(template, TEMPLATES[ProjectTemplate.GENERIC])

        self.console.print(f"\n[cyan]Initializing {template_config.name}...[/cyan]")

        # Create directories
        for dir_path in template_config.directories:
            full_path = self.project_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            self.console.print(f"  [green]✓[/green] Created {dir_path}/")

        # Create files
        if create_files:
            for filename, content in template_config.files.items():
                file_path = self.project_dir / filename

                # Create parent directories if needed
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Don't overwrite existing files
                if file_path.exists():
                    self.console.print(f"  [yellow]○[/yellow] Skipped {filename} (exists)")
                    continue

                file_path.write_text(content)
                self.console.print(f"  [green]✓[/green] Created {filename}")

        # Create BHARATBUILD.md
        self._create_bharatbuild_md(
            project_name=project_name or self.project_dir.name,
            description=description,
            template_config=template_config
        )

        # Create package.json for Node projects
        if template in [ProjectTemplate.NODEJS, ProjectTemplate.REACT, ProjectTemplate.NEXTJS]:
            self._create_package_json(
                project_name=project_name or self.project_dir.name,
                template_config=template_config
            )

        self.console.print(f"\n[green]✓ Project initialized![/green]")
        self.console.print(f"[dim]Edit BHARATBUILD.md to customize AI behavior[/dim]")

    def _create_bharatbuild_md(
        self,
        project_name: str,
        description: str,
        template_config: TemplateConfig
    ):
        """Create BHARATBUILD.md file"""
        config = template_config.bharatbuild_config

        content = f"""# {project_name}

{description}

## Project Info

- **Name**: {project_name}
- **Description**: {description}
- **Type**: {template_config.name}

## System Prompt

```
You are helping with the {project_name} project.
Focus on clean, maintainable code following best practices.
```

## Code Style

"""
        # Add code style from template
        for key, value in config.get("code_style", {}).items():
            content += f"- **{key.replace('_', ' ').title()}**: {value}\n"

        content += """
## Permissions

### Allowed Paths
- src/
- tests/
- docs/

### Denied Paths
- .env
- node_modules/
- __pycache__/

## Custom Rules

1. Write clean, readable code
2. Add comments for complex logic
3. Follow project conventions
4. Write tests for new features

## Memory Hints

- Project initialized with BharatBuild AI
"""
        if config.get("framework"):
            content += f"- Uses {config['framework']} framework\n"

        if config.get("language"):
            content += f"- Primary language: {config['language']}\n"

        file_path = self.project_dir / "BHARATBUILD.md"

        if file_path.exists():
            # Backup existing
            backup_path = self.project_dir / "BHARATBUILD.md.backup"
            file_path.rename(backup_path)
            self.console.print(f"  [yellow]○[/yellow] Backed up existing BHARATBUILD.md")

        file_path.write_text(content)
        self.console.print(f"  [green]✓[/green] Created BHARATBUILD.md")

    def _create_package_json(self, project_name: str, template_config: TemplateConfig):
        """Create package.json for Node projects"""
        package_path = self.project_dir / "package.json"

        if package_path.exists():
            return

        package = {
            "name": project_name.lower().replace(" ", "-"),
            "version": "1.0.0",
            "description": f"{project_name} - Created with BharatBuild AI",
            "main": "index.js",
            "scripts": template_config.scripts or {"test": "echo \"Error: no test specified\" && exit 1"},
            "keywords": [],
            "author": "",
            "license": "MIT",
            "dependencies": {},
            "devDependencies": {}
        }

        package_path.write_text(json.dumps(package, indent=2))
        self.console.print(f"  [green]✓[/green] Created package.json")

    def init_global_config(self):
        """Initialize global configuration"""
        self.console.print("\n[bold cyan]Global Configuration Setup[/bold cyan]\n")

        # Create config directory
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Get API key
        api_key = Prompt.ask(
            "Anthropic API Key",
            password=True,
            default=""
        )

        # Get default model
        model = Prompt.ask(
            "Default model",
            choices=["haiku", "sonnet", "opus"],
            default="sonnet"
        )

        # Get preferences
        config = {
            "api_key": api_key,
            "model": f"claude-3-{model}-20240229",
            "max_tokens": 4096,
            "theme": "default",
            "editor": os.environ.get("EDITOR", ""),
            "auto_save": True,
            "sound_enabled": True,
            "telemetry_enabled": False,
        }

        # Save config
        config_path = self.config_dir / "config.json"
        config_path.write_text(json.dumps(config, indent=2))

        # Set restrictive permissions on config file (contains API key)
        try:
            os.chmod(config_path, 0o600)
        except Exception:
            pass

        self.console.print(f"\n[green]✓ Global config saved to {config_path}[/green]")

        # Create other config files
        self._create_default_prompts()
        self._create_default_hooks()

    def _create_default_prompts(self):
        """Create default prompt files"""
        prompts_dir = self.config_dir / "prompts"
        prompts_dir.mkdir(exist_ok=True)

        default_prompt = """You are BharatBuild AI, an intelligent coding assistant.
You help developers write clean, efficient, and maintainable code.
Always explain your reasoning and suggest best practices.
"""

        (prompts_dir / "default.txt").write_text(default_prompt)
        self.console.print(f"  [green]✓[/green] Created default prompts")

    def _create_default_hooks(self):
        """Create default hooks configuration"""
        hooks_file = self.config_dir / "hooks.json"

        hooks = {
            "pre_file_write": [],
            "post_file_write": [],
            "pre_bash": [],
            "post_bash": [],
        }

        hooks_file.write_text(json.dumps(hooks, indent=2))
        self.console.print(f"  [green]✓[/green] Created hooks config")

    def show_templates(self):
        """Display available templates"""
        table = Table(title="Available Templates", show_header=True, header_style="bold cyan")
        table.add_column("Template")
        table.add_column("Description")
        table.add_column("Language")

        for key, config in TEMPLATES.items():
            lang = config.bharatbuild_config.get("language", "Generic")
            table.add_row(key.value, config.description, lang)

        self.console.print(table)

    def show_status(self):
        """Show initialization status"""
        content_lines = []

        # Project status
        has_bharatbuild = (self.project_dir / "BHARATBUILD.md").exists()
        content_lines.append(f"[bold]Project Directory:[/bold] {self.project_dir}")
        content_lines.append(
            f"[bold]BHARATBUILD.md:[/bold] {'[green]Found[/green]' if has_bharatbuild else '[yellow]Not found[/yellow]'}"
        )

        # Detect project type
        detected = []
        if (self.project_dir / "package.json").exists():
            detected.append("Node.js")
        if (self.project_dir / "requirements.txt").exists():
            detected.append("Python")
        if (self.project_dir / "pyproject.toml").exists():
            detected.append("Python")

        if detected:
            content_lines.append(f"[bold]Detected Type:[/bold] {', '.join(detected)}")

        content_lines.append("")

        # Global config status
        has_config = (self.config_dir / "config.json").exists()
        content_lines.append(f"[bold]Config Directory:[/bold] {self.config_dir}")
        content_lines.append(
            f"[bold]Global Config:[/bold] {'[green]Found[/green]' if has_config else '[yellow]Not found[/yellow]'}"
        )

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title="[bold cyan]Initialization Status[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)
