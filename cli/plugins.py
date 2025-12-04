"""
BharatBuild CLI Plugin System

Install and manage plugins:
  /plugins            List installed plugins
  /plugin install     Install plugin
  /plugin remove      Remove plugin
  /plugin enable      Enable plugin
  /plugin disable     Disable plugin
"""

import os
import json
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import urllib.request

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm


class PluginType(str, Enum):
    """Types of plugins"""
    COMMAND = "command"       # Adds slash commands
    AGENT = "agent"           # Adds custom agents
    SKILL = "skill"           # Adds skills
    HOOK = "hook"             # Adds hooks
    MCP = "mcp"               # MCP server integration
    THEME = "theme"           # UI themes
    EXTENSION = "extension"   # General extension


@dataclass
class PluginManifest:
    """Plugin manifest (plugin.json)"""
    id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    homepage: str = ""
    repository: str = ""
    license: str = "MIT"

    # Plugin type and capabilities
    type: PluginType = PluginType.EXTENSION
    provides: List[str] = field(default_factory=list)  # What it provides

    # Dependencies
    requires: List[str] = field(default_factory=list)  # Required plugins
    python_requires: str = ""  # Python version requirement
    dependencies: List[str] = field(default_factory=list)  # pip packages

    # Entry points
    main: str = ""  # Main module/file
    commands: Dict[str, str] = field(default_factory=dict)  # command -> handler
    hooks: Dict[str, str] = field(default_factory=dict)  # event -> handler

    # Permissions
    permissions: List[str] = field(default_factory=list)  # Required permissions


@dataclass
class InstalledPlugin:
    """An installed plugin"""
    manifest: PluginManifest
    path: Path
    enabled: bool = True
    installed_at: str = ""
    updated_at: str = ""


class PluginManager:
    """
    Manages BharatBuild plugins.

    Plugin structure:
    ```
    my-plugin/
        plugin.json       # Manifest
        main.py           # Entry point
        commands/         # Slash commands
        skills/           # Skills
        agents/           # Agents
        hooks/            # Hooks
        README.md
    ```

    Usage:
        manager = PluginManager(console, config_dir)

        # Install plugin
        manager.install_from_url("https://...")

        # List plugins
        manager.list_plugins()

        # Enable/disable
        manager.enable_plugin("my-plugin")
    """

    MARKETPLACE_URL = "https://plugins.bharatbuild.ai"  # Placeholder

    def __init__(self, console: Console, config_dir: Path = None):
        self.console = console
        self.config_dir = config_dir or Path.home() / ".bharatbuild"
        self.plugins_dir = self.config_dir / "plugins"
        self.registry_file = self.config_dir / "plugins_registry.json"

        # Ensure directories exist
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

        # Load registry
        self._plugins: Dict[str, InstalledPlugin] = {}
        self._load_registry()

    def _load_registry(self):
        """Load plugins registry"""
        if self.registry_file.exists():
            try:
                with open(self.registry_file) as f:
                    data = json.load(f)

                for plugin_data in data.get("plugins", []):
                    plugin = self._load_plugin_data(plugin_data)
                    if plugin:
                        self._plugins[plugin.manifest.id] = plugin

            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load plugin registry: {e}[/yellow]")

        # Scan plugins directory for unregistered plugins
        self._scan_plugins_dir()

    def _scan_plugins_dir(self):
        """Scan plugins directory for plugins"""
        for plugin_dir in self.plugins_dir.iterdir():
            if plugin_dir.is_dir():
                manifest_file = plugin_dir / "plugin.json"
                if manifest_file.exists() and plugin_dir.name not in self._plugins:
                    plugin = self._load_plugin_from_dir(plugin_dir)
                    if plugin:
                        self._plugins[plugin.manifest.id] = plugin

    def _load_plugin_from_dir(self, plugin_dir: Path) -> Optional[InstalledPlugin]:
        """Load plugin from directory"""
        manifest_file = plugin_dir / "plugin.json"

        if not manifest_file.exists():
            return None

        try:
            with open(manifest_file) as f:
                data = json.load(f)

            manifest = PluginManifest(
                id=data.get("id", plugin_dir.name),
                name=data.get("name", plugin_dir.name),
                description=data.get("description", ""),
                version=data.get("version", "1.0.0"),
                author=data.get("author", ""),
                homepage=data.get("homepage", ""),
                repository=data.get("repository", ""),
                license=data.get("license", "MIT"),
                type=PluginType(data.get("type", "extension")),
                provides=data.get("provides", []),
                requires=data.get("requires", []),
                python_requires=data.get("python_requires", ""),
                dependencies=data.get("dependencies", []),
                main=data.get("main", ""),
                commands=data.get("commands", {}),
                hooks=data.get("hooks", {}),
                permissions=data.get("permissions", [])
            )

            return InstalledPlugin(
                manifest=manifest,
                path=plugin_dir,
                enabled=True,
                installed_at=datetime.now().isoformat()
            )

        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not load plugin {plugin_dir.name}: {e}[/yellow]")
            return None

    def _load_plugin_data(self, data: Dict) -> Optional[InstalledPlugin]:
        """Load plugin from registry data"""
        try:
            manifest = PluginManifest(
                id=data["id"],
                name=data.get("name", data["id"]),
                description=data.get("description", ""),
                version=data.get("version", "1.0.0"),
                author=data.get("author", ""),
                type=PluginType(data.get("type", "extension")),
                provides=data.get("provides", []),
                commands=data.get("commands", {}),
                hooks=data.get("hooks", {})
            )

            plugin_path = self.plugins_dir / data["id"]

            return InstalledPlugin(
                manifest=manifest,
                path=plugin_path,
                enabled=data.get("enabled", True),
                installed_at=data.get("installed_at", ""),
                updated_at=data.get("updated_at", "")
            )

        except Exception:
            return None

    def _save_registry(self):
        """Save plugins registry"""
        data = {
            "plugins": [
                {
                    "id": plugin.manifest.id,
                    "name": plugin.manifest.name,
                    "description": plugin.manifest.description,
                    "version": plugin.manifest.version,
                    "author": plugin.manifest.author,
                    "type": plugin.manifest.type.value,
                    "provides": plugin.manifest.provides,
                    "commands": plugin.manifest.commands,
                    "hooks": plugin.manifest.hooks,
                    "enabled": plugin.enabled,
                    "installed_at": plugin.installed_at,
                    "updated_at": plugin.updated_at
                }
                for plugin in self._plugins.values()
            ]
        }

        with open(self.registry_file, 'w') as f:
            json.dump(data, f, indent=2)

    # ==================== Installation ====================

    def install_from_url(self, url: str) -> bool:
        """Install plugin from URL"""
        self.console.print(f"[cyan]Downloading plugin from {url}...[/cyan]")

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                zip_path = temp_path / "plugin.zip"

                # Download
                urllib.request.urlretrieve(url, zip_path)

                # Extract
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path / "extracted")

                # Find plugin directory
                extracted = temp_path / "extracted"
                plugin_dirs = [d for d in extracted.iterdir() if d.is_dir()]

                if not plugin_dirs:
                    self.console.print("[red]No plugin found in archive[/red]")
                    return False

                plugin_source = plugin_dirs[0]

                # Install
                return self._install_from_dir(plugin_source)

        except Exception as e:
            self.console.print(f"[red]Failed to install plugin: {e}[/red]")
            return False

    def install_from_path(self, path: Path) -> bool:
        """Install plugin from local path"""
        if not path.exists():
            self.console.print(f"[red]Path not found: {path}[/red]")
            return False

        if path.is_file() and path.suffix == ".zip":
            # Extract and install
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                with zipfile.ZipFile(path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)

                plugin_dirs = [d for d in temp_path.iterdir() if d.is_dir()]
                if plugin_dirs:
                    return self._install_from_dir(plugin_dirs[0])

        elif path.is_dir():
            return self._install_from_dir(path)

        self.console.print("[red]Invalid plugin path[/red]")
        return False

    def _install_from_dir(self, source_dir: Path) -> bool:
        """Install plugin from directory"""
        manifest_file = source_dir / "plugin.json"

        if not manifest_file.exists():
            self.console.print("[red]No plugin.json found[/red]")
            return False

        try:
            with open(manifest_file) as f:
                manifest_data = json.load(f)

            plugin_id = manifest_data.get("id", source_dir.name)

            # Check if already installed
            if plugin_id in self._plugins:
                if not Confirm.ask(f"Plugin '{plugin_id}' already installed. Update?"):
                    return False
                # Remove old version
                self.uninstall(plugin_id, confirm=False)

            # Copy to plugins directory
            dest_dir = self.plugins_dir / plugin_id
            shutil.copytree(source_dir, dest_dir)

            # Install dependencies
            dependencies = manifest_data.get("dependencies", [])
            if dependencies:
                self._install_dependencies(dependencies)

            # Load plugin
            plugin = self._load_plugin_from_dir(dest_dir)
            if plugin:
                self._plugins[plugin_id] = plugin
                self._save_registry()

                self.console.print(f"[green]✓ Installed plugin: {manifest_data.get('name', plugin_id)}[/green]")
                return True

        except Exception as e:
            self.console.print(f"[red]Failed to install plugin: {e}[/red]")

        return False

    def _install_dependencies(self, dependencies: List[str]):
        """Install pip dependencies"""
        if not dependencies:
            return

        self.console.print("[cyan]Installing dependencies...[/cyan]")

        import subprocess
        for dep in dependencies:
            try:
                subprocess.run(
                    ["pip", "install", dep],
                    capture_output=True,
                    timeout=60
                )
            except Exception:
                self.console.print(f"[yellow]Warning: Could not install {dep}[/yellow]")

    def uninstall(self, plugin_id: str, confirm: bool = True) -> bool:
        """Uninstall a plugin"""
        if plugin_id not in self._plugins:
            self.console.print(f"[red]Plugin not found: {plugin_id}[/red]")
            return False

        plugin = self._plugins[plugin_id]

        if confirm and not Confirm.ask(f"Uninstall '{plugin.manifest.name}'?"):
            return False

        # Remove directory
        if plugin.path.exists():
            shutil.rmtree(plugin.path)

        del self._plugins[plugin_id]
        self._save_registry()

        self.console.print(f"[green]✓ Uninstalled: {plugin.manifest.name}[/green]")
        return True

    # ==================== Enable/Disable ====================

    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a plugin"""
        if plugin_id not in self._plugins:
            self.console.print(f"[red]Plugin not found: {plugin_id}[/red]")
            return False

        self._plugins[plugin_id].enabled = True
        self._save_registry()

        self.console.print(f"[green]✓ Enabled: {self._plugins[plugin_id].manifest.name}[/green]")
        return True

    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin"""
        if plugin_id not in self._plugins:
            self.console.print(f"[red]Plugin not found: {plugin_id}[/red]")
            return False

        self._plugins[plugin_id].enabled = False
        self._save_registry()

        self.console.print(f"[green]✓ Disabled: {self._plugins[plugin_id].manifest.name}[/green]")
        return True

    def is_enabled(self, plugin_id: str) -> bool:
        """Check if plugin is enabled"""
        plugin = self._plugins.get(plugin_id)
        return plugin.enabled if plugin else False

    # ==================== Plugin Access ====================

    def get_plugin(self, plugin_id: str) -> Optional[InstalledPlugin]:
        """Get plugin by ID"""
        return self._plugins.get(plugin_id)

    def get_all_plugins(self) -> List[InstalledPlugin]:
        """Get all installed plugins"""
        return list(self._plugins.values())

    def get_enabled_plugins(self) -> List[InstalledPlugin]:
        """Get all enabled plugins"""
        return [p for p in self._plugins.values() if p.enabled]

    def get_plugin_commands(self) -> Dict[str, tuple]:
        """Get all commands from enabled plugins"""
        commands = {}
        for plugin in self.get_enabled_plugins():
            for cmd, handler in plugin.manifest.commands.items():
                commands[cmd] = (plugin.manifest.id, handler)
        return commands

    def get_plugin_hooks(self, event: str) -> List[tuple]:
        """Get all hooks for an event from enabled plugins"""
        hooks = []
        for plugin in self.get_enabled_plugins():
            if event in plugin.manifest.hooks:
                hooks.append((plugin.manifest.id, plugin.manifest.hooks[event]))
        return hooks

    # ==================== Marketplace ====================

    def search_marketplace(self, query: str = "") -> List[Dict]:
        """Search marketplace for plugins"""
        # This would connect to a real marketplace API
        # For now, return sample data
        sample_plugins = [
            {
                "id": "git-helper",
                "name": "Git Helper",
                "description": "Enhanced git commands and workflows",
                "author": "BharatBuild",
                "downloads": 1000
            },
            {
                "id": "docker-tools",
                "name": "Docker Tools",
                "description": "Docker and container management",
                "author": "BharatBuild",
                "downloads": 500
            },
            {
                "id": "test-runner",
                "name": "Test Runner",
                "description": "Run and manage tests easily",
                "author": "Community",
                "downloads": 750
            }
        ]

        if query:
            query_lower = query.lower()
            return [p for p in sample_plugins if query_lower in p["name"].lower() or query_lower in p["description"].lower()]

        return sample_plugins

    # ==================== Display ====================

    def list_plugins(self):
        """List all installed plugins"""
        if not self._plugins:
            self.console.print("[dim]No plugins installed[/dim]")
            self.console.print("[dim]Use /plugin install to add plugins[/dim]")
            return

        table = Table(title="Installed Plugins", show_header=True, header_style="bold cyan")
        table.add_column("Name")
        table.add_column("Version")
        table.add_column("Type")
        table.add_column("Status")
        table.add_column("Provides")

        for plugin in sorted(self._plugins.values(), key=lambda p: p.manifest.name):
            status = "[green]Enabled[/green]" if plugin.enabled else "[dim]Disabled[/dim]"

            provides = ", ".join(plugin.manifest.provides[:3])
            if len(plugin.manifest.provides) > 3:
                provides += "..."

            table.add_row(
                f"[bold]{plugin.manifest.name}[/bold]",
                plugin.manifest.version,
                plugin.manifest.type.value,
                status,
                provides or "[dim]-[/dim]"
            )

        self.console.print(table)

    def show_plugin(self, plugin_id: str):
        """Show plugin details"""
        plugin = self.get_plugin(plugin_id)

        if not plugin:
            self.console.print(f"[red]Plugin not found: {plugin_id}[/red]")
            return

        content_lines = []
        content_lines.append(f"[bold]Name:[/bold] {plugin.manifest.name}")
        content_lines.append(f"[bold]ID:[/bold] {plugin.manifest.id}")
        content_lines.append(f"[bold]Version:[/bold] {plugin.manifest.version}")
        content_lines.append(f"[bold]Author:[/bold] {plugin.manifest.author or 'Unknown'}")
        content_lines.append(f"[bold]Type:[/bold] {plugin.manifest.type.value}")
        content_lines.append(f"[bold]Status:[/bold] {'Enabled' if plugin.enabled else 'Disabled'}")
        content_lines.append(f"[bold]Path:[/bold] {plugin.path}")
        content_lines.append("")

        if plugin.manifest.description:
            content_lines.append(f"[bold]Description:[/bold]")
            content_lines.append(f"  {plugin.manifest.description}")
            content_lines.append("")

        if plugin.manifest.provides:
            content_lines.append(f"[bold]Provides:[/bold] {', '.join(plugin.manifest.provides)}")

        if plugin.manifest.commands:
            content_lines.append(f"[bold]Commands:[/bold] {', '.join(plugin.manifest.commands.keys())}")

        if plugin.manifest.hooks:
            content_lines.append(f"[bold]Hooks:[/bold] {', '.join(plugin.manifest.hooks.keys())}")

        if plugin.manifest.dependencies:
            content_lines.append(f"[bold]Dependencies:[/bold] {', '.join(plugin.manifest.dependencies)}")

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title=f"[bold cyan]Plugin: {plugin.manifest.name}[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

    def show_help(self):
        """Show plugin help"""
        help_text = """
[bold cyan]Plugin System[/bold cyan]

Install and manage plugins.

[bold]Commands:[/bold]
  [green]/plugins[/green]            List installed plugins
  [green]/plugin show <id>[/green]   Show plugin details
  [green]/plugin install[/green]     Install from URL/path
  [green]/plugin remove <id>[/green] Uninstall plugin
  [green]/plugin enable <id>[/green] Enable plugin
  [green]/plugin disable <id>[/green] Disable plugin
  [green]/plugin search[/green]      Search marketplace

[bold]Plugin Types:[/bold]
  • command   - Adds slash commands
  • agent     - Adds custom agents
  • skill     - Adds skills
  • hook      - Adds event hooks
  • mcp       - MCP server integration
  • theme     - UI themes
  • extension - General extension

[bold]Plugin Location:[/bold]
  ~/.bharatbuild/plugins/

[bold]Creating Plugins:[/bold]
  1. Create directory with plugin.json
  2. Add main.py entry point
  3. Install with /plugin install <path>

[bold]Examples:[/bold]
  /plugin install https://example.com/plugin.zip
  /plugin install ./my-plugin
  /plugin enable git-helper
"""
        self.console.print(help_text)


# Plugin template for creating new plugins
PLUGIN_TEMPLATE = {
    "plugin.json": """{
  "id": "my-plugin",
  "name": "My Plugin",
  "description": "Description of what this plugin does",
  "version": "1.0.0",
  "author": "Your Name",
  "type": "extension",
  "provides": ["feature1", "feature2"],
  "commands": {
    "mycommand": "main:handle_mycommand"
  },
  "hooks": {},
  "dependencies": []
}
""",
    "main.py": '''"""
My Plugin - Main entry point
"""

def handle_mycommand(args, context):
    """Handle /mycommand"""
    return "Hello from my plugin!"

def on_load(context):
    """Called when plugin is loaded"""
    print("My plugin loaded!")

def on_unload(context):
    """Called when plugin is unloaded"""
    print("My plugin unloaded!")
''',
    "README.md": """# My Plugin

Description of your plugin.

## Installation

```bash
/plugin install <path-to-plugin>
```

## Usage

```
/mycommand
```

## License

MIT
"""
}
