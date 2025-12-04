@echo off
REM BharatBuild AI - Development Startup Script (Windows)

echo =========================================
echo   BharatBuild AI - Development Mode
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
    echo ! No .env file found. Creating from .env.example...
    copy .env.example .env
    echo √ Created .env file
    echo.
    echo ! IMPORTANT: Please edit .env and add your ANTHROPIC_API_KEY
    echo   Press any key to continue after updating .env, or Ctrl+C to exit...
    pause >nul
)

REM Stop any existing containers
echo Cleaning up existing containers...
docker-compose -f docker-compose.dev.yml down

echo.
echo Starting development environment...
echo.

REM Start services
docker-compose -f docker-compose.dev.yml up --build

echo.
echo =========================================
echo   Development environment stopped
echo =========================================
pause
