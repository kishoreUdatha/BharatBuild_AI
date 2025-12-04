# BharatBuild AI - Scaling Guide

## Overview

This document provides a comprehensive guide for scaling BharatBuild AI from development to production, supporting from 100 to 100,000+ concurrent users.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Scaling Phases](#scaling-phases)
3. [Phase 1: Development (Current)](#phase-1-development-current)
4. [Phase 2: Early Production (Fly.io/Railway)](#phase-2-early-production)
5. [Phase 3: Enterprise (Kubernetes)](#phase-3-enterprise-kubernetes)
6. [Cost Comparison](#cost-comparison)
7. [Hybrid Architecture (Recommended)](#hybrid-architecture)
8. [Implementation Guide](#implementation-guide)

---

## Architecture Overview

### Current Architecture (Single Docker)

```
┌─────────────────────────────────────────────────────────┐
│                    SINGLE SERVER                         │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Frontend   │  │   Backend   │  │  PostgreSQL │     │
│  │  (Next.js)  │  │  (FastAPI)  │  │             │     │
│  │  Port 3000  │  │  Port 8000  │  │  Port 5432  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                         │
│  ┌─────────────┐  ┌─────────────────────────────────┐  │
│  │    Redis    │  │      User Projects              │  │
│  │  Port 6379  │  │  /app/user_projects/{id}/       │  │
│  └─────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Scalable Architecture (Kubernetes + WebContainers)

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                             │
├─────────────────────────────────────────────────────────────────┤
│  Frontend Projects (JavaScript/React/Vue/Next.js)               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              WebContainers (Browser Runtime)             │   │
│  │              - No server required                        │   │
│  │              - Unlimited concurrent users                │   │
│  │              - Zero infrastructure cost                  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     KUBERNETES CLUSTER                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    INGRESS / LOAD BALANCER               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                │                                 │
│         ┌──────────────────────┼──────────────────────┐         │
│         ▼                      ▼                      ▼         │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐   │
│  │  Frontend   │       │   Backend   │       │   Backend   │   │
│  │  Service    │       │  Service 1  │       │  Service N  │   │
│  │  (3 pods)   │       │  (10 pods)  │       │  (10 pods)  │   │
│  └─────────────┘       └─────────────┘       └─────────────┘   │
│                                │                                 │
│         ┌──────────────────────┼──────────────────────┐         │
│         ▼                      ▼                      ▼         │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐   │
│  │ PostgreSQL  │       │    Redis    │       │     S3      │   │
│  │  (Primary   │       │   Cluster   │       │   Storage   │   │
│  │  + Replica) │       │  (3 nodes)  │       │             │   │
│  └─────────────┘       └─────────────┘       └─────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              USER PROJECT PODS (Auto-scaled)             │   │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │   │
│  │  │User A│ │User B│ │User C│ │User D│ │User N│          │   │
│  │  │Python│ │Flask │ │Django│ │FastAPI│ │ Go  │          │   │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Scaling Phases

| Phase | Users | Infrastructure | Monthly Cost |
|-------|-------|----------------|--------------|
| Phase 1 | 100-500 | Single Docker | $50-100 |
| Phase 2 | 1,000-50,000 | Fly.io/Railway | $500-2,000 |
| Phase 3 | 100,000+ | Kubernetes | $4,000-15,000 |

---

## Phase 1: Development (Current)

### Specifications

- **Users**: 100-500 concurrent
- **Server**: Single VPS/Cloud Instance
- **Cost**: $50-100/month

### Infrastructure

| Component | Specification | Purpose |
|-----------|---------------|---------|
| VPS | 4 vCPU, 8GB RAM, 100GB SSD | All services |
| Docker | docker-compose | Container orchestration |
| PostgreSQL | Single instance | Database |
| Redis | Single instance | Cache & queues |

### Limitations

- Single point of failure
- Limited port availability (~62k ports)
- No auto-scaling
- Memory constraints for concurrent projects

### Current docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: bharatbuild
      POSTGRES_PASSWORD: bharatbuild123
      POSTGRES_DB: bharatbuild_db
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - user_projects:/app/user_projects
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
  user_projects:
```

---

## Phase 2: Early Production

### Option A: Fly.io

**Best for**: Quick scaling, simple deployment

#### Specifications

- **Users**: 1,000-50,000 concurrent
- **Cost**: $500-2,000/month
- **Regions**: Global edge deployment

#### fly.toml Configuration

```toml
# fly.toml - Backend
app = "bharatbuild-backend"
primary_region = "sin"  # Singapore

[build]
  dockerfile = "backend/Dockerfile"

[env]
  DATABASE_URL = "postgres://..."
  REDIS_URL = "redis://..."

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

[metrics]
  port = 9091
  path = "/metrics"
```

#### Fly.io Cost Breakdown

| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| Backend VMs | 5x shared-cpu-2x (2GB) | $75 |
| Frontend VMs | 3x shared-cpu-1x (1GB) | $30 |
| PostgreSQL | 2GB RAM, 20GB disk | $50 |
| Redis (Upstash) | Pay-per-use | $20 |
| Bandwidth | 100GB | $0 (included) |
| **Total** | | **~$175/month** |

For 50k users: ~$1,500/month (scaled up)

### Option B: Railway

**Best for**: Developer-friendly, auto-scaling

#### railway.json Configuration

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "backend/Dockerfile"
  },
  "deploy": {
    "numReplicas": 3,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

#### Railway Cost Breakdown

| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| Backend | $20/service + usage | $100-500 |
| Frontend | $20/service + usage | $50-200 |
| PostgreSQL | Managed | $50-200 |
| Redis | Managed | $20-50 |
| **Total** | | **$240-950/month** |

---

## Phase 3: Enterprise (Kubernetes)

### AWS EKS Setup

#### Cluster Specifications

| Component | Specification | Purpose |
|-----------|---------------|---------|
| Control Plane | EKS Managed | Kubernetes API |
| Worker Nodes | 20x m5.xlarge | Application workloads |
| Node Groups | 3 (frontend, backend, user-projects) | Isolation |
| Availability Zones | 3 | High availability |

#### AWS EKS Cost Breakdown (100k Users)

| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| EKS Control Plane | Managed | $73 |
| Worker Nodes | 20x m5.xlarge (4 vCPU, 16GB) | $2,800 |
| Spot Instances | 50% of workers | -$1,400 (savings) |
| Application LB | ALB | $20 + $0.008/LCU-hour |
| NAT Gateway | 3 AZs | $100 |
| EBS Storage | 2TB gp3 | $160 |
| Data Transfer | 10TB outbound | $900 |
| RDS PostgreSQL | db.r5.xlarge Multi-AZ | $700 |
| ElastiCache Redis | r5.large cluster | $300 |
| S3 Storage | 1TB + requests | $50 |
| CloudWatch | Logs, metrics, alarms | $150 |
| Route 53 | DNS + health checks | $10 |
| WAF | Web firewall | $50 |
| **Total** | | **~$3,900/month** |

With Reserved Instances (1-year): **~$2,700/month**

#### Google GKE Cost Breakdown (100k Users)

| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| GKE Autopilot | Managed cluster | $73 |
| Worker Nodes | 20x e2-standard-4 | $2,000 |
| Preemptible VMs | 50% of workers | -$1,000 (savings) |
| Cloud Load Balancer | Regional | $18 + traffic |
| Cloud NAT | 3 regions | $90 |
| Persistent Disk | 2TB SSD | $340 |
| Data Transfer | 10TB | $800 |
| Cloud SQL | db-custom-4-16384 HA | $600 |
| Memorystore Redis | 5GB cluster | $250 |
| Cloud Storage | 1TB | $20 |
| Cloud Monitoring | Logs & metrics | $100 |
| Cloud DNS | Managed DNS | $5 |
| Cloud Armor | WAF | $50 |
| **Total** | | **~$3,350/month** |

With Committed Use (1-year): **~$2,400/month**

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
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-credentials
              key: url
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
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: backend
              topologyKey: "kubernetes.io/hostname"
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
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

#### Frontend Deployment

```yaml
# k8s/frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: bharatbuild
spec:
  replicas: 3
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: bharatbuild/frontend:latest
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_API_URL
          value: "https://api.bharatbuild.ai"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

#### Ingress (AWS ALB)

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
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/ssl-redirect: '443'
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

#### User Project Pod Template

```yaml
# k8s/user-project-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: user-project-${PROJECT_ID}
  namespace: bharatbuild-projects
  labels:
    app: user-project
    project-id: ${PROJECT_ID}
    user-id: ${USER_ID}
spec:
  containers:
  - name: project-runtime
    image: bharatbuild/project-runtime:latest
    ports:
    - containerPort: 3000
      name: http
    resources:
      requests:
        memory: "256Mi"
        cpu: "100m"
      limits:
        memory: "1Gi"
        cpu: "500m"
    volumeMounts:
    - name: project-files
      mountPath: /app/project
  volumes:
  - name: project-files
    persistentVolumeClaim:
      claimName: project-${PROJECT_ID}-pvc
  restartPolicy: Never
  activeDeadlineSeconds: 3600  # Auto-terminate after 1 hour
```

---

## Cost Comparison

### Monthly Cost by User Count

| Users | Docker | Fly.io | Railway | AWS EKS | GKE |
|-------|--------|--------|---------|---------|-----|
| 100 | $50 | $50 | $50 | N/A | N/A |
| 500 | $100 | $100 | $100 | N/A | N/A |
| 1,000 | N/A | $200 | $250 | $1,500 | $1,200 |
| 5,000 | N/A | $500 | $600 | $2,000 | $1,800 |
| 10,000 | N/A | $800 | $1,000 | $2,500 | $2,200 |
| 50,000 | N/A | $2,000 | $2,500 | $3,500 | $3,000 |
| 100,000 | N/A | $4,000 | N/A | $4,500 | $4,000 |
| 500,000 | N/A | N/A | N/A | $15,000 | $12,000 |

### Cost Per User

| Users | AWS EKS | GKE | Fly.io |
|-------|---------|-----|--------|
| 10,000 | $0.25 | $0.22 | $0.08 |
| 50,000 | $0.07 | $0.06 | $0.04 |
| 100,000 | $0.045 | $0.04 | $0.04 |
| 500,000 | $0.03 | $0.024 | N/A |

---

## Hybrid Architecture (Recommended)

### Best Approach for BharatBuild AI

Combine **WebContainers** for frontend projects with **Kubernetes** for backend projects.

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND PROJECTS                     │
│                      (React, Vue, Next.js)                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │               WebContainers (Browser)                  │  │
│  │                                                        │  │
│  │  ✅ Free - No server cost                             │  │
│  │  ✅ Unlimited users                                    │  │
│  │  ✅ Instant preview                                    │  │
│  │  ✅ No port management needed                          │  │
│  │                                                        │  │
│  │  ❌ JavaScript/Node.js only                           │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              +
┌─────────────────────────────────────────────────────────────┐
│                       BACKEND PROJECTS                       │
│                  (Python, Java, Go, Rust)                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                  Kubernetes Cluster                    │  │
│  │                                                        │  │
│  │  ✅ All languages supported                           │  │
│  │  ✅ Auto-scaling                                       │  │
│  │  ✅ High availability                                  │  │
│  │  ✅ Resource isolation                                 │  │
│  │                                                        │  │
│  │  ❌ Costs money                                        │  │
│  │  ❌ More complex                                       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Cost Savings with Hybrid

| Approach | 100k Users Cost | Frontend Cost | Backend Cost |
|----------|-----------------|---------------|--------------|
| Kubernetes Only | $4,500/month | $1,500 | $3,000 |
| Hybrid (WebContainers + K8s) | $2,500/month | $0 | $2,500 |
| **Savings** | **$2,000/month** | **100%** | **17%** |

---

## Implementation Guide

### Step 1: Add WebContainers for Frontend

```bash
# Install WebContainers SDK
cd frontend
npm install @webcontainer/api
```

### Step 2: Setup Fly.io (Phase 2)

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Launch app
fly launch --name bharatbuild-backend

# Deploy
fly deploy
```

### Step 3: Setup Kubernetes (Phase 3)

```bash
# Create EKS cluster
eksctl create cluster \
  --name bharatbuild \
  --region ap-south-1 \
  --nodegroup-name workers \
  --node-type m5.xlarge \
  --nodes 5 \
  --nodes-min 3 \
  --nodes-max 20 \
  --managed

# Apply manifests
kubectl apply -f k8s/

# Setup autoscaling
kubectl apply -f k8s/backend-hpa.yaml
```

---

## Monitoring & Observability

### Recommended Stack

| Tool | Purpose | Cost |
|------|---------|------|
| Prometheus | Metrics | Free (self-hosted) |
| Grafana | Dashboards | Free (self-hosted) |
| Loki | Logs | Free (self-hosted) |
| Jaeger | Tracing | Free (self-hosted) |

### Key Metrics to Monitor

1. **Application**: Request latency, error rate, throughput
2. **Infrastructure**: CPU, memory, disk, network
3. **Kubernetes**: Pod count, node health, HPA status
4. **Database**: Connections, query time, replication lag
5. **User Projects**: Active projects, resource usage, failures

---

## Security Considerations

### Kubernetes Security

1. **Network Policies**: Isolate namespaces
2. **RBAC**: Role-based access control
3. **Pod Security**: Non-root containers
4. **Secrets Management**: Use external secrets (AWS Secrets Manager)
5. **Image Scanning**: Scan for vulnerabilities

### User Project Isolation

1. **Namespace per user** or **Pod per project**
2. **Resource quotas** to prevent abuse
3. **Network isolation** between projects
4. **Auto-termination** of idle projects

---

## Disaster Recovery

### Backup Strategy

| Component | Backup Frequency | Retention | Method |
|-----------|------------------|-----------|--------|
| PostgreSQL | Hourly | 30 days | RDS automated backups |
| Redis | Daily | 7 days | RDB snapshots |
| User Projects | On save | 90 days | S3 versioning |
| Kubernetes Config | On change | Forever | GitOps |

### Recovery Time Objectives

| Scenario | RTO | RPO |
|----------|-----|-----|
| Single pod failure | < 1 min | 0 |
| Node failure | < 5 min | 0 |
| AZ failure | < 15 min | 0 |
| Region failure | < 1 hour | < 5 min |

---

## Conclusion

### Recommended Path

1. **Start**: Current Docker setup (free, up to 500 users)
2. **Scale**: Fly.io when reaching 1,000+ users (~$200/month)
3. **Enterprise**: Kubernetes at 50,000+ users (~$3,000/month)
4. **Optimize**: Add WebContainers to reduce costs by 40%

### Next Steps

1. [ ] Implement WebContainers for frontend projects
2. [ ] Create Fly.io deployment configuration
3. [ ] Prepare Kubernetes manifests
4. [ ] Setup monitoring and alerting
5. [ ] Implement auto-scaling policies
6. [ ] Configure disaster recovery

---

## Support

For questions about scaling, contact:
- Documentation: `/docs/SCALING_GUIDE.md`
- Architecture: `/docs/ARCHITECTURE.md`
- Deployment: `/docs/DEPLOYMENT.md`
