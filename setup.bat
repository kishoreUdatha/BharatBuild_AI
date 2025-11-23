@echo off
REM BharatBuild AI Setup Script for Windows
REM This script sets up the development environment

echo =========================================
echo BharatBuild AI - Setup Script
echo =========================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not installed
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker Compose is not installed
    pause
    exit /b 1
)

echo [OK] Docker and Docker Compose are installed
echo.

REM Check if .env exists
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
    echo [OK] .env file created
    echo.
    echo WARNING: Edit .env file and add your API keys:
    echo   - ANTHROPIC_API_KEY (required^)
    echo   - GOOGLE_CLIENT_ID (optional^)
    echo   - RAZORPAY_KEY_ID (optional^)
    echo.
    pause
) else (
    echo [OK] .env file already exists
)

echo.
echo Starting services with Docker Compose...
echo.

REM Pull images
echo Pulling Docker images...
docker-compose pull

REM Build and start services
echo Building and starting services...
docker-compose up -d

REM Wait for services
echo.
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM Run database migrations
echo.
echo Running database migrations...
docker-compose exec -T backend alembic upgrade head
echo [OK] Database migrations completed

echo.
echo =========================================
echo Setup Complete!
echo =========================================
echo.
echo Your BharatBuild AI platform is now running:
echo.
echo   Frontend:    http://localhost:3000
echo   Backend API: http://localhost:8000
echo   API Docs:    http://localhost:8000/docs
echo   MinIO:       http://localhost:9001
echo.
echo To view logs:
echo   docker-compose logs -f
echo.
echo To stop services:
echo   docker-compose down
echo.
echo Next steps:
echo   1. Open http://localhost:3000 in your browser
echo   2. Register a new account
echo   3. Create your first project
echo   4. Check the documentation in /docs
echo.
echo Happy building!
echo.
pause
