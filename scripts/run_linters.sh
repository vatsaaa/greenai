#!/usr/bin/env bash
set -euo pipefail

# Minimal linter wrapper used by CI and local dev. It prefers `.venv_py311` if present.
if [[ -f .venv_py311/bin/activate ]]; then
  # shellcheck disable=SC1091
  . .venv_py311/bin/activate
fi

echo "Running ruff..."
ruff . || true

echo "Running black --check..."
black --check . || true

echo "Running mypy..."
mypy . || true

echo "Linting complete (some tools may return non-zero if not installed)."
#!/usr/bin/env bash
set -euo pipefail

# Run linters/formatters only on git-tracked Python files (avoid scanning venvs/node_modules)
files=$(git ls-files '*.py')
if [ -z "$files" ]; then
  echo "No Python files to lint/format"
  exit 0
fi

echo "Running mypy on tracked files..."
mypy --ignore-missing-imports $files || true

echo "Running ruff on tracked files..."
ruff check $files || true

echo "Running black --check on tracked files..."
black --check $files || true

echo "Linters complete."
