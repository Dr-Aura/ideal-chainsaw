#!/usr/bin/env bash
# run.sh — start ideal-chainsaw with the project venv
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_DIR="${VENV_DIR:-ai-env}"

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "No venv at $VENV_DIR — running setup first…"
  bash "$ROOT/scripts/setup_debian.sh"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if ! command -v streamlit >/dev/null 2>&1; then
  echo "streamlit not found in venv — reinstalling dependencies…"
  bash "$ROOT/scripts/setup_debian.sh"
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
fi

exec streamlit run app.py "$@"
