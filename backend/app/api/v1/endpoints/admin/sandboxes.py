"""
Admin Sandbox/Container Health Management endpoints.
Provides visibility into all user sandboxes and their health status.
"""
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID
import os
import time
import asyncio
import socket

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_admin
from app.models.user import User
from app.models.project import Project
from app.core.logging_config import logger

router = APIRouter()


@router.get("/connection-health")
async def get_sandbox_connection_health(
    admin: User = Depends(get_current_admin)
):
    """
    Check the health/connectivity of the sandbox server (remote Docker host).
    Returns connection status, latency, and Docker API availability.
    """
    sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
    sandbox_public_url = os.environ.get("SANDBOX_PUBLIC_URL", "")

    result = {
        "sandbox_mode": "remote" if sandbox_docker_host else "local",
        "sandbox_docker_host": sandbox_docker_host or "local",
        "sandbox_public_url": sandbox_public_url,
        "connection_status": "unknown",
        "docker_api_status": "unknown",
        "latency_ms": None,
        "docker_version": None,
        "docker_info": None,
        "error": None,
        "last_checked": datetime.utcnow().isoformat()
    }

    if not sandbox_docker_host:
        # Local mode - check local Docker
        try:
            import docker
            start = time.time()
            client = docker.from_env()
            version = client.version()
            latency = (time.time() - start) * 1000

            result["connection_status"] = "connected"
            result["docker_api_status"] = "healthy"
            result["latency_ms"] = round(latency, 2)
            result["docker_version"] = version.get("Version", "unknown")
            result["docker_info"] = {
                "containers": client.info().get("Containers", 0),
                "running": client.info().get("ContainersRunning", 0),
                "paused": client.info().get("ContainersPaused", 0),
                "stopped": client.info().get("ContainersStopped", 0),
                "images": client.info().get("Images", 0),
                "memory_total_gb": round(client.info().get("MemTotal", 0) / (1024**3), 2),
                "cpus": client.info().get("NCPU", 0),
                "os": client.info().get("OperatingSystem", "unknown"),
                "kernel": client.info().get("KernelVersion", "unknown"),
            }
        except Exception as e:
            result["connection_status"] = "error"
            result["docker_api_status"] = "unavailable"
            result["error"] = str(e)
        return result

    # Remote mode - check remote Docker host
    try:
        # Parse host and port from SANDBOX_DOCKER_HOST (e.g., tcp://1.2.3.4:2375)
        host_url = sandbox_docker_host.replace("tcp://", "").replace("http://", "")
        if ":" in host_url:
            host, port_str = host_url.split(":")
            port = int(port_str)
        else:
            host = host_url
            port = 2375

        # TCP connectivity check
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        tcp_result = sock.connect_ex((host, port))
        sock.close()
        tcp_latency = (time.time() - start) * 1000

        if tcp_result != 0:
            result["connection_status"] = "unreachable"
            result["docker_api_status"] = "unavailable"
            result["error"] = f"Cannot connect to {host}:{port} (TCP error: {tcp_result})"
            return result

        result["connection_status"] = "connected"
        result["latency_ms"] = round(tcp_latency, 2)

        # Docker API check
        try:
            import docker
            start = time.time()
            client = docker.DockerClient(base_url=sandbox_docker_host, timeout=10)
            version = client.version()
            api_latency = (time.time() - start) * 1000

            result["docker_api_status"] = "healthy"
            result["latency_ms"] = round(api_latency, 2)
            result["docker_version"] = version.get("Version", "unknown")
            result["docker_info"] = {
                "containers": client.info().get("Containers", 0),
                "running": client.info().get("ContainersRunning", 0),
                "paused": client.info().get("ContainersPaused", 0),
                "stopped": client.info().get("ContainersStopped", 0),
                "images": client.info().get("Images", 0),
                "memory_total_gb": round(client.info().get("MemTotal", 0) / (1024**3), 2),
                "cpus": client.info().get("NCPU", 0),
                "os": client.info().get("OperatingSystem", "unknown"),
                "kernel": client.info().get("KernelVersion", "unknown"),
            }
        except Exception as e:
            result["docker_api_status"] = "error"
            result["error"] = f"Docker API error: {str(e)}"

    except Exception as e:
        result["connection_status"] = "error"
        result["error"] = str(e)

    return result


@router.get("")
async def list_all_sandboxes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status: running, stopped, error"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    sort_by: str = Query("last_activity", regex="^(last_activity|created_at|idle_time_minutes|project_name)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    List all active sandboxes/containers across all users.

    Returns:
        List of sandboxes with health status, resource usage, and user info
    """
    try:
        from app.modules.execution.container_manager import get_container_manager
        from app.modules.execution.health_monitor import get_health_monitor, HealthStatus

        manager = get_container_manager()
        health_monitor = get_health_monitor()

        sandboxes = []

        for project_id, container in manager.containers.items():
            # Filter by status if provided
            if status:
                if status == "running" and container.status.value != "running":
                    continue
                elif status == "stopped" and container.status.value != "stopped":
                    continue
                elif status == "error" and container.status.value != "error":
                    continue

            # Filter by user_id if provided
            if user_id and container.user_id != user_id:
                continue

            # Get health status
            health_state = None
            health_status = "unknown"
            consecutive_failures = 0
            last_check = None
            restart_count = 0

            if health_monitor:
                health_state = health_monitor.get_health(project_id)
                if health_state and health_state.last_check:
                    health_status = health_state.last_check.status.value
                    consecutive_failures = health_state.last_check.consecutive_failures
                    last_check = health_state.last_check.checked_at.isoformat()
                    restart_count = health_state.restart_count

            # Get resource stats
            stats = await manager.get_container_stats(project_id)

            # Get user info
            user_info = await db.execute(
                select(User.email, User.full_name).where(User.id == UUID(container.user_id))
            )
            user_row = user_info.first()

            # Get project info
            project_info = await db.execute(
                select(Project.name).where(Project.id == UUID(project_id))
            )
            project_row = project_info.first()

            sandbox_info = {
                "project_id": project_id,
                "project_name": project_row.name if project_row else "Unknown",
                "container_id": container.container_id[:12],
                "user_id": container.user_id,
                "user_email": user_row.email if user_row else "Unknown",
                "user_name": user_row.full_name if user_row else None,
                "status": container.status.value,
                "health_status": health_status,
                "consecutive_failures": consecutive_failures,
                "restart_count": restart_count,
                "last_health_check": last_check,
                "created_at": container.created_at.isoformat(),
                "last_activity": container.last_activity.isoformat(),
                "idle_time_minutes": int((datetime.utcnow() - container.last_activity).total_seconds() / 60),
                "port_mappings": container.port_mappings,
                "active_port": container.active_port,
                "resource_usage": stats if stats else {
                    "cpu_percent": 0,
                    "memory_usage_mb": 0,
                    "memory_limit_mb": 512,
                    "memory_percent": 0,
                    "status": "unknown"
                }
            }

            sandboxes.append(sandbox_info)

        # Sort by specified field
        reverse = sort_order == "desc"
        if sort_by == "last_activity":
            sandboxes.sort(key=lambda x: x["last_activity"], reverse=reverse)
        elif sort_by == "created_at":
            sandboxes.sort(key=lambda x: x["created_at"], reverse=reverse)
        elif sort_by == "idle_time_minutes":
            sandboxes.sort(key=lambda x: x["idle_time_minutes"], reverse=reverse)
        elif sort_by == "project_name":
            sandboxes.sort(key=lambda x: x["project_name"].lower(), reverse=reverse)

        # Paginate
        total = len(sandboxes)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = sandboxes[start:end]

        return {
            "items": paginated,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    except Exception as e:
        logger.error(f"Failed to list sandboxes: {e}")
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
            "error": str(e)
        }


@router.get("/stats")
async def get_sandbox_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get aggregate statistics for all sandboxes.
    """
    try:
        from app.modules.execution.container_manager import get_container_manager, get_port_manager
        from app.modules.execution.health_monitor import get_health_monitor, HealthStatus

        manager = get_container_manager()
        health_monitor = get_health_monitor()
        port_manager = get_port_manager()

        total_sandboxes = len(manager.containers)
        running = 0
        stopped = 0
        error = 0
        healthy = 0
        unhealthy = 0

        total_cpu = 0
        total_memory = 0

        for project_id, container in manager.containers.items():
            # Count by status
            if container.status.value == "running":
                running += 1
            elif container.status.value == "stopped":
                stopped += 1
            elif container.status.value == "error":
                error += 1

            # Count by health
            if health_monitor:
                health_state = health_monitor.get_health(project_id)
                if health_state and health_state.last_check:
                    if health_state.last_check.status == HealthStatus.HEALTHY:
                        healthy += 1
                    else:
                        unhealthy += 1

            # Sum resources
            stats = await manager.get_container_stats(project_id)
            if stats:
                total_cpu += stats.get("cpu_percent", 0)
                total_memory += stats.get("memory_usage_mb", 0)

        # Get port stats
        port_stats = port_manager.get_stats()

        # Get unhealthy containers list
        unhealthy_list = []
        if health_monitor:
            unhealthy_list = health_monitor.get_unhealthy_containers()

        return {
            "total_sandboxes": total_sandboxes,
            "by_status": {
                "running": running,
                "stopped": stopped,
                "error": error
            },
            "by_health": {
                "healthy": healthy,
                "unhealthy": unhealthy,
                "unknown": total_sandboxes - healthy - unhealthy
            },
            "resource_usage": {
                "total_cpu_percent": round(total_cpu, 2),
                "total_memory_mb": round(total_memory, 2),
                "avg_cpu_percent": round(total_cpu / max(running, 1), 2),
                "avg_memory_mb": round(total_memory / max(running, 1), 2)
            },
            "ports": port_stats,
            "unhealthy_containers": unhealthy_list[:10]  # Top 10 unhealthy
        }

    except Exception as e:
        logger.error(f"Failed to get sandbox stats: {e}")
        return {
            "total_sandboxes": 0,
            "by_status": {"running": 0, "stopped": 0, "error": 0},
            "by_health": {"healthy": 0, "unhealthy": 0, "unknown": 0},
            "resource_usage": {"total_cpu_percent": 0, "total_memory_mb": 0},
            "ports": {"total_allocated": 0, "available": 0},
            "error": str(e)
        }


@router.get("/{project_id}")
async def get_sandbox_details(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get detailed info for a specific sandbox.
    """
    try:
        from app.modules.execution.container_manager import get_container_manager
        from app.modules.execution.health_monitor import get_health_monitor

        manager = get_container_manager()
        health_monitor = get_health_monitor()

        if project_id not in manager.containers:
            raise HTTPException(status_code=404, detail="Sandbox not found")

        container = manager.containers[project_id]

        # Get health history
        health_info = {}
        if health_monitor:
            health_state = health_monitor.get_health(project_id)
            if health_state:
                health_info = {
                    "status": health_state.last_check.status.value if health_state.last_check else "unknown",
                    "consecutive_failures": health_state.last_check.consecutive_failures if health_state.last_check else 0,
                    "response_time_ms": health_state.last_check.response_time_ms if health_state.last_check else 0,
                    "error_message": health_state.last_check.error_message if health_state.last_check else None,
                    "restart_count": health_state.restart_count,
                    "last_restart": health_state.last_restart.isoformat() if health_state.last_restart else None,
                    "last_healthy": health_state.last_healthy.isoformat() if health_state.last_healthy else None,
                    "is_monitored": health_state.is_monitored
                }

        # Get real-time stats
        stats = await manager.get_container_stats(project_id)

        # Get user info
        user_info = await db.execute(
            select(User.email, User.full_name, User.role).where(User.id == UUID(container.user_id))
        )
        user_row = user_info.first()

        # Get project info
        project_info = await db.execute(
            select(Project).where(Project.id == UUID(project_id))
        )
        project_row = project_info.scalar_one_or_none()

        # Get all preview URLs
        preview_urls = manager.get_all_preview_urls(project_id)

        return {
            "project_id": project_id,
            "project_name": project_row.name if project_row else "Unknown",
            "project_type": project_row.project_type if project_row else "unknown",
            "container_id": container.container_id,
            "user": {
                "id": container.user_id,
                "email": user_row.email if user_row else "Unknown",
                "name": user_row.full_name if user_row else None,
                "role": user_row.role if user_row else None
            },
            "status": container.status.value,
            "health": health_info,
            "resource_usage": stats,
            "config": {
                "memory_limit": container.config.memory_limit,
                "cpu_limit": container.config.cpu_limit,
                "idle_timeout": container.config.idle_timeout,
                "max_lifetime": container.config.max_lifetime,
                "command_timeout": container.config.command_timeout
            },
            "networking": {
                "port_mappings": container.port_mappings,
                "active_port": container.active_port,
                "preview_urls": preview_urls
            },
            "timestamps": {
                "created_at": container.created_at.isoformat(),
                "last_activity": container.last_activity.isoformat(),
                "uptime_minutes": int((datetime.utcnow() - container.created_at).total_seconds() / 60),
                "idle_time_minutes": int((datetime.utcnow() - container.last_activity).total_seconds() / 60),
                "is_expired": container.is_expired()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sandbox details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/restart")
async def restart_sandbox(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Restart a sandbox container.
    """
    try:
        from app.modules.execution.container_manager import get_container_manager
        import docker

        manager = get_container_manager()

        if project_id not in manager.containers:
            raise HTTPException(status_code=404, detail="Sandbox not found")

        container_info = manager.containers[project_id]

        # Get Docker container and restart
        docker_container = manager.docker.containers.get(container_info.container_id)
        docker_container.restart(timeout=30)

        # Update status
        container_info.status = manager.containers[project_id].status
        container_info.touch()

        # Log audit
        from app.models.audit_log import AuditLog
        audit_log = AuditLog(
            admin_id=admin.id,
            action="sandbox_restarted",
            target_type="sandbox",
            target_id=UUID(project_id),
            details={"container_id": container_info.container_id[:12]}
        )
        db.add(audit_log)
        await db.commit()

        return {"success": True, "message": f"Sandbox {project_id} restarted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restart sandbox: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/stop")
async def stop_sandbox(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Stop a sandbox container.
    """
    try:
        from app.modules.execution.container_manager import get_container_manager

        manager = get_container_manager()

        if project_id not in manager.containers:
            raise HTTPException(status_code=404, detail="Sandbox not found")

        success = await manager.stop_container(project_id)

        if success:
            # Log audit
            from app.models.audit_log import AuditLog
            audit_log = AuditLog(
                admin_id=admin.id,
                action="sandbox_stopped",
                target_type="sandbox",
                target_id=UUID(project_id),
                details={}
            )
            db.add(audit_log)
            await db.commit()

        return {"success": success, "message": f"Sandbox {project_id} stopped" if success else "Failed to stop"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop sandbox: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_sandbox(
    project_id: str,
    delete_files: bool = Query(False, description="Also delete project files"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Delete a sandbox container.
    """
    try:
        from app.modules.execution.container_manager import get_container_manager

        manager = get_container_manager()

        if project_id not in manager.containers:
            raise HTTPException(status_code=404, detail="Sandbox not found")

        success = await manager.delete_container(project_id, delete_files=delete_files)

        if success:
            # Log audit
            from app.models.audit_log import AuditLog
            audit_log = AuditLog(
                admin_id=admin.id,
                action="sandbox_deleted",
                target_type="sandbox",
                target_id=UUID(project_id),
                details={"files_deleted": delete_files}
            )
            db.add(audit_log)
            await db.commit()

        return {"success": success, "message": f"Sandbox {project_id} deleted" if success else "Failed to delete"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete sandbox: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup-expired")
async def cleanup_expired_sandboxes(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Manually trigger cleanup of expired sandboxes.
    """
    try:
        from app.modules.execution.container_manager import get_container_manager

        manager = get_container_manager()
        cleaned = await manager.cleanup_expired()

        # Log audit
        from app.models.audit_log import AuditLog
        audit_log = AuditLog(
            admin_id=admin.id,
            action="sandboxes_cleanup",
            target_type="sandbox",
            target_id=None,
            details={"cleaned_count": cleaned}
        )
        db.add(audit_log)
        await db.commit()

        return {"success": True, "cleaned_count": cleaned}

    except Exception as e:
        logger.error(f"Failed to cleanup sandboxes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
