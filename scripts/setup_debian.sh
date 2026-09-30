#!/usr/bin/env bash
# setup_debian.sh — create venv + install dependencies (Debian 13 / Ubuntu)
# Safe under PEP 668. Runnable from ANY directory — you do not need to cd first.
#
# Usage (pick one):
#   bash /path/to/ideal-chainsaw/scripts/setup_debian.sh
#   bash scripts/setup_debian.sh          # if shell is already in the repo
#   bash scripts/setup_debian.sh --force  # recreate venv
#
# Note: Linux is case-sensitive. Use lowercase: bash  (not BASH), and the
# shell builtin is "cd" (not "CD"). This script does not require you to cd.
#
set -euo pipefail

# Resolve project root from this script's location (works even if invoked via symlink)
SCRIPT_PATH="${BASH_SOURCE[0]}"
if command -v readlink >/dev/null 2>&1; then
  if readlink -f "$SCRIPT_PATH" >/dev/null 2>&1; then
    SCRIPT_PATH="$(readlink -f "$SCRIPT_PATH")"
  fi
fi
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
ROOT="$(dirname "$SCRIPT_DIR")"

# Stay in ROOT for the rest of the script using absolute paths only
VENV_NAME="${VENV_DIR:-ai-env}"
# Allow VENV_DIR to be absolute; otherwise place under project root
if [[ "$VENV_NAME" = /* ]]; then
  VENV_ABS="$VENV_NAME"
else
  VENV_ABS="$ROOT/$VENV_NAME"
fi

PYTHON="${PYTHON:-python3}"
FORCE=0
REQ_FILE="$ROOT/requirements.txt"

for arg in "$@"; do
  case "$arg" in
    --force|-f) FORCE=1 ;;
    -h|--help)
      echo "Usage: bash $SCRIPT_PATH [--force]"
      echo "  Creates venv at: $VENV_ABS"
      echo "  Installs:        $REQ_FILE"
      echo "  No need to change directory first."
      exit 0
      ;;
  esac
done

echo "==> ideal-chainsaw setup (Debian-safe)"
echo "    project : $ROOT"
echo "    python  : $PYTHON"
echo "    venv    : $VENV_ABS"
echo

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON not found."
  echo "  sudo apt update && sudo apt install -y python3"
  exit 1
fi

if [[ ! -f "$REQ_FILE" ]]; then
  echo "ERROR: requirements.txt not found at: $REQ_FILE"
  echo "  Is this the ideal-chainsaw repo?"
  exit 1
fi

install_apt_pkgs() {
  echo "==> Installing system packages: python3-venv python3-pip"
  if command -v sudo >/dev/null 2>&1; then
    sudo apt-get update -qq
    sudo apt-get install -y python3-venv python3-pip
  elif [[ "$(id -u)" -eq 0 ]]; then
    apt-get update -qq
    apt-get install -y python3-venv python3-pip
  else
    echo "ERROR: need sudo for: apt install python3-venv python3-pip"
    exit 1
  fi
}

if ! "$PYTHON" -m venv --help >/dev/null 2>&1; then
  echo "NOTE: python3-venv missing."
  install_apt_pkgs
fi

if [[ "$FORCE" -eq 1 && -d "$VENV_ABS" ]]; then
  echo "==> --force: removing $VENV_ABS"
  rm -rf "$VENV_ABS"
fi

if [[ ! -d "$VENV_ABS" ]]; then
  echo "==> Creating virtual environment"
  if ! "$PYTHON" -m venv "$VENV_ABS"; then
    echo "venv failed; installing python3-venv and retrying…"
    install_apt_pkgs
    "$PYTHON" -m venv "$VENV_ABS"
  fi
else
  echo "==> Reusing venv (pass --force to recreate)"
fi

VENV_PY="$VENV_ABS/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "ERROR: missing $VENV_PY — broken venv."
  echo "  bash $SCRIPT_PATH --force"
  exit 1
fi

if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
  echo "==> Bootstrapping pip (ensurepip)"
  if ! "$VENV_PY" -m ensurepip --upgrade 2>/dev/null; then
    install_apt_pkgs
    rm -rf "$VENV_ABS"
    "$PYTHON" -m venv "$VENV_ABS"
    VENV_PY="$VENV_ABS/bin/python"
  fi
fi

if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
  echo "ERROR: pip unavailable inside venv."
  exit 1
fi

echo "==> Upgrading pip/setuptools/wheel inside venv"
"$VENV_PY" -m pip install --upgrade pip setuptools wheel

echo "==> Installing dependencies from $REQ_FILE"
"$VENV_PY" -m pip install -r "$REQ_FILE"

echo "==> Verifying imports"
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
    print(f"  WARN duckduckgo_search: {e}")
if missing:
    raise SystemExit("Missing: " + ", ".join(missing))
print("  required packages OK")
PY

mkdir -p "$ROOT/data" "$ROOT/.streamlit"
SECRETS="$ROOT/.streamlit/secrets.toml"
if [[ ! -f "$SECRETS" ]]; then
  cat > "$SECRETS" << 'EOF'
# https://console.groq.com/
GROQ_API_KEY = "gsk_your_actual_private_key_here"
EOF
  echo "==> Wrote $SECRETS — add your real API key"
else
  echo "==> Secrets file exists (unchanged): $SECRETS"
fi

RUN_SH="$ROOT/scripts/run.sh"
echo
echo "✅ Setup complete."
echo
echo "1. Edit secrets:  nano $SECRETS"
echo "2. Start app:     bash $RUN_SH"
echo
echo "No directory change required. Do not use system pip or --break-system-packages."
