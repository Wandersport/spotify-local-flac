"""Production HTTP server with byte-range audio streaming, path validation, and REST API."""

import os
import re
import json
import hmac
import logging
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional, Dict, Any, Tuple
from .config import Config
from .db import Database
from .scanner import LibraryScanner
from .metadata import extract_artwork_bytes

logger = logging.getLogger(__name__)

MIME_MAP = {
    "flac": "audio/flac",
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "ogg": "audio/ogg",
    "opus": "audio/ogg; codecs=opus",
    "m4a": "audio/mp4",
    "mp4": "audio/mp4"
}

ALLOWED_ORIGINS = {
    "https://xpui.app.spotify.com",
    "null"
}


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class APIHandler(BaseHTTPRequestHandler):
    # Class-level references set when server starts
    config: Config
    db: Database
    scanner: LibraryScanner
    watcher: Optional[Any] = None

    # Suppress default server version in headers for security
    server_version = "SpotifyLocalFLAC/1.0"
    sys_version = ""

    def log_message(self, format: str, *args: Any) -> None:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)

    def _send_cors_headers(self) -> None:
        origin = self.headers.get("Origin")
        if origin:
            if (origin in ALLOWED_ORIGINS or
                origin.startswith("http://127.0.0.1:") or
                origin.startswith("http://localhost:")):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
        else:
            self.send_header("Access-Control-Allow-Origin", "https://xpui.app.spotify.com")

        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, Range")
        self.send_header("Access-Control-Expose-Headers", "Content-Range, Content-Length, Accept-Ranges, ETag")

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_error(self, status: int, message: str) -> None:
        self._send_json({"error": message, "status": status}, status=status)

    def _check_auth(self, query_params: Dict[str, list]) -> bool:
        """Validate token from Authorization header or URL query parameter.
        
        Note: HTML5 <audio> and <img> elements cannot send custom Authorization HTTP
        headers in standard browser APIs, so query parameter token authentication (?token=...)
        is technically necessary for media stream and artwork requests.
        """
        expected_token = self.config.auth_token
        if not expected_token:
            return True

        # Check Authorization header (constant-time comparison)
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if hmac.compare_digest(token, expected_token):
                return True

        # Check query parameter ?token=... (constant-time comparison)
        if "token" in query_params:
            if hmac.compare_digest(query_params["token"][0], expected_token):
                return True

        return False

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = urllib.parse.parse_qs(parsed.query)

        # Healthcheck endpoint (unauthenticated)
        if path == "/api/health":
            self._send_json({"status": "ok"})
            return

        # Authenticate all other endpoints
        if not self._check_auth(query):
            self._send_error(401, "Unauthorized: Invalid or missing token")
            return

        try:
            if path == "/api/status":
                self._handle_status()
            elif path == "/api/config":
                self._handle_get_config()
            elif path == "/api/tracks":
                self._handle_get_tracks(query)
            elif path.startswith("/api/tracks/"):
                track_id_str = path.split("/")[-1]
                self._handle_get_track_by_id(track_id_str)
            elif path == "/api/albums":
                self._handle_get_albums(query)
            elif path == "/api/artists":
                self._handle_get_artists(query)
            elif path == "/api/folders":
                self._handle_get_folders(query)
            elif path == "/api/recent":
                self._handle_get_recent(query)
            elif path.startswith("/api/artwork/"):
                track_id_str = path.split("/")[-1]
                self._handle_get_artwork(track_id_str)
            elif path.startswith("/api/stream/"):
                track_id_str = path.split("/")[-1]
                self._handle_stream(track_id_str)
            else:
                self._send_error(404, "Endpoint not found")
        except Exception as e:
            logger.exception("Error handling GET %s: %s", path, e)
            self._send_error(500, f"Internal server error: {e}")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = urllib.parse.parse_qs(parsed.query)

        if not self._check_auth(query):
            self._send_error(401, "Unauthorized: Invalid or missing token")
            return

        try:
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len) if content_len > 0 else b""
            body_data = {}
            if body_bytes:
                try:
                    body_data = json.loads(body_bytes.decode("utf-8"))
                except Exception:
                    self._send_error(400, "Invalid JSON body")
                    return

            if path == "/api/scan":
                self._handle_post_scan()
            elif path == "/api/config/directories":
                self._handle_post_directories(body_data)
            elif path == "/api/recent":
                self._handle_post_recent(body_data)
            else:
                self._send_error(404, "Endpoint not found")
        except Exception as e:
            logger.exception("Error handling POST %s: %s", path, e)
            self._send_error(500, f"Internal server error: {e}")

    def _handle_status(self) -> None:
        stats = self.db.get_stats()
        scanner_status = (
            self.scanner.get_status()
            if self.scanner
            else {"is_scanning": False, "tracks_found": 0, "last_scan": None, "current_file": None}
        )
        self._send_json({
            "status": "online",
            "stats": stats,
            "scanner": scanner_status,
            "music_directories": self.config.music_directories
        })

    def _handle_get_config(self) -> None:
        self._send_json({
            "music_directories": self.config.music_directories,
            "exclude_patterns": self.config.exclude_patterns,
            "supported_extensions": self.config.supported_extensions,
            "database_path": self.config.database_path,
            "watch_directories": self.config.watch_directories,
            "port": self.config.port
        })

    def _handle_post_scan(self) -> None:
        self.scanner.scan_async()
        self._send_json({"message": "Scan started", "is_scanning": True})

    def _handle_post_directories(self, data: Dict[str, Any]) -> None:
        action = data.get("action", "add")
        directory = data.get("directory", "").strip()

        if not directory:
            self._send_error(400, "Missing directory path")
            return

        if action == "add":
            if not os.path.isdir(os.path.expanduser(directory)):
                self._send_error(400, f"Directory does not exist: {directory}")
                return
            success = self.config.add_directory(directory)
            if success:
                if hasattr(self, "watcher") and self.watcher:
                    try:
                        self.watcher.add_root(directory)
                    except Exception as e:
                        logger.warning("Error adding watcher root for %s: %s", directory, e)
                self.scanner.scan_async()
            self._send_json({
                "success": success,
                "music_directories": self.config.music_directories
            })
        elif action == "remove":
            success = self.config.remove_directory(directory)
            if success:
                if hasattr(self, "watcher") and self.watcher:
                    try:
                        self.watcher.remove_root(directory)
                    except Exception as e:
                        logger.warning("Error removing watcher root for %s: %s", directory, e)
                # Immediately remove tracks belonging exclusively to that removed source
                deleted_count = self.db.delete_tracks_by_prefix(directory)
                logger.info("Removed %d tracks belonging to removed source: %s", deleted_count, directory)
            self._send_json({
                "success": success,
                "music_directories": self.config.music_directories
            })
        else:
            self._send_error(400, f"Unknown action: {action}")

    def _handle_get_tracks(self, query: Dict[str, list]) -> None:
        search = query.get("search", [None])[0]
        artist = query.get("artist", [None])[0]
        album = query.get("album", [None])[0]
        folder = query.get("folder", [None])[0]
        codec = query.get("codec", [None])[0]
        sort_by = query.get("sort_by", ["title"])[0]
        sort_order = query.get("sort_order", ["asc"])[0]
        limit = max(1, min(10000, int(query.get("limit", [500])[0])))
        offset = max(0, int(query.get("offset", [0])[0]))

        tracks, total = self.db.query_tracks(
            search=search,
            artist=artist,
            album=album,
            folder=folder,
            codec=codec,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset
        )
        self._send_json({"tracks": tracks, "total": total, "limit": limit, "offset": offset})

    def _handle_get_track_by_id(self, track_id_str: str) -> None:
        try:
            track_id = int(track_id_str)
        except ValueError:
            self._send_error(400, "Invalid track ID")
            return

        track = self.db.get_track_by_id(track_id)
        if not track:
            self._send_error(404, "Track not found")
            return
        self._send_json({"track": track})

    def _handle_get_albums(self, query: Dict[str, list]) -> None:
        search = query.get("search", [None])[0]
        albums = self.db.get_albums(search=search)
        self._send_json({"albums": albums, "total": len(albums)})

    def _handle_get_artists(self, query: Dict[str, list]) -> None:
        search = query.get("search", [None])[0]
        artists = self.db.get_artists(search=search)
        self._send_json({"artists": artists, "total": len(artists)})

    def _handle_get_folders(self, query: Dict[str, list]) -> None:
        requested_path = query.get("path", [None])[0]
        music_dirs = self.config.music_directories

        if not requested_path:
            # Return configured root library directories
            roots = []
            for d in music_dirs:
                if os.path.isdir(d):
                    roots.append({
                        "name": os.path.basename(d) or d,
                        "path": d,
                        "is_dir": True
                    })
            self._send_json({"current_path": None, "items": roots, "music_directories": music_dirs})
            return

        abs_path = os.path.realpath(os.path.abspath(os.path.expanduser(requested_path)))
        if not self.config.is_path_allowed(abs_path):
            self._send_error(403, "Access to requested path is forbidden")
            return

        if not os.path.isdir(abs_path):
            self._send_error(404, "Directory not found")
            return

        items = []
        try:
            for entry in sorted(os.scandir(abs_path), key=lambda e: (not e.is_dir(), e.name.lower())):
                ext = os.path.splitext(entry.name)[1].lower()
                if entry.is_dir():
                    if entry.name.startswith(".") or entry.name.lower() in ("lost+found", "$recycle.bin", ".trash-1000"):
                        continue
                    items.append({
                        "name": entry.name,
                        "path": entry.path,
                        "is_dir": True
                    })
                elif entry.is_file():
                    if ext in self.config.supported_extensions:
                        track = self.db.get_track_by_path(entry.path)
                        items.append({
                            "name": entry.name,
                            "path": entry.path,
                            "is_dir": False,
                            "track": track
                        })
        except PermissionError:
            self._send_error(403, "Permission denied reading directory")
            return

        parent = os.path.dirname(abs_path)
        has_parent = self.config.is_path_allowed(parent) and parent != abs_path

        self._send_json({
            "current_path": abs_path,
            "parent_path": parent if has_parent else None,
            "music_directories": music_dirs,
            "items": items
        })

    def _handle_get_recent(self, query: Dict[str, list]) -> None:
        limit = min(200, max(1, int(query.get("limit", [50])[0])))
        recent = self.db.get_recently_played(limit=limit)
        self._send_json({"recent": recent, "total": len(recent)})

    def _handle_post_recent(self, data: Dict[str, Any]) -> None:
        track_id = data.get("track_id")
        if track_id is None:
            self._send_error(400, "Missing track_id")
            return
        try:
            track_id_int = int(track_id)
            self.db.record_recently_played(track_id_int)
            self._send_json({"success": True})
        except ValueError:
            self._send_error(400, "Invalid track_id")

    def _handle_get_artwork(self, track_id_str: str) -> None:
        try:
            track_id = int(track_id_str)
        except ValueError:
            self._send_error(400, "Invalid track ID")
            return

        track = self.db.get_track_by_id(track_id)
        if not track:
            self._send_error(404, "Track not found")
            return

        file_path = track["path"]
        if not self.config.is_path_allowed(file_path) or not os.path.isfile(file_path):
            self._send_error(404, "Track file not accessible")
            return

        data, mime = extract_artwork_bytes(file_path)
        if not data:
            self._send_error(404, "No artwork found")
            return

        etag = f'"{track["mtime"]}-{len(data)}"'
        if self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self._send_cors_headers()
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", mime or "image/jpeg")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.send_header("ETag", etag)
        self._send_cors_headers()
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _handle_stream(self, track_id_str: str) -> None:
        """Stream audio file supporting HTTP 206 Partial Content range requests."""
        try:
            track_id = int(track_id_str)
        except ValueError:
            self._send_error(400, "Invalid track ID")
            return

        track = self.db.get_track_by_id(track_id)
        if not track:
            self._send_error(404, "Track not found")
            return

        file_path = track["path"]
        if not self.config.is_path_allowed(file_path) or not os.path.isfile(file_path):
            self._send_error(403, "Access to file forbidden")
            return

        try:
            file_size = os.path.getsize(file_path)
        except OSError:
            self._send_error(404, "File not accessible")
            return

        codec = track.get("codec", "FLAC").lower()
        content_type = MIME_MAP.get(codec, "audio/flac")

        range_header = self.headers.get("Range")
        start = 0
        end = file_size - 1

        if range_header:
            m = re.match(r"^bytes=(\d+)-(\d*)$", range_header.strip())
            if m:
                start = int(m.group(1))
                if m.group(2):
                    end = int(m.group(2))

        if start >= file_size or end >= file_size or start > end:
            self.send_response(416)  # Range Not Satisfiable
            self.send_header("Content-Range", f"bytes */{file_size}")
            self._send_cors_headers()
            self.end_headers()
            return

        chunk_len = end - start + 1
        is_partial = (range_header is not None)

        if is_partial:
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        else:
            self.send_response(200)

        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(chunk_len))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        self._send_cors_headers()
        self.end_headers()
        if self.command == "HEAD":
            return

        # Stream chunk by chunk (64KB buffer) without loading entire file into memory
        BUFFER_SIZE = 64 * 1024
        bytes_left = chunk_len

        try:
            with open(file_path, "rb") as f:
                f.seek(start)
                while bytes_left > 0:
                    read_len = min(BUFFER_SIZE, bytes_left)
                    buf = f.read(read_len)
                    if not buf:
                        break
                    self.wfile.write(buf)
                    bytes_left -= len(buf)
        except (BrokenPipeError, ConnectionResetError):
            # Client closed stream (e.g. paused or sought to another position)
            pass
        except Exception as e:
            logger.debug("Stream error on %s: %s", file_path, e)
