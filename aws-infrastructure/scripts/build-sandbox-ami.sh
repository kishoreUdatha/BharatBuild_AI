#!/bin/bash
# =============================================================================
# BharatBuild Sandbox AMI Builder
# =============================================================================
# This script prepares an EC2 instance to be captured as a custom AMI
# with Docker, docker-compose, and all base images pre-installed.
#
# Usage:
# 1. Launch a t3.xlarge Amazon Linux 2023 instance
# 2. SSH into the instance
# 3. Run this script: sudo bash build-sandbox-ami.sh
# 4. Create AMI from the instance in AWS Console
# =============================================================================

set -e

echo "=============================================="
echo "BharatBuild Sandbox AMI Builder"
echo "=============================================="

# Update system
echo "[1/8] Updating system packages..."
dnf update -y

# Install Docker
echo "[2/8] Installing Docker..."
dnf install -y docker
systemctl enable docker

# Configure Docker daemon for remote access
echo "[3/8] Configuring Docker daemon..."
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'DOCKERCONFIG'
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"],
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "live-restore": true
}
DOCKERCONFIG

# Override Docker service
mkdir -p /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/override.conf <<'OVERRIDE'
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd
OVERRIDE

systemctl daemon-reload
systemctl start docker

# Install Docker Compose
echo "[4/8] Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create sandbox network
echo "[5/8] Creating Docker network..."
docker network create bharatbuild-sandbox || true

# Pull all base images
echo "[6/8] Pulling Docker images (this takes 10-15 minutes)..."

# Frontend / JavaScript
echo "  - Pulling Node.js images..."
docker pull node:18-alpine &
docker pull node:20-alpine &
docker pull node:22-alpine &

# Python
echo "  - Pulling Python images..."
docker pull python:3.11-slim &
docker pull python:3.12-slim &
docker pull python:3.11 &

# Java / JVM
echo "  - Pulling Java images..."
docker pull openjdk:17-slim &
docker pull openjdk:21-slim &
docker pull maven:3.9-eclipse-temurin-17 &
docker pull maven:3.9-eclipse-temurin-21 &
docker pull gradle:8-jdk17-alpine &

# Go
echo "  - Pulling Go images..."
docker pull golang:1.21-alpine &
docker pull golang:1.22-alpine &

# .NET
echo "  - Pulling .NET images..."
docker pull mcr.microsoft.com/dotnet/sdk:8.0 &
docker pull mcr.microsoft.com/dotnet/aspnet:8.0 &

# Rust
echo "  - Pulling Rust images..."
docker pull rust:1.75-slim &

# PHP
echo "  - Pulling PHP images..."
docker pull php:8.3-apache &
docker pull php:8.3-fpm-alpine &

# Ruby
echo "  - Pulling Ruby images..."
docker pull ruby:3.3-slim &

# Databases
echo "  - Pulling database images..."
docker pull postgres:15-alpine &
docker pull postgres:16-alpine &
docker pull mysql:8.0 &
docker pull mongo:7 &
docker pull redis:7-alpine &

# Utilities
echo "  - Pulling utility images..."
docker pull nginx:alpine &
docker pull alpine:latest &
docker pull docker/compose:latest &
docker pull busybox:latest &

# Wait for all pulls to complete
echo "  - Waiting for all image pulls to complete..."
wait
echo "  - All images pulled successfully!"

# Install Nginx for reverse proxy
echo "[7/8] Installing Nginx..."
dnf install -y nginx
systemctl enable nginx

# Create Nginx config for sandbox reverse proxy
cat > /etc/nginx/conf.d/sandbox.conf <<'NGINXCONFIG'
server {
    listen 8080;
    server_name _;

    # Health check endpoint for ALB
    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }

    # Sandbox proxy - matches /sandbox/{port}/* and proxies to localhost:{port}/*
    location ~ ^/sandbox/([0-9]+)(/.*)?$ {
        set $target_port $1;
        set $path $2;

        if ($path = '') {
            set $path /;
        }

        proxy_pass http://127.0.0.1:$target_port$path$is_args$args;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
NGINXCONFIG

systemctl start nginx

# Create startup script that updates SSM parameter with current IP
echo "[8/8] Creating startup script for dynamic IP..."
cat > /usr/local/bin/update-sandbox-ip.sh <<'STARTUPSCRIPT'
#!/bin/bash
# Update SSM parameter with this instance's private IP
INSTANCE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)

# Update SSM parameters
aws ssm put-parameter \
  --region "$REGION" \
  --name "/bharatbuild/sandbox/docker-host" \
  --value "tcp://${INSTANCE_IP}:2375" \
  --type String \
  --overwrite || true

aws ssm put-parameter \
  --region "$REGION" \
  --name "/bharatbuild/sandbox/instance-id" \
  --value "$INSTANCE_ID" \
  --type String \
  --overwrite || true

aws ssm put-parameter \
  --region "$REGION" \
  --name "/bharatbuild/sandbox/private-ip" \
  --value "$INSTANCE_IP" \
  --type String \
  --overwrite || true

echo "Updated SSM parameters: IP=$INSTANCE_IP, Instance=$INSTANCE_ID"
STARTUPSCRIPT

chmod +x /usr/local/bin/update-sandbox-ip.sh

# Create systemd service to run on boot
cat > /etc/systemd/system/update-sandbox-ip.service <<'SYSTEMD'
[Unit]
Description=Update SSM with Sandbox IP
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/update-sandbox-ip.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
SYSTEMD

systemctl daemon-reload
systemctl enable update-sandbox-ip.service

# Create workspace directory
mkdir -p /opt/sandbox/workspaces
chmod 777 /opt/sandbox/workspaces

# Clean up for AMI
echo "Cleaning up for AMI creation..."
dnf clean all
rm -rf /var/cache/dnf
rm -rf /tmp/*
rm -rf /var/tmp/*

# List installed images
echo ""
echo "=============================================="
echo "AMI Build Complete!"
echo "=============================================="
echo ""
echo "Docker images installed:"
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"
echo ""
echo "Next steps:"
echo "1. Go to AWS Console > EC2 > Instances"
echo "2. Select this instance"
echo "3. Actions > Image and templates > Create image"
echo "4. Name: bharatbuild-sandbox-ami-$(date +%Y%m%d)"
echo "5. Wait for AMI to be available"
echo "6. Update terraform with the new AMI ID"
echo ""
