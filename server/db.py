"""Database layer using SQLite for high performance and lightweight caching."""

import os
import sqlite3
import threading
import time
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def escape_like(s: str) -> str:
    """Escape special characters for SQL LIKE pattern matching."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class Database:
    def __init__(self, db_path: str):
        self.db_path = os.path.abspath(os.path.expanduser(db_path))
        self._lock = threading.RLock()
        self._local = threading.local()
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local SQLite connection with row factory."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            # Enable WAL mode for high concurrency between reader & writer threads
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute("PRAGMA cache_size=-64000;")  # 64MB cache
            self._local.conn = conn
        return self._local.conn

    def close(self) -> None:
        """Close connection if open."""
        with self._lock:
            if hasattr(self._local, "conn") and self._local.conn is not None:
                try:
                    self._local.conn.close()
                except Exception:
                    pass
                self._local.conn = None

    def init_db(self) -> None:
        """Initialize SQLite database tables and indices."""
        with self._lock:
            conn = self._get_connection()
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tracks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        path TEXT UNIQUE NOT NULL,
                        filename TEXT NOT NULL,
                        title TEXT NOT NULL,
                        artist TEXT NOT NULL,
                        album TEXT NOT NULL,
                        album_artist TEXT,
                        genre TEXT,
                        year INTEGER,
                        track_number INTEGER,
                        disc_number INTEGER,
                        duration REAL NOT NULL,
                        codec TEXT NOT NULL,
                        sample_rate INTEGER NOT NULL,
                        bit_depth INTEGER,
                        channels INTEGER,
                        bitrate INTEGER,
                        file_size INTEGER NOT NULL,
                        mtime REAL NOT NULL,
                        has_artwork INTEGER DEFAULT 0,
                        created_at REAL NOT NULL
                    );
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist);
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks(album);
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks(title);
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tracks_path ON tracks(path);
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS recently_played (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
                        played_at REAL NOT NULL
                    );
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_recent_played_at ON recently_played(played_at DESC);
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS scan_directories (
                        path TEXT UNIQUE NOT NULL,
                        last_scanned REAL NOT NULL
                    );
                """)

    def upsert_track(self, track: Dict[str, Any]) -> int:
        """Insert or update track record based on file path."""
        with self._lock:
            conn = self._get_connection()
            now = time.time()
            data = {
                "album_artist": None,
                "genre": None,
                "year": None,
                "track_number": None,
                "disc_number": None,
                "bitrate": None,
                "bit_depth": None,
                "channels": 2,
                "sample_rate": 44100,
                **track,
                "created_at": now,
            }
            with conn:
                cursor = conn.execute("""
                    INSERT INTO tracks (
                        path, filename, title, artist, album, album_artist, genre,
                        year, track_number, disc_number, duration, codec, sample_rate,
                        bit_depth, channels, bitrate, file_size, mtime, has_artwork, created_at
                    ) VALUES (
                        :path, :filename, :title, :artist, :album, :album_artist, :genre,
                        :year, :track_number, :disc_number, :duration, :codec, :sample_rate,
                        :bit_depth, :channels, :bitrate, :file_size, :mtime, :has_artwork, :created_at
                    )
                    ON CONFLICT(path) DO UPDATE SET
                        filename=excluded.filename,
                        title=excluded.title,
                        artist=excluded.artist,
                        album=excluded.album,
                        album_artist=excluded.album_artist,
                        genre=excluded.genre,
                        year=excluded.year,
                        track_number=excluded.track_number,
                        disc_number=excluded.disc_number,
                        duration=excluded.duration,
                        codec=excluded.codec,
                        sample_rate=excluded.sample_rate,
                        bit_depth=excluded.bit_depth,
                        channels=excluded.channels,
                        bitrate=excluded.bitrate,
                        file_size=excluded.file_size,
                        mtime=excluded.mtime,
                        has_artwork=excluded.has_artwork;
                """, data)
                return cursor.lastrowid or 0

    def upsert_tracks_batch(self, tracks: List[Dict[str, Any]]) -> int:
        """Insert or update a list of track records in a single transaction."""
        if not tracks:
            return 0
        with self._lock:
            conn = self._get_connection()
            now = time.time()
            prepared = [
                {
                    "album_artist": None,
                    "genre": None,
                    "year": None,
                    "track_number": None,
                    "disc_number": None,
                    "bitrate": None,
                    "bit_depth": None,
                    "channels": 2,
                    "sample_rate": 44100,
                    **t,
                    "created_at": now,
                }
                for t in tracks
            ]
            with conn:
                conn.executemany("""
                    INSERT INTO tracks (
                        path, filename, title, artist, album, album_artist, genre,
                        year, track_number, disc_number, duration, codec, sample_rate,
                        bit_depth, channels, bitrate, file_size, mtime, has_artwork, created_at
                    ) VALUES (
                        :path, :filename, :title, :artist, :album, :album_artist, :genre,
                        :year, :track_number, :disc_number, :duration, :codec, :sample_rate,
                        :bit_depth, :channels, :bitrate, :file_size, :mtime, :has_artwork, :created_at
                    )
                    ON CONFLICT(path) DO UPDATE SET
                        filename=excluded.filename,
                        title=excluded.title,
                        artist=excluded.artist,
                        album=excluded.album,
                        album_artist=excluded.album_artist,
                        genre=excluded.genre,
                        year=excluded.year,
                        track_number=excluded.track_number,
                        disc_number=excluded.disc_number,
                        duration=excluded.duration,
                        codec=excluded.codec,
                        sample_rate=excluded.sample_rate,
                        bit_depth=excluded.bit_depth,
                        channels=excluded.channels,
                        bitrate=excluded.bitrate,
                        file_size=excluded.file_size,
                        mtime=excluded.mtime,
                        has_artwork=excluded.has_artwork;
                """, prepared)
                return len(tracks)

    def get_track_mtime(self, path: str) -> Optional[Tuple[float, int]]:
        """Get (mtime, file_size) for path if known."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT mtime, file_size FROM tracks WHERE path = ?", (path,))
        row = cursor.fetchone()
        return (row["mtime"], row["file_size"]) if row else None

    def get_all_paths(self) -> List[str]:
        """Get list of all indexed track paths."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT path FROM tracks")
        return [row["path"] for row in cursor.fetchall()]

    def delete_tracks_by_paths(self, paths: List[str]) -> int:
        """Delete tracks that no longer exist on disk."""
        if not paths:
            return 0
        with self._lock:
            conn = self._get_connection()
            with conn:
                # Batch in chunks of 500
                total = 0
                for i in range(0, len(paths), 500):
                    chunk = paths[i:i + 500]
                    placeholders = ",".join("?" for _ in chunk)
                    cur = conn.execute(f"DELETE FROM tracks WHERE path IN ({placeholders})", chunk)
                    total += cur.rowcount
                return total

    def delete_tracks_by_prefix(self, path_prefix: str) -> int:
        """Delete tracks under a specific directory path prefix (e.g. removed music source)."""
        with self._lock:
            conn = self._get_connection()
            with conn:
                real_prefix = os.path.realpath(os.path.abspath(os.path.expanduser(path_prefix)))
                escaped_prefix = escape_like(real_prefix)
                sql = "DELETE FROM tracks WHERE path = ? OR path LIKE ? ESCAPE '\\'"
                cur = conn.execute(sql, (real_prefix, f"{escaped_prefix}/%"))
                return cur.rowcount

    def delete_track_by_path(self, path: str) -> bool:
        with self._lock:
            conn = self._get_connection()
            with conn:
                cur = conn.execute("DELETE FROM tracks WHERE path = ?", (path,))
                return cur.rowcount > 0

    def get_track_by_id(self, track_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM tracks WHERE id = ?", (track_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_track_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM tracks WHERE path = ?", (path,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def query_tracks(
        self,
        search: Optional[str] = None,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        folder: Optional[str] = None,
        codec: Optional[str] = None,
        sort_by: str = "title",
        sort_order: str = "asc",
        limit: int = 1000,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Query tracks with filters, safe SQL LIKE escaping, server-side sorting, and pagination."""
        conn = self._get_connection()
        conditions = []
        params: List[Any] = []

        if search:
            q = f"%{escape_like(search)}%"
            conditions.append("(title LIKE ? ESCAPE '\\' OR artist LIKE ? ESCAPE '\\' OR album LIKE ? ESCAPE '\\' OR filename LIKE ? ESCAPE '\\')")
            params.extend([q, q, q, q])

        if artist:
            conditions.append("artist = ?")
            params.append(artist)

        if album:
            conditions.append("album = ?")
            params.append(album)

        if codec:
            conditions.append("UPPER(codec) = ?")
            params.append(codec.strip().upper())

        if folder:
            f = os.path.realpath(os.path.abspath(os.path.expanduser(folder)))
            escaped_f = escape_like(f)
            conditions.append("(path LIKE ? ESCAPE '\\' OR path = ?)")
            params.extend([f"{escaped_f}/%", f])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        valid_sort_fields = {
            "title": ["title COLLATE NOCASE", "artist COLLATE NOCASE"],
            "artist": ["artist COLLATE NOCASE", "album COLLATE NOCASE", "track_number", "title COLLATE NOCASE"],
            "album": ["album COLLATE NOCASE", "disc_number", "track_number", "title COLLATE NOCASE"],
            "year": ["year", "album COLLATE NOCASE", "track_number"],
            "duration": ["duration"],
            "track_number": ["disc_number", "track_number", "title COLLATE NOCASE"],
            "created_at": ["created_at"],
            "mtime": ["mtime"]
        }
        cols = valid_sort_fields.get(sort_by.lower(), ["title COLLATE NOCASE"])
        direction = "DESC" if sort_order.lower() == "desc" else "ASC"
        order_clause = ", ".join(f"{c} {direction}" for c in cols)

        # Count total matching
        count_sql = f"SELECT COUNT(*) as cnt FROM tracks {where_clause}"
        total = conn.execute(count_sql, params).fetchone()["cnt"]

        # Fetch records
        sql = f"""
            SELECT * FROM tracks
            {where_clause}
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
        """
        fetch_params = list(params)
        fetch_params.extend([limit, offset])
        cursor = conn.execute(sql, fetch_params)
        tracks = [dict(r) for r in cursor.fetchall()]
        return tracks, total

    def get_albums(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get aggregated albums list with safe search escaping."""
        conn = self._get_connection()
        where = ""
        params: List[Any] = []
        if search:
            where = "WHERE album LIKE ? ESCAPE '\\' OR artist LIKE ? ESCAPE '\\'"
            q = f"%{escape_like(search)}%"
            params = [q, q]

        sql = f"""
            SELECT
                album,
                COALESCE(album_artist, artist) as artist,
                MAX(year) as year,
                COUNT(*) as track_count,
                SUM(duration) as total_duration,
                MIN(id) as sample_track_id,
                MAX(has_artwork) as has_artwork
            FROM tracks
            {where}
            GROUP BY album, COALESCE(album_artist, artist)
            ORDER BY album COLLATE NOCASE ASC
        """
        cursor = conn.execute(sql, params)
        return [dict(r) for r in cursor.fetchall()]

    def get_artists(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get aggregated artists list with safe search escaping."""
        conn = self._get_connection()
        where = ""
        params: List[Any] = []
        if search:
            where = "WHERE artist LIKE ? ESCAPE '\\'"
            params = [f"%{escape_like(search)}%"]

        sql = f"""
            SELECT
                artist,
                COUNT(*) as track_count,
                COUNT(DISTINCT album) as album_count,
                SUM(duration) as total_duration,
                MIN(id) as sample_track_id,
                MAX(has_artwork) as has_artwork
            FROM tracks
            {where}
            GROUP BY artist
            ORDER BY artist COLLATE NOCASE ASC
        """
        cursor = conn.execute(sql, params)
        return [dict(r) for r in cursor.fetchall()]

    def record_recently_played(self, track_id: int) -> None:
        """Record track playback event."""
        with self._lock:
            conn = self._get_connection()
            with conn:
                conn.execute(
                    "INSERT INTO recently_played (track_id, played_at) VALUES (?, ?)",
                    (track_id, time.time())
                )
                # Keep only latest 200 entries
                conn.execute("""
                    DELETE FROM recently_played WHERE id NOT IN (
                        SELECT id FROM recently_played ORDER BY played_at DESC LIMIT 200
                    )
                """)

    def get_recently_played(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recently played tracks with deduplication."""
        conn = self._get_connection()
        sql = """
            SELECT t.*, MAX(r.played_at) as last_played_at
            FROM recently_played r
            JOIN tracks t ON t.id = r.track_id
            GROUP BY t.id
            ORDER BY last_played_at DESC
            LIMIT ?
        """
        cursor = conn.execute(sql, (limit,))
        return [dict(r) for r in cursor.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        """Get library summary stats."""
        conn = self._get_connection()
        row = conn.execute("""
            SELECT
                COUNT(*) as total_tracks,
                COUNT(DISTINCT album) as total_albums,
                COUNT(DISTINCT artist) as total_artists,
                COALESCE(SUM(duration), 0) as total_duration,
                COALESCE(SUM(file_size), 0) as total_size,
                COALESCE(SUM(CASE WHEN codec = 'FLAC' THEN 1 ELSE 0 END), 0) as flac_count
            FROM tracks
        """).fetchone()
        return dict(row) if row else {
            "total_tracks": 0, "total_albums": 0, "total_artists": 0,
            "total_duration": 0, "total_size": 0, "flac_count": 0
        }
