"""
BharatBuild CLI MCP (Model Context Protocol) Client

Enables connection to MCP servers for extended capabilities:
  /mcp add github
  /mcp add postgres://localhost:5432/mydb
  /mcp list
  /mcp remove github
"""

import os
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class MCPTransport(str, Enum):
    """MCP transport types"""
    STDIO = "stdio"         # Process with stdin/stdout
    HTTP = "http"           # HTTP/HTTPS endpoint
    WEBSOCKET = "websocket" # WebSocket connection


class MCPServerStatus(str, Enum):
    """MCP server connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class MCPTool:
    """An MCP tool provided by a server"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str


@dataclass
class MCPResource:
    """An MCP resource provided by a server"""
    uri: str
    name: str
    description: str
    mime_type: Optional[str]
    server_name: str


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server"""
    name: str
    transport: MCPTransport
    command: Optional[str] = None       # For stdio transport
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    url: Optional[str] = None           # For http/websocket transport
    enabled: bool = True
    auto_connect: bool = True


@dataclass
class MCPServerState:
    """Runtime state of an MCP server"""
    config: MCPServerConfig
    status: MCPServerStatus = MCPServerStatus.DISCONNECTED
    tools: List[MCPTool] = field(default_factory=list)
    resources: List[MCPResource] = field(default_factory=list)
    process: Optional[subprocess.Popen] = None
    error_message: Optional[str] = None
    connected_at: Optional[datetime] = None


class MCPClient:
    """
    MCP client for connecting to and interacting with MCP servers.

    Usage:
        client = MCPClient(console, config_dir)

        # Add a server
        await client.add_server("github", "npx", ["-y", "@modelcontextprotocol/server-github"])

        # Connect to all servers
        await client.connect_all()

        # List available tools
        tools = client.get_all_tools()

        # Call a tool
        result = await client.call_tool("github", "search_repos", {"query": "python"})

        # Read a resource
        content = await client.read_resource("github", "repo://owner/repo")
    """

    def __init__(
        self,
        console: Console,
        config_dir: Optional[Path] = None
    ):
        self.console = console
        self.config_dir = config_dir or (Path.home() / ".bharatbuild" / "mcp")
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self._servers: Dict[str, MCPServerState] = {}
        self._tool_callbacks: Dict[str, Callable] = {}

        # Load saved configurations
        self._load_configs()

    def _load_configs(self):
        """Load server configurations from disk"""
        config_file = self.config_dir / "servers.json"

        if config_file.exists():
            try:
                with open(config_file) as f:
                    data = json.load(f)

                for name, config_data in data.get("servers", {}).items():
                    config = MCPServerConfig(
                        name=name,
                        transport=MCPTransport(config_data.get("transport", "stdio")),
                        command=config_data.get("command"),
                        args=config_data.get("args", []),
                        env=config_data.get("env", {}),
                        url=config_data.get("url"),
                        enabled=config_data.get("enabled", True),
                        auto_connect=config_data.get("auto_connect", True)
                    )
                    self._servers[name] = MCPServerState(config=config)

            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load MCP configs: {e}[/yellow]")

    def _save_configs(self):
        """Save server configurations to disk"""
        config_file = self.config_dir / "servers.json"

        try:
            servers_data = {}
            for name, state in self._servers.items():
                config = state.config
                servers_data[name] = {
                    "transport": config.transport.value,
                    "command": config.command,
                    "args": config.args,
                    "env": config.env,
                    "url": config.url,
                    "enabled": config.enabled,
                    "auto_connect": config.auto_connect
                }

            with open(config_file, 'w') as f:
                json.dump({"servers": servers_data}, f, indent=2)

        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not save MCP configs: {e}[/yellow]")

    # ==================== Server Management ====================

    async def add_server(
        self,
        name: str,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        url: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        auto_connect: bool = True
    ) -> bool:
        """
        Add an MCP server.

        Examples:
            # Stdio server (process)
            await client.add_server("github", "npx", ["-y", "@modelcontextprotocol/server-github"])

            # HTTP server
            await client.add_server("custom", url="http://localhost:8080/mcp")
        """
        if name in self._servers:
            self.console.print(f"[yellow]Server '{name}' already exists[/yellow]")
            return False

        # Determine transport type
        if url:
            if url.startswith("ws://") or url.startswith("wss://"):
                transport = MCPTransport.WEBSOCKET
            else:
                transport = MCPTransport.HTTP
        else:
            transport = MCPTransport.STDIO

        config = MCPServerConfig(
            name=name,
            transport=transport,
            command=command,
            args=args or [],
            env=env or {},
            url=url,
            auto_connect=auto_connect
        )

        self._servers[name] = MCPServerState(config=config)
        self._save_configs()

        self.console.print(f"[green]✓ Added MCP server: {name}[/green]")

        if auto_connect:
            await self.connect_server(name)

        return True

    async def remove_server(self, name: str) -> bool:
        """Remove an MCP server"""
        if name not in self._servers:
            self.console.print(f"[yellow]Server '{name}' not found[/yellow]")
            return False

        # Disconnect first
        await self.disconnect_server(name)

        del self._servers[name]
        self._save_configs()

        self.console.print(f"[green]✓ Removed MCP server: {name}[/green]")
        return True

    async def connect_server(self, name: str) -> bool:
        """Connect to an MCP server"""
        if name not in self._servers:
            self.console.print(f"[red]Server '{name}' not found[/red]")
            return False

        state = self._servers[name]

        if state.status == MCPServerStatus.CONNECTED:
            self.console.print(f"[dim]Server '{name}' already connected[/dim]")
            return True

        state.status = MCPServerStatus.CONNECTING
        self.console.print(f"[dim]Connecting to {name}...[/dim]")

        try:
            if state.config.transport == MCPTransport.STDIO:
                await self._connect_stdio(state)
            elif state.config.transport == MCPTransport.HTTP:
                await self._connect_http(state)
            elif state.config.transport == MCPTransport.WEBSOCKET:
                await self._connect_websocket(state)

            state.status = MCPServerStatus.CONNECTED
            state.connected_at = datetime.now()
            self.console.print(f"[green]✓ Connected to {name}[/green]")

            # Fetch capabilities
            await self._fetch_capabilities(state)

            return True

        except Exception as e:
            state.status = MCPServerStatus.ERROR
            state.error_message = str(e)
            self.console.print(f"[red]✗ Failed to connect to {name}: {e}[/red]")
            return False

    async def disconnect_server(self, name: str) -> bool:
        """Disconnect from an MCP server"""
        if name not in self._servers:
            return False

        state = self._servers[name]

        if state.process:
            try:
                state.process.terminate()
                state.process.wait(timeout=5)
            except Exception:
                state.process.kill()
            state.process = None

        state.status = MCPServerStatus.DISCONNECTED
        state.tools = []
        state.resources = []

        self.console.print(f"[dim]Disconnected from {name}[/dim]")
        return True

    async def connect_all(self):
        """Connect to all enabled servers"""
        for name, state in self._servers.items():
            if state.config.enabled and state.config.auto_connect:
                await self.connect_server(name)

    async def disconnect_all(self):
        """Disconnect from all servers"""
        for name in list(self._servers.keys()):
            await self.disconnect_server(name)

    # ==================== Transport Implementations ====================

    async def _connect_stdio(self, state: MCPServerState):
        """Connect to stdio-based MCP server"""
        config = state.config

        if not config.command:
            raise ValueError("No command specified for stdio server")

        # Build environment
        env = os.environ.copy()
        env.update(config.env)

        # Start process
        cmd = [config.command] + config.args
        state.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True
        )

        # Wait briefly to check if process started
        await asyncio.sleep(0.5)

        if state.process.poll() is not None:
            stderr = state.process.stderr.read() if state.process.stderr else ""
            raise RuntimeError(f"Process exited immediately: {stderr}")

    async def _connect_http(self, state: MCPServerState):
        """Connect to HTTP-based MCP server"""
        import httpx

        if not state.config.url:
            raise ValueError("No URL specified for HTTP server")

        # Test connection
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(state.config.url)
            response.raise_for_status()

    async def _connect_websocket(self, state: MCPServerState):
        """Connect to WebSocket-based MCP server"""
        # WebSocket implementation would go here
        raise NotImplementedError("WebSocket transport not yet implemented")

    async def _fetch_capabilities(self, state: MCPServerState):
        """Fetch tools and resources from server"""
        # This would implement the MCP protocol to fetch capabilities
        # For now, we'll simulate it

        # In a real implementation, this would:
        # 1. Send "initialize" request
        # 2. Send "tools/list" request
        # 3. Send "resources/list" request
        # 4. Store the results

        pass

    # ==================== Tool & Resource Access ====================

    def get_all_tools(self) -> List[MCPTool]:
        """Get all available tools from connected servers"""
        tools = []
        for state in self._servers.values():
            if state.status == MCPServerStatus.CONNECTED:
                tools.extend(state.tools)
        return tools

    def get_all_resources(self) -> List[MCPResource]:
        """Get all available resources from connected servers"""
        resources = []
        for state in self._servers.values():
            if state.status == MCPServerStatus.CONNECTED:
                resources.extend(state.resources)
        return resources

    def get_server_tools(self, server_name: str) -> List[MCPTool]:
        """Get tools from a specific server"""
        if server_name in self._servers:
            return self._servers[server_name].tools
        return []

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call a tool on an MCP server.

        Returns the tool result.
        """
        if server_name not in self._servers:
            raise ValueError(f"Server '{server_name}' not found")

        state = self._servers[server_name]

        if state.status != MCPServerStatus.CONNECTED:
            raise RuntimeError(f"Server '{server_name}' not connected")

        # In a real implementation, this would send the tool call via the appropriate transport
        # and return the result

        self.console.print(f"[dim]Calling {server_name}.{tool_name}...[/dim]")

        # Placeholder result
        return {"status": "success", "result": None}

    async def read_resource(
        self,
        server_name: str,
        uri: str
    ) -> str:
        """
        Read a resource from an MCP server.

        Returns the resource content.
        """
        if server_name not in self._servers:
            raise ValueError(f"Server '{server_name}' not found")

        state = self._servers[server_name]

        if state.status != MCPServerStatus.CONNECTED:
            raise RuntimeError(f"Server '{server_name}' not connected")

        # In a real implementation, this would send the resource read request
        # via the appropriate transport and return the content

        self.console.print(f"[dim]Reading {uri} from {server_name}...[/dim]")

        # Placeholder result
        return ""

    # ==================== Display ====================

    def show_servers(self):
        """Show all configured servers"""
        if not self._servers:
            self.console.print("[dim]No MCP servers configured[/dim]")
            self.console.print("[dim]Use /mcp add <name> <command> to add a server[/dim]")
            return

        table = Table(title="MCP Servers", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="cyan")
        table.add_column("Transport")
        table.add_column("Status")
        table.add_column("Tools")
        table.add_column("Resources")

        for name, state in self._servers.items():
            # Status with color
            status_colors = {
                MCPServerStatus.CONNECTED: "green",
                MCPServerStatus.CONNECTING: "yellow",
                MCPServerStatus.DISCONNECTED: "dim",
                MCPServerStatus.ERROR: "red",
            }
            status_color = status_colors.get(state.status, "dim")
            status_text = f"[{status_color}]{state.status.value}[/{status_color}]"

            if state.status == MCPServerStatus.ERROR and state.error_message:
                status_text += f" [red dim]({state.error_message[:20]}...)[/red dim]"

            table.add_row(
                name,
                state.config.transport.value,
                status_text,
                str(len(state.tools)),
                str(len(state.resources))
            )

        self.console.print(table)

    def show_tools(self, server_name: Optional[str] = None):
        """Show available tools"""
        if server_name:
            tools = self.get_server_tools(server_name)
        else:
            tools = self.get_all_tools()

        if not tools:
            self.console.print("[dim]No tools available[/dim]")
            return

        table = Table(title="MCP Tools", show_header=True, header_style="bold cyan")
        table.add_column("Server", style="dim")
        table.add_column("Tool", style="cyan")
        table.add_column("Description")

        for tool in tools:
            table.add_row(
                tool.server_name,
                tool.name,
                tool.description[:50] + "..." if len(tool.description) > 50 else tool.description
            )

        self.console.print(table)

    def show_resources(self, server_name: Optional[str] = None):
        """Show available resources"""
        if server_name:
            if server_name in self._servers:
                resources = self._servers[server_name].resources
            else:
                resources = []
        else:
            resources = self.get_all_resources()

        if not resources:
            self.console.print("[dim]No resources available[/dim]")
            return

        table = Table(title="MCP Resources", show_header=True, header_style="bold cyan")
        table.add_column("Server", style="dim")
        table.add_column("URI", style="cyan")
        table.add_column("Name")
        table.add_column("Type", style="dim")

        for resource in resources:
            table.add_row(
                resource.server_name,
                resource.uri[:40] + "..." if len(resource.uri) > 40 else resource.uri,
                resource.name,
                resource.mime_type or "-"
            )

        self.console.print(table)


# ==================== Built-in Server Presets ====================

MCP_SERVER_PRESETS = {
    "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": ""},
        "description": "GitHub API access"
    },
    "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem"],
        "description": "Local filesystem access"
    },
    "postgres": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres"],
        "env": {"POSTGRES_CONNECTION_STRING": ""},
        "description": "PostgreSQL database access"
    },
    "sqlite": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sqlite"],
        "description": "SQLite database access"
    },
    "memory": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "description": "In-memory key-value store"
    },
    "fetch": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-fetch"],
        "description": "HTTP fetch capabilities"
    },
    "brave-search": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-brave-search"],
        "env": {"BRAVE_API_KEY": ""},
        "description": "Brave Search API"
    },
    "puppeteer": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        "description": "Browser automation"
    },
}


def get_mcp_preset(name: str) -> Optional[Dict[str, Any]]:
    """Get a preset MCP server configuration"""
    return MCP_SERVER_PRESETS.get(name)


def list_mcp_presets() -> List[str]:
    """List available MCP server presets"""
    return list(MCP_SERVER_PRESETS.keys())
