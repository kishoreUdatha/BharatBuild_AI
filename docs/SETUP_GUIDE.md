# Setup Guide

Complete guide to set up BharatBuild AI platform for local development.

## Prerequisites

Ensure you have the following installed:

- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL 14+**
- **Redis 7+**
- **Docker & Docker Compose** (recommended)
- **Git**

## Quick Start (Docker - Recommended)

### 1. Clone Repository

```bash
git clone <repository-url>
cd BharatBuild_AI
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set required variables:
```bash
# Minimum required configuration
ANTHROPIC_API_KEY=your-claude-api-key
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
```

### 3. Start Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- Redis (port 6379)
- MinIO (ports 9000, 9001)
- Backend API (port 8000)
- Frontend (port 3000)
- Celery Worker
- Celery Beat

### 4. Run Migrations

```bash
docker-compose exec backend alembic upgrade head
```

### 5. Access Applications

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **MinIO Console:** http://localhost:9001

## Manual Setup (Without Docker)

### Backend Setup

#### 1. Create Virtual Environment

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Setup PostgreSQL

```bash
# Create database
createdb bharatbuild_db

# Or using psql
psql -U postgres
CREATE DATABASE bharatbuild_db;
CREATE USER bharatbuild WITH PASSWORD 'bharatbuild123';
GRANT ALL PRIVILEGES ON DATABASE bharatbuild_db TO bharatbuild;
\q
```

#### 4. Setup Redis

```bash
# Install Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# Start Redis
sudo systemctl start redis

# Or using Homebrew (macOS)
brew install redis
brew services start redis
```

#### 5. Configure Environment

```bash
cp ../.env.example .env
```

Edit `.env` with your configuration:
```bash
DATABASE_URL=postgresql://bharatbuild:bharatbuild123@localhost:5432/bharatbuild_db
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=your-api-key
```

#### 6. Run Migrations

```bash
alembic upgrade head
```

#### 7. Start Backend

```bash
uvicorn app.main:app --reload
```

Backend will be available at http://localhost:8000

#### 8. Start Celery Worker (Optional)

In a new terminal:
```bash
celery -A app.core.celery_app worker --loglevel=info
```

#### 9. Start Celery Beat (Optional)

In another terminal:
```bash
celery -A app.core.celery_app beat --loglevel=info
```

### Frontend Setup

#### 1. Install Dependencies

```bash
cd frontend
npm install
```

#### 2. Configure Environment

```bash
cp .env.example .env.local
```

Edit `.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

#### 3. Start Frontend

```bash
npm run dev
```

Frontend will be available at http://localhost:3000

## Additional Setup

### MinIO (S3-Compatible Storage)

#### Using Docker

```bash
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  --name minio \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"
```

#### Create Bucket

1. Access MinIO console: http://localhost:9001
2. Login with credentials (minioadmin/minioadmin)
3. Create bucket named `bharatbuild-storage`

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs:
   - http://localhost:3000/auth/callback/google
6. Copy Client ID and Secret to `.env`

### Razorpay Setup

1. Sign up at [Razorpay](https://razorpay.com/)
2. Get API keys from Dashboard
3. Add to `.env`:
```bash
RAZORPAY_KEY_ID=your_key_id
RAZORPAY_KEY_SECRET=your_key_secret
```

## Database Migrations

### Create New Migration

```bash
cd backend
alembic revision --autogenerate -m "description of changes"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

### View Migration History

```bash
alembic history
```

## Testing

### Backend Tests

```bash
cd backend
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_auth.py
```

### Frontend Tests

```bash
cd frontend
npm test

# With coverage
npm test -- --coverage
```

## Development Tools

### API Testing

Use the interactive API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Or use tools like:
- Postman
- Insomnia
- curl

Example curl request:
```bash
# Register user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","role":"student"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

### Database Management

Using pgAdmin or psql:
```bash
psql -U bharatbuild -d bharatbuild_db

# View tables
\dt

# View users
SELECT * FROM users;
```

### Redis Management

Using redis-cli:
```bash
redis-cli

# View all keys
KEYS *

# Get value
GET key_name
```

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>
```

#### Database Connection Error

- Check PostgreSQL is running: `sudo systemctl status postgresql`
- Verify credentials in `.env`
- Check DATABASE_URL format

#### Redis Connection Error

- Check Redis is running: `redis-cli ping`
- Should return: `PONG`

#### Migration Errors

```bash
# Reset migrations (development only)
alembic downgrade base
alembic upgrade head
```

#### Module Not Found

```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or for frontend
npm install
```

### Logs

View application logs:
```bash
# Docker
docker-compose logs -f backend
docker-compose logs -f frontend

# Manual setup
# Backend logs in console
# Check logs/app.log
```

## Next Steps

1. Read [API Documentation](API_DOCUMENTATION.md)
2. Check [Deployment Guide](DEPLOYMENT.md)
3. Review code in `/backend` and `/frontend`
4. Join our Discord for support
5. Star the repository!

## Development Workflow

### Making Changes

1. Create feature branch
```bash
git checkout -b feature/your-feature-name
```

2. Make changes

3. Run tests
```bash
pytest  # Backend
npm test  # Frontend
```

4. Commit changes
```bash
git add .
git commit -m "Description of changes"
```

5. Push and create PR
```bash
git push origin feature/your-feature-name
```

### Code Quality

Run linters:
```bash
# Backend
black .
flake8
mypy app

# Frontend
npm run lint
npm run type-check
```

## Support

Need help?
- GitHub Issues: Report bugs and request features
- Discord: Join our community
- Email: support@bharatbuild.ai
