"""
BharatBuild CLI Cost Tracking

Tracks token usage and costs per session:
  /cost           Show current session costs
  /cost history   Show cost history
  /cost reset     Reset session costs
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class ModelTier(str, Enum):
    """Model pricing tiers"""
    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"


@dataclass
class ModelPricing:
    """Pricing per model"""
    input_per_1k: float   # Cost per 1000 input tokens
    output_per_1k: float  # Cost per 1000 output tokens


# Claude model pricing (as of early 2024)
MODEL_PRICING = {
    ModelTier.HAIKU: ModelPricing(
        input_per_1k=0.00025,
        output_per_1k=0.00125
    ),
    ModelTier.SONNET: ModelPricing(
        input_per_1k=0.003,
        output_per_1k=0.015
    ),
    ModelTier.OPUS: ModelPricing(
        input_per_1k=0.015,
        output_per_1k=0.075
    ),
}


@dataclass
class UsageRecord:
    """A single usage record"""
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    prompt_preview: str = ""


@dataclass
class SessionStats:
    """Statistics for a session"""
    session_id: str
    started_at: str
    ended_at: Optional[str] = None
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    model_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    records: List[UsageRecord] = field(default_factory=list)


class CostTracker:
    """
    Tracks token usage and costs.

    Usage:
        tracker = CostTracker(console, config_dir)

        # Record usage
        tracker.record_usage(
            model="sonnet",
            input_tokens=500,
            output_tokens=1000
        )

        # Show current stats
        tracker.show_session_stats()

        # Get total cost
        cost = tracker.get_session_cost()
    """

    def __init__(
        self,
        console: Console,
        config_dir: Optional[Path] = None,
        model: str = "sonnet"
    ):
        self.console = console
        self.config_dir = config_dir or (Path.home() / ".bharatbuild" / "costs")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.default_model = model

        # Current session
        self._session = SessionStats(
            session_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            started_at=datetime.now().isoformat()
        )

        # Load history
        self._history: List[SessionStats] = []
        self._load_history()

    def _load_history(self):
        """Load cost history"""
        history_file = self.config_dir / "history.json"

        if history_file.exists():
            try:
                with open(history_file) as f:
                    data = json.load(f)

                for session_data in data.get("sessions", []):
                    records = [
                        UsageRecord(**r) for r in session_data.get("records", [])
                    ]

                    session = SessionStats(
                        session_id=session_data["session_id"],
                        started_at=session_data["started_at"],
                        ended_at=session_data.get("ended_at"),
                        total_requests=session_data.get("total_requests", 0),
                        total_input_tokens=session_data.get("total_input_tokens", 0),
                        total_output_tokens=session_data.get("total_output_tokens", 0),
                        total_tokens=session_data.get("total_tokens", 0),
                        total_cost=session_data.get("total_cost", 0.0),
                        model_breakdown=session_data.get("model_breakdown", {}),
                        records=records
                    )
                    self._history.append(session)

            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load cost history: {e}[/yellow]")

    def _save_history(self):
        """Save cost history"""
        history_file = self.config_dir / "history.json"

        try:
            sessions_data = []

            # Include current session
            all_sessions = self._history + [self._session]

            for session in all_sessions[-100:]:  # Keep last 100 sessions
                sessions_data.append({
                    "session_id": session.session_id,
                    "started_at": session.started_at,
                    "ended_at": session.ended_at,
                    "total_requests": session.total_requests,
                    "total_input_tokens": session.total_input_tokens,
                    "total_output_tokens": session.total_output_tokens,
                    "total_tokens": session.total_tokens,
                    "total_cost": session.total_cost,
                    "model_breakdown": session.model_breakdown,
                    "records": [
                        {
                            "timestamp": r.timestamp,
                            "model": r.model,
                            "input_tokens": r.input_tokens,
                            "output_tokens": r.output_tokens,
                            "total_tokens": r.total_tokens,
                            "cost": r.cost,
                            "prompt_preview": r.prompt_preview
                        }
                        for r in session.records[-50:]  # Keep last 50 records per session
                    ]
                })

            with open(history_file, 'w') as f:
                json.dump({"sessions": sessions_data}, f, indent=2)

        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not save cost history: {e}[/yellow]")

    def _get_model_tier(self, model: str) -> ModelTier:
        """Get model tier from model name"""
        model_lower = model.lower()

        if "haiku" in model_lower:
            return ModelTier.HAIKU
        elif "opus" in model_lower:
            return ModelTier.OPUS
        else:
            return ModelTier.SONNET

    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost for token usage"""
        tier = self._get_model_tier(model)
        pricing = MODEL_PRICING.get(tier, MODEL_PRICING[ModelTier.SONNET])

        input_cost = (input_tokens / 1000) * pricing.input_per_1k
        output_cost = (output_tokens / 1000) * pricing.output_per_1k

        return input_cost + output_cost

    # ==================== Recording ====================

    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        model: Optional[str] = None,
        prompt_preview: str = ""
    ):
        """Record token usage"""
        model = model or self.default_model
        total_tokens = input_tokens + output_tokens
        cost = self._calculate_cost(model, input_tokens, output_tokens)

        # Create record
        record = UsageRecord(
            timestamp=datetime.now().isoformat(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost=cost,
            prompt_preview=prompt_preview[:50]
        )

        # Update session
        self._session.records.append(record)
        self._session.total_requests += 1
        self._session.total_input_tokens += input_tokens
        self._session.total_output_tokens += output_tokens
        self._session.total_tokens += total_tokens
        self._session.total_cost += cost

        # Update model breakdown
        tier = self._get_model_tier(model).value
        if tier not in self._session.model_breakdown:
            self._session.model_breakdown[tier] = {
                "requests": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }

        self._session.model_breakdown[tier]["requests"] += 1
        self._session.model_breakdown[tier]["input_tokens"] += input_tokens
        self._session.model_breakdown[tier]["output_tokens"] += output_tokens
        self._session.model_breakdown[tier]["cost"] += cost

        # Auto-save periodically
        if self._session.total_requests % 10 == 0:
            self._save_history()

    def get_session_cost(self) -> float:
        """Get current session total cost"""
        return self._session.total_cost

    def get_session_tokens(self) -> int:
        """Get current session total tokens"""
        return self._session.total_tokens

    def reset_session(self):
        """Start a new session (saves current to history)"""
        # End current session
        self._session.ended_at = datetime.now().isoformat()

        # Add to history if has usage
        if self._session.total_requests > 0:
            self._history.append(self._session)
            self._save_history()

        # Start new session
        self._session = SessionStats(
            session_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            started_at=datetime.now().isoformat()
        )

        self.console.print("[green]✓ Session costs reset[/green]")

    def end_session(self):
        """End current session and save"""
        self._session.ended_at = datetime.now().isoformat()
        self._save_history()

    # ==================== Display ====================

    def show_session_stats(self):
        """Show current session statistics"""
        session = self._session

        if session.total_requests == 0:
            self.console.print("[dim]No usage this session[/dim]")
            return

        # Calculate duration
        started = datetime.fromisoformat(session.started_at)
        duration = datetime.now() - started
        duration_str = self._format_duration(duration)

        # Build display
        content_lines = []
        content_lines.append(f"[bold]Session Duration:[/bold] {duration_str}")
        content_lines.append(f"[bold]Total Requests:[/bold] {session.total_requests}")
        content_lines.append("")

        # Token breakdown
        content_lines.append("[bold]Tokens:[/bold]")
        content_lines.append(f"  Input:  [cyan]{session.total_input_tokens:,}[/cyan]")
        content_lines.append(f"  Output: [cyan]{session.total_output_tokens:,}[/cyan]")
        content_lines.append(f"  Total:  [cyan]{session.total_tokens:,}[/cyan]")
        content_lines.append("")

        # Cost
        content_lines.append(f"[bold]Total Cost:[/bold] [green]${session.total_cost:.4f}[/green]")

        # Model breakdown
        if session.model_breakdown:
            content_lines.append("")
            content_lines.append("[bold]By Model:[/bold]")
            for model, stats in session.model_breakdown.items():
                content_lines.append(
                    f"  {model}: {stats['requests']} requests, "
                    f"{stats['input_tokens'] + stats['output_tokens']:,} tokens, "
                    f"${stats['cost']:.4f}"
                )

        content = "\n".join(content_lines)

        panel = Panel(
            Text.from_markup(content),
            title="[bold cyan]Session Cost Summary[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

    def show_compact_stats(self):
        """Show compact stats in one line"""
        session = self._session

        if session.total_requests == 0:
            return

        tokens_str = self._format_tokens(session.total_tokens)
        cost_str = f"${session.total_cost:.4f}"

        self.console.print(
            f"[dim]Session: {session.total_requests} requests · "
            f"{tokens_str} tokens · {cost_str}[/dim]"
        )

    def show_history(self, limit: int = 10):
        """Show cost history"""
        if not self._history:
            self.console.print("[dim]No cost history[/dim]")
            return

        table = Table(title="Cost History", show_header=True, header_style="bold cyan")
        table.add_column("Date", style="dim")
        table.add_column("Duration")
        table.add_column("Requests", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Cost", justify="right", style="green")

        for session in reversed(self._history[-limit:]):
            # Format date
            started = datetime.fromisoformat(session.started_at)
            date_str = started.strftime("%Y-%m-%d %H:%M")

            # Format duration
            if session.ended_at:
                ended = datetime.fromisoformat(session.ended_at)
                duration = ended - started
            else:
                duration = timedelta(0)
            duration_str = self._format_duration(duration)

            table.add_row(
                date_str,
                duration_str,
                str(session.total_requests),
                f"{session.total_tokens:,}",
                f"${session.total_cost:.4f}"
            )

        self.console.print(table)

        # Total
        total_cost = sum(s.total_cost for s in self._history)
        total_tokens = sum(s.total_tokens for s in self._history)
        total_requests = sum(s.total_requests for s in self._history)

        self.console.print(f"\n[bold]Total (all time):[/bold] {total_requests} requests, {total_tokens:,} tokens, [green]${total_cost:.4f}[/green]")

    def show_recent_usage(self, limit: int = 10):
        """Show recent usage records"""
        records = self._session.records[-limit:]

        if not records:
            self.console.print("[dim]No usage records[/dim]")
            return

        table = Table(title="Recent Usage", show_header=True, header_style="bold cyan")
        table.add_column("Time", style="dim")
        table.add_column("Model")
        table.add_column("Input", justify="right")
        table.add_column("Output", justify="right")
        table.add_column("Cost", justify="right", style="green")
        table.add_column("Prompt")

        for record in reversed(records):
            # Format time
            timestamp = datetime.fromisoformat(record.timestamp)
            time_str = timestamp.strftime("%H:%M:%S")

            table.add_row(
                time_str,
                record.model,
                str(record.input_tokens),
                str(record.output_tokens),
                f"${record.cost:.4f}",
                record.prompt_preview[:20] + "..." if len(record.prompt_preview) > 20 else record.prompt_preview
            )

        self.console.print(table)

    def show_budget_status(self, budget: float):
        """Show budget status"""
        spent = self._session.total_cost
        remaining = max(0, budget - spent)
        percent_used = (spent / budget * 100) if budget > 0 else 0

        # Build progress bar
        bar_width = 30
        filled = int(bar_width * min(percent_used, 100) / 100)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Color based on usage
        if percent_used < 50:
            color = "green"
        elif percent_used < 80:
            color = "yellow"
        else:
            color = "red"

        content_lines = []
        content_lines.append(f"[bold]Budget:[/bold] ${budget:.2f}")
        content_lines.append(f"[bold]Spent:[/bold] ${spent:.4f}")
        content_lines.append(f"[bold]Remaining:[/bold] ${remaining:.4f}")
        content_lines.append("")
        content_lines.append(f"[{color}]{bar}[/{color}] {percent_used:.1f}%")

        content = "\n".join(content_lines)

        panel = Panel(
            Text.from_markup(content),
            title="[bold cyan]Budget Status[/bold cyan]",
            border_style=color
        )

        self.console.print(panel)

    def _format_duration(self, delta: timedelta) -> str:
        """Format duration for display"""
        total_seconds = int(delta.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            mins = total_seconds // 60
            secs = total_seconds % 60
            return f"{mins}m {secs}s"
        else:
            hours = total_seconds // 3600
            mins = (total_seconds % 3600) // 60
            return f"{hours}h {mins}m"

    def _format_tokens(self, tokens: int) -> str:
        """Format token count for display"""
        if tokens >= 1_000_000:
            return f"{tokens / 1_000_000:.1f}M"
        elif tokens >= 1000:
            return f"{tokens / 1000:.1f}k"
        return str(tokens)

    def show_pricing(self):
        """Show model pricing information"""
        table = Table(title="Model Pricing", show_header=True, header_style="bold cyan")
        table.add_column("Model")
        table.add_column("Input (per 1K)", justify="right")
        table.add_column("Output (per 1K)", justify="right")

        for tier, pricing in MODEL_PRICING.items():
            table.add_row(
                tier.value.capitalize(),
                f"${pricing.input_per_1k:.5f}",
                f"${pricing.output_per_1k:.5f}"
            )

        self.console.print(table)
