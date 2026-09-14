"""Tests for symlink safety, directory traversal escapes, and recursion loop prevention."""

import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.config import Config
from server.db import Database
from server.scanner import LibraryScanner
from server.watcher import DirectoryWatcher


class TestSymlinkSafety(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.music_dir = os.path.join(self.temp_dir, "Music")
        os.makedirs(self.music_dir, exist_ok=True)

        self.outside_dir = os.path.join(self.temp_dir, "SecretOutside")
        os.makedirs(self.outside_dir, exist_ok=True)

        self.outside_file = os.path.join(self.outside_dir, "passwords.txt")
        with open(self.outside_file, "w") as f:
            f.write("secret=12345\n")

        self.outside_audio = os.path.join(self.outside_dir, "secret.flac")
        with open(self.outside_audio, "wb") as f:
            f.write(b"fLaC\x00\x00\x00\x22dummy")

        self.config_path = os.path.join(self.temp_dir, "config.json")
        self.db_path = os.path.join(self.temp_dir, "test.db")

        self.config = Config(self.config_path)
        self.config.data["music_directories"] = [self.music_dir]
        self.config.data["database_path"] = self.db_path
        self.config.data["supported_extensions"] = [".flac", ".mp3"]

        self.db = Database(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir)

    def test_is_path_allowed_canonicalization(self):
        # 1. Normal file inside
        inside_file = os.path.join(self.music_dir, "song.flac")
        self.assertTrue(self.config.is_path_allowed(inside_file))

        # 2. Traversal attempt using ..
        traversal = os.path.join(self.music_dir, "..", "SecretOutside", "passwords.txt")
        self.assertFalse(self.config.is_path_allowed(traversal))

        # 3. File symlink pointing outside
        symlink_to_outside = os.path.join(self.music_dir, "leak.flac")
        os.symlink(self.outside_audio, symlink_to_outside)
        self.assertFalse(self.config.is_path_allowed(symlink_to_outside))

        # 4. File symlink pointing inside
        real_inside = os.path.join(self.music_dir, "real.flac")
        with open(real_inside, "wb") as f:
            f.write(b"fLaC\x00\x00\x00\x22dummy")
        symlink_to_inside = os.path.join(self.music_dir, "alias.flac")
        os.symlink(real_inside, symlink_to_inside)
        self.assertTrue(self.config.is_path_allowed(symlink_to_inside))

    def test_scanner_skips_outside_symlinks(self):
        # Real audio file inside
        real_audio = os.path.join(self.music_dir, "track1.flac")
        with open(real_audio, "wb") as f:
            f.write(b"fLaC\x00\x00\x00\x22dummy")

        # Symlink pointing to outside file
        symlink_file = os.path.join(self.music_dir, "outside_symlink.flac")
        os.symlink(self.outside_audio, symlink_file)

        # Directory symlink pointing to outside directory
        symlink_dir = os.path.join(self.music_dir, "outside_dir_symlink")
        os.symlink(self.outside_dir, symlink_dir)

        def make_fake_meta(path):
            return {
                "path": path,
                "filename": os.path.basename(path),
                "file_size": 100,
                "mtime": 1700000000.0,
                "title": "Track",
                "artist": "Artist",
                "album": "Album",
                "album_artist": "Artist",
                "genre": "Test",
                "year": 2024,
                "track_number": 1,
                "disc_number": 1,
                "duration": 120.0,
                "codec": "FLAC",
                "sample_rate": 44100,
                "bit_depth": 16,
                "channels": 2,
                "bitrate": 1411200,
                "has_artwork": False,
            }

        scanner = LibraryScanner(self.config, self.db)
        with patch("server.scanner.extract_metadata", side_effect=make_fake_meta):
            stats = scanner.scan_sync()

        # Check tracks in database
        tracks, total = self.db.query_tracks()
        self.assertEqual(total, 1, "Only the real inside track should be indexed")
        self.assertEqual(tracks[0]["path"], os.path.realpath(real_audio))

        # Ensure no track in DB points to or originates from outside_dir
        for t in tracks:
            self.assertTrue(self.config.is_path_allowed(t["path"]))
            self.assertFalse(t["path"].startswith(self.outside_dir))

    def test_scanner_handles_recursive_directory_loops(self):
        # Create directory loop: music/subdir/self_loop -> music/subdir
        sub_dir = os.path.join(self.music_dir, "album")
        os.makedirs(sub_dir, exist_ok=True)
        loop_link = os.path.join(sub_dir, "self_loop")
        os.symlink(sub_dir, loop_link)

        # Create another loop pointing to music_dir root
        root_loop = os.path.join(sub_dir, "root_loop")
        os.symlink(self.music_dir, root_loop)

        # Real track
        track = os.path.join(sub_dir, "track.flac")
        with open(track, "wb") as f:
            f.write(b"fLaC\x00\x00\x00\x22dummy")

        def make_fake_meta(path):
            return {
                "path": path,
                "filename": os.path.basename(path),
                "file_size": 100,
                "mtime": 1700000000.0,
                "title": "Loop Test Track",
                "artist": "Artist",
                "album": "Album",
                "album_artist": "Artist",
                "genre": "Test",
                "year": 2024,
                "track_number": 1,
                "disc_number": 1,
                "duration": 100.0,
                "codec": "FLAC",
                "sample_rate": 44100,
                "bit_depth": 16,
                "channels": 2,
                "bitrate": 1411200,
                "has_artwork": False,
            }

        scanner = LibraryScanner(self.config, self.db)
        with patch("server.scanner.extract_metadata", side_effect=make_fake_meta):
            stats = scanner.scan_sync()

        # Scan should terminate cleanly and find exactly 1 track (not infinite copies)
        tracks, total = self.db.query_tracks()
        self.assertEqual(total, 1)

    def test_watcher_ignores_directory_symlinks(self):
        scanner = LibraryScanner(self.config, self.db)
        watcher = DirectoryWatcher(self.config, scanner)
        symlink_dir = os.path.join(self.music_dir, "sym_dir")
        os.symlink(self.outside_dir, symlink_dir)

        if not watcher._init_libc():
            self.skipTest("libc inotify not available on this platform")

        import ctypes
        watcher._inotify_fd = watcher._libc.inotify_init()
        try:
            # Add watches
            watcher.add_root(self.music_dir)

            # Check that symlink_dir is not added as a watch path
            for wd, path in list(watcher._wd_to_path.items()):
                self.assertFalse(os.path.islink(path), f"Watcher registered symlink path: {path}")
                self.assertFalse(path.startswith(self.outside_dir), f"Watcher registered outside path: {path}")
        finally:
            if watcher._inotify_fd is not None:
                os.close(watcher._inotify_fd)


if __name__ == "__main__":
    unittest.main()
