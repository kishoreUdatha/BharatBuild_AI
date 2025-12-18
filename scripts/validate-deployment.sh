#!/bin/bash
# ============================================
# BharatBuild AI - Pre-Deployment Validation Script
# Run this before deploying to production
# ============================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================"
echo "BharatBuild AI - Pre-Deployment Validation"
echo "============================================"
echo ""

ERRORS=0
WARNINGS=0

# Function to print success
success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Function to print warning
warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# Function to print error
error() {
    echo -e "${RED}✗${NC} $1"
    ((ERRORS++))
}

# ============================================
# 1. Check required files exist
# ============================================
echo "1. Checking required files..."

FILES_TO_CHECK=(
    "docker-compose.yml"
    "backend/Dockerfile.light"
    "frontend/Dockerfile"
    "backend/requirements.txt"
    "frontend/package.json"
    ".env"
)

for file in "${FILES_TO_CHECK[@]}"; do
    if [ -f "$file" ]; then
        success "$file exists"
    else
        error "$file is MISSING!"
    fi
done

echo ""

# ============================================
# 2. Check environment variables
# ============================================
echo "2. Checking environment variables..."

if [ -f ".env" ]; then
    REQUIRED_VARS=(
        "DATABASE_URL"
        "SECRET_KEY"
        "JWT_SECRET_KEY"
        "ANTHROPIC_API_KEY"
    )

    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${var}=" .env && ! grep -q "^${var}=$" .env; then
            success "$var is set"
        else
            error "$var is NOT set or empty in .env"
        fi
    done
else
    error ".env file not found"
fi

echo ""

# ============================================
# 3. Check Docker is running
# ============================================
echo "3. Checking Docker..."

if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        success "Docker is running"
    else
        error "Docker is installed but not running"
    fi
else
    error "Docker is NOT installed"
fi

echo ""

# ============================================
# 4. Check backend tests pass
# ============================================
echo "4. Running backend tests..."

if [ -d "backend" ]; then
    cd backend
    if pip install -q pytest pytest-asyncio aiosqlite faker httpx 2>/dev/null; then
        if TESTING=true DATABASE_URL="sqlite+aiosqlite:///./test.db" pytest tests/unit -v --tb=short 2>/dev/null; then
            success "Backend unit tests passed"
        else
            warning "Some backend tests failed (check logs)"
        fi
    else
        warning "Could not install test dependencies"
    fi
    cd ..
else
    error "Backend directory not found"
fi

echo ""

# ============================================
# 5. Check frontend builds
# ============================================
echo "5. Checking frontend build..."

if [ -d "frontend" ]; then
    cd frontend
    if npm install --silent 2>/dev/null && npm run build 2>/dev/null; then
        success "Frontend builds successfully"
    else
        error "Frontend build FAILED"
    fi
    cd ..
else
    error "Frontend directory not found"
fi

echo ""

# ============================================
# 6. Check for security issues
# ============================================
echo "6. Running security checks..."

# Check for hardcoded secrets (basic check)
if grep -rE "(password|secret|api_key).*=.*['\"][^'\"]+['\"]" backend/app --include="*.py" 2>/dev/null | grep -v "test" | grep -v "#" | grep -v "settings\." > /dev/null; then
    warning "Possible hardcoded secrets found in backend (review manually)"
else
    success "No obvious hardcoded secrets in backend"
fi

# Check for .env in git
if git ls-files --error-unmatch .env 2>/dev/null; then
    error ".env file is tracked by git - REMOVE IT!"
else
    success ".env is not tracked by git"
fi

echo ""

# ============================================
# 7. Check Docker Compose configuration
# ============================================
echo "7. Validating Docker Compose..."

if docker-compose config -q 2>/dev/null; then
    success "docker-compose.yml is valid"
else
    error "docker-compose.yml has syntax errors"
fi

echo ""

# ============================================
# 8. Check database migrations
# ============================================
echo "8. Checking database migrations..."

if [ -d "backend/alembic/versions" ]; then
    MIGRATION_COUNT=$(ls -1 backend/alembic/versions/*.py 2>/dev/null | wc -l)
    if [ "$MIGRATION_COUNT" -gt 0 ]; then
        success "Found $MIGRATION_COUNT migration files"
    else
        warning "No migration files found"
    fi
else
    warning "Alembic versions directory not found"
fi

echo ""

# ============================================
# Summary
# ============================================
echo "============================================"
echo "VALIDATION SUMMARY"
echo "============================================"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}All checks passed! Ready for deployment.${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}$WARNINGS warning(s), but no errors. Review warnings before deploying.${NC}"
    exit 0
else
    echo -e "${RED}$ERRORS error(s) and $WARNINGS warning(s) found.${NC}"
    echo -e "${RED}Fix errors before deploying!${NC}"
    exit 1
fi
