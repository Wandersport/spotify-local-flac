#!/usr/bin/env bash
# Spotify Local FLAC - Production Installer
# Supports CachyOS / Arch Linux (Native & Flatpak Spotify)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_HOME="$HOME"

echo "=========================================================="
echo "  Installing Spotify Local FLAC Integration"
echo "=========================================================="

# 1. Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "✔ Detected OS: ${PRETTY_NAME:-$NAME}"
    if [[ "${ID:-}" != "cachyos" && "${ID:-}" != "arch" && "${ID_LIKE:-}" != *"arch"* ]]; then
        echo "⚠ Warning: This installer is optimized for Arch / CachyOS. Continuing..."
    fi
else
    echo "⚠ Cannot identify OS from /etc/os-release. Continuing..."
fi

# 2. Check and install dependencies
echo "--- Checking dependencies ---"
MISSING_PKGS=()

command -v python3 >/dev/null 2>&1 || MISSING_PKGS+=(python)
python3 -c "import mutagen" >/dev/null 2>&1 || MISSING_PKGS+=(python-mutagen)

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    echo "Installing missing dependencies: ${MISSING_PKGS[*]}"
    if command -v pacman >/dev/null 2>&1; then
        sudo pacman -S --noconfirm --needed "${MISSING_PKGS[@]}"
    else
        echo "❌ pacman not found. Please install manually: ${MISSING_PKGS[*]}"
        exit 1
    fi
fi
echo "✔ Core Python dependencies verified."

# 3. Detect Spotify installation
echo "--- Detecting Spotify installation ---"
IS_FLATPAK=0
SPOTIFY_PATH=""
PREFS_PATH=""

if flatpak info com.spotify.Client >/dev/null 2>&1; then
    IS_FLATPAK=1
    echo "✔ Detected Spotify installed via Flatpak (com.spotify.Client)"
    
    # Check for system or user flatpak install
    SYSTEM_FP_PATH="/var/lib/flatpak/app/com.spotify.Client/x86_64/stable/active/files/extra/share/spotify"
    USER_FP_PATH="$USER_HOME/.local/share/flatpak/app/com.spotify.Client/x86_64/stable/active/files/extra/share/spotify"
    
    if [ -d "$SYSTEM_FP_PATH" ]; then
        SPOTIFY_PATH="$SYSTEM_FP_PATH"
        echo "✔ Flatpak Spotify path: $SPOTIFY_PATH"
        # Grant write permissions for Spicetify patching if not already writable
        if [ ! -w "$SPOTIFY_PATH" ] || [ ! -w "$SPOTIFY_PATH/Apps" ]; then
            echo "Granting write permissions to Spotify Flatpak directory for Spicetify..."
            sudo chmod a+wr "$SPOTIFY_PATH"
            sudo chmod -R a+wr "$SPOTIFY_PATH/Apps"
        fi
    elif [ -d "$USER_FP_PATH" ]; then
        SPOTIFY_PATH="$USER_FP_PATH"
        echo "✔ User Flatpak Spotify path: $SPOTIFY_PATH"
        chmod a+wr "$SPOTIFY_PATH" || true
        chmod -R a+wr "$SPOTIFY_PATH/Apps" || true
    else
        # Try dynamic search
        FOUND_PATH=$(find /var/lib/flatpak/app/com.spotify.Client/ -name "spotify" -type f 2>/dev/null | grep -E "extra/share/spotify/spotify$" | head -n 1 || true)
        if [ -n "$FOUND_PATH" ]; then
            SPOTIFY_PATH="$(dirname "$FOUND_PATH")"
            sudo chmod a+wr "$SPOTIFY_PATH"
            sudo chmod -R a+wr "$SPOTIFY_PATH/Apps"
        else
            echo "❌ Could not find Spotify Flatpak app directory."
            exit 1
        fi
    fi
    
    PREFS_PATH="$USER_HOME/.var/app/com.spotify.Client/config/spotify/prefs"
    if [ ! -f "$PREFS_PATH" ]; then
        mkdir -p "$(dirname "$PREFS_PATH")"
        touch "$PREFS_PATH"
    fi
    echo "✔ Spotify prefs path: $PREFS_PATH"

elif command -v spotify >/dev/null 2>&1; then
    echo "✔ Detected Native Spotify installation"
    SPOTIFY_BIN="$(command -v spotify)"
    # Resolve symlink
    REAL_SPOTIFY="$(readlink -f "$SPOTIFY_BIN" || echo "$SPOTIFY_BIN")"
    SPOTIFY_PATH="$(dirname "$REAL_SPOTIFY")"
    PREFS_PATH="$USER_HOME/.config/spotify/prefs"
    if [ ! -w "$SPOTIFY_PATH" ]; then
        sudo chmod a+wr "$SPOTIFY_PATH" || true
        sudo chmod -R a+wr "$SPOTIFY_PATH/Apps" 2>/dev/null || true
    fi
else
    echo "❌ Neither Flatpak com.spotify.Client nor native Spotify was found."
    exit 1
fi

# 4. Check & configure Spicetify
echo "--- Checking Spicetify CLI ---"
if ! command -v spicetify >/dev/null 2>&1; then
    echo "Installing spicetify-bin from AUR..."
    if command -v yay >/dev/null 2>&1; then
        yay -S --noconfirm spicetify-bin
    elif command -v paru >/dev/null 2>&1; then
        paru -S --noconfirm spicetify-bin
    else
        echo "Installing Spicetify via official release script..."
        curl -fsSL https://raw.githubusercontent.com/spicetify/cli/main/install.sh | sh
        export PATH="$USER_HOME/.spicetify:$PATH"
    fi
fi
echo "✔ Spicetify CLI version: $(spicetify --version)"

# Configure Spicetify paths
spicetify config spotify_path "$SPOTIFY_PATH"
spicetify config prefs_path "$PREFS_PATH"
spicetify config always_enable_devtools 1

# 5. Install Companion backend to ~/.local/share/spotify-local-flac
echo "--- Installing companion backend service ---"
INSTALL_DIR="$USER_HOME/.local/share/spotify-local-flac"
CONFIG_DIR="$USER_HOME/.config/spotify-local-flac"
BIN_DIR="$USER_HOME/.local/bin"

mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$BIN_DIR"

# Copy server code
cp -r "$SCRIPT_DIR/server" "$INSTALL_DIR/"

# Create executable wrapper
cat << 'EOF' > "$BIN_DIR/spotify-local-flac-server"
#!/usr/bin/env bash
exec /usr/bin/python3 "$HOME/.local/share/spotify-local-flac/server/main.py" "$@"
EOF
chmod +x "$BIN_DIR/spotify-local-flac-server"
echo "✔ Backend files installed to $INSTALL_DIR"

# 6. Configure service and security token
TOKEN_FILE="$CONFIG_DIR/token"
if [ ! -f "$TOKEN_FILE" ]; then
    python3 -c "import secrets; print(secrets.token_hex(32))" > "$TOKEN_FILE"
    chmod 600 "$TOKEN_FILE"
fi
AUTH_TOKEN="$(cat "$TOKEN_FILE" | tr -d ' \r\n')"
echo "✔ Local auth token configured."

# Set up config.json if not present
CONFIG_FILE="$CONFIG_DIR/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    # Auto-detect existing user music directories
    DETECTED_DIRS=()
    [ -d "$USER_HOME/Music" ] && DETECTED_DIRS+=("\"$USER_HOME/Music\"")
    
    # Check for /mnt/1TB/[copias]/Music/[NEW MUSIC FOLDERS] or similar
    if [ -d "/mnt/1TB/[copias]/Music/[NEW MUSIC FOLDERS]" ]; then
        DETECTED_DIRS+=("\"/mnt/1TB/[copias]/Music/[NEW MUSIC FOLDERS]\"")
    fi
    
    DIRS_JSON=$(IFS=,; echo "${DETECTED_DIRS[*]}")
    if [ -z "$DIRS_JSON" ]; then
        DIRS_JSON="\"$USER_HOME/Music\""
    fi

    cat << EOF > "$CONFIG_FILE"
{
  "host": "127.0.0.1",
  "port": 18492,
  "music_directories": [
    $DIRS_JSON
  ],
  "exclude_patterns": [
    ".*",
    "*recycle*",
    "*trash*",
    "*lost+found*"
  ],
  "supported_extensions": [
    ".flac",
    ".alac",
    ".wav",
    ".mp3",
    ".ogg",
    ".m4a",
    ".opus",
    ".aiff"
  ],
  "database_path": "$INSTALL_DIR/library.db",
  "watch_directories": true,
  "log_level": "INFO"
}
EOF
    echo "✔ Created default configuration with detected music directories."
fi

# 7. Install Spicetify Custom App and Extension
echo "--- Installing Spicetify Custom App and Extension ---"
SPICETIFY_CUSTOM_APPS="$USER_HOME/.config/spicetify/CustomApps"
SPICETIFY_EXTENSIONS="$USER_HOME/.config/spicetify/Extensions"
mkdir -p "$SPICETIFY_CUSTOM_APPS/local-flac" "$SPICETIFY_EXTENSIONS"

# Copy custom app files
cp -r "$SCRIPT_DIR/spicetify/CustomApps/local-flac/"* "$SPICETIFY_CUSTOM_APPS/local-flac/"

# Inject current token & port into extension
EXT_SRC="$SCRIPT_DIR/spicetify/Extensions/local-flac-player.js"
EXT_DEST="$SPICETIFY_EXTENSIONS/local-flac-player.js"

sed -e "s/token: \"\"/token: \"$AUTH_TOKEN\"/g" "$EXT_SRC" > "$EXT_DEST"

# Configure spicetify config-xpui.ini
echo "Registering custom app 'local-flac' and extension 'local-flac-player.js' in Spicetify..."
spicetify config custom_apps local-flac
spicetify config extensions local-flac-player.js

echo "Applying Spicetify modifications..."
# If not yet backed up, run backup apply, else apply
if spicetify apply; then
    echo "✔ Spicetify successfully applied!"
else
    echo "Spicetify apply failed, trying backup apply..."
    spicetify backup apply
fi

# 8. Install and start systemd user service
echo "--- Setting up systemd user service ---"
SYSTEMD_USER_DIR="$USER_HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"
cp "$SCRIPT_DIR/systemd/spotify-local-flac.service" "$SYSTEMD_USER_DIR/"

systemctl --user daemon-reload
systemctl --user enable spotify-local-flac.service
systemctl --user restart spotify-local-flac.service

# 9. Verify service health
echo "--- Verifying backend service health ---"
sleep 1
HEALTH_CHECK=""
for i in {1..5}; do
    if curl -s http://127.0.0.1:18492/api/health | grep -q '"status":\s*"ok"'; then
        HEALTH_CHECK="ok"
        break
    fi
    sleep 1
done

if [ "$HEALTH_CHECK" = "ok" ]; then
    echo "✔ Local FLAC backend service is healthy and running on 127.0.0.1:18492!"
else
    echo "⚠ Warning: Service health check did not respond immediately. Check 'journalctl --user -u spotify-local-flac.service -e'"
fi

echo ""
echo "=========================================================="
echo "  Installation Complete!"
echo "  Open Spotify -> click 'Local FLAC' in the sidebar."
echo "  Manage service: systemctl --user status spotify-local-flac"
echo "  View logs:      journalctl --user -u spotify-local-flac -f"
echo "=========================================================="
