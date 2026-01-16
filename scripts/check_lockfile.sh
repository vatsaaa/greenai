#!/usr/bin/env bash
set -euo pipefail

# Simple local lockfile drift check. Requires pip-compile (pip-tools) in PATH.
if [[ ! -f requirements.in ]]; then
  echo "No requirements.in found; skipping lockfile check."
  exit 0
fi

TMP_OUT=$(mktemp)
trap 'rm -f "$TMP_OUT"' EXIT

echo "Generating temporary lockfile via pip-compile..."
pip-compile --quiet --output-file "$TMP_OUT" requirements.in

if cmp -s "$TMP_OUT" requirements.lock.txt; then
  echo "Lockfile is up to date."
  exit 0
else
  echo "Lockfile differs. Run 'pip-compile' and update requirements.lock.txt if intentional."
  echo "Diff:" 
  diff -u requirements.lock.txt "$TMP_OUT" || true
  exit 2
fi
#!/usr/bin/env bash
set -euo pipefail

# check_lockfile.sh
# Usage: ./scripts/check_lockfile.sh
#
# Generates a compiled lockfile from `requirements.in` (if present) and
# compares it to `requirements.lock.txt`. Exits with code 0 when up-to-date,
# or non-zero when drift is detected.

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WORKDIR"

if [ ! -f requirements.in ]; then
  echo "No requirements.in found; skipping lockfile check."
  exit 0
fi

if ! command -v pip-compile >/dev/null 2>&1; then
  echo "pip-compile not found. Installing pip-tools into a temporary venv..."
  python -m pip install --user pip-tools
fi

TMP_COMP=compiled.lock
echo "Compiling requirements.in -> $TMP_COMP"
pip-compile requirements.in --output-file=$TMP_COMP --generate-hashes

if [ ! -f requirements.lock.txt ]; then
  echo "requirements.lock.txt not found; please create it by running pip-compile requirements.in --output-file=requirements.lock.txt"
  echo "Generated compiled lockfile is at $TMP_COMP"
  exit 2
fi

if cmp -s "$TMP_COMP" requirements.lock.txt; then
  echo "Lockfile is up-to-date"
  rm -f "$TMP_COMP"
  exit 0
else
  echo "Lockfile is out-of-date. Diff:" >&2
  diff -u requirements.lock.txt "$TMP_COMP" || true
  echo "Run: pip-compile requirements.in --output-file=requirements.lock.txt --generate-hashes" >&2
  rm -f "$TMP_COMP"
  exit 3
fi
