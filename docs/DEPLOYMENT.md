# Deployment Guide

This guide covers deploying BharatBuild AI platform to production.

## Prerequisites

- Docker & Docker Compose installed
- Domain name configured
- SSL certificates (Let's Encrypt recommended)
- Cloud provider account (AWS/GCP/Azure/Render)
- Environment variables configured

## Quick Deploy with Docker Compose

### 1. Production Setup

```bash
# Clone repository
git clone <repository-url>
cd BharatBuild_AI

# Copy and configure environment
cp .env.example .env
# Edit .env with production values

# Build and start services
docker-compose --profile production up -d

# Run migrations
docker-compose exec backend alembic upgrade head

# Create admin user (optional)
docker-compose exec backend python scripts/create_admin.py
```

### 2. Environment Configuration

Critical production environment variables:

```bash
# Security
SECRET_KEY=<strong-random-key>
JWT_SECRET_KEY=<strong-random-key>
DEBUG=False

# Database
DATABASE_URL=postgresql://user:password@postgres:5432/bharatbuild_db

# Claude AI
ANTHROPIC_API_KEY=<your-api-key>

# OAuth
GOOGLE_CLIENT_ID=<your-client-id>
GOOGLE_CLIENT_SECRET=<your-client-secret>

# Razorpay
RAZORPAY_KEY_ID=<your-key-id>
RAZORPAY_KEY_SECRET=<your-key-secret>

# CORS
CORS_ORIGINS=https://yourdomain.com

# SSL
USE_HTTPS=True
```

## AWS ECS Deployment

### 1. Build and Push Images

```bash
# Configure AWS CLI
aws configure

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build -t bharatbuild-backend ./backend
docker tag bharatbuild-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/bharatbuild-backend:latest

# Push
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/bharatbuild-backend:latest
```

### 2. Create ECS Task Definition

Create `task-definition.json`:

```json
{
  "family": "bharatbuild",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/bharatbuild-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"}
      ],
      "secrets": [
        {"name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:..."}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/bharatbuild",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "backend"
        }
      }
    }
  ]
}
```

### 3. Create ECS Service

```bash
aws ecs create-service \
  --cluster bharatbuild-cluster \
  --service-name bharatbuild-backend \
  --task-definition bharatbuild \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

## Render Deployment

### 1. Create PostgreSQL Database

- Create PostgreSQL database on Render
- Note the Internal Database URL

### 2. Create Redis Instance

- Create Redis instance on Render
- Note the Internal Redis URL

### 3. Deploy Backend

Create `render.yaml`:

```yaml
services:
  - type: web
    name: bharatbuild-backend
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: bharatbuild-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          name: bharatbuild-redis
          type: redis
          property: connectionString
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: SECRET_KEY
        generateValue: true
      - key: JWT_SECRET_KEY
        generateValue: true

databases:
  - name: bharatbuild-db
    databaseName: bharatbuild
    user: bharatbuild

  - name: bharatbuild-redis
    type: redis
```

### 4. Deploy Frontend

```yaml
services:
  - type: web
    name: bharatbuild-frontend
    env: node
    buildCommand: "npm install && npm run build"
    startCommand: "npm start"
    envVars:
      - key: NEXT_PUBLIC_API_URL
        value: https://bharatbuild-backend.onrender.com/api/v1
```

## SSL Configuration

### Let's Encrypt with Certbot

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
certbot renew --dry-run
```

### Update Nginx Config

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # ... rest of configuration
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

## Monitoring & Logging

### 1. Application Logs

```bash
# Docker logs
docker-compose logs -f backend

# ECS logs
aws logs tail /ecs/bharatbuild --follow
```

### 2. Health Checks

Set up monitoring:
- `/health` endpoint for basic health
- Database connectivity
- Redis connectivity
- External API status

### 3. Metrics

Recommended tools:
- Prometheus + Grafana
- AWS CloudWatch
- Datadog
- New Relic

## Scaling

### Horizontal Scaling

```bash
# Docker Compose
docker-compose up -d --scale backend=3

# ECS
aws ecs update-service \
  --cluster bharatbuild-cluster \
  --service bharatbuild-backend \
  --desired-count 5
```

### Database Scaling

- Enable read replicas
- Connection pooling (PgBouncer)
- Caching strategy with Redis

## Backup Strategy

### Database Backups

```bash
# Automated backups (daily)
0 2 * * * pg_dump -h localhost -U bharatbuild bharatbuild_db | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz

# Restore
gunzip < backup.sql.gz | psql -h localhost -U bharatbuild bharatbuild_db
```

### File Storage Backups

- Configure S3 versioning
- Cross-region replication
- Regular backup verification

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check DATABASE_URL
   - Verify network connectivity
   - Check credentials

2. **High Memory Usage**
   - Adjust worker processes
   - Enable connection pooling
   - Review queries for optimization

3. **Slow Response Times**
   - Enable Redis caching
   - Optimize database queries
   - Use CDN for static assets

## Security Checklist

- [ ] HTTPS enabled
- [ ] Strong secrets configured
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Database encrypted at rest
- [ ] Regular security updates
- [ ] Secrets in environment variables
- [ ] Firewall rules configured
- [ ] Backups automated
- [ ] Monitoring enabled

## Support

For deployment issues:
- Check logs first
- Review configuration
- Open GitHub issue
- Contact support team
