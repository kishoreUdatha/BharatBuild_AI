#!/bin/bash
# =============================================================================
# Docker Entrypoint Script for BharatBuild Backend
# =============================================================================
# Fetches Docker TLS certificates from AWS Secrets Manager at container startup
# and writes them to /certs/ directory for Docker API authentication.
# =============================================================================

set -e

# Function to fetch and decode a secret from Secrets Manager
fetch_secret_to_file() {
    local secret_name=$1
    local output_file=$2

    if [ -z "$secret_name" ]; then
        echo "[Entrypoint] No secret name provided for $output_file, skipping"
        return 0
    fi

    echo "[Entrypoint] Fetching secret: $secret_name -> $output_file"

    # Fetch from Secrets Manager and decode base64
    if aws secretsmanager get-secret-value \
        --secret-id "$secret_name" \
        --query 'SecretString' \
        --output text \
        --region "${AWS_REGION:-ap-south-1}" 2>/dev/null | base64 -d > "$output_file" 2>/dev/null; then
        chmod 600 "$output_file"
        echo "[Entrypoint] Successfully wrote $output_file"
        return 0
    else
        echo "[Entrypoint] Failed to fetch $secret_name (may not exist)"
        rm -f "$output_file" 2>/dev/null
        return 1
    fi
}

# =============================================================================
# Fetch Docker TLS certificates if configured
# =============================================================================
if [ "$DOCKER_TLS_ENABLED" = "true" ] || [ "$DOCKER_TLS_ENABLED" = "True" ]; then
    echo "[Entrypoint] Docker TLS enabled, fetching certificates..."

    # Create certs directory
    mkdir -p /certs
    chmod 700 /certs

    # Fetch each certificate
    CA_SUCCESS=false
    CERT_SUCCESS=false
    KEY_SUCCESS=false

    if fetch_secret_to_file "$DOCKER_TLS_CA_SECRET" "/certs/ca.pem"; then
        CA_SUCCESS=true
    fi

    if fetch_secret_to_file "$DOCKER_TLS_CERT_SECRET" "/certs/client-cert.pem"; then
        CERT_SUCCESS=true
    fi

    if fetch_secret_to_file "$DOCKER_TLS_KEY_SECRET" "/certs/client-key.pem"; then
        KEY_SUCCESS=true
    fi

    # Check if all certs were fetched successfully
    if [ "$CA_SUCCESS" = "true" ] && [ "$CERT_SUCCESS" = "true" ] && [ "$KEY_SUCCESS" = "true" ]; then
        echo "[Entrypoint] All Docker TLS certificates loaded successfully"
        ls -la /certs/
    else
        echo "[Entrypoint] Warning: Not all Docker TLS certificates could be loaded"
        echo "[Entrypoint] CA: $CA_SUCCESS, Cert: $CERT_SUCCESS, Key: $KEY_SUCCESS"
        echo "[Entrypoint] Docker client will fall back to SSM restore method"
    fi
else
    echo "[Entrypoint] Docker TLS disabled, skipping certificate fetch"
fi

# =============================================================================
# Execute the main command
# =============================================================================
echo "[Entrypoint] Starting application: $@"
exec "$@"
