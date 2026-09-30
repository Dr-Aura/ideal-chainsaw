#!/usr/bin/env bash
# setup_debian.sh — ideal-chainsaw on Debian 13 (Trixie) / Ubuntu
# Avoids PEP 668 "externally managed environment" errors by using a venv only.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_DIR="${VENV_DIR:-ai-env}"
PYTHON="${PYTHON:-python3}"

echo "==> ideal-chainsaw Debian/Ubuntu setup"
echo "    project: $ROOT"
echo "    venv:    $VENV_DIR"
echo

# ---------------------------------------------------------------------------
# System packages (apt) — only what is required to create a venv
# ---------------------------------------------------------------------------
need_apt=0
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON not found. Install with: sudo apt install python3"
  exit 1
fi

if ! "$PYTHON" -m venv --help >/dev/null 2>&1; then
  echo "NOTE: python3-venv is missing (required on Debian/Ubuntu)."
  need_apt=1
fi

if ! command -v pip3 >/dev/null 2>&1 && ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
  # ensurepip often comes with python3-venv
  need_apt=1
fi

if [[ "$need_apt" -eq 1 ]]; then
  echo "Installing system packages (requires sudo): python3-venv python3-pip"
  if command -v sudo >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3-venv python3-pip
  else
    echo "ERROR: sudo not available. Run as root or install manually:"
    echo "  apt-get install -y python3-venv python3-pip"
    exit 1
  fi
fi

# ---------------------------------------------------------------------------
# Virtual environment (NEVER install into system Python)
# ---------------------------------------------------------------------------
if [[ ! -d "$VENV_DIR" ]]; then
  echo "==> Creating virtual environment: $VENV_DIR"
  "$PYTHON" -m venv "$VENV_DIR"
else
  echo "==> Reusing existing venv: $VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> Upgrading pip/setuptools/wheel inside venv"
python -m pip install --upgrade pip setuptools wheel

echo "==> Installing requirements.txt"
python -m pip install -r requirements.txt

# ---------------------------------------------------------------------------
# Secrets template (do not overwrite existing key)
# ---------------------------------------------------------------------------
mkdir -p .streamlit
if [[ ! -f .streamlit/secrets.toml ]]; then
  cat > .streamlit/secrets.toml << 'EOF'
# Get a key at https://console.groq.com/
GROQ_API_KEY = "gsk_your_actual_private_key_here"
EOF
  echo "==> Created .streamlit/secrets.toml — edit and paste your Groq API key"
else
  echo "==> .streamlit/secrets.toml already exists (left unchanged)"
fi

mkdir -p data

echo
echo "✅ Setup complete."
echo
echo "Activate and run:"
echo "  source $VENV_DIR/bin/activate"
echo "  streamlit run app.py"
echo
echo "Or one-liner:"
echo "  source $VENV_DIR/bin/activate && streamlit run app.py"
echo
echo "Do NOT use: pip install --break-system-packages"
echo "Do NOT use: sudo pip install ..."
