"""
Message Service - Manages project chat history (project_messages table)
Stores all messages between users and AI agents for conversation replay and context.
"""

from typing import Optional, List, Union
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func

from app.models.project_message import ProjectMessage, MessageRole
from app.core.logging_config import logger


def to_str(value: Union[UUID, str, None]) -> Optional[str]:
    """Convert UUID to string if needed"""
    if value is None:
        return None
    return str(value) if isinstance(value, UUID) else value


class MessageService:
    """
    Service for managing project chat messages.

    Use cases:
    - Store user prompts
    - Store AI agent responses (planner, writer, fixer, etc.)
    - Retrieve conversation history for context
    - Track token usage per message
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_message(
        self,
        project_id: UUID,
        role: MessageRole,
        content: str,
        agent_type: Optional[str] = None,
        tokens_used: int = 0,
        model_used: Optional[str] = None,
        extra_data: Optional[str] = None
    ) -> ProjectMessage:
        """
        Add a new message to the project conversation.

        Args:
            project_id: Project UUID
            role: Who sent the message (user, planner, writer, etc.)
            content: Message content
            agent_type: Specific agent type if applicable
            tokens_used: Number of tokens consumed
            model_used: LLM model used (claude-3.5-sonnet, etc.)
            extra_data: JSON string with additional metadata

        Returns:
            Created ProjectMessage instance
        """
        message = ProjectMessage(
            project_id=to_str(project_id),
            role=role.value if isinstance(role, MessageRole) else role,
            content=content,
            agent_type=agent_type,
            tokens_used=tokens_used,
            model_used=model_used,
            extra_data=extra_data,
            created_at=datetime.utcnow()
        )

        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)

        role_str = role.value if isinstance(role, MessageRole) else role
        logger.debug(f"Added message: {role_str} for project {project_id}")
        return message

    async def add_user_message(
        self,
        project_id: UUID,
        content: str,
        extra_data: Optional[str] = None
    ) -> ProjectMessage:
        """Convenience method for adding user messages"""
        return await self.add_message(
            project_id=project_id,
            role=MessageRole.USER,
            content=content,
            extra_data=extra_data
        )

    async def add_agent_message(
        self,
        project_id: UUID,
        agent_type: str,
        content: str,
        tokens_used: int = 0,
        model_used: str = "claude-3-5-sonnet-20241022",
        extra_data: Optional[str] = None
    ) -> ProjectMessage:
        """
        Add an agent response message.

        Args:
            agent_type: One of 'planner', 'writer', 'fixer', 'runner', 'reviewer'
        """
        role_map = {
            'planner': MessageRole.PLANNER,
            'writer': MessageRole.WRITER,
            'fixer': MessageRole.FIXER,
            'runner': MessageRole.RUNNER,
            'reviewer': MessageRole.REVIEWER,
            'system': MessageRole.SYSTEM,
            'assistant': MessageRole.ASSISTANT
        }

        role = role_map.get(agent_type.lower(), MessageRole.ASSISTANT)

        return await self.add_message(
            project_id=project_id,
            role=role,
            content=content,
            agent_type=agent_type,
            tokens_used=tokens_used,
            model_used=model_used,
            extra_data=extra_data
        )

    async def get_messages(
        self,
        project_id: UUID,
        limit: Optional[int] = None,
        offset: int = 0,
        role_filter: Optional[MessageRole] = None
    ) -> List[ProjectMessage]:
        """
        Get messages for a project.

        Args:
            project_id: Project UUID
            limit: Maximum number of messages (None = all)
            offset: Skip first N messages
            role_filter: Filter by specific role

        Returns:
            List of messages ordered by creation time
        """
        query = (
            select(ProjectMessage)
            .where(ProjectMessage.project_id == to_str(project_id))
            .order_by(ProjectMessage.created_at)
        )

        if role_filter:
            query = query.where(ProjectMessage.role == role_filter)

        if offset > 0:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_conversation_context(
        self,
        project_id: UUID,
        max_messages: int = 20,
        max_tokens: int = 50000
    ) -> List[dict]:
        """
        Get conversation history formatted for LLM context.

        Returns recent messages up to token limit, formatted as:
        [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        messages = await self.get_messages(project_id, limit=max_messages * 2)

        # Reverse to get most recent first, then take what fits
        messages = list(reversed(messages))

        context = []
        total_tokens = 0

        for msg in messages:
            # Rough token estimate (4 chars = 1 token)
            msg_tokens = len(msg.content) // 4

            if total_tokens + msg_tokens > max_tokens:
                break

            # Map internal roles to standard LLM roles
            if msg.role == MessageRole.USER:
                role = "user"
            else:
                role = "assistant"

            context.append({
                "role": role,
                "content": msg.content
            })
            total_tokens += msg_tokens

        # Reverse back to chronological order
        return list(reversed(context))

    async def get_message_count(self, project_id: UUID) -> int:
        """Get total message count for a project"""
        result = await self.db.execute(
            select(func.count(ProjectMessage.id))
            .where(ProjectMessage.project_id == to_str(project_id))
        )
        return result.scalar() or 0

    async def get_total_tokens(self, project_id: UUID) -> int:
        """Get total tokens used in project conversation"""
        result = await self.db.execute(
            select(func.sum(ProjectMessage.tokens_used))
            .where(ProjectMessage.project_id == to_str(project_id))
        )
        return result.scalar() or 0

    async def delete_project_messages(self, project_id: UUID) -> int:
        """Delete all messages for a project"""
        result = await self.db.execute(
            delete(ProjectMessage)
            .where(ProjectMessage.project_id == to_str(project_id))
        )
        await self.db.commit()

        deleted = result.rowcount
        logger.info(f"Deleted {deleted} messages for project {project_id}")
        return deleted

    async def get_last_message(
        self,
        project_id: UUID,
        role: Optional[MessageRole] = None
    ) -> Optional[ProjectMessage]:
        """Get the last message, optionally filtered by role"""
        query = (
            select(ProjectMessage)
            .where(ProjectMessage.project_id == to_str(project_id))
            .order_by(ProjectMessage.created_at.desc())
            .limit(1)
        )

        if role:
            query = query.where(ProjectMessage.role == role)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()
