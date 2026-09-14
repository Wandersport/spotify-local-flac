#!/usr/bin/env bash
# Spotify Local FLAC - Update Script
# Use after Spotify updates, or to update backend code

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_HOME="$HOME"

echo "=========================================================="
echo "  Updating Spotify Local FLAC Integration"
echo "=========================================================="

# 1. Update backend files
INSTALL_DIR="$USER_HOME/.local/share/spotify-local-flac"
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating backend code..."
    cp -r "$SCRIPT_DIR/server" "$INSTALL_DIR/"
    systemctl --user restart spotify-local-flac.service || true
    echo "✔ Backend restarted."
fi

# 2. Update Spicetify files
SPICETIFY_CUSTOM_APPS="$USER_HOME/.config/spicetify/CustomApps/local-flac"
SPICETIFY_EXTENSIONS="$USER_HOME/.config/spicetify/Extensions"
TOKEN_FILE="$USER_HOME/.config/spotify-local-flac/token"
AUTH_TOKEN=""
[ -f "$TOKEN_FILE" ] && AUTH_TOKEN="$(cat "$TOKEN_FILE" | tr -d ' \r\n')"

if [ -d "$SPICETIFY_CUSTOM_APPS" ]; then
    echo "Updating Custom App..."
    cp -r "$SCRIPT_DIR/spicetify/CustomApps/local-flac/"* "$SPICETIFY_CUSTOM_APPS/"
fi

if [ -d "$SPICETIFY_EXTENSIONS" ]; then
    echo "Updating Extension..."
    EXT_SRC="$SCRIPT_DIR/spicetify/Extensions/local-flac-player.js"
    EXT_DEST="$SPICETIFY_EXTENSIONS/local-flac-player.js"
    sed -e "s/token: \"\"/token: \"$AUTH_TOKEN\"/g" "$EXT_SRC" > "$EXT_DEST"
fi

# 3. Check Spicetify status & re-apply
if command -v spicetify >/dev/null 2>&1; then
    echo "Re-applying Spicetify..."
    if ! spicetify apply; then
        echo "Spicetify apply needed backup, running backup apply..."
        spicetify backup apply
    fi
    echo "✔ Spicetify updated successfully!"
fi

echo "=========================================================="
echo "  Update complete!"
echo "=========================================================="
