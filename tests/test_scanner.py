"""Regression tests for LibraryScanner exclusion semantics."""

import os
import shutil
import tempfile
import unittest

from server.config import Config
from server.db import Database
from server.scanner import LibraryScanner


class TestScannerExclusions(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config.json")
        self.music_dir = os.path.join(self.temp_dir, "Music")
        os.makedirs(self.music_dir, exist_ok=True)

        self.cfg = Config(self.config_path)
        self.cfg.data["music_directories"] = [self.music_dir]
        self.cfg.data["exclude_patterns"] = [
            ".*",
            "*recycle*",
            "*trash*",
            "*lost+found*"
        ]
        self.cfg.data["supported_extensions"] = [
            ".flac",
            ".alac",
            ".wav",
            ".mp3",
            ".ogg",
            ".m4a",
            ".opus",
            ".aiff"
        ]

        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.db = Database(self.db_path)
        self.scanner = LibraryScanner(self.cfg, self.db)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_should_exclude_unit_semantics(self):
        # 1. Supported audio files starting with dot must NOT be excluded
        self.assertFalse(
            self.scanner._should_exclude(
                os.path.join(self.music_dir, ".223 song.mp3"),
                ".223 song.mp3",
                is_dir=False
            )
        )
        self.assertFalse(
            self.scanner._should_exclude(
                os.path.join(self.music_dir, ".hidden.flac"),
                ".hidden.flac",
                is_dir=False
            )
        )

        # 2. Known hidden junk files must be excluded
        self.assertTrue(
            self.scanner._should_exclude(
                os.path.join(self.music_dir, ".DS_Store"),
                ".DS_Store",
                is_dir=False
            )
        )
        self.assertTrue(
            self.scanner._should_exclude(
                os.path.join(self.music_dir, "._song.mp3"),
                "._song.mp3",
                is_dir=False
            )
        )

        # 3. Hidden directories must be excluded
        self.assertTrue(
            self.scanner._should_exclude(
                os.path.join(self.music_dir, ".git"),
                ".git",
                is_dir=True
            )
        )
        self.assertTrue(
            self.scanner._should_exclude(
                os.path.join(self.music_dir, ".cache"),
                ".cache",
                is_dir=True
            )
        )

        # 4. Recycle / Trash / Lost+Found must be excluded
        self.assertTrue(
            self.scanner._should_exclude(
                os.path.join(self.music_dir, "$RECYCLE.BIN"),
                "$RECYCLE.BIN",
                is_dir=True
            )
        )
        self.assertTrue(
            self.scanner._should_exclude(
                os.path.join(self.music_dir, "Trash"),
                "Trash",
                is_dir=True
            )
        )
        self.assertTrue(
            self.scanner._should_exclude(
                os.path.join(self.music_dir, "lost+found"),
                "lost+found",
                is_dir=True
            )
        )
        self.assertTrue(
            self.scanner._should_exclude(
                os.path.join(self.music_dir, "trash_folder", "track.mp3"),
                "track.mp3",
                is_dir=False
            )
        )


if __name__ == "__main__":
    unittest.main()
