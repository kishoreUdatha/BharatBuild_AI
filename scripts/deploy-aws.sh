#!/bin/bash

# ============================================
# BharatBuild AI - AWS ECS Deployment Script
# Quick manual deployment to AWS ECS
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

# Configuration
AWS_REGION="${AWS_REGION:-ap-south-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-930030325663}"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ECS_CLUSTER="${ECS_CLUSTER:-bharatbuild-cluster}"
BACKEND_SERVICE="${BACKEND_SERVICE:-bharatbuild-backend}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-bharatbuild-frontend}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Get current version
get_version() {
    if [ -n "$1" ]; then
        echo "$1"
    else
        # Use git commit hash or timestamp
        if [ -d ".git" ]; then
            git rev-parse --short HEAD
        else
            date +%Y%m%d%H%M%S
        fi
    fi
}

# Generate all tags for an image
generate_tags() {
    local SERVICE=$1
    local VERSION=$2

    # Short SHA
    SHORT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "$VERSION")

    # Full SHA
    FULL_SHA=$(git rev-parse HEAD 2>/dev/null || echo "$VERSION")

    # Version tag (vYYYYMMDD.HHMM)
    VERSION_TAG="v$(date +%Y%m%d.%H%M)"

    # Date tag (YYYY-MM-DD)
    DATE_TAG=$(date +%Y-%m-%d)

    # Branch name
    BRANCH_TAG=$(git rev-parse --abbrev-ref HEAD 2>/dev/null | sed 's/[^a-zA-Z0-9._-]/-/g' || echo "main")

    # Build number (use timestamp if no CI)
    BUILD_NUMBER="build-$(date +%Y%m%d%H%M%S)"

    # Environment tag
    if [ "$BRANCH_TAG" == "main" ] || [ "$BRANCH_TAG" == "production" ]; then
        ENV_TAG="prod"
    elif [ "$BRANCH_TAG" == "develop" ]; then
        ENV_TAG="staging"
    else
        ENV_TAG="dev"
    fi

    # Return all tags
    echo "${ECR_REGISTRY}/bharatbuild/${SERVICE}:${VERSION}"
    echo "${ECR_REGISTRY}/bharatbuild/${SERVICE}:${SHORT_SHA}"
    echo "${ECR_REGISTRY}/bharatbuild/${SERVICE}:${FULL_SHA}"
    echo "${ECR_REGISTRY}/bharatbuild/${SERVICE}:${VERSION_TAG}"
    echo "${ECR_REGISTRY}/bharatbuild/${SERVICE}:${DATE_TAG}"
    echo "${ECR_REGISTRY}/bharatbuild/${SERVICE}:${BRANCH_TAG}"
    echo "${ECR_REGISTRY}/bharatbuild/${SERVICE}:${BUILD_NUMBER}"
    echo "${ECR_REGISTRY}/bharatbuild/${SERVICE}:${ENV_TAG}"
    echo "${ECR_REGISTRY}/bharatbuild/${SERVICE}:${ENV_TAG}-${SHORT_SHA}"
    echo "${ECR_REGISTRY}/bharatbuild/${SERVICE}:latest"
}

# Check AWS CLI
check_aws() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        exit 1
    fi

    # Check if logged in
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI not configured. Run: aws configure"
        exit 1
    fi

    print_success "AWS CLI configured"
}

# Login to ECR
login_ecr() {
    print_status "Logging in to ECR..."
    aws ecr get-login-password --region $AWS_REGION | \
        docker login --username AWS --password-stdin $ECR_REGISTRY
    print_success "ECR login successful"
}

# Build backend image with all tags
build_backend() {
    local VERSION=$1
    print_status "Building backend image (v${VERSION})..."

    # Generate all tag arguments
    local TAGS=""
    while IFS= read -r tag; do
        TAGS="$TAGS -t $tag"
    done < <(generate_tags "backend" "$VERSION")

    # Build with labels
    docker build \
        -f backend/Dockerfile.prod \
        $TAGS \
        --label "org.opencontainers.image.title=BharatBuild Backend" \
        --label "org.opencontainers.image.description=BharatBuild AI Backend Service" \
        --label "org.opencontainers.image.version=${VERSION}" \
        --label "org.opencontainers.image.created=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --label "org.opencontainers.image.revision=$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" \
        --label "org.opencontainers.image.vendor=BharatBuild" \
        --label "com.bharatbuild.git.branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')" \
        --label "com.bharatbuild.git.commit=$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" \
        --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
        --build-arg GIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo 'unknown') \
        --build-arg VERSION=${VERSION} \
        ./backend

    print_success "Backend image built with $(echo "$TAGS" | wc -w) tags"
}

# Build frontend image with all tags
build_frontend() {
    local VERSION=$1
    local API_URL="${NEXT_PUBLIC_API_URL:-https://bharatbuild.ai/api/v1}"
    local WS_URL="${NEXT_PUBLIC_WS_URL:-wss://bharatbuild.ai/ws}"

    print_status "Building frontend image (v${VERSION})..."

    # Generate all tag arguments
    local TAGS=""
    while IFS= read -r tag; do
        TAGS="$TAGS -t $tag"
    done < <(generate_tags "frontend" "$VERSION")

    # Build with labels
    docker build \
        -f frontend/Dockerfile.prod \
        $TAGS \
        --label "org.opencontainers.image.title=BharatBuild Frontend" \
        --label "org.opencontainers.image.description=BharatBuild AI Frontend Service" \
        --label "org.opencontainers.image.version=${VERSION}" \
        --label "org.opencontainers.image.created=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --label "org.opencontainers.image.revision=$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" \
        --label "org.opencontainers.image.vendor=BharatBuild" \
        --label "com.bharatbuild.git.branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')" \
        --label "com.bharatbuild.git.commit=$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" \
        --build-arg NEXT_PUBLIC_API_URL=${API_URL} \
        --build-arg NEXT_PUBLIC_WS_URL=${WS_URL} \
        --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
        --build-arg GIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo 'unknown') \
        --build-arg VERSION=${VERSION} \
        ./frontend

    print_success "Frontend image built with $(echo "$TAGS" | wc -w) tags"
}

# Push images to ECR (all tags)
push_images() {
    local VERSION=$1

    print_status "Pushing backend images (all tags)..."
    while IFS= read -r tag; do
        print_status "  Pushing $tag"
        docker push "$tag"
    done < <(generate_tags "backend" "$VERSION")

    print_status "Pushing frontend images (all tags)..."
    while IFS= read -r tag; do
        print_status "  Pushing $tag"
        docker push "$tag"
    done < <(generate_tags "frontend" "$VERSION")

    print_success "All images pushed to ECR"
}

# List all tags for a service
list_tags() {
    local SERVICE=${1:-backend}
    local VERSION=$(get_version)

    echo ""
    echo "Tags for ${SERVICE}:"
    echo "===================="
    generate_tags "$SERVICE" "$VERSION"
    echo ""
}

# Update ECS service
update_ecs_service() {
    local SERVICE=$1
    local VERSION=$2

    print_status "Updating ECS service: ${SERVICE}..."

    # Get current task definition
    TASK_DEF=$(aws ecs describe-services \
        --cluster $ECS_CLUSTER \
        --services $SERVICE \
        --query 'services[0].taskDefinition' \
        --output text)

    # Get task definition family
    TASK_FAMILY=$(echo $TASK_DEF | sed 's/:.*$//')

    # Get current task definition JSON
    aws ecs describe-task-definition \
        --task-definition $TASK_DEF \
        --query 'taskDefinition' > /tmp/task-def.json

    # Update image in task definition
    CONTAINER_NAME=$(echo $SERVICE | sed 's/bharatbuild-//')
    NEW_IMAGE="${ECR_REGISTRY}/bharatbuild/${CONTAINER_NAME}:${VERSION}"

    # Create new task definition with updated image
    jq --arg IMAGE "$NEW_IMAGE" --arg CONTAINER "$CONTAINER_NAME" \
        '.containerDefinitions |= map(if .name == $CONTAINER then .image = $IMAGE else . end) |
         del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)' \
        /tmp/task-def.json > /tmp/new-task-def.json

    # Register new task definition
    NEW_TASK_DEF=$(aws ecs register-task-definition \
        --cli-input-json file:///tmp/new-task-def.json \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text)

    print_status "New task definition: $NEW_TASK_DEF"

    # Update service
    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service $SERVICE \
        --task-definition $NEW_TASK_DEF \
        --force-new-deployment \
        > /dev/null

    print_success "Service ${SERVICE} updated"
}

# Wait for service stability
wait_for_stability() {
    local SERVICE=$1

    print_status "Waiting for ${SERVICE} to stabilize..."

    aws ecs wait services-stable \
        --cluster $ECS_CLUSTER \
        --services $SERVICE

    print_success "${SERVICE} is stable"
}

# Check service health
check_health() {
    print_status "Checking service health..."

    # Get ALB DNS
    ALB_DNS=$(aws elbv2 describe-load-balancers \
        --names bharatbuild-alb \
        --query 'LoadBalancers[0].DNSName' \
        --output text 2>/dev/null || echo "bharatbuild-alb-223139118.ap-south-1.elb.amazonaws.com")

    # Check backend health
    BACKEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" \
        "http://${ALB_DNS}/api/v1/health" 2>/dev/null || echo "000")

    if [ "$BACKEND_HEALTH" == "200" ]; then
        print_success "Backend: Healthy (HTTP 200)"
    else
        print_warning "Backend: HTTP $BACKEND_HEALTH"
    fi

    # Check frontend
    FRONTEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" \
        "http://${ALB_DNS}/" 2>/dev/null || echo "000")

    if [ "$FRONTEND_HEALTH" == "200" ]; then
        print_success "Frontend: Healthy (HTTP 200)"
    else
        print_warning "Frontend: HTTP $FRONTEND_HEALTH"
    fi
}

# Full deployment
deploy() {
    local VERSION=$(get_version $1)

    echo ""
    echo "=========================================="
    echo "  BharatBuild AI - AWS ECS Deployment"
    echo "  Version: ${VERSION}"
    echo "=========================================="
    echo ""

    check_aws
    login_ecr

    # Build images
    build_backend $VERSION
    build_frontend $VERSION

    # Push to ECR
    push_images $VERSION

    # Update ECS services
    update_ecs_service $BACKEND_SERVICE $VERSION
    update_ecs_service $FRONTEND_SERVICE $VERSION

    # Wait for stability
    wait_for_stability $BACKEND_SERVICE
    wait_for_stability $FRONTEND_SERVICE

    # Health check
    check_health

    echo ""
    print_success "Deployment complete!"
    echo ""
    echo "Version: ${VERSION}"
    echo "Backend:  ${ECR_REGISTRY}/bharatbuild/backend:${VERSION}"
    echo "Frontend: ${ECR_REGISTRY}/bharatbuild/frontend:${VERSION}"
    echo ""
}

# Deploy only backend
deploy_backend() {
    local VERSION=$(get_version $1)

    print_status "Deploying backend only (v${VERSION})..."

    check_aws
    login_ecr
    build_backend $VERSION

    docker push ${ECR_REGISTRY}/bharatbuild/backend:${VERSION}
    docker push ${ECR_REGISTRY}/bharatbuild/backend:latest

    update_ecs_service $BACKEND_SERVICE $VERSION
    wait_for_stability $BACKEND_SERVICE
    check_health

    print_success "Backend deployment complete!"
}

# Deploy only frontend
deploy_frontend() {
    local VERSION=$(get_version $1)

    print_status "Deploying frontend only (v${VERSION})..."

    check_aws
    login_ecr
    build_frontend $VERSION

    docker push ${ECR_REGISTRY}/bharatbuild/frontend:${VERSION}
    docker push ${ECR_REGISTRY}/bharatbuild/frontend:latest

    update_ecs_service $FRONTEND_SERVICE $VERSION
    wait_for_stability $FRONTEND_SERVICE
    check_health

    print_success "Frontend deployment complete!"
}

# Force new deployment (restart services)
force_deploy() {
    print_status "Forcing new deployment..."

    check_aws

    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service $BACKEND_SERVICE \
        --force-new-deployment \
        > /dev/null

    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service $FRONTEND_SERVICE \
        --force-new-deployment \
        > /dev/null

    wait_for_stability $BACKEND_SERVICE
    wait_for_stability $FRONTEND_SERVICE

    print_success "Force deployment complete!"
}

# Rollback to previous version
rollback() {
    local SERVICE=${1:-$BACKEND_SERVICE}

    print_status "Rolling back ${SERVICE}..."

    check_aws

    # Get current task definition
    CURRENT_TASK=$(aws ecs describe-services \
        --cluster $ECS_CLUSTER \
        --services $SERVICE \
        --query 'services[0].taskDefinition' \
        --output text)

    # Get task family
    TASK_FAMILY=$(echo $CURRENT_TASK | sed 's/:.*$//')

    # Get previous revision
    PREVIOUS_TASK=$(aws ecs list-task-definitions \
        --family-prefix $TASK_FAMILY \
        --sort DESC \
        --query 'taskDefinitionArns[1]' \
        --output text)

    if [ -z "$PREVIOUS_TASK" ] || [ "$PREVIOUS_TASK" == "None" ]; then
        print_error "No previous task definition found"
        exit 1
    fi

    print_status "Rolling back to: $PREVIOUS_TASK"

    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service $SERVICE \
        --task-definition $PREVIOUS_TASK \
        --force-new-deployment \
        > /dev/null

    wait_for_stability $SERVICE

    print_success "Rollback complete!"
}

# Show service status
status() {
    print_status "Checking service status..."

    check_aws

    echo ""
    echo "ECS Cluster: $ECS_CLUSTER"
    echo ""

    # Backend service
    echo "Backend Service:"
    aws ecs describe-services \
        --cluster $ECS_CLUSTER \
        --services $BACKEND_SERVICE \
        --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,TaskDef:taskDefinition}' \
        --output table

    # Frontend service
    echo ""
    echo "Frontend Service:"
    aws ecs describe-services \
        --cluster $ECS_CLUSTER \
        --services $FRONTEND_SERVICE \
        --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,TaskDef:taskDefinition}' \
        --output table

    # Recent deployments
    echo ""
    echo "Recent Backend Deployments:"
    aws ecs describe-services \
        --cluster $ECS_CLUSTER \
        --services $BACKEND_SERVICE \
        --query 'services[0].deployments[*].{Status:status,Running:runningCount,Desired:desiredCount,Created:createdAt}' \
        --output table

    check_health
}

# View logs
logs() {
    local SERVICE=${1:-backend}
    local LINES=${2:-100}

    print_status "Fetching logs for ${SERVICE}..."

    check_aws

    aws logs tail /ecs/bharatbuild/${SERVICE} \
        --follow \
        --since 1h
}

# Main
main() {
    case "${1:-help}" in
        deploy)
            deploy $2
            ;;
        backend)
            deploy_backend $2
            ;;
        frontend)
            deploy_frontend $2
            ;;
        force)
            force_deploy
            ;;
        rollback)
            rollback $2
            ;;
        status)
            status
            ;;
        health)
            check_health
            ;;
        logs)
            logs $2 $3
            ;;
        tags)
            list_tags $2
            ;;
        help|*)
            echo ""
            echo "BharatBuild AI - AWS ECS Deployment"
            echo ""
            echo "Usage: $0 <command> [version]"
            echo ""
            echo "Commands:"
            echo "  deploy [version]    Full deployment (backend + frontend)"
            echo "  backend [version]   Deploy backend only"
            echo "  frontend [version]  Deploy frontend only"
            echo "  force               Force restart all services"
            echo "  rollback [service]  Rollback to previous version"
            echo "  status              Show service status"
            echo "  health              Check service health"
            echo "  logs [service]      View service logs"
            echo "  tags [service]      List all tags that will be created"
            echo ""
            echo "Docker Image Tags Generated:"
            echo "  - <version>         Custom version (e.g., v42)"
            echo "  - <short-sha>       Git short SHA (e.g., abc1234)"
            echo "  - <full-sha>        Git full SHA"
            echo "  - v<date>.<time>    Version tag (e.g., v20241212.1430)"
            echo "  - <date>            Date tag (e.g., 2024-12-12)"
            echo "  - <branch>          Branch name (e.g., main, develop)"
            echo "  - build-<number>    Build number"
            echo "  - <env>             Environment (prod, staging, dev)"
            echo "  - <env>-<sha>       Environment + short SHA"
            echo "  - latest            Latest tag"
            echo ""
            echo "Examples:"
            echo "  $0 deploy           # Deploy with auto-generated version"
            echo "  $0 deploy v42       # Deploy with specific version"
            echo "  $0 backend          # Deploy only backend"
            echo "  $0 rollback         # Rollback backend to previous version"
            echo "  $0 tags backend     # List tags for backend"
            echo ""
            ;;
    esac
}

main "$@"
