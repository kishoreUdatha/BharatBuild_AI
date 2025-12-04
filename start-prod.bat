@echo off
REM BharatBuild AI - Production Startup Script (Windows)

echo =========================================
echo   BharatBuild AI - Production Mode
echo =========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo X Error: Docker is not running. Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo √ Docker is running
echo.

REM Check if .env file exists
if not exist .env (
    echo X Error: No .env file found. Please create one from .env.example
    pause
    exit /b 1
)

echo √ Environment configured
echo.

REM Stop any existing containers
echo Cleaning up existing containers...
docker-compose down

echo.
echo Starting production environment...
echo.

REM Start services
docker-compose up -d --build

echo.
echo =========================================
echo   √ Production environment started!
echo =========================================
echo.
echo Services:
echo   - Frontend:  http://localhost:3000
echo   - Backend:   http://localhost:8000
echo   - API Docs:  http://localhost:8000/docs
echo.
echo To view logs: docker-compose logs -f
echo To stop:      docker-compose down
echo.
pause
