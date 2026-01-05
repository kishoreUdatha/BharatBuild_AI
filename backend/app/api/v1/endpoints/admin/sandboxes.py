"""
Admin Sandbox/Container Health Management endpoints.
Provides visibility into all user sandboxes and their health status.
"""
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID
import os
import re
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
            # TLS-enabled docker client
            from app.services.docker_client_helper import get_docker_client as get_tls_client
            client = get_tls_client(timeout=10)
            if not client:
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
    In EC2 mode, queries Docker directly for real-time container info.

    Returns:
        List of sandboxes with health status, resource usage, and user info
    """
    try:
        sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")

        # If remote EC2 mode, query Docker directly
        if sandbox_docker_host:
            return await _list_ec2_sandboxes(page, page_size, status, sort_by, sort_order, db)

        # Local mode - use in-memory tracking
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


async def _list_ec2_sandboxes(
    page: int,
    page_size: int,
    status: Optional[str],
    sort_by: str,
    sort_order: str,
    db: AsyncSession
):
    """
    List sandboxes from EC2 Docker directly.
    Only shows BharatBuild containers (docker-compose projects).
    """
    import docker
    import re

    sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")

    try:
        # TLS-enabled docker client
        from app.services.docker_client_helper import get_docker_client as get_tls_client
        client = get_tls_client(timeout=10)
        if not client:
            client = docker.DockerClient(base_url=sandbox_docker_host, timeout=10)
        all_containers = client.containers.list(all=True)
    except Exception as e:
        logger.error(f"Failed to connect to EC2 Docker: {e}")
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
            "error": f"Cannot connect to EC2 Docker: {e}"
        }

    sandboxes = []
    now = datetime.utcnow()

    # Group containers by project (docker-compose project name)
    projects = {}
    for container in all_containers:
        name = container.name
        # Match bharatbuild_{project_id}_{service}_1 pattern
        match = re.match(r'bharatbuild_([a-f0-9-]+)_(.+)_\d+$', name, re.IGNORECASE)
        if not match:
            continue

        project_id = match.group(1)
        service = match.group(2)

        if project_id not in projects:
            projects[project_id] = {
                "containers": [],
                "services": {}
            }

        projects[project_id]["containers"].append(container)
        projects[project_id]["services"][service] = {
            "status": container.status,
            "id": container.short_id
        }

    # Build sandbox info for each project
    for project_id, project_data in projects.items():
        containers = project_data["containers"]
        services = project_data["services"]

        # Determine overall status from containers
        statuses = [c.status for c in containers]
        if all(s == "running" for s in statuses):
            overall_status = "running"
        elif any(s == "running" for s in statuses):
            overall_status = "partial"
        elif any(s == "restarting" for s in statuses):
            overall_status = "error"
        else:
            overall_status = "stopped"

        # Filter by status
        if status:
            if status == "running" and overall_status not in ["running", "partial"]:
                continue
            elif status == "stopped" and overall_status != "stopped":
                continue
            elif status == "error" and overall_status != "error":
                continue

        # Get timestamps from first container
        first_container = containers[0]
        attrs = first_container.attrs
        state = attrs.get("State", {})

        created_at = now
        last_activity = now

        created_str = attrs.get("Created", "")
        started_str = state.get("StartedAt", "")

        if created_str:
            try:
                created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00").split(".")[0]).replace(tzinfo=None)
            except:
                pass

        if started_str and started_str != "0001-01-01T00:00:00Z":
            try:
                last_activity = datetime.fromisoformat(started_str.replace("Z", "+00:00").split(".")[0]).replace(tzinfo=None)
            except:
                pass

        idle_minutes = int((now - last_activity).total_seconds() / 60)

        # Determine health status
        if overall_status == "running":
            health_status = "healthy" if idle_minutes < 30 else "idle"
        elif overall_status == "error":
            health_status = "unhealthy"
        else:
            health_status = "unknown"

        # Get project info from DB
        project_name = f"Project {project_id[:8]}"
        user_email = "Unknown"
        user_name = None
        user_id_str = None

        try:
            project_info = await db.execute(
                select(Project.name, Project.user_id).where(Project.id == UUID(project_id))
            )
            project_row = project_info.first()
            if project_row:
                project_name = project_row.name
                user_id_str = str(project_row.user_id)

                user_info = await db.execute(
                    select(User.email, User.full_name).where(User.id == project_row.user_id)
                )
                user_row = user_info.first()
                if user_row:
                    user_email = user_row.email
                    user_name = user_row.full_name
        except Exception as e:
            logger.warning(f"Failed to get project/user info for {project_id}: {e}")

        sandbox_info = {
            "project_id": project_id,
            "project_name": project_name,
            "container_id": first_container.short_id,
            "user_id": user_id_str,
            "user_email": user_email,
            "user_name": user_name,
            "status": overall_status,
            "health_status": health_status,
            "consecutive_failures": 0,
            "restart_count": 0,
            "last_health_check": now.isoformat(),
            "created_at": created_at.isoformat(),
            "last_activity": last_activity.isoformat(),
            "idle_time_minutes": idle_minutes,
            "port_mappings": {},
            "active_port": None,
            "services": services,
            "container_count": len(containers),
            "resource_usage": {
                "cpu_percent": 0,
                "memory_usage_mb": 0,
                "memory_limit_mb": 512,
                "memory_percent": 0,
                "status": overall_status
            }
        }

        sandboxes.append(sandbox_info)

    # Sort
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


@router.get("/stats")
async def get_sandbox_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get aggregate statistics for all sandboxes.
    In EC2 mode, queries Docker directly.
    """
    try:
        sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")

        # If EC2 mode, query Docker directly
        if sandbox_docker_host:
            return await _get_ec2_sandbox_stats()

        # Local mode - use in-memory tracking
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


async def _get_ec2_sandbox_stats():
    """Get sandbox stats by querying EC2 Docker directly."""
    import docker
    import re

    sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")

    try:
        # TLS-enabled docker client
        from app.services.docker_client_helper import get_docker_client as get_tls_client
        client = get_tls_client(timeout=10)
        if not client:
            client = docker.DockerClient(base_url=sandbox_docker_host, timeout=10)
        all_containers = client.containers.list(all=True)
    except Exception as e:
        logger.error(f"Failed to connect to EC2 Docker for stats: {e}")
        return {
            "total_sandboxes": 0,
            "by_status": {"running": 0, "stopped": 0, "error": 0},
            "by_health": {"healthy": 0, "unhealthy": 0, "unknown": 0},
            "resource_usage": {"total_cpu_percent": 0, "total_memory_mb": 0, "avg_cpu_percent": 0, "avg_memory_mb": 0},
            "ports": {"total_allocated": 0, "available": 100},
            "error": f"Cannot connect to EC2 Docker: {e}"
        }

    # Group by project and count stats
    projects = {}
    now = datetime.utcnow()

    for container in all_containers:
        name = container.name
        match = re.match(r'bharatbuild_([a-f0-9-]+)_(.+)_\d+$', name, re.IGNORECASE)
        if not match:
            continue

        project_id = match.group(1)
        if project_id not in projects:
            projects[project_id] = {"containers": [], "statuses": []}

        projects[project_id]["containers"].append(container)
        projects[project_id]["statuses"].append(container.status)

    # Calculate stats
    total_sandboxes = len(projects)
    running = 0
    stopped = 0
    error = 0
    healthy = 0
    unhealthy = 0

    for project_id, data in projects.items():
        statuses = data["statuses"]
        if all(s == "running" for s in statuses):
            running += 1
            # Check idle time for health
            first_container = data["containers"][0]
            started_str = first_container.attrs.get("State", {}).get("StartedAt", "")
            if started_str and started_str != "0001-01-01T00:00:00Z":
                try:
                    started_at = datetime.fromisoformat(started_str.replace("Z", "+00:00").split(".")[0]).replace(tzinfo=None)
                    idle_minutes = (now - started_at).total_seconds() / 60
                    if idle_minutes < 30:
                        healthy += 1
                    else:
                        unhealthy += 1
                except:
                    healthy += 1
            else:
                healthy += 1
        elif any(s == "running" for s in statuses):
            running += 1
            unhealthy += 1  # Partial = unhealthy
        elif any(s == "restarting" for s in statuses):
            error += 1
            unhealthy += 1
        else:
            stopped += 1

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
            "total_cpu_percent": 0,  # Would need docker stats API
            "total_memory_mb": 0,
            "avg_cpu_percent": 0,
            "avg_memory_mb": 0
        },
        "ports": {
            "total_allocated": running * 5,  # Estimate ~5 ports per project
            "available": 100
        },
        "unhealthy_containers": []
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


@router.get("/ec2-containers")
async def list_ec2_sandbox_containers(
    admin: User = Depends(get_current_admin)
):
    """
    List all containers running on EC2 sandbox with health and idle status.
    This queries the remote EC2 Docker directly for real-time container info.
    """
    try:
        from app.services.container_executor import container_executor
        from datetime import datetime

        sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
        if not sandbox_docker_host:
            return {
                "mode": "local",
                "message": "No EC2 sandbox configured (SANDBOX_DOCKER_HOST not set)",
                "containers": []
            }

        # Use container_executor's docker client (connected to EC2)
        if not container_executor.docker_client:
            await container_executor.initialize()

        if not container_executor.docker_client:
            raise HTTPException(status_code=503, detail="Cannot connect to EC2 Docker")

        # Get all containers from EC2
        all_containers = container_executor.docker_client.containers.list(all=True)

        containers_list = []
        now = datetime.utcnow()
        idle_timeout_minutes = 30

        for container in all_containers:
            try:
                # Get container details
                attrs = container.attrs
                state = attrs.get("State", {})
                labels = attrs.get("Config", {}).get("Labels", {})

                # Parse timestamps
                created_str = attrs.get("Created", "")
                started_str = state.get("StartedAt", "")
                finished_str = state.get("FinishedAt", "")

                created_at = None
                started_at = None
                finished_at = None
                idle_minutes = 0

                if created_str:
                    try:
                        created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00").split(".")[0])
                        created_at = created_at.replace(tzinfo=None)
                    except:
                        pass

                if started_str and started_str != "0001-01-01T00:00:00Z":
                    try:
                        started_at = datetime.fromisoformat(started_str.replace("Z", "+00:00").split(".")[0])
                        started_at = started_at.replace(tzinfo=None)
                    except:
                        pass

                if finished_str and finished_str != "0001-01-01T00:00:00Z":
                    try:
                        finished_at = datetime.fromisoformat(finished_str.replace("Z", "+00:00").split(".")[0])
                        finished_at = finished_at.replace(tzinfo=None)
                    except:
                        pass

                # Calculate idle time
                project_id = labels.get("project_id", "unknown")
                is_bharatbuild = "bharatbuild" in container.name.lower()

                if container.status == "running":
                    # Check if tracked in memory
                    if project_id in container_executor.active_containers:
                        last_activity = container_executor.active_containers[project_id].get("last_activity")
                        if last_activity:
                            idle_minutes = (now - last_activity).total_seconds() / 60
                    elif started_at:
                        idle_minutes = (now - started_at).total_seconds() / 60
                elif finished_at:
                    idle_minutes = (now - finished_at).total_seconds() / 60

                # Determine health status
                health_status = "unknown"
                if container.status == "running":
                    if idle_minutes > idle_timeout_minutes:
                        health_status = "idle"
                    else:
                        health_status = "active"
                elif container.status == "exited":
                    exit_code = state.get("ExitCode", -1)
                    if exit_code == 0:
                        health_status = "stopped"
                    else:
                        health_status = "crashed"
                elif container.status == "restarting":
                    health_status = "restarting"

                # Get ports
                ports = []
                for port_config in attrs.get("NetworkSettings", {}).get("Ports", {}).values():
                    if port_config:
                        for p in port_config:
                            if p.get("HostPort"):
                                ports.append(int(p["HostPort"]))

                containers_list.append({
                    "id": container.short_id,
                    "name": container.name,
                    "status": container.status,
                    "health_status": health_status,
                    "project_id": project_id,
                    "is_bharatbuild": is_bharatbuild,
                    "image": container.image.tags[0] if container.image.tags else str(container.image.id)[:12],
                    "created_at": created_at.isoformat() if created_at else None,
                    "started_at": started_at.isoformat() if started_at else None,
                    "finished_at": finished_at.isoformat() if finished_at else None,
                    "idle_minutes": round(idle_minutes, 1),
                    "will_cleanup": idle_minutes > idle_timeout_minutes,
                    "ports": ports,
                    "exit_code": state.get("ExitCode") if container.status == "exited" else None,
                })

            except Exception as e:
                logger.warning(f"Error getting container info for {container.name}: {e}")
                continue

        # Sort by idle time (most idle first)
        containers_list.sort(key=lambda x: x["idle_minutes"], reverse=True)

        # Summary stats
        summary = {
            "total": len(containers_list),
            "running": len([c for c in containers_list if c["status"] == "running"]),
            "stopped": len([c for c in containers_list if c["status"] == "exited"]),
            "restarting": len([c for c in containers_list if c["status"] == "restarting"]),
            "bharatbuild": len([c for c in containers_list if c["is_bharatbuild"]]),
            "idle_30min": len([c for c in containers_list if c["will_cleanup"]]),
            "active": len([c for c in containers_list if c["health_status"] == "active"]),
        }

        return {
            "mode": "ec2",
            "sandbox_host": sandbox_docker_host,
            "checked_at": now.isoformat(),
            "idle_timeout_minutes": idle_timeout_minutes,
            "summary": summary,
            "containers": containers_list
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list EC2 containers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ec2-containers/{container_id}/stop")
async def stop_ec2_container(
    container_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Stop a specific container on EC2 sandbox."""
    try:
        from app.services.container_executor import container_executor

        if not container_executor.docker_client:
            await container_executor.initialize()

        container = container_executor.docker_client.containers.get(container_id)
        container_name = container.name

        if container.status == "running":
            container.stop(timeout=10)

        # Log audit
        from app.models.audit_log import AuditLog
        audit_log = AuditLog(
            admin_id=admin.id,
            action="ec2_container_stop",
            target_type="container",
            target_id=container_id,
            details={"container_name": container_name}
        )
        db.add(audit_log)
        await db.commit()

        return {"success": True, "container_id": container_id, "action": "stopped"}

    except Exception as e:
        logger.error(f"Failed to stop EC2 container {container_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ec2-containers/{container_id}/remove")
async def remove_ec2_container(
    container_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Remove a specific container from EC2 sandbox."""
    try:
        from app.services.container_executor import container_executor

        if not container_executor.docker_client:
            await container_executor.initialize()

        container = container_executor.docker_client.containers.get(container_id)
        container_name = container.name
        project_id = container.labels.get("project_id", "unknown")

        # Stop if running
        if container.status == "running":
            container.stop(timeout=5)

        # Remove
        container.remove(force=True)

        # Remove from active containers if tracked
        if project_id in container_executor.active_containers:
            del container_executor.active_containers[project_id]

        # Log audit
        from app.models.audit_log import AuditLog
        audit_log = AuditLog(
            admin_id=admin.id,
            action="ec2_container_remove",
            target_type="container",
            target_id=container_id,
            details={"container_name": container_name, "project_id": project_id}
        )
        db.add(audit_log)
        await db.commit()

        return {"success": True, "container_id": container_id, "action": "removed"}

    except Exception as e:
        logger.error(f"Failed to remove EC2 container {container_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ec2-containers/cleanup-idle")
async def cleanup_idle_ec2_containers(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger cleanup of idle containers (>30 min) on EC2 sandbox."""
    try:
        from app.services.container_executor import container_executor

        if not container_executor.docker_client:
            await container_executor.initialize()

        # Trigger the cleanup
        await container_executor._cleanup_orphaned_containers()

        # Log audit
        from app.models.audit_log import AuditLog
        audit_log = AuditLog(
            admin_id=admin.id,
            action="ec2_containers_cleanup",
            target_type="container",
            target_id=None,
            details={"triggered_by": "admin_manual"}
        )
        db.add(audit_log)
        await db.commit()

        return {"success": True, "message": "Idle container cleanup triggered"}

    except Exception as e:
        logger.error(f"Failed to cleanup EC2 containers: {e}")
        raise HTTPException(status_code=500, detail=str(e))
