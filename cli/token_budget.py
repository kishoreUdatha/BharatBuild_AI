"""
BharatBuild CLI Token Budget Management

Manage token limits and budgets per session/request.

Usage:
  /budget set 100000    Set max tokens
  /budget show          Show remaining budget
  /budget reset         Reset budget
"""

import time
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn


class BudgetType(str, Enum):
    """Types of token budgets"""
    SESSION = "session"       # Per session limit
    REQUEST = "request"       # Per request limit
    DAILY = "daily"           # Daily limit
    MONTHLY = "monthly"       # Monthly limit
    PROJECT = "project"       # Per project limit


@dataclass
class TokenUsage:
    """Token usage record"""
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    model: str
    prompt_preview: str = ""


@dataclass
class BudgetConfig:
    """Budget configuration"""
    max_tokens: int = 0                    # 0 = unlimited
    max_input_tokens: int = 0
    max_output_tokens: int = 0
    max_cost: float = 0.0                  # 0 = unlimited
    warn_at_percentage: float = 80.0       # Warn at 80%
    hard_limit: bool = False               # Block when exceeded
    auto_compact_at: float = 90.0          # Auto-compact context at 90%


@dataclass
class BudgetStatus:
    """Current budget status"""
    budget_type: BudgetType
    max_tokens: int
    used_tokens: int
    remaining_tokens: int
    percentage_used: float
    max_cost: float
    estimated_cost: float
    is_exceeded: bool
    is_warning: bool


class TokenBudgetManager:
    """
    Manages token budgets and limits.

    Usage:
        manager = TokenBudgetManager(console)

        # Set budget
        manager.set_budget(BudgetType.SESSION, max_tokens=100000)

        # Check before request
        if manager.can_spend(estimated_tokens=5000):
            # Make request
            ...

        # Record usage
        manager.record_usage(input_tokens=1000, output_tokens=2000)

        # Check status
        status = manager.get_status()
    """

    def __init__(
        self,
        console: Console,
        default_budget: int = 0,
        model: str = "sonnet"
    ):
        self.console = console
        self.model = model

        # Budgets
        self._budgets: Dict[BudgetType, BudgetConfig] = {}

        # Usage tracking
        self._session_usage: List[TokenUsage] = []
        self._daily_usage: Dict[str, List[TokenUsage]] = {}  # date -> usage

        # Callbacks
        self._on_warning: Optional[Callable[[BudgetStatus], None]] = None
        self._on_exceeded: Optional[Callable[[BudgetStatus], None]] = None

        # Set default budget if provided
        if default_budget > 0:
            self.set_budget(BudgetType.SESSION, max_tokens=default_budget)

    # ==================== Budget Configuration ====================

    def set_budget(
        self,
        budget_type: BudgetType,
        max_tokens: int = 0,
        max_input_tokens: int = 0,
        max_output_tokens: int = 0,
        max_cost: float = 0.0,
        warn_at: float = 80.0,
        hard_limit: bool = False
    ):
        """Set a budget limit"""
        self._budgets[budget_type] = BudgetConfig(
            max_tokens=max_tokens,
            max_input_tokens=max_input_tokens,
            max_output_tokens=max_output_tokens,
            max_cost=max_cost,
            warn_at_percentage=warn_at,
            hard_limit=hard_limit
        )

        self.console.print(f"[green]✓ {budget_type.value.capitalize()} budget set: {max_tokens:,} tokens[/green]")

    def remove_budget(self, budget_type: BudgetType):
        """Remove a budget limit"""
        if budget_type in self._budgets:
            del self._budgets[budget_type]
            self.console.print(f"[green]✓ {budget_type.value.capitalize()} budget removed[/green]")

    def set_on_warning(self, callback: Callable[[BudgetStatus], None]):
        """Set callback for budget warning"""
        self._on_warning = callback

    def set_on_exceeded(self, callback: Callable[[BudgetStatus], None]):
        """Set callback for budget exceeded"""
        self._on_exceeded = callback

    # ==================== Usage Tracking ====================

    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = None,
        prompt_preview: str = ""
    ):
        """Record token usage"""
        usage = TokenUsage(
            timestamp=datetime.now(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model or self.model,
            prompt_preview=prompt_preview[:50]
        )

        # Session usage
        self._session_usage.append(usage)

        # Daily usage
        date_key = datetime.now().strftime("%Y-%m-%d")
        if date_key not in self._daily_usage:
            self._daily_usage[date_key] = []
        self._daily_usage[date_key].append(usage)

        # Check budgets
        self._check_budgets()

    def get_session_usage(self) -> Dict[str, int]:
        """Get current session usage"""
        total_input = sum(u.input_tokens for u in self._session_usage)
        total_output = sum(u.output_tokens for u in self._session_usage)

        return {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "requests": len(self._session_usage)
        }

    def get_daily_usage(self, date: str = None) -> Dict[str, int]:
        """Get usage for a specific day"""
        date_key = date or datetime.now().strftime("%Y-%m-%d")
        usage_list = self._daily_usage.get(date_key, [])

        total_input = sum(u.input_tokens for u in usage_list)
        total_output = sum(u.output_tokens for u in usage_list)

        return {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "requests": len(usage_list)
        }

    def reset_session(self):
        """Reset session usage"""
        self._session_usage.clear()
        self.console.print("[green]✓ Session usage reset[/green]")

    # ==================== Budget Checking ====================

    def can_spend(
        self,
        estimated_tokens: int = 0,
        estimated_input: int = 0,
        estimated_output: int = 0
    ) -> bool:
        """Check if we can spend the estimated tokens"""
        if estimated_tokens == 0:
            estimated_tokens = estimated_input + estimated_output

        for budget_type, config in self._budgets.items():
            if not config.hard_limit:
                continue

            status = self._get_budget_status(budget_type)

            if config.max_tokens > 0:
                if status.used_tokens + estimated_tokens > config.max_tokens:
                    return False

        return True

    def get_remaining(self, budget_type: BudgetType = BudgetType.SESSION) -> int:
        """Get remaining tokens for a budget"""
        status = self._get_budget_status(budget_type)
        return status.remaining_tokens

    def get_status(self, budget_type: BudgetType = None) -> List[BudgetStatus]:
        """Get status of all budgets or specific budget"""
        if budget_type:
            return [self._get_budget_status(budget_type)]

        return [self._get_budget_status(bt) for bt in self._budgets.keys()]

    def _get_budget_status(self, budget_type: BudgetType) -> BudgetStatus:
        """Get status for specific budget type"""
        config = self._budgets.get(budget_type, BudgetConfig())

        # Get relevant usage
        if budget_type == BudgetType.SESSION:
            usage = self.get_session_usage()
        elif budget_type == BudgetType.DAILY:
            usage = self.get_daily_usage()
        else:
            usage = self.get_session_usage()

        used = usage["total_tokens"]
        max_tokens = config.max_tokens

        if max_tokens > 0:
            remaining = max(0, max_tokens - used)
            percentage = (used / max_tokens) * 100
        else:
            remaining = float('inf')
            percentage = 0

        # Estimate cost
        estimated_cost = self._estimate_cost(usage["input_tokens"], usage["output_tokens"])

        return BudgetStatus(
            budget_type=budget_type,
            max_tokens=max_tokens,
            used_tokens=used,
            remaining_tokens=remaining if remaining != float('inf') else 0,
            percentage_used=percentage,
            max_cost=config.max_cost,
            estimated_cost=estimated_cost,
            is_exceeded=max_tokens > 0 and used >= max_tokens,
            is_warning=percentage >= config.warn_at_percentage
        )

    def _check_budgets(self):
        """Check all budgets and trigger callbacks"""
        for budget_type, config in self._budgets.items():
            status = self._get_budget_status(budget_type)

            if status.is_exceeded and self._on_exceeded:
                self._on_exceeded(status)
            elif status.is_warning and self._on_warning:
                self._on_warning(status)

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost based on model"""
        # Approximate pricing per 1K tokens
        pricing = {
            "haiku": (0.00025, 0.00125),
            "sonnet": (0.003, 0.015),
            "opus": (0.015, 0.075)
        }

        model_key = "sonnet"
        for key in pricing.keys():
            if key in self.model.lower():
                model_key = key
                break

        input_price, output_price = pricing[model_key]

        input_cost = (input_tokens / 1000) * input_price
        output_cost = (output_tokens / 1000) * output_price

        return input_cost + output_cost

    # ==================== Display ====================

    def show_budget_status(self):
        """Display budget status"""
        statuses = self.get_status()

        if not statuses:
            self.console.print("[dim]No budgets configured[/dim]")
            return

        for status in statuses:
            self._show_single_status(status)

    def _show_single_status(self, status: BudgetStatus):
        """Display single budget status"""
        # Build progress bar
        if status.max_tokens > 0:
            bar_width = 30
            filled = int(bar_width * min(status.percentage_used, 100) / 100)
            bar = "█" * filled + "░" * (bar_width - filled)

            # Color based on usage
            if status.percentage_used < 50:
                color = "green"
            elif status.percentage_used < 80:
                color = "yellow"
            else:
                color = "red"
        else:
            bar = "░" * 30
            color = "dim"

        content_lines = []
        content_lines.append(f"[bold]Type:[/bold] {status.budget_type.value.capitalize()}")

        if status.max_tokens > 0:
            content_lines.append(f"[bold]Limit:[/bold] {status.max_tokens:,} tokens")
            content_lines.append(f"[bold]Used:[/bold] {status.used_tokens:,} tokens")
            content_lines.append(f"[bold]Remaining:[/bold] {status.remaining_tokens:,} tokens")
            content_lines.append("")
            content_lines.append(f"[{color}]{bar}[/{color}] {status.percentage_used:.1f}%")
        else:
            content_lines.append(f"[bold]Used:[/bold] {status.used_tokens:,} tokens")
            content_lines.append("[dim]No limit set[/dim]")

        content_lines.append("")
        content_lines.append(f"[bold]Estimated Cost:[/bold] ${status.estimated_cost:.4f}")

        if status.is_exceeded:
            content_lines.append("")
            content_lines.append("[bold red]⚠ Budget exceeded![/bold red]")
        elif status.is_warning:
            content_lines.append("")
            content_lines.append("[yellow]⚠ Approaching budget limit[/yellow]")

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title=f"[bold cyan]{status.budget_type.value.capitalize()} Budget[/bold cyan]",
            border_style=color
        )

        self.console.print(panel)

    def show_usage_history(self, limit: int = 10):
        """Show recent usage history"""
        if not self._session_usage:
            self.console.print("[dim]No usage this session[/dim]")
            return

        table = Table(title="Recent Token Usage", show_header=True, header_style="bold cyan")
        table.add_column("Time", style="dim")
        table.add_column("Model")
        table.add_column("Input", justify="right")
        table.add_column("Output", justify="right")
        table.add_column("Total", justify="right")

        for usage in reversed(self._session_usage[-limit:]):
            time_str = usage.timestamp.strftime("%H:%M:%S")
            total = usage.input_tokens + usage.output_tokens

            table.add_row(
                time_str,
                usage.model,
                str(usage.input_tokens),
                str(usage.output_tokens),
                str(total)
            )

        self.console.print(table)

    def show_help(self):
        """Show budget help"""
        help_text = """
[bold cyan]Token Budget Commands[/bold cyan]

Manage token usage limits.

[bold]Commands:[/bold]
  [green]/budget[/green]              Show current budget status
  [green]/budget set <n>[/green]     Set session token limit
  [green]/budget daily <n>[/green]   Set daily token limit
  [green]/budget reset[/green]       Reset session usage
  [green]/budget history[/green]     Show usage history
  [green]/budget remove[/green]      Remove budget limit

[bold]Examples:[/bold]
  /budget set 100000    Limit session to 100K tokens
  /budget daily 500000  Limit daily usage to 500K
  /budget set 50000 --hard  Hard limit (blocks requests)

[bold]Options:[/bold]
  --hard              Block requests when exceeded
  --warn <percent>    Warn at percentage (default: 80%)
"""
        self.console.print(help_text)


class AutoCompactor:
    """
    Automatically compact context when approaching token limits.

    Works with TokenBudgetManager to reduce context when needed.
    """

    def __init__(
        self,
        budget_manager: TokenBudgetManager,
        console: Console,
        compact_callback: Callable[[], None]
    ):
        self.budget_manager = budget_manager
        self.console = console
        self.compact_callback = compact_callback
        self._last_compact = 0

    def check_and_compact(self) -> bool:
        """Check if compaction is needed and perform it"""
        for status in self.budget_manager.get_status():
            config = self.budget_manager._budgets.get(status.budget_type)
            if not config:
                continue

            if status.percentage_used >= config.auto_compact_at:
                # Avoid compacting too frequently
                current_time = time.time()
                if current_time - self._last_compact < 60:  # At least 1 minute between compactions
                    continue

                self.console.print("[yellow]Auto-compacting context to free up tokens...[/yellow]")
                self.compact_callback()
                self._last_compact = current_time
                return True

        return False
