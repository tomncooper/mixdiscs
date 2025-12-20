#!/bin/bash
# Validate changed playlists locally
# Usage: ./scripts/validate_changed.sh [base_branch]

set -e

BASE_BRANCH="${1:-main}"

# Check if Spotify credentials are set
if [ -z "$SPOTIPY_CLIENT_ID" ] || [ -z "$SPOTIPY_CLIENT_SECRET" ]; then
    echo "Error: Spotify credentials not set"
    echo "Please export SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET"
    exit 1
fi

# Get changed files
CHANGED_FILES=$(./scripts/get_changed_playlists.sh "$BASE_BRANCH")

if [ -z "$CHANGED_FILES" ]; then
    echo "No playlist files to validate"
    exit 0
fi

echo "Validating changed playlists..."
echo ""

# Run validation
uv run python app.py validate config.yaml --files $CHANGED_FILES
