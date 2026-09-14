import unittest
import subprocess
import os
import urllib.request

class TestFolderNavigation(unittest.TestCase):
    def test_live_folder_navigation(self):
        """Run the automated CDP live folder navigation & state regression test."""
        try:
            with urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2):
                pass
        except Exception:
            self.skipTest("Live Spotify client with CDP (--remote-debugging-port=9222) not running")

        test_file = os.path.join(os.path.dirname(__file__), "test_folder_navigation.js")
        result = subprocess.run(["node", test_file], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, f"Folder navigation regression test failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")

if __name__ == "__main__":
    unittest.main()
