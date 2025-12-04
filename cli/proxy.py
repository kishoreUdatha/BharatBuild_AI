"""
BharatBuild CLI Proxy Support

Configure proxy settings for API requests:
  /proxy set <url>    Set proxy URL
  /proxy clear        Clear proxy settings
  /proxy test         Test proxy connection
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from urllib.parse import urlparse

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm


@dataclass
class ProxyConfig:
    """Proxy configuration"""
    http_proxy: str = ""
    https_proxy: str = ""
    no_proxy: str = ""  # Comma-separated list of hosts to bypass
    proxy_auth_user: str = ""
    proxy_auth_pass: str = ""
    verify_ssl: bool = True


class ProxyManager:
    """
    Manages proxy configuration for API requests.

    Supports:
    - HTTP/HTTPS proxies
    - SOCKS proxies (if PySocks installed)
    - Proxy authentication
    - No-proxy lists
    - SSL verification settings

    Usage:
        manager = ProxyManager(console, config_dir)

        # Set proxy
        manager.set_proxy("http://proxy.company.com:8080")

        # Get proxy config for httpx
        proxies = manager.get_httpx_config()

        # Test connection
        manager.test_proxy()
    """

    # Environment variable names
    ENV_VARS = [
        "HTTP_PROXY", "http_proxy",
        "HTTPS_PROXY", "https_proxy",
        "NO_PROXY", "no_proxy",
        "ALL_PROXY", "all_proxy",
    ]

    def __init__(self, console: Console, config_dir: Path = None):
        self.console = console
        self.config_dir = config_dir or Path.home() / ".bharatbuild"
        self.config_file = self.config_dir / "proxy.json"

        # Load config
        self.config = self._load_config()

    def _load_config(self) -> ProxyConfig:
        """Load proxy config from file or environment"""
        config = ProxyConfig()

        # First check environment variables
        config.http_proxy = os.environ.get("HTTP_PROXY", os.environ.get("http_proxy", ""))
        config.https_proxy = os.environ.get("HTTPS_PROXY", os.environ.get("https_proxy", ""))
        config.no_proxy = os.environ.get("NO_PROXY", os.environ.get("no_proxy", ""))

        # Then load from config file (overrides env)
        if self.config_file.exists():
            try:
                import json
                with open(self.config_file) as f:
                    data = json.load(f)

                config.http_proxy = data.get("http_proxy", config.http_proxy)
                config.https_proxy = data.get("https_proxy", config.https_proxy)
                config.no_proxy = data.get("no_proxy", config.no_proxy)
                config.proxy_auth_user = data.get("proxy_auth_user", "")
                config.proxy_auth_pass = data.get("proxy_auth_pass", "")
                config.verify_ssl = data.get("verify_ssl", True)

            except Exception:
                pass

        return config

    def _save_config(self):
        """Save proxy config to file"""
        import json

        self.config_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "http_proxy": self.config.http_proxy,
            "https_proxy": self.config.https_proxy,
            "no_proxy": self.config.no_proxy,
            "proxy_auth_user": self.config.proxy_auth_user,
            "proxy_auth_pass": self.config.proxy_auth_pass,
            "verify_ssl": self.config.verify_ssl,
        }

        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Set restrictive permissions (may contain credentials)
        try:
            os.chmod(self.config_file, 0o600)
        except Exception:
            pass

    # ==================== Configuration ====================

    def set_proxy(
        self,
        proxy_url: str,
        https_proxy: str = None,
        no_proxy: str = None
    ) -> bool:
        """Set proxy URL"""
        # Validate URL
        if not self._validate_proxy_url(proxy_url):
            self.console.print("[red]Invalid proxy URL format[/red]")
            self.console.print("[dim]Expected format: http://host:port or http://user:pass@host:port[/dim]")
            return False

        self.config.http_proxy = proxy_url
        self.config.https_proxy = https_proxy or proxy_url

        if no_proxy:
            self.config.no_proxy = no_proxy

        # Extract auth from URL if present
        parsed = urlparse(proxy_url)
        if parsed.username:
            self.config.proxy_auth_user = parsed.username
        if parsed.password:
            self.config.proxy_auth_pass = parsed.password

        self._save_config()
        self._apply_to_environment()

        self.console.print(f"[green]✓ Proxy configured: {self._mask_proxy_url(proxy_url)}[/green]")
        return True

    def set_proxy_auth(self, username: str, password: str):
        """Set proxy authentication credentials"""
        self.config.proxy_auth_user = username
        self.config.proxy_auth_pass = password
        self._save_config()

        self.console.print("[green]✓ Proxy authentication configured[/green]")

    def set_no_proxy(self, hosts: str):
        """Set hosts to bypass proxy"""
        self.config.no_proxy = hosts
        self._save_config()
        self._apply_to_environment()

        self.console.print(f"[green]✓ No-proxy list updated: {hosts}[/green]")

    def set_ssl_verify(self, verify: bool):
        """Enable/disable SSL verification"""
        self.config.verify_ssl = verify
        self._save_config()

        status = "enabled" if verify else "disabled"
        self.console.print(f"[green]✓ SSL verification {status}[/green]")

        if not verify:
            self.console.print("[yellow]Warning: Disabling SSL verification is not recommended[/yellow]")

    def clear_proxy(self):
        """Clear proxy settings"""
        self.config = ProxyConfig()
        self._save_config()
        self._clear_environment()

        self.console.print("[green]✓ Proxy settings cleared[/green]")

    def _validate_proxy_url(self, url: str) -> bool:
        """Validate proxy URL format"""
        if not url:
            return False

        # Basic URL validation
        pattern = r'^(https?|socks[45]?)://([^:]+:[^@]+@)?[\w.-]+(:\d+)?/?$'
        return bool(re.match(pattern, url, re.IGNORECASE))

    def _mask_proxy_url(self, url: str) -> str:
        """Mask credentials in proxy URL"""
        parsed = urlparse(url)
        if parsed.password:
            return url.replace(parsed.password, "****")
        return url

    def _apply_to_environment(self):
        """Apply proxy settings to environment variables"""
        if self.config.http_proxy:
            os.environ["HTTP_PROXY"] = self.config.http_proxy
            os.environ["http_proxy"] = self.config.http_proxy

        if self.config.https_proxy:
            os.environ["HTTPS_PROXY"] = self.config.https_proxy
            os.environ["https_proxy"] = self.config.https_proxy

        if self.config.no_proxy:
            os.environ["NO_PROXY"] = self.config.no_proxy
            os.environ["no_proxy"] = self.config.no_proxy

    def _clear_environment(self):
        """Clear proxy environment variables"""
        for var in self.ENV_VARS:
            if var in os.environ:
                del os.environ[var]

    # ==================== Get Proxy Config ====================

    def get_httpx_config(self) -> Dict[str, Any]:
        """Get proxy configuration for httpx client"""
        config = {}

        if self.config.http_proxy or self.config.https_proxy:
            proxies = {}

            if self.config.http_proxy:
                proxies["http://"] = self.config.http_proxy

            if self.config.https_proxy:
                proxies["https://"] = self.config.https_proxy

            config["proxies"] = proxies

        config["verify"] = self.config.verify_ssl

        return config

    def get_requests_config(self) -> Dict[str, Any]:
        """Get proxy configuration for requests library"""
        config = {
            "proxies": {},
            "verify": self.config.verify_ssl
        }

        if self.config.http_proxy:
            config["proxies"]["http"] = self.config.http_proxy

        if self.config.https_proxy:
            config["proxies"]["https"] = self.config.https_proxy

        return config

    def is_configured(self) -> bool:
        """Check if proxy is configured"""
        return bool(self.config.http_proxy or self.config.https_proxy)

    def should_bypass(self, host: str) -> bool:
        """Check if host should bypass proxy"""
        if not self.config.no_proxy:
            return False

        no_proxy_list = [h.strip() for h in self.config.no_proxy.split(",")]

        for pattern in no_proxy_list:
            if pattern == "*":
                return True
            if host == pattern:
                return True
            if pattern.startswith(".") and host.endswith(pattern):
                return True
            if host.endswith("." + pattern):
                return True

        return False

    # ==================== Test Proxy ====================

    def test_proxy(self, test_url: str = "https://api.anthropic.com") -> bool:
        """Test proxy connection"""
        if not self.is_configured():
            self.console.print("[yellow]No proxy configured[/yellow]")
            return True

        self.console.print(f"[cyan]Testing proxy connection to {test_url}...[/cyan]")

        try:
            import httpx

            config = self.get_httpx_config()

            with httpx.Client(**config, timeout=10) as client:
                response = client.head(test_url)

                if response.status_code < 500:
                    self.console.print(f"[green]✓ Proxy connection successful (HTTP {response.status_code})[/green]")
                    return True
                else:
                    self.console.print(f"[red]✗ Proxy connection failed (HTTP {response.status_code})[/red]")
                    return False

        except Exception as e:
            self.console.print(f"[red]✗ Proxy connection failed: {e}[/red]")
            return False

    # ==================== Interactive ====================

    def configure_interactive(self):
        """Configure proxy interactively"""
        self.console.print("\n[bold cyan]Proxy Configuration[/bold cyan]\n")

        # Current status
        if self.is_configured():
            self.console.print(f"Current proxy: {self._mask_proxy_url(self.config.https_proxy or self.config.http_proxy)}")
            if not Confirm.ask("Reconfigure proxy?"):
                return

        # Get proxy URL
        proxy_url = Prompt.ask("Proxy URL (e.g., http://proxy:8080)", default="")

        if not proxy_url:
            if Confirm.ask("Clear proxy settings?"):
                self.clear_proxy()
            return

        # Validate
        if not self._validate_proxy_url(proxy_url):
            self.console.print("[red]Invalid proxy URL[/red]")
            return

        # Authentication
        needs_auth = Confirm.ask("Does proxy require authentication?", default=False)

        if needs_auth:
            username = Prompt.ask("Username")
            password = Prompt.ask("Password", password=True)

            # Add auth to URL
            parsed = urlparse(proxy_url)
            proxy_url = f"{parsed.scheme}://{username}:{password}@{parsed.netloc}"

        # No-proxy list
        no_proxy = Prompt.ask(
            "Hosts to bypass proxy (comma-separated)",
            default="localhost,127.0.0.1"
        )

        # SSL verification
        verify_ssl = Confirm.ask("Verify SSL certificates?", default=True)

        # Apply settings
        self.set_proxy(proxy_url, no_proxy=no_proxy)
        self.set_ssl_verify(verify_ssl)

        # Test
        if Confirm.ask("Test proxy connection?", default=True):
            self.test_proxy()

    # ==================== Display ====================

    def show_status(self):
        """Show proxy status"""
        content_lines = []

        if self.is_configured():
            content_lines.append(f"[bold]Status:[/bold] [green]Configured[/green]")
            content_lines.append("")

            if self.config.http_proxy:
                content_lines.append(f"[bold]HTTP Proxy:[/bold] {self._mask_proxy_url(self.config.http_proxy)}")

            if self.config.https_proxy:
                content_lines.append(f"[bold]HTTPS Proxy:[/bold] {self._mask_proxy_url(self.config.https_proxy)}")

            if self.config.no_proxy:
                content_lines.append(f"[bold]No Proxy:[/bold] {self.config.no_proxy}")

            if self.config.proxy_auth_user:
                content_lines.append(f"[bold]Auth User:[/bold] {self.config.proxy_auth_user}")

            content_lines.append(f"[bold]SSL Verify:[/bold] {'Yes' if self.config.verify_ssl else 'No'}")

        else:
            content_lines.append(f"[bold]Status:[/bold] [dim]Not configured[/dim]")
            content_lines.append("")
            content_lines.append("[dim]Use /proxy set <url> to configure[/dim]")

        # Check environment
        content_lines.append("")
        content_lines.append("[bold]Environment:[/bold]")

        for var in ["HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"]:
            value = os.environ.get(var, "")
            if value:
                content_lines.append(f"  {var}: {self._mask_proxy_url(value)}")
            else:
                content_lines.append(f"  {var}: [dim]not set[/dim]")

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title="[bold cyan]Proxy Settings[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

    def show_help(self):
        """Show proxy help"""
        help_text = """
[bold cyan]Proxy Commands[/bold cyan]

Configure proxy settings for API requests.

[bold]Commands:[/bold]
  [green]/proxy[/green]                Show proxy status
  [green]/proxy set <url>[/green]      Set proxy URL
  [green]/proxy auth[/green]           Set proxy authentication
  [green]/proxy no-proxy <h>[/green]   Set hosts to bypass
  [green]/proxy ssl on/off[/green]     Toggle SSL verification
  [green]/proxy test[/green]           Test proxy connection
  [green]/proxy clear[/green]          Clear proxy settings
  [green]/proxy config[/green]         Interactive configuration

[bold]URL Formats:[/bold]
  http://proxy.example.com:8080
  http://user:pass@proxy.example.com:8080
  socks5://proxy.example.com:1080

[bold]Environment Variables:[/bold]
  HTTP_PROXY, HTTPS_PROXY, NO_PROXY
  These are set automatically when configuring.

[bold]Examples:[/bold]
  /proxy set http://proxy.company.com:8080
  /proxy no-proxy localhost,127.0.0.1,.internal.com
  /proxy test
"""
        self.console.print(help_text)
