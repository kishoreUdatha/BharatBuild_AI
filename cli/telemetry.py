"""
BharatBuild CLI Telemetry

Privacy-respecting telemetry with full user control:
  /telemetry on       Enable telemetry
  /telemetry off      Disable telemetry
  /telemetry status   Show telemetry status
"""

import os
import json
import uuid
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm


class TelemetryEvent(str, Enum):
    """Types of telemetry events"""
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    COMMAND_USED = "command_used"
    FEATURE_USED = "feature_used"
    ERROR_OCCURRED = "error_occurred"
    MODEL_USED = "model_used"


@dataclass
class TelemetryConfig:
    """Telemetry configuration"""
    enabled: bool = False  # Disabled by default
    anonymous_id: str = ""  # Anonymous installation ID
    share_usage: bool = True  # Share usage statistics
    share_errors: bool = True  # Share error reports
    share_model_usage: bool = True  # Share model usage


@dataclass
class TelemetryEvent:
    """A telemetry event"""
    event_type: str
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)


class TelemetryManager:
    """
    Privacy-respecting telemetry manager.

    Principles:
    - Disabled by default (opt-in)
    - No personal data collected
    - No prompt/response content
    - Anonymous installation ID only
    - Full transparency about what's collected
    - Easy to disable completely

    What we collect (when enabled):
    - Anonymous installation ID
    - Feature usage counts
    - Error types (not content)
    - Model usage statistics
    - Session duration

    What we NEVER collect:
    - API keys
    - Prompt content
    - Response content
    - File contents
    - Personal information
    - IP addresses (handled server-side)

    Usage:
        telemetry = TelemetryManager(console, config_dir)

        # Check if enabled
        if telemetry.is_enabled():
            telemetry.track_event("command_used", {"command": "help"})
    """

    def __init__(self, console: Console, config_dir: Path = None):
        self.console = console
        self.config_dir = config_dir or Path.home() / ".bharatbuild"
        self.config_file = self.config_dir / "telemetry.json"
        self.events_file = self.config_dir / "telemetry_events.json"

        # Load config
        self.config = self._load_config()

        # Events queue
        self._events: List[TelemetryEvent] = []

    def _load_config(self) -> TelemetryConfig:
        """Load telemetry configuration"""
        config = TelemetryConfig()

        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    data = json.load(f)

                config.enabled = data.get("enabled", False)
                config.anonymous_id = data.get("anonymous_id", "")
                config.share_usage = data.get("share_usage", True)
                config.share_errors = data.get("share_errors", True)
                config.share_model_usage = data.get("share_model_usage", True)

            except Exception:
                pass

        # Generate anonymous ID if not exists
        if not config.anonymous_id:
            config.anonymous_id = self._generate_anonymous_id()
            self._save_config(config)

        return config

    def _save_config(self, config: TelemetryConfig = None):
        """Save telemetry configuration"""
        config = config or self.config
        self.config_dir.mkdir(parents=True, exist_ok=True)

        with open(self.config_file, 'w') as f:
            json.dump({
                "enabled": config.enabled,
                "anonymous_id": config.anonymous_id,
                "share_usage": config.share_usage,
                "share_errors": config.share_errors,
                "share_model_usage": config.share_model_usage,
            }, f, indent=2)

    def _generate_anonymous_id(self) -> str:
        """Generate anonymous installation ID"""
        # Use random UUID - no machine-identifiable info
        return str(uuid.uuid4())

    # ==================== Control ====================

    def is_enabled(self) -> bool:
        """Check if telemetry is enabled"""
        # Also check environment variable
        env_disabled = os.environ.get("BHARATBUILD_TELEMETRY_DISABLED", "").lower() in ("1", "true", "yes")
        return self.config.enabled and not env_disabled

    def enable(self, show_notice: bool = True):
        """Enable telemetry"""
        self.config.enabled = True
        self._save_config()

        if show_notice:
            self.console.print("[green]✓ Telemetry enabled[/green]")
            self.console.print("[dim]Thank you for helping improve BharatBuild![/dim]")
            self._show_what_we_collect()

    def disable(self):
        """Disable telemetry"""
        self.config.enabled = False
        self._save_config()

        # Clear any pending events
        self._events.clear()
        if self.events_file.exists():
            self.events_file.unlink()

        self.console.print("[green]✓ Telemetry disabled[/green]")
        self.console.print("[dim]No data will be collected or sent[/dim]")

    def set_preferences(
        self,
        share_usage: bool = None,
        share_errors: bool = None,
        share_model_usage: bool = None
    ):
        """Set telemetry preferences"""
        if share_usage is not None:
            self.config.share_usage = share_usage

        if share_errors is not None:
            self.config.share_errors = share_errors

        if share_model_usage is not None:
            self.config.share_model_usage = share_model_usage

        self._save_config()
        self.console.print("[green]✓ Telemetry preferences updated[/green]")

    # ==================== Event Tracking ====================

    def track_event(self, event_type: str, data: Dict[str, Any] = None):
        """Track a telemetry event"""
        if not self.is_enabled():
            return

        # Filter based on preferences
        if event_type == "error_occurred" and not self.config.share_errors:
            return
        if event_type == "model_used" and not self.config.share_model_usage:
            return
        if event_type in ("command_used", "feature_used") and not self.config.share_usage:
            return

        # Sanitize data - remove any potentially sensitive info
        safe_data = self._sanitize_data(data or {})

        event = TelemetryEvent(
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            data=safe_data
        )

        self._events.append(event)

        # Batch save
        if len(self._events) >= 10:
            self._save_events()

    def track_session_start(self):
        """Track session start"""
        self.track_event("session_start", {
            "version": self._get_version(),
            "platform": self._get_platform(),
        })

    def track_session_end(self, duration_seconds: float, requests: int):
        """Track session end"""
        self.track_event("session_end", {
            "duration": int(duration_seconds),
            "requests": requests,
        })

    def track_command(self, command: str):
        """Track command usage"""
        # Only track command name, not arguments
        self.track_event("command_used", {"command": command})

    def track_feature(self, feature: str):
        """Track feature usage"""
        self.track_event("feature_used", {"feature": feature})

    def track_error(self, error_type: str):
        """Track error occurrence"""
        # Only track error type, not message or stack trace
        self.track_event("error_occurred", {"type": error_type})

    def track_model_usage(self, model: str, tokens: int):
        """Track model usage"""
        # Only track model name and token count
        self.track_event("model_used", {
            "model": self._anonymize_model(model),
            "tokens": tokens
        })

    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove any potentially sensitive data"""
        # List of keys that should never be included
        sensitive_keys = [
            "api_key", "key", "token", "password", "secret",
            "content", "message", "prompt", "response",
            "path", "file", "url", "email", "username"
        ]

        safe_data = {}

        for key, value in data.items():
            # Skip sensitive keys
            if any(s in key.lower() for s in sensitive_keys):
                continue

            # Truncate strings
            if isinstance(value, str) and len(value) > 50:
                value = value[:50]

            safe_data[key] = value

        return safe_data

    def _anonymize_model(self, model: str) -> str:
        """Anonymize model name to just the tier"""
        if "haiku" in model.lower():
            return "haiku"
        elif "sonnet" in model.lower():
            return "sonnet"
        elif "opus" in model.lower():
            return "opus"
        return "unknown"

    def _get_version(self) -> str:
        """Get BharatBuild version"""
        return "1.0.0"  # Replace with actual version

    def _get_platform(self) -> str:
        """Get platform identifier"""
        import platform
        return platform.system().lower()

    def _save_events(self):
        """Save events to file"""
        if not self._events:
            return

        try:
            existing = []
            if self.events_file.exists():
                with open(self.events_file) as f:
                    existing = json.load(f)

            # Add new events
            existing.extend([asdict(e) for e in self._events])

            # Keep only recent events (max 100)
            existing = existing[-100:]

            with open(self.events_file, 'w') as f:
                json.dump(existing, f)

            self._events.clear()

        except Exception:
            pass

    def flush(self):
        """Flush pending events"""
        self._save_events()

        # In a real implementation, this would send to server
        # For now, just clear local events
        if self.events_file.exists():
            self.events_file.unlink()

    # ==================== Display ====================

    def show_status(self):
        """Show telemetry status"""
        content_lines = []

        if self.is_enabled():
            content_lines.append("[bold]Status:[/bold] [green]Enabled[/green]")
        else:
            content_lines.append("[bold]Status:[/bold] [dim]Disabled[/dim]")

        content_lines.append(f"[bold]Anonymous ID:[/bold] {self.config.anonymous_id[:8]}...")
        content_lines.append("")

        content_lines.append("[bold]Sharing Preferences:[/bold]")
        content_lines.append(f"  Usage statistics: {'Yes' if self.config.share_usage else 'No'}")
        content_lines.append(f"  Error reports: {'Yes' if self.config.share_errors else 'No'}")
        content_lines.append(f"  Model usage: {'Yes' if self.config.share_model_usage else 'No'}")

        # Environment override
        if os.environ.get("BHARATBUILD_TELEMETRY_DISABLED"):
            content_lines.append("")
            content_lines.append("[yellow]Note: Disabled via BHARATBUILD_TELEMETRY_DISABLED[/yellow]")

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title="[bold cyan]Telemetry Status[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

    def _show_what_we_collect(self):
        """Show what data we collect"""
        self.console.print("\n[bold]What we collect:[/bold]")
        self.console.print("  • Anonymous installation ID")
        self.console.print("  • Feature usage counts")
        self.console.print("  • Error types (not messages)")
        self.console.print("  • Model usage statistics")
        self.console.print("  • Session duration")

        self.console.print("\n[bold]What we NEVER collect:[/bold]")
        self.console.print("  • API keys or credentials")
        self.console.print("  • Prompt or response content")
        self.console.print("  • File contents or paths")
        self.console.print("  • Personal information")

    def show_privacy_policy(self):
        """Show privacy policy"""
        policy = """
[bold cyan]BharatBuild AI Privacy Policy[/bold cyan]

[bold]Our Commitment[/bold]
We respect your privacy and are committed to being transparent about
our data practices. Telemetry is disabled by default and fully optional.

[bold]What We Collect (When Enabled)[/bold]
• Anonymous installation ID (random UUID, not tied to you)
• Feature and command usage counts
• Error types (not error messages or stack traces)
• Model usage statistics (model tier and token counts)
• Session duration

[bold]What We NEVER Collect[/bold]
• API keys, passwords, or credentials
• Prompt content or AI responses
• File contents, paths, or names
• Code you write or generate
• Personal information (name, email, etc.)
• IP addresses are not logged server-side

[bold]How Data is Used[/bold]
• Improve BharatBuild features
• Identify common errors
• Understand usage patterns
• Prioritize development

[bold]Your Control[/bold]
• Telemetry is disabled by default
• Enable/disable anytime with /telemetry on/off
• Set BHARATBUILD_TELEMETRY_DISABLED=1 to force disable
• Choose what to share in preferences
• Delete local data anytime

[bold]Data Retention[/bold]
• Local data: Cleared when you disable telemetry
• Server data: Aggregated and anonymized, raw data deleted after 30 days

[bold]Contact[/bold]
Questions? Contact us at privacy@bharatbuild.ai
"""
        self.console.print(policy)

    def show_help(self):
        """Show telemetry help"""
        help_text = """
[bold cyan]Telemetry Commands[/bold cyan]

Privacy-respecting usage analytics (disabled by default).

[bold]Commands:[/bold]
  [green]/telemetry[/green]            Show telemetry status
  [green]/telemetry on[/green]         Enable telemetry
  [green]/telemetry off[/green]        Disable telemetry
  [green]/telemetry privacy[/green]    Show privacy policy
  [green]/telemetry prefs[/green]      Configure preferences

[bold]Environment Variable:[/bold]
  BHARATBUILD_TELEMETRY_DISABLED=1
  Set this to force-disable telemetry.

[bold]What We Collect:[/bold]
  • Anonymous installation ID
  • Feature usage counts
  • Error types (not messages)
  • Model usage stats
  • Session duration

[bold]What We NEVER Collect:[/bold]
  • API keys or credentials
  • Prompt/response content
  • File contents or paths
  • Personal information
"""
        self.console.print(help_text)

    # ==================== First Run ====================

    def prompt_for_consent(self) -> bool:
        """Prompt user for telemetry consent on first run"""
        self.console.print("\n[bold cyan]Help Improve BharatBuild AI[/bold cyan]\n")

        self.console.print("Would you like to share anonymous usage data?")
        self.console.print("This helps us improve BharatBuild for everyone.\n")

        self._show_what_we_collect()

        self.console.print("\n[dim]You can change this anytime with /telemetry on/off[/dim]\n")

        if Confirm.ask("Enable telemetry?", default=False):
            self.enable(show_notice=False)
            return True
        else:
            self.disable()
            return False
