@echo off
setlocal enabledelayedexpansion

echo.
echo  ============================================
echo   BharatBuild CLI - Windows Installer
echo  ============================================
echo.

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed.
    echo         Install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('node --version') do set NODE_VER=%%v
echo [OK] Node.js %NODE_VER% found

REM Check npm
npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found. Reinstall Node.js from https://nodejs.org
    pause
    exit /b 1
)

echo.
echo [1/3] Installing dependencies...
call npm install
if errorlevel 1 (
    echo [ERROR] npm install failed. Check your internet connection and try again.
    pause
    exit /b 1
)
echo [OK] Dependencies installed

echo.
echo [2/3] Building TypeScript...
call npm run build
if errorlevel 1 (
    echo [ERROR] TypeScript build failed. See errors above.
    pause
    exit /b 1
)
echo [OK] Build complete

echo.
echo [3/3] Installing globally...
call npm link 2>nul
if errorlevel 1 (
    echo [WARN] npm link failed, trying npm install -g...
    call npm install -g .
    if errorlevel 1 (
        echo [ERROR] Global install failed.
        echo         Try running this script as Administrator.
        pause
        exit /b 1
    )
)
echo [OK] Installed globally

echo.
echo  ============================================
echo   BharatBuild CLI installed successfully!
echo.
echo   Commands:
echo     bharatbuild              Start interactive REPL
echo     bharatbuild login        Login to your account
echo     bharatbuild student      Student mode
echo     bharatbuild developer    Developer mode
echo     bharatbuild founder      Founder mode
echo     bharatbuild --help       Show all commands
echo  ============================================
echo.

pause
