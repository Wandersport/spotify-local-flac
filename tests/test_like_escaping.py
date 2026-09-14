"""Tests for SQL LIKE query escaping (percent, underscore, and backslash)."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.db import Database, escape_like


class TestLikeEscaping(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_like.db")
        self.db = Database(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir)

    def test_escape_like_helper(self):
        self.assertEqual(escape_like("100% Hits"), "100\\% Hits")
        self.assertEqual(escape_like("track_01"), "track\\_01")
        self.assertEqual(escape_like("c:\\music"), "c:\\\\music")
        self.assertEqual(escape_like("50%_off\\now"), "50\\%\\_off\\\\now")
        self.assertEqual(escape_like("normal text"), "normal text")

    def test_folder_filtering_with_percent_and_underscore(self):
        tracks = [
            {
                "path": "/music/100% Hits/track1.flac",
                "filename": "track1.flac",
                "title": "Percent Track",
                "artist": "Artist",
                "album": "100% Hits",
                "duration": 180.0,
                "codec": "FLAC",
                "file_size": 1000,
                "mtime": 1000.0,
                "has_artwork": False
            },
            {
                "path": "/music/1000 Hits/track2.flac",
                "filename": "track2.flac",
                "title": "Zeroes Track",
                "artist": "Artist",
                "album": "1000 Hits",
                "duration": 180.0,
                "codec": "FLAC",
                "file_size": 1000,
                "mtime": 1000.0,
                "has_artwork": False
            },
            {
                "path": "/music/a_b/track3.flac",
                "filename": "track3.flac",
                "title": "Underscore Track",
                "artist": "Artist",
                "album": "a_b",
                "duration": 180.0,
                "codec": "FLAC",
                "file_size": 1000,
                "mtime": 1000.0,
                "has_artwork": False
            },
            {
                "path": "/music/axb/track4.flac",
                "filename": "track4.flac",
                "title": "Letter X Track",
                "artist": "Artist",
                "album": "axb",
                "duration": 180.0,
                "codec": "FLAC",
                "file_size": 1000,
                "mtime": 1000.0,
                "has_artwork": False
            }
        ]
        self.db.upsert_tracks_batch(tracks)

        # 1. Filter by folder "/music/100% Hits"
        # Without proper escaping, % would act as wildcard and also match "/music/1000 Hits"
        res_percent, total_percent = self.db.query_tracks(folder="/music/100% Hits")
        self.assertEqual(total_percent, 1)
        self.assertEqual(res_percent[0]["path"], "/music/100% Hits/track1.flac")

        # 2. Filter by folder "/music/a_b"
        # Without proper escaping, _ would act as wildcard and also match "/music/axb"
        res_under, total_under = self.db.query_tracks(folder="/music/a_b")
        self.assertEqual(total_under, 1)
        self.assertEqual(res_under[0]["path"], "/music/a_b/track3.flac")

    def test_search_escaping_with_percent_and_underscore(self):
        tracks = [
            {
                "path": "/music/t1.flac",
                "filename": "t1.flac",
                "title": "Top 100% Hits",
                "artist": "Artist A",
                "album": "Album A",
                "duration": 180.0,
                "codec": "FLAC",
                "file_size": 1000,
                "mtime": 1000.0,
                "has_artwork": False
            },
            {
                "path": "/music/t2.flac",
                "filename": "t2.flac",
                "title": "Top 1000 Hits",
                "artist": "Artist B",
                "album": "Album B",
                "duration": 180.0,
                "codec": "FLAC",
                "file_size": 1000,
                "mtime": 1000.0,
                "has_artwork": False
            },
            {
                "path": "/music/t3.flac",
                "filename": "t3.flac",
                "title": "Song a_b version",
                "artist": "Artist C",
                "album": "Album C",
                "duration": 180.0,
                "codec": "FLAC",
                "file_size": 1000,
                "mtime": 1000.0,
                "has_artwork": False
            },
            {
                "path": "/music/t4.flac",
                "filename": "t4.flac",
                "title": "Song axb version",
                "artist": "Artist D",
                "album": "Album D",
                "duration": 180.0,
                "codec": "FLAC",
                "file_size": 1000,
                "mtime": 1000.0,
                "has_artwork": False
            }
        ]
        self.db.upsert_tracks_batch(tracks)

        # Search exact "100%"
        res_p, total_p = self.db.query_tracks(search="100%")
        self.assertEqual(total_p, 1)
        self.assertEqual(res_p[0]["title"], "Top 100% Hits")

        # Search exact "a_b"
        res_u, total_u = self.db.query_tracks(search="a_b")
        self.assertEqual(total_u, 1)
        self.assertEqual(res_u[0]["title"], "Song a_b version")


if __name__ == "__main__":
    unittest.main()
