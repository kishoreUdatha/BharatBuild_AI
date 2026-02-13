"""
Team WebSocket Manager

Manages real-time communication for team collaboration:
- Member presence (online/offline status)
- Task updates
- File change notifications
- Team chat messages

Uses asyncio for efficient connection management.
"""

import asyncio
import json
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from fastapi import WebSocket, WebSocketDisconnect

from app.core.logging_config import logger


class EventType(str, Enum):
    """WebSocket event types"""
    # Connection events
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"

    # Presence events
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    PRESENCE_UPDATE = "presence_update"

    # Task events
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    TASK_ASSIGNED = "task_assigned"

    # File events
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    FILE_LOCKED = "file_locked"
    FILE_UNLOCKED = "file_unlocked"

    # Merge events
    MERGE_STARTED = "merge_started"
    MERGE_COMPLETED = "merge_completed"
    MERGE_CONFLICT = "merge_conflict"

    # Chat events
    CHAT_MESSAGE = "chat_message"
    TYPING_START = "typing_start"
    TYPING_STOP = "typing_stop"

    # System events
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


@dataclass
class TeamConnection:
    """Represents a WebSocket connection to a team"""
    websocket: WebSocket
    user_id: str
    user_name: str
    team_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TeamPresence:
    """Tracks online members in a team"""
    team_id: str
    members: Dict[str, TeamConnection] = field(default_factory=dict)
    file_locks: Dict[str, str] = field(default_factory=dict)  # file_path -> user_id


class TeamWebSocketManager:
    """
    Manages WebSocket connections for team collaboration.

    Handles multiple teams with multiple connections per team.
    Provides real-time updates for presence, tasks, and file changes.
    """

    def __init__(self):
        # team_id -> TeamPresence
        self._teams: Dict[str, TeamPresence] = {}
        # user_id -> connection (for direct messaging)
        self._user_connections: Dict[str, TeamConnection] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        team_id: str,
        user_id: str,
        user_name: str
    ) -> TeamConnection:
        """
        Register a new WebSocket connection for a team member.

        Args:
            websocket: The WebSocket connection
            team_id: Team ID
            user_id: User ID
            user_name: User's display name

        Returns:
            TeamConnection object
        """
        await websocket.accept()

        connection = TeamConnection(
            websocket=websocket,
            user_id=user_id,
            user_name=user_name,
            team_id=team_id
        )

        async with self._lock:
            # Initialize team presence if needed
            if team_id not in self._teams:
                self._teams[team_id] = TeamPresence(team_id=team_id)

            # Add connection
            self._teams[team_id].members[user_id] = connection
            self._user_connections[user_id] = connection

        logger.info(f"WebSocket connected: user {user_id} to team {team_id}")

        # Notify others that member joined
        await self.broadcast_to_team(
            team_id=team_id,
            event_type=EventType.MEMBER_JOINED,
            data={
                "user_id": user_id,
                "user_name": user_name,
                "timestamp": datetime.utcnow().isoformat()
            },
            exclude_user=user_id
        )

        # Send current presence to new member
        await self.send_to_user(
            user_id=user_id,
            event_type=EventType.CONNECTED,
            data={
                "team_id": team_id,
                "online_members": await self.get_online_members(team_id),
                "file_locks": self.get_file_locks(team_id)
            }
        )

        return connection

    async def disconnect(self, user_id: str, team_id: str):
        """
        Remove a WebSocket connection.

        Args:
            user_id: User ID
            team_id: Team ID
        """
        async with self._lock:
            # Remove from team
            if team_id in self._teams:
                team = self._teams[team_id]
                connection = team.members.pop(user_id, None)

                # Release any file locks held by this user
                locks_to_release = [
                    path for path, uid in team.file_locks.items()
                    if uid == user_id
                ]
                for path in locks_to_release:
                    del team.file_locks[path]

                # Clean up empty teams
                if not team.members:
                    del self._teams[team_id]

            # Remove from user connections
            self._user_connections.pop(user_id, None)

        logger.info(f"WebSocket disconnected: user {user_id} from team {team_id}")

        # Notify others
        await self.broadcast_to_team(
            team_id=team_id,
            event_type=EventType.MEMBER_LEFT,
            data={
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "released_locks": locks_to_release if 'locks_to_release' in locals() else []
            },
            exclude_user=user_id
        )

    async def send_to_user(
        self,
        user_id: str,
        event_type: EventType,
        data: Dict[str, Any]
    ):
        """Send a message to a specific user."""
        connection = self._user_connections.get(user_id)
        if connection:
            try:
                message = {
                    "type": event_type.value,
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await connection.websocket.send_json(message)
                connection.last_activity = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                # Connection might be dead, clean up
                await self.disconnect(user_id, connection.team_id)

    async def broadcast_to_team(
        self,
        team_id: str,
        event_type: EventType,
        data: Dict[str, Any],
        exclude_user: Optional[str] = None
    ):
        """
        Broadcast a message to all members of a team.

        Args:
            team_id: Team to broadcast to
            event_type: Type of event
            data: Event data
            exclude_user: Optional user to exclude from broadcast
        """
        if team_id not in self._teams:
            return

        team = self._teams[team_id]
        message = {
            "type": event_type.value,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }

        dead_connections = []

        for user_id, connection in team.members.items():
            if exclude_user and user_id == exclude_user:
                continue
            try:
                await connection.websocket.send_json(message)
                connection.last_activity = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                dead_connections.append(user_id)

        # Clean up dead connections
        for user_id in dead_connections:
            await self.disconnect(user_id, team_id)

    async def get_online_members(self, team_id: str) -> List[Dict[str, Any]]:
        """Get list of online members in a team."""
        if team_id not in self._teams:
            return []

        team = self._teams[team_id]
        return [
            {
                "user_id": conn.user_id,
                "user_name": conn.user_name,
                "connected_at": conn.connected_at.isoformat(),
                "last_activity": conn.last_activity.isoformat()
            }
            for conn in team.members.values()
        ]

    def get_file_locks(self, team_id: str) -> Dict[str, str]:
        """Get current file locks for a team."""
        if team_id not in self._teams:
            return {}
        return dict(self._teams[team_id].file_locks)

    async def lock_file(
        self,
        team_id: str,
        user_id: str,
        file_path: str
    ) -> bool:
        """
        Attempt to lock a file for editing.

        Returns True if lock acquired, False if already locked by another user.
        """
        if team_id not in self._teams:
            return False

        team = self._teams[team_id]

        async with self._lock:
            # Check if already locked by someone else
            if file_path in team.file_locks:
                if team.file_locks[file_path] != user_id:
                    return False

            # Acquire lock
            team.file_locks[file_path] = user_id

        # Notify team
        connection = self._user_connections.get(user_id)
        await self.broadcast_to_team(
            team_id=team_id,
            event_type=EventType.FILE_LOCKED,
            data={
                "file_path": file_path,
                "locked_by": user_id,
                "locked_by_name": connection.user_name if connection else "Unknown"
            }
        )

        return True

    async def unlock_file(
        self,
        team_id: str,
        user_id: str,
        file_path: str
    ) -> bool:
        """
        Release a file lock.

        Returns True if unlocked, False if not locked by this user.
        """
        if team_id not in self._teams:
            return False

        team = self._teams[team_id]

        async with self._lock:
            # Check if locked by this user
            if file_path not in team.file_locks:
                return True  # Already unlocked

            if team.file_locks[file_path] != user_id:
                return False  # Locked by someone else

            # Release lock
            del team.file_locks[file_path]

        # Notify team
        await self.broadcast_to_team(
            team_id=team_id,
            event_type=EventType.FILE_UNLOCKED,
            data={
                "file_path": file_path,
                "unlocked_by": user_id
            }
        )

        return True

    # ==================== Event Broadcasting Helpers ====================

    async def notify_task_created(
        self,
        team_id: str,
        task_data: Dict[str, Any],
        created_by: str
    ):
        """Notify team of new task."""
        await self.broadcast_to_team(
            team_id=team_id,
            event_type=EventType.TASK_CREATED,
            data={
                "task": task_data,
                "created_by": created_by
            }
        )

    async def notify_task_updated(
        self,
        team_id: str,
        task_id: str,
        changes: Dict[str, Any],
        updated_by: str
    ):
        """Notify team of task update."""
        await self.broadcast_to_team(
            team_id=team_id,
            event_type=EventType.TASK_UPDATED,
            data={
                "task_id": task_id,
                "changes": changes,
                "updated_by": updated_by
            }
        )

    async def notify_task_assigned(
        self,
        team_id: str,
        task_id: str,
        task_title: str,
        assignee_id: str,
        assigned_by: str
    ):
        """Notify team (especially assignee) of task assignment."""
        await self.broadcast_to_team(
            team_id=team_id,
            event_type=EventType.TASK_ASSIGNED,
            data={
                "task_id": task_id,
                "task_title": task_title,
                "assignee_id": assignee_id,
                "assigned_by": assigned_by
            }
        )

    async def notify_file_changed(
        self,
        team_id: str,
        file_path: str,
        change_type: str,
        changed_by: str
    ):
        """Notify team of file change."""
        event_map = {
            "created": EventType.FILE_CREATED,
            "modified": EventType.FILE_MODIFIED,
            "deleted": EventType.FILE_DELETED
        }
        event_type = event_map.get(change_type, EventType.FILE_MODIFIED)

        await self.broadcast_to_team(
            team_id=team_id,
            event_type=event_type,
            data={
                "file_path": file_path,
                "change_type": change_type,
                "changed_by": changed_by
            },
            exclude_user=changed_by
        )

    async def send_chat_message(
        self,
        team_id: str,
        sender_id: str,
        sender_name: str,
        message: str,
        message_id: Optional[str] = None
    ):
        """Send a chat message to the team."""
        import uuid
        await self.broadcast_to_team(
            team_id=team_id,
            event_type=EventType.CHAT_MESSAGE,
            data={
                "message_id": message_id or str(uuid.uuid4()),
                "sender_id": sender_id,
                "sender_name": sender_name,
                "content": message
            }
        )

    async def handle_typing(
        self,
        team_id: str,
        user_id: str,
        user_name: str,
        is_typing: bool
    ):
        """Handle typing indicator."""
        event_type = EventType.TYPING_START if is_typing else EventType.TYPING_STOP
        await self.broadcast_to_team(
            team_id=team_id,
            event_type=event_type,
            data={
                "user_id": user_id,
                "user_name": user_name
            },
            exclude_user=user_id
        )

    async def handle_ping(self, user_id: str):
        """Handle ping and respond with pong."""
        await self.send_to_user(
            user_id=user_id,
            event_type=EventType.PONG,
            data={"server_time": datetime.utcnow().isoformat()}
        )


# Singleton instance
team_websocket_manager = TeamWebSocketManager()
