# EFS Setup Guide for BharatBuild AI Sandbox

## Architecture: EFS + S3 Hybrid

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EFS + S3 HYBRID STORAGE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   EFS (Hot Storage)              S3 (Cold/Archive Storage)              │
│   ─────────────────              ────────────────────────               │
│   • Active sessions              • Long-term archive                    │
│   • Fast read/write (1-5ms)      • Cheap storage ($0.023/GB)            │
│   • Cleanup after 2h idle        • Keep forever                         │
│   • Auto-fixer writes here       • Restore source after months          │
│   • Safe during long builds      • Always synced after build success    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Why EFS + S3?

| Scenario | EFS Only | S3 Only | EFS + S3 (Hybrid) |
|----------|----------|---------|-------------------|
| Fast writes during build | ✅ | ❌ Slow | ✅ |
| Safe if user disconnects | ✅ | ❌ Lost | ✅ |
| Retrieve after 2 months | ❌ Cleaned up | ✅ | ✅ |
| Cost effective | ❌ $0.30/GB | ✅ $0.023/GB | ✅ Best of both |

## Flow

```
1. User opens project
   → Check EFS (fast) → Found? Use it!
   → Not on EFS? Restore from S3

2. Auto-fixer runs
   → Write to EFS immediately (safe)
   → Build runs (2-5 min for Java)
   → User can disconnect safely

3. Build succeeds
   → Sync EFS → S3 (archive)
   → User returns after 2 months? Restore from S3
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         VPC (ap-south-1)                             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐           │
│   │   ECS       │     │   EC2       │     │   EC2       │           │
│   │  Backend    │     │  Sandbox-1  │     │  Sandbox-2  │           │
│   └──────┬──────┘     └──────┬──────┘     └──────┬──────┘           │
│          │                   │                   │                   │
│          │         ┌─────────┴─────────┐         │                   │
│          │         │                   │         │                   │
│          │         ▼                   ▼         │                   │
│          │    ┌─────────────────────────────┐    │                   │
│          │    │         EFS                 │    │                   │
│          │    │  /efs/sandbox/workspace/    │◄───┘                   │
│          │    │                             │                        │
│          │    │  ├── user-1/                │                        │
│          │    │  │   ├── project-a/         │                        │
│          │    │  │   └── project-b/         │                        │
│          │    │  └── user-2/                │                        │
│          │    │      └── project-c/         │                        │
│          │    └─────────────────────────────┘                        │
│          │                   │                                       │
│          │                   ▼                                       │
│          │    ┌─────────────────────────────┐                        │
│          └───►│         S3 (Archive)        │  ← Optional backup     │
│               │  Long-term storage only     │                        │
│               └─────────────────────────────┘                        │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Step 1: Create EFS File System

### Via AWS Console

1. Go to **EFS Console** → **Create file system**
2. Settings:
   - Name: `bharatbuild-sandbox`
   - VPC: Select your VPC (same as EC2 sandbox)
   - Availability: Regional (multi-AZ for durability)

3. Performance settings:
   - Throughput mode: **Bursting** (cost-effective)
   - Performance mode: **General Purpose**

4. Network settings:
   - Create mount targets in **all subnets** where sandbox EC2 runs
   - Security group: Create new or use existing (see Step 2)

### Via AWS CLI

```bash
# Create EFS file system
aws efs create-file-system \
    --region ap-south-1 \
    --performance-mode generalPurpose \
    --throughput-mode bursting \
    --encrypted \
    --tags Key=Name,Value=bharatbuild-sandbox

# Note the FileSystemId (e.g., fs-0123456789abcdef0)
```

## Step 2: Security Group for EFS

```bash
# Create security group for EFS
aws ec2 create-security-group \
    --group-name bharatbuild-efs-sg \
    --description "Security group for BharatBuild EFS" \
    --vpc-id vpc-xxxxx

# Allow NFS traffic (port 2049) from sandbox EC2 security group
aws ec2 authorize-security-group-ingress \
    --group-id sg-efs-xxxxx \
    --protocol tcp \
    --port 2049 \
    --source-group sg-sandbox-ec2-xxxxx
```

## Step 3: Create Mount Targets

```bash
# Create mount target in each subnet
aws efs create-mount-target \
    --file-system-id fs-xxxxx \
    --subnet-id subnet-xxxxx \
    --security-groups sg-efs-xxxxx
```

## Step 4: Mount EFS on Sandbox EC2

### Install EFS Utils (Amazon Linux 2)

```bash
sudo yum install -y amazon-efs-utils
```

### Install EFS Utils (Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y git binutils
git clone https://github.com/aws/efs-utils
cd efs-utils
./build-deb.sh
sudo apt-get install -y ./build/amazon-efs-utils*deb
```

### Create Mount Point and Mount

```bash
# Create mount directory
sudo mkdir -p /efs/sandbox/workspace

# Mount EFS (replace fs-xxxxx with your FileSystemId)
sudo mount -t efs -o tls fs-xxxxx:/ /efs/sandbox/workspace

# Verify mount
df -h /efs/sandbox/workspace
```

### Make Mount Persistent (fstab)

```bash
# Add to /etc/fstab
echo "fs-xxxxx:/ /efs/sandbox/workspace efs _netdev,tls 0 0" | sudo tee -a /etc/fstab
```

## Step 5: Set Permissions

```bash
# Set ownership (same user that runs Docker/containers)
sudo chown -R ec2-user:ec2-user /efs/sandbox/workspace

# Set permissions
sudo chmod -R 755 /efs/sandbox/workspace
```

## Step 6: Update Environment Variables

Add to your EC2 sandbox environment or `.env`:

```bash
# Use EFS path instead of local /tmp
SANDBOX_PATH=/efs/sandbox/workspace

# Disable S3 sync (EFS handles persistence)
EFS_ENABLED=true
```

## Step 7: Verify Setup

```bash
# Test write
echo "test" > /efs/sandbox/workspace/test.txt

# Verify from another EC2 in same VPC
cat /efs/sandbox/workspace/test.txt

# Check EFS metrics
aws efs describe-file-systems --file-system-id fs-xxxxx
```

## Cost Estimation

| Usage | Storage | Monthly Cost |
|-------|---------|--------------|
| 10k users | ~50 GB | ~$15 |
| 50k users | ~200 GB | ~$60 |
| 100k users | ~500 GB | ~$150 |

**Note**: EFS charges for:
- Storage: $0.30/GB-month (Standard)
- Infrequent Access: $0.025/GB-month (for old projects)

## Lifecycle Policy (Cost Optimization)

Move inactive files to Infrequent Access after 30 days:

```bash
aws efs put-lifecycle-configuration \
    --file-system-id fs-xxxxx \
    --lifecycle-policies TransitionToIA=AFTER_30_DAYS
```

## Troubleshooting

### Mount fails with "Connection timed out"
- Check security group allows port 2049
- Verify mount target exists in same subnet

### Permission denied
- Check EFS access point permissions
- Verify EC2 IAM role has `elasticfilesystem:ClientMount`

### Slow performance
- Check if using Bursting mode and out of credits
- Consider switching to Provisioned throughput for heavy use

## Rollback Plan

If EFS has issues, revert to S3:

```bash
# Change environment variable
SANDBOX_PATH=/tmp/sandbox/workspace
EFS_ENABLED=false

# Unmount EFS
sudo umount /efs/sandbox/workspace
```
