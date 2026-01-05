# =============================================================================
# EC2 Sandbox Server - Docker Runtime for User Projects
# =============================================================================
# This EC2 instance runs Docker containers for user-generated projects
# Fargate cannot run Docker-in-Docker, so we use EC2 for sandbox execution
#
# SECURITY: Docker API uses TLS for secure remote access
# SCALING: Auto-scaling group for horizontal scaling
# =============================================================================

# =============================================================================
# Variables
# =============================================================================

variable "sandbox_instance_type" {
  description = "EC2 instance type for sandbox server"
  default     = "t3.xlarge"  # 4 vCPU, 16 GB RAM - supports ~25-30 concurrent sandboxes
}

variable "sandbox_use_spot" {
  description = "Use spot instances for sandbox (70% cheaper but can be interrupted)"
  default     = true  # Spot + ASG + Pre-baked AMI for cost savings with auto-recovery
}

variable "sandbox_key_name" {
  description = "SSH key pair name for sandbox EC2 instance"
  default     = ""  # Set to your key pair name for SSH access
}

variable "sandbox_enable_autoscaling" {
  description = "Enable auto-scaling for sandbox servers (required for spot auto-recovery)"
  default     = true  # Enabled for spot instance auto-recovery
}

variable "sandbox_custom_ami_id" {
  description = "Custom AMI ID with pre-baked Docker images (leave empty to use Amazon Linux 2023)"
  default     = "ami-0b4eaf40674cec484"  # Pre-baked AMI with Docker + all images (created 2025-01-04)
}

variable "sandbox_use_dynamic_ip" {
  description = "Use SSM Parameter Store for dynamic IP discovery (required for spot/ASG)"
  default     = true
}

variable "sandbox_min_size" {
  description = "Minimum number of sandbox instances"
  default     = 1
}

variable "sandbox_max_size" {
  description = "Maximum number of sandbox instances"
  default     = 5
}

variable "sandbox_desired_size" {
  description = "Desired number of sandbox instances"
  default     = 1
}

variable "sandbox_enable_tls" {
  description = "Enable TLS for Docker API (recommended for production)"
  default     = true
}

# =============================================================================
# AMI - Amazon Linux 2023 (latest)
# =============================================================================

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# =============================================================================
# Security Group for Sandbox Server
# =============================================================================

resource "aws_security_group" "sandbox" {
  name        = "${var.app_name}-sandbox-sg"
  description = "Security group for Docker sandbox server"
  vpc_id      = aws_vpc.main.id

  # Docker API without TLS (from ECS backend only) - for development
  ingress {
    description     = "Docker API from ECS (no TLS)"
    from_port       = 2375
    to_port         = 2375
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  # Docker API with TLS (from ECS backend only) - for production
  ingress {
    description     = "Docker API from ECS (TLS)"
    from_port       = 2376
    to_port         = 2376
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  # SSH for debugging (optional - remove in production)
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Restrict to your IP in production
  }

  # Sandbox preview ports (10000-10100) - from ALB for direct access
  ingress {
    description     = "Sandbox previews from ALB"
    from_port       = 10000
    to_port         = 10100
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Sandbox preview ports (10000-10100) - from ECS for reverse proxy
  ingress {
    description     = "Sandbox previews from ECS backend (reverse proxy)"
    from_port       = 10000
    to_port         = 10100
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  # Nginx reverse proxy port (for ALB health checks and routing)
  ingress {
    description     = "Nginx proxy from ALB"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Allow all outbound (for npm install, pip install, etc.)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.app_name}-sandbox-sg"
  }
}

# Allow ECS to connect to sandbox
resource "aws_security_group_rule" "ecs_to_sandbox" {
  type                     = "egress"
  from_port                = 2375
  to_port                  = 2375
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.sandbox.id
  security_group_id        = aws_security_group.ecs.id
  description              = "ECS to Sandbox Docker API"
}

# =============================================================================
# IAM Role for Sandbox Server
# =============================================================================

resource "aws_iam_role" "sandbox" {
  name = "${var.app_name}-sandbox-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_instance_profile" "sandbox" {
  name = "${var.app_name}-sandbox-profile"
  role = aws_iam_role.sandbox.name
}

# S3 access for project files
resource "aws_iam_role_policy" "sandbox_s3" {
  name = "${var.app_name}-sandbox-s3-policy"
  role = aws_iam_role.sandbox.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ]
      Resource = [
        aws_s3_bucket.storage.arn,
        "${aws_s3_bucket.storage.arn}/*"
      ]
    }]
  })
}

# ECR access for pulling base images
resource "aws_iam_role_policy" "sandbox_ecr" {
  name = "${var.app_name}-sandbox-ecr-policy"
  role = aws_iam_role.sandbox.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ]
      Resource = "*"
    }]
  })
}

# CloudWatch Logs access
resource "aws_iam_role_policy" "sandbox_logs" {
  name = "${var.app_name}-sandbox-logs-policy"
  role = aws_iam_role.sandbox.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
    }]
  })
}

# SSM for Session Manager access (better than SSH)
resource "aws_iam_role_policy_attachment" "sandbox_ssm" {
  role       = aws_iam_role.sandbox.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# SSM PutParameter permission for dynamic IP discovery
# Allows sandbox to update SSM parameters with its current IP on startup
resource "aws_iam_role_policy" "sandbox_ssm_params" {
  name = "${var.app_name}-sandbox-ssm-params-policy"
  role = aws_iam_role.sandbox.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ssm:PutParameter",
        "ssm:GetParameter"
      ]
      Resource = [
        "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.app_name}/sandbox/*",
        "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.app_name}/docker/*"
      ]
    }]
  })
}

# =============================================================================
# CloudWatch Log Group for Sandbox
# =============================================================================

resource "aws_cloudwatch_log_group" "sandbox" {
  name              = "/ec2/${var.app_name}/sandbox"
  retention_in_days = 7  # Short retention for sandbox logs
}

# =============================================================================
# EC2 Instance (On-Demand)
# =============================================================================

resource "aws_instance" "sandbox" {
  count = var.sandbox_use_spot ? 0 : 1

  ami                         = data.aws_ami.amazon_linux_2023.id
  instance_type               = var.sandbox_instance_type
  subnet_id                   = aws_subnet.public[0].id  # Public subnet for Elastic IP
  vpc_security_group_ids      = [aws_security_group.sandbox.id]
  iam_instance_profile        = aws_iam_instance_profile.sandbox.name
  associate_public_ip_address = true
  key_name                    = var.sandbox_key_name != "" ? var.sandbox_key_name : null

  root_block_device {
    volume_size = 100  # 100 GB for Docker images
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = base64encode(local.sandbox_user_data)

  tags = {
    Name        = "${var.app_name}-sandbox-server"
    Environment = "production"
    Project     = var.app_name
    ManagedBy   = "terraform"
  }

  lifecycle {
    ignore_changes = [ami]
  }
}

# =============================================================================
# EC2 Spot Instance (70% cheaper)
# =============================================================================

resource "aws_spot_instance_request" "sandbox" {
  # Only create standalone spot instance when ASG is disabled
  count = var.sandbox_use_spot && !var.sandbox_enable_autoscaling ? 1 : 0

  ami                         = data.aws_ami.amazon_linux_2023.id
  instance_type               = var.sandbox_instance_type
  subnet_id                   = aws_subnet.public[0].id  # Public subnet for Elastic IP
  vpc_security_group_ids      = [aws_security_group.sandbox.id]
  iam_instance_profile        = aws_iam_instance_profile.sandbox.name
  associate_public_ip_address = true
  key_name                    = var.sandbox_key_name != "" ? var.sandbox_key_name : null

  spot_type            = "persistent"
  wait_for_fulfillment = true

  root_block_device {
    volume_size = 100
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = base64encode(local.sandbox_user_data)

  tags = {
    Name = "${var.app_name}-sandbox-server-spot"
  }

  lifecycle {
    ignore_changes = [ami]
  }
}

# Tags for the actual spot instance (must be applied separately)
resource "aws_ec2_tag" "sandbox_spot_name" {
  count       = var.sandbox_use_spot && !var.sandbox_enable_autoscaling ? 1 : 0
  resource_id = aws_spot_instance_request.sandbox[0].spot_instance_id
  key         = "Name"
  value       = "${var.app_name}-sandbox-server"
}

resource "aws_ec2_tag" "sandbox_spot_environment" {
  count       = var.sandbox_use_spot && !var.sandbox_enable_autoscaling ? 1 : 0
  resource_id = aws_spot_instance_request.sandbox[0].spot_instance_id
  key         = "Environment"
  value       = "production"
}

resource "aws_ec2_tag" "sandbox_spot_project" {
  count       = var.sandbox_use_spot && !var.sandbox_enable_autoscaling ? 1 : 0
  resource_id = aws_spot_instance_request.sandbox[0].spot_instance_id
  key         = "Project"
  value       = var.app_name
}

resource "aws_ec2_tag" "sandbox_spot_managed_by" {
  count       = var.sandbox_use_spot && !var.sandbox_enable_autoscaling ? 1 : 0
  resource_id = aws_spot_instance_request.sandbox[0].spot_instance_id
  key         = "ManagedBy"
  value       = "terraform"
}

# =============================================================================
# User Data Script - Docker Setup
# =============================================================================

locals {
  sandbox_user_data = <<-EOF
#!/bin/bash
set -e

# Update system
dnf update -y

# Install Docker and OpenSSL for TLS
dnf install -y docker openssl
systemctl start docker
systemctl enable docker

# ==========================================================
# TLS Certificate Generation for Docker API Security
# This creates self-signed certs - use proper CA in production
# ==========================================================
mkdir -p /opt/docker-certs
cd /opt/docker-certs

# Generate CA key and certificate
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -days 365 -key ca-key.pem -sha256 -out ca.pem \
  -subj "/C=IN/ST=State/L=City/O=BharatBuild/CN=Docker CA"

# Generate server key
openssl genrsa -out server-key.pem 4096

# Get instance private IP for SAN - using TOKEN for IMDSv2 compatibility
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
PRIVATE_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/local-ipv4)
PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4 || echo "")

echo "Detected PRIVATE_IP: $PRIVATE_IP" >> /var/log/sandbox-setup.log
echo "Detected PUBLIC_IP: $PUBLIC_IP" >> /var/log/sandbox-setup.log

# Create server CSR with SANs - using quoted heredoc and sed for variable substitution
cat > server-csr.conf <<'CSRCONF'
[req]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = localhost
IP.1 = 127.0.0.1
IP.2 = __PRIVATE_IP__
CSRCONF

# Replace placeholder with actual IP
sed -i "s/__PRIVATE_IP__/$PRIVATE_IP/g" server-csr.conf

# Add public IP if available
if [ -n "$PUBLIC_IP" ]; then
  echo "IP.3 = $PUBLIC_IP" >> server-csr.conf
fi

# Log the CSR config for debugging
cat server-csr.conf >> /var/log/sandbox-setup.log

openssl req -subj "/CN=$PRIVATE_IP" -sha256 -new -key server-key.pem -out server.csr -config server-csr.conf

# Sign server certificate
openssl x509 -req -days 365 -sha256 -in server.csr -CA ca.pem -CAkey ca-key.pem \
  -CAcreateserial -out server-cert.pem -extfile server-csr.conf -extensions v3_req

# Generate client key and certificate (for ECS backend)
openssl genrsa -out client-key.pem 4096
openssl req -subj '/CN=client' -new -key client-key.pem -out client.csr

cat > client-ext.cnf <<CLIENTEXT
extendedKeyUsage = clientAuth
CLIENTEXT

openssl x509 -req -days 365 -sha256 -in client.csr -CA ca.pem -CAkey ca-key.pem \
  -CAcreateserial -out client-cert.pem -extfile client-ext.cnf

# Set permissions
chmod 0400 ca-key.pem server-key.pem client-key.pem
chmod 0444 ca.pem server-cert.pem client-cert.pem

# Store client certs in SSM for ECS to retrieve
aws ssm put-parameter --name "/${var.app_name}/docker/ca-cert" --value "$(cat ca.pem)" --type SecureString --overwrite --region ${var.aws_region} || true
aws ssm put-parameter --name "/${var.app_name}/docker/client-cert" --value "$(cat client-cert.pem)" --type SecureString --overwrite --region ${var.aws_region} || true
aws ssm put-parameter --name "/${var.app_name}/docker/client-key" --value "$(cat client-key.pem)" --type SecureString --overwrite --region ${var.aws_region} || true

# ==========================================================
# Update SSM Parameters for Dynamic IP Discovery
# This allows ECS backend to find this instance when ASG replaces it
# ==========================================================
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
echo "Updating SSM parameters: PRIVATE_IP=$PRIVATE_IP, INSTANCE_ID=$INSTANCE_ID" >> /var/log/sandbox-setup.log

aws ssm put-parameter --name "/${var.app_name}/sandbox/docker-host" --value "tcp://$PRIVATE_IP:2375" --type String --overwrite --region ${var.aws_region} || true
aws ssm put-parameter --name "/${var.app_name}/sandbox/instance-id" --value "$INSTANCE_ID" --type String --overwrite --region ${var.aws_region} || true
aws ssm put-parameter --name "/${var.app_name}/sandbox/private-ip" --value "$PRIVATE_IP" --type String --overwrite --region ${var.aws_region} || true

echo "SSM sandbox parameters updated successfully" >> /var/log/sandbox-setup.log

# ==========================================================
# Configure Docker with TLS
# Listens on both 2375 (no TLS) and 2376 (TLS)
# ==========================================================
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'DOCKERCONFIG'
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375", "tcp://0.0.0.0:2376"],
  "tls": true,
  "tlscacert": "/opt/docker-certs/ca.pem",
  "tlscert": "/opt/docker-certs/server-cert.pem",
  "tlskey": "/opt/docker-certs/server-key.pem",
  "tlsverify": true,
  "log-driver": "awslogs",
  "log-opts": {
    "awslogs-region": "${var.aws_region}",
    "awslogs-group": "/ec2/${var.app_name}/sandbox"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65535,
      "Soft": 65535
    }
  },
  "live-restore": true
}
DOCKERCONFIG

# Override Docker service to not use -H flag (conflicts with daemon.json)
mkdir -p /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/override.conf <<'OVERRIDE'
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd
OVERRIDE

# Reload and restart Docker
systemctl daemon-reload
systemctl restart docker

# Create sandbox network
docker network create bharatbuild-sandbox || true

# Pull common base images (speeds up sandbox creation)
# =============================================================================
# FRONTEND / JAVASCRIPT
# =============================================================================
docker pull node:18-alpine &
docker pull node:20-alpine &
docker pull node:22-alpine &

# =============================================================================
# PYTHON
# =============================================================================
docker pull python:3.11-slim &
docker pull python:3.12-slim &
docker pull python:3.11 &

# =============================================================================
# JAVA / JVM
# =============================================================================
docker pull openjdk:17-slim &
docker pull openjdk:21-slim &
docker pull maven:3.9-eclipse-temurin-17 &
docker pull maven:3.9-eclipse-temurin-21 &
docker pull gradle:8-jdk17-alpine &

# =============================================================================
# GO
# =============================================================================
docker pull golang:1.21-alpine &
docker pull golang:1.22-alpine &

# =============================================================================
# .NET
# =============================================================================
docker pull mcr.microsoft.com/dotnet/sdk:8.0 &
docker pull mcr.microsoft.com/dotnet/aspnet:8.0 &

# =============================================================================
# RUST
# =============================================================================
docker pull rust:1.75-slim &

# =============================================================================
# PHP
# =============================================================================
docker pull php:8.3-apache &
docker pull php:8.3-fpm-alpine &

# =============================================================================
# RUBY
# =============================================================================
docker pull ruby:3.3-slim &

# =============================================================================
# DATABASES
# =============================================================================
docker pull postgres:15-alpine &
docker pull postgres:16-alpine &
docker pull mysql:8.0 &
docker pull mongo:7 &
docker pull redis:7-alpine &

# =============================================================================
# WEB SERVERS / UTILITIES
# =============================================================================
docker pull nginx:alpine &
docker pull alpine:latest &
docker pull docker/compose:latest &
docker pull busybox:latest &

# =============================================================================
# AI/ML & DATA SCIENCE
# =============================================================================
docker pull tensorflow/tensorflow:latest &
docker pull pytorch/pytorch:latest &
docker pull jupyter/scipy-notebook:latest &
docker pull jupyter/tensorflow-notebook:latest &

# =============================================================================
# BLOCKCHAIN / WEB3
# =============================================================================
docker pull trufflesuite/ganache:latest &
docker pull ethereum/solc:stable &

# =============================================================================
# SECURITY / NETWORKING
# =============================================================================
docker pull owasp/zap2docker-stable:latest &
docker pull instrumentisto/nmap:latest &

# =============================================================================
# FRONTEND FRAMEWORKS (Full Node for React/Angular/Vue)
# =============================================================================
docker pull node:20 &
docker pull node:lts &

# =============================================================================
# MOBILE DEVELOPMENT
# =============================================================================
docker pull cirrusci/flutter:stable &

# =============================================================================
# C/C++ DEVELOPMENT
# =============================================================================
docker pull gcc:latest &
docker pull gcc:13 &

wait

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create sandbox workspace directory
mkdir -p /opt/sandbox/workspaces
chmod 777 /opt/sandbox/workspaces

# Install CloudWatch agent for monitoring
dnf install -y amazon-cloudwatch-agent

# ==========================================================
# Install and Configure Nginx for path-based preview routing
# Routes /sandbox/{port}/* to localhost:{port}/*
# ==========================================================
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

        # Default path to / if empty
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
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    # Preview alias (same as sandbox)
    location ~ ^/preview/([0-9]+)(/.*)?$ {
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
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
NGINXCONFIG

# Start Nginx
systemctl start nginx

# Create cleanup script (removes idle containers based on heartbeat label)
cat > /opt/sandbox/cleanup.sh <<'CLEANUP'
#!/bin/bash
# Remove containers idle for more than 30 minutes (1800 seconds)
# Uses heartbeat label (last_activity) instead of container age
# This prevents race condition where active container is deleted

IDLE_TIMEOUT=1800  # 30 minutes in seconds
NOW_TS=$(date +%s)

docker ps -q --filter "label=bharatbuild=true" --filter "status=running" | while read container; do
  # Check heartbeat label first
  LAST_ACTIVITY=$(docker inspect --format='{{index .Config.Labels "last_activity"}}' $container 2>/dev/null || echo "")

  if [ -n "$LAST_ACTIVITY" ]; then
    # Parse ISO timestamp
    ACTIVITY_TS=$(date -d "$LAST_ACTIVITY" +%s 2>/dev/null || echo "0")
    if [ "$ACTIVITY_TS" != "0" ]; then
      IDLE_TIME=$((NOW_TS - ACTIVITY_TS))
      if [ $IDLE_TIME -gt $IDLE_TIMEOUT ]; then
        PROJECT_ID=$(docker inspect --format='{{index .Config.Labels "project_id"}}' $container || echo "unknown")
        echo "$(date): Stopping idle container: $container (project: $PROJECT_ID, idle: $IDLE_TIME s)"
        docker stop $container
        docker rm $container
      fi
      continue
    fi
  fi

  # Fallback: use container start time if no heartbeat label
  STARTED=$(docker inspect --format='{{.State.StartedAt}}' $container)
  STARTED_TS=$(date -d "$STARTED" +%s 2>/dev/null || echo "0")
  if [ "$STARTED_TS" != "0" ]; then
    AGE=$((NOW_TS - STARTED_TS))
    if [ $AGE -gt $IDLE_TIMEOUT ]; then
      PROJECT_ID=$(docker inspect --format='{{index .Config.Labels "project_id"}}' $container || echo "unknown")
      echo "$(date): Stopping old container: $container (project: $PROJECT_ID, age: $AGE s)"
      docker stop $container
      docker rm $container
    fi
  fi
done

# Prune unused resources (images, networks, volumes)
docker system prune -f --volumes 2>/dev/null

# Cleanup old user networks (older than 24 hours with no containers)
docker network ls --filter "label=bharatbuild=true" -q | while read network; do
  CREATED=$(docker network inspect --format='{{index .Labels "created_at"}}' $network 2>/dev/null || echo "")
  if [ -n "$CREATED" ]; then
    CREATED_TS=$(date -d "$CREATED" +%s 2>/dev/null || echo "0")
    if [ "$CREATED_TS" != "0" ]; then
      AGE=$((NOW_TS - CREATED_TS))
      # 24 hours = 86400 seconds
      if [ $AGE -gt 86400 ]; then
        # Check if network has containers
        CONTAINERS=$(docker network inspect --format='{{len .Containers}}' $network 2>/dev/null || echo "0")
        if [ "$CONTAINERS" = "0" ]; then
          echo "$(date): Removing old network: $network (age: $AGE s)"
          docker network rm $network 2>/dev/null || true
        fi
      fi
    fi
  fi
done
CLEANUP
chmod +x /opt/sandbox/cleanup.sh

# Add cron job for cleanup every 5 minutes
echo "*/5 * * * * /opt/sandbox/cleanup.sh >> /var/log/sandbox-cleanup.log 2>&1" | crontab -

# Log completion
echo "Sandbox server setup complete at $(date)" >> /var/log/sandbox-setup.log
EOF
}

# =============================================================================
# ALB Target Group for Sandbox Previews
# =============================================================================

resource "aws_lb_target_group" "sandbox" {
  name_prefix = "sbox-"  # Use prefix for create_before_destroy compatibility
  port        = 8080  # Nginx reverse proxy port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "instance"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 5
    timeout             = 5
    interval            = 30
    path                = "/health"  # Nginx health endpoint
    protocol            = "HTTP"
    port                = "8080"
    matcher             = "200"
  }

  tags = {
    Name = "${var.app_name}-sandbox-tg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Register EC2 instance with target group (Nginx port)
resource "aws_lb_target_group_attachment" "sandbox" {
  count            = var.sandbox_use_spot ? 0 : 1
  target_group_arn = aws_lb_target_group.sandbox.arn
  target_id        = aws_instance.sandbox[0].id
  port             = 8080  # Nginx reverse proxy port
}

resource "aws_lb_target_group_attachment" "sandbox_spot" {
  count            = var.sandbox_use_spot && !var.sandbox_enable_autoscaling ? 1 : 0
  target_group_arn = aws_lb_target_group.sandbox.arn
  target_id        = aws_spot_instance_request.sandbox[0].spot_instance_id
  port             = 8080  # Nginx reverse proxy port
}

# =============================================================================
# ALB Listener Rule for Sandbox Previews
# =============================================================================

resource "aws_lb_listener_rule" "sandbox_http" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 50  # Higher priority than backend

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.sandbox.arn
  }

  condition {
    path_pattern {
      values = ["/sandbox/*", "/preview/*"]
    }
  }
}

# HTTPS rule (only when domain is configured AND Route53 zone exists)
resource "aws_lb_listener_rule" "sandbox_https" {
  count        = var.domain_name != "" && var.route53_zone_exists ? 1 : 0
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 50

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.sandbox.arn
  }

  condition {
    path_pattern {
      values = ["/sandbox/*", "/preview/*"]
    }
  }
}

# =============================================================================
# Elastic IP for SSH Access (Debug/Admin)
# =============================================================================

resource "aws_eip" "sandbox" {
  domain = "vpc"

  tags = {
    Name = "${var.app_name}-sandbox-eip"
  }
}

resource "aws_eip_association" "sandbox" {
  count         = var.sandbox_use_spot ? 0 : 1
  instance_id   = aws_instance.sandbox[0].id
  allocation_id = aws_eip.sandbox.id
}

resource "aws_eip_association" "sandbox_spot" {
  count         = var.sandbox_use_spot && !var.sandbox_enable_autoscaling ? 1 : 0
  instance_id   = aws_spot_instance_request.sandbox[0].spot_instance_id
  allocation_id = aws_eip.sandbox.id
}

# =============================================================================
# Auto-Scaling Group for Sandbox Servers (Optional - for high traffic)
# =============================================================================

# Launch Template for Auto-Scaling
resource "aws_launch_template" "sandbox" {
  count = var.sandbox_enable_autoscaling ? 1 : 0

  name_prefix   = "${var.app_name}-sandbox-"
  # Use custom pre-baked AMI if provided, otherwise Amazon Linux 2023
  image_id      = var.sandbox_custom_ami_id != "" ? var.sandbox_custom_ami_id : data.aws_ami.amazon_linux_2023.id
  instance_type = var.sandbox_instance_type

  iam_instance_profile {
    name = aws_iam_instance_profile.sandbox.name
  }

  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [aws_security_group.sandbox.id]
  }

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size = 100
      volume_type = "gp3"
      encrypted   = true
    }
  }

  user_data = base64encode(local.sandbox_user_data)

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name        = "${var.app_name}-sandbox-asg"
      Environment = "production"
      Project     = var.app_name
      ManagedBy   = "terraform"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Auto-Scaling Group
resource "aws_autoscaling_group" "sandbox" {
  count = var.sandbox_enable_autoscaling ? 1 : 0

  name_prefix         = "${var.app_name}-sandbox-asg-"
  min_size            = var.sandbox_min_size
  max_size            = var.sandbox_max_size
  desired_capacity    = var.sandbox_desired_size
  vpc_zone_identifier = aws_subnet.public[*].id

  # Use mixed instances for cost optimization
  mixed_instances_policy {
    launch_template {
      launch_template_specification {
        launch_template_id = aws_launch_template.sandbox[0].id
        version            = "$Latest"
      }

      override {
        instance_type = "t3.xlarge"
      }
      override {
        instance_type = "t3a.xlarge"
      }
      override {
        instance_type = "m5.xlarge"
      }
    }

    instances_distribution {
      on_demand_base_capacity                  = var.sandbox_use_spot ? 0 : 1
      on_demand_percentage_above_base_capacity = var.sandbox_use_spot ? 0 : 100
      spot_allocation_strategy                 = "capacity-optimized"
    }
  }

  target_group_arns = [aws_lb_target_group.sandbox.arn]

  health_check_type         = "ELB"
  health_check_grace_period = 300

  tag {
    key                 = "Name"
    value               = "${var.app_name}-sandbox-asg"
    propagate_at_launch = true
  }

  tag {
    key                 = "Environment"
    value               = "production"
    propagate_at_launch = true
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Auto-Scaling Policies
resource "aws_autoscaling_policy" "sandbox_scale_up" {
  count = var.sandbox_enable_autoscaling ? 1 : 0

  name                   = "${var.app_name}-sandbox-scale-up"
  scaling_adjustment     = 1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.sandbox[0].name
}

resource "aws_autoscaling_policy" "sandbox_scale_down" {
  count = var.sandbox_enable_autoscaling ? 1 : 0

  name                   = "${var.app_name}-sandbox-scale-down"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.sandbox[0].name
}

# CloudWatch Alarms for Auto-Scaling
resource "aws_cloudwatch_metric_alarm" "sandbox_high_cpu" {
  count = var.sandbox_enable_autoscaling ? 1 : 0

  alarm_name          = "${var.app_name}-sandbox-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 120
  statistic           = "Average"
  threshold           = 70

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.sandbox[0].name
  }

  alarm_actions = [aws_autoscaling_policy.sandbox_scale_up[0].arn]
}

resource "aws_cloudwatch_metric_alarm" "sandbox_low_cpu" {
  count = var.sandbox_enable_autoscaling ? 1 : 0

  alarm_name          = "${var.app_name}-sandbox-low-cpu"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 120
  statistic           = "Average"
  threshold           = 30

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.sandbox[0].name
  }

  alarm_actions = [aws_autoscaling_policy.sandbox_scale_down[0].arn]
}

# =============================================================================
# Outputs
# =============================================================================

output "sandbox_instance_id" {
  description = "Sandbox EC2 instance ID"
  value       = var.sandbox_enable_autoscaling ? null : (var.sandbox_use_spot ? (length(aws_spot_instance_request.sandbox) > 0 ? aws_spot_instance_request.sandbox[0].spot_instance_id : null) : (length(aws_instance.sandbox) > 0 ? aws_instance.sandbox[0].id : null))
}

output "sandbox_private_ip" {
  description = "Sandbox server private IP (for ECS to connect)"
  value       = var.sandbox_enable_autoscaling ? null : (var.sandbox_use_spot ? (length(aws_spot_instance_request.sandbox) > 0 ? aws_spot_instance_request.sandbox[0].private_ip : null) : (length(aws_instance.sandbox) > 0 ? aws_instance.sandbox[0].private_ip : null))
}

output "sandbox_docker_url" {
  description = "Docker API URL for ECS backend to use (TLS on port 2376)"
  value       = var.sandbox_enable_autoscaling ? "Use ALB DNS for auto-scaling" : (var.sandbox_use_spot ? (length(aws_spot_instance_request.sandbox) > 0 ? "tcp://${aws_spot_instance_request.sandbox[0].private_ip}:2376" : null) : (length(aws_instance.sandbox) > 0 ? "tcp://${aws_instance.sandbox[0].private_ip}:2376" : null))
}

output "sandbox_docker_url_no_tls" {
  description = "Docker API URL without TLS (development only)"
  value       = var.sandbox_enable_autoscaling ? null : (var.sandbox_use_spot ? (length(aws_spot_instance_request.sandbox) > 0 ? "tcp://${aws_spot_instance_request.sandbox[0].private_ip}:2375" : null) : (length(aws_instance.sandbox) > 0 ? "tcp://${aws_instance.sandbox[0].private_ip}:2375" : null))
}

# =============================================================================
# SSM Parameters for Dynamic IP Discovery
# =============================================================================
# These parameters are updated by the sandbox instance on startup
# Backend reads these to discover current sandbox IP

resource "aws_ssm_parameter" "sandbox_docker_host" {
  name        = "/bharatbuild/sandbox/docker-host"
  description = "Docker API endpoint for sandbox (updated by instance on startup)"
  type        = "String"
  value       = "tcp://0.0.0.0:2375"  # Placeholder - updated by instance

  lifecycle {
    ignore_changes = [value]  # Don't overwrite instance updates
  }

  tags = {
    Name        = "${var.app_name}-sandbox-docker-host"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

resource "aws_ssm_parameter" "sandbox_instance_id" {
  name        = "/bharatbuild/sandbox/instance-id"
  description = "Current sandbox instance ID (updated by instance on startup)"
  type        = "String"
  value       = "pending"  # Placeholder - updated by instance

  lifecycle {
    ignore_changes = [value]
  }

  tags = {
    Name        = "${var.app_name}-sandbox-instance-id"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

resource "aws_ssm_parameter" "sandbox_private_ip" {
  name        = "/bharatbuild/sandbox/private-ip"
  description = "Current sandbox private IP (updated by instance on startup)"
  type        = "String"
  value       = "0.0.0.0"  # Placeholder - updated by instance

  lifecycle {
    ignore_changes = [value]
  }

  tags = {
    Name        = "${var.app_name}-sandbox-private-ip"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

output "sandbox_preview_url" {
  description = "Base URL for sandbox previews"
  value       = var.domain_name != "" ? "https://${var.domain_name}/sandbox" : "http://${aws_lb.main.dns_name}/sandbox"
}

output "sandbox_public_ip" {
  description = "Sandbox server public IP (for SSH access)"
  value       = var.sandbox_enable_autoscaling ? null : aws_eip.sandbox.public_ip
}

output "sandbox_ssh_command" {
  description = "SSH command to connect to sandbox"
  value       = var.sandbox_enable_autoscaling ? "Use SSM Session Manager for auto-scaling instances" : "ssh -i your-key.pem ec2-user@${aws_eip.sandbox.public_ip}"
}

output "sandbox_autoscaling_enabled" {
  description = "Whether auto-scaling is enabled"
  value       = var.sandbox_enable_autoscaling
}

output "sandbox_tls_enabled" {
  description = "Whether TLS is enabled for Docker API"
  value       = var.sandbox_enable_tls
}
