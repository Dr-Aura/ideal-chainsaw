#!/usr/bin/env bash
# run.sh — start ideal-chainsaw using the project venv (Debian-safe)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_DIR="${VENV_DIR:-ai-env}"

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "No venv found at $VENV_DIR"
  echo "Run first:  bash scripts/setup_debian.sh"
  exit 1
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

exec streamlit run app.py "$@"
