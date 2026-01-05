"""
Docker Client Helper with TLS Support

Provides a consistent way to create Docker clients with TLS for secure
communication with remote Docker hosts (EC2 sandbox).

Usage:
    from app.services.docker_client_helper import get_docker_client
    client = get_docker_client()
"""

import os
import docker
import docker.tls
from typing import Optional
from app.core.logging_config import logger
from app.core.config import settings


def get_docker_client(timeout: int = 30) -> Optional[docker.DockerClient]:
    """
    Get a Docker client configured for the sandbox environment.

    Supports:
    - TLS-secured connection to remote Docker (uses settings.DOCKER_TLS_*)
    - Fallback to non-TLS for development
    - Dynamic host discovery via SSM parameter

    Args:
        timeout: Connection timeout in seconds

    Returns:
        docker.DockerClient or None if connection fails
    """
    # Get sandbox Docker host
    sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST", "")

    if not sandbox_docker_host:
        # Try to get from SSM parameter
        try:
            import boto3
            ssm_client = boto3.client('ssm', region_name=settings.AWS_REGION or "ap-south-1")
            param_response = ssm_client.get_parameter(Name="/bharatbuild/sandbox/docker-host")
            sandbox_docker_host = param_response['Parameter']['Value']
            logger.info(f"[DockerHelper] Got Docker host from SSM: {sandbox_docker_host}")
        except Exception as e:
            logger.debug(f"[DockerHelper] Could not get Docker host from SSM: {e}")

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
        return None


def get_docker_client_for_ssm_restore(instance_id: str = None) -> dict:
    """
    Get Docker client info for SSM-based restore.

    For restore operations, we prefer SSM over direct Docker API.
    This returns the instance ID and region for SSM commands.

    Returns:
        dict with 'instance_id', 'region', 'available'
    """
    region = settings.AWS_REGION or "ap-south-1"

    if instance_id:
        return {"instance_id": instance_id, "region": region, "available": True}

    # Try to get from env var first
    instance_id = os.environ.get("SANDBOX_EC2_INSTANCE_ID", "")

    if not instance_id:
        # Try to get from SSM parameter
        try:
            import boto3
            ssm_client = boto3.client('ssm', region_name=region)
            param_response = ssm_client.get_parameter(Name="/bharatbuild/sandbox/instance-id")
            instance_id = param_response['Parameter']['Value']
            logger.info(f"[DockerHelper] Got instance ID from SSM: {instance_id}")
        except Exception as e:
            logger.warning(f"[DockerHelper] Could not get instance ID from SSM: {e}")
            return {"instance_id": None, "region": region, "available": False}

    return {"instance_id": instance_id, "region": region, "available": True}
