"""
Team Collaboration WebSocket Endpoint

Provides real-time communication for team members:
- Presence updates (who's online)
- Task status changes
- File editing notifications
- Team chat

Connection URL: WS /api/v1/teams/ws/{team_id}?token=<jwt>
"""

import json
import asyncio
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.core.database import get_db
from app.core.logging_config import logger
from app.models.user import User
from app.models.team import Team, TeamMember
from app.services.team_websocket import team_websocket_manager, EventType


router = APIRouter()


async def get_user_from_token(token: str, db: AsyncSession) -> Optional[User]:
    """Validate JWT token and return user."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if not user_id:
            return None

        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    except JWTError:
        return None


async def verify_team_membership(
    team_id: str,
    user_id: str,
    db: AsyncSession
) -> Optional[TeamMember]:
    """Verify user is an active member of the team."""
    result = await db.execute(
        select(TeamMember).where(
            and_(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
                TeamMember.is_active == True
            )
        )
    )
    return result.scalar_one_or_none()


@router.websocket("/ws/{team_id}")
async def team_websocket_endpoint(
    websocket: WebSocket,
    team_id: str,
    token: str = Query(...)
):
    """
    WebSocket endpoint for team collaboration.

    Connect: WS /api/v1/teams/ws/{team_id}?token=<jwt>

    Message format (send):
    {
        "type": "event_type",
        "data": { ... }
    }

    Supported client events:
    - ping: Keep-alive ping
    - chat_message: { content: "message" }
    - typing_start: Start typing indicator
    - typing_stop: Stop typing indicator
    - file_lock: { file_path: "path/to/file" }
    - file_unlock: { file_path: "path/to/file" }

    Server events:
    - connected: Initial connection with online members
    - member_joined/member_left: Presence updates
    - task_created/task_updated/task_deleted: Task changes
    - file_created/file_modified/file_deleted: File changes
    - file_locked/file_unlocked: File lock status
    - chat_message: Team chat
    - typing_start/typing_stop: Typing indicators
    - pong: Response to ping
    - error: Error notification
    """
    # Get database session
    # Note: We need to create a session manually for WebSocket endpoints
    from app.core.database import get_session_local

    async with get_session_local()() as db:
        # Authenticate user from token
        user = await get_user_from_token(token, db)
        if not user:
            await websocket.close(code=4001, reason="Invalid or expired token")
            return

        # Verify team membership
        member = await verify_team_membership(team_id, str(user.id), db)
        if not member:
            await websocket.close(code=4003, reason="Not a member of this team")
            return

        # Connect to team
        connection = await team_websocket_manager.connect(
            websocket=websocket,
            team_id=team_id,
            user_id=str(user.id),
            user_name=user.full_name or user.email
        )

        try:
            # Message handling loop
            while True:
                try:
                    # Receive message
                    data = await websocket.receive_json()

                    event_type = data.get("type", "")
                    event_data = data.get("data", {})

                    # Handle different event types
                    if event_type == "ping":
                        await team_websocket_manager.handle_ping(str(user.id))

                    elif event_type == "chat_message":
                        content = event_data.get("content", "").strip()
                        if content:
                            await team_websocket_manager.send_chat_message(
                                team_id=team_id,
                                sender_id=str(user.id),
                                sender_name=user.full_name or user.email,
                                message=content
                            )

                    elif event_type == "typing_start":
                        await team_websocket_manager.handle_typing(
                            team_id=team_id,
                            user_id=str(user.id),
                            user_name=user.full_name or user.email,
                            is_typing=True
                        )

                    elif event_type == "typing_stop":
                        await team_websocket_manager.handle_typing(
                            team_id=team_id,
                            user_id=str(user.id),
                            user_name=user.full_name or user.email,
                            is_typing=False
                        )

                    elif event_type == "file_lock":
                        file_path = event_data.get("file_path", "")
                        if file_path:
                            success = await team_websocket_manager.lock_file(
                                team_id=team_id,
                                user_id=str(user.id),
                                file_path=file_path
                            )
                            if not success:
                                await team_websocket_manager.send_to_user(
                                    user_id=str(user.id),
                                    event_type=EventType.ERROR,
                                    data={
                                        "error": "file_locked",
                                        "message": f"File {file_path} is locked by another user"
                                    }
                                )

                    elif event_type == "file_unlock":
                        file_path = event_data.get("file_path", "")
                        if file_path:
                            await team_websocket_manager.unlock_file(
                                team_id=team_id,
                                user_id=str(user.id),
                                file_path=file_path
                            )

                    elif event_type == "file_changed":
                        # Notify others of file change
                        file_path = event_data.get("file_path", "")
                        change_type = event_data.get("change_type", "modified")
                        if file_path:
                            await team_websocket_manager.notify_file_changed(
                                team_id=team_id,
                                file_path=file_path,
                                change_type=change_type,
                                changed_by=str(user.id)
                            )

                    elif event_type == "presence_update":
                        # Update last activity
                        connection.last_activity = connection.last_activity.__class__.utcnow()

                    else:
                        logger.debug(f"Unknown WebSocket event type: {event_type}")

                except json.JSONDecodeError:
                    await team_websocket_manager.send_to_user(
                        user_id=str(user.id),
                        event_type=EventType.ERROR,
                        data={"error": "invalid_json", "message": "Invalid JSON message"}
                    )

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user.id} from team {team_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}", exc_info=True)
        finally:
            # Clean up connection
            await team_websocket_manager.disconnect(
                user_id=str(user.id),
                team_id=team_id
            )


@router.get("/ws/test")
async def test_websocket_connection():
    """
    Test endpoint to verify WebSocket is available.

    Use this to check if the WebSocket route is properly configured.
    """
    return {
        "status": "ok",
        "message": "WebSocket endpoint available at /api/v1/teams/ws/{team_id}?token=<jwt>",
        "events": {
            "client_events": [
                "ping",
                "chat_message",
                "typing_start",
                "typing_stop",
                "file_lock",
                "file_unlock",
                "file_changed",
                "presence_update"
            ],
            "server_events": [
                "connected",
                "disconnected",
                "member_joined",
                "member_left",
                "task_created",
                "task_updated",
                "task_deleted",
                "file_created",
                "file_modified",
                "file_deleted",
                "file_locked",
                "file_unlocked",
                "chat_message",
                "typing_start",
                "typing_stop",
                "pong",
                "error"
            ]
        }
    }
