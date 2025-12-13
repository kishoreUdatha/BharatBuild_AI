"""
Token Tracking Service
======================
Centralized service for logging detailed token usage.

Usage:
    from app.services.token_tracker import token_tracker

    # Log a token transaction
    await token_tracker.log_transaction(
        user_id="user-uuid",
        project_id="project-uuid",
        agent_type=AgentType.WRITER,
        operation=OperationType.GENERATE_FILE,
        model="haiku",
        input_tokens=1000,
        output_tokens=2000,
        file_path="src/App.tsx"
    )

    # Get project token usage
    usage = await token_tracker.get_project_usage("project-uuid")

    # Get user's daily usage
    daily = await token_tracker.get_user_daily_usage("user-uuid")
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import logger
from app.models.usage import (
    TokenTransaction,
    TokenUsage,
    AgentType,
    OperationType
)


class TokenTracker:
    """
    Service for tracking and querying token usage.
    """

    async def log_transaction(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: Optional[str],
        agent_type: AgentType,
        operation: OperationType,
        model: str,
        input_tokens: int,
        output_tokens: int,
        file_path: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[TokenTransaction]:
        """
        Log a detailed token transaction.

        Args:
            db: Database session
            user_id: User UUID
            project_id: Project UUID (optional)
            agent_type: Type of agent (planner, writer, etc.)
            operation: Specific operation (generate_file, fix_error, etc.)
            model: Model used (haiku, sonnet, opus)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            file_path: File path for file operations
            error_message: Error message for fix operations
            metadata: Additional metadata

        Returns:
            Created TokenTransaction or None on error
        """
        try:
            total_tokens = input_tokens + output_tokens
            cost_paise = TokenTransaction.calculate_cost_paise(
                input_tokens, output_tokens, model
            )

            transaction = TokenTransaction(
                user_id=user_id,
                project_id=project_id,
                agent_type=agent_type,
                operation=operation,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_paise=cost_paise,
                file_path=file_path,
                error_message=error_message,
                metadata=metadata
            )

            db.add(transaction)
            await db.commit()
            await db.refresh(transaction)

            logger.info(
                f"[TokenTracker] Logged: {agent_type.value}/{operation.value} "
                f"| {total_tokens} tokens | ₹{cost_paise/100:.2f} | model={model}"
            )

            return transaction

        except Exception as e:
            logger.error(f"[TokenTracker] Failed to log transaction: {e}")
            await db.rollback()
            return None

    async def log_transaction_simple(
        self,
        user_id: str,
        project_id: Optional[str],
        agent_type: AgentType,
        operation: OperationType,
        model: str,
        input_tokens: int,
        output_tokens: int,
        file_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[TokenTransaction]:
        """
        Log transaction with automatic database session management.
        Use this when you don't have an existing db session.
        """
        try:
            from app.core.database import async_session

            async with async_session() as db:
                return await self.log_transaction(
                    db=db,
                    user_id=user_id,
                    project_id=project_id,
                    agent_type=agent_type,
                    operation=operation,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    file_path=file_path,
                    metadata=metadata
                )
        except Exception as e:
            logger.error(f"[TokenTracker] Failed to log transaction (simple): {e}")
            return None

    async def get_project_usage(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Get total token usage for a project.

        Returns:
            {
                "total_tokens": 15000,
                "total_cost_paise": 500,
                "total_cost_rupees": 5.00,
                "by_agent": {"planner": 3000, "writer": 12000},
                "by_model": {"haiku": 10000, "sonnet": 5000},
                "transaction_count": 25
            }
        """
        try:
            # Total tokens and cost
            total_result = await db.execute(
                select(
                    func.sum(TokenTransaction.total_tokens),
                    func.sum(TokenTransaction.cost_paise),
                    func.count(TokenTransaction.id)
                ).where(TokenTransaction.project_id == project_id)
            )
            total_row = total_result.one()
            total_tokens = total_row[0] or 0
            total_cost_paise = total_row[1] or 0
            transaction_count = total_row[2] or 0

            # By agent type
            agent_result = await db.execute(
                select(
                    TokenTransaction.agent_type,
                    func.sum(TokenTransaction.total_tokens)
                )
                .where(TokenTransaction.project_id == project_id)
                .group_by(TokenTransaction.agent_type)
            )
            by_agent = {row[0].value: row[1] for row in agent_result.all()}

            # By model
            model_result = await db.execute(
                select(
                    TokenTransaction.model,
                    func.sum(TokenTransaction.total_tokens)
                )
                .where(TokenTransaction.project_id == project_id)
                .group_by(TokenTransaction.model)
            )
            by_model = {row[0]: row[1] for row in model_result.all()}

            return {
                "project_id": project_id,
                "total_tokens": total_tokens,
                "total_cost_paise": total_cost_paise,
                "total_cost_rupees": total_cost_paise / 100,
                "by_agent": by_agent,
                "by_model": by_model,
                "transaction_count": transaction_count
            }

        except Exception as e:
            logger.error(f"[TokenTracker] Failed to get project usage: {e}")
            return {
                "project_id": project_id,
                "total_tokens": 0,
                "total_cost_paise": 0,
                "total_cost_rupees": 0,
                "by_agent": {},
                "by_model": {},
                "transaction_count": 0
            }

    async def get_user_usage(
        self,
        db: AsyncSession,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get user's token usage for the last N days.

        Returns:
            {
                "total_tokens": 50000,
                "total_cost_rupees": 15.50,
                "by_project": {"proj-1": 20000, "proj-2": 30000},
                "by_agent": {"planner": 10000, "writer": 40000},
                "daily_breakdown": [{"date": "2024-01-15", "tokens": 5000}, ...]
            }
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # Total tokens and cost
            total_result = await db.execute(
                select(
                    func.sum(TokenTransaction.total_tokens),
                    func.sum(TokenTransaction.cost_paise)
                ).where(
                    and_(
                        TokenTransaction.user_id == user_id,
                        TokenTransaction.created_at >= start_date
                    )
                )
            )
            total_row = total_result.one()
            total_tokens = total_row[0] or 0
            total_cost_paise = total_row[1] or 0

            # By project
            project_result = await db.execute(
                select(
                    TokenTransaction.project_id,
                    func.sum(TokenTransaction.total_tokens)
                )
                .where(
                    and_(
                        TokenTransaction.user_id == user_id,
                        TokenTransaction.created_at >= start_date
                    )
                )
                .group_by(TokenTransaction.project_id)
            )
            by_project = {
                str(row[0]) if row[0] else "unknown": row[1]
                for row in project_result.all()
            }

            # By agent type
            agent_result = await db.execute(
                select(
                    TokenTransaction.agent_type,
                    func.sum(TokenTransaction.total_tokens)
                )
                .where(
                    and_(
                        TokenTransaction.user_id == user_id,
                        TokenTransaction.created_at >= start_date
                    )
                )
                .group_by(TokenTransaction.agent_type)
            )
            by_agent = {row[0].value: row[1] for row in agent_result.all()}

            return {
                "user_id": user_id,
                "period_days": days,
                "total_tokens": total_tokens,
                "total_cost_paise": total_cost_paise,
                "total_cost_rupees": total_cost_paise / 100,
                "by_project": by_project,
                "by_agent": by_agent
            }

        except Exception as e:
            logger.error(f"[TokenTracker] Failed to get user usage: {e}")
            return {
                "user_id": user_id,
                "period_days": days,
                "total_tokens": 0,
                "total_cost_paise": 0,
                "total_cost_rupees": 0,
                "by_project": {},
                "by_agent": {}
            }

    async def get_recent_transactions(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent token transactions for a user."""
        try:
            result = await db.execute(
                select(TokenTransaction)
                .where(TokenTransaction.user_id == user_id)
                .order_by(TokenTransaction.created_at.desc())
                .limit(limit)
            )
            transactions = result.scalars().all()

            return [
                {
                    "id": str(tx.id),
                    "project_id": str(tx.project_id) if tx.project_id else None,
                    "agent_type": tx.agent_type.value,
                    "operation": tx.operation.value,
                    "model": tx.model,
                    "input_tokens": tx.input_tokens,
                    "output_tokens": tx.output_tokens,
                    "total_tokens": tx.total_tokens,
                    "cost_paise": tx.cost_paise,
                    "cost_rupees": tx.cost_paise / 100,
                    "file_path": tx.file_path,
                    "created_at": tx.created_at.isoformat()
                }
                for tx in transactions
            ]

        except Exception as e:
            logger.error(f"[TokenTracker] Failed to get recent transactions: {e}")
            return []


# Singleton instance
token_tracker = TokenTracker()
