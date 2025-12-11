#!/bin/bash

# ============================================
# BharatBuild AI - Production Deployment Script
# Beta Version
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "Please run as root or with sudo"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    print_success "Prerequisites check passed!"
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

# Show logs
show_logs() {
    docker-compose -f docker-compose.prod.yml logs -f
}

# Health check
health_check() {
    print_status "Running health check..."

    source .env.production

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
}

# Main menu
main() {
    echo "============================================"
    echo "  BharatBuild AI - Production Deployment"
    echo "  Beta Version"
    echo "============================================"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup     - First time setup (prerequisites, env, ssl)"
    echo "  deploy    - Build and deploy all services"
    echo "  ssl       - Setup/renew SSL certificates"
    echo "  migrate   - Run database migrations"
    echo "  logs      - Show service logs"
    echo "  health    - Check service health"
    echo "  restart   - Restart all services"
    echo "  stop      - Stop all services"
    echo "  status    - Show service status"
    echo ""

    case "$1" in
        setup)
            check_prerequisites
            check_env
            setup_ssl
            update_nginx_config
            deploy
            init_minio
            run_migrations
            health_check
            ;;
        deploy)
            check_env
            deploy
            health_check
            ;;
        ssl)
            setup_ssl
            update_nginx_config
            docker-compose -f docker-compose.prod.yml restart nginx
            ;;
        migrate)
            run_migrations
            ;;
        logs)
            show_logs
            ;;
        health)
            health_check
            ;;
        restart)
            docker-compose -f docker-compose.prod.yml restart
            health_check
            ;;
        stop)
            docker-compose -f docker-compose.prod.yml down
            ;;
        status)
            docker-compose -f docker-compose.prod.yml ps
            ;;
        *)
            print_error "Unknown command: $1"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
