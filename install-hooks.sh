#!/usr/bin/env bash
# install-hooks.sh — enable the versioned .githooks/ directory for this clone.
#
# Run this once after cloning the repo:
#     ./install-hooks.sh
#
# It is idempotent: safe to re-run.
set -e

cd "$(git rev-parse --show-toplevel)"

if [ ! -d .githooks ]; then
  echo "❌ .githooks/ not found in $(pwd)"
  exit 1
fi

# Make sure all hook files are executable
chmod +x .githooks/*

# Set the hooks path
git config core.hooksPath .githooks

echo "✅ Git hooks enabled (.githooks/)"
echo "   Verify with: git config --get core.hooksPath"
echo "   (should print: .githooks)"
echo
echo "Bypass with: git commit --no-verify"
