"""Tests for live inotify DirectoryWatcher root management and DB cleanup."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.config import Config
from server.db import Database
from server.scanner import LibraryScanner
from server.watcher import DirectoryWatcher


class TestWatcherLive(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root1 = os.path.join(self.temp_dir, "Music1")
        self.root2 = os.path.join(self.temp_dir, "Music2")
        os.makedirs(self.root1, exist_ok=True)
        os.makedirs(self.root2, exist_ok=True)

        self.config_path = os.path.join(self.temp_dir, "config.json")
        self.db_path = os.path.join(self.temp_dir, "test.db")

        self.config = Config(self.config_path)
        self.config.data["music_directories"] = [self.root1, self.root2]
        self.config.data["database_path"] = self.db_path

        self.db = Database(self.db_path)
        self.scanner = LibraryScanner(self.config, self.db)
        self.watcher = DirectoryWatcher(self.config, self.scanner)

        if not self.watcher._init_libc():
            self.skipTest("libc inotify not available on this platform")

        import ctypes
        self.watcher._inotify_fd = self.watcher._libc.inotify_init()

    def tearDown(self):
        if self.watcher._inotify_fd is not None:
            try:
                os.close(self.watcher._inotify_fd)
            except Exception:
                pass
        self.db.close()
        shutil.rmtree(self.temp_dir)

    def test_add_and_remove_root(self):
        # 1. Add root1
        self.watcher.add_root(self.root1)
        root1_real = os.path.realpath(self.root1)
        self.assertIn(root1_real, list(self.watcher._wd_to_path.values()))

        # 2. Add root2
        self.watcher.add_root(self.root2)
        root2_real = os.path.realpath(self.root2)
        self.assertIn(root2_real, list(self.watcher._wd_to_path.values()))

        # 3. Populate tracks under root1 and root2
        self.db.upsert_track({
            "path": os.path.join(root1_real, "song1.flac"),
            "filename": "song1.flac",
            "title": "Song 1",
            "artist": "Artist 1",
            "album": "Album 1",
            "duration": 100.0,
            "codec": "FLAC",
            "file_size": 1000,
            "mtime": 1000.0,
            "has_artwork": False
        })
        self.db.upsert_track({
            "path": os.path.join(root2_real, "song2.flac"),
            "filename": "song2.flac",
            "title": "Song 2",
            "artist": "Artist 2",
            "album": "Album 2",
            "duration": 200.0,
            "codec": "FLAC",
            "file_size": 2000,
            "mtime": 2000.0,
            "has_artwork": False
        })

        tracks, total = self.db.query_tracks()
        self.assertEqual(total, 2)

        # 4. Remove root1 from watcher
        self.watcher.remove_root(self.root1)
        self.assertNotIn(root1_real, list(self.watcher._wd_to_path.values()))
        self.assertIn(root2_real, list(self.watcher._wd_to_path.values()))

        # 5. Clean DB by prefix for removed root
        deleted_count = self.db.delete_tracks_by_prefix(root1_real)
        self.assertEqual(deleted_count, 1)

        # Only song2 remains
        tracks, total = self.db.query_tracks()
        self.assertEqual(total, 1)
        self.assertEqual(tracks[0]["path"], os.path.join(root2_real, "song2.flac"))

    def test_reload_roots(self):
        self.watcher.add_root(self.root1)
        root1_real = os.path.realpath(self.root1)
        self.assertIn(root1_real, list(self.watcher._wd_to_path.values()))

        # Change config music directories to only root2
        self.config.data["music_directories"] = [self.root2]
        self.watcher.reload_roots()

        root2_real = os.path.realpath(self.root2)
        self.assertNotIn(root1_real, list(self.watcher._wd_to_path.values()))
        self.assertIn(root2_real, list(self.watcher._wd_to_path.values()))


if __name__ == "__main__":
    unittest.main()
