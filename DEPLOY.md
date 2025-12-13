# BharatBuild AI - VPS Deployment Guide

Deploy BharatBuild AI to production in **under 30 minutes**.

## Quick Start

### Step 1: Get a VPS Server

**Recommended Providers:**
| Provider | Spec | Cost |
|----------|------|------|
| **Hetzner** (Best) | 8 vCPU, 16GB RAM | ~$30/month |
| DigitalOcean | 8 vCPU, 16GB RAM | ~$80/month |
| Contabo | 10 vCPU, 60GB RAM | ~$25/month |

Choose **Ubuntu 22.04 LTS** as the OS.

### Step 2: Point Domain to Server

1. Get your server's IP address
2. Go to your domain registrar (GoDaddy, Namecheap, etc.)
3. Add DNS records:
   ```
   A Record: @ → YOUR_SERVER_IP
   A Record: www → YOUR_SERVER_IP
   ```
4. Wait 5-10 minutes for DNS propagation

### Step 3: Connect to Server

```bash
ssh root@YOUR_SERVER_IP
```

### Step 4: Setup Server

```bash
# Download and run setup script
curl -sSL https://raw.githubusercontent.com/YOUR_REPO/main/scripts/setup-server.sh | bash

# OR manually:
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose git
```

### Step 5: Clone Repository

```bash
cd /opt
git clone https://github.com/YOUR_USERNAME/BharatBuild_AI.git bharatbuild
cd bharatbuild
```

### Step 6: Deploy

```bash
# Run interactive setup
./scripts/deploy.sh setup

# Then deploy with SSL
./scripts/deploy.sh deploy
```

The wizard will ask for:
- Your domain name
- Anthropic API key (get from https://console.anthropic.com)
- Google OAuth credentials (optional)
- Razorpay keys (optional)

**That's it! Your app will be live at `https://your-domain.com`**

---

## Deployment Commands

```bash
./scripts/deploy.sh setup     # Interactive configuration
./scripts/deploy.sh deploy    # Full deploy with SSL
./scripts/deploy.sh quick     # Quick deploy (HTTP only, for testing)
./scripts/deploy.sh ssl       # Setup/renew SSL certificate
./scripts/deploy.sh status    # Check service status
./scripts/deploy.sh logs      # View all logs
./scripts/deploy.sh logs backend   # View specific service logs
./scripts/deploy.sh restart   # Restart all services
./scripts/deploy.sh stop      # Stop all services
./scripts/deploy.sh backup    # Backup database
./scripts/deploy.sh update    # Pull latest code and redeploy
./scripts/deploy.sh health    # Health check
```

---

## What You Need Before Deployment

### Required
1. **Domain Name** - Point to your server IP
2. **Anthropic API Key** - For Claude AI features
   - Get from: https://console.anthropic.com
   - Starts with: `sk-ant-api03-...`

### Optional (but recommended)
3. **Google OAuth** - For Google Sign-In
   - Create at: https://console.cloud.google.com/apis/credentials
   - Set redirect URI: `https://your-domain.com/auth/callback/google`

4. **Razorpay** - For payments
   - Get from: https://dashboard.razorpay.com/app/keys

5. **SMTP** - For sending emails
   - Gmail: Use App Password (not regular password)

---

## Server Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Storage | 40 GB SSD | 80 GB SSD |
| OS | Ubuntu 22.04 | Ubuntu 22.04 |

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│                   Nginx (SSL)                     │
│                 Port 80, 443                      │
└──────────────────────────────────────────────────┘
              │                    │
              ▼                    ▼
┌─────────────────────┐  ┌─────────────────────┐
│   Frontend (Next.js) │  │   Backend (FastAPI)  │
│      Port 3000       │  │      Port 8000       │
└─────────────────────┘  └─────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Redis       │    │     MinIO       │
│    Port 5432    │    │   Port 6379     │    │   Port 9000     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## Troubleshooting

### Services not starting
```bash
# Check logs
./scripts/deploy.sh logs

# Check specific service
docker-compose -f docker-compose.prod.yml logs backend
```

### SSL certificate issues
```bash
# Renew certificate
./scripts/deploy.sh ssl

# Check certificate status
certbot certificates
```

### Database issues
```bash
# Connect to database
docker-compose -f docker-compose.prod.yml exec postgres psql -U bharatbuild bharatbuild_db

# Run migrations manually
docker-compose -f docker-compose.prod.yml exec backend python -c "
from app.core.database import engine, Base
from app.models import *
import asyncio
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(init())
"
```

### Out of memory
```bash
# Check memory usage
free -h
docker stats

# Add more swap
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
```

---

## Updating the Application

```bash
cd /opt/bharatbuild

# Pull latest changes
git pull origin main

# Rebuild and restart
./scripts/deploy.sh update
```

---

## Backup & Restore

### Create backup
```bash
./scripts/deploy.sh backup
# Backup saved to: backups/backup_YYYYMMDD_HHMMSS.sql.gz
```

### Restore backup
```bash
gunzip backups/backup_YYYYMMDD_HHMMSS.sql.gz
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U bharatbuild bharatbuild_db < backups/backup_YYYYMMDD_HHMMSS.sql
```

---

## Security Checklist

- [ ] SSL certificate installed
- [ ] Firewall enabled (UFW)
- [ ] SSH key authentication (disable password login)
- [ ] Fail2Ban configured
- [ ] Regular backups scheduled
- [ ] `.env.production` has secure passwords (auto-generated)

---

## Monitoring

### Check service status
```bash
./scripts/deploy.sh status
```

### View resource usage
```bash
docker stats
htop
```

### Set up monitoring (optional)
Consider adding:
- **Uptime Robot** - Free uptime monitoring
- **Sentry** - Error tracking
- **Prometheus + Grafana** - Metrics dashboard

---

## Cost Estimate

| Item | Monthly Cost |
|------|-------------|
| VPS (Hetzner CX41) | $30 |
| Domain | $1 |
| Anthropic API | ~$10-50 (usage-based) |
| **Total** | **~$40-80/month** |

---

## Support

- Check logs first: `./scripts/deploy.sh logs`
- GitHub Issues: https://github.com/YOUR_REPO/issues
- Documentation: https://docs.bharatbuild.ai
