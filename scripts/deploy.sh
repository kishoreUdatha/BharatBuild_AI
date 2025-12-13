#!/bin/bash

# ============================================
# BharatBuild AI - Production Deployment Script
# One-Click VPS Deployment
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print colored message
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${CYAN}============================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}============================================${NC}"
    echo ""
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Generate secure password
generate_password() {
    openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        print_status "Run: curl -fsSL https://get.docker.com | sh"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    print_success "Prerequisites check passed!"
}

# Interactive setup wizard
setup_wizard() {
    print_header "BharatBuild AI Setup Wizard"

    if [ -f ".env.production" ]; then
        print_warning ".env.production already exists"
        read -p "Overwrite existing configuration? (y/N): " overwrite
        if [ "$overwrite" != "y" ] && [ "$overwrite" != "Y" ]; then
            print_status "Keeping existing configuration"
            return 0
        fi
    fi

    echo "Please enter your configuration:"
    echo ""

    # Domain
    read -p "Enter your domain (e.g., bharatbuild.ai): " DOMAIN
    if [ -z "$DOMAIN" ]; then
        print_error "Domain is required"
        exit 1
    fi

    # Anthropic API Key
    echo ""
    read -p "Enter Anthropic API Key (sk-ant-...): " ANTHROPIC_KEY
    if [ -z "$ANTHROPIC_KEY" ]; then
        print_error "Anthropic API Key is required for AI features"
        exit 1
    fi

    # Storage Selection
    echo ""
    print_header "Storage Configuration"
    echo "Choose your storage option:"
    echo "  1) AWS S3 (Recommended for production)"
    echo "  2) MinIO (Self-hosted, included in Docker)"
    echo ""
    read -p "Enter choice (1 or 2): " STORAGE_CHOICE

    if [ "$STORAGE_CHOICE" == "1" ]; then
        USE_S3=true
        USE_MINIO=false
        echo ""
        print_status "AWS S3 Configuration"
        read -p "AWS Access Key ID: " AWS_ACCESS_KEY
        if [ -z "$AWS_ACCESS_KEY" ]; then
            print_error "AWS Access Key ID is required for S3"
            exit 1
        fi
        read -p "AWS Secret Access Key: " AWS_SECRET_KEY
        if [ -z "$AWS_SECRET_KEY" ]; then
            print_error "AWS Secret Access Key is required for S3"
            exit 1
        fi
        read -p "AWS Region (default: ap-south-1): " AWS_REGION
        AWS_REGION=${AWS_REGION:-ap-south-1}
        read -p "S3 Bucket Name (default: bharatbuild-projects): " S3_BUCKET
        S3_BUCKET=${S3_BUCKET:-bharatbuild-projects}
    else
        USE_S3=false
        USE_MINIO=true
        MINIO_PASSWORD=$(generate_password)
    fi

    # Database Selection
    echo ""
    print_header "Database Configuration"
    echo "Choose your database option:"
    echo "  1) AWS RDS PostgreSQL (Recommended for production)"
    echo "  2) Docker PostgreSQL (Self-hosted, included in Docker)"
    echo ""
    read -p "Enter choice (1 or 2): " DB_CHOICE

    if [ "$DB_CHOICE" == "1" ]; then
        USE_RDS=true
        echo ""
        print_status "AWS RDS Configuration"
        read -p "RDS Host (e.g., mydb.xxxxx.ap-south-1.rds.amazonaws.com): " RDS_HOST
        if [ -z "$RDS_HOST" ]; then
            print_error "RDS Host is required"
            exit 1
        fi
        read -p "RDS Port (default: 5432): " RDS_PORT
        RDS_PORT=${RDS_PORT:-5432}
        read -p "Database Name (default: bharatbuild_db): " RDS_DB_NAME
        RDS_DB_NAME=${RDS_DB_NAME:-bharatbuild_db}
        read -p "Database User: " RDS_USER
        read -p "Database Password: " RDS_PASSWORD
        DATABASE_URL="postgresql://${RDS_USER}:${RDS_PASSWORD}@${RDS_HOST}:${RDS_PORT}/${RDS_DB_NAME}"
    else
        USE_RDS=false
        DB_PASSWORD=$(generate_password)
        DATABASE_URL="postgresql://bharatbuild:${DB_PASSWORD}@postgres:5432/bharatbuild_db"
    fi

    # Redis Selection
    echo ""
    print_header "Redis Configuration"
    echo "Choose your Redis option:"
    echo "  1) AWS ElastiCache Redis"
    echo "  2) Docker Redis (Self-hosted, included in Docker)"
    echo ""
    read -p "Enter choice (1 or 2): " REDIS_CHOICE

    if [ "$REDIS_CHOICE" == "1" ]; then
        USE_ELASTICACHE=true
        echo ""
        print_status "AWS ElastiCache Configuration"
        read -p "ElastiCache Endpoint (e.g., myredis.xxxxx.cache.amazonaws.com): " ELASTICACHE_HOST
        read -p "ElastiCache Port (default: 6379): " ELASTICACHE_PORT
        ELASTICACHE_PORT=${ELASTICACHE_PORT:-6379}
        read -p "Redis Auth Token (if enabled, press Enter to skip): " REDIS_AUTH_TOKEN
        if [ -n "$REDIS_AUTH_TOKEN" ]; then
            REDIS_URL="redis://:${REDIS_AUTH_TOKEN}@${ELASTICACHE_HOST}:${ELASTICACHE_PORT}/0"
            CELERY_BROKER_URL="redis://:${REDIS_AUTH_TOKEN}@${ELASTICACHE_HOST}:${ELASTICACHE_PORT}/2"
            CELERY_RESULT_BACKEND="redis://:${REDIS_AUTH_TOKEN}@${ELASTICACHE_HOST}:${ELASTICACHE_PORT}/3"
        else
            REDIS_URL="redis://${ELASTICACHE_HOST}:${ELASTICACHE_PORT}/0"
            CELERY_BROKER_URL="redis://${ELASTICACHE_HOST}:${ELASTICACHE_PORT}/2"
            CELERY_RESULT_BACKEND="redis://${ELASTICACHE_HOST}:${ELASTICACHE_PORT}/3"
        fi
        REDIS_PASSWORD=${REDIS_AUTH_TOKEN:-""}
    else
        USE_ELASTICACHE=false
        REDIS_PASSWORD=$(generate_password)
        REDIS_URL="redis://:${REDIS_PASSWORD}@redis:6379/0"
        CELERY_BROKER_URL="redis://:${REDIS_PASSWORD}@redis:6379/2"
        CELERY_RESULT_BACKEND="redis://:${REDIS_PASSWORD}@redis:6379/3"
    fi

    # Google OAuth (optional)
    echo ""
    print_status "Google OAuth (optional - for Google Sign-In)"
    read -p "Google Client ID (press Enter to skip): " GOOGLE_CLIENT_ID
    read -p "Google Client Secret (press Enter to skip): " GOOGLE_CLIENT_SECRET

    # Razorpay (optional)
    echo ""
    print_status "Razorpay Payment (optional)"
    read -p "Razorpay Key ID (press Enter to skip): " RAZORPAY_KEY_ID
    read -p "Razorpay Key Secret (press Enter to skip): " RAZORPAY_KEY_SECRET

    # SMTP (optional)
    echo ""
    print_status "Email Configuration (optional)"
    read -p "SMTP Host (default: smtp.gmail.com): " SMTP_HOST
    SMTP_HOST=${SMTP_HOST:-smtp.gmail.com}
    read -p "SMTP User (email address): " SMTP_USER
    read -p "SMTP Password (app password): " SMTP_PASSWORD

    # Generate secure keys
    print_status "Generating secure keys..."
    SECRET_KEY=$(generate_password)$(generate_password)
    JWT_SECRET=$(generate_password)$(generate_password)

    # Create .env.production
    cat > ".env.production" << EOF
# ============================================
# BharatBuild AI - Production Environment
# Generated on $(date)
# DO NOT COMMIT THIS FILE TO GIT!
# ============================================

# Application
APP_NAME=BharatBuild AI
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=${SECRET_KEY}

# Domain
DOMAIN=${DOMAIN}
API_URL=https://${DOMAIN}
WS_URL=wss://${DOMAIN}

# ==================== DATABASE ====================
# Using: $([ "$USE_RDS" == "true" ] && echo "AWS RDS" || echo "Docker PostgreSQL")
USE_RDS=${USE_RDS}
DB_USER=${RDS_USER:-bharatbuild}
DB_PASSWORD=${RDS_PASSWORD:-$DB_PASSWORD}
DB_NAME=${RDS_DB_NAME:-bharatbuild_db}
DATABASE_URL=${DATABASE_URL}

# ==================== REDIS ====================
# Using: $([ "$USE_ELASTICACHE" == "true" ] && echo "AWS ElastiCache" || echo "Docker Redis")
USE_ELASTICACHE=${USE_ELASTICACHE}
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_URL=${REDIS_URL}

# Celery
CELERY_BROKER_URL=${CELERY_BROKER_URL}
CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND}

# ==================== STORAGE ====================
# Using: $([ "$USE_S3" == "true" ] && echo "AWS S3" || echo "MinIO (self-hosted)")
USE_S3=${USE_S3}
USE_MINIO=${USE_MINIO}
EOF

    if [ "$USE_S3" == "true" ]; then
        cat >> ".env.production" << EOF
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_KEY}
AWS_REGION=${AWS_REGION}
S3_BUCKET_NAME=${S3_BUCKET}
EOF
    else
        cat >> ".env.production" << EOF
MINIO_USER=bharatbuild
MINIO_PASSWORD=${MINIO_PASSWORD}
MINIO_ENDPOINT=minio:9000
S3_BUCKET_NAME=bharatbuild-projects
AWS_ACCESS_KEY_ID=bharatbuild
AWS_SECRET_ACCESS_KEY=${MINIO_PASSWORD}
EOF
    fi

    cat >> ".env.production" << EOF

# ==================== AI ====================
ANTHROPIC_API_KEY=${ANTHROPIC_KEY}
CLAUDE_HAIKU_MODEL=claude-3-5-haiku-20241022
CLAUDE_SONNET_MODEL=claude-sonnet-4-20250514
CLAUDE_MAX_TOKENS=4096

# ==================== AUTH ====================
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth
GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID:-}
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET:-}
GOOGLE_REDIRECT_URI=https://${DOMAIN}/auth/callback/google

# ==================== PAYMENT ====================
RAZORPAY_KEY_ID=${RAZORPAY_KEY_ID:-}
RAZORPAY_KEY_SECRET=${RAZORPAY_KEY_SECRET:-}

# ==================== EMAIL ====================
SMTP_HOST=${SMTP_HOST}
SMTP_PORT=587
SMTP_USER=${SMTP_USER:-}
SMTP_PASSWORD=${SMTP_PASSWORD:-}
EMAIL_FROM=noreply@${DOMAIN}

# ==================== OTHER ====================
CORS_ORIGINS=https://${DOMAIN}
NEXT_PUBLIC_API_URL=https://${DOMAIN}/api/v1
NEXT_PUBLIC_WS_URL=wss://${DOMAIN}/ws
RATE_LIMIT_PER_MINUTE=30
RATE_LIMIT_PER_HOUR=500
LOG_LEVEL=WARNING
EOF

    chmod 600 ".env.production"
    print_success "Configuration saved to .env.production"

    # Update nginx config with domain
    update_nginx_config

    # Show summary
    echo ""
    print_header "Configuration Summary"
    echo "  Domain:   ${DOMAIN}"
    echo "  Database: $([ "$USE_RDS" == "true" ] && echo "AWS RDS" || echo "Docker PostgreSQL")"
    echo "  Redis:    $([ "$USE_ELASTICACHE" == "true" ] && echo "AWS ElastiCache" || echo "Docker Redis")"
    echo "  Storage:  $([ "$USE_S3" == "true" ] && echo "AWS S3 (${S3_BUCKET})" || echo "MinIO (self-hosted)")"
    echo ""
    print_success "Setup complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Point your domain DNS to this server's IP"
    echo "  2. Run: ./scripts/deploy.sh ssl"
    echo "  3. Run: ./scripts/deploy.sh deploy"
    echo ""
}

# Check environment file
check_env() {
    print_status "Checking environment configuration..."

    if [ ! -f ".env.production" ]; then
        print_error ".env.production file not found!"
        print_status "Please copy .env.production.example to .env.production and fill in your values:"
        echo "  cp .env.production.example .env.production"
        echo "  nano .env.production"
        exit 1
    fi

    # Check required variables
    source .env.production

    REQUIRED_VARS=(
        "ANTHROPIC_API_KEY"
        "DB_PASSWORD"
        "REDIS_PASSWORD"
        "MINIO_PASSWORD"
        "JWT_SECRET_KEY"
        "SECRET_KEY"
        "DOMAIN"
    )

    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ] || [[ "${!var}" == *"CHANGE_ME"* ]]; then
            print_error "Required variable $var is not set or contains placeholder value"
            exit 1
        fi
    done

    print_success "Environment configuration validated!"
}

# Setup SSL certificates with Let's Encrypt
setup_ssl() {
    print_status "Setting up SSL certificates..."

    source .env.production

    # Create directories
    mkdir -p docker/nginx/ssl
    mkdir -p docker/nginx/certbot/www

    # Check if certificates exist
    if [ -d "docker/nginx/ssl/live/${DOMAIN}" ]; then
        print_warning "SSL certificates already exist for ${DOMAIN}"
        read -p "Do you want to renew? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 0
        fi
    fi

    print_status "Obtaining SSL certificate for ${DOMAIN}..."

    # Run certbot to obtain certificate
    docker run -it --rm \
        -v "$(pwd)/docker/nginx/ssl:/etc/letsencrypt" \
        -v "$(pwd)/docker/nginx/certbot/www:/var/www/certbot" \
        certbot/certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email admin@${DOMAIN} \
        --agree-tos \
        --no-eff-email \
        -d ${DOMAIN} \
        -d www.${DOMAIN}

    print_success "SSL certificate obtained!"
}

# Update nginx config with domain
update_nginx_config() {
    print_status "Updating nginx configuration..."

    source .env.production

    # Replace placeholder domain in nginx config
    sed -i "s/your-domain.com/${DOMAIN}/g" docker/nginx/conf.d/production.conf

    print_success "Nginx configuration updated!"
}

# Build and start services
deploy() {
    print_status "Starting deployment..."

    # Pull latest code (if using git)
    if [ -d ".git" ]; then
        print_status "Pulling latest code..."
        git pull origin main || true
    fi

    # Build images
    print_status "Building Docker images..."
    docker-compose -f docker-compose.prod.yml build --no-cache

    # Stop existing services
    print_status "Stopping existing services..."
    docker-compose -f docker-compose.prod.yml down || true

    # Start services
    print_status "Starting services..."
    docker-compose -f docker-compose.prod.yml up -d

    # Wait for services to be healthy
    print_status "Waiting for services to be ready..."
    sleep 30

    # Check service health
    print_status "Checking service health..."
    docker-compose -f docker-compose.prod.yml ps

    print_success "Deployment complete!"
}

# Initialize MinIO bucket
init_minio() {
    print_status "Initializing MinIO bucket..."

    source .env.production

    # Wait for MinIO to be ready
    sleep 10

    # Create bucket using MinIO client
    docker run --rm --network bharatbuild_prod \
        minio/mc:latest \
        sh -c "mc alias set myminio http://minio:9000 ${MINIO_USER} ${MINIO_PASSWORD} && \
               mc mb --ignore-existing myminio/${S3_BUCKET_NAME:-bharatbuild-projects}"

    print_success "MinIO bucket created!"
}

# Run database migrations
run_migrations() {
    print_status "Running database migrations..."

    docker-compose -f docker-compose.prod.yml exec -T backend \
        python -c "from app.core.database import Base, engine; Base.metadata.create_all(bind=engine)"

    print_success "Database migrations complete!"
}

# Get the correct docker-compose file based on configuration
get_compose_file() {
    if [ -f ".env.production" ]; then
        source .env.production
        # Use AWS compose file if using external AWS services
        if [ "$USE_S3" == "true" ] && [ "$USE_RDS" == "true" ]; then
            echo "docker-compose.aws.yml"
        else
            echo "docker-compose.prod.yml"
        fi
    else
        echo "docker-compose.prod.yml"
    fi
}

# Show logs
show_logs() {
    COMPOSE_FILE=$(get_compose_file)
    docker-compose -f $COMPOSE_FILE logs -f
}

# Health check
health_check() {
    print_status "Running health check..."

    source .env.production
    COMPOSE_FILE=$(get_compose_file)

    # Check backend
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q "200"; then
        print_success "Backend: Healthy"
    else
        print_error "Backend: Unhealthy"
    fi

    # Check frontend
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200"; then
        print_success "Frontend: Healthy"
    else
        print_error "Frontend: Unhealthy"
    fi

    # Check nginx
    if curl -s -o /dev/null -w "%{http_code}" https://${DOMAIN}/health 2>/dev/null | grep -q "200"; then
        print_success "Nginx (HTTPS): Healthy"
    else
        print_warning "Nginx (HTTPS): Check SSL configuration"
    fi

    # Check AWS services if configured
    if [ "$USE_S3" == "true" ]; then
        print_status "Storage: AWS S3 (${S3_BUCKET_NAME})"
    else
        print_status "Storage: MinIO (self-hosted)"
    fi

    if [ "$USE_RDS" == "true" ]; then
        print_status "Database: AWS RDS"
    else
        print_status "Database: Docker PostgreSQL"
    fi
}

# Backup database
backup_db() {
    print_header "Database Backup"

    source .env.production
    COMPOSE_FILE=$(get_compose_file)

    mkdir -p backups
    BACKUP_FILE="backups/backup_$(date +%Y%m%d_%H%M%S).sql"

    print_status "Creating backup..."

    if [ "$USE_RDS" == "true" ]; then
        # Backup from RDS
        print_status "Backing up from AWS RDS..."
        PGPASSWORD=$DB_PASSWORD pg_dump -h $(echo $DATABASE_URL | sed -E 's/.*@([^:]+).*/\1/') \
            -U $DB_USER -d $DB_NAME > "$BACKUP_FILE"
    else
        # Backup from Docker PostgreSQL
        docker-compose -f $COMPOSE_FILE exec -T postgres pg_dump -U $DB_USER $DB_NAME > "$BACKUP_FILE"
    fi

    gzip "$BACKUP_FILE"
    print_success "Backup created: ${BACKUP_FILE}.gz"
}

# Update application
update_app() {
    print_header "Updating Application"

    print_status "Pulling latest code..."
    git pull origin main || git pull origin master

    print_status "Rebuilding containers..."
    source .env.production
    export $(grep -v '^#' .env.production | xargs)
    COMPOSE_FILE=$(get_compose_file)

    docker-compose -f $COMPOSE_FILE build
    docker-compose -f $COMPOSE_FILE up -d

    print_success "Update complete!"
    health_check
}

# Quick deploy (no SSL - for testing)
quick_deploy() {
    print_header "Quick Deploy (HTTP only - for testing)"

    check_prerequisites

    if [ ! -f ".env.production" ]; then
        setup_wizard
    fi

    source .env.production
    export $(grep -v '^#' .env.production | xargs)
    COMPOSE_FILE=$(get_compose_file)

    print_status "Using compose file: $COMPOSE_FILE"
    print_status "Building Docker images..."
    docker-compose -f $COMPOSE_FILE build

    print_status "Starting services..."
    docker-compose -f $COMPOSE_FILE up -d

    print_status "Waiting for services..."
    sleep 20

    # Only init MinIO if not using S3
    if [ "$USE_MINIO" == "true" ]; then
        init_minio
    else
        print_status "Using AWS S3 for storage - skipping MinIO init"
    fi

    run_migrations

    print_success "Quick deploy complete!"
    echo ""
    echo "Application running at:"
    echo "  Backend: http://$(hostname -I | awk '{print $1}'):8000"
    echo "  Frontend: http://$(hostname -I | awk '{print $1}'):3000"
    echo ""
    echo "Configuration:"
    echo "  Storage:  $([ "$USE_S3" == "true" ] && echo "AWS S3" || echo "MinIO")"
    echo "  Database: $([ "$USE_RDS" == "true" ] && echo "AWS RDS" || echo "Docker PostgreSQL")"
    echo "  Redis:    $([ "$USE_ELASTICACHE" == "true" ] && echo "AWS ElastiCache" || echo "Docker Redis")"
    echo ""
    echo "For production with SSL, run:"
    echo "  ./scripts/deploy.sh ssl"
    echo "  ./scripts/deploy.sh restart"
}

# Full deploy with SSL
full_deploy() {
    print_header "Full Production Deploy"

    check_prerequisites

    if [ ! -f ".env.production" ]; then
        setup_wizard
    fi

    source .env.production
    COMPOSE_FILE=$(get_compose_file)

    check_env
    setup_ssl
    deploy

    # Only init MinIO if not using S3
    if [ "$USE_MINIO" == "true" ]; then
        init_minio
    else
        print_status "Using AWS S3 for storage - skipping MinIO init"
    fi

    run_migrations
    health_check

    print_success "Deployment complete!"
    echo ""
    echo "Your application is now live at:"
    echo "  https://${DOMAIN}"
    echo ""
    echo "Configuration:"
    echo "  Storage:  $([ "$USE_S3" == "true" ] && echo "AWS S3" || echo "MinIO")"
    echo "  Database: $([ "$USE_RDS" == "true" ] && echo "AWS RDS" || echo "Docker PostgreSQL")"
    echo "  Redis:    $([ "$USE_ELASTICACHE" == "true" ] && echo "AWS ElastiCache" || echo "Docker Redis")"
    echo ""
}

# Main menu
main() {
    print_header "BharatBuild AI - Deployment"

    if [ -z "$1" ]; then
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  setup       - Interactive setup wizard"
        echo "  quick       - Quick deploy (HTTP only, for testing)"
        echo "  deploy      - Full deploy with SSL"
        echo "  ssl         - Setup/renew SSL certificates"
        echo "  migrate     - Run database migrations"
        echo "  logs        - Show service logs"
        echo "  health      - Check service health"
        echo "  restart     - Restart all services"
        echo "  stop        - Stop all services"
        echo "  status      - Show service status"
        echo "  backup      - Backup database"
        echo "  update      - Pull latest code and redeploy"
        echo ""
        exit 0
    fi

    # Get compose file for commands that need it
    COMPOSE_FILE=$(get_compose_file)

    case "$1" in
        setup)
            check_prerequisites
            setup_wizard
            ;;
        quick)
            quick_deploy
            ;;
        deploy)
            full_deploy
            ;;
        ssl)
            setup_ssl
            update_nginx_config
            docker-compose -f $COMPOSE_FILE restart nginx
            ;;
        migrate)
            run_migrations
            ;;
        logs)
            if [ -n "$2" ]; then
                docker-compose -f $COMPOSE_FILE logs -f --tail=100 "$2"
            else
                show_logs
            fi
            ;;
        health)
            health_check
            ;;
        restart)
            source .env.production 2>/dev/null || true
            export $(grep -v '^#' .env.production | xargs) 2>/dev/null || true
            docker-compose -f $COMPOSE_FILE restart
            health_check
            ;;
        stop)
            docker-compose -f $COMPOSE_FILE down
            print_success "Services stopped"
            ;;
        status)
            docker-compose -f $COMPOSE_FILE ps
            echo ""
            print_status "Resource Usage:"
            docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || true
            ;;
        backup)
            backup_db
            ;;
        update)
            update_app
            ;;
        *)
            print_error "Unknown command: $1"
            echo "Run '$0' without arguments to see available commands"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
