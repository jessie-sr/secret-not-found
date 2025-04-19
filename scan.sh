#!/usr/bin/env bash
# scan.sh  ─ run from the repo root to install / invoke Secret‑Not‑Found

set -euo pipefail                                    # safer Bash defaults

# --- paths -------------------------------------------------------------------
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "❌  Not inside a Git repository." >&2
  exit 1
}

HOOK_PATH="$REPO_ROOT/.git/hooks/pre-push"           # where Git looks
INSTALL_PY="$REPO_ROOT/secret-not-found/install.py"

# --- 1. install the hook if needed -------------------------------------------
if [[ ! -x "$HOOK_PATH" ]]; then
  echo "🔧  Installing pre‑push hook..."
  python3 "$INSTALL_PY"
  echo "✅  Hook installed at .git/hooks/pre-push"
fi

# --- 2. invoke the scanner via the hook --------------------------------------
echo "🔍  Running Secret‑Not‑Found scanner..."
"$HOOK_PATH"   # identical to what Git does during `git push`
STATUS=$?

if [[ $STATUS -eq 0 ]]; then
  echo "✅  No secrets detected"
else
  echo "🚨  Secrets found (hook exit $STATUS)" >&2
fi

exit $STATUS