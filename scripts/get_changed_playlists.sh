#!/bin/bash
# Get changed playlist files compared to main branch
# Usage: ./scripts/get_changed_playlists.sh [base_branch]

set -e

BASE_BRANCH="${1:-main}"

echo "Comparing against branch: $BASE_BRANCH" >&2

# Get changed .yaml files in mixdiscs/ directory (Added or Modified only)
CHANGED_FILES=$(git diff --name-only --diff-filter=AM "$BASE_BRANCH"...HEAD -- 'mixdiscs/*/*.yaml')

if [ -z "$CHANGED_FILES" ]; then
    echo "No playlist files changed" >&2
    exit 0
fi

echo "Changed files:" >&2
echo "$CHANGED_FILES" >&2
echo "" >&2

# Output files space-separated for use with --files argument
echo "$CHANGED_FILES" | tr '\n' ' '
