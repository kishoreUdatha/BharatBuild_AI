# Deployment Guide

## Overview

This guide covers deploying BharatBuild AI from development to production, supporting from 100 to 100,000+ concurrent users.

## Deployment Options

| Stage | Users | Infrastructure | Monthly Cost |
|-------|-------|----------------|--------------|
| Development | 1-100 | Local/Docker | $0 |
| Phase 1 | 100-500 | Single VPS | $50-100 |
| Phase 2 | 1,000-50,000 | Fly.io/Railway | $200-2,000 |
| Phase 3 | 100,000+ | Kubernetes | $3,000-15,000 |

---

## Local Development

### Prerequisites

```bash
# Required software
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ (or use Docker)
- Redis 7+ (or use Docker)
```

### Quick Start

```bash
# Clone repository
git clone https://github.com/yourorg/bharatbuild-ai.git
cd bharatbuild-ai

# Start all services with Docker Compose
docker-compose up -d

# Access:
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Manual Setup

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../.env.example .env
# Edit .env with your settings

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local

# Start development server
npm run dev
```

### Environment Variables

Create `.env` file:

```bash
# Database
DATABASE_URL=postgresql://bharatbuild:bharatbuild123@localhost:5432/bharatbuild_db

# Redis
REDIS_URL=redis://localhost:6379

# Claude API
ANTHROPIC_API_KEY=sk-ant-api03-...

# JWT Secret
JWT_SECRET=your-super-secret-key-here
JWT_ALGORITHM=HS256

# Storage
JOBS_BASE_PATH=/tmp/jobs
JOB_EXPIRY_HOURS=48

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000

# Optional: AWS S3
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=ap-south-1
S3_BUCKET=bharatbuild-projects
```

---

## Phase 1: Single VPS Deployment

### Server Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Storage | 100 GB SSD | 200 GB SSD |
| OS | Ubuntu 22.04 | Ubuntu 22.04 |

### Setup Script

```bash
#!/bin/bash
# deploy-vps.sh

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone repository
git clone https://github.com/yourorg/bharatbuild-ai.git
cd bharatbuild-ai

# Configure environment
cp .env.example .env
# Edit .env with production values

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Setup Nginx
sudo apt install nginx -y
sudo cp nginx/bharatbuild.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/bharatbuild.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Setup SSL with Certbot
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d bharatbuild.ai -d www.bharatbuild.ai
```

### docker-compose.prod.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    restart: always
    environment:
      POSTGRES_USER: bharatbuild
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: bharatbuild_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bharatbuild"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: always
    environment:
      - DATABASE_URL=postgresql://bharatbuild:${DB_PASSWORD}@postgres:5432/bharatbuild_db
      - REDIS_URL=redis://redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
      - JOBS_BASE_PATH=/app/jobs
    volumes:
      - jobs_data:/app/jobs
      - /var/run/docker.sock:/var/run/docker.sock  # For container execution
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    ports:
      - "8000:8000"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        - NEXT_PUBLIC_API_URL=https://api.bharatbuild.ai
    restart: always
    ports:
      - "3000:3000"
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - ./nginx/certbot:/var/www/certbot
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
  redis_data:
  jobs_data:
```

### Nginx Configuration

```nginx
# nginx/bharatbuild.conf

upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:3000;
}

server {
    listen 80;
    server_name bharatbuild.ai www.bharatbuild.ai;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name bharatbuild.ai www.bharatbuild.ai;

    ssl_certificate /etc/letsencrypt/live/bharatbuild.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bharatbuild.ai/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }

    # Preview proxy
    location /preview/ {
        proxy_pass http://backend/api/v1/preview/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
```

---

## Phase 2: Fly.io Deployment

### Setup

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Create app
fly apps create bharatbuild-backend
fly apps create bharatbuild-frontend
```

### fly.toml (Backend)

```toml
app = "bharatbuild-backend"
primary_region = "sin"  # Singapore

[build]
  dockerfile = "backend/Dockerfile"

[env]
  JOBS_BASE_PATH = "/app/jobs"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 2

  [http_service.concurrency]
    type = "connections"
    hard_limit = 100
    soft_limit = 80

[[vm]]
  cpu_kind = "shared"
  cpus = 2
  memory_mb = 2048

[mounts]
  source = "jobs_data"
  destination = "/app/jobs"

[metrics]
  port = 9091
  path = "/metrics"
```

### Deploy

```bash
# Set secrets
fly secrets set ANTHROPIC_API_KEY=sk-ant-... -a bharatbuild-backend
fly secrets set DATABASE_URL=postgres://... -a bharatbuild-backend
fly secrets set JWT_SECRET=... -a bharatbuild-backend

# Deploy backend
fly deploy -a bharatbuild-backend

# Deploy frontend
fly deploy -a bharatbuild-frontend
```

### Fly.io Database

```bash
# Create PostgreSQL
fly postgres create --name bharatbuild-db --region sin

# Attach to backend
fly postgres attach bharatbuild-db -a bharatbuild-backend
```

---

## Phase 3: Kubernetes Deployment

### Cluster Setup (AWS EKS)

```bash
# Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Create cluster
eksctl create cluster \
  --name bharatbuild \
  --region ap-south-1 \
  --nodegroup-name workers \
  --node-type m5.xlarge \
  --nodes 5 \
  --nodes-min 3 \
  --nodes-max 20 \
  --managed

# Configure kubectl
aws eks update-kubeconfig --name bharatbuild --region ap-south-1
```

### Kubernetes Manifests

#### Namespace

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: bharatbuild
  labels:
    app: bharatbuild
```

#### Secrets

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: bharatbuild-secrets
  namespace: bharatbuild
type: Opaque
stringData:
  ANTHROPIC_API_KEY: "sk-ant-..."
  DATABASE_URL: "postgresql://..."
  JWT_SECRET: "your-secret"
```

#### Backend Deployment

```yaml
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: bharatbuild
spec:
  replicas: 10
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: bharatbuild/backend:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: bharatbuild-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: jobs-storage
          mountPath: /app/jobs
      volumes:
      - name: jobs-storage
        emptyDir:
          sizeLimit: 10Gi
```

#### Backend Service

```yaml
# k8s/backend-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: bharatbuild
spec:
  selector:
    app: backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

#### Horizontal Pod Autoscaler

```yaml
# k8s/backend-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: bharatbuild
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 5
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: bharatbuild-ingress
  namespace: bharatbuild
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:...
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01
spec:
  rules:
  - host: bharatbuild.ai
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 3000
  - host: api.bharatbuild.ai
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
```

### Deploy to Kubernetes

```bash
# Apply all manifests
kubectl apply -f k8s/

# Check status
kubectl get pods -n bharatbuild
kubectl get services -n bharatbuild
kubectl get hpa -n bharatbuild

# View logs
kubectl logs -f deployment/backend -n bharatbuild
```

---

## Database Setup

### PostgreSQL (Production)

```bash
# AWS RDS
aws rds create-db-instance \
  --db-instance-identifier bharatbuild-db \
  --db-instance-class db.r5.large \
  --engine postgres \
  --engine-version 15 \
  --master-username bharatbuild \
  --master-user-password YOUR_PASSWORD \
  --allocated-storage 100 \
  --multi-az \
  --backup-retention-period 7
```

### Redis (Production)

```bash
# AWS ElastiCache
aws elasticache create-replication-group \
  --replication-group-id bharatbuild-redis \
  --replication-group-description "BharatBuild Redis" \
  --engine redis \
  --cache-node-type cache.r5.large \
  --num-cache-clusters 2 \
  --automatic-failover-enabled
```

---

## Monitoring

### Prometheus + Grafana

```yaml
# k8s/prometheus.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
      - job_name: 'bharatbuild-backend'
        kubernetes_sd_configs:
          - role: pod
            namespaces:
              names: [bharatbuild]
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            regex: backend
            action: keep
```

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| CPU Usage | > 80% |
| Memory Usage | > 85% |
| Request Latency (P99) | > 2s |
| Error Rate | > 1% |
| Active Containers | > 1000 |

---

## Backup & Recovery

### Database Backup

```bash
# Automated daily backups
0 2 * * * pg_dump -U bharatbuild bharatbuild_db | gzip > /backups/db-$(date +\%Y\%m\%d).sql.gz

# Upload to S3
aws s3 cp /backups/ s3://bharatbuild-backups/ --recursive
```

### Recovery

```bash
# Restore from backup
gunzip -c db-20240115.sql.gz | psql -U bharatbuild bharatbuild_db
```

---

## SSL/TLS Setup

### Let's Encrypt (Certbot)

```bash
# Install
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d bharatbuild.ai -d www.bharatbuild.ai -d api.bharatbuild.ai

# Auto-renewal
sudo certbot renew --dry-run
```

### AWS Certificate Manager

```bash
# Request certificate
aws acm request-certificate \
  --domain-name bharatbuild.ai \
  --subject-alternative-names "*.bharatbuild.ai" \
  --validation-method DNS
```

---

## Health Checks

### Backend Health Endpoint

```python
@app.get("/health")
async def health_check():
    # Check database
    try:
        await database.execute("SELECT 1")
        db_status = "healthy"
    except:
        db_status = "unhealthy"

    # Check Redis
    try:
        await redis.ping()
        redis_status = "healthy"
    except:
        redis_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded",
        "database": db_status,
        "redis": redis_status,
        "version": "1.0.0"
    }
```

---

## Deployment Checklist

### Pre-deployment

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] SSL certificates obtained
- [ ] DNS records configured
- [ ] Firewall rules set
- [ ] Monitoring configured

### Post-deployment

- [ ] Health checks passing
- [ ] Logs visible
- [ ] Metrics flowing
- [ ] Alerts configured
- [ ] Backup tested
- [ ] Rollback tested

---

## Rollback

### Docker Compose

```bash
# Rollback to previous version
docker-compose down
git checkout v1.2.3
docker-compose up -d
```

### Kubernetes

```bash
# View rollout history
kubectl rollout history deployment/backend -n bharatbuild

# Rollback to previous revision
kubectl rollout undo deployment/backend -n bharatbuild

# Rollback to specific revision
kubectl rollout undo deployment/backend --to-revision=2 -n bharatbuild
```

---

## Summary

| Deployment | Best For | Complexity |
|------------|----------|------------|
| Docker Compose | Development, small scale | Low |
| Single VPS | 100-500 users | Medium |
| Fly.io | 1,000-50,000 users | Medium |
| Kubernetes | 100,000+ users | High |

Start simple, scale as needed!
