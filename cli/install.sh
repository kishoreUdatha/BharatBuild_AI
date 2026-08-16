#!/usr/bin/env bash
# BharatBuild CLI — Linux / macOS installer
set -e

echo ""
echo "  BharatBuild CLI Installer"
echo "  ========================="
echo ""

# Python check
if ! command -v python3 &>/dev/null; then
    echo "  ERROR: python3 not found. Install Python 3.10+ first."
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  Python $PY_VER detected"

# Virtualenv (optional but recommended)
VENV_DIR="$HOME/.bharatbuild/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "  Creating virtualenv at $VENV_DIR …"
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# Install deps
echo "  Installing dependencies …"
pip install --quiet --upgrade pip
pip install --quiet -r "$(dirname "$0")/requirements.txt"

# Install the CLI package itself
echo "  Installing bharatbuild CLI …"
pip install --quiet -e "$(dirname "$0")/.."

# Wrapper script so it works without activating venv
INSTALL_BIN="/usr/local/bin/bharatbuild"
VENV_BIN="$VENV_DIR/bin/bharatbuild"

if [ -w "/usr/local/bin" ]; then
    cat > "$INSTALL_BIN" <<EOF
#!/usr/bin/env bash
source "$VENV_DIR/bin/activate"
exec bharatbuild "\$@"
EOF
    chmod +x "$INSTALL_BIN"
    echo "  Installed to $INSTALL_BIN"
else
    echo "  NOTE: /usr/local/bin not writable. Add this to your shell profile:"
    echo ""
    echo "    alias bharatbuild='source $VENV_DIR/bin/activate && bharatbuild'"
    echo ""
fi

echo ""
echo "  Done!  Run:  bharatbuild login"
echo ""
