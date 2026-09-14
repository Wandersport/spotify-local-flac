#!/usr/bin/env bash
# Spotify Local FLAC - Uninstaller

set -euo pipefail

USER_HOME="$HOME"
INSTALL_DIR="$USER_HOME/.local/share/spotify-local-flac"
CONFIG_DIR="$USER_HOME/.config/spotify-local-flac"
BIN_FILE="$USER_HOME/.local/bin/spotify-local-flac-server"
SERVICE_FILE="$USER_HOME/.config/systemd/user/spotify-local-flac.service"
SPICETIFY_CUSTOM_APPS="$USER_HOME/.config/spicetify/CustomApps/local-flac"
SPICETIFY_EXTENSIONS="$USER_HOME/.config/spicetify/Extensions/local-flac-player.js"

echo "=========================================================="
echo "  Uninstalling Spotify Local FLAC Integration"
echo "=========================================================="

# 1. Stop and disable systemd user service
if systemctl --user is-active --quiet spotify-local-flac.service 2>/dev/null; then
    echo "Stopping spotify-local-flac.service..."
    systemctl --user stop spotify-local-flac.service
fi

if systemctl --user is-enabled --quiet spotify-local-flac.service 2>/dev/null; then
    echo "Disabling spotify-local-flac.service..."
    systemctl --user disable spotify-local-flac.service
fi

rm -f "$SERVICE_FILE"
systemctl --user daemon-reload
echo "✔ Systemd user service removed."

# 2. Unregister from Spicetify
if command -v spicetify >/dev/null 2>&1; then
    echo "Unregistering custom app and extension from Spicetify..."
    spicetify config custom_apps local-flac- || true
    spicetify config extensions local-flac-player.js- || true
    spicetify apply || true
fi

# 3. Remove custom app and extension files
rm -rf "$SPICETIFY_CUSTOM_APPS"
rm -f "$SPICETIFY_EXTENSIONS"
echo "✔ Spicetify components removed."

# 4. Remove backend binaries and data
rm -f "$BIN_FILE"
rm -rf "$INSTALL_DIR"
echo "✔ Backend installation removed."

# Optional: keep or remove config
if [ "${1:-}" = "--purge" ]; then
    rm -rf "$CONFIG_DIR"
    echo "✔ Purged configuration and database."
else
    echo "Note: Configuration left at $CONFIG_DIR (run with --purge to remove)."
fi

echo "=========================================================="
echo "  Uninstallation complete."
echo "=========================================================="
