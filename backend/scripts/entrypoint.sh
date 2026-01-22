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
            ('A is brother of B. B is sister of C. D is father of A. How is C related to D?', QuestionCategory.LOGICAL, ['Daughter', 'Son', 'Granddaughter', 'Cannot be determined'], 0),
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
