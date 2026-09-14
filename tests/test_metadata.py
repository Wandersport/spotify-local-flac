"""Unit tests for metadata extraction, including real FLAC validation if available."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.metadata import extract_metadata, extract_artwork_bytes


class TestMetadata(unittest.TestCase):
    def test_real_flac_files_if_available(self):
        root = os.environ.get("TEST_MUSIC_DIR", "")
        if not root or not os.path.isdir(root):
            self.skipTest("TEST_MUSIC_DIR not configured or directory not found")

        flac_files = []
        for dirpath, _, filenames in os.walk(root):
            for f in filenames:
                if f.lower().endswith(".flac"):
                    flac_files.append(os.path.join(dirpath, f))
                    if len(flac_files) >= 5:
                        break
            if len(flac_files) >= 5:
                break

        self.assertGreater(len(flac_files), 0, "No FLAC files found to test")

        for f in flac_files:
            meta = extract_metadata(f)
            self.assertIsNotNone(meta, f"Failed extracting metadata from {f}")
            self.assertEqual(meta["codec"], "FLAC")
            self.assertGreater(meta["duration"], 0)
            self.assertIn(meta["sample_rate"], (44100, 48000, 88200, 96000, 192000))
            self.assertIn(meta["bit_depth"], (16, 24, 32))
            self.assertTrue(len(meta["title"]) > 0)
            self.assertTrue(len(meta["artist"]) > 0)

            # Test artwork
            if meta["has_artwork"]:
                art_data, mime = extract_artwork_bytes(f)
                self.assertIsNotNone(art_data)
                self.assertIn(mime, ("image/jpeg", "image/png"))


if __name__ == "__main__":
    unittest.main()
