"""
BharatBuild CLI Extended Thinking Display

Shows Claude Code style thinking/reasoning display:
╭─ 💭 Thinking ───────────────────────────────╮
│ Let me analyze the codebase structure...    │
│ I see there are 3 main modules...           │
│ The best approach would be...               │
╰─────────────────────────────────────────────╯
"""

import time
import threading
from typing import Optional, List, Callable
from dataclasses import dataclass
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.box import ROUNDED


class ThinkingState(str, Enum):
    """States of thinking display"""
    THINKING = "thinking"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    REASONING = "reasoning"
    COMPLETE = "complete"


@dataclass
class ThinkingStep:
    """A step in the thinking process"""
    content: str
    state: ThinkingState = ThinkingState.THINKING
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class ThinkingDisplay:
    """
    Extended thinking display with streaming support.

    Shows thinking process in a Claude Code style panel that
    updates in real-time as thoughts are streamed.

    Usage:
        display = ThinkingDisplay(console)

        # Start thinking display
        display.start()

        # Add thoughts as they stream
        display.add_thought("Let me analyze the code...")
        display.add_thought("I see the issue is in the auth module...")

        # Update state
        display.set_state(ThinkingState.PLANNING)
        display.add_thought("I'll fix this by...")

        # Complete
        display.complete()
    """

    def __init__(
        self,
        console: Console,
        title: str = "Thinking",
        max_lines: int = 15,
        show_elapsed: bool = True,
        collapsible: bool = True
    ):
        self.console = console
        self.title = title
        self.max_lines = max_lines
        self.show_elapsed = show_elapsed
        self.collapsible = collapsible

        # State
        self._thoughts: List[ThinkingStep] = []
        self._state = ThinkingState.THINKING
        self._start_time = None
        self._running = False
        self._collapsed = False
        self._lock = threading.Lock()

        # Live display
        self._live: Optional[Live] = None

        # State icons
        self._state_icons = {
            ThinkingState.THINKING: "💭",
            ThinkingState.ANALYZING: "🔍",
            ThinkingState.PLANNING: "📋",
            ThinkingState.REASONING: "🧠",
            ThinkingState.COMPLETE: "✅",
        }

        # State colors
        self._state_colors = {
            ThinkingState.THINKING: "cyan",
            ThinkingState.ANALYZING: "blue",
            ThinkingState.PLANNING: "magenta",
            ThinkingState.REASONING: "yellow",
            ThinkingState.COMPLETE: "green",
        }

    def _get_renderable(self) -> Panel:
        """Get the panel to render"""
        with self._lock:
            # Build content
            lines = []

            if self._collapsed:
                lines.append("[dim]... (collapsed, press 'e' to expand)[/dim]")
            else:
                # Show thoughts
                display_thoughts = self._thoughts[-self.max_lines:] if len(self._thoughts) > self.max_lines else self._thoughts

                if len(self._thoughts) > self.max_lines:
                    hidden = len(self._thoughts) - self.max_lines
                    lines.append(f"[dim]... {hidden} earlier thoughts hidden[/dim]")
                    lines.append("")

                for thought in display_thoughts:
                    # Word wrap long lines
                    wrapped = self._wrap_text(thought.content, 55)
                    for i, line in enumerate(wrapped):
                        if i == 0:
                            state_icon = self._state_icons.get(thought.state, "💭")
                            lines.append(f"[dim]{state_icon}[/dim] {line}")
                        else:
                            lines.append(f"   {line}")

            content = "\n".join(lines) if lines else "[dim]...[/dim]"

            # Build title
            icon = self._state_icons.get(self._state, "💭")
            color = self._state_colors.get(self._state, "cyan")

            title_parts = [f"{icon} {self.title}"]

            if self.show_elapsed and self._start_time:
                elapsed = time.time() - self._start_time
                title_parts.append(f"[dim]{self._format_elapsed(elapsed)}[/dim]")

            title = " · ".join(title_parts)

            return Panel(
                Text.from_markup(content),
                title=f"[bold {color}]{title}[/bold {color}]",
                border_style=color,
                box=ROUNDED,
                padding=(0, 1)
            )

    def _wrap_text(self, text: str, width: int) -> List[str]:
        """Wrap text to specified width"""
        lines = []
        for line in text.split('\n'):
            if len(line) <= width:
                lines.append(line)
            else:
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line) + len(word) + 1 <= width:
                        current_line += (" " if current_line else "") + word
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)
        return lines

    def _format_elapsed(self, seconds: float) -> str:
        """Format elapsed time"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins}m"

    def start(self):
        """Start the thinking display"""
        self._start_time = time.time()
        self._running = True
        self._thoughts = []
        self._state = ThinkingState.THINKING

        self._live = Live(
            self._get_renderable(),
            console=self.console,
            refresh_per_second=4,
            transient=False
        )
        self._live.start()

    def stop(self):
        """Stop the thinking display"""
        self._running = False
        if self._live:
            self._live.stop()
            self._live = None

    def add_thought(self, content: str, state: Optional[ThinkingState] = None):
        """Add a thought to the display"""
        with self._lock:
            thought = ThinkingStep(
                content=content,
                state=state or self._state
            )
            self._thoughts.append(thought)

        if self._live:
            self._live.update(self._get_renderable())

    def add_thoughts(self, thoughts: List[str]):
        """Add multiple thoughts at once"""
        for thought in thoughts:
            self.add_thought(thought)

    def set_state(self, state: ThinkingState):
        """Change the thinking state"""
        with self._lock:
            self._state = state

        if self._live:
            self._live.update(self._get_renderable())

    def set_title(self, title: str):
        """Change the title"""
        with self._lock:
            self.title = title

        if self._live:
            self._live.update(self._get_renderable())

    def toggle_collapse(self):
        """Toggle collapsed state"""
        with self._lock:
            self._collapsed = not self._collapsed

        if self._live:
            self._live.update(self._get_renderable())

    def complete(self, final_thought: Optional[str] = None):
        """Mark thinking as complete"""
        with self._lock:
            self._state = ThinkingState.COMPLETE
            if final_thought:
                self._thoughts.append(ThinkingStep(
                    content=final_thought,
                    state=ThinkingState.COMPLETE
                ))

        if self._live:
            self._live.update(self._get_renderable())
            # Keep displayed briefly then stop
            time.sleep(0.5)
            self.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


class StreamingThinkingDisplay:
    """
    Streaming thinking display that handles character-by-character input.

    Usage:
        with StreamingThinkingDisplay(console) as display:
            for char in thinking_stream:
                display.add_char(char)
    """

    def __init__(
        self,
        console: Console,
        title: str = "Thinking",
        buffer_size: int = 50
    ):
        self.console = console
        self.title = title
        self.buffer_size = buffer_size

        self._buffer = ""
        self._display = ThinkingDisplay(console, title)
        self._last_update = 0

    def start(self):
        """Start streaming display"""
        self._display.start()

    def stop(self):
        """Stop streaming display"""
        # Flush buffer
        if self._buffer:
            self._display.add_thought(self._buffer)
            self._buffer = ""
        self._display.stop()

    def add_char(self, char: str):
        """Add a character to the stream"""
        self._buffer += char

        # Check for natural break points
        if char in '.!?\n' or len(self._buffer) >= self.buffer_size:
            self._flush_buffer()

    def add_text(self, text: str):
        """Add text to the stream"""
        for char in text:
            self.add_char(char)

    def _flush_buffer(self):
        """Flush buffer to display"""
        if self._buffer.strip():
            self._display.add_thought(self._buffer.strip())
        self._buffer = ""

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


class ReasoningChain:
    """
    Display a chain of reasoning steps.

    Usage:
        chain = ReasoningChain(console)
        chain.add_step("First, let me understand the problem...")
        chain.add_step("The key insight is...")
        chain.add_step("Therefore, the solution is...")
        chain.display()
    """

    def __init__(self, console: Console):
        self.console = console
        self._steps: List[str] = []

    def add_step(self, step: str):
        """Add a reasoning step"""
        self._steps.append(step)

    def display(self, title: str = "Reasoning"):
        """Display the reasoning chain"""
        if not self._steps:
            return

        content_lines = []
        for i, step in enumerate(self._steps, 1):
            # Wrap long steps
            wrapped = []
            words = step.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= 55:
                    current_line += (" " if current_line else "") + word
                else:
                    if current_line:
                        wrapped.append(current_line)
                    current_line = word
            if current_line:
                wrapped.append(current_line)

            for j, line in enumerate(wrapped):
                if j == 0:
                    content_lines.append(f"[cyan]{i}.[/cyan] {line}")
                else:
                    content_lines.append(f"   {line}")

        content = "\n".join(content_lines)

        panel = Panel(
            Text.from_markup(content),
            title=f"[bold cyan]🧠 {title}[/bold cyan]",
            border_style="cyan",
            box=ROUNDED,
            padding=(0, 1)
        )

        self.console.print(panel)


def create_thinking_display(
    console: Console,
    title: str = "Thinking",
    streaming: bool = False
) -> ThinkingDisplay:
    """Create a thinking display"""
    if streaming:
        return StreamingThinkingDisplay(console, title)
    return ThinkingDisplay(console, title)
