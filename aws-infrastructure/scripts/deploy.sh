#!/bin/bash
# =============================================================================
# BharatBuild AI - AWS Deployment Script
# =============================================================================
# Usage: ./deploy.sh [command]
# Commands: init, plan, apply, destroy, push-images, update-secrets
# =============================================================================

set -e

# Configuration
AWS_REGION="${AWS_REGION:-ap-south-1}"
APP_NAME="${APP_NAME:-bharatbuild}"
ENVIRONMENT="${ENVIRONMENT:-production}"
TERRAFORM_DIR="../terraform"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed. Please install it first."
        exit 1
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi

    log_success "All prerequisites met!"
}

# Initialize Terraform
terraform_init() {
    log_info "Initializing Terraform..."
    cd "$TERRAFORM_DIR"

    # Create S3 bucket for state if it doesn't exist
    BUCKET_NAME="${APP_NAME}-terraform-state"
    if ! aws s3 ls "s3://${BUCKET_NAME}" 2>&1 > /dev/null; then
        log_info "Creating Terraform state bucket: ${BUCKET_NAME}"
        aws s3 mb "s3://${BUCKET_NAME}" --region "$AWS_REGION"
        aws s3api put-bucket-versioning \
            --bucket "$BUCKET_NAME" \
            --versioning-configuration Status=Enabled
        aws s3api put-bucket-encryption \
            --bucket "$BUCKET_NAME" \
            --server-side-encryption-configuration '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'
    fi

    # Create DynamoDB table for state locking
    TABLE_NAME="${APP_NAME}-terraform-locks"
    if ! aws dynamodb describe-table --table-name "$TABLE_NAME" 2>&1 > /dev/null; then
        log_info "Creating Terraform lock table: ${TABLE_NAME}"
        aws dynamodb create-table \
            --table-name "$TABLE_NAME" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region "$AWS_REGION"
    fi

    terraform init
    log_success "Terraform initialized!"
}

# Plan Terraform changes
terraform_plan() {
    log_info "Planning Terraform changes..."
    cd "$TERRAFORM_DIR"

    if [ ! -f "terraform.tfvars" ]; then
        log_error "terraform.tfvars not found. Create it from terraform.tfvars.example"
        exit 1
    fi

    terraform plan -out=tfplan
    log_success "Plan created! Review and run 'apply' to proceed."
}

# Apply Terraform changes
terraform_apply() {
    log_info "Applying Terraform changes..."
    cd "$TERRAFORM_DIR"

    if [ -f "tfplan" ]; then
        terraform apply tfplan
        rm tfplan
    else
        terraform apply
    fi

    log_success "Infrastructure deployed!"
}

# Destroy infrastructure
terraform_destroy() {
    log_warning "This will DESTROY all infrastructure!"
    read -p "Are you sure? Type 'yes' to confirm: " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "Cancelled."
        exit 0
    fi

    cd "$TERRAFORM_DIR"
    terraform destroy
    log_success "Infrastructure destroyed."
}

# Build and push Docker images
push_images() {
    log_info "Building and pushing Docker images..."

    # Get AWS account ID
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

    # Login to ECR
    log_info "Logging into ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$ECR_REGISTRY"

    # Build and push backend
    log_info "Building backend image..."
    cd "../../backend"
    docker build -f Dockerfile.cpu -t "${ECR_REGISTRY}/${APP_NAME}/backend:latest" .
    docker push "${ECR_REGISTRY}/${APP_NAME}/backend:latest"
    log_success "Backend image pushed!"

    # Build and push frontend
    log_info "Building frontend image..."
    cd "../frontend"

    # Get domain from Terraform output
    DOMAIN_NAME=$(cd "../aws-infrastructure/terraform" && terraform output -raw app_url 2>/dev/null | sed 's|https://||' || echo "your-domain.com")

    docker build \
        --build-arg NEXT_PUBLIC_API_URL="https://${DOMAIN_NAME}/api/v1" \
        --build-arg NEXT_PUBLIC_WS_URL="wss://${DOMAIN_NAME}/ws" \
        -t "${ECR_REGISTRY}/${APP_NAME}/frontend:latest" .
    docker push "${ECR_REGISTRY}/${APP_NAME}/frontend:latest"
    log_success "Frontend image pushed!"

    # Build and push celery (same image as backend)
    docker tag "${ECR_REGISTRY}/${APP_NAME}/backend:latest" "${ECR_REGISTRY}/${APP_NAME}/celery:latest"
    docker push "${ECR_REGISTRY}/${APP_NAME}/celery:latest"
    log_success "Celery image pushed!"

    cd "../aws-infrastructure/scripts"
    log_success "All images pushed to ECR!"
}

# Update secrets in Secrets Manager
update_secrets() {
    log_info "Updating secrets in AWS Secrets Manager..."

    SECRET_NAME="${APP_NAME}/app-secrets"

    # Check if secrets.json exists
    if [ ! -f "secrets.json" ]; then
        log_info "Creating secrets.json template..."
        cat > secrets.json << 'EOF'
{
    "SECRET_KEY": "CHANGE_ME_64_CHAR_RANDOM_STRING_HERE_USE_OPENSSL_RAND_HEX_32",
    "JWT_SECRET_KEY": "CHANGE_ME_64_CHAR_RANDOM_STRING_HERE_USE_OPENSSL_RAND_HEX_32",
    "ANTHROPIC_API_KEY": "sk-ant-api03-YOUR_API_KEY_HERE",
    "GOOGLE_CLIENT_ID": "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com",
    "GOOGLE_CLIENT_SECRET": "YOUR_GOOGLE_CLIENT_SECRET",
    "RAZORPAY_KEY_ID": "YOUR_RAZORPAY_KEY_ID",
    "RAZORPAY_KEY_SECRET": "YOUR_RAZORPAY_KEY_SECRET"
}
EOF
        log_warning "Created secrets.json template. Please edit it with real values and run this command again."
        exit 1
    fi

    # Validate secrets don't contain placeholder values
    if grep -q "CHANGE_ME\|YOUR_" secrets.json; then
        log_error "secrets.json contains placeholder values. Please update with real values."
        exit 1
    fi

    # Update secrets
    aws secretsmanager put-secret-value \
        --secret-id "$SECRET_NAME" \
        --secret-string file://secrets.json \
        --region "$AWS_REGION"

    log_success "Secrets updated!"
    log_warning "Remember to delete secrets.json for security!"
}

# Force new deployment
force_deploy() {
    log_info "Forcing new deployment of all ECS services..."

    aws ecs update-service \
        --cluster "${APP_NAME}-cluster" \
        --service "${APP_NAME}-backend" \
        --force-new-deployment \
        --region "$AWS_REGION" > /dev/null

    aws ecs update-service \
        --cluster "${APP_NAME}-cluster" \
        --service "${APP_NAME}-frontend" \
        --force-new-deployment \
        --region "$AWS_REGION" > /dev/null

    aws ecs update-service \
        --cluster "${APP_NAME}-cluster" \
        --service "${APP_NAME}-celery" \
        --force-new-deployment \
        --region "$AWS_REGION" > /dev/null

    log_success "Deployment triggered! Services will update within a few minutes."
}

# Check service status
check_status() {
    log_info "Checking service status..."

    echo ""
    echo "=== ECS Services ==="
    aws ecs describe-services \
        --cluster "${APP_NAME}-cluster" \
        --services "${APP_NAME}-backend" "${APP_NAME}-frontend" "${APP_NAME}-celery" \
        --query 'services[].{Name:serviceName,Status:status,Running:runningCount,Desired:desiredCount}' \
        --output table \
        --region "$AWS_REGION"

    echo ""
    echo "=== RDS Status ==="
    aws rds describe-db-instances \
        --db-instance-identifier "${APP_NAME}-db" \
        --query 'DBInstances[].{ID:DBInstanceIdentifier,Status:DBInstanceStatus,Endpoint:Endpoint.Address}' \
        --output table \
        --region "$AWS_REGION" 2>/dev/null || echo "RDS not found"

    echo ""
    echo "=== Redis Status ==="
    aws elasticache describe-replication-groups \
        --replication-group-id "${APP_NAME}-redis" \
        --query 'ReplicationGroups[].{ID:ReplicationGroupId,Status:Status,Endpoint:NodeGroups[0].PrimaryEndpoint.Address}' \
        --output table \
        --region "$AWS_REGION" 2>/dev/null || echo "Redis not found"

    echo ""
    log_success "Status check complete!"
}

# View logs
view_logs() {
    SERVICE="${1:-backend}"
    log_info "Viewing logs for ${SERVICE}..."

    aws logs tail "/ecs/${APP_NAME}/${SERVICE}" \
        --follow \
        --region "$AWS_REGION"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."

    # Get a running backend task
    TASK_ARN=$(aws ecs list-tasks \
        --cluster "${APP_NAME}-cluster" \
        --service-name "${APP_NAME}-backend" \
        --query 'taskArns[0]' \
        --output text \
        --region "$AWS_REGION")

    if [ "$TASK_ARN" == "None" ]; then
        log_error "No running backend tasks found"
        exit 1
    fi

    log_info "Running migrations on task: $TASK_ARN"
    aws ecs execute-command \
        --cluster "${APP_NAME}-cluster" \
        --task "$TASK_ARN" \
        --container backend \
        --interactive \
        --command "python -m alembic upgrade head" \
        --region "$AWS_REGION"

    log_success "Migrations complete!"
}

# Invalidate CloudFront cache
invalidate_cache() {
    log_info "Invalidating CloudFront cache..."

    DISTRIBUTION_ID=$(aws cloudfront list-distributions \
        --query "DistributionList.Items[?Comment=='BharatBuild CDN'].Id" \
        --output text \
        --region "$AWS_REGION")

    if [ -z "$DISTRIBUTION_ID" ]; then
        log_error "CloudFront distribution not found"
        exit 1
    fi

    aws cloudfront create-invalidation \
        --distribution-id "$DISTRIBUTION_ID" \
        --paths "/*" \
        --region "$AWS_REGION"

    log_success "Cache invalidation triggered!"
}

# Show help
show_help() {
    echo ""
    echo "BharatBuild AI - AWS Deployment Script"
    echo ""
    echo "Usage: ./deploy.sh [command]"
    echo ""
    echo "Commands:"
    echo "  init            Initialize Terraform (create state bucket, etc.)"
    echo "  plan            Plan Terraform changes"
    echo "  apply           Apply Terraform changes"
    echo "  destroy         Destroy all infrastructure"
    echo "  push-images     Build and push Docker images to ECR"
    echo "  update-secrets  Update secrets in AWS Secrets Manager"
    echo "  force-deploy    Force new deployment of all services"
    echo "  status          Check service status"
    echo "  logs [service]  View logs (backend/frontend/celery)"
    echo "  migrate         Run database migrations"
    echo "  invalidate      Invalidate CloudFront cache"
    echo "  help            Show this help message"
    echo ""
    echo "First-time deployment:"
    echo "  1. ./deploy.sh init"
    echo "  2. Edit terraform.tfvars with your values"
    echo "  3. ./deploy.sh plan"
    echo "  4. ./deploy.sh apply"
    echo "  5. Edit secrets.json with your API keys"
    echo "  6. ./deploy.sh update-secrets"
    echo "  7. ./deploy.sh push-images"
    echo "  8. ./deploy.sh force-deploy"
    echo ""
}

# Main
case "$1" in
    init)
        check_prerequisites
        terraform_init
        ;;
    plan)
        terraform_plan
        ;;
    apply)
        terraform_apply
        ;;
    destroy)
        terraform_destroy
        ;;
    push-images)
        check_prerequisites
        push_images
        ;;
    update-secrets)
        update_secrets
        ;;
    force-deploy)
        force_deploy
        ;;
    status)
        check_status
        ;;
    logs)
        view_logs "$2"
        ;;
    migrate)
        run_migrations
        ;;
    invalidate)
        invalidate_cache
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
