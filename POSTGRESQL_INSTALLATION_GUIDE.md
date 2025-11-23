# PostgreSQL Installation Guide for Windows

## Step-by-Step Installation

### Option 1: Official PostgreSQL Installer (Recommended)

#### 1. Download PostgreSQL

1. Open your browser and go to: **https://www.postgresql.org/download/windows/**
2. Click on "Download the installer"
3. You'll be redirected to EnterpriseDB
4. Download **PostgreSQL 16.x** for Windows x86-64
5. Download link: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads

#### 2. Run the Installer

1. Double-click the downloaded `.exe` file
2. Click "Next" through the welcome screen
3. **Installation Directory**: Keep default `C:\Program Files\PostgreSQL\16`
4. **Select Components**: Check all (PostgreSQL Server, pgAdmin 4, Stack Builder, Command Line Tools)
5. **Data Directory**: Keep default `C:\Program Files\PostgreSQL\16\data`
6. **Password**: Set a password for the `postgres` superuser
   - **IMPORTANT**: Remember this password! You'll need it later.
   - Example: `postgres123` (for development only)
7. **Port**: Keep default `5432`
8. **Locale**: Keep default (Default locale)
9. Click "Next" and "Finish"

#### 3. Verify Installation

Open Command Prompt and run:

```bash
# Check PostgreSQL version
"C:\Program Files\PostgreSQL\16\bin\psql.exe" --version

# Should show: psql (PostgreSQL) 16.x
```

#### 4. Add PostgreSQL to PATH (Important)

1. Open **Environment Variables**:
   - Press `Win + X` → System → Advanced system settings
   - Click "Environment Variables"
2. Under "System variables", find `Path`, click "Edit"
3. Click "New" and add: `C:\Program Files\PostgreSQL\16\bin`
4. Click "OK" on all dialogs
5. **Close and reopen** Command Prompt/Terminal

Test PATH:
```bash
psql --version
# Should work without full path now
```

---

### Option 2: Using Scoop (Package Manager)

If you have Scoop installed:

```bash
scoop install postgresql

# Start PostgreSQL service
pg_ctl -D "$env:USERPROFILE\scoop\apps\postgresql\current\data" start
```

---

### Option 3: Using Chocolatey (Package Manager)

If you have Chocolatey installed:

```bash
choco install postgresql

# PostgreSQL service should start automatically
```

---

## Post-Installation Setup

### 1. Start PostgreSQL Service

**Method A: Using Services (GUI)**
1. Press `Win + R`, type `services.msc`, press Enter
2. Find "postgresql-x64-16" service
3. Right-click → Start
4. Right-click → Properties → Startup type: Automatic

**Method B: Using Command Line**
```bash
# Start service
net start postgresql-x64-16

# Stop service
net stop postgresql-x64-16
```

### 2. Create Database for BharatBuild AI

Open Command Prompt or PowerShell:

```bash
# Connect to PostgreSQL as superuser
psql -U postgres

# You'll be prompted for the password you set during installation
```

In the PostgreSQL shell:

```sql
-- Create database
CREATE DATABASE bharatbuild;

-- Create user for the application (optional, but recommended)
CREATE USER bharatbuild_user WITH PASSWORD 'bharatbuild_pass123';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE bharatbuild TO bharatbuild_user;

-- Exit
\q
```

### 3. Test Connection

```bash
# Test connection to new database
psql -U postgres -d bharatbuild

# Should connect successfully
# Exit with: \q
```

---

## Update BharatBuild AI Configuration

### 1. Update backend/.env file

Open `backend/.env` and update the DATABASE_URL:

**If using postgres superuser**:
```bash
DATABASE_URL=postgresql+asyncpg://postgres:your_password_here@localhost:5432/bharatbuild
```

**If using bharatbuild_user** (recommended):
```bash
DATABASE_URL=postgresql+asyncpg://bharatbuild_user:bharatbuild_pass123@localhost:5432/bharatbuild
```

Replace `your_password_here` with the actual password you set during installation.

### 2. Install Python PostgreSQL Driver

```bash
cd backend
./venv/Scripts/activate

# Install psycopg2-binary (requires PostgreSQL to be installed first)
pip install psycopg2-binary==2.9.9

# Install async PostgreSQL driver
pip install asyncpg==0.29.0

# Install SQLAlchemy
pip install sqlalchemy==2.0.25 alembic==1.13.1
```

---

## Troubleshooting

### Issue 1: "psql: command not found"

**Solution**: PostgreSQL bin folder not in PATH. Add manually:
```bash
# Add to PATH temporarily (current session only)
set PATH=%PATH%;C:\Program Files\PostgreSQL\16\bin
```

Or follow "Add PostgreSQL to PATH" section above for permanent fix.

### Issue 2: "password authentication failed"

**Solution**: Wrong password or user doesn't exist.
- Verify password is correct
- Reset password:
```bash
psql -U postgres
ALTER USER postgres PASSWORD 'newpassword';
```

### Issue 3: "could not connect to server"

**Solution**: PostgreSQL service not running.
```bash
# Start service
net start postgresql-x64-16

# Or check Services (services.msc)
```

### Issue 4: psycopg2-binary installation fails

**Solution**: Requires PostgreSQL to be installed first and added to PATH.
- Ensure PostgreSQL is installed
- Ensure `C:\Program Files\PostgreSQL\16\bin` is in PATH
- Restart terminal after adding to PATH
- Try installation again

### Issue 5: Port 5432 already in use

**Solution**: Another PostgreSQL instance or service using the port.
```bash
# Find process using port 5432
netstat -ano | findstr :5432

# Stop the service or change PostgreSQL port in postgresql.conf
```

---

## Quick Reference

### Common PostgreSQL Commands

```sql
-- List databases
\l

-- Connect to database
\c bharatbuild

-- List tables
\dt

-- Describe table
\d table_name

-- List users
\du

-- Exit
\q
```

### Common Windows Commands

```bash
# Check if PostgreSQL is running
sc query postgresql-x64-16

# Start PostgreSQL service
net start postgresql-x64-16

# Stop PostgreSQL service
net stop postgresql-x64-16

# Check PostgreSQL version
psql --version

# Connect to PostgreSQL
psql -U postgres
```

---

## Using pgAdmin 4 (GUI Tool)

pgAdmin 4 is installed automatically with PostgreSQL.

1. Search for "pgAdmin 4" in Start Menu
2. Open pgAdmin 4
3. Set master password (first time only)
4. Expand "Servers" → "PostgreSQL 16"
5. Enter your postgres password
6. Right-click "Databases" → Create → Database → Name: `bharatbuild`

---

## Next Steps After Installation

1. ✅ PostgreSQL installed and running
2. ✅ Database `bharatbuild` created
3. ✅ Connection tested
4. ⏭️ Install Redis for caching (see REDIS_INSTALLATION_GUIDE.md)
5. ⏭️ Install remaining Python packages
6. ⏭️ Run Alembic migrations
7. ⏭️ Start backend server

---

## Alternative: Use Docker (Easier Setup)

If you have Docker Desktop installed, you can skip manual installation:

```bash
# Run PostgreSQL in Docker
docker run -d \
  --name bharatbuild-postgres \
  -e POSTGRES_DB=bharatbuild \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres123 \
  -p 5432:5432 \
  postgres:16

# Database URL for Docker:
DATABASE_URL=postgresql+asyncpg://postgres:postgres123@localhost:5432/bharatbuild
```

**Advantages**:
- No installation needed
- Easy to start/stop
- Easy to reset (just delete container)
- No PATH configuration needed

**Commands**:
```bash
# Start container
docker start bharatbuild-postgres

# Stop container
docker stop bharatbuild-postgres

# Remove container
docker rm bharatbuild-postgres

# View logs
docker logs bharatbuild-postgres
```

---

## Summary

**Installation Time**: 10-15 minutes
**Disk Space**: ~150 MB
**Default Port**: 5432
**Default User**: postgres
**GUI Tool**: pgAdmin 4

Once PostgreSQL is installed and configured, you'll be able to:
- Run the BharatBuild AI backend
- Store user data and projects in the database
- Run database migrations with Alembic
- Test the complete multi-agent system

Need help? Check the troubleshooting section or ask for assistance!
