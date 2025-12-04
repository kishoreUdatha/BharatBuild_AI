"""
BharatBuild CLI Memory/Context Persistence

Provides persistent memory across sessions:
  /memory add "User prefers TypeScript over JavaScript"
  /memory list
  /memory search "preferences"
  /memory clear
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class MemoryType(str, Enum):
    """Types of memories"""
    FACT = "fact"           # User facts/preferences
    PROJECT = "project"     # Project-specific context
    CODE = "code"           # Code patterns/snippets
    INSTRUCTION = "instruction"  # User instructions
    CORRECTION = "correction"    # Corrections/clarifications
    SUMMARY = "summary"     # Conversation summaries


class MemoryPriority(str, Enum):
    """Priority levels for memories"""
    HIGH = "high"       # Always include
    MEDIUM = "medium"   # Include when relevant
    LOW = "low"         # Include if space allows


@dataclass
class Memory:
    """A single memory entry"""
    id: str
    content: str
    memory_type: MemoryType
    priority: MemoryPriority = MemoryPriority.MEDIUM
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0
    last_accessed: Optional[str] = None
    source: str = ""  # Where this memory came from
    project_id: Optional[str] = None  # Project-specific memory
    expires_at: Optional[str] = None  # Optional expiration


@dataclass
class MemoryStats:
    """Statistics about memory usage"""
    total_memories: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_priority: Dict[str, int] = field(default_factory=dict)
    total_tokens_estimate: int = 0


class MemoryManager:
    """
    Manages persistent memory across sessions.

    Usage:
        memory = MemoryManager(console, config_dir)

        # Add a memory
        memory.add("User prefers dark mode", MemoryType.FACT)

        # Search memories
        results = memory.search("preferences")

        # Get context for prompt
        context = memory.get_context_string(max_tokens=2000)
    """

    def __init__(
        self,
        console: Console,
        config_dir: Optional[Path] = None,
        project_id: Optional[str] = None,
        max_memories: int = 500
    ):
        self.console = console
        self.config_dir = config_dir or (Path.home() / ".bharatbuild" / "memory")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.project_id = project_id
        self.max_memories = max_memories

        self._memories: Dict[str, Memory] = {}
        self._load_memories()

    def _get_memory_file(self) -> Path:
        """Get memory file path"""
        return self.config_dir / "memories.json"

    def _get_project_memory_file(self) -> Optional[Path]:
        """Get project-specific memory file"""
        if self.project_id:
            return self.config_dir / f"project_{self.project_id}.json"
        return None

    def _load_memories(self):
        """Load memories from disk"""
        # Load global memories
        self._load_from_file(self._get_memory_file())

        # Load project memories
        project_file = self._get_project_memory_file()
        if project_file:
            self._load_from_file(project_file)

    def _load_from_file(self, path: Path):
        """Load memories from a specific file"""
        if not path or not path.exists():
            return

        try:
            with open(path) as f:
                data = json.load(f)

            for mem_data in data.get("memories", []):
                memory = Memory(
                    id=mem_data["id"],
                    content=mem_data["content"],
                    memory_type=MemoryType(mem_data.get("memory_type", "fact")),
                    priority=MemoryPriority(mem_data.get("priority", "medium")),
                    tags=mem_data.get("tags", []),
                    created_at=mem_data.get("created_at", ""),
                    updated_at=mem_data.get("updated_at", ""),
                    access_count=mem_data.get("access_count", 0),
                    last_accessed=mem_data.get("last_accessed"),
                    source=mem_data.get("source", ""),
                    project_id=mem_data.get("project_id"),
                    expires_at=mem_data.get("expires_at")
                )
                self._memories[memory.id] = memory

        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not load memories: {e}[/yellow]")

    def _save_memories(self):
        """Save memories to disk"""
        # Separate global and project memories
        global_memories = []
        project_memories = []

        for memory in self._memories.values():
            mem_data = {
                "id": memory.id,
                "content": memory.content,
                "memory_type": memory.memory_type.value,
                "priority": memory.priority.value,
                "tags": memory.tags,
                "created_at": memory.created_at,
                "updated_at": memory.updated_at,
                "access_count": memory.access_count,
                "last_accessed": memory.last_accessed,
                "source": memory.source,
                "project_id": memory.project_id,
                "expires_at": memory.expires_at
            }

            if memory.project_id == self.project_id and self.project_id:
                project_memories.append(mem_data)
            else:
                global_memories.append(mem_data)

        # Save global memories
        try:
            with open(self._get_memory_file(), 'w') as f:
                json.dump({"memories": global_memories}, f, indent=2)
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not save memories: {e}[/yellow]")

        # Save project memories
        project_file = self._get_project_memory_file()
        if project_file and project_memories:
            try:
                with open(project_file, 'w') as f:
                    json.dump({"memories": project_memories}, f, indent=2)
            except Exception:
                pass

    def _generate_id(self, content: str) -> str:
        """Generate unique ID for memory"""
        hash_input = f"{content}{datetime.now().isoformat()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: ~4 chars per token)"""
        return len(text) // 4

    # ==================== Memory Operations ====================

    def add(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.FACT,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        tags: Optional[List[str]] = None,
        source: str = "user",
        project_specific: bool = False
    ) -> Memory:
        """Add a new memory"""
        # Check for duplicates
        for existing in self._memories.values():
            if existing.content.lower() == content.lower():
                # Update existing
                existing.access_count += 1
                existing.updated_at = datetime.now().isoformat()
                self._save_memories()
                return existing

        # Create new memory
        memory = Memory(
            id=self._generate_id(content),
            content=content,
            memory_type=memory_type,
            priority=priority,
            tags=tags or [],
            source=source,
            project_id=self.project_id if project_specific else None
        )

        self._memories[memory.id] = memory

        # Trim if needed
        self._trim_memories()

        self._save_memories()
        return memory

    def update(
        self,
        memory_id: str,
        content: Optional[str] = None,
        priority: Optional[MemoryPriority] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Update an existing memory"""
        if memory_id not in self._memories:
            return False

        memory = self._memories[memory_id]

        if content:
            memory.content = content
        if priority:
            memory.priority = priority
        if tags is not None:
            memory.tags = tags

        memory.updated_at = datetime.now().isoformat()
        self._save_memories()

        return True

    def delete(self, memory_id: str) -> bool:
        """Delete a memory"""
        if memory_id not in self._memories:
            return False

        del self._memories[memory_id]
        self._save_memories()
        return True

    def get(self, memory_id: str) -> Optional[Memory]:
        """Get a memory by ID"""
        memory = self._memories.get(memory_id)
        if memory:
            memory.access_count += 1
            memory.last_accessed = datetime.now().isoformat()
        return memory

    def search(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Memory]:
        """Search memories"""
        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for memory in self._memories.values():
            # Filter by type
            if memory_type and memory.memory_type != memory_type:
                continue

            # Filter by tags
            if tags and not any(t in memory.tags for t in tags):
                continue

            # Match content
            content_lower = memory.content.lower()
            if query_lower in content_lower:
                results.append((memory, 100))  # Exact match
            elif any(word in content_lower for word in query_words):
                # Partial match - score by word matches
                matches = sum(1 for word in query_words if word in content_lower)
                results.append((memory, matches * 10))

        # Sort by score, then by priority, then by access count
        priority_order = {MemoryPriority.HIGH: 0, MemoryPriority.MEDIUM: 1, MemoryPriority.LOW: 2}
        results.sort(key=lambda x: (-x[1], priority_order[x[0].priority], -x[0].access_count))

        return [r[0] for r in results[:limit]]

    def get_all(
        self,
        memory_type: Optional[MemoryType] = None,
        priority: Optional[MemoryPriority] = None,
        project_only: bool = False
    ) -> List[Memory]:
        """Get all memories with optional filters"""
        memories = list(self._memories.values())

        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]

        if priority:
            memories = [m for m in memories if m.priority == priority]

        if project_only and self.project_id:
            memories = [m for m in memories if m.project_id == self.project_id]

        return memories

    def clear(self, project_only: bool = False):
        """Clear memories"""
        if project_only and self.project_id:
            self._memories = {
                k: v for k, v in self._memories.items()
                if v.project_id != self.project_id
            }
        else:
            self._memories = {}

        self._save_memories()

    def _trim_memories(self):
        """Trim old/low priority memories if over limit"""
        if len(self._memories) <= self.max_memories:
            return

        # Sort by priority, then by last access
        memories = list(self._memories.values())
        priority_order = {MemoryPriority.LOW: 0, MemoryPriority.MEDIUM: 1, MemoryPriority.HIGH: 2}

        memories.sort(key=lambda m: (
            priority_order[m.priority],
            m.last_accessed or m.created_at
        ))

        # Remove oldest low-priority memories
        to_remove = len(memories) - self.max_memories
        for memory in memories[:to_remove]:
            del self._memories[memory.id]

    # ==================== Context Generation ====================

    def get_context_string(
        self,
        max_tokens: int = 2000,
        include_types: Optional[List[MemoryType]] = None,
        query: Optional[str] = None
    ) -> str:
        """
        Generate context string for including in prompts.

        Returns formatted memory context within token limit.
        """
        # Get relevant memories
        if query:
            memories = self.search(query, limit=50)
        else:
            memories = self.get_all()

        # Filter by types
        if include_types:
            memories = [m for m in memories if m.memory_type in include_types]

        # Sort by priority
        priority_order = {MemoryPriority.HIGH: 0, MemoryPriority.MEDIUM: 1, MemoryPriority.LOW: 2}
        memories.sort(key=lambda m: (priority_order[m.priority], -m.access_count))

        # Build context string within token limit
        lines = []
        total_tokens = 0

        # Add high priority first
        for memory in memories:
            line = f"- {memory.content}"
            tokens = self._estimate_tokens(line)

            if total_tokens + tokens > max_tokens:
                break

            lines.append(line)
            total_tokens += tokens

            # Mark as accessed
            memory.access_count += 1
            memory.last_accessed = datetime.now().isoformat()

        if not lines:
            return ""

        return "## Memory Context\n" + "\n".join(lines)

    def get_relevant_context(
        self,
        prompt: str,
        max_tokens: int = 1500
    ) -> str:
        """Get context relevant to a specific prompt"""
        # Extract keywords from prompt
        words = set(re.findall(r'\b\w{3,}\b', prompt.lower()))

        # Find relevant memories
        relevant = []
        for memory in self._memories.values():
            content_words = set(re.findall(r'\b\w{3,}\b', memory.content.lower()))
            overlap = len(words & content_words)

            if overlap > 0 or memory.priority == MemoryPriority.HIGH:
                score = overlap * 10
                if memory.priority == MemoryPriority.HIGH:
                    score += 50
                relevant.append((memory, score))

        # Sort by relevance
        relevant.sort(key=lambda x: -x[1])

        # Build context
        lines = []
        total_tokens = 0

        for memory, score in relevant:
            line = f"- {memory.content}"
            tokens = self._estimate_tokens(line)

            if total_tokens + tokens > max_tokens:
                break

            lines.append(line)
            total_tokens += tokens

        if not lines:
            return ""

        return "## Relevant Context\n" + "\n".join(lines)

    # ==================== Auto-learning ====================

    def learn_from_conversation(
        self,
        user_message: str,
        assistant_response: str
    ):
        """
        Automatically extract memories from conversation.

        Looks for:
        - User preferences ("I prefer...", "I like...", "I always...")
        - Corrections ("Actually...", "No, I meant...")
        - Project context ("This project uses...", "We're building...")
        """
        # Preference patterns
        preference_patterns = [
            r"I (?:prefer|like|want|always|usually|never)\s+(.+?)(?:\.|$)",
            r"(?:please |always |never )(.+?)(?:\.|$)",
            r"my (?:preference|style|approach) is\s+(.+?)(?:\.|$)",
        ]

        for pattern in preference_patterns:
            matches = re.findall(pattern, user_message, re.IGNORECASE)
            for match in matches:
                if len(match) > 10:  # Meaningful content
                    self.add(
                        f"User preference: {match.strip()}",
                        MemoryType.FACT,
                        MemoryPriority.MEDIUM,
                        tags=["auto", "preference"],
                        source="auto_learn"
                    )

        # Correction patterns
        correction_patterns = [
            r"(?:actually|no,? I meant|that's not right)\s*[,:]?\s*(.+?)(?:\.|$)",
        ]

        for pattern in correction_patterns:
            matches = re.findall(pattern, user_message, re.IGNORECASE)
            for match in matches:
                if len(match) > 10:
                    self.add(
                        f"Correction: {match.strip()}",
                        MemoryType.CORRECTION,
                        MemoryPriority.HIGH,
                        tags=["auto", "correction"],
                        source="auto_learn"
                    )

    # ==================== Display ====================

    def show_memories(
        self,
        memory_type: Optional[MemoryType] = None,
        limit: int = 20
    ):
        """Display memories"""
        memories = self.get_all(memory_type=memory_type)[:limit]

        if not memories:
            self.console.print("[dim]No memories stored[/dim]")
            return

        table = Table(title="Memories", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim", width=8)
        table.add_column("Type", width=12)
        table.add_column("Priority", width=8)
        table.add_column("Content")
        table.add_column("Tags", style="dim")

        for memory in memories:
            priority_colors = {
                MemoryPriority.HIGH: "red",
                MemoryPriority.MEDIUM: "yellow",
                MemoryPriority.LOW: "dim"
            }

            table.add_row(
                memory.id[:8],
                memory.memory_type.value,
                f"[{priority_colors[memory.priority]}]{memory.priority.value}[/{priority_colors[memory.priority]}]",
                memory.content[:50] + "..." if len(memory.content) > 50 else memory.content,
                ", ".join(memory.tags[:3])
            )

        self.console.print(table)

        if len(self._memories) > limit:
            self.console.print(f"[dim]Showing {limit} of {len(self._memories)} memories[/dim]")

    def show_stats(self):
        """Show memory statistics"""
        stats = MemoryStats()
        stats.total_memories = len(self._memories)

        for memory in self._memories.values():
            # By type
            type_key = memory.memory_type.value
            stats.by_type[type_key] = stats.by_type.get(type_key, 0) + 1

            # By priority
            priority_key = memory.priority.value
            stats.by_priority[priority_key] = stats.by_priority.get(priority_key, 0) + 1

            # Token estimate
            stats.total_tokens_estimate += self._estimate_tokens(memory.content)

        content_lines = []
        content_lines.append(f"[bold]Total Memories:[/bold] {stats.total_memories}")
        content_lines.append(f"[bold]Est. Tokens:[/bold] ~{stats.total_tokens_estimate:,}")
        content_lines.append("")

        content_lines.append("[bold]By Type:[/bold]")
        for type_name, count in sorted(stats.by_type.items()):
            content_lines.append(f"  {type_name}: {count}")

        content_lines.append("")
        content_lines.append("[bold]By Priority:[/bold]")
        for priority, count in sorted(stats.by_priority.items()):
            content_lines.append(f"  {priority}: {count}")

        content = "\n".join(content_lines)

        panel = Panel(
            Text.from_markup(content),
            title="[bold cyan]Memory Statistics[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

    def show_help(self):
        """Show help for memory commands"""
        help_text = """
[bold cyan]Memory System[/bold cyan]

Persistent memory across sessions for context and preferences.

[bold]Commands:[/bold]
  [green]/memory list[/green]              List all memories
  [green]/memory add <text>[/green]        Add a new memory
  [green]/memory search <query>[/green]    Search memories
  [green]/memory delete <id>[/green]       Delete a memory
  [green]/memory clear[/green]             Clear all memories
  [green]/memory stats[/green]             Show statistics

[bold]Memory Types:[/bold]
  • fact        - User facts/preferences
  • project     - Project-specific context
  • code        - Code patterns/snippets
  • instruction - User instructions
  • correction  - Corrections/clarifications

[bold]Priority Levels:[/bold]
  • high   - Always included in context
  • medium - Included when relevant
  • low    - Included if space allows

[bold]Examples:[/bold]
  /memory add "I prefer TypeScript over JavaScript" --type fact --priority high
  /memory search "typescript"
  /memory list --type fact
"""
        panel = Panel(
            Text.from_markup(help_text),
            title="[bold]Memory Help[/bold]",
            border_style="cyan"
        )
        self.console.print(panel)
