"""
Session Manager - Handles conversation persistence and history

Allows resuming previous sessions like Claude Code.
"""

import json
import os
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

from cli.config import CLIConfig


@dataclass
class SessionMessage:
    """A message in the session"""
    role: str
    content: str
    timestamp: float
    tool_calls: List[Dict[str, Any]] = None
    token_usage: Dict[str, int] = None

    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []
        if self.token_usage is None:
            self.token_usage = {}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMessage":
        return cls(**data)


class SessionManager:
    """Manages conversation sessions"""

    def __init__(self, config: CLIConfig):
        self.config = config
        self.session_file = Path(config.session_file)
        self.sessions_dir = Path(config.config_dir) / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def has_session(self) -> bool:
        """Check if a previous session exists"""
        return self.session_file.exists()

    def save_session(self, messages: List[Any]) -> None:
        """Save current session to file"""
        session_data = {
            "version": "1.0",
            "timestamp": time.time(),
            "working_directory": self.config.working_directory,
            "model": self.config.model,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "tool_calls": getattr(msg, 'tool_calls', []),
                    "token_usage": getattr(msg, 'token_usage', {})
                }
                for msg in messages
            ]
        }

        with open(self.session_file, 'w') as f:
            json.dump(session_data, f, indent=2)

    def load_session(self) -> List[Any]:
        """Load previous session from file"""
        if not self.session_file.exists():
            return []

        try:
            with open(self.session_file, 'r') as f:
                data = json.load(f)

            # Import here to avoid circular imports
            from cli.app import Message

            messages = []
            for msg_data in data.get("messages", []):
                msg = Message(
                    role=msg_data["role"],
                    content=msg_data["content"],
                    timestamp=msg_data.get("timestamp", time.time()),
                    tool_calls=msg_data.get("tool_calls", []),
                    token_usage=msg_data.get("token_usage")
                )
                messages.append(msg)

            return messages

        except (json.JSONDecodeError, KeyError) as e:
            # Corrupted session file
            return []

    def clear_session(self) -> None:
        """Clear current session"""
        if self.session_file.exists():
            self.session_file.unlink()

    def archive_session(self, name: Optional[str] = None) -> str:
        """Archive current session with a name"""
        if not self.session_file.exists():
            return ""

        if name is None:
            name = f"session_{int(time.time())}"

        archive_path = self.sessions_dir / f"{name}.json"

        # Copy session file to archive
        with open(self.session_file, 'r') as src:
            data = json.load(src)

        data["name"] = name
        data["archived_at"] = time.time()

        with open(archive_path, 'w') as dst:
            json.dump(data, dst, indent=2)

        return str(archive_path)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all archived sessions"""
        sessions = []

        for session_path in self.sessions_dir.glob("*.json"):
            try:
                with open(session_path, 'r') as f:
                    data = json.load(f)

                sessions.append({
                    "name": data.get("name", session_path.stem),
                    "timestamp": data.get("timestamp", 0),
                    "message_count": len(data.get("messages", [])),
                    "working_directory": data.get("working_directory", ""),
                    "path": str(session_path)
                })
            except (json.JSONDecodeError, KeyError):
                continue

        return sorted(sessions, key=lambda x: x["timestamp"], reverse=True)

    def load_archived_session(self, name: str) -> List[Any]:
        """Load an archived session by name"""
        session_path = self.sessions_dir / f"{name}.json"

        if not session_path.exists():
            # Try to find by partial name
            for path in self.sessions_dir.glob(f"*{name}*.json"):
                session_path = path
                break

        if not session_path.exists():
            return []

        # Copy to current session
        with open(session_path, 'r') as f:
            data = json.load(f)

        with open(self.session_file, 'w') as f:
            json.dump(data, f, indent=2)

        return self.load_session()

    def delete_archived_session(self, name: str) -> bool:
        """Delete an archived session"""
        session_path = self.sessions_dir / f"{name}.json"

        if session_path.exists():
            session_path.unlink()
            return True

        return False

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session"""
        if not self.session_file.exists():
            return {}

        try:
            with open(self.session_file, 'r') as f:
                data = json.load(f)

            messages = data.get("messages", [])
            user_messages = [m for m in messages if m.get("role") == "user"]
            assistant_messages = [m for m in messages if m.get("role") == "assistant"]

            total_tokens = sum(
                m.get("token_usage", {}).get("total_tokens", 0)
                for m in messages
            )

            return {
                "message_count": len(messages),
                "user_messages": len(user_messages),
                "assistant_messages": len(assistant_messages),
                "total_tokens": total_tokens,
                "working_directory": data.get("working_directory", ""),
                "model": data.get("model", ""),
                "started_at": data.get("timestamp", 0)
            }

        except (json.JSONDecodeError, KeyError):
            return {}

    def compact_session(self, keep_last: int = 10) -> int:
        """Compact session by keeping only the last N messages"""
        if not self.session_file.exists():
            return 0

        try:
            with open(self.session_file, 'r') as f:
                data = json.load(f)

            messages = data.get("messages", [])
            original_count = len(messages)

            if original_count <= keep_last:
                return 0

            # Keep last N messages
            data["messages"] = messages[-keep_last:]
            data["compacted_at"] = time.time()
            data["original_count"] = original_count

            with open(self.session_file, 'w') as f:
                json.dump(data, f, indent=2)

            return original_count - keep_last

        except (json.JSONDecodeError, KeyError):
            return 0
