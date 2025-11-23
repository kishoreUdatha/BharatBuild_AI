# S3 Cloud Storage Integration Guide

## Overview

BharatBuild AI now supports **production-grade cloud storage** using AWS S3, similar to how Bolt.new stores user projects. You can switch between local file system (for development) and S3 (for production) with a single configuration change.

---

## Storage Architecture Comparison

### **Bolt.new Storage (Reference)**
```
AWS S3
├── User Projects
│   └── s3://bolt-projects/{user_id}/{project_id}/
├── Auto-scaling
├── CDN Integration (CloudFront)
├── Automatic Backups
└── Multi-region Replication
```

### **BharatBuild AI Storage (Now Implemented)**
```
Configurable Storage
├── Local (Development)
│   └── ./user_projects/{project_id}/
├── AWS S3 (Production)
│   └── s3://bharatbuild-projects/{user_id}/{project_id}/
└── MinIO (Self-hosted S3-compatible)
    └── s3://bharatbuild-projects/{user_id}/{project_id}/
```

---

## Storage Modes

### 1. **Local Storage** (Default for Development)

**When to Use:**
- Local development
- Testing
- Single-server deployments

**Advantages:**
- ✅ No cloud costs
- ✅ Faster for development
- ✅ No internet required
- ✅ Simple setup

**Disadvantages:**
- ❌ Not scalable
- ❌ Data lost if server crashes
- ❌ Can't work with multiple servers
- ❌ No automatic backups

**Configuration:**
```bash
# .env
STORAGE_MODE=local
```

**Storage Path:**
```
./user_projects/
└── {project_id}/
    ├── backend/
    ├── frontend/
    └── documentation/
```

---

### 2. **AWS S3 Storage** (Production - Like Bolt.new)

**When to Use:**
- Production deployments
- Multi-server applications
- High-traffic applications
- When you need reliability & backups

**Advantages:**
- ✅ Unlimited scalability
- ✅ 99.99% uptime (SLA)
- ✅ Automatic backups & versioning
- ✅ Works with multiple servers
- ✅ CDN integration available
- ✅ Geographic replication
- ✅ Pay only for what you use

**Disadvantages:**
- ❌ Requires AWS account
- ❌ Costs money (but cheap)
- ❌ Slightly higher latency

**Configuration:**
```bash
# .env
STORAGE_MODE=s3

# AWS Credentials
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=ap-south-1  # Mumbai for India
S3_BUCKET_NAME=bharatbuild-projects
```

**Storage Path:**
```
s3://bharatbuild-projects/
└── projects/
    └── {user_id}/
        └── {project_id}/
            ├── backend/
            ├── frontend/
            └── documentation/
```

---

### 3. **MinIO Storage** (Self-hosted S3-compatible)

**When to Use:**
- Want S3 features without AWS
- On-premises deployment
- Full data control

**Advantages:**
- ✅ S3-compatible API
- ✅ Self-hosted (your servers)
- ✅ No AWS costs
- ✅ Full data control

**Disadvantages:**
- ❌ You manage infrastructure
- ❌ You handle backups
- ❌ You ensure uptime

**Configuration:**
```bash
# .env
STORAGE_MODE=minio

# MinIO Credentials
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_REGION=us-east-1
S3_BUCKET_NAME=bharatbuild-projects
MINIO_ENDPOINT=localhost:9000  # Your MinIO server
```

---

## Setting Up AWS S3 (Production Setup)

### Step 1: Create AWS Account
1. Go to https://aws.amazon.com
2. Sign up (12 months free tier)
3. Complete verification

### Step 2: Create S3 Bucket

```bash
# Using AWS CLI
aws s3 mb s3://bharatbuild-projects --region ap-south-1

# Or use AWS Console:
# 1. Go to S3 Console
# 2. Click "Create bucket"
# 3. Name: bharatbuild-projects
# 4. Region: Asia Pacific (Mumbai) ap-south-1
# 5. Block all public access: YES
# 6. Enable versioning: YES
# 7. Create bucket
```

### Step 3: Create IAM User with S3 Access

```bash
# Create IAM user
aws iam create-user --user-name bharatbuild-storage

# Attach S3 full access policy
aws iam attach-user-policy \
  --user-name bharatbuild-storage \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Create access key
aws iam create-access-key --user-name bharatbuild-storage
```

**Save the output:**
```json
{
  "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
  "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}
```

### Step 4: Configure BharatBuild AI

Add to `.env`:
```bash
# Enable S3 Storage
STORAGE_MODE=s3

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=ap-south-1
S3_BUCKET_NAME=bharatbuild-projects
```

### Step 5: Install Required Dependencies

```bash
cd backend
pip install boto3  # Already in requirements.txt
```

### Step 6: Restart Backend

```bash
cd backend
uvicorn app.main:app --reload
```

**You should see:**
```
INFO: StorageManager: Using AWS S3 storage (bucket: bharatbuild-projects)
INFO: S3FileManager initialized with bucket: bharatbuild-projects
```

---

## Setting Up MinIO (Self-hosted Alternative)

### Step 1: Install MinIO

**Docker (Recommended):**
```bash
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  --name minio \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  -v /data/minio:/data \
  minio/minio server /data --console-address ":9001"
```

**Or download binary:**
```bash
# Linux
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
./minio server /data

# Windows
# Download from https://min.io/download
```

### Step 2: Configure BharatBuild AI

Add to `.env`:
```bash
# Enable MinIO Storage
STORAGE_MODE=minio

# MinIO Configuration
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_REGION=us-east-1
S3_BUCKET_NAME=bharatbuild-projects
MINIO_ENDPOINT=localhost:9000
```

### Step 3: Access MinIO Console

```
URL: http://localhost:9001
Username: minioadmin
Password: minioadmin
```

---

## Cost Comparison

### **Local Storage**
```
Cost: $0
Storage: Limited to disk space
Backup: Manual
```

### **AWS S3 Storage**
```
Storage: $0.023 per GB/month (ap-south-1)
Requests:
  - PUT: $0.005 per 1,000 requests
  - GET: $0.0004 per 1,000 requests
Data Transfer:
  - Upload: Free
  - Download: $0.109 per GB (after 100GB free)

Example Monthly Cost (1000 active users):
  - 50 projects/user × 10MB/project = 500GB storage
  - Storage: 500GB × $0.023 = $11.50/month
  - Requests: ~100,000 requests = $0.50/month
  - Total: ~$12/month
```

### **MinIO Storage**
```
Cost: Server hosting costs (VPS/dedicated)
Storage: Limited to your server capacity
Backup: Your responsibility
```

**Winner for Production**: AWS S3 (cheap, reliable, scalable)

---

## API Usage Examples

The storage API is **identical** regardless of storage mode!

### Create Project
```python
from app.modules.automation.storage_manager import storage_manager

# Works with local, S3, or MinIO
result = await storage_manager.create_project(
    user_id="user-123",
    project_id="demo-001",
    name="Todo App"
)
```

### Create File
```python
# Generate code from Coder Agent
code = """
from fastapi import FastAPI
app = FastAPI()
"""

# Save to storage (local or S3)
result = await storage_manager.create_file(
    user_id="user-123",
    project_id="demo-001",
    file_path="backend/app/main.py",
    content=code
)
```

### Read File
```python
content = await storage_manager.read_file(
    user_id="user-123",
    project_id="demo-001",
    file_path="backend/app/main.py"
)
print(content)
```

### Get File Tree
```python
files = await storage_manager.get_file_tree(
    user_id="user-123",
    project_id="demo-001"
)
# Returns: [
#   {"path": "backend/app/main.py", "type": "file", "language": "python"},
#   {"path": "frontend/src/app/page.tsx", "type": "file", "language": "typescript"},
#   ...
# ]
```

### Get Presigned URL (S3 Only)
```python
# Generate direct download link (valid for 1 hour)
url = await storage_manager.get_presigned_url(
    user_id="user-123",
    project_id="demo-001",
    file_path="documentation/README.md",
    expiration=3600
)
# Frontend can download directly from this URL
# url = "https://bharatbuild-projects.s3.ap-south-1.amazonaws.com/projects/user-123/demo-001/documentation/README.md?..."
```

---

## Migration Guide

### Migrating from Local to S3

**Step 1: Export existing projects**
```python
# migration_script.py
import asyncio
from app.modules.automation.file_manager import file_manager
from app.modules.automation.s3_file_manager import s3_file_manager

async def migrate_to_s3(user_id: str, project_id: str):
    """Migrate a project from local to S3"""

    # Get all files from local storage
    files = await file_manager.get_file_tree(project_id)

    # Create project in S3
    await s3_file_manager.create_project(user_id, project_id, "Migrated Project")

    # Copy each file
    for file in files:
        if file['type'] == 'file':
            # Read from local
            content = await file_manager.read_file(project_id, file['path'])

            # Write to S3
            await s3_file_manager.create_file(
                user_id,
                project_id,
                file['path'],
                content
            )
            print(f"Migrated: {file['path']}")

    print(f"Migration complete: {project_id}")

# Run migration
asyncio.run(migrate_to_s3("user-123", "demo-001"))
```

**Step 2: Update .env**
```bash
STORAGE_MODE=s3
```

**Step 3: Restart backend**

---

## Monitoring & Troubleshooting

### Check Storage Mode
```python
from app.modules.automation.storage_manager import storage_manager

info = storage_manager.get_storage_info()
print(info)
# {
#   "storage_mode": "s3",
#   "backend": "S3FileManager",
#   "bucket": "bharatbuild-projects",
#   "region": "ap-south-1"
# }
```

### Common Errors

**Error: "NoSuchBucket"**
```
Solution: Bucket doesn't exist, create it:
aws s3 mb s3://bharatbuild-projects --region ap-south-1
```

**Error: "AccessDenied"**
```
Solution: Check IAM permissions
- Verify AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
- Ensure IAM user has S3 access
- Check bucket policy
```

**Error: "InvalidAccessKeyId"**
```
Solution: Invalid credentials
- Double-check .env file
- Regenerate access keys if needed
```

---

## Security Best Practices

### 1. **Use IAM User (not root account)**
```bash
# Create dedicated IAM user
aws iam create-user --user-name bharatbuild-storage
```

### 2. **Minimal Permissions**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::bharatbuild-projects",
        "arn:aws:s3:::bharatbuild-projects/*"
      ]
    }
  ]
}
```

### 3. **Enable Versioning**
```bash
aws s3api put-bucket-versioning \
  --bucket bharatbuild-projects \
  --versioning-configuration Status=Enabled
```

### 4. **Block Public Access**
```bash
aws s3api put-public-access-block \
  --bucket bharatbuild-projects \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

### 5. **Enable Encryption**
```bash
aws s3api put-bucket-encryption \
  --bucket bharatbuild-projects \
  --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

### 6. **Never Commit Credentials**
```bash
# .gitignore
.env
.env.local
.env.production
```

---

## Performance Optimization

### 1. **Use CloudFront CDN (for file downloads)**
```bash
# Create CloudFront distribution
aws cloudfront create-distribution \
  --origin-domain-name bharatbuild-projects.s3.ap-south-1.amazonaws.com
```

### 2. **Enable Transfer Acceleration**
```bash
aws s3api put-bucket-accelerate-configuration \
  --bucket bharatbuild-projects \
  --accelerate-configuration Status=Enabled
```

### 3. **Use Multipart Upload for Large Files**
Already implemented in S3FileManager for files > 5MB

---

## Summary

✅ **Created S3FileManager** - AWS S3 cloud storage implementation
✅ **Created StorageManager** - Unified API that works with local/S3/MinIO
✅ **Updated Configuration** - Added STORAGE_MODE setting
✅ **Backward Compatible** - Existing code continues to work
✅ **Production Ready** - Same storage architecture as Bolt.new

**To switch to S3 storage:**
1. Create AWS account & S3 bucket
2. Update `.env`: `STORAGE_MODE=s3`
3. Add AWS credentials to `.env`
4. Restart backend
5. Done! All files now stored in cloud ☁️

Your BharatBuild AI platform is now production-ready with scalable cloud storage! 🚀
