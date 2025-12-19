#!/bin/bash
# ============================================
# BharatBuild AI - VPS Server Setup Script
# Run this on a fresh Ubuntu 22.04 server
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() { echo -e "${BLUE}[*]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

# ============================================
# Check if running as root
# ============================================
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (sudo ./setup-server.sh)"
    exit 1
fi

print_status "Starting BharatBuild AI Server Setup..."
echo ""

# ============================================
# Update System
# ============================================
print_status "Updating system packages..."
apt-get update && apt-get upgrade -y
print_success "System updated"

# ============================================
# Install Docker
# ============================================
print_status "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    systemctl enable docker
    systemctl start docker
    print_success "Docker installed"
else
    print_success "Docker already installed"
fi

# ============================================
# Install Docker Compose
# ============================================
print_status "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    print_success "Docker Compose installed"
else
    print_success "Docker Compose already installed"
fi

# ============================================
# Install Additional Tools
# ============================================
print_status "Installing additional tools..."
apt-get install -y \
    git \
    curl \
    wget \
    htop \
    ufw \
    certbot \
    python3-certbot-nginx \
    nginx \
    fail2ban
print_success "Additional tools installed"

# ============================================
# Configure Firewall
# ============================================
print_status "Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable
print_success "Firewall configured (SSH, HTTP, HTTPS allowed)"

# ============================================
# Configure Fail2Ban
# ============================================
print_status "Configuring Fail2Ban..."
systemctl enable fail2ban
systemctl start fail2ban
print_success "Fail2Ban configured"

# ============================================
# Create App Directory
# ============================================
print_status "Creating application directory..."
mkdir -p /opt/bharatbuild
chown -R $SUDO_USER:$SUDO_USER /opt/bharatbuild
print_success "Directory created at /opt/bharatbuild"

# ============================================
# Create swap file (for low memory servers)
# ============================================
print_status "Creating swap file..."
if [ ! -f /swapfile ]; then
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    print_success "4GB swap file created"
else
    print_success "Swap file already exists"
fi

# ============================================
# Optimize System
# ============================================
print_status "Optimizing system settings..."
cat >> /etc/sysctl.conf << EOF
# Network optimization
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15

# File descriptors
fs.file-max = 65535
EOF
sysctl -p
print_success "System optimized"

# ============================================
# Setup Complete
# ============================================
echo ""
echo "============================================"
print_success "Server setup complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Clone your repository to /opt/bharatbuild"
echo "  2. Run: cd /opt/bharatbuild && ./scripts/deploy.sh"
echo ""
echo "Server Info:"
echo "  - Docker: $(docker --version)"
echo "  - Docker Compose: $(docker-compose --version)"
echo "  - Firewall: Active (SSH, HTTP, HTTPS)"
echo ""
