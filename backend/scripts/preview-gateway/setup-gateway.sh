#!/bin/bash
# ============================================
# BharatBuild AI - Preview Gateway Setup
# Run this on the EC2 sandbox instance
# ============================================

set -e

echo "============================================"
echo "  BharatBuild Preview Gateway Setup"
echo "============================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running!"
    exit 1
fi

# Create the Docker network if it doesn't exist
echo "[1/4] Creating Docker network 'bharatbuild-sandbox'..."
if ! docker network inspect bharatbuild-sandbox > /dev/null 2>&1; then
    docker network create bharatbuild-sandbox
    echo "  Created network: bharatbuild-sandbox"
else
    echo "  Network already exists: bharatbuild-sandbox"
fi

# Stop and remove existing gateway if running
echo "[2/4] Stopping existing gateway (if any)..."
docker stop preview-gateway 2>/dev/null || true
docker rm preview-gateway 2>/dev/null || true

# Pull the latest Traefik image
echo "[3/4] Pulling Traefik image..."
docker pull traefik:v3.0

# Start Traefik gateway
echo "[4/4] Starting Preview Gateway..."
docker run -d \
    --name preview-gateway \
    --restart unless-stopped \
    --network bharatbuild-sandbox \
    -p 8080:8080 \
    -p 8081:8080 \
    -v /var/run/docker.sock:/var/run/docker.sock:ro \
    traefik:v3.0 \
    --api.insecure=true \
    --api.dashboard=true \
    --providers.docker=true \
    --providers.docker.exposedbydefault=false \
    --providers.docker.network=bharatbuild-sandbox \
    --entrypoints.web.address=:8080 \
    --log.level=INFO \
    --accesslog=true

echo ""
echo "============================================"
echo "  Preview Gateway Started Successfully!"
echo "============================================"
echo ""
echo "Gateway is listening on:"
echo "  - Port 8080: Preview proxy endpoint"
echo "  - Port 8081: Traefik dashboard (for debugging)"
echo ""
echo "To test the gateway:"
echo "  curl http://localhost:8080/"
echo ""
echo "To view the dashboard:"
echo "  http://<EC2-IP>:8081/dashboard/"
echo ""
echo "To check gateway logs:"
echo "  docker logs -f preview-gateway"
echo ""
