"""
BharatBuild CLI Output Streaming Modes

Control how AI responses are streamed:
  /stream on         Enable streaming
  /stream off        Disable streaming
  /stream mode <m>   Set streaming mode
"""

import sys
import time
import asyncio
from typing import Optional, Dict, Any, Callable, AsyncGenerator, Generator
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown


class StreamMode(str, Enum):
    """Streaming display modes"""
    NONE = "none"           # No streaming, wait for complete response
    CHARACTER = "character" # Stream character by character
    WORD = "word"           # Stream word by word
    LINE = "line"           # Stream line by line
    CHUNK = "chunk"         # Stream in chunks (default)
    MARKDOWN = "markdown"   # Stream with live markdown rendering


@dataclass
class StreamConfig:
    """Streaming configuration"""
    enabled: bool = True
    mode: StreamMode = StreamMode.CHUNK
    chunk_size: int = 10          # Characters per chunk
    delay_ms: int = 0             # Delay between chunks (0 = no delay)
    show_cursor: bool = True      # Show blinking cursor while streaming
    render_markdown: bool = True  # Render markdown in final output
    typewriter_effect: bool = False  # Simulate typewriter


class StreamRenderer(ABC):
    """Base class for stream renderers"""

    @abstractmethod
    def start(self):
        """Start streaming"""
        pass

    @abstractmethod
    def update(self, content: str):
        """Update with new content"""
        pass

    @abstractmethod
    def finish(self):
        """Finish streaming"""
        pass


class CharacterStreamRenderer(StreamRenderer):
    """Render stream character by character"""

    def __init__(self, console: Console, config: StreamConfig):
        self.console = console
        self.config = config
        self._buffer = ""

    def start(self):
        self._buffer = ""

    def update(self, content: str):
        new_chars = content[len(self._buffer):]
        for char in new_chars:
            self.console.print(char, end="")
            if self.config.delay_ms > 0:
                time.sleep(self.config.delay_ms / 1000)
        self._buffer = content

    def finish(self):
        self.console.print()  # New line


class WordStreamRenderer(StreamRenderer):
    """Render stream word by word"""

    def __init__(self, console: Console, config: StreamConfig):
        self.console = console
        self.config = config
        self._words_shown = 0

    def start(self):
        self._words_shown = 0

    def update(self, content: str):
        words = content.split()
        new_words = words[self._words_shown:]

        for word in new_words:
            self.console.print(word, end=" ")
            if self.config.delay_ms > 0:
                time.sleep(self.config.delay_ms / 1000)

        self._words_shown = len(words)

    def finish(self):
        self.console.print()


class LineStreamRenderer(StreamRenderer):
    """Render stream line by line"""

    def __init__(self, console: Console, config: StreamConfig):
        self.console = console
        self.config = config
        self._lines_shown = 0

    def start(self):
        self._lines_shown = 0

    def update(self, content: str):
        lines = content.split('\n')
        new_lines = lines[self._lines_shown:]

        for line in new_lines[:-1]:  # Don't print incomplete last line
            self.console.print(line)
            if self.config.delay_ms > 0:
                time.sleep(self.config.delay_ms / 1000)

        self._lines_shown = len(lines) - 1

    def finish(self):
        # Print any remaining content
        pass


class ChunkStreamRenderer(StreamRenderer):
    """Render stream in chunks"""

    def __init__(self, console: Console, config: StreamConfig):
        self.console = console
        self.config = config
        self._buffer = ""

    def start(self):
        self._buffer = ""

    def update(self, content: str):
        new_content = content[len(self._buffer):]
        self.console.print(new_content, end="")
        self._buffer = content

    def finish(self):
        self.console.print()


class MarkdownStreamRenderer(StreamRenderer):
    """Render stream with live markdown"""

    def __init__(self, console: Console, config: StreamConfig):
        self.console = console
        self.config = config
        self._content = ""
        self._live: Optional[Live] = None

    def start(self):
        self._content = ""
        self._live = Live(
            Text(""),
            console=self.console,
            refresh_per_second=10,
            transient=True
        )
        self._live.start()

    def update(self, content: str):
        self._content = content
        if self._live:
            # Render markdown
            try:
                md = Markdown(content)
                self._live.update(md)
            except Exception:
                self._live.update(Text(content))

    def finish(self):
        if self._live:
            self._live.stop()

        # Final render with markdown
        if self._content:
            try:
                md = Markdown(self._content)
                self.console.print(md)
            except Exception:
                self.console.print(self._content)


class TypewriterRenderer(StreamRenderer):
    """Typewriter effect renderer"""

    def __init__(self, console: Console, config: StreamConfig):
        self.console = console
        self.config = config
        self._buffer = ""

    def start(self):
        self._buffer = ""

    def update(self, content: str):
        new_chars = content[len(self._buffer):]

        for char in new_chars:
            self.console.print(char, end="")
            # Variable delay for typewriter effect
            if char in '.!?':
                time.sleep(0.3)
            elif char == ',':
                time.sleep(0.15)
            elif char == ' ':
                time.sleep(0.05)
            else:
                time.sleep(0.02)

        self._buffer = content

    def finish(self):
        self.console.print()


class StreamManager:
    """
    Manages output streaming.

    Usage:
        manager = StreamManager(console)

        # Stream a response
        async for chunk in get_response_stream():
            manager.stream(chunk)

        # Or use context manager
        with manager.streaming() as stream:
            for chunk in chunks:
                stream.update(chunk)
    """

    def __init__(self, console: Console, config: StreamConfig = None):
        self.console = console
        self.config = config or StreamConfig()
        self._renderer: Optional[StreamRenderer] = None

    def get_renderer(self) -> StreamRenderer:
        """Get appropriate renderer for current mode"""
        renderers = {
            StreamMode.CHARACTER: CharacterStreamRenderer,
            StreamMode.WORD: WordStreamRenderer,
            StreamMode.LINE: LineStreamRenderer,
            StreamMode.CHUNK: ChunkStreamRenderer,
            StreamMode.MARKDOWN: MarkdownStreamRenderer,
        }

        if self.config.typewriter_effect:
            return TypewriterRenderer(self.console, self.config)

        renderer_class = renderers.get(self.config.mode, ChunkStreamRenderer)
        return renderer_class(self.console, self.config)

    def set_mode(self, mode: StreamMode):
        """Set streaming mode"""
        self.config.mode = mode
        self.console.print(f"[green]✓ Streaming mode: {mode.value}[/green]")

    def enable(self):
        """Enable streaming"""
        self.config.enabled = True
        self.console.print("[green]✓ Streaming enabled[/green]")

    def disable(self):
        """Disable streaming"""
        self.config.enabled = False
        self.console.print("[green]✓ Streaming disabled[/green]")

    def toggle(self) -> bool:
        """Toggle streaming"""
        self.config.enabled = not self.config.enabled
        status = "enabled" if self.config.enabled else "disabled"
        self.console.print(f"[green]✓ Streaming {status}[/green]")
        return self.config.enabled

    # ==================== Streaming Methods ====================

    def start_stream(self):
        """Start a new stream"""
        if not self.config.enabled:
            return

        self._renderer = self.get_renderer()
        self._renderer.start()

    def stream(self, content: str):
        """Stream content"""
        if not self.config.enabled or not self._renderer:
            return

        self._renderer.update(content)

    def end_stream(self):
        """End the current stream"""
        if self._renderer:
            self._renderer.finish()
            self._renderer = None

    def stream_complete(self, content: str):
        """Stream complete content at once"""
        if not self.config.enabled:
            self.console.print(content)
            return

        self.start_stream()
        self.stream(content)
        self.end_stream()

    # ==================== Context Manager ====================

    class StreamContext:
        """Context manager for streaming"""

        def __init__(self, manager: 'StreamManager'):
            self.manager = manager
            self._content = ""

        def __enter__(self):
            self.manager.start_stream()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.manager.end_stream()
            return False

        def update(self, content: str):
            """Update with full content"""
            self._content = content
            self.manager.stream(content)

        def append(self, chunk: str):
            """Append chunk to content"""
            self._content += chunk
            self.manager.stream(self._content)

    def streaming(self) -> StreamContext:
        """Get streaming context manager"""
        return self.StreamContext(self)

    # ==================== Async Streaming ====================

    async def stream_async(self, generator: AsyncGenerator[str, None]):
        """Stream from async generator"""
        if not self.config.enabled:
            # Collect all and print at once
            content = ""
            async for chunk in generator:
                content += chunk
            self.console.print(content)
            return

        self.start_stream()
        content = ""

        try:
            async for chunk in generator:
                content += chunk
                self.stream(content)
        finally:
            self.end_stream()

    def stream_sync(self, generator: Generator[str, None, None]):
        """Stream from sync generator"""
        if not self.config.enabled:
            content = "".join(generator)
            self.console.print(content)
            return

        self.start_stream()
        content = ""

        try:
            for chunk in generator:
                content += chunk
                self.stream(content)
        finally:
            self.end_stream()

    # ==================== Display ====================

    def show_status(self):
        """Show streaming status"""
        content_lines = []

        status = "[green]Enabled[/green]" if self.config.enabled else "[dim]Disabled[/dim]"
        content_lines.append(f"[bold]Status:[/bold] {status}")
        content_lines.append(f"[bold]Mode:[/bold] {self.config.mode.value}")
        content_lines.append(f"[bold]Chunk size:[/bold] {self.config.chunk_size}")

        if self.config.delay_ms > 0:
            content_lines.append(f"[bold]Delay:[/bold] {self.config.delay_ms}ms")

        content_lines.append(f"[bold]Typewriter:[/bold] {'Yes' if self.config.typewriter_effect else 'No'}")
        content_lines.append(f"[bold]Markdown:[/bold] {'Yes' if self.config.render_markdown else 'No'}")

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title="[bold cyan]Streaming Settings[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

    def show_modes(self):
        """Show available streaming modes"""
        self.console.print("\n[bold cyan]Streaming Modes[/bold cyan]\n")

        modes = [
            ("none", "No streaming, wait for complete response"),
            ("character", "Stream character by character"),
            ("word", "Stream word by word"),
            ("line", "Stream line by line"),
            ("chunk", "Stream in chunks (default)"),
            ("markdown", "Stream with live markdown rendering"),
        ]

        for mode, desc in modes:
            indicator = "[green]►[/green]" if mode == self.config.mode.value else " "
            self.console.print(f"  {indicator} [bold]{mode}[/bold] - {desc}")

    def demo(self):
        """Demo current streaming mode"""
        demo_text = """This is a demonstration of the streaming output.

The text will appear according to the current streaming mode.

**Features:**
- Real-time output
- Multiple modes available
- Markdown rendering support

```python
def hello():
    print("Hello from BharatBuild!")
```

Thank you for using BharatBuild AI!
"""

        self.console.print(f"\n[cyan]Demo: {self.config.mode.value} mode[/cyan]\n")
        self.stream_complete(demo_text)

    def show_help(self):
        """Show streaming help"""
        help_text = """
[bold cyan]Streaming Commands[/bold cyan]

Control how AI responses are displayed.

[bold]Commands:[/bold]
  [green]/stream[/green]              Show streaming status
  [green]/stream on[/green]           Enable streaming
  [green]/stream off[/green]          Disable streaming
  [green]/stream mode <m>[/green]     Set streaming mode
  [green]/stream demo[/green]         Demo current mode
  [green]/stream modes[/green]        List available modes

[bold]Modes:[/bold]
  • none      - Wait for complete response
  • character - Character by character
  • word      - Word by word
  • line      - Line by line
  • chunk     - Chunks (default)
  • markdown  - Live markdown rendering

[bold]Settings:[/bold]
  /stream delay <ms>     Set delay between chunks
  /stream typewriter     Toggle typewriter effect

[bold]Examples:[/bold]
  /stream mode markdown
  /stream delay 50
  /stream typewriter on
"""
        self.console.print(help_text)
