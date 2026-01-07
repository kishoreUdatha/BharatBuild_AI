"""
Docker Client Helper with TLS Support

Provides a consistent way to create Docker clients with TLS for secure
communication with remote Docker hosts (EC2 sandbox).

Usage:
    from app.services.docker_client_helper import get_docker_client
    client = get_docker_client()
"""

import os
import time
import docker
import docker.tls
from typing import Optional
from app.core.logging_config import logger
from app.core.config import settings


# TTL Cache for SSM parameters (5 minutes)
# Fixes: ASG replaces EC2 → new IP → old cached IP fails
_ssm_cache = {
    "docker_host": {"value": None, "expires": 0},
    "instance_id": {"value": None, "expires": 0}
}
_SSM_CACHE_TTL = 300  # 5 minutes


def _invalidate_cache(cache_key: str = None):
    """
    Invalidate SSM cache on connection failure.

    This ensures we fetch fresh IP from SSM on next call,
    reducing stale window from 5 minutes to 1 failed request.
    """
    if cache_key:
        _ssm_cache[cache_key] = {"value": None, "expires": 0}
        logger.info(f"[DockerHelper] Invalidated cache for {cache_key}")
    else:
        # Invalidate all
        for key in _ssm_cache:
            _ssm_cache[key] = {"value": None, "expires": 0}
        logger.info("[DockerHelper] Invalidated all SSM cache (connection failed)")


def _get_ssm_param_cached(param_name: str, cache_key: str) -> Optional[str]:
    """
    Get SSM parameter with TTL caching.

    This ensures we pick up new IP addresses when ASG replaces EC2 instances,
    while not hammering SSM on every Docker call.
    """
    now = time.time()

    # Check cache
    if _ssm_cache[cache_key]["value"] and _ssm_cache[cache_key]["expires"] > now:
        return _ssm_cache[cache_key]["value"]

    # Fetch fresh from SSM
    try:
        import boto3
        ssm_client = boto3.client('ssm', region_name=settings.AWS_REGION or "ap-south-1")
        param_response = ssm_client.get_parameter(Name=param_name)
        value = param_response['Parameter']['Value']

        # Update cache
        _ssm_cache[cache_key] = {"value": value, "expires": now + _SSM_CACHE_TTL}
        logger.info(f"[DockerHelper] Refreshed {param_name} from SSM: {value} (TTL: {_SSM_CACHE_TTL}s)")
        return value
    except Exception as e:
        logger.debug(f"[DockerHelper] Could not get {param_name} from SSM: {e}")
        # Return stale cache if available
        if _ssm_cache[cache_key]["value"]:
            logger.warning(f"[DockerHelper] Using stale cache for {param_name}")
            return _ssm_cache[cache_key]["value"]
        return None


def get_docker_client(timeout: int = 30) -> Optional[docker.DockerClient]:
    """
    Get a Docker client configured for the sandbox environment.

    Supports:
    - TLS-secured connection to remote Docker (uses settings.DOCKER_TLS_*)
    - Fallback to non-TLS for development
    - Dynamic host discovery via SSM parameter with TTL cache

    Args:
        timeout: Connection timeout in seconds

    Returns:
        docker.DockerClient or None if connection fails
    """
    # ALWAYS fetch from SSM with TTL cache (fixes ASG IP change issue)
    # Don't use env var - it's stale after container starts
    sandbox_docker_host = _get_ssm_param_cached("/bharatbuild/sandbox/docker-host", "docker_host")

    if not sandbox_docker_host:
        # Fallback to local Docker
        try:
            client = docker.from_env()
            client.ping()
            logger.info("[DockerHelper] Connected to local Docker")
            return client
        except Exception as e:
            logger.error(f"[DockerHelper] Local Docker not available: {e}")
            return None

    # Try TLS connection first
    if settings.DOCKER_TLS_ENABLED:
        client = _try_tls_connection(sandbox_docker_host, timeout)
        if client:
            return client

    # Fallback to non-TLS (for development/internal VPC)
    try:
        client = docker.DockerClient(base_url=sandbox_docker_host, timeout=timeout)
        client.ping()
        logger.info(f"[DockerHelper] Connected to Docker (no TLS): {sandbox_docker_host}")
        return client
    except Exception as e:
        logger.error(f"[DockerHelper] Docker connection failed: {e}")
        # Invalidate cache so next call fetches fresh IP from SSM
        # This reduces stale window from 5 min to 1 failed request
        _invalidate_cache("docker_host")
        return None


def _try_tls_connection(docker_host: str, timeout: int) -> Optional[docker.DockerClient]:
    """
    Try to connect to Docker with TLS.

    Args:
        docker_host: Docker host URL (tcp://...)
        timeout: Connection timeout

    Returns:
        docker.DockerClient or None if TLS connection fails
    """
    # Check if certs exist
    ca_cert = settings.DOCKER_TLS_CA_CERT
    client_cert = settings.DOCKER_TLS_CLIENT_CERT
    client_key = settings.DOCKER_TLS_CLIENT_KEY

    if not all([os.path.exists(ca_cert), os.path.exists(client_cert), os.path.exists(client_key)]):
        logger.debug(f"[DockerHelper] TLS certs not found at {ca_cert}, skipping TLS")
        return None

    try:
        tls_config = docker.tls.TLSConfig(
            ca_cert=ca_cert,
            client_cert=(client_cert, client_key),
            verify=settings.DOCKER_TLS_VERIFY
        )

        # Convert tcp:// to https:// and use TLS port (2376)
        secure_host = docker_host.replace("tcp://", "https://").replace(":2375", ":2376")

        client = docker.DockerClient(base_url=secure_host, tls=tls_config, timeout=timeout)
        client.ping()
        logger.info(f"[DockerHelper] Connected to Docker via TLS: {secure_host}")
        return client

    except Exception as e:
        logger.warning(f"[DockerHelper] TLS connection failed: {e}")
        # Invalidate cache so next call fetches fresh IP from SSM
        _invalidate_cache("docker_host")
        return None


def get_docker_client_for_ssm_restore(instance_id: str = None) -> dict:
    """
    Get Docker client info for SSM-based restore.

    For restore operations, we prefer SSM over direct Docker API.
    This returns the instance ID and region for SSM commands.

    Uses TTL cache to handle ASG instance replacements automatically.

    Returns:
        dict with 'instance_id', 'region', 'available'
    """
    region = settings.AWS_REGION or "ap-south-1"

    if instance_id:
        return {"instance_id": instance_id, "region": region, "available": True}

    # ALWAYS fetch from SSM with TTL cache (fixes ASG instance replacement issue)
    # Don't use env var - it's stale after container starts
    instance_id = _get_ssm_param_cached("/bharatbuild/sandbox/instance-id", "instance_id")

    if not instance_id:
        return {"instance_id": None, "region": region, "available": False}

    return {"instance_id": instance_id, "region": region, "available": True}
