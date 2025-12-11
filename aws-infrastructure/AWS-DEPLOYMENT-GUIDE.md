# BharatBuild AI - AWS Deployment Guide

## Architecture Overview

This deployment is designed for **100,000 active users** with the following architecture:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CloudFront CDN                                  │
│                          (Global Edge Locations)                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Application Load Balancer                             │
│                           (Multi-AZ, SSL/TLS)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                     │                              │
                     ▼                              ▼
┌───────────────────────────────┐    ┌───────────────────────────────┐
│      ECS Fargate Cluster       │    │      ECS Fargate Cluster       │
│  ┌─────────────────────────┐  │    │  ┌─────────────────────────┐  │
│  │    Backend (5-20 pods)   │  │    │  │   Frontend (3-10 pods)  │  │
│  │    - FastAPI             │  │    │  │   - Next.js              │  │
│  │    - Auto-scaling        │  │    │  │   - Auto-scaling         │  │
│  └─────────────────────────┘  │    │  └─────────────────────────┘  │
│  ┌─────────────────────────┐  │    │                               │
│  │   Celery (3-10 workers)  │  │    │                               │
│  │   - Background tasks     │  │    │                               │
│  └─────────────────────────┘  │    │                               │
└───────────────────────────────┘    └───────────────────────────────┘
            │                                    │
            ▼                                    │
┌───────────────────────────────┐               │
│       RDS PostgreSQL          │               │
│  ┌─────────────────────────┐  │               │
│  │   Primary (Multi-AZ)     │  │               │
│  │   db.t3.large (8GB)      │  │               │
│  └─────────────────────────┘  │               │
│  ┌─────────────────────────┐  │               │
│  │   Read Replica           │  │               │
│  │   db.t3.medium           │  │               │
│  └─────────────────────────┘  │               │
└───────────────────────────────┘               │
            │                                    │
            ▼                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                        ElastiCache Redis Cluster                           │
│                    (3 nodes, cache.t3.medium, Multi-AZ)                    │
└───────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                              S3 Storage                                     │
│                  (Projects, Documents, User Assets)                        │
└───────────────────────────────────────────────────────────────────────────┘
```

## Estimated Monthly Costs

| Service | Specification | Est. Cost |
|---------|--------------|-----------|
| **ECS Fargate (Backend)** | 5 tasks × 1 vCPU, 2GB | ~$150 |
| **ECS Fargate (Frontend)** | 3 tasks × 0.5 vCPU, 1GB | ~$50 |
| **ECS Fargate (Celery)** | 3 tasks × 1 vCPU, 2GB | ~$90 |
| **RDS PostgreSQL** | db.t3.large + replica | ~$250 |
| **ElastiCache Redis** | 3 × cache.t3.medium | ~$150 |
| **ALB** | Application Load Balancer | ~$25 |
| **CloudFront** | 1TB transfer | ~$85 |
| **S3** | 100GB storage | ~$3 |
| **NAT Gateway** | 2 × NAT Gateway | ~$70 |
| **Data Transfer** | Estimated | ~$50 |
| **Route 53** | Hosted zone + queries | ~$1 |
| **Secrets Manager** | 7 secrets | ~$3 |
| **CloudWatch** | Logs + metrics | ~$30 |
| **Total (base)** | | **~$950/month** |

**With auto-scaling under load:** ~$1,500-2,500/month

## Prerequisites

1. **AWS Account** with admin access
2. **Domain Name** registered in Route 53
3. **AWS CLI** installed and configured
4. **Terraform** v1.0+ installed
5. **Docker** installed

## Step-by-Step Deployment

### Step 1: Configure AWS CLI

```bash
# Install AWS CLI (if not installed)
# Windows: Download from https://aws.amazon.com/cli/
# Mac: brew install awscli
# Linux: pip install awscli

# Configure credentials
aws configure
# Enter:
#   AWS Access Key ID
#   AWS Secret Access Key
#   Default region: ap-south-1
#   Default output format: json
```

### Step 2: Register Domain in Route 53 (if not done)

1. Go to AWS Console → Route 53
2. Register a new domain or transfer existing
3. Create a Hosted Zone for your domain

### Step 3: Clone and Configure

```bash
# Navigate to infrastructure directory
cd aws-infrastructure

# Copy terraform variables template
cp terraform/terraform.tfvars.example terraform/terraform.tfvars

# Edit with your values
nano terraform/terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
aws_region     = "ap-south-1"
environment    = "production"
app_name       = "bharatbuild"
domain_name    = "your-actual-domain.com"  # CHANGE THIS
db_password    = "generate-strong-password-here"
redis_auth_token = "generate-strong-token-here"
```

Generate secure passwords:
```bash
# Generate database password
openssl rand -base64 32

# Generate Redis token
openssl rand -base64 24
```

### Step 4: Initialize Terraform

```bash
cd scripts
chmod +x deploy.sh
./deploy.sh init
```

This will:
- Create S3 bucket for Terraform state
- Create DynamoDB table for state locking
- Initialize Terraform

### Step 5: Plan Infrastructure

```bash
./deploy.sh plan
```

Review the plan carefully. It will create:
- VPC with public/private subnets
- NAT Gateways
- Security Groups
- RDS PostgreSQL (Multi-AZ)
- ElastiCache Redis Cluster
- ECS Cluster with Fargate
- Application Load Balancer
- CloudFront Distribution
- S3 Bucket
- ACM Certificates
- IAM Roles

### Step 6: Deploy Infrastructure

```bash
./deploy.sh apply
```

This takes ~15-30 minutes. Wait for completion.

### Step 7: Configure Secrets

Create `scripts/secrets.json`:
```json
{
    "SECRET_KEY": "your-64-char-secret-key",
    "JWT_SECRET_KEY": "your-64-char-jwt-secret",
    "ANTHROPIC_API_KEY": "sk-ant-api03-your-key-here",
    "GOOGLE_CLIENT_ID": "your-google-client-id.apps.googleusercontent.com",
    "GOOGLE_CLIENT_SECRET": "your-google-client-secret",
    "RAZORPAY_KEY_ID": "rzp_live_your_key_id",
    "RAZORPAY_KEY_SECRET": "your-razorpay-secret"
}
```

Upload secrets:
```bash
./deploy.sh update-secrets

# IMPORTANT: Delete secrets.json after upload!
rm secrets.json
```

### Step 8: Build and Push Docker Images

```bash
./deploy.sh push-images
```

This builds and pushes:
- Backend image
- Frontend image
- Celery worker image

### Step 9: Deploy Services

```bash
./deploy.sh force-deploy
```

### Step 10: Run Database Migrations

```bash
./deploy.sh migrate
```

### Step 11: Verify Deployment

```bash
# Check service status
./deploy.sh status

# View logs
./deploy.sh logs backend
./deploy.sh logs frontend
```

Visit `https://your-domain.com` to verify the application is running.

## GitHub Actions CI/CD

### Configure GitHub Secrets

Go to your GitHub repo → Settings → Secrets and add:

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID |
| `DOMAIN_NAME` | Your domain name |
| `CLOUDFRONT_DISTRIBUTION_ID` | CloudFront distribution ID |
| `ANTHROPIC_API_KEY` | For running tests |

### Deployment Flow

1. Push to `main` branch
2. GitHub Actions runs tests
3. Builds Docker images
4. Pushes to ECR
5. Updates ECS services
6. Invalidates CloudFront cache

## Monitoring & Alerts

### CloudWatch Dashboards

The deployment creates:
- ECS service metrics (CPU, Memory, Request count)
- RDS metrics (Connections, CPU, Storage)
- Redis metrics (Memory, Connections, Cache hits)
- ALB metrics (Request count, Latency, Error rate)

### Alerts

Configured alerts for:
- Backend CPU > 80%
- RDS CPU > 80%
- Redis Memory > 80%

Add email notifications:
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:ap-south-1:ACCOUNT_ID:bharatbuild-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

## Scaling

### Manual Scaling

```bash
# Scale backend to 10 tasks
aws ecs update-service \
  --cluster bharatbuild-cluster \
  --service bharatbuild-backend \
  --desired-count 10

# Scale frontend to 5 tasks
aws ecs update-service \
  --cluster bharatbuild-cluster \
  --service bharatbuild-frontend \
  --desired-count 5
```

### Auto-Scaling Policies

Already configured:
- Backend: 5-20 tasks, scale at 70% CPU
- Frontend: 3-10 tasks, scale at 70% CPU
- Celery: 3-10 tasks, scale at 70% CPU

## Backup & Recovery

### RDS Backups

- Automatic daily backups (7-day retention)
- Point-in-time recovery enabled
- Manual snapshots before major updates

### S3 Backups

- Versioning enabled
- Cross-region replication (optional)

## Cost Optimization Tips

1. **Use Fargate Spot** for non-critical workloads (Celery workers)
2. **Reserved Instances** for RDS (up to 60% savings)
3. **S3 Intelligent-Tiering** for infrequently accessed data
4. **CloudFront caching** to reduce origin requests
5. **Right-size instances** based on actual usage after 2-4 weeks

## Troubleshooting

### Services not starting

```bash
# Check ECS service events
aws ecs describe-services \
  --cluster bharatbuild-cluster \
  --services bharatbuild-backend \
  --query 'services[0].events[:5]'

# Check task logs
./deploy.sh logs backend
```

### Database connection issues

```bash
# Check security groups allow connection
# Check RDS is in the same VPC/subnets
# Verify DATABASE_URL is correct in task definition
```

### SSL Certificate issues

```bash
# Check certificate status
aws acm describe-certificate \
  --certificate-arn YOUR_CERT_ARN \
  --query 'Certificate.Status'
```

## Support

For issues:
1. Check CloudWatch Logs
2. Review ECS service events
3. Verify security group rules
4. Check secrets in Secrets Manager
5. Review ALB health checks

---

**Estimated Deployment Time:** 30-45 minutes

**Monthly Cost:** ~$950-2,500 depending on traffic
