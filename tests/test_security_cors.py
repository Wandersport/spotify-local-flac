"""Tests for CORS restrictions and timing-safe authentication."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from http.client import HTTPConnection
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.config import Config
from server.db import Database
from server.app import ThreadedHTTPServer, APIHandler


class TestSecurityAndCORS(unittest.TestCase):
    server = None
    server_thread = None

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.config_path = os.path.join(cls.temp_dir, "config.json")
        cls.db_path = os.path.join(cls.temp_dir, "test.db")
        cls.music_dir = os.path.join(cls.temp_dir, "Music")
        os.makedirs(cls.music_dir, exist_ok=True)

        cls.config = Config(cls.config_path)
        cls.config.data["music_directories"] = [cls.music_dir]
        cls.config.data["database_path"] = cls.db_path
        cls.config.data["port"] = 18499  # Separate test port

        cls.db = Database(cls.db_path)
        cls.token = cls.config.auth_token

        APIHandler.config = cls.config
        APIHandler.db = cls.db
        APIHandler.scanner = None
        APIHandler.watcher = None

        cls.server = ThreadedHTTPServer((cls.config.host, cls.config.port), APIHandler)
        cls.server_thread = threading.Thread(
            target=cls.server.serve_forever,
            daemon=True
        )
        cls.server_thread.start()

        # Wait for server to become responsive
        import time
        for _ in range(30):
            try:
                conn = HTTPConnection("127.0.0.1", 18499, timeout=1)
                conn.request("GET", "/api/health")
                resp = conn.getresponse()
                if resp.status == 200:
                    conn.close()
                    break
            except Exception:
                time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        if cls.server:
            cls.server.shutdown()
        cls.db.close()
        shutil.rmtree(cls.temp_dir)

    def test_cors_allowed_spotify_origin(self):
        conn = HTTPConnection("127.0.0.1", 18499)
        conn.request("GET", "/api/health", headers={"Origin": "https://xpui.app.spotify.com"})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.getheader("Access-Control-Allow-Origin"), "https://xpui.app.spotify.com")
        conn.close()

    def test_cors_allowed_null_origin(self):
        conn = HTTPConnection("127.0.0.1", 18499)
        conn.request("GET", "/api/health", headers={"Origin": "null"})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.getheader("Access-Control-Allow-Origin"), "null")
        conn.close()

    def test_cors_allowed_localhost_origin(self):
        conn = HTTPConnection("127.0.0.1", 18499)
        conn.request("GET", "/api/health", headers={"Origin": "http://127.0.0.1:18499"})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.getheader("Access-Control-Allow-Origin"), "http://127.0.0.1:18499")
        conn.close()

    def test_cors_disallowed_evil_origin(self):
        conn = HTTPConnection("127.0.0.1", 18499)
        conn.request("GET", "/api/health", headers={"Origin": "https://evil-attacker.com"})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        # Malicious origin must NOT be echoed in Access-Control-Allow-Origin
        self.assertIsNone(resp.getheader("Access-Control-Allow-Origin"))
        conn.close()

    def test_auth_valid_bearer_header(self):
        conn = HTTPConnection("127.0.0.1", 18499)
        conn.request("GET", "/api/status", headers={"Authorization": f"Bearer {self.token}"})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        conn.close()

    def test_auth_invalid_bearer_header(self):
        conn = HTTPConnection("127.0.0.1", 18499)
        conn.request("GET", "/api/status", headers={"Authorization": "Bearer invalid_token_12345"})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 401)
        conn.close()

    def test_auth_missing_header(self):
        conn = HTTPConnection("127.0.0.1", 18499)
        conn.request("GET", "/api/status")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 401)
        conn.close()

    def test_auth_valid_query_token_for_artwork(self):
        conn = HTTPConnection("127.0.0.1", 18499)
        conn.request("GET", f"/api/artwork/1?token={self.token}")
        resp = conn.getresponse()
        # Should not be 401 (might be 404 because track 1 doesn't exist, but auth succeeds)
        self.assertNotEqual(resp.status, 401)
        conn.close()

    def test_auth_invalid_query_token_for_artwork(self):
        conn = HTTPConnection("127.0.0.1", 18499)
        conn.request("GET", "/api/artwork/1?token=bad_token")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 401)
        conn.close()


if __name__ == "__main__":
    unittest.main()
