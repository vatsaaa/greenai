#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 [--force]

Shows a preview of redundant/untracked/ignored files that would be removed.
By default it only previews; pass --force to actually delete (uses `git clean`).

Options:
  --force   Perform destructive removal (equivalent to `git clean -fdX`)
  --help    Show this message
EOF
}

if [[ "${1-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "${1-}" == "--force" ]]; then
  echo "WARNING: Running with --force. This will permanently delete untracked and ignored files."
  read -r -p "Type YES to continue: " ans
  if [[ "$ans" != "YES" ]]; then
    echo "Aborting. To actually delete, re-run with --force and type YES."
    exit 1
  fi
  echo "Performing destructive cleanup: removing untracked and ignored files..."
  git clean -fdX
  git clean -fd
  echo "Cleanup complete."
  exit 0
fi

echo "Preview: showing ignored files that would be removed (git clean -ndX):"
git clean -ndX || true
echo
echo "Preview: showing untracked files that would be removed (git clean -nd):"
git clean -nd || true
echo
echo "To actually delete these files, re-run with --force (and confirm)."
#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 [--force]

Shows a preview of redundant/untracked/ignored files that would be removed.
By default it only previews; pass --force to actually delete (uses `git clean`).

Options:
  --force   Perform destructive removal (equivalent to `git clean -fdX`)
  --help    Show this message
EOF
}

if [[ "${1-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "${1-}" == "--force" ]]; then
  echo "WARNING: Running with --force. This will permanently delete untracked and ignored files."
  read -r -p "Type YES to continue: " ans
  if [[ "$ans" != "YES" ]]; then
    echo "Aborting. To actually delete, re-run with --force and type YES."
    exit 1
  fi
  echo "Performing destructive cleanup: removing untracked and ignored files..."
  # Remove ignored files (X) and untracked files (-f)
  git clean -fdX
  git clean -fd
  echo "Cleanup complete."
  exit 0
fi

echo "Preview: showing ignored files that would be removed (git clean -ndX):"
git clean -ndX || true
echo
echo "Preview: showing untracked files that would be removed (git clean -nd):"
git clean -nd || true
echo
echo "To actually delete these files, re-run with --force (and confirm)."
