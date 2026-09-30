#!/usr/bin/env bash
# run.sh — start ideal-chainsaw (works from any directory; no user cd needed)
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
if command -v readlink >/dev/null 2>&1; then
  if readlink -f "$SCRIPT_PATH" >/dev/null 2>&1; then
    SCRIPT_PATH="$(readlink -f "$SCRIPT_PATH")"
  fi
fi
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
ROOT="$(dirname "$SCRIPT_DIR")"

VENV_NAME="${VENV_DIR:-ai-env}"
if [[ "$VENV_NAME" = /* ]]; then
  VENV_ABS="$VENV_NAME"
else
  VENV_ABS="$ROOT/$VENV_NAME"
fi

SETUP="$ROOT/scripts/setup_debian.sh"
APP="$ROOT/app.py"

if [[ ! -x "$VENV_ABS/bin/python" ]]; then
  echo "No venv at $VENV_ABS — running setup…"
  bash "$SETUP"
fi

STREAMLIT="$VENV_ABS/bin/streamlit"
if [[ ! -x "$STREAMLIT" ]]; then
  echo "streamlit missing — reinstalling dependencies…"
  bash "$SETUP"
  STREAMLIT="$VENV_ABS/bin/streamlit"
fi

if [[ ! -f "$APP" ]]; then
  echo "ERROR: app.py not found at $APP"
  exit 1
fi

# Enter project root so data/ and relative paths resolve.
# Use the shell builtin explicitly (lowercase "cd" — not "CD").
if ! builtin cd "$ROOT"; then
  echo "ERROR: cannot enter project directory: $ROOT"
  echo "  Check that the path exists and you have permission."
  exit 1
fi

exec "$STREAMLIT" run "$APP" "$@"
