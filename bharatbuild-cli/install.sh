#!/usr/bin/env bash
set -e

echo ""
echo " ============================================"
echo "  BharatBuild CLI - Linux/Mac Installer"
echo " ============================================"
echo ""

# Check Node.js
if ! command -v node &>/dev/null; then
    echo "[ERROR] Node.js is not installed."
    echo "        Install Node.js 18+ from https://nodejs.org"
    exit 1
fi

NODE_VER=$(node --version)
NODE_MAJOR=$(echo "$NODE_VER" | cut -d'.' -f1 | tr -d 'v')
if [ "$NODE_MAJOR" -lt 18 ]; then
    echo "[ERROR] Node.js 18+ required. Current: $NODE_VER"
    exit 1
fi
echo "[OK] Node.js $NODE_VER found"

# Check npm
if ! command -v npm &>/dev/null; then
    echo "[ERROR] npm not found. Reinstall Node.js."
    exit 1
fi

echo ""
echo "[1/3] Installing dependencies..."
npm install
echo "[OK] Dependencies installed"

echo ""
echo "[2/3] Building TypeScript..."
npm run build
echo "[OK] Build complete"

echo ""
echo "[3/3] Installing globally..."
if npm link 2>/dev/null; then
    echo "[OK] Installed via npm link"
else
    echo "[WARN] npm link failed, trying with sudo..."
    sudo npm link
    echo "[OK] Installed via sudo npm link"
fi

echo ""
echo " ==========================================="
echo "  BharatBuild CLI installed successfully!"
echo ""
echo "  Commands:"
echo "    bharatbuild              Start interactive REPL"
echo "    bharatbuild login        Login to your account"
echo "    bharatbuild student      Student mode"
echo "    bharatbuild developer    Developer mode"
echo "    bharatbuild founder      Founder mode"
echo "    bharatbuild --help       Show all commands"
echo " ==========================================="
echo ""
