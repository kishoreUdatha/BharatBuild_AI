"""
Admin WebSocket endpoint for real-time updates.
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Set
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.billing import Subscription, Transaction
from app.models.audit_log import AuditLog
from app.modules.auth.dependencies import get_current_user_from_token

router = APIRouter()


class AdminConnectionManager:
    """Manages WebSocket connections for admin dashboard."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._broadcast_task = None

    async def connect(self, websocket: WebSocket, admin_id: str):
        await websocket.accept()
        self.active_connections[admin_id] = websocket

    def disconnect(self, admin_id: str):
        if admin_id in self.active_connections:
            del self.active_connections[admin_id]

    async def send_personal_message(self, message: dict, admin_id: str):
        if admin_id in self.active_connections:
            try:
                await self.active_connections[admin_id].send_json(message)
            except Exception:
                self.disconnect(admin_id)

    async def broadcast(self, message: dict):
        disconnected = []
        for admin_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(admin_id)

        for admin_id in disconnected:
            self.disconnect(admin_id)


manager = AdminConnectionManager()


async def get_live_stats(db: AsyncSession) -> dict:
    """Get current live statistics for dashboard."""

    # Total users
    total_users = await db.execute(select(func.count(User.id)))
    total_users_count = total_users.scalar() or 0

    # Active users (logged in within last 24 hours)
    from datetime import timedelta
    yesterday = datetime.utcnow() - timedelta(days=1)
    active_users = await db.execute(
        select(func.count(User.id)).where(User.last_login_at >= yesterday)
    )
    active_users_count = active_users.scalar() or 0

    # Total projects
    total_projects = await db.execute(select(func.count(Project.id)))
    total_projects_count = total_projects.scalar() or 0

    # Active subscriptions
    active_subs = await db.execute(
        select(func.count(Subscription.id)).where(Subscription.status == "active")
    )
    active_subs_count = active_subs.scalar() or 0

    # Today's revenue
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_revenue = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.created_at >= today_start,
            Transaction.status == "completed"
        )
    )
    today_revenue_amount = today_revenue.scalar() or 0

    return {
        "type": "stats_update",
        "data": {
            "total_users": total_users_count,
            "active_users": active_users_count,
            "total_projects": total_projects_count,
            "active_subscriptions": active_subs_count,
            "today_revenue": today_revenue_amount / 100,  # Convert paise to rupees
            "timestamp": datetime.utcnow().isoformat()
        }
    }


async def get_recent_activity(db: AsyncSession, limit: int = 10) -> dict:
    """Get recent activity for live feed."""

    result = await db.execute(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()

    activities = []
    for log in logs:
        # Get admin info
        admin_result = await db.execute(
            select(User.email, User.full_name).where(User.id == log.admin_id)
        )
        admin_info = admin_result.first()

        activities.append({
            "id": str(log.id),
            "action": log.action,
            "target_type": log.target_type,
            "target_id": str(log.target_id) if log.target_id else None,
            "admin_email": admin_info.email if admin_info else "Unknown",
            "admin_name": admin_info.full_name if admin_info else None,
            "details": log.details,
            "created_at": log.created_at.isoformat() if log.created_at else None
        })

    return {
        "type": "activity_update",
        "data": activities
    }


@router.websocket("/ws")
async def admin_websocket(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for admin real-time updates.

    Connect with: ws://host/api/v1/admin/ws?token=<jwt_token>

    Message types sent:
    - stats_update: Live dashboard statistics
    - activity_update: Recent activity feed
    - notification: Admin notifications
    """

    # Verify token and check admin role
    try:
        user = await get_current_user_from_token(token, db)
        if user.role != "ADMIN" and not user.is_superuser:
            await websocket.close(code=4003, reason="Admin access required")
            return
    except Exception as e:
        await websocket.close(code=4001, reason="Invalid token")
        return

    admin_id = str(user.id)
    await manager.connect(websocket, admin_id)

    try:
        # Send initial data
        stats = await get_live_stats(db)
        await manager.send_personal_message(stats, admin_id)

        activity = await get_recent_activity(db)
        await manager.send_personal_message(activity, admin_id)

        # Send welcome notification
        await manager.send_personal_message({
            "type": "notification",
            "data": {
                "title": "Connected",
                "message": "Real-time updates enabled",
                "level": "info"
            }
        }, admin_id)

        # Keep connection alive and send periodic updates
        last_stats_update = datetime.utcnow()

        while True:
            try:
                # Wait for message or timeout for periodic update
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0  # Send stats update every 30 seconds
                )

                # Handle incoming messages
                if message.get("type") == "ping":
                    await manager.send_personal_message({"type": "pong"}, admin_id)

                elif message.get("type") == "request_stats":
                    stats = await get_live_stats(db)
                    await manager.send_personal_message(stats, admin_id)

                elif message.get("type") == "request_activity":
                    activity = await get_recent_activity(db)
                    await manager.send_personal_message(activity, admin_id)

            except asyncio.TimeoutError:
                # Send periodic stats update
                stats = await get_live_stats(db)
                await manager.send_personal_message(stats, admin_id)
                last_stats_update = datetime.utcnow()

    except WebSocketDisconnect:
        manager.disconnect(admin_id)
    except Exception as e:
        manager.disconnect(admin_id)


async def broadcast_admin_event(event_type: str, data: dict):
    """
    Broadcast an event to all connected admin clients.
    Call this from other endpoints when important events occur.
    """
    await manager.broadcast({
        "type": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    })


async def notify_new_user(user_email: str):
    """Notify admins of new user registration."""
    await manager.broadcast({
        "type": "notification",
        "data": {
            "title": "New User",
            "message": f"New user registered: {user_email}",
            "level": "info"
        }
    })


async def notify_new_subscription(user_email: str, plan_name: str):
    """Notify admins of new subscription."""
    await manager.broadcast({
        "type": "notification",
        "data": {
            "title": "New Subscription",
            "message": f"{user_email} subscribed to {plan_name}",
            "level": "success"
        }
    })


async def notify_payment_received(amount: float, currency: str = "INR"):
    """Notify admins of payment received."""
    await manager.broadcast({
        "type": "notification",
        "data": {
            "title": "Payment Received",
            "message": f"Payment of {currency} {amount:.2f} received",
            "level": "success"
        }
    })
