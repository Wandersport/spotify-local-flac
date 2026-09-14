"""Configuration manager for Spotify Local FLAC companion service."""

import os
import json
import secrets
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = os.path.expanduser("~/.config/spotify-local-flac")
DEFAULT_CONFIG_FILE = os.path.join(DEFAULT_CONFIG_DIR, "config.json")
DEFAULT_TOKEN_FILE = os.path.join(DEFAULT_CONFIG_DIR, "token")
DEFAULT_DATA_DIR = os.path.expanduser("~/.local/share/spotify-local-flac")
DEFAULT_DB_FILE = os.path.join(DEFAULT_DATA_DIR, "library.db")

DEFAULT_CONFIG: Dict[str, Any] = {
    "host": "127.0.0.1",
    "port": 18492,
    "music_directories": [
        os.path.expanduser("~/Music")
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
    "database_path": DEFAULT_DB_FILE,
    "watch_directories": True,
    "log_level": "INFO"
}


class Config:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or DEFAULT_CONFIG_FILE
        self.config_dir = os.path.dirname(self.config_path)
        self.token_file = os.path.join(self.config_dir, "token")
        self.data: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self.auth_token: str = ""
        self.load()

    def load(self) -> None:
        """Load configuration and auth token from disk."""
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Load or generate auth token
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, "r", encoding="utf-8") as f:
                    self.auth_token = f.read().strip()
            except Exception as e:
                logger.warning("Failed to read token file: %s", e)
        
        if not self.auth_token:
            self.auth_token = secrets.token_hex(32)
            try:
                # Set strict permissions (user read/write only)
                old_umask = os.umask(0o077)
                try:
                    with open(self.token_file, "w", encoding="utf-8") as f:
                        f.write(self.auth_token + "\n")
                finally:
                    os.umask(old_umask)
            except Exception as e:
                logger.error("Failed to write token file: %s", e)

        # Load config.json
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    user_cfg = json.load(f)
                    if isinstance(user_cfg, dict):
                        self.data.update(user_cfg)
            except Exception as e:
                logger.error("Failed to load config from %s: %s", self.config_path, e)
        else:
            self.save()

        # Ensure database directory exists
        db_dir = os.path.dirname(self.database_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def save(self) -> None:
        """Save current configuration to disk."""
        os.makedirs(self.config_dir, exist_ok=True)
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to save config to %s: %s", self.config_path, e)

    @property
    def host(self) -> str:
        # Enforce localhost only for security
        h = self.data.get("host", "127.0.0.1")
        if h not in ("127.0.0.1", "localhost", "::1"):
            logger.warning("Non-localhost host '%s' rejected for security; falling back to 127.0.0.1", h)
            return "127.0.0.1"
        return h

    @property
    def port(self) -> int:
        return int(self.data.get("port", 18492))

    @property
    def music_directories(self) -> List[str]:
        dirs = self.data.get("music_directories", [])
        resolved = []
        for d in dirs:
            exp = os.path.abspath(os.path.expanduser(d))
            if exp not in resolved:
                resolved.append(exp)
        return resolved

    @property
    def exclude_patterns(self) -> List[str]:
        return self.data.get("exclude_patterns", DEFAULT_CONFIG["exclude_patterns"])

    @property
    def supported_extensions(self) -> List[str]:
        exts = self.data.get("supported_extensions", DEFAULT_CONFIG["supported_extensions"])
        return [e.lower() if e.startswith(".") else f".{e.lower()}" for e in exts]

    @property
    def database_path(self) -> str:
        db_p = self.data.get("database_path", DEFAULT_DB_FILE)
        return os.path.abspath(os.path.expanduser(db_p))

    @property
    def watch_directories(self) -> bool:
        return bool(self.data.get("watch_directories", True))

    @property
    def log_level(self) -> str:
        return self.data.get("log_level", "INFO").upper()

    def add_directory(self, path: str) -> bool:
        """Add music directory if it exists."""
        abs_path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(abs_path):
            return False
        dirs = self.music_directories
        if abs_path not in dirs:
            dirs.append(abs_path)
            self.data["music_directories"] = dirs
            self.save()
            return True
        return False

    def remove_directory(self, path: str) -> bool:
        """Remove a directory from the configuration."""
        abs_path = os.path.abspath(os.path.expanduser(path))
        dirs = self.music_directories
        if abs_path in dirs:
            dirs.remove(abs_path)
            self.data["music_directories"] = dirs
            self.save()
            return True
        return False

    def is_path_allowed(self, target_path: str) -> bool:
        """Check if target_path is within one of the configured music directories (preventing path traversal)."""
        try:
            real_target = os.path.realpath(os.path.abspath(os.path.expanduser(target_path)))
            for music_dir in self.music_directories:
                real_music_dir = os.path.realpath(music_dir)
                if real_target == real_music_dir or real_target.startswith(real_music_dir + os.sep):
                    return True
            return False
        except Exception:
            return False
