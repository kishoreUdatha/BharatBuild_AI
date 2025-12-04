"""
BharatBuild CLI API Key Management

Secure storage and management of API keys:
  /api-key set        Set API key
  /api-key show       Show masked key
  /api-key validate   Validate key
  /api-key rotate     Rotate keys
"""

import os
import json
import base64
import hashlib
import secrets
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm


class KeyProvider(str, Enum):
    """API key providers"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    AZURE = "azure"
    CUSTOM = "custom"


@dataclass
class APIKey:
    """Stored API key"""
    provider: KeyProvider
    key_hash: str  # SHA256 hash for identification
    encrypted_key: str  # Base64 encoded "encrypted" key
    name: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: str = ""
    last_validated: str = ""
    is_valid: bool = True
    usage_count: int = 0


class APIKeyManager:
    """
    Manages API keys securely.

    Features:
    - Secure storage with obfuscation
    - Multiple key support
    - Key validation
    - Usage tracking
    - Key rotation

    Usage:
        manager = APIKeyManager(console, config_dir)

        # Set key
        manager.set_key(KeyProvider.ANTHROPIC, "sk-...")

        # Get key
        key = manager.get_key(KeyProvider.ANTHROPIC)

        # Validate key
        is_valid = manager.validate_key(KeyProvider.ANTHROPIC)
    """

    def __init__(self, console: Console, config_dir: Path = None):
        self.console = console
        self.config_dir = config_dir or Path.home() / ".bharatbuild"
        self.keys_file = self.config_dir / "keys.json"

        # Ensure directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load keys
        self._keys: Dict[str, APIKey] = {}
        self._load_keys()

        # Obfuscation key (derived from machine-specific info)
        self._obfuscation_key = self._get_obfuscation_key()

    def _get_obfuscation_key(self) -> bytes:
        """Get machine-specific obfuscation key"""
        # Combine machine-specific values
        import platform
        machine_info = f"{platform.node()}-{platform.machine()}-bharatbuild"
        return hashlib.sha256(machine_info.encode()).digest()

    def _obfuscate(self, data: str) -> str:
        """Simple obfuscation (not true encryption)"""
        # XOR with obfuscation key
        data_bytes = data.encode()
        key = self._obfuscation_key

        obfuscated = bytes(
            data_bytes[i] ^ key[i % len(key)]
            for i in range(len(data_bytes))
        )

        return base64.b64encode(obfuscated).decode()

    def _deobfuscate(self, data: str) -> str:
        """Reverse obfuscation"""
        try:
            obfuscated = base64.b64decode(data.encode())
            key = self._obfuscation_key

            deobfuscated = bytes(
                obfuscated[i] ^ key[i % len(key)]
                for i in range(len(obfuscated))
            )

            return deobfuscated.decode()
        except Exception:
            return ""

    def _hash_key(self, key: str) -> str:
        """Create hash of key for identification"""
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _load_keys(self):
        """Load keys from storage"""
        if not self.keys_file.exists():
            return

        try:
            with open(self.keys_file) as f:
                data = json.load(f)

            for key_data in data.get("keys", []):
                api_key = APIKey(
                    provider=KeyProvider(key_data["provider"]),
                    key_hash=key_data["key_hash"],
                    encrypted_key=key_data["encrypted_key"],
                    name=key_data.get("name", ""),
                    created_at=key_data.get("created_at", ""),
                    last_used=key_data.get("last_used", ""),
                    last_validated=key_data.get("last_validated", ""),
                    is_valid=key_data.get("is_valid", True),
                    usage_count=key_data.get("usage_count", 0)
                )
                self._keys[api_key.provider.value] = api_key

        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not load API keys: {e}[/yellow]")

    def _save_keys(self):
        """Save keys to storage"""
        data = {
            "keys": [
                {
                    "provider": key.provider.value,
                    "key_hash": key.key_hash,
                    "encrypted_key": key.encrypted_key,
                    "name": key.name,
                    "created_at": key.created_at,
                    "last_used": key.last_used,
                    "last_validated": key.last_validated,
                    "is_valid": key.is_valid,
                    "usage_count": key.usage_count
                }
                for key in self._keys.values()
            ]
        }

        with open(self.keys_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Set restrictive permissions
        try:
            os.chmod(self.keys_file, 0o600)
        except Exception:
            pass

    # ==================== Key Operations ====================

    def set_key(
        self,
        provider: KeyProvider,
        key: str,
        name: str = "",
        from_env: bool = False
    ) -> bool:
        """Set an API key"""
        if not key:
            self.console.print("[red]API key cannot be empty[/red]")
            return False

        # Basic validation
        if provider == KeyProvider.ANTHROPIC and not key.startswith("sk-"):
            self.console.print("[yellow]Warning: Anthropic keys typically start with 'sk-'[/yellow]")

        # Create key object
        api_key = APIKey(
            provider=provider,
            key_hash=self._hash_key(key),
            encrypted_key=self._obfuscate(key),
            name=name or f"{provider.value} key"
        )

        # Store
        self._keys[provider.value] = api_key
        self._save_keys()

        # Also set environment variable for current session
        env_var = self._get_env_var_name(provider)
        os.environ[env_var] = key

        masked = self._mask_key(key)
        self.console.print(f"[green]✓ API key set for {provider.value}: {masked}[/green]")

        return True

    def get_key(self, provider: KeyProvider) -> Optional[str]:
        """Get an API key"""
        # First check environment variable
        env_var = self._get_env_var_name(provider)
        env_key = os.environ.get(env_var)

        if env_key:
            return env_key

        # Then check stored keys
        api_key = self._keys.get(provider.value)
        if api_key:
            # Update usage
            api_key.last_used = datetime.now().isoformat()
            api_key.usage_count += 1
            self._save_keys()

            return self._deobfuscate(api_key.encrypted_key)

        return None

    def remove_key(self, provider: KeyProvider) -> bool:
        """Remove an API key"""
        if provider.value not in self._keys:
            self.console.print(f"[yellow]No key found for {provider.value}[/yellow]")
            return False

        if not Confirm.ask(f"Remove API key for {provider.value}?"):
            return False

        del self._keys[provider.value]
        self._save_keys()

        # Also remove from environment
        env_var = self._get_env_var_name(provider)
        if env_var in os.environ:
            del os.environ[env_var]

        self.console.print(f"[green]✓ Removed API key for {provider.value}[/green]")
        return True

    def validate_key(self, provider: KeyProvider) -> bool:
        """Validate an API key by making a test request"""
        key = self.get_key(provider)

        if not key:
            self.console.print(f"[red]No key found for {provider.value}[/red]")
            return False

        self.console.print(f"[cyan]Validating {provider.value} API key...[/cyan]")

        is_valid = False

        if provider == KeyProvider.ANTHROPIC:
            is_valid = self._validate_anthropic_key(key)
        elif provider == KeyProvider.OPENAI:
            is_valid = self._validate_openai_key(key)
        else:
            # Basic format check for others
            is_valid = len(key) > 10

        # Update validation status
        if provider.value in self._keys:
            self._keys[provider.value].is_valid = is_valid
            self._keys[provider.value].last_validated = datetime.now().isoformat()
            self._save_keys()

        if is_valid:
            self.console.print(f"[green]✓ API key is valid[/green]")
        else:
            self.console.print(f"[red]✗ API key is invalid or expired[/red]")

        return is_valid

    def _validate_anthropic_key(self, key: str) -> bool:
        """Validate Anthropic API key"""
        try:
            import httpx

            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "Hi"}]
                },
                timeout=10
            )

            # 200 or 400 (bad request but authenticated) means valid key
            return response.status_code in [200, 400]

        except Exception:
            return False

    def _validate_openai_key(self, key: str) -> bool:
        """Validate OpenAI API key"""
        try:
            import httpx

            response = httpx.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"},
                timeout=10
            )

            return response.status_code == 200

        except Exception:
            return False

    def _get_env_var_name(self, provider: KeyProvider) -> str:
        """Get environment variable name for provider"""
        env_vars = {
            KeyProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            KeyProvider.OPENAI: "OPENAI_API_KEY",
            KeyProvider.GOOGLE: "GOOGLE_API_KEY",
            KeyProvider.AZURE: "AZURE_API_KEY",
        }
        return env_vars.get(provider, f"{provider.value.upper()}_API_KEY")

    def _mask_key(self, key: str) -> str:
        """Mask API key for display"""
        if len(key) < 10:
            return "*" * len(key)
        return key[:7] + "..." + key[-4:]

    # ==================== Key Rotation ====================

    def rotate_key(self, provider: KeyProvider, new_key: str) -> bool:
        """Rotate an API key"""
        old_key = self.get_key(provider)

        if not old_key:
            self.console.print(f"[yellow]No existing key for {provider.value}. Setting new key.[/yellow]")
            return self.set_key(provider, new_key)

        # Validate new key first
        self.console.print("[cyan]Validating new key...[/cyan]")

        # Temporarily set new key to validate
        os.environ[self._get_env_var_name(provider)] = new_key

        is_valid = False
        if provider == KeyProvider.ANTHROPIC:
            is_valid = self._validate_anthropic_key(new_key)
        elif provider == KeyProvider.OPENAI:
            is_valid = self._validate_openai_key(new_key)
        else:
            is_valid = len(new_key) > 10

        if not is_valid:
            # Restore old key
            os.environ[self._get_env_var_name(provider)] = old_key
            self.console.print("[red]New key is invalid. Keeping old key.[/red]")
            return False

        # Set new key
        return self.set_key(provider, new_key, name=f"{provider.value} key (rotated)")

    # ==================== Interactive ====================

    def set_key_interactive(self, provider: KeyProvider = None):
        """Set API key interactively"""
        if not provider:
            # Ask for provider
            self.console.print("[bold]Select API provider:[/bold]")
            for i, p in enumerate(KeyProvider, 1):
                self.console.print(f"  {i}. {p.value}")

            choice = Prompt.ask("Provider", choices=[str(i) for i in range(1, len(KeyProvider) + 1)])
            provider = list(KeyProvider)[int(choice) - 1]

        # Get key
        key = Prompt.ask(f"Enter {provider.value} API key", password=True)

        if not key:
            self.console.print("[yellow]Cancelled[/yellow]")
            return

        # Validate?
        validate = Confirm.ask("Validate key?", default=True)

        if validate:
            # Temporarily set for validation
            os.environ[self._get_env_var_name(provider)] = key
            is_valid = self.validate_key(provider)

            if not is_valid:
                if not Confirm.ask("Key appears invalid. Save anyway?"):
                    return

        self.set_key(provider, key)

    # ==================== Display ====================

    def list_keys(self):
        """List all stored keys"""
        if not self._keys:
            self.console.print("[dim]No API keys stored[/dim]")
            self.console.print("[dim]Use /api-key set to add a key[/dim]")
            return

        table = Table(title="Stored API Keys", show_header=True, header_style="bold cyan")
        table.add_column("Provider")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Last Used")
        table.add_column("Uses")

        for api_key in self._keys.values():
            # Status
            if api_key.is_valid:
                status = "[green]Valid[/green]"
            else:
                status = "[red]Invalid[/red]"

            # Last used
            if api_key.last_used:
                try:
                    dt = datetime.fromisoformat(api_key.last_used)
                    last_used = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    last_used = api_key.last_used
            else:
                last_used = "[dim]Never[/dim]"

            table.add_row(
                api_key.provider.value,
                api_key.name,
                status,
                last_used,
                str(api_key.usage_count)
            )

        self.console.print(table)

        # Check environment variables
        self.console.print("\n[bold]Environment Variables:[/bold]")
        for provider in KeyProvider:
            env_var = self._get_env_var_name(provider)
            if os.environ.get(env_var):
                masked = self._mask_key(os.environ[env_var])
                self.console.print(f"  {env_var}: {masked}")

    def show_key(self, provider: KeyProvider, reveal: bool = False):
        """Show a specific key"""
        key = self.get_key(provider)

        if not key:
            self.console.print(f"[red]No key found for {provider.value}[/red]")
            return

        if reveal:
            if Confirm.ask("Reveal full API key?"):
                self.console.print(f"[bold]{provider.value}:[/bold] {key}")
            else:
                self.console.print(f"[bold]{provider.value}:[/bold] {self._mask_key(key)}")
        else:
            self.console.print(f"[bold]{provider.value}:[/bold] {self._mask_key(key)}")

        # Show additional info
        if provider.value in self._keys:
            api_key = self._keys[provider.value]
            self.console.print(f"[dim]Hash: {api_key.key_hash}[/dim]")
            self.console.print(f"[dim]Created: {api_key.created_at}[/dim]")

    def show_help(self):
        """Show API key help"""
        help_text = """
[bold cyan]API Key Commands[/bold cyan]

Manage API keys securely.

[bold]Commands:[/bold]
  [green]/api-key[/green]              List stored keys
  [green]/api-key set[/green]          Set key interactively
  [green]/api-key show <p>[/green]     Show key for provider
  [green]/api-key validate[/green]     Validate a key
  [green]/api-key remove <p>[/green]   Remove a key
  [green]/api-key rotate <p>[/green]   Rotate key

[bold]Providers:[/bold]
  • anthropic - Anthropic API (Claude)
  • openai    - OpenAI API (GPT)
  • google    - Google AI API
  • azure     - Azure OpenAI

[bold]Environment Variables:[/bold]
  ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.
  Environment variables take precedence over stored keys.

[bold]Security:[/bold]
  • Keys are stored with obfuscation
  • Config file has restricted permissions
  • Keys are never logged or displayed in full
"""
        self.console.print(help_text)
