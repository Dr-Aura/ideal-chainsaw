#!/usr/bin/env bash
# setup_debian.sh — create venv + install all Python dependencies (Debian 13 / Ubuntu)
# Avoids PEP 668 by never installing into system Python.
#
# Usage:
#   bash scripts/setup_debian.sh
#   bash scripts/setup_debian.sh --force    # delete and recreate venv
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_DIR="${VENV_DIR:-ai-env}"
PYTHON="${PYTHON:-python3}"
FORCE=0

for arg in "$@"; do
  case "$arg" in
    --force|-f) FORCE=1 ;;
    -h|--help)
      echo "Usage: bash scripts/setup_debian.sh [--force]"
      echo "  Creates $VENV_DIR, upgrades pip, installs requirements.txt"
      exit 0
      ;;
  esac
done

echo "==> ideal-chainsaw setup"
echo "    project : $ROOT"
echo "    python  : $PYTHON ($("$PYTHON" --version 2>/dev/null || echo missing))"
echo "    venv    : $VENV_DIR"
echo

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON not found."
  echo "  sudo apt update && sudo apt install -y python3"
  exit 1
fi

if [[ ! -f requirements.txt ]]; then
  echo "ERROR: requirements.txt not found in $ROOT"
  exit 1
fi

# ---------------------------------------------------------------------------
# System packages needed to *create* a venv (not the app deps)
# ---------------------------------------------------------------------------
install_apt_pkgs() {
  echo "==> Installing system packages: python3-venv python3-pip"
  if command -v sudo >/dev/null 2>&1; then
    sudo apt-get update -qq
    sudo apt-get install -y python3-venv python3-pip
  elif [[ "$(id -u)" -eq 0 ]]; then
    apt-get update -qq
    apt-get install -y python3-venv python3-pip
  else
    echo "ERROR: need sudo to install python3-venv python3-pip"
    exit 1
  fi
}

if ! "$PYTHON" -m venv --help >/dev/null 2>&1; then
  echo "NOTE: python3-venv missing — required on Debian/Ubuntu."
  install_apt_pkgs
fi

# ---------------------------------------------------------------------------
# Create / recreate virtual environment
# ---------------------------------------------------------------------------
if [[ "$FORCE" -eq 1 && -d "$VENV_DIR" ]]; then
  echo "==> --force: removing existing $VENV_DIR"
  rm -rf "$VENV_DIR"
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "==> Creating virtual environment: $VENV_DIR"
  if ! "$PYTHON" -m venv "$VENV_DIR"; then
    echo "venv creation failed; installing python3-venv and retrying…"
    install_apt_pkgs
    "$PYTHON" -m venv "$VENV_DIR"
  fi
else
  echo "==> Reusing existing venv: $VENV_DIR (use --force to recreate)"
fi

if [[ ! -f "$VENV_DIR/bin/python" ]]; then
  echo "ERROR: $VENV_DIR/bin/python missing — venv is broken."
  echo "  bash scripts/setup_debian.sh --force"
  exit 1
fi

VENV_PY="$VENV_DIR/bin/python"

# ---------------------------------------------------------------------------
# Ensure pip exists inside the venv (some Debian images ship without ensurepip)
# ---------------------------------------------------------------------------
if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
  echo "==> Bootstrapping pip inside venv (ensurepip)"
  if ! "$VENV_PY" -m ensurepip --upgrade 2>/dev/null; then
    echo "ensurepip failed — installing python3-pip via apt and recreating venv"
    install_apt_pkgs
    rm -rf "$VENV_DIR"
    "$PYTHON" -m venv "$VENV_DIR"
    VENV_PY="$VENV_DIR/bin/python"
  fi
fi

if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
  echo "ERROR: pip still unavailable inside venv."
  exit 1
fi

echo "==> Upgrading pip, setuptools, wheel (inside venv only)"
"$VENV_PY" -m pip install --upgrade pip setuptools wheel

echo "==> Installing project dependencies from requirements.txt"
"$VENV_PY" -m pip install -r requirements.txt

# ---------------------------------------------------------------------------
# Verify critical imports
# ---------------------------------------------------------------------------
echo "==> Verifying installs"
"$VENV_PY" - <<'PY'
import importlib
mods = ["streamlit", "groq", "numpy", "sklearn", "plotly"]
missing = []
for m in mods:
    try:
        importlib.import_module(m)
        print(f"  ok  {m}")
    except Exception as e:
        print(f"  FAIL {m}: {e}")
        missing.append(m)
try:
    importlib.import_module("duckduckgo_search")
    print("  ok  duckduckgo_search")
except Exception as e:
    print(f"  WARN duckduckgo_search: {e} (web search disabled until fixed)")
if missing:
    raise SystemExit("Missing required packages: " + ", ".join(missing))
print("  all required packages import OK")
PY

# ---------------------------------------------------------------------------
# App dirs + secrets template
# ---------------------------------------------------------------------------
mkdir -p data .streamlit

if [[ ! -f .streamlit/secrets.toml ]]; then
  cat > .streamlit/secrets.toml << 'EOF'
# Get a key at https://console.groq.com/
GROQ_API_KEY = "gsk_your_actual_private_key_here"
EOF
  echo "==> Created .streamlit/secrets.toml — put your real Groq API key there"
else
  echo "==> .streamlit/secrets.toml already exists (unchanged)"
fi

echo
echo "✅ Venv ready and dependencies installed."
echo
echo "Next:"
echo "  1. Edit .streamlit/secrets.toml with your GROQ_API_KEY"
echo "  2. Run the app:"
echo "       bash scripts/run.sh"
echo "     or:"
echo "       source $VENV_DIR/bin/activate"
echo "       streamlit run app.py"
echo
echo "Never: sudo pip install …  or  pip install --break-system-packages"
