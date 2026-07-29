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
# Fetch Docker TLS certificates for talking to the sandbox Docker daemon.
#
# These are published by the sandbox EC2 user_data (see ec2-sandbox.tf) into SSM
# PARAMETER STORE at /<app>/docker/{ca-cert,client-cert,client-key}. An earlier
# version of this script read them from Secrets Manager instead, which is a
# different service holding different (non-existent) names -- the fetch always
# failed, and because the failure was silent the container ran with 0-byte cert
# files and every sandbox exec returned "Docker service is not available".
#
# The values are stored as raw PEM. Base64 is still accepted so that either
# encoding works.
# =============================================================================
fetch_docker_tls_certs() {
    if [ "$DOCKER_TLS_ENABLED" != "true" ] && [ "$DOCKER_TLS_ENABLED" != "True" ]; then
        echo "[Entrypoint] Docker TLS disabled, skipping certificate fetch"
        return 0
    fi

    if ! command -v aws &> /dev/null; then
        echo "[Entrypoint] WARNING: AWS CLI not found, skipping TLS cert fetch"
        return 0
    fi

    local REGION="${AWS_REGION:-ap-south-2}"
    local CA_PARAM="${DOCKER_TLS_CA_PARAM:-/bharatbuild/docker/ca-cert}"
    local CERT_PARAM="${DOCKER_TLS_CERT_PARAM:-/bharatbuild/docker/client-cert}"
    local KEY_PARAM="${DOCKER_TLS_KEY_PARAM:-/bharatbuild/docker/client-key}"

    echo "[Entrypoint] Docker TLS enabled, fetching certificates from SSM Parameter Store (region: $REGION)"

    mkdir -p /certs
    chmod 700 /certs

    # Fetch one SSM parameter into a PEM file.
    # Deliberately assigns to a variable first rather than piping straight to the
    # file: in a pipeline `if` inspects only the LAST command's status, so a
    # failed aws call followed by `base64 -d` (which happily exits 0 on empty
    # input) previously looked like success and produced an empty file.
    _fetch_pem() {
        local param="$1" dest="$2" label="$3" value=""

        if ! value=$(aws ssm get-parameter \
                        --name "$param" \
                        --with-decryption \
                        --query 'Parameter.Value' \
                        --output text \
                        --region "$REGION" 2>&1); then
            echo "[Entrypoint] ERROR: could not read $label from SSM ($param): $value"
            return 1
        fi

        if [ -z "$value" ] || [ "$value" = "None" ]; then
            echo "[Entrypoint] ERROR: $label ($param) is empty"
            return 1
        fi

        case "$value" in
            -----BEGIN*)
                printf '%s\n' "$value" > "$dest"
                ;;
            *)
                if ! printf '%s' "$value" | base64 -d > "$dest" 2>/dev/null; then
                    echo "[Entrypoint] ERROR: $label ($param) is neither PEM nor valid base64"
                    rm -f "$dest"
                    return 1
                fi
                ;;
        esac

        if ! grep -q -- "-----BEGIN" "$dest" 2>/dev/null; then
            echo "[Entrypoint] ERROR: $label ($param) did not yield a PEM document"
            rm -f "$dest"
            return 1
        fi

        chmod 600 "$dest"
        echo "[Entrypoint] $label OK ($(wc -c < "$dest") bytes)"
        return 0
    }

    local OK=0
    _fetch_pem "$CA_PARAM"   /certs/ca.pem          "CA cert"    && OK=$((OK + 1))
    _fetch_pem "$CERT_PARAM" /certs/client-cert.pem "client cert" && OK=$((OK + 1))
    _fetch_pem "$KEY_PARAM"  /certs/client-key.pem  "client key"  && OK=$((OK + 1))

    if [ "$OK" -eq 3 ]; then
        echo "[Entrypoint] All 3 Docker TLS certificates loaded"
    else
        # Not fatal: the app still serves normally, only sandbox code execution
        # is affected. But say so loudly instead of claiming success.
        echo "[Entrypoint] WARNING: only $OK/3 Docker TLS certificates loaded."
        echo "[Entrypoint] WARNING: sandbox code execution will fail until this is fixed."
        rm -f /certs/ca.pem /certs/client-cert.pem /certs/client-key.pem 2>/dev/null || true
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

# Seed campus drive data if not exists
seed_campus_drive() {
    echo "[Entrypoint] Checking campus drive seed data..."

    python -c "
import asyncio
from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal
from app.models.campus_drive import CampusDrive, CampusDriveQuestion, QuestionCategory

async def seed():
    async with AsyncSessionLocal() as db:
        # Check if campus drive exists
        result = await db.execute(select(CampusDrive).where(CampusDrive.name == 'Campus Placement Drive 2026'))
        if result.scalar_one_or_none():
            print('[Entrypoint] Campus drive data already exists')
            return

        print('[Entrypoint] Seeding campus drive data...')

        # Create campus drive
        drive = CampusDrive(
            name='Campus Placement Drive 2026',
            company_name='BharatBuild',
            description='Annual campus placement drive for engineering students.',
            quiz_duration_minutes=60,
            passing_percentage=60.0,
            total_questions=30,
            logical_questions=5,
            technical_questions=10,
            ai_ml_questions=10,
            english_questions=5,
            is_active=True
        )
        db.add(drive)
        await db.flush()

        # Seed questions
        questions = [
            ('If all Bloops are Razzies and all Razzies are Lazzies, then all Bloops are definitely Lazzies?', QuestionCategory.LOGICAL, ['True', 'False', 'Cannot be determined', 'Partially true'], 0),
            ('A is brother of B. B is sister of C. D is father of A. How is C related to D?', QuestionCategory.LOGICAL, ['Daughter', 'Son', 'Granddaughter', 'Cannot be determined'], 3),
            ('Complete: 2, 6, 12, 20, 30, ?', QuestionCategory.LOGICAL, ['40', '42', '44', '46'], 1),
            ('Odd one out: 8, 27, 64, 100, 125, 216', QuestionCategory.LOGICAL, ['27', '64', '100', '125'], 2),
            ('Clock shows 3:15. Angle between hands?', QuestionCategory.LOGICAL, ['0°', '7.5°', '15°', '22.5°'], 1),
            ('Ram 7th from left, Shyam 9th from right. After swap Ram is 11th. Total students?', QuestionCategory.LOGICAL, ['17', '18', '19', '20'], 2),
            ('Time complexity of binary search?', QuestionCategory.TECHNICAL, ['O(n)', 'O(log n)', 'O(n log n)', 'O(1)'], 1),
            ('Which uses LIFO?', QuestionCategory.TECHNICAL, ['Queue', 'Stack', 'Array', 'Linked List'], 1),
            ('Output of print(type([]) == type({}))?', QuestionCategory.TECHNICAL, ['True', 'False', 'Error', 'None'], 1),
            ('Which HTTP method is idempotent?', QuestionCategory.TECHNICAL, ['POST', 'GET', 'PATCH', 'None'], 1),
            ('SQL stands for?', QuestionCategory.TECHNICAL, ['Structured Query Language', 'Simple Query Language', 'Standard Query Language', 'Sequential Query Language'], 0),
            ('Best average case sorting?', QuestionCategory.TECHNICAL, ['Bubble Sort', 'Insertion Sort', 'Quick Sort', 'Selection Sort'], 2),
            ('Purpose of finally block?', QuestionCategory.TECHNICAL, ['Only if exception', 'Only if no exception', 'Always execute', 'Skip handling'], 2),
            ('NOT a JavaScript data type?', QuestionCategory.TECHNICAL, ['Boolean', 'Undefined', 'Integer', 'Symbol'], 2),
            ('Difference between == and ===?', QuestionCategory.TECHNICAL, ['No difference', '=== checks type', '== checks type', '=== is faster'], 1),
            ('CSS property for background color?', QuestionCategory.TECHNICAL, ['color', 'bgcolor', 'background-color', 'background'], 2),
            ('Git is used for?', QuestionCategory.TECHNICAL, ['Database', 'Version control', 'Web hosting', 'Compilation'], 1),
            ('Which is NoSQL database?', QuestionCategory.TECHNICAL, ['MySQL', 'PostgreSQL', 'MongoDB', 'Oracle'], 2),
            ('CNN stands for?', QuestionCategory.AI_ML, ['Central Neural Network', 'Convolutional Neural Network', 'Connected Neural Network', 'Computed Neural Network'], 1),
            ('Algorithm for classification?', QuestionCategory.AI_ML, ['Linear Regression', 'K-Means', 'Random Forest', 'PCA'], 2),
            ('What is overfitting?', QuestionCategory.AI_ML, ['Good on train, bad on test', 'Bad on train', 'Slow training', 'High memory'], 0),
            ('Common activation in hidden layers?', QuestionCategory.AI_ML, ['Sigmoid', 'Tanh', 'ReLU', 'Softmax'], 2),
            ('Purpose of learning rate?', QuestionCategory.AI_ML, ['Model complexity', 'Step size', 'Regularization', 'Batch size'], 1),
            ('Metric for classification?', QuestionCategory.AI_ML, ['RMSE', 'MAE', 'Accuracy', 'R-squared'], 2),
            ('Learning with labeled data?', QuestionCategory.AI_ML, ['Unsupervised', 'Supervised', 'Reinforcement', 'Semi-supervised'], 1),
            ('Deep learning library?', QuestionCategory.AI_ML, ['NumPy', 'Pandas', 'TensorFlow', 'Matplotlib'], 2),
            ('Purpose of dropout?', QuestionCategory.AI_ML, ['Speed up', 'Prevent overfitting', 'Increase accuracy', 'Reduce memory'], 1),
            ('Clustering algorithm?', QuestionCategory.AI_ML, ['Linear Regression', 'Decision Tree', 'K-Means', 'Naive Bayes'], 2),
            ('NLP stands for?', QuestionCategory.AI_ML, ['Neural Learning Process', 'Natural Language Processing', 'Network Layer Protocol', 'Non-Linear Programming'], 1),
            ('Improvement over gradient descent?', QuestionCategory.AI_ML, ['SGD', 'Adam', 'RMSprop', 'All of above'], 3),
            ('Correct sentence?', QuestionCategory.ENGLISH, ['He dont know nothing', 'He doesnt know anything', 'He dont know anything', 'He doesnt know nothing'], 1),
            ('Synonym of Eloquent?', QuestionCategory.ENGLISH, ['Silent', 'Articulate', 'Humble', 'Arrogant'], 1),
            ('Antonym of Benevolent?', QuestionCategory.ENGLISH, ['Kind', 'Generous', 'Malevolent', 'Caring'], 2),
            ('She ___ to the store yesterday.', QuestionCategory.ENGLISH, ['go', 'goes', 'went', 'going'], 2),
            ('Grammatically correct?', QuestionCategory.ENGLISH, ['Me and him went', 'Him and me went', 'He and I went', 'I and he went'], 2),
            ('Ubiquitous means?', QuestionCategory.ENGLISH, ['Rare', 'Present everywhere', 'Unique', 'Unknown'], 1),
        ]

        for text, category, options, correct in questions:
            q = CampusDriveQuestion(
                question_text=text,
                category=category,
                options=options,
                correct_option=correct,
                marks=1.0,
                is_global=True
            )
            db.add(q)

        await db.commit()
        print('[Entrypoint] Campus drive data seeded successfully!')

asyncio.run(seed())
" || echo "[Entrypoint] WARNING: Campus drive seeding had issues"
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

        # Seed campus drive data if not exists
        seed_campus_drive
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
