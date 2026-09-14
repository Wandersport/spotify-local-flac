"""Tests for large library scalability, pagination, and server-side sorting (up to 25,000 tracks)."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.db import Database


class TestPaginationLargeLibrary(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "large_library.db")
        self.db = Database(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir)

    def _populate_tracks(self, count: int):
        tracks = []
        for i in range(count):
            pad_i = f"{i:05d}"
            rev_i = f"{count - i:05d}"
            tracks.append({
                "path": f"/music/track_{pad_i}.flac",
                "filename": f"track_{pad_i}.flac",
                "title": f"Song {rev_i}",  # Reverse order so default title sort is opposite insertion
                "artist": f"Artist {i % 100:03d}",
                "album": f"Album {i % 20:03d}",
                "track_number": (i % 12) + 1,
                "disc_number": 1,
                "duration": 180.0 + (i % 60),
                "year": 2020 + (i % 5),
                "codec": "FLAC" if i % 2 == 0 else "MP3",
                "bitrate": 1411200,
                "sample_rate": 44100,
                "bit_depth": 16,
                "channels": 2,
                "file_size": 25000000,
                "mtime": 1700000000.0 + i,
                "has_artwork": False,
            })
        self.db.upsert_tracks_batch(tracks)

    def test_pagination_1000_tracks(self):
        self._populate_tracks(1000)
        tracks, total = self.db.query_tracks(limit=250, offset=0)
        self.assertEqual(total, 1000)
        self.assertEqual(len(tracks), 250)

        # Page 2
        tracks2, total2 = self.db.query_tracks(limit=250, offset=250)
        self.assertEqual(total2, 1000)
        self.assertEqual(len(tracks2), 250)
        self.assertNotEqual(tracks[0]["id"], tracks2[0]["id"])

    def test_pagination_beyond_5000_tracks_ceiling(self):
        # 5,001 tracks must not truncate or cap at 5,000
        count = 5001
        self._populate_tracks(count)

        # Query full total
        tracks, total = self.db.query_tracks(limit=500, offset=0)
        self.assertEqual(total, count, "Total tracks must be exactly 5001, not capped at 5000")
        self.assertEqual(len(tracks), 500)

        # Query offset 5000 (the 5001st track beyond previous ceiling)
        tracks_edge, total_edge = self.db.query_tracks(limit=500, offset=5000)
        self.assertEqual(total_edge, count)
        self.assertEqual(len(tracks_edge), 1, "Must return the 5001st track")
        self.assertEqual(tracks_edge[0]["filename"], "track_00000.flac")
        self.assertEqual(tracks_edge[0]["title"], f"Song {count:05d}")

    def test_pagination_10000_tracks(self):
        count = 10000
        self._populate_tracks(count)

        tracks, total = self.db.query_tracks(limit=500, offset=0)
        self.assertEqual(total, 10000)

        # Fetch offset 9500
        tracks_last, total_last = self.db.query_tracks(limit=500, offset=9500)
        self.assertEqual(len(tracks_last), 500)
        self.assertEqual(total_last, 10000)

    def test_pagination_25000_tracks(self):
        count = 25000
        self._populate_tracks(count)

        tracks, total = self.db.query_tracks(limit=1000, offset=0)
        self.assertEqual(total, 25000)

        # Query middle chunk at offset 12500
        tracks_mid, total_mid = self.db.query_tracks(limit=500, offset=12500)
        self.assertEqual(len(tracks_mid), 500)
        self.assertEqual(total_mid, 25000)

        # Query end chunk at offset 24500
        tracks_end, total_end = self.db.query_tracks(limit=1000, offset=24500)
        self.assertEqual(len(tracks_end), 500)

    def test_server_side_sorting_across_complete_library(self):
        # When sorting, the sort must be evaluated across ALL rows in the database,
        # not just the first page loaded.
        count = 6000
        self._populate_tracks(count)

        # Sort by title ascending: 'Song 00001' should be the very first row
        tracks_asc, total_asc = self.db.query_tracks(sort_by="title", sort_order="asc", limit=10, offset=0)
        self.assertEqual(total_asc, count)
        self.assertEqual(tracks_asc[0]["title"], "Song 00001")

        # Sort by title descending: 'Song 06000' should be the very first row
        tracks_desc, total_desc = self.db.query_tracks(sort_by="title", sort_order="desc", limit=10, offset=0)
        self.assertEqual(total_desc, count)
        self.assertEqual(tracks_desc[0]["title"], f"Song {count:05d}")

        # Sort by artist ascending
        tracks_art, total_art = self.db.query_tracks(sort_by="artist", sort_order="asc", limit=10, offset=0)
        self.assertEqual(tracks_art[0]["artist"], "Artist 000")

        # Sort by album ascending
        tracks_alb, total_alb = self.db.query_tracks(sort_by="album", sort_order="asc", limit=10, offset=0)
        self.assertEqual(tracks_alb[0]["album"], "Album 000")

    def test_codec_filtering(self):
        count = 2000
        self._populate_tracks(count)

        # 1000 FLAC, 1000 MP3
        tracks_flac, total_flac = self.db.query_tracks(codec="FLAC", limit=500, offset=0)
        self.assertEqual(total_flac, 1000)
        for t in tracks_flac:
            self.assertEqual(t["codec"], "FLAC")

        tracks_mp3, total_mp3 = self.db.query_tracks(codec="MP3", limit=500, offset=0)
        self.assertEqual(total_mp3, 1000)
        for t in tracks_mp3:
            self.assertEqual(t["codec"], "MP3")


if __name__ == "__main__":
    unittest.main()
