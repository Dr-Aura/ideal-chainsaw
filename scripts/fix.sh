#!/usr/bin/env bash
# fix.sh — repair a broken ideal-chainsaw local install (Debian 13 safe)
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
if command -v readlink >/dev/null 2>&1; then
  if readlink -f "$SCRIPT_PATH" >/dev/null 2>&1; then
    SCRIPT_PATH="$(readlink -f "$SCRIPT_PATH")"
  fi
fi
ROOT="$(dirname "$(dirname "$SCRIPT_PATH")")"

echo "==> Repairing ideal-chainsaw at: $ROOT"

# Remove mistaken key-as-filename files
if [[ -d "$ROOT/.streamlit" ]]; then
  shopt -s nullglob
  bad=("$ROOT"/.streamlit/gsk_*)
  if ((${#bad[@]})); then
    echo "==> Removing invalid secret filenames:"
    printf '    %s\n' "${bad[@]}"
    rm -f "${bad[@]}"
  fi
  shopt -u nullglob
fi

# Recreate venv + reinstall deps
bash "$ROOT/scripts/setup_debian.sh" --force

SECRETS="$ROOT/.streamlit/secrets.toml"
if [[ -f "$SECRETS" ]]; then
  if grep -qiE 'your_actual_private_key|your_real_key|gsk_\.\.\.|changeme|placeholder' "$SECRETS" 2>/dev/null; then
    echo
    echo "⚠️  $SECRETS still has a placeholder key."
    echo "   Edit it and paste your real key from https://console.groq.com/"
    echo "   nano $SECRETS"
  else
    echo "==> secrets.toml present"
  fi
else
  echo
  echo "⚠️  No secrets.toml — create it:"
  echo "   nano $SECRETS"
  echo '   GROQ_API_KEY = "gsk_your_real_key"'
fi

echo
echo "✅ Repair steps done. Start with:"
echo "   bash $ROOT/scripts/run.sh"
