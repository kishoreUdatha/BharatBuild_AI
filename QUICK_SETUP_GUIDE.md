# BharatBuild AI - Quick Setup Guide

## 🚀 Quick Start (15 Minutes)

### Prerequisites
- Windows 10/11
- Python 3.13 (already installed ✅)
- Node.js (already installed ✅)

---

## Step 1: Install PostgreSQL (5 minutes)

### Option A: Download Installer (Recommended)

1. **Download**: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
   - Select: PostgreSQL 16.x for Windows x86-64

2. **Install**:
   - Run the downloaded `.exe` file
   - Password: `postgres123` (or choose your own - REMEMBER IT!)
   - Port: `5432` (keep default)
   - Click through with defaults

3. **Add to PATH**:
   - Win + X → System → Advanced → Environment Variables
   - Edit `Path` → Add: `C:\Program Files\PostgreSQL\16\bin`
   - Click OK, close terminal, reopen

4. **Create Database**:
```bash
psql -U postgres
# Enter password when prompted

# In psql shell:
CREATE DATABASE bharatbuild;
\q
```

### Option B: Using Docker (Fastest - 2 minutes)

```bash
docker run -d --name bharatbuild-postgres -e POSTGRES_DB=bharatbuild -e POSTGRES_PASSWORD=postgres123 -p 5432:5432 postgres:16
```

---

## Step 2: Install Redis (3 minutes)

### Option A: Using Docker (Easiest)

```bash
docker run -d --name bharatbuild-redis -p 6379:6379 redis:7-alpine
```

### Option B: Using WSL2

```bash
# Install WSL2 first (if not already)
wsl --install

# In WSL2 terminal:
sudo apt update
sudo apt install redis-server
redis-server --daemonize yes
```

---

## Step 3: Install Python Dependencies (5 minutes)

```bash
cd backend

# Activate virtual environment
./venv/Scripts/activate

# Install database packages
pip install sqlalchemy==2.0.25 alembic==1.13.1 asyncpg==0.29.0 psycopg2-binary==2.9.9

# Install Redis and Celery
pip install redis==5.0.1 celery==5.3.6

# Install document generation (optional for now)
pip install python-docx==1.1.0 python-pptx==0.6.23

# Try reportlab and matplotlib (may fail, that's OK for now)
pip install reportlab PyPDF2 || echo "Skipping reportlab for now"
```

---

## Step 4: Update Configuration (1 minute)

Edit `backend/.env`:

```bash
# Update these lines:
DATABASE_URL=postgresql+asyncpg://postgres:postgres123@localhost:5432/bharatbuild
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Add your Claude API key (REQUIRED):
ANTHROPIC_API_KEY=sk-ant-your-actual-api-key-here
```

Get Claude API key from: https://console.anthropic.com/

---

## Step 5: Initialize Database (1 minute)

```bash
cd backend

# Run Alembic migrations
./venv/Scripts/alembic upgrade head
```

---

## Step 6: Start Backend Server

```bash
cd backend
./venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Starting BharatBuild AI Platform...
INFO:     Environment: development
INFO:     Application startup complete.
```

---

## Step 7: Test the System

### Test Backend Health

Open new terminal:
```bash
curl http://localhost:8000/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "app_name": "BharatBuild AI",
  "version": "1.0.0",
  "environment": "development"
}
```

### Test Frontend

Open browser: **http://localhost:3000** (or 3001, 3010)

You should see the BharatBuild AI homepage!

### Test Multi-Agent System

```bash
curl -X POST http://localhost:8000/api/v1/automation/multi-agent/execute/stream \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "test-hello-world",
    "user_prompt": "Create a simple hello world React app",
    "mode": "code_only",
    "include_tests": false
  }'
```

---

## Troubleshooting

### "psql: command not found"
- PostgreSQL not in PATH
- Solution: Add `C:\Program Files\PostgreSQL\16\bin` to PATH
- Restart terminal

### "connection refused" (PostgreSQL)
- PostgreSQL service not running
- Solution: `net start postgresql-x64-16`

### "connection refused" (Redis)
- Redis not running
- Solution (Docker): `docker start bharatbuild-redis`
- Solution (WSL2): `wsl redis-server --daemonize yes`

### Backend fails with "ModuleNotFoundError"
- Missing Python packages
- Solution: Install missing package with `pip install <package-name>`

### "Invalid API key" (Claude)
- Wrong or missing ANTHROPIC_API_KEY
- Solution: Get real API key from https://console.anthropic.com/
- Update `backend/.env`

---

## System Overview

Once everything is running, you'll have:

1. **Frontend**: http://localhost:3000
   - Bolt.new-inspired UI
   - Chat interface
   - Project builder

2. **Backend**: http://localhost:8000
   - REST API
   - Multi-agent orchestrator
   - Document generation

3. **API Docs**: http://localhost:8000/docs
   - Interactive Swagger UI
   - Test API endpoints

4. **PostgreSQL**: localhost:5432
   - Database: `bharatbuild`
   - User data, projects

5. **Redis**: localhost:6379
   - Caching
   - Celery task queue

---

## Next Steps

1. ✅ Access frontend at http://localhost:3000
2. ✅ Click "Start Building" button
3. ✅ Try generating a project: "Build a todo app with authentication"
4. ✅ Watch multi-agent system work (Planner → Architect → Coder → Tester → Docs)
5. ✅ Check generated files in `user_projects/` folder

---

## Full Feature Testing

Try these prompts in the Bolt interface:

1. **Simple Project**:
   ```
   Create a calculator app with React
   ```

2. **Full-Stack App**:
   ```
   Build a blog platform with user authentication,
   post creation, comments, and admin dashboard
   ```

3. **Academic Project** (with documentation):
   ```
   Create a library management system with:
   - Book borrowing/returning
   - User registration
   - Generate complete SRS, SDS, testing plan,
     project report (60-80 pages), and PowerPoint presentation
   ```

---

## Development Tips

1. **View Logs**: Backend terminal shows real-time logs
2. **API Testing**: Use http://localhost:8000/docs for interactive API testing
3. **Database**: Use pgAdmin 4 or `psql` to view database
4. **Redis**: Use `redis-cli` to monitor cache
5. **Hot Reload**: Both frontend and backend auto-reload on code changes

---

## Need Help?

- PostgreSQL issues: See `POSTGRESQL_INSTALLATION_GUIDE.md`
- Multi-agent details: See `MULTI_AGENT_INTEGRATION.md`
- PDF/PPT generation: See `PDF_DOCUMENTS_GUIDE.md`
- S3 storage: See `S3_STORAGE_GUIDE.md`

Happy Building! 🚀
