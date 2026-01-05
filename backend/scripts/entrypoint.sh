#!/bin/bash
# ============================================
# BharatBuild AI - Container Entrypoint
# Handles database migrations before app start
# ============================================

set -e

echo "============================================"
echo "  BharatBuild AI - Starting Container"
echo "============================================"
echo ""

# =============================================================================
# Fetch Docker TLS certificates from Secrets Manager (if enabled)
# =============================================================================
fetch_docker_tls_certs() {
    if [ "$DOCKER_TLS_ENABLED" != "true" ] && [ "$DOCKER_TLS_ENABLED" != "True" ]; then
        echo "[Entrypoint] Docker TLS disabled, skipping certificate fetch"
        return 0
    fi

    echo "[Entrypoint] Docker TLS enabled, fetching certificates from Secrets Manager..."

    # Check if aws cli is available
    if ! command -v aws &> /dev/null; then
        echo "[Entrypoint] WARNING: AWS CLI not found, skipping TLS cert fetch"
        return 0
    fi

    # Create certs directory
    mkdir -p /certs
    chmod 700 /certs

    local REGION="${AWS_REGION:-ap-south-1}"
    local SUCCESS_COUNT=0

    # Fetch CA cert
    if [ -n "$DOCKER_TLS_CA_SECRET" ]; then
        echo "[Entrypoint] Fetching CA cert: $DOCKER_TLS_CA_SECRET"
        if aws secretsmanager get-secret-value \
            --secret-id "$DOCKER_TLS_CA_SECRET" \
            --query 'SecretString' \
            --output text \
            --region "$REGION" 2>/dev/null | base64 -d > /certs/ca.pem 2>/dev/null; then
            chmod 600 /certs/ca.pem
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            echo "[Entrypoint] CA cert saved to /certs/ca.pem"
        else
            echo "[Entrypoint] WARNING: Failed to fetch CA cert"
            rm -f /certs/ca.pem 2>/dev/null
        fi
    fi

    # Fetch client cert
    if [ -n "$DOCKER_TLS_CERT_SECRET" ]; then
        echo "[Entrypoint] Fetching client cert: $DOCKER_TLS_CERT_SECRET"
        if aws secretsmanager get-secret-value \
            --secret-id "$DOCKER_TLS_CERT_SECRET" \
            --query 'SecretString' \
            --output text \
            --region "$REGION" 2>/dev/null | base64 -d > /certs/client-cert.pem 2>/dev/null; then
            chmod 600 /certs/client-cert.pem
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            echo "[Entrypoint] Client cert saved to /certs/client-cert.pem"
        else
            echo "[Entrypoint] WARNING: Failed to fetch client cert"
            rm -f /certs/client-cert.pem 2>/dev/null
        fi
    fi

    # Fetch client key
    if [ -n "$DOCKER_TLS_KEY_SECRET" ]; then
        echo "[Entrypoint] Fetching client key: $DOCKER_TLS_KEY_SECRET"
        if aws secretsmanager get-secret-value \
            --secret-id "$DOCKER_TLS_KEY_SECRET" \
            --query 'SecretString' \
            --output text \
            --region "$REGION" 2>/dev/null | base64 -d > /certs/client-key.pem 2>/dev/null; then
            chmod 600 /certs/client-key.pem
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            echo "[Entrypoint] Client key saved to /certs/client-key.pem"
        else
            echo "[Entrypoint] WARNING: Failed to fetch client key"
            rm -f /certs/client-key.pem 2>/dev/null
        fi
    fi

    if [ $SUCCESS_COUNT -eq 3 ]; then
        echo "[Entrypoint] All Docker TLS certificates loaded successfully"
        ls -la /certs/
    else
        echo "[Entrypoint] WARNING: Only $SUCCESS_COUNT/3 TLS certs loaded (will use SSM fallback)"
    fi
}

# Fetch Docker TLS certs before anything else
fetch_docker_tls_certs

# Wait for database to be ready
wait_for_db() {
    echo "[Entrypoint] Waiting for database to be ready..."

    MAX_RETRIES=30
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if python -c "
from sqlalchemy import create_engine
from app.core.config import settings
import sys

try:
    # Convert async URL to sync for checking
    db_url = settings.DATABASE_URL
    if '+asyncpg' in db_url:
        db_url = db_url.replace('+asyncpg', '')
    elif 'postgresql+asyncpg' in db_url:
        db_url = db_url.replace('postgresql+asyncpg', 'postgresql')

    engine = create_engine(db_url)
    conn = engine.connect()
    conn.close()
    print('[Entrypoint] Database is ready!')
    sys.exit(0)
except Exception as e:
    print(f'[Entrypoint] Database not ready: {e}')
    sys.exit(1)
" 2>/dev/null; then
            return 0
        fi

        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "[Entrypoint] Database not ready, retrying in 2s... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 2
    done

    echo "[Entrypoint] ERROR: Database not available after $MAX_RETRIES attempts"
    exit 1
}

# Run database migrations
run_migrations() {
    echo "[Entrypoint] Running database migrations..."

    cd /app

    # Check if alembic is available
    if ! command -v alembic &> /dev/null; then
        echo "[Entrypoint] WARNING: Alembic not found, skipping migrations"
        return 0
    fi

    # Check current migration status
    echo "[Entrypoint] Checking migration status..."
    alembic current 2>&1 || true

    # Run migrations with error tolerance
    # DuplicateTable errors are expected when tables already exist
    echo "[Entrypoint] Applying migrations..."
    set +e  # Temporarily disable exit on error
    MIGRATION_OUTPUT=$(alembic upgrade head 2>&1)
    MIGRATION_EXIT=$?
    set -e  # Re-enable exit on error

    if [ $MIGRATION_EXIT -eq 0 ]; then
        echo "[Entrypoint] Migrations completed successfully!"
    elif echo "$MIGRATION_OUTPUT" | grep -q "DuplicateTable\|already exists\|Duplicate column\|duplicate key"; then
        echo "[Entrypoint] Tables already exist (expected), continuing..."
        # Stamp the current revision to mark migrations as complete
        alembic stamp head 2>&1 || true
    else
        echo "[Entrypoint] WARNING: Migration had issues: $MIGRATION_OUTPUT"
        echo "[Entrypoint] Continuing anyway..."
    fi

    # Show final status
    echo "[Entrypoint] Current migration status:"
    alembic current 2>&1 || true
}

# Initialize database tables (fallback if migrations fail)
init_tables() {
    echo "[Entrypoint] Ensuring database tables exist..."

    python -c "
from app.core.database import Base, get_engine
from app.models import *  # Import all models
import asyncio

async def init():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print('[Entrypoint] Database tables verified/created')

asyncio.run(init())
" || echo "[Entrypoint] WARNING: Table initialization had issues"
}

# Main execution
main() {
    # Skip DB operations if SKIP_DB_INIT is set (for testing)
    if [ "$SKIP_DB_INIT" = "true" ]; then
        echo "[Entrypoint] Skipping database initialization (SKIP_DB_INIT=true)"
    else
        # Wait for database
        wait_for_db

        # First ensure base tables exist (SQLAlchemy create_all is idempotent)
        init_tables

        # Then run migrations to add columns/indexes
        run_migrations
    fi

    echo ""
    echo "============================================"
    echo "  Starting Application"
    echo "============================================"
    echo ""

    # Execute the main command
    exec "$@"
}

# Run main with all passed arguments
main "$@"
