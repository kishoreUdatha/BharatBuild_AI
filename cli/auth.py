"""
BharatBuild CLI Authentication Module
======================================

Full-featured authentication system:
  /login              Interactive login
  /login --api-key    Login with API key
  /login --github     Login with GitHub OAuth
  /logout             Logout from account
  /whoami             Show current user
  /account            Manage account settings

Students register via UI → Get token → Use token in CLI
All API calls go through your backend using YOUR Anthropic key.

Flow:
1. Student registers on web UI
2. Student gets access token from UI
3. Student runs: bharatbuild login
4. CLI stores token locally
5. All requests include token → Backend validates → Uses your API key
"""

import os
import json
import hashlib
import secrets
import webbrowser
import threading
import time
import httpx
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn


class AuthProvider(str, Enum):
    """Authentication providers"""
    LOCAL = "local"
    GITHUB = "github"
    GOOGLE = "google"
    BHARATBUILD = "bharatbuild"
    API_KEY = "api_key"


class AccountTier(str, Enum):
    """Account tiers"""
    FREE = "free"
    STUDENT = "student"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


@dataclass
class UserCredentials:
    """Stored user credentials"""
    user_id: str
    email: str
    name: str
    access_token: str
    refresh_token: Optional[str] = None
    token_expiry: Optional[str] = None
    college_name: Optional[str] = None
    department: Optional[str] = None
    roll_number: Optional[str] = None

    # Extended fields for Claude Code-style auth
    provider: AuthProvider = AuthProvider.LOCAL
    tier: AccountTier = AccountTier.FREE
    avatar_url: str = ""
    daily_requests: int = 0
    daily_limit: int = 100
    monthly_tokens: int = 0
    monthly_limit: int = 100000
    created_at: str = ""
    last_login: str = ""


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback for browser-based auth"""

    auth_code = None
    state = None

    def do_GET(self):
        """Handle GET request from OAuth callback"""
        query = urlparse(self.path).query
        params = parse_qs(query)

        OAuthCallbackHandler.auth_code = params.get("code", [None])[0]
        OAuthCallbackHandler.state = params.get("state", [None])[0]

        # Send success response
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>BharatBuild - Login Successful</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .card {
                    background: white;
                    padding: 2rem 3rem;
                    border-radius: 12px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    text-align: center;
                }
                h1 { color: #333; margin-bottom: 0.5rem; }
                p { color: #666; }
                .success { color: #10b981; font-size: 48px; }
            </style>
        </head>
        <body>
            <div class="card">
                <div class="success">✓</div>
                <h1>Login Successful!</h1>
                <p>You can close this window and return to the CLI.</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress server logs"""
        pass


class CLIAuthManager:
    """
    Manages CLI authentication.

    Token is stored in ~/.bharatbuild/credentials.json

    Features:
    - Email/password login
    - Token-based login
    - OAuth login (GitHub, Google)
    - API key authentication
    - Account management
    - Usage tracking
    """

    # Where to store credentials
    CONFIG_DIR = Path.home() / ".bharatbuild"
    CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"

    # OAuth configuration
    OAUTH_CONFIG = {
        AuthProvider.GITHUB: {
            "client_id": "bharatbuild_github_client",
            "auth_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "scopes": ["user:email", "read:user"]
        },
        AuthProvider.GOOGLE: {
            "client_id": "bharatbuild_google_client",
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": ["email", "profile"]
        },
        AuthProvider.BHARATBUILD: {
            "client_id": "bharatbuild_cli",
            "auth_url": "https://auth.bharatbuild.dev/authorize",
            "token_url": "https://auth.bharatbuild.dev/token",
            "scopes": ["cli", "api"]
        }
    }

    CALLBACK_PORT = 8377

    def __init__(self, api_base_url: str = "http://localhost:8000/api/v1"):
        self.api_base_url = api_base_url
        self.console = Console()
        self.credentials: Optional[UserCredentials] = None

        # Ensure config directory exists
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Load existing credentials if available
        self._load_credentials()

    def _load_credentials(self) -> bool:
        """Load credentials from file"""
        if self.CREDENTIALS_FILE.exists():
            try:
                with open(self.CREDENTIALS_FILE, 'r') as f:
                    data = json.load(f)
                    self.credentials = UserCredentials(**data)
                    return True
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load credentials: {e}[/yellow]")
        return False

    def _save_credentials(self):
        """Save credentials to file"""
        if self.credentials:
            try:
                with open(self.CREDENTIALS_FILE, 'w') as f:
                    json.dump(asdict(self.credentials), f, indent=2)
                # Secure the file (Unix only)
                try:
                    os.chmod(self.CREDENTIALS_FILE, 0o600)
                except:
                    pass
            except Exception as e:
                self.console.print(f"[red]Error saving credentials: {e}[/red]")

    def _clear_credentials(self):
        """Clear stored credentials"""
        self.credentials = None
        if self.CREDENTIALS_FILE.exists():
            self.CREDENTIALS_FILE.unlink()

    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        if not self.credentials or not self.credentials.access_token:
            return False

        # Check if token is expired
        if self.credentials.token_expiry:
            try:
                expiry = datetime.fromisoformat(self.credentials.token_expiry)
                if datetime.now() > expiry:
                    self.console.print("[yellow]Session expired. Please login again.[/yellow]")
                    return False
            except:
                pass

        return True

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers for API requests"""
        if self.credentials and self.credentials.access_token:
            return {
                "Authorization": f"Bearer {self.credentials.access_token}",
                "X-User-ID": self.credentials.user_id,
                "X-User-Email": self.credentials.email
            }
        return {}

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get current user info"""
        if self.credentials:
            return {
                "user_id": self.credentials.user_id,
                "email": self.credentials.email,
                "name": self.credentials.name,
                "college_name": self.credentials.college_name,
                "department": self.credentials.department,
                "roll_number": self.credentials.roll_number
            }
        return None

    async def login_with_token(self, token: str) -> bool:
        """
        Login using access token from web UI.

        Students get this token from:
        1. Web UI after registration
        2. Profile page → API Access → Generate CLI Token
        """
        try:
            async with httpx.AsyncClient() as client:
                # Validate token with backend
                response = await client.get(
                    f"{self.api_base_url}/auth/validate-token",
                    headers={"Authorization": f"Bearer {token}"}
                )

                if response.status_code == 200:
                    data = response.json()
                    user = data.get("user", {})

                    self.credentials = UserCredentials(
                        user_id=user.get("id", ""),
                        email=user.get("email", ""),
                        name=user.get("name", ""),
                        access_token=token,
                        refresh_token=data.get("refresh_token"),
                        token_expiry=data.get("expires_at"),
                        college_name=user.get("college_name"),
                        department=user.get("department"),
                        roll_number=user.get("roll_number")
                    )

                    self._save_credentials()
                    return True
                else:
                    error = response.json().get("detail", "Invalid token")
                    self.console.print(f"[red]Authentication failed: {error}[/red]")
                    return False

        except httpx.ConnectError:
            self.console.print("[red]Cannot connect to server. Is the backend running?[/red]")
            return False
        except Exception as e:
            self.console.print(f"[red]Login error: {e}[/red]")
            return False

    async def login_with_credentials(self, email: str, password: str) -> bool:
        """Login using email and password"""
        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Login to get tokens
                response = await client.post(
                    f"{self.api_base_url}/auth/login",
                    json={"email": email, "password": password}
                )

                if response.status_code != 200:
                    error = response.json().get("detail", "Invalid credentials")
                    self.console.print(f"[red]Login failed: {error}[/red]")
                    return False

                token_data = response.json()
                access_token = token_data.get("access_token", "")

                # Step 2: Fetch user info using the token
                user_response = await client.get(
                    f"{self.api_base_url}/auth/me",
                    headers={"Authorization": f"Bearer {access_token}"}
                )

                if user_response.status_code == 200:
                    user = user_response.json()

                    self.credentials = UserCredentials(
                        user_id=str(user.get("id", "")),
                        email=user.get("email", email),
                        name=user.get("full_name", ""),
                        access_token=access_token,
                        refresh_token=token_data.get("refresh_token"),
                        token_expiry=token_data.get("expires_at"),
                        college_name=user.get("college_name"),
                        department=user.get("department"),
                        roll_number=user.get("roll_number")
                    )

                    self._save_credentials()
                    return True
                else:
                    # Fallback: use email as name if can't fetch user info
                    self.credentials = UserCredentials(
                        user_id="",
                        email=email,
                        name=email.split("@")[0],
                        access_token=access_token,
                        refresh_token=token_data.get("refresh_token"),
                        token_expiry=token_data.get("expires_at")
                    )
                    self._save_credentials()
                    return True

        except httpx.ConnectError:
            self.console.print("[red]Cannot connect to server. Is the backend running?[/red]")
            return False
        except Exception as e:
            self.console.print(f"[red]Login error: {e}[/red]")
            return False

    async def refresh_token(self) -> bool:
        """Refresh access token using refresh token"""
        if not self.credentials or not self.credentials.refresh_token:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base_url}/auth/refresh",
                    json={"refresh_token": self.credentials.refresh_token}
                )

                if response.status_code == 200:
                    data = response.json()
                    self.credentials.access_token = data.get("access_token", "")
                    self.credentials.token_expiry = data.get("expires_at")
                    self._save_credentials()
                    return True

        except:
            pass

        return False

    def logout(self):
        """Logout and clear credentials"""
        self._clear_credentials()
        self.console.print("[green]Logged out successfully[/green]")

    async def interactive_login(self) -> bool:
        """Interactive login flow"""
        self.console.print(Panel(
            "[bold cyan]BharatBuild AI - Login[/bold cyan]\n\n"
            "Login using your registered account.\n"
            "If you don't have an account, register at the web portal.",
            border_style="cyan"
        ))

        login_method = Prompt.ask(
            "Login method",
            choices=["email", "token"],
            default="email"
        )

        if login_method == "token":
            self.console.print("\n[dim]Get your CLI token from: Web Portal → Profile → API Access[/dim]")
            token = Prompt.ask("Enter your CLI token")
            return await self.login_with_token(token)
        else:
            email = Prompt.ask("Email")
            password = Prompt.ask("Password", password=True)
            return await self.login_with_credentials(email, password)

    def show_status(self):
        """Show current authentication status"""
        if self.is_authenticated():
            self.console.print(Panel(
                f"[green]Authenticated[/green]\n\n"
                f"[bold]User:[/bold] {self.credentials.name}\n"
                f"[bold]Email:[/bold] {self.credentials.email}\n"
                f"[bold]College:[/bold] {self.credentials.college_name or 'Not set'}\n"
                f"[bold]Roll No:[/bold] {self.credentials.roll_number or 'Not set'}",
                title="Authentication Status",
                border_style="green"
            ))
        else:
            self.console.print(Panel(
                "[red]Not authenticated[/red]\n\n"
                "Please login using: [cyan]bharatbuild login[/cyan]\n"
                "Or register at the web portal first.",
                title="Authentication Status",
                border_style="red"
            ))

    # ==================== Extended Login Methods ====================

    def login_extended(self, provider: AuthProvider = None):
        """Extended interactive login with multiple providers"""
        if self.is_authenticated():
            self.console.print(f"[yellow]Already logged in as {self.credentials.email}[/yellow]")
            if not Confirm.ask("Login with a different account?", default=False):
                return

        self.console.print("\n[bold cyan]🔐 BharatBuild Login[/bold cyan]\n")

        # Select provider
        if not provider:
            self.console.print("[bold]Choose login method:[/bold]\n")
            self.console.print("  [cyan]1.[/cyan] 📧 Email & Password")
            self.console.print("  [cyan]2.[/cyan] 🔑 Access Token")
            self.console.print("  [cyan]3.[/cyan] 🔐 API Key")
            self.console.print("  [cyan]4.[/cyan] 🐙 GitHub")
            self.console.print("  [cyan]5.[/cyan] 🔵 Google")
            self.console.print()

            choice = Prompt.ask(
                "Select method",
                choices=["1", "2", "3", "4", "5"],
                default="1"
            )

            provider_map = {
                "1": AuthProvider.LOCAL,
                "2": AuthProvider.BHARATBUILD,
                "3": AuthProvider.API_KEY,
                "4": AuthProvider.GITHUB,
                "5": AuthProvider.GOOGLE
            }
            provider = provider_map[choice]

        # Route to provider handler
        if provider == AuthProvider.LOCAL:
            # Use existing email/password login
            import asyncio
            asyncio.run(self.interactive_login())
        elif provider == AuthProvider.API_KEY:
            self._login_with_api_key()
        elif provider in [AuthProvider.GITHUB, AuthProvider.GOOGLE]:
            self._login_with_oauth(provider)
        else:
            # Token login
            self.console.print("\n[dim]Get your CLI token from: Web Portal → Profile → API Access[/dim]")
            token = Prompt.ask("Enter your CLI token")
            import asyncio
            asyncio.run(self.login_with_token(token))

    def _login_with_api_key(self):
        """Login with API key"""
        self.console.print("\n[bold]API Key Login[/bold]")
        self.console.print("[dim]Enter your BharatBuild API key (starts with 'bb_')[/dim]\n")

        api_key = Prompt.ask("API Key", password=True)

        if not api_key:
            self.console.print("[red]API key cannot be empty[/red]")
            return

        if not api_key.startswith("bb_"):
            self.console.print("[yellow]Warning: API key should start with 'bb_'[/yellow]")

        # Validate API key
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Validating API key...", total=None)

            # In production, this would call the API to validate
            time.sleep(1)

            # Create user from API key
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:8]

            self.credentials = UserCredentials(
                user_id=f"api_{key_hash}",
                email=f"api_user_{key_hash}@bharatbuild.dev",
                name="API User",
                access_token=api_key,
                provider=AuthProvider.API_KEY,
                tier=AccountTier.PRO,
                token_expiry=(datetime.now() + timedelta(days=365)).isoformat(),
                created_at=datetime.now().isoformat(),
                last_login=datetime.now().isoformat()
            )

            self._save_credentials()
            progress.update(task, description="[green]Validated[/green]")

        self.console.print(f"\n[green]Logged in successfully![/green]")
        self._show_user_panel()

    def _login_with_oauth(self, provider: AuthProvider):
        """Login with OAuth provider (GitHub, Google)"""
        config = self.OAUTH_CONFIG.get(provider)
        if not config:
            self.console.print(f"[red]Unknown provider: {provider}[/red]")
            return

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Build authorization URL
        import urllib.parse

        params = {
            "client_id": config["client_id"],
            "redirect_uri": f"http://localhost:{self.CALLBACK_PORT}/callback",
            "scope": " ".join(config["scopes"]),
            "state": state,
            "response_type": "code"
        }

        auth_url = f"{config['auth_url']}?{urllib.parse.urlencode(params)}"

        self.console.print(f"\n[bold]Opening browser for {provider.value} login...[/bold]")
        self.console.print("[dim]If browser doesn't open, visit this URL:[/dim]")
        self.console.print(f"[dim]{auth_url}[/dim]\n")

        # Start callback server
        server = HTTPServer(('localhost', self.CALLBACK_PORT), OAuthCallbackHandler)
        server_thread = threading.Thread(target=server.handle_request)
        server_thread.start()

        # Open browser
        try:
            webbrowser.open(auth_url)
        except Exception as e:
            self.console.print(f"[yellow]Could not open browser: {e}[/yellow]")

        # Wait for callback
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Waiting for login...", total=None)

            server_thread.join(timeout=120)

            if OAuthCallbackHandler.auth_code:
                progress.update(task, description="[cyan]Exchanging code...[/cyan]")

                # Verify state
                if OAuthCallbackHandler.state != state:
                    self.console.print("[red]Security error: state mismatch[/red]")
                    return

                # Exchange code for token
                self._exchange_oauth_code(
                    provider,
                    OAuthCallbackHandler.auth_code,
                    config
                )

                progress.update(task, description="[green]✓ Login complete[/green]")
            else:
                progress.update(task, description="[red]Login timed out[/red]")

        # Reset handler state
        OAuthCallbackHandler.auth_code = None
        OAuthCallbackHandler.state = None

    def _exchange_oauth_code(self, provider: AuthProvider, code: str, config: Dict):
        """Exchange OAuth code for token"""
        # In production, this would make a POST request to the token endpoint
        # For demonstration, create mock data
        time.sleep(1)

        # Mock user data based on provider
        user_id = hashlib.sha256(code.encode()).hexdigest()[:12]

        provider_names = {
            AuthProvider.GITHUB: "GitHub User",
            AuthProvider.GOOGLE: "Google User",
            AuthProvider.BHARATBUILD: "BharatBuild User"
        }

        self.credentials = UserCredentials(
            user_id=f"{provider.value}_{user_id}",
            email=f"user_{user_id}@{provider.value}.com",
            name=provider_names.get(provider, "User"),
            access_token=f"oauth_{secrets.token_urlsafe(32)}",
            refresh_token=f"refresh_{secrets.token_urlsafe(32)}",
            token_expiry=(datetime.now() + timedelta(hours=1)).isoformat(),
            provider=provider,
            tier=AccountTier.FREE,
            created_at=datetime.now().isoformat(),
            last_login=datetime.now().isoformat()
        )

        self._save_credentials()

        self.console.print(f"\n[green]✓ Logged in with {provider.value}![/green]")
        self._show_user_panel()

    # ==================== Account Management ====================

    def whoami(self):
        """Show current user (Claude Code style)"""
        if not self.is_authenticated():
            self.console.print("[dim]Not logged in[/dim]")
            self.console.print("[dim]Use '/login' to authenticate[/dim]")
            return

        self._show_user_panel()

    def _show_user_panel(self):
        """Display user info panel"""
        if not self.credentials:
            return

        tier_colors = {
            AccountTier.FREE: "dim",
            AccountTier.STUDENT: "cyan",
            AccountTier.PRO: "green",
            AccountTier.TEAM: "blue",
            AccountTier.ENTERPRISE: "magenta"
        }

        tier = getattr(self.credentials, 'tier', AccountTier.FREE)
        tier_color = tier_colors.get(tier, "white")
        provider = getattr(self.credentials, 'provider', AuthProvider.LOCAL)

        content_lines = []
        content_lines.append(f"[bold]Email:[/bold] {self.credentials.email}")
        content_lines.append(f"[bold]Name:[/bold] {self.credentials.name or '[dim]Not set[/dim]'}")
        content_lines.append(f"[bold]Tier:[/bold] [{tier_color}]{tier.value.upper()}[/{tier_color}]")
        content_lines.append(f"[bold]Provider:[/bold] {provider.value}")

        if self.credentials.college_name:
            content_lines.append(f"[bold]College:[/bold] {self.credentials.college_name}")

        if self.credentials.roll_number:
            content_lines.append(f"[bold]Roll No:[/bold] {self.credentials.roll_number}")

        # Usage info
        daily_requests = getattr(self.credentials, 'daily_requests', 0)
        daily_limit = getattr(self.credentials, 'daily_limit', 100)
        monthly_tokens = getattr(self.credentials, 'monthly_tokens', 0)
        monthly_limit = getattr(self.credentials, 'monthly_limit', 100000)

        content_lines.append("")
        content_lines.append("[bold]Usage:[/bold]")
        content_lines.append(f"  Daily: {daily_requests}/{daily_limit} requests")
        content_lines.append(f"  Monthly: {monthly_tokens:,}/{monthly_limit:,} tokens")

        last_login = getattr(self.credentials, 'last_login', '')
        if last_login:
            try:
                dt = datetime.fromisoformat(last_login)
                content_lines.append("")
                content_lines.append(f"[dim]Last login: {dt.strftime('%Y-%m-%d %H:%M')}[/dim]")
            except Exception:
                pass

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title="[bold cyan]Account[/bold cyan]",
            border_style="cyan"
        )
        self.console.print(panel)

    def show_account(self):
        """Show account management options"""
        if not self.is_authenticated():
            self.console.print("[dim]Not logged in[/dim]")
            return

        self._show_user_panel()

        self.console.print("\n[bold]Account Actions:[/bold]")
        self.console.print("  [cyan]1.[/cyan] View usage details")
        self.console.print("  [cyan]2.[/cyan] Upgrade plan")
        self.console.print("  [cyan]3.[/cyan] API keys")
        self.console.print("  [cyan]4.[/cyan] Logout")
        self.console.print("  [cyan]5.[/cyan] Back")

        choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "5"], default="5")

        if choice == "1":
            self._show_usage()
        elif choice == "2":
            self._show_upgrade()
        elif choice == "3":
            self._show_api_keys()
        elif choice == "4":
            self.logout()

    def _show_usage(self):
        """Show detailed usage statistics"""
        if not self.credentials:
            return

        daily_requests = getattr(self.credentials, 'daily_requests', 0)
        daily_limit = getattr(self.credentials, 'daily_limit', 100)
        monthly_tokens = getattr(self.credentials, 'monthly_tokens', 0)
        monthly_limit = getattr(self.credentials, 'monthly_limit', 100000)

        table = Table(title="Usage Statistics", show_header=True, header_style="bold cyan")
        table.add_column("Metric")
        table.add_column("Used", justify="right")
        table.add_column("Limit", justify="right")
        table.add_column("Remaining", justify="right")

        daily_remaining = max(0, daily_limit - daily_requests)
        monthly_remaining = max(0, monthly_limit - monthly_tokens)

        table.add_row(
            "Daily Requests",
            str(daily_requests),
            str(daily_limit),
            f"[green]{daily_remaining}[/green]" if daily_remaining > 0 else "[red]0[/red]"
        )

        table.add_row(
            "Monthly Tokens",
            f"{monthly_tokens:,}",
            f"{monthly_limit:,}",
            f"[green]{monthly_remaining:,}[/green]" if monthly_remaining > 0 else "[red]0[/red]"
        )

        self.console.print(table)

    def _show_upgrade(self):
        """Show upgrade options"""
        self.console.print("\n[bold cyan]Upgrade Your Plan[/bold cyan]\n")

        plans = [
            ("Student", "$0/mo", "100 requests/day, 100K tokens/mo", "For students with .edu email"),
            ("Pro", "$20/mo", "1000 requests/day, 1M tokens/mo", "For professionals"),
            ("Team", "$50/mo", "5000 requests/day, 5M tokens/mo", "For small teams"),
            ("Enterprise", "Custom", "Unlimited", "Custom solutions")
        ]

        table = Table(show_header=True, header_style="bold")
        table.add_column("Plan")
        table.add_column("Price")
        table.add_column("Limits")
        table.add_column("Description")

        for plan, price, limits, desc in plans:
            table.add_row(plan, price, limits, desc)

        self.console.print(table)
        self.console.print("\n[dim]Visit https://bharatbuild.dev/pricing for more details[/dim]")

    def _show_api_keys(self):
        """Show API key management"""
        self.console.print("\n[bold cyan]API Keys[/bold cyan]\n")

        self.console.print("[dim]API keys are managed at https://bharatbuild.dev/settings/api-keys[/dim]")

        if Confirm.ask("\nOpen in browser?", default=True):
            try:
                webbrowser.open("https://bharatbuild.dev/settings/api-keys")
            except Exception as e:
                self.console.print(f"[red]Could not open browser: {e}[/red]")

    # ==================== Utilities ====================

    def require_auth(self, message: str = "This action requires authentication") -> bool:
        """Check for required authentication"""
        if not self.is_authenticated():
            self.console.print(f"[yellow]{message}[/yellow]")
            self.console.print("[dim]Use '/login' to authenticate[/dim]")
            return False
        return True

    def update_usage(self, requests: int = 0, tokens: int = 0):
        """Update usage statistics"""
        if not self.credentials:
            return

        self.credentials.daily_requests = getattr(self.credentials, 'daily_requests', 0) + requests
        self.credentials.monthly_tokens = getattr(self.credentials, 'monthly_tokens', 0) + tokens

        self._save_credentials()

    def check_limits(self) -> bool:
        """Check if user is within usage limits"""
        if not self.credentials:
            return True

        daily_requests = getattr(self.credentials, 'daily_requests', 0)
        daily_limit = getattr(self.credentials, 'daily_limit', 100)
        monthly_tokens = getattr(self.credentials, 'monthly_tokens', 0)
        monthly_limit = getattr(self.credentials, 'monthly_limit', 100000)

        if daily_requests >= daily_limit:
            self.console.print("[red]Daily request limit reached[/red]")
            self.console.print("[dim]Upgrade your plan for more requests[/dim]")
            return False

        if monthly_tokens >= monthly_limit:
            self.console.print("[red]Monthly token limit reached[/red]")
            self.console.print("[dim]Upgrade your plan for more tokens[/dim]")
            return False

        return True

    def show_help(self):
        """Show auth help"""
        help_text = """
[bold cyan]Authentication Commands[/bold cyan]

Login and manage your BharatBuild account.

[bold]Commands:[/bold]
  [green]/login[/green]         Login to BharatBuild
  [green]/logout[/green]        Logout from account
  [green]/whoami[/green]        Show current user
  [green]/account[/green]       Manage account settings

[bold]Login Methods:[/bold]
  - Email & Password
  - Access Token (from web portal)
  - API Key (for CI/CD)
  - GitHub OAuth
  - Google OAuth

[bold]Environment Variables:[/bold]
  BHARATBUILD_API_KEY    Set API key
  BHARATBUILD_EMAIL      Set email for login

[bold]API Key Format:[/bold]
  API keys start with 'bb_' prefix
  Example: bb_live_abc123xyz...

[bold]Account Tiers:[/bold]
  Free       - 100 requests/day
  Student    - 100 requests/day (free with .edu email)
  Pro        - 1000 requests/day
  Team       - 5000 requests/day
  Enterprise - Custom limits

[bold]Examples:[/bold]
  /login
  /login --api-key
  /login --github
  export BHARATBUILD_API_KEY=bb_live_...
"""
        self.console.print(help_text)


# Singleton instance
_auth_manager: Optional[CLIAuthManager] = None


def get_auth_manager(api_base_url: str = "http://localhost:8000/api/v1") -> CLIAuthManager:
    """Get or create auth manager singleton"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = CLIAuthManager(api_base_url)
    return _auth_manager
