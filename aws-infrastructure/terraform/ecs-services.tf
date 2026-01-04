# =============================================================================
# ECS Task Definitions and Services
# =============================================================================

# =============================================================================
# Application Load Balancer
# =============================================================================

resource "aws_lb" "main" {
  name               = "${var.app_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  # Increase idle timeout for SSE streaming (Claude API can take time to respond)
  idle_timeout       = 300  # 5 minutes (default is 60 seconds)

  enable_deletion_protection = false  # Set to true in production with domain

  tags = {
    Name = "${var.app_name}-alb"
  }
}

# HTTP Listener (for now, without domain/SSL)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# HTTPS Listener (only when domain is configured AND certificate is validated)
resource "aws_lb_listener" "https" {
  count             = var.domain_name != "" && var.route53_zone_exists ? 1 : 0
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.main[0].arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }

  depends_on = [aws_acm_certificate_validation.main]
}

# Backend API listener rule (HTTP)
resource "aws_lb_listener_rule" "backend_http" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/api/*", "/ws/*", "/docs", "/redoc", "/openapi.json"]
    }
  }
}

# Backend API listener rule (HTTPS - only when domain configured AND certificate validated)
resource "aws_lb_listener_rule" "backend_https" {
  count        = var.domain_name != "" && var.route53_zone_exists ? 1 : 0
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/api/*", "/ws/*", "/docs", "/redoc", "/openapi.json"]
    }
  }
}

# Target Groups
resource "aws_lb_target_group" "backend" {
  name        = "${var.app_name}-backend-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    path                = "/api/v1/health"
    protocol            = "HTTP"
    matcher             = "200"
  }

  deregistration_delay = 30
}

resource "aws_lb_target_group" "frontend" {
  name        = "${var.app_name}-frontend-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    path                = "/"
    protocol            = "HTTP"
    matcher             = "200"
  }

  deregistration_delay = 30
}

# =============================================================================
# ACM Certificate (only when domain is configured)
# =============================================================================

resource "aws_acm_certificate" "main" {
  count                     = var.domain_name != "" ? 1 : 0
  domain_name               = var.domain_name
  subject_alternative_names = ["*.${var.domain_name}"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "main" {
  count                   = var.domain_name != "" && var.route53_zone_exists ? 1 : 0
  certificate_arn         = aws_acm_certificate.main[0].arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# =============================================================================
# Route 53 (only when domain AND hosted zone exist)
# =============================================================================

data "aws_route53_zone" "main" {
  count        = var.domain_name != "" && var.route53_zone_exists ? 1 : 0
  name         = var.domain_name
  private_zone = false
}

resource "aws_route53_record" "cert_validation" {
  for_each = var.domain_name != "" && var.route53_zone_exists ? {
    for dvo in aws_acm_certificate.main[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main[0].zone_id
}

resource "aws_route53_record" "app" {
  count   = var.domain_name != "" && var.route53_zone_exists ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "app_www" {
  count   = var.domain_name != "" && var.route53_zone_exists ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# =============================================================================
# API Subdomain (api.bharatbuild.ai) - Direct to ALB, bypassing CloudFront
# This eliminates CloudFront HTTP/2 buffering issues for SSE streaming
# =============================================================================

resource "aws_route53_record" "api" {
  count   = var.domain_name != "" && var.route53_zone_exists ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = "api.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# HTTPS listener rule for api subdomain - forwards ALL traffic to backend
# No path pattern needed since entire subdomain is for API
resource "aws_lb_listener_rule" "api_subdomain_https" {
  count        = var.domain_name != "" && var.route53_zone_exists ? 1 : 0
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 40  # Higher priority than path-based rules, changed from 50 to avoid conflict

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    host_header {
      values = ["api.${var.domain_name}"]
    }
  }
}

# HTTP listener rule for api subdomain - redirect to HTTPS
resource "aws_lb_listener_rule" "api_subdomain_http" {
  count        = var.domain_name != "" && var.route53_zone_exists ? 1 : 0
  listener_arn = aws_lb_listener.http.arn
  priority     = 40  # Changed from 50 to avoid conflict

  action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  condition {
    host_header {
      values = ["api.${var.domain_name}"]
    }
  }
}

# =============================================================================
# Backend Task Definition
# =============================================================================

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.app_name}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024  # 1 vCPU
  memory                   = 3072  # 3 GB (optimized - Docker offloaded to EC2)
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "backend"
    image     = "${aws_ecr_repository.backend.repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 8000
      hostPort      = 8000
      protocol      = "tcp"
    }]

    environment = [
      { name = "ENVIRONMENT", value = "production" },
      { name = "DEBUG", value = "true" },
      { name = "WORKERS", value = "4" },
      { name = "DATABASE_URL", value = "postgresql+asyncpg://bharatbuild_admin:${var.db_password}@${aws_db_instance.main.endpoint}/bharatbuild" },
      { name = "REDIS_URL", value = "rediss://:${var.redis_auth_token}@${aws_elasticache_replication_group.main.primary_endpoint_address}:6379/0" },
      { name = "S3_BUCKET", value = aws_s3_bucket.storage.id },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "CORS_ORIGINS_STR", value = var.domain_name != "" ? "https://${var.domain_name},https://www.${var.domain_name}" : "http://${aws_lb.main.dns_name}" },
      { name = "STORAGE_MODE", value = "s3" },
      { name = "USE_MINIO", value = "false" },
      # Frontend URL for preview URL generation
      { name = "FRONTEND_URL", value = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}" },
      # Celery Configuration
      { name = "CELERY_BROKER_URL", value = "rediss://:${var.redis_auth_token}@${aws_elasticache_replication_group.main.primary_endpoint_address}:6379/0?ssl_cert_reqs=CERT_NONE" },
      { name = "CELERY_RESULT_BACKEND", value = "rediss://:${var.redis_auth_token}@${aws_elasticache_replication_group.main.primary_endpoint_address}:6379/1?ssl_cert_reqs=CERT_NONE" },
      # User Projects Path (S3 mode uses this as prefix)
      { name = "USER_PROJECTS_PATH", value = "/tmp/projects" },
      # Sandbox Server Configuration (EC2 Docker host)
      # When using ASG/Spot, use dynamic IP discovery via SSM Parameter Store
      { name = "SANDBOX_USE_DYNAMIC_IP", value = var.sandbox_enable_autoscaling ? "true" : "false" },
      { name = "SANDBOX_SSM_PARAM_DOCKER_HOST", value = "/bharatbuild/sandbox/docker-host" },
      { name = "SANDBOX_SSM_PARAM_INSTANCE_ID", value = "/bharatbuild/sandbox/instance-id" },
      # Fallback static values (used when dynamic IP is disabled)
      { name = "SANDBOX_DOCKER_HOST", value = var.sandbox_enable_autoscaling ? "" : (var.sandbox_use_spot ? (length(aws_spot_instance_request.sandbox) > 0 ? "tcp://${aws_spot_instance_request.sandbox[0].private_ip}:2375" : "") : (length(aws_instance.sandbox) > 0 ? "tcp://${aws_instance.sandbox[0].private_ip}:2375" : "")) },
      { name = "SANDBOX_PREVIEW_BASE_URL", value = var.domain_name != "" ? "https://${var.domain_name}/sandbox" : "http://${aws_lb.main.dns_name}/sandbox" },
      # Sandbox workspace path (EFS mount for persistence)
      { name = "SANDBOX_PATH", value = "/efs/sandbox/workspace" },
      # Sandbox EC2 instance ID for SSM commands (static fallback)
      { name = "SANDBOX_EC2_INSTANCE_ID", value = var.sandbox_enable_autoscaling ? "" : (var.sandbox_use_spot ? (length(aws_spot_instance_request.sandbox) > 0 ? aws_spot_instance_request.sandbox[0].spot_instance_id : "") : (length(aws_instance.sandbox) > 0 ? aws_instance.sandbox[0].id : "")) },
      # EFS enabled for hot storage (S3 still used for archival)
      { name = "EFS_ENABLED", value = "true" },
      # RESET_DB - Set to true to drop and recreate all tables (one-time use)
      { name = "RESET_DB", value = "false" },
      # OAuth Redirect URIs (must match frontend callback pages)
      { name = "GITHUB_REDIRECT_URI", value = var.domain_name != "" ? "https://${var.domain_name}/auth/callback/github" : "http://${aws_lb.main.dns_name}/auth/callback/github" },
      { name = "GOOGLE_REDIRECT_URI", value = var.domain_name != "" ? "https://${var.domain_name}/auth/callback/google" : "http://${aws_lb.main.dns_name}/auth/callback/google" },
    ]

    secrets = [
      { name = "SECRET_KEY", valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:SECRET_KEY::" },
      { name = "JWT_SECRET_KEY", valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:JWT_SECRET_KEY::" },
      { name = "ANTHROPIC_API_KEY", valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:ANTHROPIC_API_KEY::" },
      { name = "GOOGLE_CLIENT_ID", valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:GOOGLE_CLIENT_ID::" },
      { name = "GOOGLE_CLIENT_SECRET", valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:GOOGLE_CLIENT_SECRET::" },
      { name = "GITHUB_CLIENT_ID", valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:GITHUB_CLIENT_ID::" },
      { name = "GITHUB_CLIENT_SECRET", valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:GITHUB_CLIENT_SECRET::" },
      { name = "RAZORPAY_KEY_ID", valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:RAZORPAY_KEY_ID::" },
      { name = "RAZORPAY_KEY_SECRET", valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:RAZORPAY_KEY_SECRET::" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.backend.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "backend"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/health || exit 1"]
      interval    = 30
      timeout     = 10
      retries     = 3
      startPeriod = 60
    }
  }])
}

# =============================================================================
# Frontend Task Definition
# =============================================================================

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.app_name}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512   # 0.5 vCPU
  memory                   = 1024  # 1 GB
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "frontend"
    image     = "${aws_ecr_repository.frontend.repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 3000
      hostPort      = 3000
      protocol      = "tcp"
    }]

    environment = [
      { name = "NODE_ENV", value = "production" },
      # Use api subdomain to bypass CloudFront and eliminate SSE buffering issues
      { name = "NEXT_PUBLIC_API_URL", value = var.domain_name != "" ? "https://api.${var.domain_name}/api/v1" : "http://${aws_lb.main.dns_name}/api/v1" },
      { name = "NEXT_PUBLIC_WS_URL", value = var.domain_name != "" ? "wss://api.${var.domain_name}/ws" : "ws://${aws_lb.main.dns_name}/ws" },
      { name = "NEXT_PUBLIC_APP_DOMAIN", value = var.domain_name != "" ? var.domain_name : aws_lb.main.dns_name },
      { name = "NEXT_PUBLIC_APP_URL", value = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}" },
      { name = "NEXT_PUBLIC_GOOGLE_CLIENT_ID", value = "248732150405-onocm8nddrfi6khku4pc867b0g163o11.apps.googleusercontent.com" },
      { name = "NEXT_PUBLIC_GITHUB_CLIENT_ID", value = "Ov23liss1u8xfp1732Xd" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "frontend"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:3000/ || exit 1"]
      interval    = 30
      timeout     = 10
      retries     = 3
      startPeriod = 30
    }
  }])
}

# =============================================================================
# Celery Worker Task Definition
# =============================================================================

resource "aws_ecs_task_definition" "celery" {
  family                   = "${var.app_name}-celery"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024  # 1 vCPU
  memory                   = 2048  # 2 GB
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "celery"
    image     = "${aws_ecr_repository.backend.repository_url}:latest"
    essential = true

    command = ["celery", "-A", "app.core.celery_app", "worker", "--loglevel=info", "--concurrency=4"]

    environment = [
      { name = "ENVIRONMENT", value = "production" },
      { name = "SKIP_DB_INIT", value = "true" },
      { name = "DATABASE_URL", value = "postgresql+asyncpg://bharatbuild_admin:${var.db_password}@${aws_db_instance.main.endpoint}/bharatbuild" },
      { name = "REDIS_URL", value = "rediss://:${var.redis_auth_token}@${aws_elasticache_replication_group.main.primary_endpoint_address}:6379/0" },
      { name = "CELERY_BROKER_URL", value = "rediss://:${var.redis_auth_token}@${aws_elasticache_replication_group.main.primary_endpoint_address}:6379/0?ssl_cert_reqs=CERT_NONE" },
      { name = "CELERY_RESULT_BACKEND", value = "rediss://:${var.redis_auth_token}@${aws_elasticache_replication_group.main.primary_endpoint_address}:6379/1?ssl_cert_reqs=CERT_NONE" },
      { name = "USER_PROJECTS_PATH", value = "/tmp/projects" },
      { name = "S3_BUCKET", value = aws_s3_bucket.storage.id },
      { name = "AWS_REGION", value = var.aws_region },
    ]

    secrets = [
      { name = "SECRET_KEY", valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:SECRET_KEY::" },
      { name = "JWT_SECRET_KEY", valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:JWT_SECRET_KEY::" },
      { name = "ANTHROPIC_API_KEY", valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:ANTHROPIC_API_KEY::" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.celery.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "celery"
      }
    }
  }])
}

# =============================================================================
# ECS Services
# =============================================================================

resource "aws_ecs_service" "backend" {
  name            = "${var.app_name}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 2  # Start small, auto-scale as needed

  launch_type = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  lifecycle {
    ignore_changes = [desired_count]
  }

  depends_on = [aws_lb_listener.http]
}

resource "aws_ecs_service" "frontend" {
  name            = "${var.app_name}-frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1  # Start small, auto-scale as needed

  launch_type = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 3000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  lifecycle {
    ignore_changes = [desired_count]
  }

  depends_on = [aws_lb_listener.http]
}

resource "aws_ecs_service" "celery" {
  name            = "${var.app_name}-celery"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.celery.arn
  desired_count   = 1  # Start small, auto-scale as needed

  launch_type = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}

# =============================================================================
# Auto Scaling
# =============================================================================

# Backend Auto Scaling
resource "aws_appautoscaling_target" "backend" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.backend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "backend_cpu" {
  name               = "${var.app_name}-backend-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.backend.resource_id
  scalable_dimension = aws_appautoscaling_target.backend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.backend.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_policy" "backend_memory" {
  name               = "${var.app_name}-backend-memory"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.backend.resource_id
  scalable_dimension = aws_appautoscaling_target.backend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.backend.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 75
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Frontend Auto Scaling
resource "aws_appautoscaling_target" "frontend" {
  max_capacity       = 5
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.frontend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "frontend_cpu" {
  name               = "${var.app_name}-frontend-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.frontend.resource_id
  scalable_dimension = aws_appautoscaling_target.frontend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.frontend.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70
  }
}

# Celery Auto Scaling
resource "aws_appautoscaling_target" "celery" {
  max_capacity       = 5
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.celery.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "celery_cpu" {
  name               = "${var.app_name}-celery-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.celery.resource_id
  scalable_dimension = aws_appautoscaling_target.celery.scalable_dimension
  service_namespace  = aws_appautoscaling_target.celery.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70
  }
}

# =============================================================================
# Secrets Manager
# =============================================================================

resource "aws_secretsmanager_secret" "app_secrets" {
  name                    = "${var.app_name}/app-secrets"
  description             = "Application secrets for BharatBuild"
  recovery_window_in_days = 7
}

# Note: Secret values should be set manually via AWS Console or CLI
# aws secretsmanager put-secret-value --secret-id bharatbuild/app-secrets --secret-string '{"SECRET_KEY":"...","JWT_SECRET_KEY":"...",...}'

# =============================================================================
# CloudWatch Alarms
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "backend_high_cpu" {
  alarm_name          = "${var.app_name}-backend-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Backend CPU utilization high"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.backend.name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "rds_high_cpu" {
  alarm_name          = "${var.app_name}-rds-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU utilization high"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "redis_high_memory" {
  alarm_name          = "${var.app_name}-redis-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Redis memory utilization high"

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.main.id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.app_name}-alerts"
}

# =============================================================================
# Outputs
# =============================================================================

output "alb_dns_name" {
  description = "ALB DNS name - use this to access your app without a domain"
  value       = aws_lb.main.dns_name
}

output "app_url" {
  description = "Application URL"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}"
}

output "api_url" {
  description = "API URL"
  value       = var.domain_name != "" ? "https://${var.domain_name}/api/v1" : "http://${aws_lb.main.dns_name}/api/v1"
}
