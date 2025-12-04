"""
BharatBuild CLI Auto-Compact Context

Automatically summarize and compact conversation context when it grows too large.
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.panel import Panel


class MessageRole(str, Enum):
    """Message roles"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class Message:
    """A conversation message"""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompactedSegment:
    """A compacted segment of conversation"""
    summary: str
    original_messages: int
    original_tokens: int
    start_time: datetime
    end_time: datetime
    key_points: List[str] = field(default_factory=list)
    files_mentioned: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)


class ContextCompactor:
    """
    Automatically compacts conversation context to save tokens.

    Strategies:
    1. Summarize old messages
    2. Remove redundant tool outputs
    3. Compress file contents
    4. Keep recent context intact

    Usage:
        compactor = ContextCompactor(console)

        # Add messages
        compactor.add_message(Message(role=MessageRole.USER, content="..."))

        # Check if compaction needed
        if compactor.should_compact(max_tokens=50000):
            compactor.compact()

        # Get context for API
        messages = compactor.get_messages()
    """

    def __init__(
        self,
        console: Console,
        max_context_tokens: int = 100000,
        keep_recent_messages: int = 10,
        keep_recent_tokens: int = 20000
    ):
        self.console = console
        self.max_context_tokens = max_context_tokens
        self.keep_recent_messages = keep_recent_messages
        self.keep_recent_tokens = keep_recent_tokens

        self._messages: List[Message] = []
        self._compacted_segments: List[CompactedSegment] = []
        self._total_tokens = 0

    def add_message(self, message: Message):
        """Add a message to context"""
        # Estimate tokens if not provided
        if message.tokens == 0:
            message.tokens = self._estimate_tokens(message.content)

        self._messages.append(message)
        self._total_tokens += message.tokens

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get messages for API call"""
        result = []

        # Add compacted history as system message
        if self._compacted_segments:
            summary = self._build_compacted_summary()
            result.append({
                "role": "system",
                "content": f"[Conversation History Summary]\n{summary}"
            })

        # Add current messages
        for msg in self._messages:
            result.append({
                "role": msg.role.value,
                "content": msg.content
            })

        return result

    def should_compact(self, max_tokens: int = None) -> bool:
        """Check if compaction is needed"""
        max_tokens = max_tokens or self.max_context_tokens
        return self._total_tokens > max_tokens

    def compact(self, target_tokens: int = None) -> int:
        """
        Compact the context to reduce tokens.

        Returns number of tokens saved.
        """
        if not self._messages:
            return 0

        target_tokens = target_tokens or self.max_context_tokens // 2
        original_tokens = self._total_tokens

        # Strategy 1: Summarize old messages (keep recent)
        tokens_saved = self._summarize_old_messages()

        # Strategy 2: Compress tool outputs
        if self._total_tokens > target_tokens:
            tokens_saved += self._compress_tool_outputs()

        # Strategy 3: Truncate long file contents
        if self._total_tokens > target_tokens:
            tokens_saved += self._truncate_file_contents()

        # Strategy 4: Remove redundant messages
        if self._total_tokens > target_tokens:
            tokens_saved += self._remove_redundant()

        self.console.print(f"[green]✓ Compacted context: saved {tokens_saved:,} tokens[/green]")

        return tokens_saved

    def _summarize_old_messages(self) -> int:
        """Summarize old messages into a compact segment"""
        if len(self._messages) <= self.keep_recent_messages:
            return 0

        # Find messages to compact
        messages_to_compact = self._messages[:-self.keep_recent_messages]
        recent_messages = self._messages[-self.keep_recent_messages:]

        if not messages_to_compact:
            return 0

        # Calculate original tokens
        original_tokens = sum(m.tokens for m in messages_to_compact)

        # Create summary
        summary = self._create_summary(messages_to_compact)

        # Extract key information
        key_points = self._extract_key_points(messages_to_compact)
        files_mentioned = self._extract_files(messages_to_compact)
        tools_used = self._extract_tools(messages_to_compact)

        # Create compacted segment
        segment = CompactedSegment(
            summary=summary,
            original_messages=len(messages_to_compact),
            original_tokens=original_tokens,
            start_time=messages_to_compact[0].timestamp,
            end_time=messages_to_compact[-1].timestamp,
            key_points=key_points,
            files_mentioned=files_mentioned,
            tools_used=tools_used
        )

        self._compacted_segments.append(segment)

        # Update messages
        self._messages = recent_messages

        # Update token count
        summary_tokens = self._estimate_tokens(summary)
        tokens_saved = original_tokens - summary_tokens
        self._total_tokens -= tokens_saved

        return tokens_saved

    def _compress_tool_outputs(self) -> int:
        """Compress verbose tool outputs"""
        tokens_saved = 0

        for msg in self._messages:
            if msg.role == MessageRole.TOOL:
                original_tokens = msg.tokens
                msg.content = self._compress_output(msg.content)
                msg.tokens = self._estimate_tokens(msg.content)
                tokens_saved += original_tokens - msg.tokens

        self._total_tokens -= tokens_saved
        return tokens_saved

    def _truncate_file_contents(self) -> int:
        """Truncate long file contents in messages"""
        tokens_saved = 0

        for msg in self._messages:
            # Look for file content patterns
            if "```" in msg.content and len(msg.content) > 5000:
                original_tokens = msg.tokens
                msg.content = self._truncate_code_blocks(msg.content)
                msg.tokens = self._estimate_tokens(msg.content)
                tokens_saved += original_tokens - msg.tokens

        self._total_tokens -= tokens_saved
        return tokens_saved

    def _remove_redundant(self) -> int:
        """Remove redundant messages"""
        tokens_saved = 0
        new_messages = []

        seen_contents = set()

        for msg in self._messages:
            # Skip exact duplicates
            content_hash = hash(msg.content[:500])  # Hash first 500 chars
            if content_hash in seen_contents:
                tokens_saved += msg.tokens
                continue

            seen_contents.add(content_hash)
            new_messages.append(msg)

        self._messages = new_messages
        self._total_tokens -= tokens_saved

        return tokens_saved

    def _create_summary(self, messages: List[Message]) -> str:
        """Create a summary of messages"""
        parts = []

        # Group by topic/task
        user_requests = []
        assistant_actions = []

        for msg in messages:
            if msg.role == MessageRole.USER:
                # Extract main request
                request = msg.content[:200]
                if len(msg.content) > 200:
                    request += "..."
                user_requests.append(request)

            elif msg.role == MessageRole.ASSISTANT:
                # Extract action summaries
                actions = self._extract_actions(msg.content)
                assistant_actions.extend(actions)

        if user_requests:
            parts.append("User requested: " + "; ".join(user_requests[:5]))

        if assistant_actions:
            parts.append("Actions taken: " + "; ".join(assistant_actions[:10]))

        return "\n".join(parts)

    def _extract_actions(self, content: str) -> List[str]:
        """Extract action summaries from assistant response"""
        actions = []

        # Look for common action patterns
        patterns = [
            r"created?\s+(?:file\s+)?['\"]?([^'\"]+)['\"]?",
            r"modified?\s+(?:file\s+)?['\"]?([^'\"]+)['\"]?",
            r"ran?\s+(?:command\s+)?[`']([^`']+)[`']",
            r"read\s+(?:file\s+)?['\"]?([^'\"]+)['\"]?",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches[:3]:  # Limit matches
                actions.append(match)

        return actions

    def _extract_key_points(self, messages: List[Message]) -> List[str]:
        """Extract key points from messages"""
        points = []

        for msg in messages:
            if msg.role == MessageRole.ASSISTANT:
                # Look for bullet points or numbered items
                bullet_pattern = r'^[\s]*[-*•]\s+(.+)$'
                numbered_pattern = r'^[\s]*\d+\.\s+(.+)$'

                for line in msg.content.split('\n'):
                    match = re.match(bullet_pattern, line) or re.match(numbered_pattern, line)
                    if match and len(points) < 10:
                        points.append(match.group(1).strip())

        return points

    def _extract_files(self, messages: List[Message]) -> List[str]:
        """Extract mentioned file paths"""
        files = set()

        file_pattern = r'[\'"`]([^\'"`]+\.[a-zA-Z]{1,5})[\'"`]'

        for msg in messages:
            matches = re.findall(file_pattern, msg.content)
            for match in matches:
                if '/' in match or '\\' in match:
                    files.add(match)

        return list(files)[:20]  # Limit to 20 files

    def _extract_tools(self, messages: List[Message]) -> List[str]:
        """Extract tools used"""
        tools = set()

        for msg in messages:
            if msg.role == MessageRole.TOOL:
                # Try to extract tool name from metadata
                tool_name = msg.metadata.get("tool_name", "")
                if tool_name:
                    tools.add(tool_name)

        return list(tools)

    def _compress_output(self, content: str, max_lines: int = 20) -> str:
        """Compress verbose output"""
        lines = content.split('\n')

        if len(lines) <= max_lines:
            return content

        # Keep first and last lines
        keep_start = max_lines // 2
        keep_end = max_lines - keep_start

        result_lines = lines[:keep_start]
        result_lines.append(f"... ({len(lines) - max_lines} lines truncated) ...")
        result_lines.extend(lines[-keep_end:])

        return '\n'.join(result_lines)

    def _truncate_code_blocks(self, content: str, max_code_lines: int = 50) -> str:
        """Truncate code blocks in content"""
        def truncate_block(match):
            lang = match.group(1) or ""
            code = match.group(2)
            lines = code.split('\n')

            if len(lines) <= max_code_lines:
                return match.group(0)

            # Keep first and last lines
            keep = max_code_lines // 2
            truncated = lines[:keep] + [f"... ({len(lines) - max_code_lines} lines) ..."] + lines[-keep:]

            return f"```{lang}\n{chr(10).join(truncated)}\n```"

        pattern = r'```(\w*)\n(.*?)```'
        return re.sub(pattern, truncate_block, content, flags=re.DOTALL)

    def _build_compacted_summary(self) -> str:
        """Build summary from all compacted segments"""
        parts = []

        for segment in self._compacted_segments:
            parts.append(f"[{segment.start_time.strftime('%H:%M')} - {segment.end_time.strftime('%H:%M')}]")
            parts.append(segment.summary)

            if segment.files_mentioned:
                parts.append(f"Files: {', '.join(segment.files_mentioned[:5])}")

            if segment.key_points:
                parts.append("Key points: " + "; ".join(segment.key_points[:3]))

            parts.append("")

        return "\n".join(parts)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        # Rough estimate: ~4 characters per token for English
        return len(text) // 4

    # ==================== Stats & Display ====================

    def get_stats(self) -> Dict[str, Any]:
        """Get compaction statistics"""
        return {
            "total_messages": len(self._messages),
            "total_tokens": self._total_tokens,
            "compacted_segments": len(self._compacted_segments),
            "compacted_messages": sum(s.original_messages for s in self._compacted_segments),
            "tokens_saved": sum(s.original_tokens for s in self._compacted_segments) - sum(
                self._estimate_tokens(s.summary) for s in self._compacted_segments
            )
        }

    def show_status(self):
        """Display compaction status"""
        stats = self.get_stats()

        content_lines = []
        content_lines.append(f"[bold]Current Messages:[/bold] {stats['total_messages']}")
        content_lines.append(f"[bold]Current Tokens:[/bold] {stats['total_tokens']:,}")
        content_lines.append(f"[bold]Max Tokens:[/bold] {self.max_context_tokens:,}")
        content_lines.append("")
        content_lines.append(f"[bold]Compacted Segments:[/bold] {stats['compacted_segments']}")
        content_lines.append(f"[bold]Compacted Messages:[/bold] {stats['compacted_messages']}")
        content_lines.append(f"[bold]Tokens Saved:[/bold] {stats['tokens_saved']:,}")

        # Progress bar
        usage_percent = (stats['total_tokens'] / self.max_context_tokens) * 100
        bar_width = 30
        filled = int(bar_width * min(usage_percent, 100) / 100)
        bar = "█" * filled + "░" * (bar_width - filled)

        if usage_percent < 50:
            color = "green"
        elif usage_percent < 80:
            color = "yellow"
        else:
            color = "red"

        content_lines.append("")
        content_lines.append(f"[{color}]{bar}[/{color}] {usage_percent:.1f}%")

        content = "\n".join(content_lines)

        panel = Panel(
            content,
            title="[bold cyan]Context Status[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

    def clear(self):
        """Clear all context"""
        self._messages.clear()
        self._compacted_segments.clear()
        self._total_tokens = 0
        self.console.print("[green]✓ Context cleared[/green]")


class SmartContextManager:
    """
    High-level context manager that combines compaction with intelligent context selection.

    Usage:
        manager = SmartContextManager(console)

        # Add messages
        manager.add_user_message("Build a todo app")
        manager.add_assistant_message("I'll create...")

        # Get context for next request
        context = manager.get_context_for_request(max_tokens=50000)
    """

    def __init__(
        self,
        console: Console,
        max_context_tokens: int = 100000
    ):
        self.console = console
        self.compactor = ContextCompactor(
            console=console,
            max_context_tokens=max_context_tokens
        )

    def add_user_message(self, content: str):
        """Add user message"""
        self.compactor.add_message(Message(
            role=MessageRole.USER,
            content=content
        ))

    def add_assistant_message(self, content: str):
        """Add assistant message"""
        self.compactor.add_message(Message(
            role=MessageRole.ASSISTANT,
            content=content
        ))

    def add_tool_result(self, tool_name: str, result: str):
        """Add tool result"""
        self.compactor.add_message(Message(
            role=MessageRole.TOOL,
            content=result,
            metadata={"tool_name": tool_name}
        ))

    def get_context_for_request(self, max_tokens: int = 50000) -> List[Dict]:
        """Get optimized context for API request"""
        # Auto-compact if needed
        if self.compactor.should_compact(max_tokens):
            self.compactor.compact(target_tokens=max_tokens // 2)

        return self.compactor.get_messages()

    def show_status(self):
        """Show context status"""
        self.compactor.show_status()

    def clear(self):
        """Clear context"""
        self.compactor.clear()
