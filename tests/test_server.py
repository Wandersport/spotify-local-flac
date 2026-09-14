"""Automated test suite for Spotify Local FLAC companion service."""

import os
import sys
import json
import time
import shutil
import tempfile
import unittest
import urllib.request
import urllib.error
import threading

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.config import Config
from server.db import Database
from server.metadata import extract_metadata, extract_artwork_bytes
from server.scanner import LibraryScanner
from server.app import ThreadedHTTPServer, APIHandler


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config.json")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_config_defaults_and_token(self):
        cfg = Config(self.config_path)
        self.assertEqual(cfg.host, "127.0.0.1")
        self.assertEqual(cfg.port, 18492)
        self.assertTrue(len(cfg.auth_token) >= 32)
        self.assertTrue(os.path.exists(self.config_path))
        self.assertTrue(os.path.exists(cfg.token_file))

    def test_path_traversal_protection(self):
        cfg = Config(self.config_path)
        music_dir = os.path.join(self.temp_dir, "Music")
        os.makedirs(music_dir, exist_ok=True)
        cfg.data["music_directories"] = [music_dir]

        safe_file = os.path.join(music_dir, "album", "song.flac")
        self.assertTrue(cfg.is_path_allowed(safe_file))

        # Path traversal attempts
        traversal_1 = os.path.join(music_dir, "..", "secret.txt")
        self.assertFalse(cfg.is_path_allowed(traversal_1))
        self.assertFalse(cfg.is_path_allowed("/etc/passwd"))
        self.assertFalse(cfg.is_path_allowed("/home/admin/.bashrc"))


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.db = Database(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_upsert_and_query_tracks(self):
        sample_track = {
            "path": "/music/artist/album/01-song.flac",
            "filename": "01-song.flac",
            "title": "Test Song",
            "artist": "Test Artist",
            "album": "Test Album",
            "album_artist": "Test Artist",
            "genre": "Hip Hop",
            "year": 2024,
            "track_number": 1,
            "disc_number": 1,
            "duration": 185.5,
            "codec": "FLAC",
            "sample_rate": 48000,
            "bit_depth": 24,
            "channels": 2,
            "bitrate": 1411200,
            "file_size": 25000000,
            "mtime": 1700000000.0,
            "has_artwork": 1
        }
        track_id = self.db.upsert_track(sample_track)
        self.assertGreater(track_id, 0)

        # Retrieve by ID
        t = self.db.get_track_by_id(track_id)
        self.assertIsNotNone(t)
        self.assertEqual(t["title"], "Test Song")
        self.assertEqual(t["codec"], "FLAC")
        self.assertEqual(t["sample_rate"], 48000)
        self.assertEqual(t["bit_depth"], 24)

        # Query search
        results, count = self.db.query_tracks(search="Test")
        self.assertEqual(count, 1)
        self.assertEqual(results[0]["id"], track_id)

        # Query albums
        albums = self.db.get_albums()
        self.assertEqual(len(albums), 1)
        self.assertEqual(albums[0]["album"], "Test Album")
        self.assertEqual(albums[0]["track_count"], 1)

        # Query artists
        artists = self.db.get_artists()
        self.assertEqual(len(artists), 1)
        self.assertEqual(artists[0]["artist"], "Test Artist")

        # Record recently played
        self.db.record_recently_played(track_id)
        recent = self.db.get_recently_played()
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["id"], track_id)


class TestHTTPServerAndStreaming(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.config_path = os.path.join(cls.temp_dir, "config.json")
        cls.music_dir = os.path.join(cls.temp_dir, "Music")
        os.makedirs(cls.music_dir, exist_ok=True)

        cls.config = Config(cls.config_path)
        cls.config.data["music_directories"] = [cls.music_dir]
        cls.config.data["port"] = 19482
        cls.config.save()

        cls.db = Database(cls.config.database_path)
        cls.scanner = LibraryScanner(cls.config, cls.db)

        # Create dummy audio file for streaming test
        cls.audio_file = os.path.join(cls.music_dir, "test_track.flac")
        cls.dummy_content = b"fLaC" + b"\x00" * 1024 * 100  # 100KB dummy payload
        with open(cls.audio_file, "wb") as f:
            f.write(cls.dummy_content)

        cls.track_id = cls.db.upsert_track({
            "path": cls.audio_file,
            "filename": "test_track.flac",
            "title": "Stream Track",
            "artist": "Stream Artist",
            "album": "Stream Album",
            "album_artist": "Stream Artist",
            "genre": "Test",
            "year": 2026,
            "track_number": 1,
            "disc_number": 1,
            "duration": 60.0,
            "codec": "FLAC",
            "sample_rate": 48000,
            "bit_depth": 24,
            "channels": 2,
            "bitrate": 1000,
            "file_size": len(cls.dummy_content),
            "mtime": os.path.getmtime(cls.audio_file),
            "has_artwork": 0
        })

        APIHandler.config = cls.config
        APIHandler.db = cls.db
        APIHandler.scanner = cls.scanner

        cls.server = ThreadedHTTPServer(("127.0.0.1", cls.config.port), APIHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.temp_dir)

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.config.port}{path}"

    def test_health_unauthenticated(self):
        req = urllib.request.Request(self._url("/api/health"))
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")

    def test_auth_rejection(self):
        req = urllib.request.Request(self._url("/api/status"))
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 401)

    def test_authenticated_status(self):
        req = urllib.request.Request(self._url("/api/status"))
        req.add_header("Authorization", f"Bearer {self.config.auth_token}")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "online")
            self.assertEqual(data["stats"]["total_tracks"], 1)

    def test_http_range_request_streaming(self):
        # Request partial byte range 1000-4999 (4000 bytes)
        req = urllib.request.Request(self._url(f"/api/stream/{self.track_id}"))
        req.add_header("Authorization", f"Bearer {self.config.auth_token}")
        req.add_header("Range", "bytes=1000-4999")

        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 206)
            self.assertEqual(resp.headers.get("Content-Range"), f"bytes 1000-4999/{len(self.dummy_content)}")
            self.assertEqual(resp.headers.get("Content-Length"), "4000")
            self.assertEqual(resp.headers.get("Content-Type"), "audio/flac")
            content = resp.read()
            self.assertEqual(len(content), 4000)
            self.assertEqual(content, self.dummy_content[1000:5000])

    def test_full_stream_request(self):
        req = urllib.request.Request(self._url(f"/api/stream/{self.track_id}"))
        req.add_header("Authorization", f"Bearer {self.config.auth_token}")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers.get("Content-Length"), str(len(self.dummy_content)))
            content = resp.read()
            self.assertEqual(len(content), len(self.dummy_content))
            self.assertEqual(content, self.dummy_content)


if __name__ == "__main__":
    unittest.main()
