# =============================================================================
# EC2 Sandbox Server - Docker Runtime for User Projects
# =============================================================================
# This EC2 instance runs Docker containers for user-generated projects
# Fargate cannot run Docker-in-Docker, so we use EC2 for sandbox execution
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
  default     = true
}

variable "sandbox_key_name" {
  description = "SSH key pair name for sandbox EC2 instance"
  default     = ""  # Set to your key pair name for SSH access
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

  # Docker API (from ECS backend only)
  ingress {
    description     = "Docker API from ECS"
    from_port       = 2375
    to_port         = 2375
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

  # Sandbox preview ports (10000-10100)
  ingress {
    description     = "Sandbox previews from ALB"
    from_port       = 10000
    to_port         = 10100
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
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
  count = var.sandbox_use_spot ? 1 : 0

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
  count       = var.sandbox_use_spot ? 1 : 0
  resource_id = aws_spot_instance_request.sandbox[0].spot_instance_id
  key         = "Name"
  value       = "${var.app_name}-sandbox-server"
}

resource "aws_ec2_tag" "sandbox_spot_environment" {
  count       = var.sandbox_use_spot ? 1 : 0
  resource_id = aws_spot_instance_request.sandbox[0].spot_instance_id
  key         = "Environment"
  value       = "production"
}

resource "aws_ec2_tag" "sandbox_spot_project" {
  count       = var.sandbox_use_spot ? 1 : 0
  resource_id = aws_spot_instance_request.sandbox[0].spot_instance_id
  key         = "Project"
  value       = var.app_name
}

resource "aws_ec2_tag" "sandbox_spot_managed_by" {
  count       = var.sandbox_use_spot ? 1 : 0
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

    # Install Docker
    dnf install -y docker
    systemctl start docker
    systemctl enable docker

    # Configure Docker to listen on TCP (for remote access from ECS)
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json <<'DOCKERCONFIG'
    {
      "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"],
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
    docker pull node:18-alpine &
    docker pull node:20-alpine &
    docker pull python:3.11-slim &
    docker pull python:3.12-slim &
    docker pull golang:1.21-alpine &
    docker pull openjdk:17-slim &
    docker pull nginx:alpine &
    docker pull postgres:15-alpine &
    docker pull redis:7-alpine &
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

    # Create cleanup script (removes idle containers)
    cat > /opt/sandbox/cleanup.sh <<'CLEANUP'
    #!/bin/bash
    # Remove containers idle for more than 30 minutes
    docker ps -q --filter "status=running" | while read container; do
      STARTED=$(docker inspect --format='{{.State.StartedAt}}' $container)
      STARTED_TS=$(date -d "$STARTED" +%s)
      NOW_TS=$(date +%s)
      AGE=$((NOW_TS - STARTED_TS))
      if [ $AGE -gt 1800 ]; then
        echo "Stopping idle container: $container (age: $AGE s)"
        docker stop $container
        docker rm $container
      fi
    done

    # Prune unused resources
    docker system prune -f --volumes
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
  count            = var.sandbox_use_spot ? 1 : 0
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
  count         = var.sandbox_use_spot ? 1 : 0
  instance_id   = aws_spot_instance_request.sandbox[0].spot_instance_id
  allocation_id = aws_eip.sandbox.id
}

# =============================================================================
# Outputs
# =============================================================================

output "sandbox_instance_id" {
  description = "Sandbox EC2 instance ID"
  value       = var.sandbox_use_spot ? (length(aws_spot_instance_request.sandbox) > 0 ? aws_spot_instance_request.sandbox[0].spot_instance_id : null) : (length(aws_instance.sandbox) > 0 ? aws_instance.sandbox[0].id : null)
}

output "sandbox_private_ip" {
  description = "Sandbox server private IP (for ECS to connect)"
  value       = var.sandbox_use_spot ? (length(aws_spot_instance_request.sandbox) > 0 ? aws_spot_instance_request.sandbox[0].private_ip : null) : (length(aws_instance.sandbox) > 0 ? aws_instance.sandbox[0].private_ip : null)
}

output "sandbox_docker_url" {
  description = "Docker API URL for ECS backend to use"
  value       = var.sandbox_use_spot ? (length(aws_spot_instance_request.sandbox) > 0 ? "tcp://${aws_spot_instance_request.sandbox[0].private_ip}:2375" : null) : (length(aws_instance.sandbox) > 0 ? "tcp://${aws_instance.sandbox[0].private_ip}:2375" : null)
}

output "sandbox_preview_url" {
  description = "Base URL for sandbox previews"
  value       = var.domain_name != "" ? "https://${var.domain_name}/sandbox" : "http://${aws_lb.main.dns_name}/sandbox"
}

output "sandbox_public_ip" {
  description = "Sandbox server public IP (for SSH access)"
  value       = aws_eip.sandbox.public_ip
}

output "sandbox_ssh_command" {
  description = "SSH command to connect to sandbox"
  value       = "ssh -i your-key.pem ec2-user@${aws_eip.sandbox.public_ip}"
}
